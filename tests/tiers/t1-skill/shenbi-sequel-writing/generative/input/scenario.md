# Generative Test: shenbi-sequel-writing

## Skill Under Test
`skills/shenbi-sequel-writing/SKILL.md`

## Test Setup
A novel project with 25 published chapters was paused after chapter 25. A breakpoint snapshot exists at `snapshots/chapter-025/`. Truth files and chapter summaries are available. No sequel writing has been started yet.

## Agent Task
Run shenbi-sequel-writing to resume the project from chapter 26. The agent must:
1. Locate the breakpoint snapshot and read the manifest
2. Rebuild all 6 context categories from files (state, threads, style, characters, world, summaries)
3. Run drift detection: check behavioral, voice, style, and setting drift
4. Explicitly re-confirm human intent before writing starts
5. Verify all published chapter checksums match snapshot
6. Produce a complete pre-writing report with all sections
7. Continue writing from chapter 26

## Seed Input
Breakpoint snapshot at `snapshots/chapter-025/` with 25 published chapters
