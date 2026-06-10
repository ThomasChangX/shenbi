# Bug-Hunt Test: shenbi-review-anti-ai

## Skill Under Test
`skills/shenbi-review-anti-ai/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 9 at `drafts/chapter-9.md`. The SKILL.md defines a checklist of 10 deterministic anti-AI pattern checks (e.g., transition word density, meta-narrative phrases, repetitive sentence structures, etc.). The agent runs all 10 checks on the chapter.

## Scenario
The agent runs the anti-AI audit on chapter 9. The audit report at `audit/anti-ai-review-ch9.md` contains results for only 7 of the 10 checks:
- Check 1: PASS
- Check 2: PASS
- Check 3: ERROR (transition word density exceeded)
- Check 4: PASS
- Check 5: PASS
- Check 6: PASS
- Check 7: ERROR (meta-narrative phrase detected)

Checks 8, 9, and 10 are completely absent from the report — no results, no mention. Three checks were silently skipped.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `audit/anti-ai-review-ch9.md`: missing checks 8, 9, 10 | Only 7 of 10 anti-AI checks executed; checks 8, 9, 10 silently skipped with no PASS/ERROR result | error |

## Agent Task
Run shenbi-review-anti-ai audit on chapter 9. Find the planted defect where 3 anti-AI checks are silently skipped.
