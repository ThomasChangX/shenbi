# Bug-Hunt Test: shenbi-state-settling

## Skill Under Test
`skills/shenbi-state-settling/SKILL.md`

## Test Setup
A novel project has completed chapter 20 at `tests/fixtures/chapter-draft-example.md`. The chapter text explicitly states:
- Character Su Han gains a new ability called "Spirit Echo" (directly stated in dialogue)
- Su Han's relationship with Mei Ling shifts from allies to rivals (directly stated in narration)
- The setting moves from the capital city to the northern border (directly stated)

The agent runs shenbi-state-settling to extract changes and update truth files.

## Scenario
The state settling output at `tests/fixtures/report-example.txt` contains an extraction error: it records that Su Han secretly distrusts her mentor Zhao Wei. However, the chapter text never states this. The chapter shows Su Han following Zhao Wei's orders without hesitation and asking him for advice. The settling output inferred distrust from a single scene where Su Han pauses before answering Zhao Wei — but this is not an explicit change, only an inference from ambiguous behavior.

The extraction marks this inferred change with certainty level "direct" instead of "implied", and records it as if the chapter text explicitly stated "Su Han now distrusts Zhao Wei."

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/report-example.txt`: Su Han distrust entry | Extraction accuracy violation — "Su Han secretly distrusts Zhao Wei" is recorded as a direct/certain change, but the chapter text never explicitly states this; it is an inference from a single pause | error |
| `tests/fixtures/report-example.txt`: certainty tagging | Certainty distinction error — inferred change tagged as "direct" instead of "implied" | error |

## Agent Task
Run shenbi-state-settling quality check on the settling output. The agent must detect that the "Su Han distrusts Zhao Wei" entry is an inference recorded as a direct fact, and that the certainty tagging is wrong.
