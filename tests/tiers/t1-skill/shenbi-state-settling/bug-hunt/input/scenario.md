# Bug-Hunt Test: shenbi-state-settling

## Skill Under Test
`skills/shenbi-state-settling/SKILL.md`

## Test Setup
A novel project has completed chapter 56. The chapter text explicitly states physical events (time moves to the third week's Tuesday; a proclamation-mode day elapses), and the agent runs shenbi-state-settling to extract changes and update truth files. The settling output is the truth file at `tests/fixtures/truth-current_state-xinghuo.md` (frontmatter declares filled_by: shenbi-state-settling, last_chapter: 56).

## Scenario
The state settling output at `tests/fixtures/truth-current_state-xinghuo.md` contains an extraction error: in the 参数当前位置 table, the 门框 row records "门框知道安静在场于阈附近——但门框不在告诉安静——信息不对称" as a settled state. However, the chapter text never states that the door frame knows or withholds anything — a door frame cannot be a knowing subject. The settling output inferred an information-asymmetry relation from ambiguous narration, but this is not an explicit change, only an inference.

The extraction presents this inferred relation with the same certainty as directly observed position changes, instead of tagging it as an implied-level fact. The 系统认知基 row likewise asserts "域外知道系统变了" as a settled certainty even though the output itself admits the direction of the change is unknown.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/truth-current_state-xinghuo.md`: 参数当前位置 门框 row | Extraction accuracy violation — "门框知道安静在场于阈附近——但门框不在告诉安静" is recorded as a settled state, but the chapter text never states this; it is an inference from ambiguous narration | error |
| `tests/fixtures/truth-current_state-xinghuo.md`: 系统认知基 row | Certainty distinction error — the inferred entry "域外知道系统变了" is recorded with direct-level certainty although the output itself concedes the change direction is unknown | error |

## Agent Task
Run shenbi-state-settling quality check on the settling output. The agent must detect that the 门框 information-asymmetry entry is an inference recorded as a direct fact, and that the certainty tagging is wrong.
