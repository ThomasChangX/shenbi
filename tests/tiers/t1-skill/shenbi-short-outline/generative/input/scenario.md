# Generative Test: shenbi-short-outline

## Skill Under Test
`skills/shenbi-short-outline/SKILL.md`

## Test Setup
A short novel project (15 chapters) has `tests/fixtures/novel-example.json` and `tests/fixtures/author-intent-example.md` configured. No outline has been generated yet.

## Agent Task
Run shenbi-short-outline for the project. The agent must:
1. Execute all 3 steps: generate -> review -> revise (no skipped steps)
2. Ensure every chapter has >=1 task advancing >=1 thread
3. Achieve 20/60/20 act proportioning by chapter count
4. Produce zero dead chapters (no "transition" tasks)
5. Maintain <=1 subplot + <=1 emotional arc
6. Create genuine reversal turning points

## Seed Input
Project config at `tests/fixtures/novel-example.json` with `tests/fixtures/author-intent-example.md` (15-chapter short novel)
