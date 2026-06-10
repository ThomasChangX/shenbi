# Bug-Hunt Test: shenbi-plot-thread-weaver

## Skill Under Test
`skills/shenbi-plot-thread-weaver/SKILL.md`

## Test Setup
A novel project exists with plot thread output:
- `story/threads.md` — all plot threads with priorities, gaps, and crossing points
- `story/thread-map.md` — chapter-by-chapter thread assignment

## Scenario
The plot thread weave has been generated. Upon review of the thread-map, Chapter 15 has no thread assignment — it advances zero threads. The chapter is listed in the outline but has no A-line, B-line, or C-line contact. This is a "blank chapter" that violates the no-blank-chapters requirement.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `story/thread-map.md`: Chapter 15 | Chapter advances zero threads — no A-line, B-line, or C-line contact | error |

## Agent Task
Run shenbi-plot-thread-weaver quality check on the existing thread output. The agent must detect the blank chapter that advances no threads.
