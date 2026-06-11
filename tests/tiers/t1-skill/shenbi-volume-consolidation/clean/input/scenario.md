# Clean Test: shenbi-volume-consolidation

## Skill Under Test
`skills/shenbi-volume-consolidation/SKILL.md`

## Test Setup
A novel project has completed Volume 1 (chapters 1-10). The consolidation report at `consolidation/volume-1/report.md` is fully correct:
- Volume summary is 420 words (within 500-word limit)
- All active hooks listed: H001, H002, H003, H005 (H004 correctly excluded as RESOLVED)
- Per-chapter summaries archived at expected paths
- Every major event in volume summary traceable to specific chapter
- Only key events affecting character arcs, plot threads, or world state included

## Scenario
All consolidation output is correct and follows all skill rules. No defects present.

## Agent Task
Run shenbi-volume-consolidation quality check on the consolidation report. Expected result: report zero issues.
