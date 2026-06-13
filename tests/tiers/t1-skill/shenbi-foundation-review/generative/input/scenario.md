# Generative Test: shenbi-foundation-review

## Skill Under Test
`skills/shenbi-foundation-review/SKILL.md`

## Test Setup
A novel project has just completed its foundation setup. The following foundation files exist:
- `tests/fixtures/author-intent-example.md` — story premise, genre, themes
- `tests/fixtures/character-profile-example.md` — main character profiles
- `tests/fixtures/outline-example.md` — world-building rules and constraints
- `tests/fixtures/chapter-plan-example.md` — core plot threads defined
- `tests/fixtures/chapter-plan-example.md` — overall story outline

## Agent Task
Run shenbi-foundation-review to evaluate the project foundation. The agent must:
1. Score all 5 dimensions independently (premise clarity, core conflict, character foundations, world consistency, plot coherence)
2. Ensure every deduction has a concrete improvement suggestion (which file, which paragraph, what to change)
3. Enforce the 80-point minimum threshold
4. Enforce the core-conflict veto (core-conflict < 18/30 = unconditional fail)
5. Score only existing content (no assumed content)
6. Make fix suggestions actionable (point to exact files/paragraphs)

## Seed Input
Foundation files from `tests/fixtures/truth/` and `tests/fixtures/chapter-plan-example.md`
