# Generative Test: shenbi-style-polishing

## Skill Under Test
`skills/shenbi-style-polishing/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `tests/fixtures/chapter-draft-example.md` that is ready for style polishing. A style profile exists at `tests/fixtures/style-profile-example.md`.

## Agent Task
Run shenbi-style-polishing on the drafted chapter. The agent must:
1. Polish only prose style — sentence rhythm, word choice, description pacing
2. Preserve all content: zero changes to plot, character behavior, or emotional tone
3. Keep word count within +-15% of original
4. Avoid introducing any AI-typical phrasing
5. Respect the style_profile.md if it exists
6. Exercise restraint — do not over-polish or rewrite
7. Produce a polishing report listing all changes with before/after pairs
8. Use [polisher-note] annotations that are specific and actionable

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`, style profile from `tests/fixtures/style-profile-example.md`
