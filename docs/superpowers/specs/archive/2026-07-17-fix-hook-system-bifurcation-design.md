# 修复钩子系统分叉：MH→P0 静默遗弃 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:** 无
> **目的:** 修复 12 个 MH-xxx 钩子在 Ch42 被静默替换为 P0-xx 参数钩子的缺陷——无映射、无 resolve、pending_hooks.md 零标准化 ID。

---

## 1. 背景

### 1.1 发现

**Agent 1 Audit 2** + **D4**：

- `pending_hooks.md` 使用**非标准化格式**（零 MH-xxx/PO-xxx ID）
- 但 12 个 MH-xxx ID 在章节 META 块中被引用（MH-001 至 MH-028）
- Ch42 起，钩子系统从 MH-xxx 静默切换为 P0-xx
- `book_spine.md` 6 个主钩子（MH01-MH06）全部显示 0% 进度
- foreshadowing-plant/track/recall 虽在所有 56 章运行，但输出从未写入结构化 pending_hooks

### 1.2 影响

- 整个伏笔经济系统（shenbi 的核心设计优势之一）**完全非功能**
- 早期钩子（金属片 MH-001、手机 MH-020、催收 MH-022 等）从未 resolve
- 无钩子生命周期追踪（PLANTED→RELEVANT→TRIGGERED→RESOLVED）

---

## 2. 根因分析

### 2.1 双重根因

**根因 1：foreshadowing skill 输出格式与 pending_hooks.md 不兼容**

foreshadowing-plant/track 产出的钩子数据未被正确追加到 `pending_hooks.md`。skill 运行了（D11 证实 56/56 章），但输出可能：
- 被写入 staging 但未 commit
- 格式不匹配 pending_hooks.md 的解析器

**根因 2：state-settling 覆盖了 pending_hooks.md**

D19 显示所有 truth 文件都是覆盖模式。每次 state-settling 用当前章数据**替换**整个文件，销毁了历史钩子数据。

---

## 3. 修复方案

### 3.1 强制追加模式

`pending_hooks.md`（以及所有累积型 truth 文件）改为**追加**而非覆盖：

```python
# truth 写入工具函数
def append_to_truth(project_dir, truth_file, new_section):
    """追加新章节数据到 truth 文件，而非覆盖。"""
    path = project_dir / "truth" / truth_file
    existing = path.read_text() if path.exists() else ""
    path.write_text(existing + "\n" + new_section)
```

### 3.2 钩子 ID 标准化

`pending_hooks.md` 强制使用标准化格式：

```markdown
| Hook ID | 生命周期 |  planted_ch | last_ch | 文本依据 |
|---------|---------|------------|---------|---------|
| MH-001  | TRIGGERED | 1 | 20 | chapter-20.md L15-24 > "和昨天一样" |
```

### 3.3 钩子迁移映射

如果叙事自然演进导致钩子重新概念化（MH→P0），需要：
1. 在 `pending_hooks.md` 中记录映射文档
2. 旧钩子标记为 RESOLVED（附注新 ID 映射）
3. 新钩子标记来源

---

## 4. 验证标准

1. `pending_hooks.md` 包含所有 56 章的钩子数据（非仅最后一章）
2. 所有钩子 ID 标准化（MH-xxx 或 P0-xx 格式）
3. 无未 resolve 的孤立钩子
4. `just check` 全量通过

---

## 5. 依赖

```
Spec CN3（Truth 文件覆盖模式）← 共享根因（追加 vs 覆盖）
  ↓
本 Spec
```
