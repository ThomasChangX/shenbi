# Bug-Hunt Test: shenbi-worldbuilding

## Skill Under Test
`skills/shenbi-worldbuilding/SKILL.md`

## Test Setup
A novel project exists with the following worldbuilding files already generated:
- `tests/fixtures/world-rules-example.md` — hard rules (世界铁律) with testable standards
- `tests/fixtures/world-story-bible-example.md` — narrative prose world bible
- `tests/fixtures/world-locations-example.md` — geographical overview (初始地点图谱)
- `tests/fixtures/world-power-system-example.md` — power system ladder (灵能认知十阶)

## Scenario
The worldbuilding output has been generated. During its quality pass, the skill should cross-check the hard rules in the rules file against the power-system file. The rules file's 规则一 requires "净消耗必须一致：连续章节中同一来源的灵能储备必须递减而非递增，除非有明确的补充事件发生" — every reserve change needs an explicit replenishment event.
Meanwhile the power-system file's 等级表 grants rank 3 (凝核) the ability "凝聚灵能核心，被动吸收灵质海能量" — continuous passive absorption with no defined 补充事件 threshold. The two standards are in unresolved tension: passive absorption implies reserves can regenerate between chapters without any recorded event, which is exactly the pattern 规则一's violation example forbids. The quality pass did not flag or reconcile this cross-file gap.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/world-rules-example.md`: 规则一 cross-checked against the power system's rank-3 passive absorption | Cross-file tension unreconciled — 规则一 demands "净消耗必须一致：连续章节中同一来源的灵能储备必须递减而非递增，除非有明确的补充事件发生" while the power system's 等级3 grants passive absorption of 灵质海 energy; no rule defines when passive absorption counts as the required 补充事件 | error |

## Agent Task
Run shenbi-worldbuilding quality check on the existing worldbuilding output. The agent must detect the unresolved tension between 规则一's reserve-consistency standard and the power system's passive absorption ability.
