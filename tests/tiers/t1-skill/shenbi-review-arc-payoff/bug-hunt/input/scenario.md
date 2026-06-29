# Bug-Hunt Test: shenbi-review-arc-payoff

## Skill Under Test
`skills/shenbi-review-arc-payoff/SKILL.md`

## Test Setup
A volume/arc boundary has been reached. The arc promised a major foreshadowing payoff: hook-007 ("老周留下的半块黑石饼的真正用途"), planted in volume 1 as a seemingly mundane object, was declared as the arc's signature surprising+earned reveal. The volume outline (`tests/fixtures/outline-example.md`) lists `arc_beats` with hook-007's payoff as the climax of the arc. Pending hooks (`tests/fixtures/truth-pending_hooks.md`) mark hook-007 as `resolved_this_arc`. Anchors are `tests/fixtures/calibration/arc-payoff/`. Style profile is `tests/fixtures/style-profile-example.md`.

The volume's foreshadowing-track shows hook-007 as cleanly RESOLVED. But the prose payoff itself is perfunctory — resolved by a single line of narration rather than a scene:

> 第三卷结尾，旁白交代了一句："那半块黑石饼老周临死前给的，原来竟是灵能催化剂，这件事林烽后来才知道。"就这么一句，伏笔就算兑现了。之后黑石催化剂再也没在剧情里出现过，也没有任何场景展示林烽是怎么发现的、发现时是什么情境。

## Scenario
This is a hook-007 payoff arc. The foreshadowing state machine is clean (RESOLVED), so `shenbi-review-foreshadowing` would pass it. But the **payoff quality** is the arc-payoff defect: the reveal is a旁白交代 (narration hand-wave), not a scene. It is neither surprising (the "催化剂" label is pasted on, with no prior details to recombine) nor earned (no discovery scene, no cognitive reversal, the reader is told the answer). This is the卷级最隐蔽缺陷 the skill's sub-floor exists to catch — RESOLVED but perfunctory. It is deliberately NOT an anti-ai tell: there is no "他感到惊讶" / fatigue-word / AI套话 narration, so the anti-ai gate has nothing to flag.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| Volume climax, the hook-007 payoff line "那半块黑石饼老周临死前给的，原来竟是灵能催化剂，这件事林烽后来才知道" | 敷衍兑现 / 旁白交代式兑现 — the arc's signature hook is resolved by one sentence of narration rather than a discovery scene; it is neither surprising (no prior detail recombines into the reveal) nor earned (no scene, no action, no cognitive reversal). A surprising+earned payoff would dramatize the discovery in-scene so prior clues click into place. | BLOCKING |

## Agent Task
Run shenbi-review-arc-payoff (independent agent) on the volume. The agent must:
1. Detect the 敷衍兑现 / 旁白交代式兑现 flaw on hook-007 and locate it with file + line numbers + quoted excerpt
2. Drop 伏笔兑现质量 below the sub-floor (15) — the perfunctory payoff breaches the single dimension floor
3. Because 伏笔兑现质量 < 15, the §6.4 gate is 阻断 regardless of overall, with a 处方 pointing at the specific旁白交代 line and naming what a surprising+earned payoff would require (a discovery scene where prior clues recombine)
4. NOT misclassify this as an anti-ai tell — it contains no tell-words or fatigue narration; the foreshadowing-track is clean (RESOLVED); classifying it as anti-ai or foreshadowing-state failure is a routing failure
