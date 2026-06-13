# Bug-Hunt Test: shenbi-snapshot-manage

## Skill Under Test
`skills/shenbi-snapshot-manage/SKILL.md`

## Test Setup
A novel project has 11 truth files in the `tests/fixtures/truth/` directory (matching the canonical list in SKILL.md):
1. `tests/fixtures/chapter-summaries-example.md`
2. `tests/fixtures/pending-hooks-example.md`
3. `tests/fixtures/chapter-summaries-example.md`
4. `tests/fixtures/character-profile-example.md`
5. `tests/fixtures/pending-hooks-example.md`
6. `tests/fixtures/pending-hooks-example.md`
7. `tests/fixtures/chapter-plan-example.md`
8. `tests/fixtures/author-intent-example.md`
9. `tests/fixtures/author-intent-example.md`
10. `tests/fixtures/report-example.txt`
11. `tests/fixtures/chapter-summaries-example.md`

The agent creates a snapshot after completing chapter 25.

## Scenario
The snapshot at `tests/fixtures/snapshots/chapter-025/` contains only 8 of the 11 truth files. The following three files are missing from the snapshot:
- `tests/fixtures/pending-hooks-example.md`
- `tests/fixtures/chapter-plan-example.md`
- `tests/fixtures/author-intent-example.md`

All 8 included files have correct content and non-zero size. The snapshot manifest claims "11 files archived" but the actual file count is 8.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/snapshots/chapter-025/`: directory contents | Snapshot completeness violation — only 8 of 11 truth files archived; missing `tests/fixtures/pending-hooks-example.md`, `tests/fixtures/chapter-plan-example.md`, and `tests/fixtures/author-intent-example.md` | error |
| `tests/fixtures/chapter-plan-example.md`: files field | Manifest inconsistency — claims 11 files but actual count is 8 | error |

## Agent Task
Run shenbi-snapshot-manage quality check on the snapshot. The agent must detect that 3 truth files are missing from the snapshot and that the manifest file list does not match the actual contents. The agent must cross-reference against the canonical 11-file list defined in SKILL.md.
