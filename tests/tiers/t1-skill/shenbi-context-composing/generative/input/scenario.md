# Generative Test: shenbi-context-composing

## Skill Under Test
`skills/shenbi-context-composing/SKILL.md`

## Test Setup
A novel project exists with truth files populated and chapters 7-9 drafted. The project is ready to compose context for chapter 10. Available fixtures include `tests/fixtures/chapter-plan-example.md` (chapter plan), `tests/fixtures/chapter-summaries-example.md` (chapter summaries), `tests/fixtures/pending-hooks-example.md` (active hooks state), `tests/fixtures/chapter-draft-example.md` (chapter 1 draft), `tests/fixtures/chapter-7-example.md` through `tests/fixtures/chapter-9-example.md` (recent chapter drafts for ending diversity check), `tests/fixtures/character-profile-example.md` (character profiles), `tests/fixtures/style-profile-example.md` (style profile), and `tests/fixtures/outline-example.md` (volume structure).

## Agent Task
Run shenbi-context-composing to compose context for chapter 10. All P1 items must be present without trimming; higher-priority items must never be trimmed before lower. Extracted summaries must match source truth files for key facts. Hook urgency must be computed as (current_chapter - last_reinforced) / max_distance. Ending diversity must be checked across recent 3 chapters, flagging if same ending pattern repeats. Only summaries from last 2 chapters (per P2 rule) and hooks sorted by urgency (max 3, per P3 rule) should be included. Hook debt brief must list every active hook with status, silence chapters, and action suggestion.

## Seed Input
Chapter plan from `tests/fixtures/chapter-plan-example.md`, hook state from `tests/fixtures/pending-hooks-example.md`, and chapter summaries from `tests/fixtures/chapter-summaries-example.md`
