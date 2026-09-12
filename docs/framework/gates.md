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
