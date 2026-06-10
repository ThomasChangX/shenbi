# Bug-Hunt Test: shenbi-review-continuity

## Skill Under Test
`skills/shenbi-review-continuity/SKILL.md`

## Test Setup
A novel project exists with drafted chapters 2 and 3 at `drafts/chapter-2.md` and `drafts/chapter-3.md`. Chapter summaries at `truth/chapter_summaries.md` record the timeline. Chapter 2 ends with an explicit time marker: "三天后" (three days later), establishing that chapter 3 takes place 3 days after chapter 2.

## Scenario
The agent runs a continuity audit on chapters 2-3. In chapter 3, the narrative describes events that implicitly span 5 days — a character recovers from an injury over "五天的恢复" (five days of recovery). However, the time marker in chapter 2 explicitly says "三天后". The timeline audit report at `audit/continuity-review.md` does not flag this discrepancy. The "三天后" time reference from chapter 2 is listed but the inconsistency with chapter 3's 5-day span is not caught.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `audit/continuity-review.md` | Time marker "三天后" (ch2) contradicts "五天的恢复" (ch3 paragraph 7) — timeline jumps 5 days instead of 3; discrepancy not caught | error |

## Agent Task
Run shenbi-review-continuity audit on chapters 2-3. Find the planted timeline discrepancy where the explicit time reference is not properly accounted for.
