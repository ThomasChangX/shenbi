# T1 Rubric: shenbi-foreshadowing-recall

## Universal Dimensions (15%)
| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed |
| 2 | Output completeness | 5% | All required output sections produced |

## Bespoke Dimensions (85%)
| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | Core functionality | 50% | Skill produces correct output for its stated purpose |
| 4 | Data contract compliance | 20% | Reads/writes/updates match frontmatter |
| 5 | Error handling | 15% | Handles missing files, invalid input gracefully |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL

## MVP Scope Note
This skill implements the deterministic full-scan filter.
The vector index is deferred to post-node-1.
