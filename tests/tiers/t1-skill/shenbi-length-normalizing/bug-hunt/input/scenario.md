# Bug-Hunt Test: shenbi-length-normalizing

## Skill Under Test
`skills/shenbi-length-normalizing/SKILL.md`

## Test Setup
A novel project exists with a drafted chapter at `tests/fixtures/chapter-draft-example.md` (5000 words). The target chapter length is 4000 words. The agent ran length normalization and produced `tests/fixtures/chapter-draft-example.md` with a consistency checklist at `tests/fixtures/report-example.txt`.

## Scenario
The length normalization has been completed. The normalized version at `tests/fixtures/chapter-draft-example.md` achieves the target word count (approximately 4000 words). However, the normalization added a new scene that did not exist in the original:

1. **New scene added**: The original chapter had 3 scenes: (A) a morning confrontation between Lin Yue and her brother, (B) a midday walk through the market where she gathers information, and (C) an evening meeting with the faction leader. The normalized version introduces a new scene (D) between scenes B and C: Lin Yue visits a teahouse and overhears a conversation about troop movements. This teahouse scene was not in the original chapter and constitutes a new narrative event with new information that changes the story.

2. **Missing consistency checklist**: The normalization report does not include the required consistency checklist confirming no narrative changes were made.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: teahouse scene (between market and meeting scenes) | Narrative changed — new scene added that was not in the original draft, introducing new plot events and information | error |
| `tests/fixtures/report-example.txt`: full document | Missing consistency checklist — required confirmation of no narrative changes is absent | error |

## Agent Task
Run shenbi-length-normalizing quality check on the normalized output. The agent must detect the new scene that was added (narrative change) and the missing consistency checklist.
