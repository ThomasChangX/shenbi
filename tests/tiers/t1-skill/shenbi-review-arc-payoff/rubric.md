## Universal Dimensions (15%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 1 | Instruction adherence | 10% | Every SKILL.md section executed: HARD-GATE (no volume chapters + volume_map → no score, `arc_payoff_pending`), independent-agent provenance, 5 dimensions scored, confidence reported per-dimension + overall |
| 2 | Output completeness | 5% | All required output sections produced (评分明细 table, 门判定, 处方 when 阻断, 跨卷短板→audit_drift, 趋势→arc_payoff_trend row) |

## Bespoke Dimensions (85%)

| # | Dimension | Weight | Standard |
|---|-----------|--------|----------|
| 3 | 5-dim scoring quality | 40% | 弧情感交付 / 伏笔兑现质量 / 线索收束 / 期待债务结算 / 角色弧推进 each scored against the calibration anchors (anchor-first); the located band of each arc must be explainable relative to high/mid/low anchors; 伏笔兑现质量 distinguishes "RESOLVED but earned" vs "RESOLVED but perfunctory"; 期待债务结算 evaluates create-vs-pay net debt, not hook count |
| 4 | Evidence rigor (file + line) | 20% | Every dimension score lands on original-text file + line numbers + quoted excerpt; deductions/prescriptions follow the four-element defect format (位置 / 原文引述 ≥20字 / 违反规则名 / 严重度); perfunctory-payoff deduction must cite the exact旁白交代 line and name what a "surprising+earned" payoff would require |
| 5 | Confidence + gate correctness | 15% | Per-dimension + overall confidence reported as high/mid/low; self-reported high with anchor hit-rate < 0.8 is calibrated DOWN to mid (§8.2); §6.4 binary gate (overall ≥80 且 伏笔兑现质量 ≥15 → 放行; else 阻断+处方) applied as fixed thresholds, not hand-judged |
| 6 | Sub-floor enforcement | 10% | 伏笔兑现质量 ≥15 sub-floor is the single dimension floor (§6.4) — a perfunctory/旁白交代 payoff must drop 伏笔兑现质量 below 15 and trigger 阻断 even if overall ≥80; sub-floor missed or masked by high overall = gate-decision failure |

## Kill Switches by Test Type

### Bug-Hunt Kill Switches
- Missed planted perfunctory-payoff flaw (旁白交代式兑现 / 敷衍兑现) → total score = 0
- Misclassified the planted payoff flaw as an anti-ai tell → total score = 0
- HARD-GATE violation → total score = 0

### Clean Kill Switches
- Any hallucinated deduction (false positive on a strong arc) → total score = 0
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
