> **Date:** 2026-08-16 | **Status:** Done (PR #117 · Revised 2026-08-31 — narrowed to live faces) | **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C3，21 条）| **代表 finding:** F360 | **严重度上限:** P0（F360/F868/F1101）| **涉及文件面:** src/shenbi/pipeline/truth_io.py（upsert 原语）、dispatch_helper 写路径、chapter_loop/staging 提交路由、skill_utils/（hook_planting、compute_drift）、约 20 个 append_dedup 技能 SKILL.md

# truth 追加写路径接线（audit-truth-upsert-wiring）— Revised 2026-08-31

## 修订说明

原 spec 的 T1-T6 主干已由 **PR #43**（fix/audit-c32-c3-batch2，2026-08-17）全套交付：T1 原语修复（ef953007/0abc15f5/552c558d：结构坍缩、CJK 键整格取值、fail-loud、replace 渲染）、T2 派发路由（c1689032 `_route_append_dedup_write` 键控合入）、T4 声明对账（c112a95a）、T5（5ce1a8e3 drift-guidance 改 create_or_overwrite）、T6 集成护栏（3cbb7240）。T3 特修面大部由后续交付覆盖：staging 双写者 lost-update → SDD #21 R3（PR #88 ec23565e chained merge base）；F1101 修订禁写 → Spec 2（chapter-revision 现 `merge_prose` + `-pre-rev` 备份）；resonance 键格式漂移 → SDD #21 R1（裸 `{N}` 键统一）；审计聚合 → PR #60。

本修订将 spec 缩窄至 2026-08-31 在 main HEAD 实读确认的存活面 R1-R3。

## 存活面（全部有 file:line 实证）

### R1 · staging 写审计盲区（P0，T3 的 PR#43-Copilot 输入，从未实施）

`_with_write_audit`（`src/shenbi/pipeline/dispatch_helper.py:2118`）的 watch 面来自 `derive_output_files`（`src/shenbi/audit/_shared.py:38-59`）——**无前缀契约路径**；而 `uses_staging=True` 的派发（state-settling、foreshadowing-lifecycle 等 checkpoint-gated 技能）实际写 `staging/<contract-path>`（`dispatch_helper.py:727-728`）。结果：pre==post 快照无变化 → Tier B 写审计与账本对 staged 写**整体不可见**（含 staging 内越权写），且记出 `blocked:false` 的"空过"记录（audit theater）。`grep -rn staging src/shenbi/audit/` 零命中——归一化从未落地。

**修复方向**：`uses_staging` 时把 watch 面扩为声明 relpath + `staging/<relpath>` 双路径快照，并在 `audit_writes` 比对前将 staged 快照键归一化回声明 relpath（去 `staging/` 前缀），使 ownership + 声明面匹配对 staged 写仍生效。

### R2 · F868 volume-consolidation 盲覆写（P0，数据丢失级，原 spec 三 P0 之一仍存活）

`skills/shenbi-volume-consolidation/SKILL.md`：reads（:7-10）**不含** `truth/volume_summaries.md`，writes 却整文件 `create_or_overwrite` 该文件（:12-13），正文指令又称「追加到 volume_summaries.md」（:72）——三重矛盾。实际行为：看不到现状的 LLM 整文件重建，旧卷摘要每卷丢失（F868 原始主张逐字成立）。

**修复方向**：`truth/volume_summaries.md` 进 reads；写语义与正文指令一致化——要么声明 `append_dedup` + `key: volume`（走既有 T2 路由），要么正文改为「读取既有文件、合并本卷行后输出全量」并保留 create_or_overwrite。实施时按文件实际表格结构定键轴，与 G4/lint 拦截面联动校验。

### R3 · append_dedup 声明形态漂移（F814 残留 + F840 功能性键错配）

- **F814 残留（规范级）**：`skills/shenbi-score-volume/SKILL.md:16-19` 的 `append_dedup` 条目声明在 `writes:` 段且 `updates:` 为空。`write_semantics` 构建遍历 writes+updates 双段（`src/shenbi/contracts/legacy.py:178-202`），功能路由不受影响——纯形态漂移，挪入 `updates:` 即可。
- **F840（P2，功能性）**：`skills/shenbi-review-arc-payoff/SKILL.md:28-29` 对 `truth/arc_payoff_trend.md` 声明 `key: chapter`，但该文件行模板首列为 `volume`（:151-153「一行一卷」）。append_dedup 路由按首格 key 合入（`dispatch_helper.py:1383-1387`），卷键文件配 `key: chapter` 是键轴错配——声明键改 `volume`（findings-ledger 该条状态仍 open）。

## 修复目标

1. staged 写纳入 Tier B 审计视野（R1），空过账本消除。
2. volume-consolidation 不再盲覆写卷摘要（R2），声明/正文/模式三面一致。
3. append_dedup 声明形态全仓同构（R3）。

## 验收标准

1. R1 新增单测：staging 派发写 `staging/truth/x.md` 后，审计账本记录的变更面含该文件（归一化键 `truth/x.md`），且无 `blocked:false` 空过记录；staging 内越权写在被声明 glob 覆盖时可被审计捕获（watch 面为模式驱动，exact 路径技能的 staging 越权写不在视野——同既有 live 越权局限，不另立目标）。
2. R2：volume-consolidation 的 reads 含 `truth/volume_summaries.md` 且写模式与正文指令一致（正文四处「追加/归档」语义点全部对齐）；G4 对该技能通过。
3. R3：score-volume 的 append_dedup 条目位于 `updates:` 段；review-arc-payoff 的 `arc_payoff_trend` 声明键为 `volume`；`just check` 中 lint/G0 契约面全绿。
4. `just check` 全绿。

## 风险与回滚

- R1 改 watch 面可能让历史"静默"的 staged 越权写开始报违规——若现网技能有合法 staging 写未声明，会暴露为 CI/审计红；实施时先全量跑 staging 技能契约对账。
- R2 若选 append_dedup 路由，需 volume_summaries 生产文件（或 fixture 镜像）存在键控表行结构；无则选「读旧+全量重写」方向。
- 各面独立可回滚；R3 零行为变更。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C3（21 条，代表 F360）：F360 F814 F828 F840 F868 F869 F1101 F1104 F1105 F1175 T304 T701 T702 T703 T704 T705 T706 T707 T711 T712 T713

**处置对照（2026-08-31，阶段 3 审查复核）**：除 R1（staging 审计面）/R2（F868）/R3（F814 残留 + F840）外全部已在 main 交付（PR #43 / #88 / #60 / Spec 2 / SDD #21；F869 经抽查确认已解——state-settling 正文已统一 append_dedup 输出行指令）。
