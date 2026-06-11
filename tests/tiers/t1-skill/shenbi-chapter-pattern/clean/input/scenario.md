# Clean Test: shenbi-chapter-pattern

## Skill Under Test
`skills/shenbi-chapter-pattern/SKILL.md`

## Test Setup
A novel project has 15 completed chapters. The chapter pattern analysis at `analysis/chapter-patterns.md` is fully correct:
- Each chapter assigned to ≥1 of 13 defined patterns
- No consecutive pattern exceeds the 3-chapter limit (max consecutive run is 2)
- Shannon entropy correctly calculated
- Next-chapter recommendation names specific primary/secondary patterns and patterns to avoid
- Minimum distinct patterns in rolling window verified (meets threshold)
- Pattern assignments: Ch1: revelation, Ch2: dialogue-heavy, Ch3: action, Ch4: romance, Ch5: action, Ch6: mystery, Ch7: dialogue-heavy, Ch8: revelation, Ch9: action, Ch10: romance, Ch11: mystery, Ch12: action, Ch13: dialogue-heavy, Ch14: revelation, Ch15: action

## Scenario
All pattern analysis output is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-chapter-pattern quality check on the pattern analysis output. Expected result: report zero issues.
