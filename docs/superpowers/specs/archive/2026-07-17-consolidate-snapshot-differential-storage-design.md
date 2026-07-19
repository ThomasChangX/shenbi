# 快照差量存储：消除 12.3MB 全量复制 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** Spec M3（快照覆盖缺口）
> **目的:** 修复 `_snapshot_chapter_files` 将完整章节+完整审计报告+完整 truth 文件全量复制到每个快照的根因——快照应为轻量级恢复点，而非完整仓库副本。

---

## 1. 背景

### 1.1 发现

51 个快照占用 **12.3 MB（总产出的 52%）**。每个快照包含：
- 完整当前章节正文
- 完整 13 种审计报告
- 完整 truth 文件快照
- 风格文件和角色文件

快照大小 = 172% ×（章节文件 + 审计文件总和）。样本（Ch25）中 ~34% 是与 `audits/` 目录逐字节重复的审计内容。

### 1.2 根因

`chapter_loop.py:903-960`（`_snapshot_chapter_files`）：

```python
# 当前实现：全量文件复制
for pattern in ['truth/*.md', 'chapters/chapter-{NNN}.md',
                'plans/chapter-{N}-plan.md', 'style/style_profile.md',
                'characters/*.md']:
    for f in project_dir.glob(pattern):
        content = f.read_text()
        snapshot_text += f"\n## {f.relative_to(project_dir)}\n\n{content}\n"
```

**问题**：审计报告（`audits/chapter-N-*.md`）也被全量复制到快照中。这些文件：
- 已经独立存在于 `audits/` 目录
- 快照生成后不会改变（审计是历史记录）
- 平均占快照大小的 30-40%

章节正文同理——已在 `chapters/chapter-N.md` 中，快照是第二份完整副本。

### 1.3 为什么这是根因而非"合理设计"

快照的目的是**恢复点**——在 rollback 时恢复到已知良好状态。恢复点只需要：
1. 哪些文件在哪个版本（hash/checksum）
2. truth 文件的状态快照（唯一在快照时可能不同的内容）

不需要：完整审计报告副本（已在 `audits/` 中）、完整章节正文副本（已在 `chapters/` 中）。

---

## 2. 上游修复

### 2.1 `_snapshot_chapter_files` 改为差量模式

```python
# chapter_loop.py:903-960 重构

def _snapshot_chapter_files(project_dir, state, force=False, label=None):
    """生成轻量级快照：仅存储文件哈希 + truth 文件内容。

    章节正文和审计报告通过哈希引用——不从磁盘复制。
    """
    chapter = state.chapter_loop.current_chapter
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')

    manifest = {
        'chapter': chapter,
        'timestamp': timestamp,
        'label': label,
        'files': {},
        'truth_snapshot': {}
    }

    # 1. 对可恢复文件仅存储哈希（不复制内容）
    for pattern_key, pattern in [
        ('chapter', f'chapters/chapter-{chapter:03d}.md'),
        ('plan', f'plans/chapter-{chapter}-plan.md'),
    ]:
        f = project_dir / pattern
        if f.exists():
            manifest['files'][pattern_key] = {
                'path': pattern,
                'sha256': hashlib.sha256(f.read_bytes()).hexdigest(),
                'size': f.stat().st_size
            }

    # 2. 对审计文件：记录存在性和哈希（不复制内容）
    manifest['audit_files'] = {}
    for af in sorted((project_dir / 'audits').glob(f'chapter-{chapter}-*.md')):
        manifest['audit_files'][af.name] = {
            'sha256': hashlib.sha256(af.read_bytes()).hexdigest(),
            'size': af.stat().st_size
        }

    # 3. truth 文件：保存完整内容（唯一需要在回滚时恢复的易变状态）
    for tf in sorted((project_dir / 'truth').glob('*.md')):
        manifest['truth_snapshot'][tf.name] = tf.read_text()

    # 4. 写入轻量级 manifest
    snapshot_dir = project_dir / 'snapshots'
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = snapshot_dir / f'chapter-{chapter:03d}-{timestamp}.json'
    safe_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
```

### 2.2 恢复逻辑

Rollback 时从 manifest 重建：

```python
def restore_from_snapshot(project_dir, snapshot_path):
    manifest = json.loads(snapshot_path.read_text())

    # 1. 恢复 truth 文件（从快照内容）
    for name, content in manifest['truth_snapshot'].items():
        safe_write(project_dir / 'truth' / name, content)

    # 2. 章节和审计文件通过哈希验证——如果当前文件哈希不匹配，说明被修改过
    #    但通常不需要恢复（它们在快照后未被修改）
    for key, info in manifest['files'].items():
        current = project_dir / info['path']
        if current.exists():
            current_hash = hashlib.sha256(current.read_bytes()).hexdigest()
            if current_hash != info['sha256']:
                logger.warning("snapshot_mismatch", file=info['path'],
                               snapshot_hash=info['sha256'], current_hash=current_hash)
```

---

## 3. 下游影响

- `shenbi-snapshot-manage` SKILL.md 需更新输出格式
- `pipeline rollback` 需使用新 manifest 格式
- 现有快照消费者（如有）需适配 JSON manifest 替代 markdown 快照

---

## 4. 验证标准

1. 新快照大小 ≤ 章节文件 × 2（非 172%）
2. Rollback 测试：从快照恢复 → truth 文件正确恢复
3. Hash 验证：修改章节文件后 snapshot 检测到不匹配
4. 旧 markdown 快照格式兼容读取（过渡期）

---

## 5. 依赖

```
Spec M3（快照覆盖缺口）← 确保所有章节有快照
  ↓
本 Spec（快照改为轻量级）
  ↓
pipeline rollback 恢复逻辑更新
```
