# 修复 Truth 文件覆盖模式 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:** 无
> **目的:** 修复所有累积型 truth 文件（resonance_trend.md、audit_drift.md、emotional_arcs.md、chapter_summaries.md、pending_hooks.md）仅含最后一章数据的缺陷——每次 state-settling 覆盖而非追加。

---

## 1. 背景

### 1.1 发现（D18-D20）

| Truth 文件 | 应有 | 实际 | 模式 |
|-----------|------|------|------|
| resonance_trend.md | 55-56 行 | **1 行**（Ch55） | 覆盖 |
| audit_drift.md | 55-56 节 | **1 节**（Ch55） | 覆盖 |
| emotional_arcs.md | 56 章条目 | **Ch55-56** | 覆盖 |
| chapter_summaries.md | 56 章引用 | **1 章** | 覆盖 |
| pending_hooks.md | 56 章钩子 | **Ch55-56** | 覆盖 |

所有 7 个 truth 文件的最后修改时间戳完全相同（21:17:47）——批量覆盖，非增量追加。

### 1.2 影响

- L1-L2 记忆层（6 层体系的核心）完全非功能
- 下游 skill 读取 truth 文件时仅看到最后一章的快照
- resonance 趋势分析、漂移检测、情感弧线追踪全部无效
- 这是 CN2（钩子系统）、CN4（style learning）、C2（文风漂移）等多个问题的**共同根因**

---

## 2. 根因分析

state-settling skill 的写入逻辑在每章执行时**重新生成整个 truth 文件**，而非追加新章节的数据。

可能原因：
1. LLM 被要求"更新 truth 文件"→ 自然行为是输出完整新版本
2. 追加逻辑需要在 prompt 中明确指示"保留现有内容，仅在末尾追加"
3. `safe_write` 是覆盖写入（`os.replace`），无追加模式

---

## 3. 修复方案

### 3.1 区分覆盖型与追加型 truth 文件

在 truth 文件元数据中标记更新模式：

```yaml
# truth 文件 frontmatter 新增
update_mode: append  # 或 replace
```

- **replace 模式**：current_state.md、character_matrix.md、current_focus.md（快照型）
- **append 模式**：resonance_trend.md、audit_drift.md、emotional_arcs.md、chapter_summaries.md、pending_hooks.md（累积型）

### 3.2 append 模式实现

```python
# truth 写入工具
def write_truth_file(project_dir, filename, new_content, mode='replace'):
    path = project_dir / 'truth' / filename
    if mode == 'append':
        existing = path.read_text() if path.exists() else ''
        # 仅追加新章节部分，不重复已有内容
        path.write_text(existing.rstrip() + '\n' + new_content)
    else:
        safe_write(path, new_content)
```

### 3.3 state-settling SKILL.md 更新

在 prompt 中明确指示追加型文件的处理方式：
- "对于追加型 truth 文件，**仅输出本章的新增内容**（一行/一节），不要重复前几章的数据"
- "对于覆盖型 truth 文件，输出完整的最新状态"

---

## 4. 验证标准

1. 运行 5 章 mini-pipeline → resonance_trend.md 有 5 行
2. 运行 5 章 mini-pipeline → chapter_summaries.md 引用 5 章
3. 追加不产生重复条目（同一章运行两次不会重复追加）
4. `just check` 全量通过

---

## 5. 依赖

```
本 Spec 是以下 Spec 的前置依赖：
  → CN2（钩子系统）— 依赖追加模式恢复 pending_hooks
  → CN4（style learning）— 需要历史 resonance 数据
  → C2（文风漂移）— 需要 resonance_trend 趋势数据
```
