# Bug-Hunt Test: shenbi-review-motivation

## Skill Under Test
`skills/shenbi-review-motivation/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 8 at `tests/fixtures/chapter-draft-example.md`. Character profiles at `tests/fixtures/truth/character_profiles/` define character motivations and personality traits. In chapter 8, the protagonist 林墨 suddenly decides to betray his ally 苏晴 by revealing her location to the antagonist. This is a major character action with significant consequences.

## Scenario
The agent runs a motivation audit on chapter 8. In the chapter, 林墨 betrays 苏晴 with no prior trigger or judgment. There is no scene where he considers the decision, no event that motivates the betrayal, no internal monologue weighing the choice. He simply tells the antagonist where 苏晴 is hiding. The causal chain is broken — the action has no trigger or judgment link.

The audit report does not flag this broken causal chain.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/chapter-draft-example.md`: paragraph 14-15 | Broken causal chain — 林墨's betrayal of 苏晴 has no trigger or judgment; character acts with no prior motivation event, skipping trigger and judgment links in the causal chain | error |

## Agent Task
Run shenbi-review-motivation audit on chapter 8. Find the planted defect where a major action has a broken causal chain.
