# Expected Output: shenbi-review-arc-payoff Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | 敷衍兑现 / 旁白交代式兑现 — hook-007 (老周黑石饼的真正用途), the arc's signature surprising+earned reveal, is resolved by a single旁白交代 line ("那半块黑石饼老周临死前给的，原来竟是灵能催化剂，这件事林烽后来才知道") instead of a discovery scene; it is neither surprising (the "催化剂" label is pasted on, no prior detail recombines) nor earned (no scene, no action, no cognitive reversal). A surprising+earned payoff would dramatize the discovery so prior clues click into place. | BLOCKING | volume climax, the hook-007 payoff narration line |

## Expected Scoring Effect
- 伏笔兑现质量 < 15 (breaches the §6.4 single dimension sub-floor)
- §6.4 gate → 阻断 (伏笔兑现质量 < 15 triggers 阻断 regardless of overall)
- 处方 must point at the specific旁白交代 line and name what a surprising+earned payoff would require

## Expected Non-Findings
The agent MUST NOT:
- Report this as an anti-ai defect (no tell-words / fatigue narration are present; the flaw is payoff quality, not AI tell). Misclassifying it as anti-ai is a kill switch.
- Report this as a foreshadowing state-machine failure — the hook IS RESOLVED; the defect is the **quality** of the resolution (爽不爽/挣没挣来), not the tracking status.
- Let overall ≥80 mask the sub-floor breach — the §6.4 gate is binary on BOTH conditions; 伏笔兑现质量 < 15 alone is 阻断.
- Report a clean 放行 on the volume.

## Expected Output Structure
- 弧级正向质量门报告 with all 5 dimensions scored anchor-first against the calibration anchors
- 评分明细 table with 伏笔兑现质量 score < 15 and line-number + quoted-excerpt evidence naming the旁白交代 payoff
- 门判定: 伏笔兑现质量 < 子地板 15 ✗ → 阻断 (binary, regardless of overall)
- 处方 pointing at the specific旁白交代 line + what a surprising+earned payoff requires
- 跨卷短板 → `truth/audit_drift.md` entry pointing at the perfunctory payoff
