# Bug-Hunt Test: shenbi-short-outline

## Skill Under Test
`skills/shenbi-short-outline/SKILL.md`

## Test Setup
A short novel project (20 chapters) has its `novel.json` and `truth/author_intent.md` set up. The short outline skill has been run, producing `outline/short_story_map.md`.

## Scenario
The short outline has been completed. However, the output contains a dead chapter and other issues:

1. **Dead chapter**: Chapter 10 in `outline/short_story_map.md` has its task listed as "transition — protagonist travels to the northern city." No threads are advanced in this chapter. There is no subplot advancement, no emotional arc progress, and no main plot development — the chapter merely moves the character geographically.

2. **Act proportioning violation**: The 20-chapter outline splits as Act 1: chapters 1-8 (8 chapters = 40%), Act 2: chapters 9-14 (6 chapters = 30%), Act 3: chapters 15-20 (6 chapters = 30%). The required 20/60/20 split is violated — Act 2 is too short and Acts 1 and 3 are too long.

3. **Skipped review step**: The generation log shows only 2 steps (generate and revise) instead of the required 3 steps (generate -> review -> revise). The review step was skipped entirely.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `outline/short_story_map.md`: chapter 10 | Dead chapter — task is "transition" with zero thread advancement; no subplot, emotional arc, or main plot progress | error |
| `outline/short_story_map.md`: act breakdown | Act proportioning violation — 40/30/30 split instead of required 20/60/20 | error |
| Generation log (3-step enforcement) | Skipped step — review step missing; only generate -> revise executed instead of generate -> review -> revise | error |

## Agent Task
Run shenbi-short-outline quality check on the outline. The agent must detect the dead chapter, the act proportioning violation, and the skipped review step.
