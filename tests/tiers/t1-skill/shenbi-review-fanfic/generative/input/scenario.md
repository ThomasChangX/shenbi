# Generative Test: shenbi-review-fanfic

## Skill Under Test
`skills/shenbi-review-fanfic/SKILL.md`

## Test Setup
A fanfic novel project exists with `tests/fixtures/novel-example.json` declaring the fanfic mode. Drafted chapter 20 at `tests/fixtures/chapter-draft-example.md`. Source material references at `tests/fixtures/truth/source_material/`.

## Agent Task
Run shenbi-review-fanfic audit on chapter 20. Produce a complete fanfic audit report including:
1. Fanfic mode identification from novel.json
2. Character behavior consistency check against source material
3. Severity classification per SKILL.md severity table for the declared mode
4. Undeclared deviation detection

## Seed Input
Drafted chapter from `tests/fixtures/chapter-draft-example.md`, fanfic mode from `tests/fixtures/novel-example.json`, source material from `tests/fixtures/truth/source_material/`
