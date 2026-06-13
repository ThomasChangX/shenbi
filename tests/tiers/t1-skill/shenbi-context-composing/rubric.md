# T1 Rubric: shenbi-context-composing

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Completeness | 20% | All P1 items present; higher-priority items never trimmed before lower |
| 4 | Accuracy | 15% | Extracted summaries match source truth files word-for-word for key facts |
| 5 | Hook urgency calculation | 15% | Computes (current_chapter - last_reinforced) / max_distance |
| 6 | Ending diversity check | 15% | Flags if recent 3 chapters share same ending pattern |
| 7 | Recency | 10% | Only summaries from last 2 chapters (per SKILL.md P2 rule); hooks sorted by urgency, max 3 |
| 8 | Hook debt brief quality | 10% | Debt brief lists every active hook with status, silence chapters, and action suggestion |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Missed planted defect (false negative) → total score = 0
- Evidence without file+line citation → detection dimension = 0
- HARD-GATE violation → total score = 0

### Clean Kill Switches
- Any hallucinated defect (false positive) → total score = 0
- HARD-GATE violation → total score = 0

### Generative Kill Switches
- HARD-GATE violation → total score = 0

## Dimension Applicability by Test Type

| # | Dimension | Bug-hunt Standard | Clean Standard |
|---|-----------|------------------|----------------|
| 1 | Instruction adherence | Executed all review/audit steps from SKILL.md; detection workflow followed | Executed all review/audit steps from SKILL.md; zero-defect verification workflow followed |
| 2 | Output completeness | Detection report present with required sections: defect description, location(file+line), violated rule, evidence, severity | Clean report present with required sections: files checked, confirmation of zero findings, per-file sign-off |
| 3 | Completeness | **Detection accuracy**: All planted defects found with file+line evidence. Missing evidence → 0. Incorrect rule identification → 0. | **Zero hallucination**: No defects reported. Any reported issue → kill switch. "Improvement suggestion" = hallucinated defect. |
| 4 | Accuracy | **False positive control**: Zero clean content flagged as defective. Any false positive → -30pts. | **Thoroughness**: Every file/section explicitly checked. Skipped file → 0. |
| 5 | Hook urgency calculation | **Rule application**: Violated rule correctly identified by name. Wrong rule → 0. Vague reference → -20pts. | **Restraint**: No fabricated "minor issues" to appear useful. Fabrication → kill switch. |
| 6 | Ending diversity check | **Evidence quality**: Citations include file path + line number. Missing → 0. Approximate → -15pts. | **Completeness**: All required output sections checked. Partial check → -25pts per missed section. |
| 7 | Recency | **Detection accuracy**: All planted defects found with file+line evidence. Missing evidence → 0. Incorrect rule identification → 0. | **Zero hallucination**: No defects reported. Any reported issue → kill switch. "Improvement suggestion" = hallucinated defect. |
| 8 | Hook debt brief quality | **Detection accuracy**: All planted defects found with file+line evidence. Missing evidence → 0. Incorrect rule identification → 0. | **Zero hallucination**: No defects reported. Any reported issue → kill switch. "Improvement suggestion" = hallucinated defect. |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
