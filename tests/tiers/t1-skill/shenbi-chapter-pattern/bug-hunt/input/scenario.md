# Bug-Hunt Test: shenbi-chapter-pattern

## Skill Under Test
`skills/shenbi-chapter-pattern/SKILL.md`

## Test Setup
A novel project has 15 completed chapters. The chapter pattern analysis at `analysis/chapter-patterns.md` classifies each chapter into one or more of the 13 defined patterns. The consecutive pattern threshold rule states that no more than 3 chapters of the same primary pattern may appear consecutively.

The pattern assignments for chapters 1-15 are:
- Ch 1: 揭示 | Ch 2: 沉淀 | Ch 3: 决战 | Ch 4: 决战 | Ch 5: 决战 | Ch 6: 决战 | Ch 7: 决战 | Ch 8: 沉淀 | Ch 9: 揭示 | Ch 10: 决战 | Ch 11: 决战 | Ch 12: 决战 | Ch 13: 决战 | Ch 14: 决战 | Ch 15: 沉淀

This means chapters 3-7 have 5 consecutive chapters with primary pattern "决战", and chapters 10-14 have another 5 consecutive "决战" chapters.

## Scenario
The chapter pattern analysis output does not flag any threshold violation for the consecutive "决战" pattern runs. Both runs (chapters 3-7 and chapters 10-14) exceed the 2-chapter maxConsecutive threshold (warning at 3) but the analysis reports the pattern distribution as healthy with no warnings.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `analysis/chapter-patterns.md`: consecutive detection section | Consecutive threshold violation — chapters 3-7 are 5 consecutive "决战" primary pattern chapters, exceeding the 2-chapter maxConsecutive limit; not flagged | error |
| `analysis/chapter-patterns.md`: consecutive detection section | Consecutive threshold violation — chapters 10-14 are 5 consecutive "决战" primary pattern chapters, exceeding the 2-chapter maxConsecutive limit; not flagged | error |
| `analysis/chapter-patterns.md`: distribution section | Distribution violation — 10 of 15 chapters use only 3 patterns (决战, 沉淀, 揭示), covering only 3 of 13 patterns in 15 chapters; below the N=10 threshold of minimum 5 patterns | warning |

## Agent Task
Run shenbi-chapter-pattern quality check on the pattern analysis output. The agent must detect that two runs of 5 consecutive "决战" chapters were not flagged as threshold violations, and that the overall pattern distribution is severely deficient.
