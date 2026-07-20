# Gate Marker 合并：21 个分散文件 → 单一 Manifest Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔵 Low
> **前置:** 无
> **目的:** 修复 G4 验证结果分散写入 21 个独立文件的根因——`run_gate_g4` 和 `cmd_post_skill` 每次调用独立写入，无中央聚合。

---

## 1. 背景

### 1.1 发现

`gate-markers/` 包含 21 个 JSON 文件（每个 skill 一个），总计 11 KB。每个文件独立记录一个 skill 的最后一次 G4 结果。

### 1.2 根因

`dispatch_helper.py:run_gate_g4()` 和 `phase_runner.py:cmd_post_skill()` 在每次 G4 检查后直接写入 `gate-markers/G4-{skill}-{test_type}.json`。无中央聚合机制——每个 skill 独立管理自己的 gate marker。

对于 chapter loop 中每章运行的 skill（如 `shenbi-chapter-drafting`），gate marker 被反复覆盖——仅保留最后一次结果，丢失了历史 G4 通过/失败记录。

### 1.3 为什么需要修复

- 无法追踪 G4 结果的**历史趋势**（某 skill 是否越来越频繁地失败？）
- 21 个碎片文件增加 I/O 和 inode 消耗
- 下游工具需 glob 21 个文件才能了解完整门禁状态

---

## 2. 上游修复

### 2.1 中央 Manifest 结构

`gate-markers/pipeline-manifest.json`：

```json
{
  "pipeline": "xinghuo-ranqiong",
  "updated_at": "2026-07-17T21:32:04Z",
  "gates": {
    "genesis": {
      "shenbi-worldbuilding": {
        "G4": {"status": "PASS", "timestamp": "...", "checks": {...}}
      }
    },
    "chapter_loop": {
      "1": {
        "shenbi-chapter-drafting": {
          "G4": {"status": "PASS", "timestamp": "...", "checks": {...}}
        }
      }
    }
  }
}
```

### 2.2 写入逻辑修改

```python
# dispatch_helper.py 或 chapter_loop.py

def record_gate_result(project_dir, phase, chapter, skill, gate, result):
    manifest_path = project_dir / 'gate-markers' / 'pipeline-manifest.json'

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {'pipeline': str(project_dir.name), 'gates': {}}

    # 按 phase → chapter → skill → gate 组织
    phase_key = phase  # 'genesis' or 'chapter_loop'
    chapter_key = str(chapter) if chapter else 'genesis'

    manifest.setdefault('gates', {}).setdefault(phase_key, {}).setdefault(chapter_key, {}).setdefault(skill, {})[gate] = result
    manifest['updated_at'] = datetime.now(timezone.utc).isoformat()

    safe_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
```

### 2.3 向后兼容

保留旧格式的读取支持（过渡期），但新写入仅使用 manifest：

```python
def get_gate_result(project_dir, skill, gate='G4'):
    # 优先新格式
    manifest_path = project_dir / 'gate-markers' / 'pipeline-manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        # 搜索所有 phase/chapter
        for phase, chapters in manifest.get('gates', {}).items():
            for chapter, skills in chapters.items():
                if skill in skills and gate in skills[skill]:
                    return skills[skill][gate]

    # 回退旧格式
    old_path = project_dir / 'gate-markers' / f'{gate}-{skill}-generative.json'
    if old_path.exists():
        return json.loads(old_path.read_text())

    return None
```

---

## 3. 下游影响

- Pipeline status 报告（`pipeline-status`）可从单一文件读取所有门禁状态
- 可追踪每章每 skill 的 G4 历史趋势
- 现有读取单个 gate marker 的代码需通过 `get_gate_result()` 适配

---

## 4. 验证标准

1. Genesis 完成后 manifest 包含所有 genesis skill 的 G4 结果
2. 每章完成后 manifest 包含该章所有 skill 的 G4 结果
3. `get_gate_result('shenbi-chapter-drafting', 'G4')` 返回最近一次结果
4. 旧格式读取兼容
5. `just check` 全量通过

---

## 5. 依赖

```
无前置依赖（独立改进）
  ↓
pipeline-status 报告可消费新 manifest
```
