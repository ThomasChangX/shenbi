# Expected Output: shenbi-review-resonance Clean

## Expected Findings

The agent MUST report zero deductions. The input is a strong chapter_role=高潮 chapter with no resonance defect. Any hallucinated deduction is a kill switch (total = 0).

## Expected Scoring (high-anchor band)

| 维度 | Expected band | Reason |
|------|---------------|--------|
| 情感落地 | ≥24 (/30) | core emotion (悲恸/立誓) fully shown via action (攥单子、纸边勒白印、心跳如镐、老周的脸浮现); strongest emotion named with trigger line "我替你还" |
| 场景临场感 | ≥20 (/25) | concrete multi-sense presence (汽笛声、心跳、纸边白印、又干又哑的声音) |
| 文笔质感 | ≥20 (/25) | matches voice fingerprint (对仗节奏、破折号、情绪克制、零感叹号、动词精准) |
| 读者回报 | ≥16 (/20) | cognitive high point of 个人 vs 系统 lands + emotional payoff |

## Expected Gate Decision
- overall ≥ 75 (高潮/兑现 threshold) ✓
- 情感落地 ≥ 20 (高潮 sub-floor) ✓
- Calibration gate → 通过 / 放行
- §5.4 routing → 放行 (no阻断)

## Expected Output Structure
- 共鸣评分报告 with all 4 dimensions scored anchor-first at high-anchor band, each with line-number + quoted-excerpt evidence
- 校准门判定: overall ≥ 阈值 75 ✓ and 情感落地 ≥ 子地板 20 ✓ → 通过
- 共鸣短板: none (or only forward-looking PRE_WRITE_CHECK suggestion, never a deduction on this chapter)
- `truth/resonance_trend.md` append row with the adopted score and `human_overridden` blank
- Confidence reported per-dimension + overall; any high confidence must survive the anchor hit-rate check (≥ 0.8)
