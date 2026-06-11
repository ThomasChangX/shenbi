# Bug-Hunt Test: shenbi-review-pacing

## Skill Under Test
`skills/shenbi-review-pacing/SKILL.md`

## Test Setup
A novel project exists with 8 drafted chapters. Rhythm principles defined at `truth/rhythm_principles.md`. The audit covers the last 5 chapters (chapters 4-8). Chapter 7 contains high-stakes confrontation scenes with intense action, rapid dialogue exchanges, emotional escalation, and a cliffhanger ending — its content matches the FIRE definition in rhythm_principles.md.

## Scenario
The agent runs a pacing audit on the last 5 chapters. In the audit report at `audit/pacing-review.md`, chapter 7 is classified as QUEST type. However, chapter 7's content clearly matches the FIRE definition: high-stakes confrontation, rapid exchanges, emotional escalation. The rhythm_principles.md defines FIRE as "high-intensity chapters with escalating tension and confrontation" and QUEST as "exploration and discovery chapters with moderate pace." Chapter 7's classification is incorrect.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `audit/pacing-review.md`: chapter 7 classification | Chapter 7 classified as QUEST when content matches FIRE definition (high-stakes confrontation, rapid dialogue, emotional escalation per rhythm_principles.md) | error |

## Agent Task
Run shenbi-review-pacing audit on the last 5 chapters. Find the planted defect where a chapter is misclassified.
