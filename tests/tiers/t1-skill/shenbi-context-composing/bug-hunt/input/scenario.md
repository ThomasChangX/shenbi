# Bug-Hunt Test: shenbi-context-composing

## Test Setup
`skills/shenbi-context-composing/SKILL.md`

## Test Setup
A novel project exists with context assembly output for chapter 10. The assembled context in the output shows that P1 (chapter plan memo from `tests/fixtures/chapter-plan-example.md`) has been partially trimmed — the "章尾必须发生的改变" section of the plan memo is missing from the assembled context. Meanwhile, P2 (recent chapter summaries) includes full content from chapters 7, 8, and 9, and P5 (world rules) includes all 5 allowed rules. A higher-priority item was trimmed while lower-priority items were included in full.

## Scenario
The context assembly for chapter 10 has been generated. Upon review, the P1 priority item (chapter plan memo) has been partially trimmed — its "章尾必须发生的改变" section is absent from the assembled context. However, P2 (recent summaries) and P5 (world rules) are included in full without any trimming. This violates the iron rule that priority levels are strictly decreasing — P1 must never be trimmed before P2 or P5.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| Assembled context output: P1 section | P1 item (chapter plan memo) trimmed — "章尾必须发生的改变" section missing — while lower-priority P2 and P5 items are included in full | error |

## Agent Task
Run shenbi-context-composing quality check on the chapter 10 context assembly. The agent must detect that a P1 item was trimmed while lower-priority items were included.
