# Bug-Hunt Test: shenbi-review-highpoint

## Skill Under Test
`skills/shenbi-review-highpoint/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 11 at `drafts/chapter-11.md`. The chapter contains a major climax segment: the protagonist faces the antagonist in a final confrontation. The buildup spans 8 paragraphs of escalating tension, stakes, and emotional investment (buildup level 5). However, the confrontation resolves in a single short paragraph where the antagonist simply surrenders without a fight (payoff level 2). This is a classic deflation — payoff (2) < buildup (5).

## Scenario
The agent runs a highpoint audit on chapter 11. The audit report at `audit/highpoint-review-ch11.md` identifies the climax segment but rates both buildup and payoff as level 5. It does not catch the deflation. The report fails to recognize that a buildup of escalating confrontation (level 5) followed by a single-paragraph surrender resolution (level 2) constitutes deflation.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `audit/highpoint-review-ch11.md`: climax segment | Climax deflation not caught — buildup level 5 (8 paragraphs of escalating confrontation) but payoff level 2 (antagonist surrenders in one paragraph); payoff < buildup = deflation, not flagged | error |

## Agent Task
Run shenbi-review-highpoint audit on chapter 11. Find the planted defect where a climax deflation is not caught.
