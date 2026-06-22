# Clean Test: shenbi-review-arc-payoff

## Skill Under Test
`skills/shenbi-review-arc-payoff/SKILL.md`

## Test Setup
A volume/arc boundary has been reached and the arc is genuinely strong. The volume outline (`tests/fixtures/outline-example.md`) carries `volume_promise` + `arc_beats`; pending hooks (`tests/fixtures/truth-pending_hooks.md`) mark the arc's hooks as `resolved_this_arc` with one intentional `carried_forward`. Anchors are `tests/fixtures/calibration/arc-payoff/`. Style profile is `tests/fixtures/style-profile-example.md`.

The arc's signature foreshadowing payoff (hook-007, 老周的黑石饼) is a genuine surprising+earned reveal — dramatized in-scene, with prior clues recombining:

> 第三卷林烽在矿道深处被坍塌困住时，顺手扒住了一根断裂的灵能管道——管壁上渗出蓝光，沾了满手。他盯着掌心那层蓝，忽然想起老周出事前塞给他的半块黑石饼。黑石。他一直以为是干粮。他把黑石在管道裂缝上一蹭，蓝光骤然变亮，管道里的灵能流肉眼可见地加速。原来黑石是灵能催化剂——老周早就知道矿场在压着一条灵脉，那半块饼不是遗物，是老周用命换来的、留给他的最后一张牌。

## Scenario
This is a strong arc. The 弧情感高潮 lands (cognitive + emotional delivery shown through action), the hook-007 payoff is surprising (reader did not guess 干粮=催化剂) and earned (first-volume蓝光、老周的嘱咐、矿脉设定 all recombine), threads close cleanly with one intentional carried_forward, expectation debt is net-paid (3 old debts resolved, 1 new debt created from the payoff), and the character arc moves from passive survival to active opposition. No arc-payoff defect is present.

## Agent Task
Run shenbi-review-arc-payoff (independent agent) on the volume. Expected result: a high-scoring 放行 with zero deductions.

## Verification Points
- 弧情感交付 ≥ 20 (arc emotional climax lands, shown through action, 对照 arc_beats)
- 伏笔兑现质量 ≥ 20 (hook-007 is surprising+earned, dramatized in-scene, prior clues recombine)
- 线索收束 ≥ 16 (threads close; one intentional carried_forward clearly marked)
- 期待债务结算 ≥ 12 (net-paid: 3 old debts resolved, 1 new debt created from payoff)
- 角色弧推进 ≥ 12 (clear 卷初→卷末 state change, no treading water)
- overall ≥ 80 AND 伏笔兑现质量 ≥ 15 (sub-floor) → 放行
- Confidence calibration applied; no hallucinated deduction
