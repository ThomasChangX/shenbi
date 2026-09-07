# Bug-Hunt Test: shenbi-review-sensitivity

## Skill Under Test
`skills/shenbi-review-sensitivity/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 6 at `tests/fixtures/chapter-draft-example.md`.
The project's `tests/fixtures/novel-example.json` records status "worldbuilding".
The platform fatigue list at `tests/fixtures/sensitive_words.txt` contains prohibited words including "台独" and "法轮功". Chapter 6 contains extensive dialogue and narration to be scanned.

## Scenario
The agent runs a sensitivity audit on chapter 6. The audit report at `tests/fixtures/audit-report-example.md` contains no platform sensitivity check at all — its compliance table covers style rules (转折词/AI标记词/了字密度) only. If any word from the platform fatigue list occurred in the chapter text, the audit would miss it entirely.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md` vs `tests/fixtures/sensitive_words.txt` | Sensitivity coverage gap — audit report runs no fatigue-list scan against the platform list (which includes "法轮功" among prohibited words), so any occurrence in the chapter would go unflagged | error |

## Agent Task
Run shenbi-review-sensitivity audit on chapter 6. Find the planted defect where the platform fatigue list is never applied to the chapter text.
