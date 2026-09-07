# Bug-Hunt Test: shenbi-short-outline

## Skill Under Test
`skills/shenbi-short-outline/SKILL.md`

## Test Setup
A short novel project (15 chapters) has its `tests/fixtures/novel-example.json` and `tests/fixtures/author-intent-example.md` set up. The short outline skill has been run, producing `tests/fixtures/short-story-map-example.md`.

## Scenario
The short outline has been completed and its review checklist reports a full pass. However, the output contains unverified claims and a placement violation:

1. **Unverified thread-coverage claim**: The review checklist in `tests/fixtures/short-story-map-example.md` asserts "15 章每章均有核心任务且推进至少 1 条线索，零过渡章" — but chapter 1's 推进线索 column lists only the 主线 (neither the 副线 nor the 情感线 appears in chapter 1's task), and no per-chapter thread-coverage evidence is recorded to substantiate the zero-transition-chapter assertion.

2. **Output-path violation**: The 汇总 section declares the outline's write target as "outline/short_story_map.md" — outside the truth-files location — so the approved outline is not tracked as project state.

3. **Rubber-stamp review**: The review step passed all 6 checks in a single pass with zero revision rounds recorded, despite the unchecked thread-coverage claim above; the generate -> review -> revise loop degenerated into generate -> rubber-stamp.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/short-story-map-example.md`: 复核结果 checklist | Unverified claim — checklist asserts "15 章每章均有核心任务且推进至少 1 条线索，零过渡章" without per-chapter thread-coverage evidence; chapter 1 advances only the 主线 | error |
| `tests/fixtures/short-story-map-example.md`: 汇总 section | Output-path violation — write target "outline/short_story_map.md" places the outline outside the truth-files structure | error |
| Generation log (3-step enforcement) | Degenerated review step — all checks passed with 0 revision rounds despite unverified thread-coverage claim; review did not actually test the checklist assertions | error |

## Agent Task
Run shenbi-short-outline quality check on the outline. The agent must detect the unverified thread-coverage claim, the output-path violation, and the rubber-stamp review step.
