# Generative Test: shenbi-snapshot-manage

## Skill Under Test
`skills/shenbi-snapshot-manage/SKILL.md`

## Test Setup
A novel project has 11 truth files in the `truth/` directory and 20 completed chapters. The project is about to begin a major revision arc starting at chapter 18. A snapshot is needed to preserve the current state.

## Agent Task
Run shenbi-snapshot-manage to create a snapshot before the revision arc. The agent must:
1. Create a snapshot including all 11 truth files
2. Generate checksums for each file
3. Record correct metadata (timestamp, file count, chapter range)
4. Ensure the snapshot is immutable after creation
5. Support view and list operations on the created snapshot

## Seed Input
Truth files from `truth/`, existing chapter drafts from `drafts/`
