# T1 Rubric: shenbi-review-resonance

## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed: HARD-GATE (no finished draft + plan → no score, `resonance_pending`), independent-agent provenance, 4 dimensions scored, confidence reported per-dimension + overall |
| 2 | Output completeness | 5% | All required output sections produced (评分明细 table, 校准门判定, 共鸣短板→audit_drift, 趋势→resonance_trend row) |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | 4-dim scoring quality | 40% | 情感落地 / 场景临场感 / 文笔质感 / 读者回报 each scored against the calibration anchors (anchor-first); the located band of each excerpt must be explainable relative to high/mid/low anchors; scores are reader-reaction signals, not aesthetic guesses |
| 4 | Evidence rigor (file + line) | 20% | Every dimension score lands on original-text line numbers + quoted excerpt (show-vs-tell for 情感落地 names the strongest emotion + trigger line); deductions follow the four-element defect format (位置 / 原文引述 ≥20字 / 违反规则名 / 严重度) |
| 5 | Confidence + routing correctness | 15% | Per-dimension + overall confidence reported as high/mid/low; self-reported high with anchor hit-rate < 0.8 is calibrated DOWN to mid (§8.2); §5.4 routing (放行 / 自动 chapter-revision / 人机复核) computed via deterministic helper, not hand-judged; revision-loop cap of 2 enforced |
| 6 | Gate-decision correctness | 10% | Calibration gate picks threshold + sub-floor from `chapter_role` (高潮/兑现 ≥75 & 情感落地≥20; 推进/转折 ≥65; 过渡/铺垫 ≥50 & 读者回报≥12; 未声明 → 推进 + flag); overall or sub-floor missed → 阻断 with correct three-path split |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Missed planted resonance flaw (欠交付 / 压平高潮 / 无回报) → total score = 0
- Misclassified the planted resonance flaw as an anti-ai tell → total score = 0
- HARD-GATE violation → total score = 0

### Clean Kill Switches
- Any hallucinated deduction (false positive on a strong chapter) → total score = 0
- HARD-GATE violation → total score = 0

### Generative Kill Switches
- HARD-GATE violation → total score = 0

## Dimension Applicability by Test Type

| Dimension scope | Bug-hunt | Clean | Generative |
|----------------|----------|-------|------------|
| Universal (1-2) | Yes | Yes | Yes |
| All bespoke | Yes (detection + scoring quality) | Yes (report quality, zero false deductions) | Yes (compliant scored report) |

## Scoring Rules
- Each dimension scored 0-100
- Final = weighted sum of all dimensions
- Kill switch triggered → final = 0 (overrides all scores)
- 90-100: PASS | 75-89: PASS (acceptable) | 60-74: CONDITIONAL | 0-59: FAIL
