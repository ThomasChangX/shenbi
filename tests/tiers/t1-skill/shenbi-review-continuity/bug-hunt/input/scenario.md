# Bug-Hunt Test: shenbi-review-continuity

## Skill Under Test
`skills/shenbi-review-continuity/SKILL.md`

## Test Setup
A novel project exists with the drafted first chapter at `tests/fixtures/chapter-draft-example.md`. Chapter summaries at `tests/fixtures/chapter-summaries-example.md` record the timeline.
The summaries' 时间推进 entry states the chapter spans "时间跨度: 约半天" from a modern-China dusk to a Medran dusk with purple skylight.

## Scenario
The agent runs a continuity audit across the draft and the summaries. The audit report at `tests/fixtures/audit-report-example.md` notes in its 弧线评估 that "林烽从意识到穿越到接受事实的过渡仅约 3 段" and dismisses the pace as a genre convention — but it never cross-checks the summaries' timeline claim against the draft. The draft's modern-side opening is a daytime scene (七月的热风 blowing through the window, a delivery flyer on the table) before 天快黑了, so the modern side alone already spans afternoon-to-dusk; the 约半天 total and the dusk-to-dusk framing do not reconcile with the draft's own opening. The discrepancy is not caught.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/audit-report-example.md`: 弧线评估 section | Timeline cross-check skipped — the report cites "林烽从意识到穿越到接受事实的过渡仅约 3 段" as its only pacing evidence and never reconciles the summaries' 约半天 (dusk-to-dusk) time span against the draft's daytime modern-side opening | error |

## Agent Task
Run shenbi-review-continuity audit on the chapter and its summaries. Find the planted timeline discrepancy where the recorded time span is not reconciled against the draft's actual opening.
