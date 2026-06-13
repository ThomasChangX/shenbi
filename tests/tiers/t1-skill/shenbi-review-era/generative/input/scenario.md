# Generative Test: shenbi-review-era

## Skill Under Test
`skills/shenbi-review-era/SKILL.md`

## Test Setup
A novel project exists with `tests/fixtures/novel-example.json` declaring a specific time period. Drafted chapter 19 at `tests/fixtures/chapter-draft-example.md`.

## Agent Task
Run shenbi-review-era audit on chapter 19. Produce a complete era audit report including:
1. Time period declaration verification from novel.json
2. Artifact/vocabulary/institution verification against time period
3. Anachronism detection
4. Historical accuracy assessment

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`, time period from `tests/fixtures/novel-example.json`
