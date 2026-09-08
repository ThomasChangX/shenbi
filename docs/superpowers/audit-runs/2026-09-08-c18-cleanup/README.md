# C18 清洗 run 记录（SDD #56 · 2026-09-08）

spec: `docs/superpowers/specs/2026-08-16-audit-artifact-contamination-fix.md` · plan: `docs/superpowers/plans/2026-09-08-spec56-c18-artifact-contamination.md`

## 目录内容

- `dispatch-verification.md` — T1 派发层验证结论（argv 断言 + 嵌埋核实 + zcode deviation）
- `baseline-report.json` — T3 lint 全树基线（清洗前计数：meta 52 / manual 4 / timestamp 66（15 组 63 文件 + 3 同文件倒挂）/ state 117）
- `recalc_resonance_deterministic.py` — T4 ch49/51 确定性层重算 oneoff（dry-run 默认）
- `old-values-archive.md` — T4 手算旧值留档（重算对照表）
- `backfill_audit_reports.py` / `regen_truth_index.py` — T6 oneoff（pending Task 6）
- `DEBUG_USE_MANUAL_CREATE.md` — T7 自 xinghuo-ranqiong/ 移入的历史 DEBUG 手册（pending Task 7）

## T4 补充说明

- lint 7 模式族为 spec 锚定（F1171 定义，基线 52）；英文聊天体变体（Here's/deliver/needs to go into/write access 等）与 heredoc 交付块超出该族，已在 T4 定点清除（13 文件），以本轮 grep 证据留档，不扩 lint 模式族（保 AC1 基线对照完整性）
