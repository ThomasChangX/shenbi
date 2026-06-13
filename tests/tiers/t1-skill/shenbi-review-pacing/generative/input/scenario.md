# Generative Test: shenbi-review-pacing

## Skill Under Test
`skills/shenbi-review-pacing/SKILL.md`

## Test Setup
A novel project exists with 10 drafted chapters. Rhythm principles defined at `tests/fixtures/style-profile-example.md`.

## Agent Task
Run shenbi-review-pacing audit on the last 5 chapters (chapters 6-10). Produce a complete pacing audit report including:
1. Chapter type classification (QUEST/FIRE/CONSTELLATION) for each chapter
2. Rhythm balance assessment
3. Pacing consistency check
4. Tension curve analysis

## Seed Input
Drafted chapters from `tests/fixtures/chapter-draft-example.md` (representing the full chapter range), rhythm principles from `tests/fixtures/style-profile-example.md`
