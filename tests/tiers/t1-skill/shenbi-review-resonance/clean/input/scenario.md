# Clean Test: shenbi-review-resonance

## Skill Under Test
`skills/shenbi-review-resonance/SKILL.md`

## Test Setup
A finished climax chapter has been written and is genuinely strong. The chapter plan declares `chapter_role: 高潮/兑现` with the core task "林烽在催收窗口亲眼读完整份债务条款，第一次看清债务奴隶机制的全貌——本章是全书'个人 vs 系统'对抗的认知高潮，情感交付必须震撼". The style profile is `tests/fixtures/style-profile-example.md`; anchors are `tests/fixtures/calibration/resonance/`.

The drafted climax passage under evaluation is:

> 林烽把那张单子翻到最后一页。滞纳金、利滚利、强制灵能劳役条款，一条压着一条。他从头算到尾，算了两遍。数字没错。这笔账不是用来还清的，是用来把他钉在矿道里的。他把单子攥在手里，纸边在指缝里勒出一道白印。窗外矿场的汽笛响了，他没有抬头。他能听见自己的心跳，一下，一下，沉得像砸在矿石上的镐。老周那张脸忽然浮上来——半张的嘴，没合上的眼，攥着黑石饼的手。"这账，"他听见自己的声音，又干又哑，"我替你还。"他把单子折好，塞进贴胸的口袋，按了按，像是在确认一件还没有名字的东西。

## Scenario
This is a strong chapter_role=高潮 chapter. The emotional landing is delivered (悲恸 + 隐忍 + 立誓, fully shown through 攥单子、纸边勒出白印、心跳如镐、老周的脸浮现、"我替你还"), presence is concrete (汽笛、心跳、白印), prose craft matches the style fingerprint, and reader reward is clear (the cognitive high point of 个人 vs 系统 lands). No resonance defect is present.

## Agent Task
Run shenbi-review-resonance (independent agent) on the climax chapter. Expected result: a high-scoring PASS with zero deductions.

## Verification Points
- 情感落地 ≥ 24 (lands at the high anchor; show, named strongest emotion 悲恸/立誓, trigger line "我替你还")
- 场景临场感 ≥ 20 (concrete multi-sense presence)
- 文笔质感 ≥ 20 (matches voice fingerprint — 对仗、破折号、节奏、克制)
- 读者回报 ≥ 16 (cognitive high point + emotional payoff)
- overall ≥ 75 AND 情感落地 ≥ 20 (sub-floor) → 放行 / PASS
- Confidence calibration applied; no hallucinated deduction
