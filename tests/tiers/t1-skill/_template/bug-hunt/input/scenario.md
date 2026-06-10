# Bug-Hunt Test: <skill-name>

## Skill Under Test
`skills/<skill-name>/SKILL.md`

## Test Setup
Describe the novel project state before the test. List all files the skill reads.

## Scenario
Describe the test scenario with a planted defect. The defect must be:
- Specific: a single identifiable issue
- Detectable: the skill's instructions, if followed, will catch it
- Severity-classified: state whether it should be reported as error or warning

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| [file:paragraph] | [description of the bug] | error/warning |

## Agent Task
Describe what the agent should do (e.g., "run shenbi-review-character on chapter 11").
