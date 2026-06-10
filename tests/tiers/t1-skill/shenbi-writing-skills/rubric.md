# T1 Rubric: shenbi-writing-skills

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Skill completeness | 20% | Every created skill has DOT flowchart, iron laws, anti-rationalization table, red flag checklist |
| 4 | Trigger-only descriptions | 15% | Description describes when to use, never what it does |
| 5 | Iron law absoluteness | 15% | Rules use MUST/NEVER/ALWAYS; "should"/"prefer"/"recommend" = fail |
| 6 | Pressure-test rigor | 15% | Skills tested against >=3 real rationalization scenarios |
| 7 | Persuasion ethics | 10% | Uses Authority/Commitment/Scarcity/Social Proof/Unity only; Liking/Reciprocity absent |
| 8 | Output format | 10% | SKILL.md follows frontmatter + markdown structure from CLAUDE.md conventions |

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
