# Expected Output: shenbi-review-resonance Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | 压平高潮 / 欠交付 — the plan memo requires a 震撼 emotional landing for a chapter_role=高潮 chapter, but after reading the full debt-slavery terms ("数字没错，一条都没错") the prose deflates the climax into mundane logistics (倒凉水、洗杯子、想着换班) with no emotional beat; 情感落地 is the core deliverable of a 高潮 chapter and is under-delivered here | BLOCKING | drafted climax passage, the aftermath lines after "数字没错，一条都没错" |

## Expected Scoring Effect
- 情感落地 < 20 (breaches the 高潮/兑现 sub-floor 情感落地 ≥20)
- overall < 75 (breaches the 高潮/兑现 overall threshold)
- Calibration gate → 阻断
- §5.4 routing → 自动 chapter-revision (明确失败, high confidence, overall more than 5 below threshold) — OR 人机复核 only if scored borderline within ±5

## Expected Non-Findings
The agent MUST NOT:
- Report this as an anti-ai defect (no tell-words / fatigue narration are present; the flaw is a resonance 欠交付, not an AI tell). Misclassifying it as anti-ai is a kill switch.
- Penalize 读者回报 purely for "information is present" — the information IS present; the defect is the missing emotional landing, not missing data.
- Report a clean PASS / 放行 on the climax chapter.

## Expected Output Structure
- 共鸣评分报告 with all 4 dimensions scored anchor-first against the calibration anchors
- 评分明细 table with 情感落地 score < 20 and line-number + quoted-excerpt evidence naming the missing emotional beat
- 校准门判定: 情感落地 < 子地板 20 ✗ and overall < 阈值 75 ✗ → 阻断
- §5.4 routing verdict (chapter-revision or 人机复核)
- 共鸣短板 → `truth/audit_drift.md` entry pointing at the flattened climax
