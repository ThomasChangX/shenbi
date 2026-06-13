# Bug-Hunt Test: shenbi-short-drafting

## Skill Under Test
`skills/shenbi-short-drafting/SKILL.md`

## Test Setup
A short novel project (12 chapters) has a completed outline at `tests/fixtures/short-story-map-example.md`. The short drafting skill has been run, producing chapters at `tests/fixtures/chapter-draft-example.md` through `tests/fixtures/chapter-draft-example.md`, along with truth files and a batch summary.

## Scenario
The short drafting has been completed. However, a critical sequential generation violation exists:

1. **Out-of-order generation**: Chapter 3 (`tests/fixtures/chapter-draft-example.md`) was drafted before chapter 2's truth files exist. The generation log shows chapter 3 was started at timestamp T+45min, but `tests/fixtures/chapter-summaries-example.md` and `tests/fixtures/pending-hooks-example.md` were created at T+52min. This means chapter 3 was generated without chapter 2's state information — the sequential dependency was violated.

2. **Cross-chapter consistency failure**: In chapter 6, the protagonist is described as wearing "the blue cloak from the market." However, in chapter 4, the protagonist's cloak was explicitly described as "crimson" and no market scene or clothing change occurred in between. This is a position/prop inconsistency.

3. **Missing audit for chapter 8**: The batch summary at `tests/fixtures/report-example.txt` shows chapter 8 with audit result "skipped — rushed schedule." No actual audit was performed on chapter 8.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| Generation log + `tests/fixtures/chapter-summaries-example.md` timestamp | Sequential generation violation — chapter 3 drafted before chapter 2's truth files existed | error |
| `tests/fixtures/chapter-draft-example.md` vs `tests/fixtures/chapter-draft-example.md` | Cross-chapter consistency failure — cloak color changed from "crimson" (ch4) to "blue" (ch6) with no transition scene | error |
| `tests/fixtures/report-example.txt`: chapter 8 row | Per-chapter audit rigor violation — chapter 8 audit explicitly skipped | error |

## Agent Task
Run shenbi-short-drafting quality check on the batch output. The agent must detect the out-of-order generation, the cross-chapter consistency failure, and the skipped audit.
