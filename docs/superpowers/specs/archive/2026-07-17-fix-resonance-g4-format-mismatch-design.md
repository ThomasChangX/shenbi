# 修复 G4 共振审计格式冲突 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟡 Medium
> **前置:** 无
> **目的:** 消除 shenbi-review-resonance 的 G4 结构性失败——35 次重试全部是 `no_valid_verdict`，表明 LLM 产出的 resonance 报告格式与 G4 checker 期望不匹配。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

54 条 retry_feedback 中，35 条（65%）来自 `shenbi-review-resonance`：

```
ch1-shenbi-review-resonance: G4 HARD check failed: ["G4.rr.detail_table:chapter-1-resonance.md:missing_['裁判理由']"]
ch2-shenbi-review-resonance: G4 HARD check failed: ['G4.rr.verdict:chapter-2-resonance.md:no_valid_verdict', 'G4.rr.evidence:...']
ch10-shenbi-review-resonance: G4 HARD check failed: ['G4.rr.verdict:chapter-10-resonance.md:no_valid_verdict']
...
```

模式分析：
- `no_valid_verdict` 出现最频繁 — LLM 产出的 `校准门判定` 行不符合正则
- `missing_['裁判理由']` — 评分明细表缺少列
- `no_file_line_ref` — 证据列缺少 `文件:行号` 引用

### 1.2 G4 checker 的期望

`gates/g4/review_resonance.py:28-89` 的三个检查：

1. **G4.rr.detail_table**（line 48-57）：评分明细表必须有 6 列头：`维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由`
2. **G4.rr.verdict**（line 61-72）：`校准门判定` 节必须有 `判定: 通过 / 阻断 / 待人机复核`
3. **G4.rr.evidence**（line 75-82）：至少一个 `L\d+|line\s+\d+|:\d+` 引用

### 1.3 为什么重试后仍未解决

G4 失败后的 feedback 只返回检查 ID（如 `G4.rr.verdict`），不返回**具体的格式期望**。LLM 看到 "verdict failed" 但不知道期望什么格式，于是重新生成——仍然不对——再次失败。

---

## 2. 修复方案

### 2.1 G4 feedback 增强（主要修复）

在 `chapter_loop.py` 的 retry feedback 构造中，对 G4 失败附加具体的格式示例：

```python
# chapter_loop.py: _build_retry_feedback 或等效位置

G4_FORMAT_EXAMPLES = {
    "G4.rr.detail_table": (
        "评分明细表格式：\n"
        "| 维度 | 得分 | 满分 | 置信度 | 证据 | 裁判理由 |\n"
        "|------|------|------|--------|------|----------|\n"
        "| 情感落地 | 25 | 30 | 高 | chapter-N.md L45-52 > ... | ... |"
    ),
    "G4.rr.verdict": (
        "校准门判定必须包含以下行：\n"
        "判定: 通过    （或：判定: 阻断  / 判定: 待人机复核）\n"
        "注意：'判定: ' 后必须有空格，且必须使用中文冒号"
    ),
    "G4.rr.evidence": (
        "证据列每行必须包含文件和行号引用，格式：\n"
        "chapter-N.md L45-52 > \"引用原文\""
    ),
}

def _enrich_g4_feedback(failures: list[str]) -> str:
    feedback = "以下 G4 检查失败，请按指定格式修正：\n\n"
    for f in failures:
        check_id = f.split(":")[0] if ":" in f else f
        feedback += f"- **{f}**\n"
        if check_id in G4_FORMAT_EXAMPLES:
            feedback += f"  期望格式：\n  {G4_FORMAT_EXAMPLES[check_id]}\n"
    return feedback
```

### 2.2 SKILL.md prompt 强化

在 `skills/shenbi-review-resonance/SKILL.md` 的输出格式节增加**具体示例**（当前仅描述字段名，无完整示例行）。

### 2.3 乐观解析

在 `review_resonance.py` 的 G4 checker 中增加容错：

```python
# 对 verdict 检查，允许多种合理变体
VERDICT_PATTERNS = [
    r'判定[：:]\s*(通过|阻断|待人机复核)',
    r'\*\*判定\*\*[：:]\s*(通过|阻断|待人机复核)',
    r'Verdict[：:]\s*(PASS|BLOCK|HUMAN_REVIEW)',
]
```

---

## 3. 验证标准

1. 构造 3 种常见格式错误 → enriched feedback 包含具体示例
2. 连续运行 5 次 resonance audit → 重试次数 ≤ 1
3. 乐观解析正确匹配合法变体

---

## 4. 依赖关系

```
无前置依赖（独立修复）
  ↓
下游：Spec M1（Token 浪费）受益于重试减少
```
