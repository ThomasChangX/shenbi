# Bug-Hunt Test: shenbi-truth-sync

## Skill Under Test
`skills/shenbi-truth-sync/SKILL.md`

## Test Setup
A novel project has chapters 1-18 completed. The truth sync scope is set to chapters 15-18. The truth file at `tests/fixtures/character-profile-example.md` records the arc state fields:
- arc_starting: "一个只想利用金手指搞钱、躺平享乐的现代利己主义青年"
- 成长弧线详解 Act 1-3 with key turning points

Chapter text at `tests/fixtures/chapter-draft-example.md` L194-206 shows the arc advancing in-chapter: the perception strengthens ("手掌上的酥麻感又强了一点") and the chapter closes on a cognitive shift.

The truth-sync output at `tests/fixtures/truth-current_state-xinghuo.md` correctly updates the 系统演化阶段 and 参数当前位置 tables but has no character-arc dimension at all. The arc-state change signaled in the synced chapters is neither applied nor flagged as a conflict.

## Scenario
The truth-sync output misses a dimension conflict between chapter text and the character profile truth file. The protagonist's arc has advanced within the synced chapters (perception strengthening, chapter-end cognitive shift), but the sync output contains no character-arc update and does not flag the divergence from the profile's arc fields.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/truth-current_state-xinghuo.md` vs `tests/fixtures/character-profile-example.md` | Missed conflict — sync output's 当前状态 tables carry no character-arc update, so the arc advancement recorded in chapter text is never reconciled with the profile's arc_starting field (躺平享乐 stance vs chapter-end cognitive shift) | error |

## Agent Task
Run shenbi-truth-sync quality check on the sync output. The agent must detect that the character-arc dimension was left out of the sync and the conflict between chapter text and the truth file was not flagged.
