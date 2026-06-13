# Clean Test: shenbi-snapshot-manage

## Skill Under Test
`skills/shenbi-snapshot-manage/SKILL.md`

## Test Setup
A novel project has 11 truth files in the `tests/fixtures/truth/` directory. A snapshot was created at `tests/fixtures/snapshots/pre-chapter-25/` and is fully correct:
- All 11 truth files included with non-zero size
- Post-creation checksum matches for every file
- Metadata correctly reports 11 files archived
- Snapshot format follows spec (create/view/list operations produce correct output)

## Scenario
All snapshot content is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-snapshot-manage quality check on the snapshot. Expected result: report zero issues.
