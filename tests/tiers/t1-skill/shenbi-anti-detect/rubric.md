# T1 Rubric: shenbi-anti-detect

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Content preservation | 15% | No changes to plot, characters, or foreshadowing |
| 4 | Targeted intervention | 15% | Only rewrites at detected marker points; no wholesale rewriting |
| 5 | Audit pass rate | 15% | Anti-AI audit passes after rewriting |
| 6 | Style preservation | 15% | Does not lose authorial voice; zero new AI-typical patterns introduced |
| 7 | Bounded iteration | 15% | After 3 failed passes, reverts to best version |
| 8 | Before/after audit comparison | 10% | Clear before/after error and warning counts with per-marker-type breakdown |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Missed planted defect (false negative) -> total score = 0
- HARD-GATE violation -> total score = 0

### Clean Kill Switches
- Any hallucinated defect (false positive) -> total score = 0
- HARD-GATE violation -> total score = 0

### Generative Kill Switches
- HARD-GATE violation -> total score = 0

## Dimension Applicability by Test Type

| Dimension scope | Bug-hunt | Clean | Generative |
|----------------|----------|-------|------------|
| Universal (1-2) | Yes | Yes | Yes |
| All bespoke | Yes (detection quality) | Yes (report quality) | Yes (output quality) |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered -> final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
