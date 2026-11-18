# Gates

Shenbi uses 11 validation gates to enforce pipeline integrity (G0-G7 plus G_TRANSITION/G_DISPATCH/G_RECONCILE):

| Gate | Purpose |
|------|---------|
| G0 | Round creation environment check |
| G1 | Pre-dispatch input validation |
| G2 | Output file validation |
| G3 | Scoring readiness |
| G4 | Skill-specific quality checks |
| G5 | T2 phase boundary |
| G6 | T3 pipeline integrity |
| G7 | Post-round audit |

Run via `just gate <Gx> [args]` or `uv run shenbi-validate <Gx>`.

## Result schema: sampling disclosure (C29)

Gate result JSON (`GateResult`, `src/shenbi/status.py`) carries two optional
disclosure keys introduced by C29 (spec #43):

- `checks[].input_sampled: true` — attached by a check when any of its input
  text was read as a clipped prefix (`clip_with_disclosure()` in
  `gates/shared.py`, replaces raw `[:3000]`/`[:5000]` slicing).
- `sampling_disclosed: "n/m checks ran on sampled input"` — top-level summary
  aggregated by `gate_G5`/`gate_G6`, persisted in gate-marker JSON by
  `write_gate_marker` and surfaced in the G7.13 re-run note.

Both keys are additive (`GateResult` is `total=False`); consumers reading only
`status`/`checks` are unaffected. Count-based sampling caps
(`files_sampled`/`findings_capped`) are documented in
[_sampling-policy.md](sampling-policy.md).

## G1.4 `.bak` 写豁免裁决（spec #48 C34 / F412）

G1.4 对 in-place 修改型 skill（`BACKUP_SKILLS` 名单）在 dispatch 前创建源文件 `.bak` 备份。这是 gate checker「纯验证无副作用」规则的**唯一成文豁免**：

- **豁免范围**：仅 G1.4 的幂等备份写（`.bak` 已存在即跳过，不重写）；不含其他任何写。
- **裁决（Option B，2026-09-07）**：保留 checker 内写而非移至 dispatcher 预阶段（Option A）。理由：G2.11 truth-diff 的 `.bak` 读方契约（`bak_path`，gates/shared.py）与 dispatcher 失败恢复路径已依赖「G1 运行时 .bak 已存在」时序；Option A 需迁移 executor run_g1 subprocess 接线 + G1.4 SKIP 分支 + G2.11 读方三处，破坏面大于收益，且引入「G1 未跑但 G2.11 期望 .bak」新时序洞。
- **锚定**：`.bak` 锚定 = 源文件同目录（见 [paths.md](paths.md)）。

## spec #80 前向门回放口径

manifest 门行对**已生成章不回放**（spec #83 T7 文档化）：`pipeline-manifest.json` 的 G4 门记录为 latest-wins 面——历史失败重试记录被最新结果覆盖，对已生成章节回放历史门行既不可达也不构成验收面。卷一 10-29 章的记录剥离即此口径；卷二起 regen-accept 判据 2b 按本口径执行（读最新记录，不回放重放历史）。

### g4_cross_chapter —— 非注册表门（spec #89 T5）

`g4_cross_chapter`（src/shenbi/gates/g4/cross_chapter.py）**不在 build_checkers 注册表**：
pipeline 于 chapter_loop.py 直连调用（需跨章上下文装配——上一章内容/前窗 plan——
注册表的 per-round 单文件形态装不下）。注册表口径的「哪些门存在」不包含它；
新增跨章门须同样走直连+本文档登记，不得默默进注册表。

## 散文↔门裕度（spec #93 T2）

散文（SKILL.md 教学面）与门（G4 执行面）的阈值**有意不同**——提示比门严是 prompt 工程设计：
自动化生成文本在对应指标上天然偏多，门给裕度防重派风暴，散文保持高压引导模型自律。
改任一侧前先读本节；把散文「对齐」到门值=改变 LLM 行为，属 prompt 变更须走内容批。

- **转折词**：散文预算 1/3000（chapter-drafting SKILL 字面 ×5 :92-94/:108/:185＋公式形态 [字数/3000] :174）
  / 门限 1/1000（chapter_drafting.py `max(5, wc//1000)`，:931 注释自认 relaxed for automated gen）——3× 裕度。
- **疲劳词**：散文面=禁用词出现即报错＋慎用词每章 >3 报警（genre-config SKILL.md 疲劳词管理节）
  / 门面=禁用∪慎用命中 >8 FAIL（chapter_drafting.py `_check_fatigue`，spec #93 T6 接线后门实读
  genre-config 词表）——门对禁用词同样给自动化裕度（散文零容忍 vs 门 ≤8），与转折词同一裕度模式。
