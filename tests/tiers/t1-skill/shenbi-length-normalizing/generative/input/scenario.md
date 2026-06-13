# Generative Test: shenbi-length-normalizing

## Skill Under Test
`skills/shenbi-length-normalizing/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `tests/fixtures/chapter-draft-example.md`.

## Agent Task
Run shenbi-length-normalizing on the chapter. The agent must:
1. Calculate current word count from the chapter file
2. Determine that the chapter is within the 3000-10000 acceptable range — no normalization needed
3. Output a report confirming the chapter is within range (no compression or expansion applied)
4. If the chapter were below 3000, the agent would expand; if above 10000, compress with dual-floor protection (≥3000 AND ≥25% original)

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md` (verify word count from file)
