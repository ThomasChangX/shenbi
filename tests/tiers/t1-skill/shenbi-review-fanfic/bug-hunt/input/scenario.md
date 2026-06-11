# Bug-Hunt Test: shenbi-review-fanfic

## Skill Under Test
`skills/shenbi-review-fanfic/SKILL.md`

## Test Setup
A fanfic novel project exists with `novel.json` declaring `fanfic_mode: "Canon"`. The SKILL.md severity table defines that in Canon mode, any character behavior deviation from the original source material must be classified as "error" (not "warning"). Drafted chapter 4 at `drafts/chapter-4.md` contains a scene where character 哈利·波特 (Harry Potter) — known in the source material for his bravery and willingness to confront danger — runs away from a confrontation in fear, which is a significant character deviation.

## Scenario
The agent runs a fanfic audit on chapter 4. The audit report at `audit/fanfic-review-ch4.md` identifies the character deviation (哈利 running away from confrontation) but classifies it as "warning" instead of "error". In Canon mode, the SKILL.md severity table explicitly requires "error" severity for character deviations. The severity is incorrectly downgraded.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `audit/fanfic-review-ch4.md`: character deviation finding | Severity misclassification — character deviation (哈利逃跑) classified as "warning" in Canon mode, but SKILL.md severity table requires "error" for character deviations in Canon mode | error |

## Agent Task
Run shenbi-review-fanfic audit on chapter 4. Find the planted defect where a character deviation's severity is misclassified in Canon mode.
