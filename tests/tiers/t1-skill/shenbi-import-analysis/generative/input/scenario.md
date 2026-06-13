# Generative Test: shenbi-import-analysis

## Skill Under Test
`skills/shenbi-import-analysis/SKILL.md`

## Test Setup
A novel manuscript exists at `tests/fixtures/chapters/` with 10 source chapters of a fantasy novel. No prior import analysis has been run.

## Agent Task
Run shenbi-import-analysis on the manuscript. The agent must:
1. Parse all source chapters and compute accurate statistics (word count, paragraph count, chapter count)
2. Execute all 8 passes in the correct serial/parallel dependency order per the DOT flowchart
3. Ensure every extracted fact has a chapter.paragraph reference
4. Mark all non-derivable items as "unconfirmed" — zero fabrication
5. Produce non-empty output files for all 8 passes
6. Ensure no contradictions between pass outputs
7. Generate an exhaustive unconfirmed items list

## Seed Input
Fantasy novel manuscript at `tests/fixtures/chapters/` with 10 chapters
