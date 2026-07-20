# 修复跨章模板复制 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** Spec C2（语言学漂移检测）
> **目的:** 检测并阻止章节开头/结尾的模板复制——9 对章节开头 >60% 相似，Ch43/45/47 开头 89% 相同仅星期替换。

---

## 1. 背景

### 1.1 发现（D25 + Agent 2）

9 对章节开头 >60% 相似：

| 章节对 | 开头相似度 | 模式 |
|--------|-----------|------|
| Ch43↔Ch46 | 83% | "冷知道深度在第X层——冷在第X日知道深度" |
| Ch50↔Ch51 | 82% | "冷知道自己在周X——冷知道周X在周X之后" |
| Ch43↔Ch45 | 81% | 相同模板，仅星期替换 |
| Ch51↔Ch53 | 63% | 同上 |
| Ch52↔Ch53 | 75% | "冷知道周X在周X之后" |

Ch41↔Ch42 结尾 **100% 相同**。

### 1.2 影响

- 这些不是"风格一致性"，是**模板填空**
- 读者在连续章节中读到几乎相同的开头会感知到机械重复
- 这是散文崩塌（C2）的直接症状

---

## 2. 修复方案

### 2.1 与 Spec C2 合并检测

Spec C2 的语言学漂移检测器（`linguistic_drift.py`）中增加：

```python
# 跨章开头相似度检测
def check_opening_similarity(prev_chapter_text, current_chapter_text, threshold=0.6):
    prev_open = extract_opening(prev_chapter_text, chars=300)
    curr_open = extract_opening(current_chapter_text, chars=300)
    ratio = SequenceMatcher(None, prev_open, curr_open).ratio()
    if ratio > threshold:
        return f"OPENING_DUPLICATE:{ratio:.0%}"
    return None
```

### 2.2 Chapter planning prompt 注入

当检测到开头重复时，在下一章的 PRE_WRITE_CHECK 中注入：
- "前章开头与本篇高度相似（{ratio}%），请使用不同的开篇方式"
- "禁止使用'冷知道/冷在/冷在场于'句式开篇"

---

## 3. 验证标准

连续 5 章开头相似度 ≤ 40%

---

## 4. 依赖

```
Spec C2（语言学漂移检测）
  ↓
本 Spec（扩展检测指标）
```
