# Generative Test: shenbi-review-character

## Skill Under Test
`skills/shenbi-review-character/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 10 at `drafts/chapter-10.md`. Character truth files are at `truth/character_profiles/`. The project has chapter summaries at `truth/chapter_summaries.md`.

## Agent Task
Run shenbi-review-character audit on chapter 10. Produce a complete character audit report including:
1. BDI coverage for all speaking/acting characters
2. Character behavior consistency check against profiles
3. Dialogue-authenticity assessment per speaker

## Seed Input
Drafted chapter from `drafts/chapter-10.md`, character profiles from `truth/character_profiles/`, chapter summaries from `truth/chapter_summaries.md`
