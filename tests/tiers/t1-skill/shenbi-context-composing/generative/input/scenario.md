# Generative Test: shenbi-context-composing

## Skill Under Test
`skills/shenbi-context-composing/SKILL.md`

## Test Setup
A novel project exists with all truth files populated and 9 chapters already drafted. The project is ready to compose context for chapter 10. Truth files include `plans/chapter-10-plan.md`, `truth/chapter_summaries.md`, `truth/pending_hooks.md` with 8 active hooks, `truth/audit_drift.md`, `world/rules.md`, `truth/character_matrix.md`, `style/style_profile.md`, and `chapters/chapter-7.md` through `chapters/chapter-9.md`.

## Agent Task
Run shenbi-context-composing to compose context for chapter 10. All P1 items must be present without trimming; higher-priority items must never be trimmed before lower. Extracted summaries must match source truth files for key facts. Hook urgency must be computed as (current_chapter - last_reinforced) / max_distance. Ending diversity must be checked across recent 3 chapters, flagging if same ending pattern repeats. Only summaries from last 3 chapters and hooks with urgency > 0.5 should be included. Hook debt brief must list every active hook with status, silence chapters, and action suggestion.

## Seed Input
Chapter plan from `tests/fixtures/chapter-plan-example.md`, hook state from `tests/fixtures/pending-hooks-example.md`, and chapter summaries from `tests/fixtures/chapter-summaries-example.md`
