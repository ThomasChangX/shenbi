# Generative Test: shenbi-foreshadowing-track

## Skill Under Test
`skills/shenbi-foreshadowing-track/SKILL.md`

## Test Setup
A novel project exists with a freshly drafted chapter 10 at `chapters/chapter-10.md`. Truth files include `truth/pending_hooks.md` with 8 active hooks at various lifecycle stages and `truth/chapter_summaries.md` with recent summaries.

## Agent Task
Run shenbi-foreshadowing-track to track all active hooks through chapter 10. Every active hook must be assessed — none skipped. All state transitions must include specific textual evidence from the chapter. Core hooks (core_hook: true) must never be ABANDONED. Hooks exceeding max_distance must be flagged as EXPIRED. Density budget must be clearly reported with operation counts and any over-budget items explicitly listed.

## Seed Input
Chapter 10 content from `tests/fixtures/chapter-draft-example.md` and existing hooks from `tests/fixtures/pending-hooks-example.md`
