# T1 Rubric: shenbi-chapter-drafting

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Plan compliance | 15% | Chapter executes memo specifications |
| 4 | AI-flavor avoidance | 15% | Transition word density <=1/3000 words; zero meta-narrative prose |
| 5 | Voice fidelity | 15% | Every dialogue line matches character voice_profile |
| 6 | Show-don't-tell | 10% | Emotions shown through action/sensation, not stated |
| 7 | Chapter-end hook | 10% | Last 300 words create pull |
| 8 | Foreshadowing integrity | 10% | Claimed foreshadowing items present in text |
| 9 | Paragraph rhythm | 5% | Varied paragraph lengths |
| 10 | PRE_WRITE_CHECK | 5% | Check completed before drafting |

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
| Non-prose bespoke (dims 3,4,5,8,10) | Yes | Yes | Yes |
| Prose/narrative quality (dims 6,7,9) | No | No | Yes |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered -> final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
