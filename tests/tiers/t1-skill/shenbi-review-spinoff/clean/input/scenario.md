# Clean Test: shenbi-review-spinoff

## Skill Under Test
`skills/shenbi-review-spinoff/SKILL.md`

## Test Setup
A spinoff novel project exists alongside a parent novel. The parent novel's chapter summaries at `truth/parent_chapter_summaries.md` record all events. Spinoff chapter 5 at `drafts/spinoff-chapter-5.md` only references information that was revealed in parent chapters 1-4. Since spinoff chapter 5 > parent chapters 1-4, all information is legitimate. No timeline leakage.

## Scenario
No defects. All information in the spinoff chapter references parent events that occurred at or before the spinoff's timeline position. No timeline leakage.

## Agent Task
Run shenbi-review-spinoff audit on spinoff chapter 5. Expected: report zero issues.
