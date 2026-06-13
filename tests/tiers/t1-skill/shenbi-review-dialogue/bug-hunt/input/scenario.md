# Bug-Hunt Test: shenbi-review-dialogue

## Skill Under Test
`skills/shenbi-review-dialogue/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 5 at `tests/fixtures/chapter-draft-example.md`. Voice profiles at `tests/fixtures/truth/character_profiles/` define two characters with distinct speech patterns:
- 苏晴: short, clipped sentences (avg 8 chars), formal vocabulary, uses "请问" / "是否" patterns
- 老陈: long, rambling sentences (avg 25 chars), colloquial vocabulary, uses "哎呀" / "就是说" filler patterns

## Scenario
The agent runs a dialogue audit on chapter 5. Two characters 苏晴 and 老陈 speak in chapter 5. Despite having very different voice profiles, both characters use identical sentence patterns throughout the chapter:
- Both use short, clipped sentences averaging ~10 chars
- Both use formal vocabulary
- Neither uses their distinctive filler words

The audit report does not flag this voice fingerprint mismatch.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: paragraphs 3, 6, 9, 14 | Voice fingerprint mismatch — 苏晴 and 老陈 use identical sentence patterns despite different voice_profile baselines | error |

## Agent Task
Run shenbi-review-dialogue audit on chapter 5. Find the planted defect where two characters speak with identical patterns despite having different voice profiles.
