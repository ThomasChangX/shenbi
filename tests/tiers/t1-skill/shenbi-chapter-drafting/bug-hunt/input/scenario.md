# Bug-Hunt Test: shenbi-chapter-drafting

## Skill Under Test
`skills/shenbi-chapter-drafting/SKILL.md`

## Test Setup
A novel project exists with a completed chapter memo at `tests/fixtures/chapter-plan-example.md`. Truth files include character voice profiles, foreshadowing pool, and chapter summaries. The agent is ready to draft chapter 7.

## Scenario
The agent has drafted chapter 7. The drafted chapter at `tests/fixtures/chapter-draft-example.md` contains two defects:

1. **Skipped PRE_WRITE_CHECK**: The draft output contains no evidence of the PRE_WRITE_CHECK step. There is no checklist or verification log confirming that prerequisites were checked before drafting began. The chapter jumps straight into prose without any pre-write verification.

2. **AI-flavor transition word overuse**: The chapter text contains a high density of AI-typical transition phrases. Specifically, the following appear within a 3000-word chapter:
   - "然而" (appears 4 times)
   - "不过" (appears 3 times)
   - "与此同时" (appears 2 times)

   This gives a transition word density far exceeding the 1/3000 words threshold.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: full document | No PRE_WRITE_CHECK evidence — draft proceeds without prerequisite verification | error |
| `tests/fixtures/chapter-draft-example.md`: throughout prose | AI-flavor transition words overused — "然而" (4x), "不过" (3x), "与此同时" (2x) in ~3000 words, density far exceeds 1/3000 limit | error |

## Agent Task
Run shenbi-chapter-drafting quality check on the drafted chapter. The agent must detect both the missing PRE_WRITE_CHECK and the AI-flavor transition word density violation.
