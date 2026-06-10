# Bug-Hunt Test: shenbi-chapter-pattern

## Skill Under Test
`skills/shenbi-chapter-pattern/SKILL.md`

## Test Setup
A novel project has 15 completed chapters. The chapter pattern analysis at `analysis/chapter-patterns.md` classifies each chapter into one or more of the 13 defined patterns. The consecutive pattern threshold rule states that no more than 3 chapters of the same primary pattern may appear consecutively.

The pattern assignments for chapters 1-15 are:
- Ch 1: revelation | Ch 2: dialogue-heavy | Ch 3: action | Ch 4: action | Ch 5: action | Ch 6: action | Ch 7: action | Ch 8: dialogue-heavy | Ch 9: revelation | Ch 10: action | Ch 11: action | Ch 12: action | Ch 13: action | Ch 14: action | Ch 15: dialogue-heavy

This means chapters 3-7 have 5 consecutive chapters with primary pattern "action", and chapters 10-14 have another 5 consecutive "action" chapters.

## Scenario
The chapter pattern analysis output does not flag any threshold violation for the consecutive "action" pattern runs. Both runs (chapters 3-7 and chapters 10-14) exceed the 3-chapter consecutive limit but the analysis reports the pattern distribution as healthy with no warnings.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `analysis/chapter-patterns.md`: threshold analysis section | Threshold strictness violation — chapters 3-7 are 5 consecutive "action" primary pattern chapters, exceeding the 3-chapter consecutive limit; this threshold violation is not flagged | error |
| `analysis/chapter-patterns.md`: threshold analysis section | Threshold strictness violation — chapters 10-14 are 5 consecutive "action" primary pattern chapters, exceeding the 3-chapter consecutive limit; this threshold violation is not flagged | error |

## Agent Task
Run shenbi-chapter-pattern quality check on the pattern analysis output. The agent must detect that two runs of 5 consecutive "action" chapters were not flagged as threshold violations.
