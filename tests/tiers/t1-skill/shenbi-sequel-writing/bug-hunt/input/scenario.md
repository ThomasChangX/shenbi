# Bug-Hunt Test: shenbi-sequel-writing

## Skill Under Test
`skills/shenbi-sequel-writing/SKILL.md`

## Test Setup
A novel project with 30 published chapters was paused after chapter 30. A breakpoint snapshot exists at `tests/fixtures/snapshots/chapter-030/`. The sequel-writing skill has been resumed to continue from chapter 31.

## Scenario
The sequel writing has been started. However, a critical historical immutability violation has occurred:

1. **Modified published chapter**: The checksum of `tests/fixtures/chapter-draft-example.md` in the current filesystem (SHA-256: a1b2c3d4...) differs from the snapshot checksum recorded in `tests/fixtures/chapter-plan-example.md` (SHA-256: e5f6a7b8...). Comparison reveals that a paragraph in chapter 25 was rewritten — the original described the protagonist as "hesitant and uncertain" but the current version reads "confident and determined." Published chapters must never be modified.

2. **Missing drift detection**: The pre-writing report at `tests/fixtures/report-example.txt` includes context reconstruction and human intent confirmation but has no drift detection section. Behavioral drift, voice drift, style drift, and setting drift checks are all missing.

3. **Human intent not confirmed**: The sequel writing log shows writing started at T+30min but the human intent re-confirmation timestamp is T+120min — the intent was confirmed after writing had already begun, not before.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md` vs `tests/fixtures/chapter-plan-example.md` | Historical immutability violation — chapter 25 checksum differs from snapshot; paragraph rewritten from "hesitant and uncertain" to "confident and determined" | error |
| `tests/fixtures/report-example.txt` | Drift detection missing — no behavioral, voice, style, or setting drift checks in pre-writing report | error |
| Writing log vs intent confirmation timestamp | Human intent confirmation violation — writing started at T+30min but intent confirmed at T+120min; confirmation must precede writing | error |

## Agent Task
Run shenbi-sequel-writing quality check on the resumed writing process. The agent must detect the modified published chapter, the missing drift detection, and the late human intent confirmation.
