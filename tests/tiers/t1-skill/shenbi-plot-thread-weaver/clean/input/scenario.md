# Clean Test: shenbi-plot-thread-weaver

## Skill Under Test
`skills/shenbi-plot-thread-weaver/SKILL.md`

## Test Setup
A novel project exists with complete, correct plot thread output:
- `story/threads.md` — all threads with correct priorities, A-lines within max_gap, C-lines resolved within span
- `story/thread-map.md` — every chapter advances at least one thread, subplot climaxes complement volume climaxes

Every chapter advances at least one thread. A-lines don't exceed max_gap. C-lines resolve within their planned spans. Subplot climaxes complement volume climaxes. Thread crossings serve dramatic effect. Priority classifications are accurate.

## Scenario
All plot thread content is correct and follows all skill rules. No blank chapters, no A-line gaps, no unclosed C-lines.

## Agent Task
Run shenbi-plot-thread-weaver quality check on the existing output. Expected result: report zero issues.
