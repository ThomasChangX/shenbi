# Bug-Hunt Test: shenbi-snapshot-manage

## Skill Under Test
`skills/shenbi-snapshot-manage/SKILL.md`

## Test Setup
A novel project has 11 truth files in the `truth/` directory (matching the canonical list in SKILL.md):
1. `truth/current_state.md`
2. `truth/pending_hooks.md`
3. `truth/chapter_summaries.md`
4. `truth/character_matrix.md`
5. `truth/emotional_arcs.md`
6. `truth/particle_ledger.md`
7. `truth/subplot_board.md`
8. `truth/author_intent.md`
9. `truth/current_focus.md`
10. `truth/audit_drift.md`
11. `truth/volume_summaries.md`

The agent creates a snapshot after completing chapter 25.

## Scenario
The snapshot at `snapshots/chapter-025/` contains only 8 of the 11 truth files. The following three files are missing from the snapshot:
- `truth/particle_ledger.md`
- `truth/subplot_board.md`
- `truth/author_intent.md`

All 8 included files have correct content and non-zero size. The snapshot manifest claims "11 files archived" but the actual file count is 8.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `snapshots/chapter-025/`: directory contents | Snapshot completeness violation — only 8 of 11 truth files archived; missing `particle_ledger.md`, `subplot_board.md`, and `author_intent.md` | error |
| `snapshots/chapter-025/manifest.md`: files field | Manifest inconsistency — claims 11 files but actual count is 8 | error |

## Agent Task
Run shenbi-snapshot-manage quality check on the snapshot. The agent must detect that 3 truth files are missing from the snapshot and that the manifest file list does not match the actual contents. The agent must cross-reference against the canonical 11-file list defined in SKILL.md.
