# Generative Test: shenbi-review-long-span

## Skill Under Test
`skills/shenbi-review-long-span/SKILL.md`

## Test Setup
A novel project exists with 12 drafted chapters at `drafts/`. The audit covers the last 5 chapters (chapters 8-12).

## Agent Task
Run shenbi-review-long-span audit on the last 5 chapters. Produce a complete long-span audit report including:
1. 6-char n-gram extraction with repetition counts
2. Repetition rate computation per SKILL.md formula
3. Threshold cross-check
4. Repetitive pattern identification with location citations

## Seed Input
Drafted chapters from `drafts/chapter-8.md` through `drafts/chapter-12.md`
