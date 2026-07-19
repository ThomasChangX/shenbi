# Pipeline 运行时运维优化 Spec

> **日期:** 2026-07-18
> **状态:** 设计中
> **严重度:** 🟡 Medium
> **前置:** Spec CN3（Truth 追加）、Spec SCR 预提取
> **目的:** 修复 5 个小但累积影响显著的运行时问题——META 块被下游消费、genre-config 重复磁盘 I/O、truth-index 陈旧、pipeline-state 膨胀、世界文件未更新。

---

## 1. 优化项

### 1.1 META 块被非 drafting 调用消费

**问题**：13 个审计器 + state-settling + lifecycle 全部读取包含 `<!--META-BEGIN-->...<!--META-END-->` 块的完整章节。审计器不需要知道"转折词预算=5"或"本章禁忌=不揭示MH-020"——这些是 drafting 的自检清单。

**证据**：Ch10 中 16% 的字符是 META 块。平均 31%。

**修复**（`dispatch_helper.py` 或 SCR 提取器中）：

```python
import re

_META_PATTERN = re.compile(r'<!--META-BEGIN-->.*?<!--META-END-->', re.DOTALL)

def _strip_meta_for_non_drafting(skill_name: str, text: str) -> str:
    """对非 drafting skill 剥离 META 块。

    drafting 本身需要这些块（PRE_WRITE_CHECK 指导写作），
    但审计器和 state-settling 不需要。
    """
    if skill_name in ('shenbi-chapter-drafting', 'shenbi-chapter-revision'):
        return text  # drafting 和 revision 需要完整内容
    return _META_PATTERN.sub('', text)
```

**节省**：每个非 drafting 调用减少 16-31% 输入。

---

### 1.2 genre-config.json 内存缓存

**问题**：`genre-config.json`（3.6KB）被每章 ~8 个 skill 独立读取——每次触发磁盘 I/O。

**修复**（`dispatch_helper.py`）：

```python
# 模块级缓存：每章仅从磁盘读取一次
_GENRE_CONFIG_CACHE: dict = {'chapter': -1, 'data': None}

def _get_genre_config(project_dir: Path, chapter: int) -> dict:
    if _GENRE_CONFIG_CACHE['chapter'] == chapter:
        return _GENRE_CONFIG_CACHE['data']

    path = project_dir / 'genre-config.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    _GENRE_CONFIG_CACHE['chapter'] = chapter
    _GENRE_CONFIG_CACHE['data'] = data
    return data
```

**节省**：每章 ~7 次磁盘 I/O → 1 次。

---

### 1.3 truth-index.json 周期性重建

**问题**：`truth-index.json` 在 Genesis 构建后从未重建。随着 56 章 truth 文件累积，索引不再反映实际内容。

**修复**：

```python
# chapter_loop.py: _complete_chapter 中

def _maybe_rebuild_truth_index(project_dir, chapter):
    """每卷边界或每 15 章重建 truth-index。"""
    # 卷边界章节：15, 35, 55, 75, 100
    volume_boundaries = _get_volume_boundaries(project_dir)
    if chapter in volume_boundaries or chapter % 15 == 0:
        from shenbi.pipeline.truth_index import build_index
        build_index(project_dir)
        logger.info("truth_index_rebuilt", chapter=chapter)
```

---

### 1.4 pipeline-state.json 增量写入

**问题**：`pipeline-state.json` 132KB/56章，每次 `json.dump` 全量写入。retry_feedback（54条）和 soft_fail_trackers 永久累积。

**修复**：

```python
# state.py: save_pipeline_state

def _compact_chapter_states(state: PipelineState, keep_last: int = 10):
    """归档已完成的章，仅保留最近 N 章在活跃状态中。"""
    cl = state.chapter_loop
    all_chapters = sorted(cl.chapter_states.keys(), key=int)

    if len(all_chapters) <= keep_last:
        return

    # 归档旧章
    archive = {}
    for ch in all_chapters[:-keep_last]:
        archive[ch] = cl.chapter_states.pop(ch)

    # 写入归档文件
    archive_path = project_dir / 'pipeline-state-archive.json'
    existing = json.loads(archive_path.read_text()) if archive_path.exists() else {}
    existing.update(archive)
    safe_write(archive_path, json.dumps(existing, ensure_ascii=False))

def _prune_retry_feedback(state: PipelineState, keep_last: int = 30):
    """仅保留最近 N 条 retry feedback。"""
    rf = state.chapter_loop.retry_feedback
    if len(rf) > keep_last:
        # 保留最近 N 条（按 key 中的章节号排序）
        keys = sorted(rf.keys(), key=lambda k: int(re.findall(r'\d+', k)[0]) if re.findall(r'\d+', k) else 0)
        for old_key in keys[:-keep_last]:
            del rf[old_key]
```

---

### 1.5 世界文件周期性审查

**问题**：`world/` 下 5 个文件（rules, power_system, locations, factions, story_bible）在 Genesis 写入后从未更新。故事已从铁炉堡发展到迷雾山脉，但 `locations.md` 从未添加新地点。

**修复**：卷边界触发——非 LLM，为人类提供"是否需要在下一卷前更新世界文件"的检查清单：

```python
# chapter_loop.py: _complete_chapter 中

def _check_world_file_freshness(project_dir, chapter):
    """卷边界时检查世界文件是否需要更新。"""
    volume_boundaries = _get_volume_boundaries(project_dir)
    if chapter not in volume_boundaries:
        return

    # 检查 locations.md 中是否包含最近 10 章出现的新地点
    from shenbi.pipeline.scr_extractor import extract_scr

    new_locations = set()
    for ch in range(chapter - 10, chapter + 1):
        scr = extract_scr(project_dir, ch)
        for loc in scr.world_refs:
            if loc['category'] == 'location':
                new_locations.add(loc['element'])

    locations_md = (project_dir / 'world' / 'locations.md').read_text()
    missing = [loc for loc in new_locations if loc not in locations_md]

    if missing:
        logger.warning("world_locations_stale", chapter=chapter, missing_locations=missing)
        # 生成人类审查提示（非阻断）
        _append_human_review_note(project_dir, f"卷{_get_volume_number(chapter)}结束："
                                  f"以下新地点未在 world/locations.md 中记录：{missing}")
```

---

## 2. 效果

| 优化项 | 影响 |
|--------|------|
| META 剥离 | 13 个审计 + state-settling + lifecycle 输入 -20% |
| genre-config 缓存 | 每章 ~7 次磁盘 I/O → 1 次 |
| truth-index 重建 | Route B 嵌入搜索覆盖新内容 |
| state 压缩 | pipeline-state.json 从 236KB→~80KB（100章时） |
| 世界文件审查 | 卷边界人类提示——非阻断 |

---

## 3. 验证标准

1. 审计 skill 收到的章节输入不含 `<!--META-BEGIN-->` 块
2. 同一章内多次请求 `genre-config.json` 仅触发一次磁盘读取
3. 卷边界后 `truth-index.json` 的 mtime 更新
4. 100 章模拟后 `pipeline-state.json` < 100KB
5. 新地点出现时日志输出 WARNING
6. `just check` 全量通过
