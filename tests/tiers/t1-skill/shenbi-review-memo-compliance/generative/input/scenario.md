# Generative Test: shenbi-review-memo-compliance

## Skill Under Test
`skills/shenbi-review-memo-compliance/SKILL.md`

## Test Setup
A novel project exists with chapter memo at `plans/chapter-10-plan.md` and drafted chapter 10 at `drafts/chapter-10.md`.

## Agent Task
Run shenbi-review-memo-compliance audit on chapter 10. Produce a complete memo-compliance audit report including:
1. Section-by-section verification of all 8 memo sections
2. Per-section fulfill/partial/missing verdict
3. Item-level checklist within each section
4. Missing items clearly identified

## Seed Input
Chapter memo from `plans/chapter-10-plan.md`, drafted chapter from `drafts/chapter-10.md`
