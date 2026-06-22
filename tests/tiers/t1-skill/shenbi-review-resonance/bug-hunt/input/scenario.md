# Bug-Hunt Test: shenbi-review-resonance

## Skill Under Test
`skills/shenbi-review-resonance/SKILL.md`

## Test Setup
A finished climax chapter has been written. The chapter plan declares `chapter_role: 高潮/兑现` with the core task "林烽在催收窗口亲眼读完整份债务条款，第一次看清债务奴隶机制的全貌——本章是全书'个人 vs 系统'对抗的认知高潮，情感交付必须震撼". The style profile is `tests/fixtures/style-profile-example.md`; anchors are `tests/fixtures/calibration/resonance/`.

The drafted climax passage under evaluation is:

> 林烽把那张单子翻到最后一页。滞纳金、利滚利、强制灵能劳役条款，白纸黑字全在那里，一条压着一条。他把每一条从头看到尾，又从头算了一遍。数字没错，一条都没错。他把单子放回桌上，起身去厨房倒了杯凉水，喝完，又倒了一杯。窗外矿场的汽笛响了两声，他想起明天该换班了。他把杯子洗了，搁回架子上，然后坐回桌前，把单子叠好，收进抽屉。他想着明天得早点起，不然赶不上第一趟矿车。

## Scenario
This is a chapter_role=高潮 chapter. The information is complete (every clause of the debt-slavery mechanism is revealed), but the emotional climax beat is flattened: after reading the crushing terms the protagonist reacts by drinking water, washing a cup, and thinking about his next shift. The devastating realization the plan memo required (震撼交付) never lands. This is a resonance-specific flaw — 压平高潮 (climax beat flattened / 欠交付). It is deliberately NOT an anti-ai tell: there is no "他感到愤怒" / "眼神一冷" / fatigue-word narration, so the anti-ai gate has nothing to flag.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| Drafted climax passage, the aftermath after "数字没错，一条都没错" | 压平高潮 / 欠交付 — the plan requires a 震撼 emotional landing for the 高潮 chapter_role; the prose deflates the climax into mundane logistics (倒水、洗杯子、想着换班) with no emotional beat, so 情感落地 drops below the 高潮 sub-floor of 20 and overall falls below the 75 threshold | BLOCKING |

## Agent Task
Run shenbi-review-resonance (independent agent) on the climax chapter. The agent must:
1. Detect the 压平高潮 / 欠交付 flaw and locate it with file + line numbers + quoted excerpt
2. Drop 情感落地 below the 高潮 sub-floor (20) and overall below the 高潮 threshold (75)
3. Flag the calibration gate as 阻断 and route via §5.4 (明确失败 → 自动 chapter-revision at high confidence, or 人机复核 if borderline)
4. NOT misclassify this as an anti-ai tell — it contains no tell-words or fatigue narration; classifying it as anti-ai is a routing failure
