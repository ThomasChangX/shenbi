# T1 Rubric: shenbi-faction-builder

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Interest-driven realism | 20% | Faction behavior explainable by interest logic; no "evil for evil's sake" |
| 4 | Internal conflict | 15% | Every faction has ≥1 internal factional split |
| 5 | Cross-faction dynamics | 15% | ≥2 factions have explicit relationships |
| 6 | Anchor character consistency | 15% | Referenced characters exist in characters/*.md |
| 7 | Behavioral predictability | 10% | "In situation X, faction does Y" patterns defined |
| 8 | Prose quality | 10% | Faction descriptions are narrative prose |

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
| 3 | Interest-driven realism | **Detection accuracy**: All planted defects found with file+line evidence. Missing evidence → 0. Incorrect rule identification → 0. | **Zero hallucination**: No defects reported. Any reported issue → kill switch. "Improvement suggestion" = hallucinated defect. |
| 4 | Internal conflict | **False positive control**: Zero clean content flagged as defective. Any false positive → -30pts. | **Thoroughness**: Every file/section explicitly checked. Skipped file → 0. |
| 5 | Cross-faction dynamics | **Rule application**: Violated rule correctly identified by name. Wrong rule → 0. Vague reference → -20pts. | **Restraint**: No fabricated "minor issues" to appear useful. Fabrication → kill switch. |
| 6 | Anchor character consistency | **Evidence quality**: Citations include file path + line number. Missing → 0. Approximate → -15pts. | **Completeness**: All required output sections checked. Partial check → -25pts per missed section. |
| 7 | Behavioral predictability | **Detection accuracy**: All planted defects found with file+line evidence. Missing evidence → 0. Incorrect rule identification → 0. | **Zero hallucination**: No defects reported. Any reported issue → kill switch. "Improvement suggestion" = hallucinated defect. |
| 8 | Prose quality | N/A — exempted: Prose quality is a content-generation metric; no meaningful bug-hunt or clean interpretation for a review/detection workflow. scoring.py renormalizes weights for remaining applicable dimensions. | N/A — exempted: Same as bug-hunt. |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
