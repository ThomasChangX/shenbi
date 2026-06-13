# Clean Test: shenbi-volume-outlining

## Skill Under Test
`skills/shenbi-volume-outlining/SKILL.md`

## Test Setup
A novel project exists with complete, correct volume outline output:
- `tests/fixtures/outline-example.md` — KRs map to specific chapter ranges, proper tension wave, ends with ≥1 tangible hook to Volume 2
- `tests/fixtures/outline-example.md` — KRs map to specific chapter ranges, proper tension wave, ends with ≥1 tangible hook to Volume 3
- `tests/fixtures/outline-example.md` — KRs map to specific chapter ranges, proper tension wave, appropriate ending

All volumes have OKRs with measurable KRs and chapter ranges. Each volume has a wave pattern (buildup/rising/explosion/aftermath). All volume endings (except the final) leave tangible hooks. Early chapters accommodate world-building needs. Surface/personal/deep conflicts are explicitly advanced.

## Scenario
All volume outline content is correct and follows all skill rules. No missing hooks, no vague KRs, no flat tension curves.

## Agent Task
Run shenbi-volume-outlining quality check on the existing output. Expected result: report zero issues.
