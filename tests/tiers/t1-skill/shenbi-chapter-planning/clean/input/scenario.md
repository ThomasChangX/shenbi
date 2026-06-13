# Clean Test: shenbi-chapter-planning

## Skill Under Test
`skills/shenbi-chapter-planning/SKILL.md`

## Test Setup
A novel project exists with a complete, correct chapter memo output at `tests/fixtures/chapter-plan-example.md`:
- All 8 required memo sections are present and populated
- Section 1 (当前任务): specific action derived from volume KR priority chain
- Section 2 (读者此刻在等什么): explicitly lists reader expectations with create/delay/satisfy strategy
- Section 3 (该兑现的/暂不掀的): foreshadowing兑现清单 and withheld reveals
- Section 4 (日常/过渡承担什么任务): non-conflict segments mapped to functions
- Section 5 (关键抉择过三连问): Why/Interest/Persona all addressed
- Section 6 (章尾必须发生的改变): 2 concrete changes (information gain, relationship shift)
- Section 7 (本章 hook 账): open/advance/resolve/defer operations listed
- Section 8 (不要做): specific avoid-patterns listed (not generic advice)

Goal derivation follows priority chain correctly. Hook accounting tracks all hooks. End-of-chapter change specifies concrete alterations.

## Scenario
All chapter memo content is correct and follows all skill rules. No missing sections, no vague goal derivation, no missing changes.

## Agent Task
Run shenbi-chapter-planning quality check on the existing chapter memo. Expected result: report zero issues.
