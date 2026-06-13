# Bug-Hunt Test: shenbi-review-character

## Skill Under Test
`skills/shenbi-review-character/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 8 at `tests/fixtures/chapter-draft-example.md`. Character truth files are at `tests/fixtures/truth/character_profiles/`. The chapter features 4 characters: protagonist 林墨 (narrator, appears throughout), 苏晴 (3 dialogue lines), 老陈 (2 dialogue lines), and a shopkeeper (1 dialogue line).

## Scenario
The agent runs a character audit on chapter 8. The audit report at `tests/fixtures/audit-report-example.md` includes BDI assessments for:
- 林墨 (protagonist) — fully assessed
- 苏晴 — fully assessed
- 老陈 — fully assessed

The shopkeeper character (小贩) has 3 dialogue lines in the chapter but is completely absent from the audit report. No BDI assessment, no mention at all.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/audit-report-example.md` | Speaking character 小贩 (3 dialogue lines) not assessed — missing from BDI coverage entirely | error |

## Agent Task
Run shenbi-review-character audit on chapter 8. Find the planted defect where a speaking character is missing from the BDI assessment.
