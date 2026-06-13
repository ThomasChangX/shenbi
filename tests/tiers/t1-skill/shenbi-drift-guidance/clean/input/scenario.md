# Clean Test: shenbi-drift-guidance

## Skill Under Test
`skills/shenbi-drift-guidance/SKILL.md`

## Test Setup
A novel project has completed chapter 14 and multiple audits have been run. The audit reports contain:
- `tests/fixtures/audit-report-example.md`: Finding CC-F001 (error) — timeline error (must be fixed, not forwarded)
- `tests/fixtures/audit-report-example.md`: Finding CC-F002 (warning) — market scene lacks sensory detail
- `tests/fixtures/audit-report-example.md`: Finding CH-F001 (warning) — dialogue voice inconsistency
- `tests/fixtures/audit-report-example.md`: Finding PC-F001 (warning) — pacing slows in middle section

The drift guidance output at `tests/fixtures/report-example.txt` is fully correct:
- Error finding CC-F001 correctly excluded (not forwarded)
- Warning findings CC-F002, CH-F001, PC-F001 correctly included (3 items, within ≤5 cap)
- Each item has specific actionable guidance ("what next chapter should do")
- Every item has a targeted_chapter field with chapter number
- Each item traceable to specific audit finding (audit name + finding ID)

## Scenario
All drift guidance output is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-drift-guidance quality check on the drift guidance output. Expected result: report zero issues.
