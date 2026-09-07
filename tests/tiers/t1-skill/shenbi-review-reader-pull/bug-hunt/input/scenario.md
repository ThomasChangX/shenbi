# Bug-Hunt Test: shenbi-review-reader-pull

## Skill Under Test
`skills/shenbi-review-reader-pull/SKILL.md`

## Test Setup
A novel project exists with the drafted first chapter at `tests/fixtures/chapter-draft-example.md`. The chapter opens with a flat scrolling beat — the protagonist stares at his phone and 拇指往上一划 — no story question, no tension. The chapter-end suspense is properly classified.

## Scenario
The agent runs a reader-pull audit on the chapter. The audit report at `tests/fixtures/audit-report-example.md` includes:
- Chapter-end curiosity check: covered (the PRE_WRITE_CHECK table records the 章尾好奇心点燃 rule)
- Mid-chapter checks: 对白/声音 sections covered
- Opening hook type: **SKIPPED** — the report has no opening-hook assessment at all. The PRE_WRITE_CHECK table checks the chapter ending but contains no row classifying the opening's hook type.

The opening has no hook type classified; the hook assessment was simply skipped.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/audit-report-example.md`: PRE_WRITE_CHECK 合规 table | Opening hook assessment skipped — the table audits "章尾好奇心点燃" but has no row classifying an opening hook type for the chapter opening, a flat phone-scrolling beat with no hook value | error |

## Agent Task
Run shenbi-review-reader-pull audit on the chapter. Find the planted defect where the opening hook assessment is skipped.
