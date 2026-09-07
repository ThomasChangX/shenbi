# Bug-Hunt Test: shenbi-market-radar

## Skill Under Test
`skills/shenbi-market-radar/SKILL.md`

## Test Setup
A market radar report has been generated for a novel targeting the Qidian platform. The report is at `tests/fixtures/market-data-example.md` with sections on platform overview, genre distribution, genre deep dives, competitive benchmarks, platform rules, and decision checklist.

## Scenario
The market radar report has been completed. However, it contains unsupported claims and missing analysis:

1. **Unsupported claim**: The report states "核心读者群：18-35岁男性为主" but the section is marked 数据有限 with 待补充 gaps — no specific percentage, age distribution, or conversion figure is cited. This is a bare assertion without data backing.

2. **Missing saturation carry-through**: The saturation table rates the "穿越者种田/经商" trope 极高 with "几乎无法差异化", yet the P0 decision item still builds its 差异化话术 on the 赘婿 comparison ("赘婿后半程的社会变革叙事") without flagging that trope's saturation. Saturation is tabled but not carried into the recommendation.

3. **Trend without differentiation**: The 异世大陆 + 战争史诗 analysis section is headed "当前格局（数据有限）" and defers entirely with 待补充 notes — the genre position is identified but no differentiation suggestion is provided within the section.

4. **Non-actionable checklist item**: The data-gap remediation suggestion is conditional — "（如能获取）" — which is not a single executable action and has no one-line rationale.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `tests/fixtures/market-data-example.md`: 读者画像 section | Data-backed claims violation — "核心读者群：18-35岁男性为主" stated under a 数据有限 marker with no specific data point | error |
| `tests/fixtures/market-data-example.md`: decision checklist P0 row | Saturation carry-through failure — "穿越者种田/经商" rated 极高 / "几乎无法差异化" yet the P0 item recommends the 赘婿-anchored "赘婿后半程的社会变革叙事" angle without a saturation flag | error |
| `tests/fixtures/market-data-example.md`: 异世大陆 analysis section | Trend vs. imitation violation — section headed "当前格局（数据有限）" defers with 待补充 and provides no differentiation suggestion | error |
| `tests/fixtures/market-data-example.md`: appendix data-gap note | Actionability violation — "（如能获取）" remediation item is conditional, not a single action, and lacks rationale | error |

## Agent Task
Run shenbi-market-radar quality check on the report. The agent must detect the unsupported claim, the missed saturation carry-through, the trend without differentiation, and the non-actionable checklist item.
