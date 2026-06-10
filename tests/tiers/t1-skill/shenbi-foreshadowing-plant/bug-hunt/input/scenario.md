# Bug-Hunt Test: shenbi-foreshadowing-plant

## Skill Under Test
`skills/shenbi-foreshadowing-plant/SKILL.md`

## Test Setup
A novel project exists with foreshadowing planting output for chapter 5. The planting summary in `truth/pending_hooks.md` lists 12 new foreshadowing operations planted in chapter 5: 7 plant operations, 3 reinforce operations, and 2 trigger operations. The skill's hard limit is 8 operations per chapter.

## Scenario
The foreshadowing planting for chapter 5 has been completed. The planting summary shows 12 foreshadowing operations in a single chapter: hook-101 through hook-107 (plant), hook-012, hook-015, hook-018 (reinforce), and hook-003, hook-007 (trigger). This totals 12 operations, which exceeds the budget of 8 per chapter defined in the skill's iron rules.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `truth/pending_hooks.md`: chapter 5 planting section | 12 foreshadowing operations in chapter 5, exceeding the ≤8 operations per chapter budget (7 plant + 3 reinforce + 2 trigger = 12) | error |

## Agent Task
Run shenbi-foreshadowing-plant quality check on the chapter 5 planting output. The agent must detect that the operation count exceeds the 8-per-chapter budget.
