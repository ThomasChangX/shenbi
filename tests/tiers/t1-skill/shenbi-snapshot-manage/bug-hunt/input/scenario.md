# Bug-Hunt Test: shenbi-snapshot-manage

## Skill Under Test
`skills/shenbi-snapshot-manage/SKILL.md`

## Test Setup
A novel project has 11 truth files in the `truth/` directory:
1. `truth/character_profiles/` (directory with individual character files)
2. `truth/world_rules.md`
3. `truth/location_registry.md`
4. `truth/ability_registry.md`
5. `truth/item_tracker.md`
6. `truth/faction_records.md`
7. `truth/relationship_map.md`
8. `truth/foreshadowing_pool.md`
9. `truth/chapter_summaries.md`
10. `truth/plot_threads.md`
11. `truth/timeline.md`

The agent creates a snapshot before starting work on chapter 25.

## Scenario
The snapshot at `snapshots/pre-chapter-25/` contains only 8 of the 11 truth files. The following three files are missing from the snapshot:
- `truth/ability_registry.md`
- `truth/faction_records.md`
- `truth/timeline.md`

All 8 included files have correct content and non-zero size. The snapshot metadata claims "11 files archived" but the actual file count is 8.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `snapshots/pre-chapter-25/`: directory contents | Snapshot completeness violation — only 8 of 11 truth files archived; missing `ability_registry.md`, `faction_records.md`, and `timeline.md` | error |
| `snapshots/pre-chapter-25/metadata.json`: file_count field | Metadata inconsistency — claims "11 files archived" but actual count is 8 | error |

## Agent Task
Run shenbi-snapshot-manage quality check on the snapshot. The agent must detect that 3 truth files are missing from the snapshot and that the metadata file count does not match the actual contents.
