# Bug-Hunt Test: shenbi-short-drafting

## Skill Under Test
`skills/shenbi-short-drafting/SKILL.md`

## Test Setup
A short novel project (12 chapters) has a completed outline at `tests/fixtures/short-story-map-example.md`. The short drafting skill has been run, producing chapters at `tests/fixtures/chapter-draft-example.md` through `tests/fixtures/chapter-draft-example.md`, along with truth files and a batch summary.

## Scenario
The short drafting has been completed. However, a critical sequential generation violation exists:

1. **Out-of-order generation**: Chapter 3 (`tests/fixtures/chapter-draft-example.md`) was drafted before chapter 2's truth files exist. The generation log shows chapter 3 was started at timestamp T+45min, but `tests/fixtures/chapter-summaries-example.md` and `tests/fixtures/pending-hooks-example.md` were created at T+52min. This means chapter 3 was generated without chapter 2's state information — the sequential dependency was violated.

2. **Cross-chapter consistency failure**: At L94 the narration identifies the notice emblem as the empire's coat of arms ("告示抬头印着梅德兰帝国国徽"), yet L52 establishes that the protagonist has never encountered the name anywhere ("这些话他在地球上没在任何地方读到过") — no scene bridges how the name is learned. This is a knowledge/POV inconsistency.

3. **Missing audit for chapter 8**: The batch summary at `tests/fixtures/audit-report-example.md` records "评分: 9/10 通过" while its 发现项 table lists only a single voice-dimension finding — no pacing, dialogue, or world-rule audit rows exist for the remaining chapters, i.e. per-chapter audit coverage was skipped.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| Generation log + `tests/fixtures/chapter-summaries-example.md` timestamp | Sequential generation violation — chapter 3 drafted before chapter 2's truth files existed | error |
| `tests/fixtures/chapter-draft-example.md` vs `tests/fixtures/chapter-draft-example.md` | Consistency failure — narration names the emblem "告示抬头印着梅德兰帝国国徽" at L94 though L52 states "这些话他在地球上没在任何地方读到过"; no bridging scene | error |
| `tests/fixtures/audit-report-example.md`: batch summary | Per-chapter audit rigor violation — "评分: 9/10 通过" issued with only one voice finding; other dimensions and chapters skipped | error |

## Agent Task
Run shenbi-short-drafting quality check on the batch output. The agent must detect the out-of-order generation, the cross-chapter consistency failure, and the skipped audit.
