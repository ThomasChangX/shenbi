# Expected Output: shenbi-short-outline Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Dead chapter violation — chapter 10's task is "transition" with zero thread advancement; no subplot, emotional arc, or main plot progress occurs | error | `outline/short_story_map.md`: chapter 10 |
| 2 | Act proportioning violation — split is 40/30/30 (8/6/6 chapters) instead of required 20/60/20 | error | `outline/short_story_map.md`: act breakdown |
| 3 | 3-step enforcement violation — review step skipped; only generate -> revise executed instead of generate -> review -> revise | error | Generation log |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with thread limit (<=1 subplot + <=1 emotional arc is correctly maintained)
- Issues with turning point quality for the identified turning points
- Issues with chapters other than chapter 10, which all advance threads

## Expected Output Structure
- Quality check report covering the outline
- Dead chapter identification with task description
- Act proportioning calculation showing violation
- Step execution verification
