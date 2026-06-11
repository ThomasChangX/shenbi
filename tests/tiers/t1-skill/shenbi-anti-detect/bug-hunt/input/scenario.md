# Bug-Hunt Test: shenbi-anti-detect

## Skill Under Test
`skills/shenbi-anti-detect/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `drafts/chapter-7.md`. An anti-detect pass has been run on the chapter, producing `drafts/chapter-7-antidetect.md` and an audit report at `reports/chapter-7-antidetect-report.md`.

## Scenario
The anti-detect pass has been completed. The AI marker audit initially found 5 specific marker points in the original draft (3 transition-phrase markers and 2 sentence-structure markers). However, instead of rewriting only at those 5 detected marker points, the anti-detect output at `drafts/chapter-7-antidetect.md` shows a wholesale rewrite of the entire chapter. The rewrites include:

1. **Wholesale rewriting**: The output shows modifications to paragraphs that had no AI markers. At least 8 additional paragraphs were rewritten beyond the 5 identified marker points. The chapter structure, paragraph order, and sentence composition in these areas differ from the original despite no markers being detected there.

2. **Content change as side effect**: Because the rewrite was wholesale rather than targeted, a foreshadowing clue that was subtly planted in the original (a specific detail about a pendant the protagonist notices) was lost in the rewrite. The detail was not at a marker point and should have been left untouched.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `drafts/chapter-7-antidetect.md`: multiple paragraphs without markers | Wholesale rewriting — at least 8 non-marker paragraphs rewritten instead of targeted intervention at only 5 marker points | error |
| `drafts/chapter-7-antidetect.md`: pendant detail scene | Content loss — foreshadowing clue (pendant detail) removed during wholesale rewrite, violating content preservation | error |

## Agent Task
Run shenbi-anti-detect quality check on the anti-detect output. The agent must detect that rewriting was wholesale rather than targeted at specific marker points, and that content (a foreshadowing clue) was lost.
