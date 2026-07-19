# 修复所有章节 resonance_score 为 null Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** Spec CN3（Truth 文件追加模式）
> **目的:** 修复评分系统——所有 56 章 resonance_score 为 null，resonance_trend.md 仅 1 行。

---

## 1. 背景

### 1.1 发现（Agent 3 §6）

- 所有 56 章 `resonance_score: null`
- `resonance_trend.md` 仅 Ch55 有一个 70/100 条目（D5）
- `shenbi-review-resonance` 通过了 G4 门禁但分数从未存储

### 1.2 影响

- 整个评分系统形同虚设
- 无法追踪章节质量趋势
- 无法触发基于分数的修订路由
- resonance 重试（35 次）的 G4 失败只检查格式，不检查分数是否被存储

---

## 2. 根因分析

resonance 审计报告（`audits/chapter-N-resonance.md`）包含评分明细表，但这些分数需要被**解析并写入** `resonance_trend.md` 和 pipeline state。

当前缺失环节：
1. G4 检查了 resonance 报告的**格式**（有无 detail_table、verdict、evidence）
2. 但无人解析报告中的**分数**并写入结构化存储
3. `_route_revision_after_resonance`（`chapter_loop.py:1427`）可能期望从某处读取分数但读不到

---

## 3. 修复方案

### 3.1 分数解析器

```python
def parse_resonance_scores(audit_path):
    """从 resonance 审计报告中解析分数。"""
    text = audit_path.read_text()
    scores = {}
    for match in re.finditer(r'\|\s*(\S+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\S+)\s*\|', text):
        dim, score, max_score, conf = match.groups()
        scores[dim] = {'score': int(score), 'max': int(max_score), 'confidence': conf}
    overall = sum(s['score'] for s in scores.values())
    return scores, overall
```

### 3.2 分数写入 pipeline state

在 resonance G4 通过后：
```python
scores, overall = parse_resonance_scores(resonance_audit_path)
ch_state['resonance_score'] = overall
ch_state['resonance_dimensions'] = scores
```

### 3.3 追加到 resonance_trend.md

依赖 Spec CN3（追加模式）：
```python
trend_row = f"| {chapter} | {chapter_role} | {scores['情感落地']['score']} | ... | {overall} | {confidence} | |"
append_to_truth(project_dir, 'resonance_trend.md', trend_row)
```

---

## 4. 验证标准

1. 运行 3 章 → 所有 3 章 resonance_score ≠ null
2. resonance_trend.md 有 3 行数据
3. `just check` 全量通过
