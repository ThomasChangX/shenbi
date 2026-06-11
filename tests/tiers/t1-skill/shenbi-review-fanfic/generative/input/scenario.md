# Generative Test: shenbi-review-fanfic

## Skill Under Test
`skills/shenbi-review-fanfic/SKILL.md`

## Test Setup
A fanfic novel project exists with `novel.json` declaring the fanfic mode. Drafted chapter 20 at `drafts/chapter-20.md`. Source material references at `truth/source_material/`.

## Agent Task
Run shenbi-review-fanfic audit on chapter 20. Produce a complete fanfic audit report including:
1. Fanfic mode identification from novel.json
2. Character behavior consistency check against source material
3. Severity classification per SKILL.md severity table for the declared mode
4. Undeclared deviation detection

## Seed Input
Drafted chapter from `drafts/chapter-20.md`, fanfic mode from `novel.json`, source material from `truth/source_material/`
