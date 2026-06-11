# Clean Test: shenbi-anti-detect

## Skill Under Test
`skills/shenbi-anti-detect/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `drafts/chapter-7.md`. An anti-detect pass has been run correctly, producing `drafts/chapter-7-antidetect.md` and an audit report at `reports/chapter-7-antidetect-report.md`.

The anti-detect output is fully correct:
- Only the 4 detected AI marker points were rewritten; all other paragraphs untouched
- Zero content changes: plot, characters, and foreshadowing fully preserved
- Anti-AI audit passes after rewriting (all markers cleared)
- Authorial voice preserved; no new AI-typical patterns introduced
- Iteration bounded (completed in 2 passes, well within 3-pass limit)
- Before/after audit report shows clear per-marker-type breakdown with error/warning counts

## Scenario
All anti-detect output is correct and follows all skill rules. Only targeted rewrites at actual marker points, with full content preservation.

## Agent Task
Run shenbi-anti-detect quality check on the anti-detect output. Expected result: report zero issues.
