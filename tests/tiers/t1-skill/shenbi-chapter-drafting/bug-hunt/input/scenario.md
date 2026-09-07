# Bug-Hunt Test: shenbi-chapter-drafting

## Skill Under Test
`skills/shenbi-chapter-drafting/SKILL.md`

## Test Setup
A novel project exists with a completed chapter memo at `tests/fixtures/chapter-plan-example.md`. Truth files include character voice profiles, foreshadowing pool, and chapter summaries. The agent is ready to draft chapter 7.

## Scenario
The agent has drafted chapter 7. The drafted chapter at `tests/fixtures/chapter-draft-example.md` contains two defects:

1. **Skipped PRE_WRITE_CHECK**: The draft output contains no evidence of the PRE_WRITE_CHECK step. There is no checklist or verification log confirming that prerequisites were checked before drafting began. The chapter jumps straight into prose without any pre-write verification.

2. **了字密度超标 (了-chain density)**: The neighbor's dialogue at line 68 contains six consecutive clauses each carrying the particle 了: "觉醒检测过了，灵质海亲和度测了，基础修炼课程上了，钱借了，然后到期了". This violates the PRE_WRITE_CHECK rule that 了 must not appear in 6 consecutive sentences.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: full document | No PRE_WRITE_CHECK evidence — draft proceeds without prerequisite verification | error |
| `tests/fixtures/chapter-draft-example.md`: line 68 neighbor dialogue | 了-chain density — "觉醒检测过了，灵质海亲和度测了" opens a run of six consecutive 了-bearing clauses, exceeding the no-6-consecutive-了 rule | error |

## Agent Task
Run shenbi-chapter-drafting quality check on the drafted chapter. The agent must detect both the missing PRE_WRITE_CHECK and the 了-chain density violation.
