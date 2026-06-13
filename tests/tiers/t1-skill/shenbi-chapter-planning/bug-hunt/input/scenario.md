# Bug-Hunt Test: shenbi-chapter-planning

## Skill Under Test
`skills/shenbi-chapter-planning/SKILL.md`

## Test Setup
A novel project exists with a chapter memo output at `tests/fixtures/chapter-plan-example.md`. The project is in Volume 2, chapter 7. Truth files are populated with hooks, summaries, and volume outline.

## Scenario
The chapter memo for chapter 7 has been generated. Upon inspection, the memo only contains 5 of the required 8 sections. The missing sections are:
- Section 2: "读者此刻在等什么" (Reader expectation management)
- Section 4: "日常/过渡承担什么任务" (Daily/transition task mapping)
- Section 6: "章尾必须发生的改变" (End-of-chapter change)

The 5 sections that are present (1: 当前任务, 3: 该兑现的/暂不掀的, 5: 关键抉择过三连问, 7: 本章 hook 账, 8: 不要做) appear correct on their own.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-plan-example.md`: full document | Missing 3 of 8 required memo sections — sections 2 (读者此刻在等什么), 4 (日常/过渡承担什么任务), and 6 (章尾必须发生的改变) are entirely absent | error |

## Agent Task
Run shenbi-chapter-planning quality check on the existing chapter memo. The agent must detect that the memo is missing 3 of the 8 required sections.
