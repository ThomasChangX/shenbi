# Plan · spec #97 pre-commit hook rev 落地链（precommit-rev-landing）

**日期**：2026-11-06 ｜ **spec**：`../specs/2026-11-06-spec97-precommit-rev-landing.md` ｜ **状态**：T0-T3 施工中（r1）

## 站点 re-anchor（2026-11-06 执行时点，spec §0 快照勘误）

**站点数勘误：C13 站点实为 7 处非 6 处**——spec §0 漏了 `archive.py:195`（provenance 回退，handler 裸 `return None`）。

| # | 站点 | 0.17 判定 | 处置 |
|---|---|---|---|
| 1 | `codex.py` `_run_dual_scorer_check` except | RUF100 判死（handler 带 `log.warning(exc_info=True)`） | 迁纯注释块 |
| 2-4 | `archive.py` `bump_stats`/`_account_bytes`/`write_dispatch_archive` except | 同上 | 迁纯注释块 |
| 5 | `escape.py` `update_escape_hatch_state` except | 同上 | 迁纯注释块 |
| 6 | `phase_runner.py` `_record_gate_manifest` except | 同上 | 迁纯注释块 |
| 7 | `archive.py:195` provenance except | **仍触发 BLE001**（裸 return 无结构化日志） | **保留 noqa** |

## T0 取证结论（执行时点新增，超出 spec r1 预判）

1. **BLE001 0.17 行为变化定位**（经验性，rule doc 未明说）：结构化处理 handler（`log.warning(..., exc_info=True)`）获豁免；裸返回/无日志 handler（:195）仍报——豁免边界=「有结构化处理证据」。
2. **形态迁移偏离注记**：spec r1 写「理由文字原样留下（尾注释）」；0.17.4 格式化器对超 100 列尾注释 except 强拆 `except (\n Exception\n):` 丑形——**改用 except 上方注释块**（文字原样、站点同址、except 行干净；:296 长理由折两行）。grep 判据不变。
3. **`[tool.ruff.format] exclude` 语义**：目录模式**必须带 `/**` 后缀**（`docs/superpowers/plans/archive/**`）才命中——无后缀形式解析不报错但不生效（173 文件复现实锤）。
4. **0.17.4 vs 0.17.3 增量**（干跑对照）：+SIM102 ×1（`tools/lint_no_fs_mutation.py:147` 嵌套 if——已修为组合 elif）+py 格式化 4 文件（尾注释强制折行——注释块迁移后消解）。
5. **uv.lock 双对齐（spec 未预判的第 5 组 bump）**：justfile lint 面 `uv run ruff check .`/`uv run mypy`（:47/:49）用锁定版——**锁 ruff 0.15.17→0.17.4、mypy 2.1.0→2.4.1 必须与 hook rev 同批**，否则 T1 删 noqa 后旧锁 ruff 在 6 站点重新报 BLE001。hook rev 取锁解析版 ruff **v0.17.4**（tag 已验存在）。
6. **mypy 2.4.1**：`uv run mypy src/shenbi/` 须全绿（待 just check 终验）。

## 任务状态

| Task | 状态 | 落点 |
|---|---|---|
| T0 前置+取证 | ✅ | #288 已合并（f→squash 6924f4dc）；本文件 §T0 |
| T1 C13 迁移 | ✅ | 6 站点注释块 + pyproject 治理注释 + 红测 `tests/unit/test_c13_allowlist_rationale.py`（≥6） |
| T2 冻结单源 | ✅ | pyproject `[tool.ruff.format] exclude`（/** 形态）+ hook 级 exclude 删（换单源指针注释）+ 活面 2 md 已格式化 |
| T3 rev 落地 | ✅ | hook ×4（v0.17.4/v2.4.1/v6.0.0/v0.11.0.1-1）+ uv.lock 双对齐 + PLR0917 ignore 挂账 + tests 非法 noqa 修 |
| 首跑验收 | ✅ | 2026-11-09 run 42549398259 三指标全过（§首跑验收结果） |

## 验收对照（spec §2）

1. `just check` 全绿 —— ✅（pre-push 全量模拟 + CI #293 quality ×4 全过）
2. md 变更面 = 2（活面）非 167 —— ✅（format --check 归零）
3. `grep -rc "C13 allowlist" src/` ≥6 —— ✅（7 文件命中）
4. 冻结单源在 pyproject、hook 级已删 —— ✅
5. `ruff format --check .` 全仓 0 命中 —— ✅（1775 formatted）

## 首跑验收结果（2026-11-09，cron 观察实录）

修复版工作流首次周一运行 **run 42549398259**（2026-11-09 02:10 UTC，2m26s）——对照修复前 8 周连续 failure（各 ~1m11s）：

| 指标 | 结果 | 证据 |
|---|---|---|
| ① run success + 零 bot PR | ✅ | 15 步全 success；11-08 以来全部 PR（#310-#319）为 spec #100 人工工作流，无 bot PR——rev 已被 #293 吃掉=零变更零 PR，符合预期 |
| ② C13 守卫绿灯 | ✅ | 「Guard C13 allowlist annotations」步骤 success（迁移后六站点无 noqa 可剥，守卫空转通过） |
| ③ 分支零残留 | ✅ | `git ls-remote --heads origin` 无 pre-commit-autoupdate（零变更未建分支；delete-branch 兜底在场） |

**附带验证**：run 步骤面显示 `checkout@v7`/`setup-uv@v7` 生效（#47/#294 依赖批上线）；「two-pass idempotent」验证以完整项目环境运行（uv sync + basedpyright + 9 个 local lint hook 真实执行）——修复前 local hooks 每周全 Failed 被 rc==1 吞掉的面，首跑即真实执法。

**结论**：spec #97 全链（T0-T3+首跑验收）完结，待用户归档裁定。周 bump 管线自此进入稳态：有新 rev 时自动开 PR（CI+守卫审查），无新 rev 时零噪音。
