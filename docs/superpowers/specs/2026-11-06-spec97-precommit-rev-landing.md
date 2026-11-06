# Spec #97 · pre-commit hook rev 落地链（precommit-rev-landing）：C13 理由迁移、markdown 格式化冻结单源、新规 fallout 验收

**日期**：2026-11-06 ｜ **系列**：工具链卫生批（pre-commit 修复续，PR #288 后件） ｜ **状态**：Active（r1 立项） ｜ **优先级**：🟠 P1（**死线驱动**——修复版工作流首跑 2026-11-09 02:00 UTC 周一；未清偿则 C13 守卫每周红灯拦 PR，属设计内升压）
**依赖**：**T0 前置 = PR #288（autoupdate 工作流修复：两遍幂等验证/C13 noqa 剥除守卫/归档冻结 exclude）合并**；与批次 A 无文件域冲突（只动 `.pre-commit-config.yaml`＋`pyproject.toml`＋6 个 src 站点的注释行＋2 个活 md 文件），**先于批次 A 执行**（小件+死线；不触 chapter_loop 等最热文件）。
**动机证据**（2026-11-05/06 取证，全部在盘可复现）：
①**8 周僵尸工作流根因链**（PR #288 已修）：仓库设置拒 Actions 建 PR（`can_approve_pull_request_reviews=false`，现已放行）→ 每周一 force-push 分支后建 PR 失败；且旧验证步骤 rc==1 判别力缺陷吞掉全部 local hook 失败（run 41376266687 日志：basedpyright＋9 个 lint hook 每周全 Failed 被当「autofix 正常」）。
②**回测基线 7725f002**（bot 分支，已删，证据存 PR #288 描述）：名义 autoupdate 实为 173 文件 +9215/−4865——剥 6 处 C13 noqa 理由＋重排 167 个 md（166 个 docs/superpowers/**archive**＋audit-runs 1＋skills 1）。
③**目标版本干跑**（2026-11-06，`uvx ruff@0.17.3` 于当前 main 树）：
- **format 面 169 文件**：`docs/superpowers/` 168（**archive 166**＋活 plan 1［#84 卷一清偿 plan］＋audit-runs 1）＋`skills/shenbi-review-long-span/ngram-methodology.md` 1——**PR #288 的 hook 级 exclude 已覆盖 167，活面残留仅 2 文件**；
- **lint 面 35 错**（**零 .md 命中——lint 不触 md 代码块，md 只有 format 面**）：PLR0917（too-many-positional-arguments 新规）×29＋RUF100 ×6（=②的 C13 noqa 判死：新 ruff 在这些站点不再发 BLE001，`uvx ruff@0.17.3 check` 逐点确认 unused: BLE001）＋另有 1 条 warning（`tests/unit/tools/test_release_split.py:91` noqa 指令格式非法——旧版容忍）。
④**冻结单源缺口实锤**：干跑走 pyproject 配置即报 167 个已冻文件——PR #288 的 exclude 落在 pre-commit hook 层，**直接 `ruff format` 调用面（just lint/CI/开发者手跑）不认 hook 级 exclude**；冻结必须落 `[tool.ruff]` 单源。

**触及的不变量维度**：无（工具链卫生；6 站点只动注释行不动逻辑）。

---

## 0. 站点清单（T1 施工面；行号为 2026-11-06 快照，plan 首步按符号 re-anchor）

| # | 站点 | 理由注释引用 |
|---|---|---|
| 1 | `src/shenbi/dispatcher/modes/codex.py:236`（`_run_dual_scorer_check`） | spec #39 T5 |
| 2-4 | `src/shenbi/observability/archive.py:95/:108/:296`（`bump_stats`/`_account_bytes`/`write_dispatch_archive`） | spec #81 §1 |
| 5 | `src/shenbi/observability/escape.py:74`（`update_escape_hatch_state`） | spec #81 §3 |
| 6 | `src/shenbi/phase_runner.py:111`（`_record_gate_manifest`） | spec #39 T5 |

现行治理约定（`pyproject.toml:127-130` 注释）：BLE001 全仓活跃，legacy 站点走 per-file-ignores（每条显式评审过），**spec 域站点走 inline `# noqa: BLE001` 带理由**。

## 1. 任务分解

### T0 · 前置与变更面取证

- 合并 PR #288（工作流修复；守卫/两遍验证为后续任务的执法面）；
- changelog 取证落盘（进本 spec 修订或 plan）：ruff 0.15.17→0.17.3（**BLE001 行为变化定位**——为何 §0 六站点不再触发；md 代码块 format 何时引入）、mypy 2.1.0→2.4.1、pre-commit-hooks 4.5.0→6.0.0（跨两个大版本；end-of-file-fixer/trailing-whitespace/check-added-large-files 语义变化核对，尤其 fixtures 字节等重文件豁免面）、shellcheck v0.11.0.1→v0.11.0.1-1；
- 复刻干跑基线（③数字为本 spec 锚；执行时点若有漂移按同口径重取）。

### T1 · C13 理由迁移（修 RUF100×6）

- **裁定（r1 推荐）**：六站点 noqa 判死后，理由以**纯注释保留在站点**（`except Exception:  # C13 allowlist: intentional broad catch, …spec #39 T5`——仅删 `noqa: BLE001` 指令本身，理由文字原样留下）；**不选** per-file-ignores 加站（理由远离站点）与保留死 noqa＋豁免 RUF100（留存永不生效的指令）；
- pyproject 治理注释同步演进：约定从「inline noqa with justification」扩写为「inline noqa（规则仍触发时）或纯注释 justification（规则已不再触发时）——理由永不离开站点」；
- 红测：`grep -rc "C13 allowlist" src/` 计数 ≥6 断言（防后续再被 autofix 静默剥除；工作流守卫为运行时防线，此为在盘防线）。

### T2 · 冻结单源与活面处置（修 format 面）

- **冻结落 `[tool.ruff]` 单源**：pyproject 增 ruff format exclude `docs/superpowers/(plans/archive|specs/archive|audit-runs)/`；**PR #288 的 pre-commit hook 级 exclude 删除**（双处必漂移，单源纪律；来源注记指向本 spec）；
- **活面 2 文件顺手格式化进本批 PR**（`plans/2026-11-01-spec84-vol1-repair-vol2-launch.md`＋`skills/shenbi-review-long-span/ngram-methodology.md`）——2 文件 diff 可人审，一次清零 format 残留面，此后周 bump PR 的 md 噪音归零；
- lint 侧**无需对称面**（③：lint 零 .md 命中）；`skills/**/*.md = ["ALL"]` per-file-ignores 仅为 lint 惯例，与 format 无关，不动。

### T3 · rev bump 落地与新规 fallout

- 四组 rev 落地（吃到干跑验证过的版本）：ruff v0.17.3 / mypy v2.4.1 / pre-commit-hooks v6.0.0 / shellcheck v0.11.0.1-1；yamllint v1.38.0 无 bump 不动；
- **PLR0917 ×29：本批不重构签名**——`lint.ignore` 挂 PLR0917 带理由注释（「29 处全仓签名重构与批次 A #87/#94 接口重构撞面，挂账批次 A 后随接口稳定再议」）；**不做**逐点 noqa（29 个站点噪音大于收益）；
- 顺手修 `tests/unit/tools/test_release_split.py:91` 非法 noqa 指令（格式化为合法 codes 列表或按需保留）；
- mypy 2.4.1 新报错面（若有）逐点清偿；`uv sync` 后 `just check` 全绿为硬门；
- **首跑验收（观察点）**：2026-11-09 02:00 UTC 修复版首跑——PR 正常开出（权限墙已拆）、两遍验证过、C13 守卫绿灯（T1 已迁移）、delete-branch 生效、PR 的 md 变更面=0。

## 2. 验收

1. `just check` 全绿（新 rev 全套：RUF100 清零、PLR0917 ignore 后零报、mypy 2.4.1 零新错）；
2. bump PR 变更面 = `.pre-commit-config.yaml`＋`pyproject.toml`＋6 站点注释行＋2 个活 md＋1 处 tests noqa 修复——**md 重排零复发（对照 7725f002 的 167 面）**；
3. `grep -rc "C13 allowlist" src/` ≥6 且 pyproject 治理注释含纯注释路径新约文；
4. 冻结单源在 pyproject（hook 级 exclude 已删）；`uvx ruff@0.17.3 format --check .` 命中 = 0（活面 2 文件已清）；
5. 首跑观察点三项落档：PR 开出/CI 绿/守卫绿灯（记录进 plan 台账或 spec 修订）。

## 3. 不做面（防过度施工）

- 不做 29 处签名重构（PLR0917 ignore 挂账批次 A 后，理由见 T3）；
- 不动 dependabot/actions 版本面（checkout@7 等为另轨机械合并，不占本 spec）；
- 不追 0.17.3/2.4.1/6.0.0 之后的更新版本（周一工作流自治跟进，本 spec 只保证吃到已验证版本）；
- 不建 md formatter 黑名单/白名单机制（exclude 一条正则已覆盖；复杂度不匹配问题规模）；
- 不动 yamllint rev、不重排 `.pre-commit-config.yaml` 结构（#92 的 justfile/lint 子配方地盘不抢）。

## 4. 与在档 spec 的关系

- **PR #288**：T0 硬前置；其 hook 级 exclude 由 T2 收敛为 pyproject 单源（来源注记回指）；
- **spec #39 T5 / #81**：§0 站点理由的规范源流——T1 是其治理约定的演进（理由锚定方式从 noqa 附带改为独立纯注释），非推翻；
- **批次 A（#86-#94）**：无文件域冲突；PLR0917 挂账回指 #87/#94 接口重构；#92 共享 pre-push/justfile 面但本 spec 不动其结构；
- **7725f002**：已删 bot 分支，作为本 spec 全程回测基线（证据面：PR #288 描述＋运行日志 41376266687＋本 spec §动机③干跑）。
