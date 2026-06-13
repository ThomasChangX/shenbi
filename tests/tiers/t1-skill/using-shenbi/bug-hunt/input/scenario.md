# Bug-Hunt Test: using-shenbi

## Skill Under Test
`skills/using-shenbi/SKILL.md`

## Test Setup
No novel project needed. Agent is fresh.

## Scenario
Present 10 natural language requests from the existing trigger test prompts in `tests/fixtures/skill-triggering-prompts/`. Three of them are deliberately ambiguous — the request could match two skills, and the wrong one is more obvious.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| Request 3 | "帮我看看角色" — agent routes to shenbi-character-design instead of shenbi-review-character | error |
| Request 7 | "检查时间线" — agent routes to shenbi-world-rules instead of shenbi-review-continuity | error |
| Request 9 | "润色" — agent skips checking anti-detect and goes straight to polishing | warning |

## Agent Task
Process each request through the using-shenbi skill-check flow.
