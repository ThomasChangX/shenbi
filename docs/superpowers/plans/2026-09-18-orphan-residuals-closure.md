# 孤儿残留收口（spec #67）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 关闭 spec #67 三面——F519/F513 legacy 路由快照根改 round_dir、F311 curated 层 remove（22 处/6 文件全清单）、T1108 不做裁决落 ledger。

**Architecture:** 面 1 是行为修复（快照观察根从框架仓库根改为派发写树）；面 2 是死输出面移除（模块删除 + 唯一存活符号 ENDING_PATTERNS 迁移）；面 3 是纯 docs 裁决回写。三面互不依赖代码层耦合，但共享单 PR 交付。

**Tech Stack:** Python 3.11+ / pytest / just（CI 同构验证）/ shenbi-sync-contracts（deps.json 生成）。

## Global Constraints

- SDD 执行上下文：本 plan 由 SDD 阶段 6 执行——**三个 task 全部为 infra**（executor 属多文件改动；chapter_loop/pipeline-cli 属 `src/shenbi/pipeline/` infra 面）→ 协调者亲自实现，不派 implementer；每 task commit 后必须产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 全量重审），无 audit-T 不得开始下一 task。
- 禁真实 LLM dispatch（核心原则 8）：所有验证走 pytest/fixtures/只读 CLI；测试仅允许 monkeypatch **函数 seam**（`dispatch`/`derive_output_files`），禁 monkeypatch 模块常量（本 plan 的面 1 即在消除该反模式）。
- pathspec commit：`git add` 显式列文件，禁 `git add -A`。
- 验证命令一律 `uv run` / `just`（与 CI `uv run --frozen` 同构）。
- 生成物禁手改：`tests/tiers/deps.json` 双机制——`expected_outputs` 面只经 `just generate`；`_tool_hashes` 面只经 `bash tests/lock-tool-hashes.sh`（重哈希全 src/shenbi 树，G0/lint_registry_reconcile R3 以此为准——**每个改了 src/ 的 task commit 都必须随之刷新并提交**，否则中间 commit 非绿）。
- conventional commits：`fix:` 面 1 / `refactor:` 面 2 / `docs:` 面 3。

## 复杂度与测试声明

- Task 1: **infra** · test_kind: `tdd_red_green`（行为变更：快照根）· 层级 T1（tests/unit/dispatcher + tests/unit/audit）· fixtures: 无需 tests/fixtures 产物（tmp_path 构造 + 真实契约 skill 名 `shenbi-genre-config`/`shenbi-state-settling`，与既有测试同形）
- Task 2: **infra** · test_kind: `regression_guard`（删除面：存留套件全绿即守卫）· 层级 T1（tests/unit/pipeline + records + gates）
- Task 3: **infra-docs** · test_kind: N/A（ledger 回写）· 验证 = `just audit-lint`
- G3.4 独立评分：**N/A**——本 spec 无生成物评分场景（全部确定性测试）。
- F947 规则：无验收依赖真实 dispatch——全部离线可复验 ✓。

---

## 验收覆盖表（spec `**验收：**` → task → 命令）

| spec 验收 | task | 验证命令 |
|---|---|---|
| 面1 pytest dispatcher+audit 绿 | T1 | `uv run pytest tests/unit/dispatcher/ tests/unit/audit/ -q` |
| 面1 executor `PROJECT_DIR` 零命中 | T1 | `grep -rn "PROJECT_DIR" src/shenbi/dispatcher/executor.py` |
| 面1 测试掩蔽零命中 | T1 | `grep -rn "PROJECT_DIR" tests/unit/dispatcher/ tests/unit/audit/` |
| 面1 dispatch_helper 孪生残留零命中 | T1 | `grep -rn "framework repo root\|F519" src/shenbi/pipeline/dispatch_helper.py` |
| 面1 无掩蔽回归断言 | T1 | 新测试 `test_snapshot_root_is_round_dir_without_any_constant_mask` |
| 面1/面2 `just check` 全绿 | T3（Step 3 终验） | `just check` |
| 面2 `chapter-.*-curated` 零命中 | T2 | `grep -rn "chapter-.*-curated" src/` |
| 面2 `curation` 零命中（22/6 全灭） | T2 | `grep -rn "curation" src/` |
| 面2 g4 `curates` 零命中 | T2 | `grep -n "curates" src/shenbi/gates/g4/context_composing.py` |
| 面2 pyproject 零命中 | T2 | `grep -n "context_curation" pyproject.toml` |
| 面2 ENDING_PATTERNS 定义+消费 | T2 | `grep -n "ENDING_PATTERNS" src/shenbi/pipeline/review_checklist.py` |
| 面2 pytest 三域绿 | T2 | `uv run pytest tests/unit/pipeline/ tests/unit/records/ tests/unit/gates/ -q` |
| 面2 `just generate` 幂等 | T2 | `just generate && git diff --exit-code tests/tiers/deps.json`（generate 后 diff 为空） |
| 面3 T1108 ledger 关闭 | T3 | ledger 行目检 + `just audit-lint` |
| 边界 ledger 四行回写 | T3 | 同上 |

---

### Task 1: F519/F513 · legacy 路由快照根 = round_dir

**Files:**
- Modify: `src/shenbi/dispatcher/executor.py`（:31-32 常量删除；:133-150 run_g2 argv 去 PROJECT_DIR；:309/:334 快照根；:287-289 docstring）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:2661-2662`（孪生 docstring）
- Modify: `tests/unit/dispatcher/test_executor_audit.py`（揭 :18/:42 掩蔽 + 新回归测试）
- Modify: `tests/unit/audit/test_write_audit_drift_attribution.py`（揭 :65 掩蔽 + fixture 重排）

**Interfaces:**
- Consumes: `snapshot_tree(root: Path, watch: list[str]) -> dict[str, str | None]`（语义不变，仅换根）；`gate_G2(files, ftype, rd, pd=None)`（第 5 参省略合法，gates/cli.py:106 `pd = arg(3, None)`）
- Produces: `dispatch_with_write_audit(skill, test_type, round_dir, prompt) -> int` 签名不变、快照根 = round_dir；executor 模块不再导出 `PROJECT_DIR`/`REPO_ROOT`（全仓零外部 import，已核验）

- [ ] **Step 1: 写失败回归测试**（追加到 `tests/unit/dispatcher/test_executor_audit.py` 末尾）

```python
def test_snapshot_root_is_round_dir_without_any_constant_mask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F519/F513 回归（spec #67 面 1）：不 monkeypatch 任何模块常量，快照根必须是 round_dir。

    修复前：快照根 = 框架仓库根（PROJECT_DIR = REPO_ROOT），round_dir 树内的
    越权写不被观察 → rc=0 假阴性。修复后：rc=2 GATE_FAIL。
    """
    monkeypatch.setattr(
        ex,
        "derive_output_files",
        lambda s, chapter=None, round_dir=None, ctx=None: ["genre-config.json"],
    )
    cfg = tmp_path / "genre-config.json"
    cfg.write_text(json.dumps(_cfg()), encoding="utf-8")

    def forbidden(skill: str, tt: str, rd: Path, prompt: str) -> int:
        d = json.loads(cfg.read_text(encoding="utf-8"))
        d["title"] = "x"  # genre-config 真实 9 键之外 → 越权
        cfg.write_text(json.dumps(d), encoding="utf-8")
        return 0

    monkeypatch.setattr(ex, "dispatch", forbidden)
    rc = ex.dispatch_with_write_audit("shenbi-genre-config", "generative", tmp_path, "p")
    assert rc == 2  # round_dir 树内的越权写必须被观察 → GATE_FAIL
```

- [ ] **Step 2: 跑新测试确认失败**

Run: `uv run pytest tests/unit/dispatcher/test_executor_audit.py::test_snapshot_root_is_round_dir_without_any_constant_mask -v`
Expected: **FAIL** — `assert 0 == 2`（越权写发生在 tmp_path=round_dir，但快照根是框架仓库根 → 零观察 → rc=0）

- [ ] **Step 3: 实施 executor.py 修改**

3a. 删除常量块（:30-32）：
```python
# 删除以下两行（保留前后空行结构）：
REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = REPO_ROOT
```

3b. `run_g2` argv 去掉 `str(PROJECT_DIR),`（原 :140-152）：
```python
    return run_subprocess_json(
        [
            "uv",
            "run",
            "shenbi-validate",
            "G2",
            output_files,
            file_type,
            str(round_dir),
        ]
    )
```
（G2 CLI 第 5 参省略 → `pd=None` → `_is_important_chapter` 恒 False——与现行 framework-根行为精确等价；重要章激活为独立产品决策，spec #67 §1 已 fence。）

3c. 快照根（原 :309/:334）：
```python
    pre = snapshot_tree(round_dir, watch)
```
```python
            post = snapshot_tree(round_dir, watch)
```

3d. docstring 尾部**整句替换**（旧句跨 :287-289，新句如下）：

旧（逐字）：
```
Snapshot root is PROJECT_DIR (framework
repo root — F519); the API/IDE wrapper roots at the pipeline project dir
where those routes actually write.
```
新：
```
Snapshot root is round_dir (the dispatched write
tree — F519/F513 fixed by spec #67); codex executes with ``-C round_dir``,
so skill writes land there. The API/IDE wrapper roots at the pipeline
project dir with the same write-tree semantics.
```

- [ ] **Step 4: 跑新测试确认通过**

Run: `uv run pytest tests/unit/dispatcher/test_executor_audit.py::test_snapshot_root_is_round_dir_without_any_constant_mask -v`
Expected: **PASS**

- [ ] **Step 5: 揭除既有掩蔽**

5a. `tests/unit/dispatcher/test_executor_audit.py`：删除 `test_audit_passes_on_allowed_genre_key_change`（:18）与 `test_audit_blocks_on_undeclared_genre_key`（:42）中的行：
```python
    monkeypatch.setattr(ex, "PROJECT_DIR", tmp_path)  # type: ignore[attr-defined]
```
（两测试 round_dir 实参已是 tmp_path，揭除后语义不变。）

5b. `tests/unit/audit/test_write_audit_drift_attribution.py` `test_zero_write_dispatch_returns_rc0`（:51-80）重排 fixture——被观察文件移入派发 round_dir 树：
```python
    from shenbi.dispatcher import executor

    round_dir = tmp_path / "round"
    (round_dir / "truth").mkdir(parents=True)
    (round_dir / "truth" / "pending_hooks.md").write_text(_DRIFTED, encoding="utf-8")

    def _zero_write_dispatch(*_args: object, **_kwargs: object) -> int:
        return 0  # dispatch 成功且不写任何文件 → pre == post

    monkeypatch.setattr(executor, "dispatch", _zero_write_dispatch)

    rc = executor.dispatch_with_write_audit(
        "shenbi-state-settling", "generative", round_dir, "no chapter marker"
    )
```
（删除 `root = tmp_path / "project"` 两树分离与 `monkeypatch.setattr(executor, "PROJECT_DIR", root)`；断言块不变。）

- [ ] **Step 6: dispatch_helper 孪生 docstring**（句跨 :2661-2662）

旧（逐字）：
```
(the legacy route snapshots the framework repo root instead,
F519, out of scope here)
```
新：
```
(the legacy CLI route snapshots its ``round_dir`` —
the same write-tree semantics, F519/F513 fixed by spec #67)
```

- [ ] **Step 7: 刷新 _tool_hashes（deps.json）**

```bash
bash tests/lock-tool-hashes.sh
git diff --stat tests/tiers/deps.json    # 期待恰 2 行 hash 变化（executor.py + dispatch_helper.py）
```

- [ ] **Step 8: 验收命令全跑**

```bash
uv run pytest tests/unit/dispatcher/ tests/unit/audit/ -q          # Expected: all passed
grep -rn "PROJECT_DIR" src/shenbi/dispatcher/executor.py           # Expected: 零输出
grep -rn "PROJECT_DIR" tests/unit/dispatcher/ tests/unit/audit/    # Expected: 零输出
grep -rn "framework repo root\|F519" src/shenbi/pipeline/dispatch_helper.py  # Expected: 零输出
```

- [ ] **Step 9: Commit**（显式列文件，含 deps.json）

```bash
git add src/shenbi/dispatcher/executor.py src/shenbi/pipeline/dispatch_helper.py tests/unit/dispatcher/test_executor_audit.py tests/unit/audit/test_write_audit_drift_attribution.py tests/tiers/deps.json
git commit -m "fix(dispatcher): F519/F513 legacy route snapshot root = round_dir (spec #67 face 1)"
```

- [ ] **Step 10: audit_loop**（scope=本 task 4 文件，sha_range=(上 commit, 本 commit)）→ `.superpowers/sdd/audit-T1.md`

---

### Task 2: F311 · curated 层 remove（22 处/6 文件）

**Files:**
- Delete: `src/shenbi/pipeline/context_curation.py`
- Modify: `src/shenbi/pipeline/chapter_loop.py`（:162、:282 注释；:1547-1576 `_run_context_curation`；:2988-2989 调用；:3001-3003 注释+事件）
- Modify: `src/shenbi/pipeline/cli.py`（:1042/:1046 docstring；:1069-1070 import；:1077-1080 写入）
- Modify: `src/shenbi/pipeline/review_checklist.py`（:25 import→本地定义；:470/:474 注释；`__all__` 补列）
- Modify: `src/shenbi/pipeline/truth_readers.py:33`、`src/shenbi/records/writer.py:5-7`、`src/shenbi/gates/g4/context_composing.py:77-78`（docstring/注释）
- Modify: `pyproject.toml:150`（BLE001 豁免行删除）
- Delete: `tests/unit/pipeline/test_context_curation.py`
- Modify: `tests/unit/pipeline/test_context_persistence.py`（删 2 个 curated 测试）、`tests/unit/pipeline/test_truth_readers.py:114-115`（docstring）
- 生成物: `tests/tiers/deps.json`（仅经 `just generate`）

**Interfaces:**
- Produces: `review_checklist.ENDING_PATTERNS: dict[str, str]`（本地定义，字典逐字保留——值为调参正则，`_get_recent_ending_types` 测试行为锚定）；`read_pending_hooks` 消费者 = G6.7/truth_index/chapter_loop 三方（不变）；`context_curation` 模块从导入面消失
- Consumes: 无新依赖

- [ ] **Step 1: chapter_loop.py 六处编辑**

1a. :162 注释：
```python
    # Step 3: Context prepare (deterministic context-assemble)
```
1b. :282 注释：
```python
        # context assembly merged into one deterministic step (spec #67)
```
1c. 删除 `_run_context_curation` 整函数（:1547-1576，从 `def _run_context_curation` 到 post-check `log.error` 块尾）。
1d. 调用点（:2986-2989）：
```python
    if step.calls_context_assembly:
        _run_context_assembly(project_dir, chapter)
```
1e. :3001-3003：
```python
    # context-composing replaced by deterministic assembly in step 4 (spec #67)
    if step.skill == "shenbi-context-composing":
        log.info("context_composing_replaced_by_assembly", chapter=chapter)
```
（跳过分支保留——skill 仍在 skills/ 注册、步骤需短路标记 done；事件名全仓零其他消费者，已核验。）

- [ ] **Step 2: pipeline/cli.py backfill 面**

2a. docstring（:1042-1047）：
```python
    """Re-run deterministic context assembly for a chapter range.

    These are deterministic Python functions and can be re-executed safely to
    close coverage gaps for already-generated chapters. Uses the real
    assemble_context(project_dir, plan_path) / write_context_file signatures
    (spec §3.1 backfill; curated layer removed by spec #67).
    """
```
2b. `_backfill_range` 头部（:1068-1070）删除两行 import：
```python
    from shenbi.pipeline.context_curation import curate_context
    from shenbi.safe_write import safe_write
```
（`write_context_file` 内部自带 safe_write；二者仅 curated 写使用——F401 预防。）
2c. 循环体（:1076-1080）：
```python
            pkg = assemble_context(project_path, plan_path)
            write_context_file(project_path, ch, pkg)  # safe_write inside
            echo(f"  Backfilled context for chapter {ch}")
```

- [ ] **Step 3: review_checklist.py 本地化 ENDING_PATTERNS**

3a. 删除 :25 import 行 `from shenbi.pipeline.context_curation import ENDING_PATTERNS`，在 imports 之后加（逐字复制自 context_curation.py:51-58）：
```python
# Ending diversity classification patterns (§2.1; spec #67: localized here —
# sole surviving consumer after the curated-layer removal).
ENDING_PATTERNS: dict[str, str] = {
    "cliffhanger": r"(突然|猛然|就在此时|一声|眼前一|[？?]$)",
    "hook": r"(但|然而|却|不过|还[有存]|等待|尚未|不知)",
    "resolution": r"(终于|最后|就这样|[。！]$)",
    "reflection": r"(回想|想起|原来|或许|也许|大概)",
    "transition": r"(第二天|次日|翌日|接下来|之后|随后)",
}
```
3b. :470 `Classifies endings using regex patterns (same as context_curation.py).` → `Classifies endings using regex patterns (ENDING_PATTERNS, defined above).`
3c. :474 `# Ending classification patterns (imported from context_curation.py).` → `# Ending classification patterns (ENDING_PATTERNS, defined above).`
3d. `__all__` 在 `"DYNAMIC_FIELDS",` 后插入 `"ENDING_PATTERNS",`。

- [ ] **Step 4: 三处 docstring/注释 + pyproject**

4a. `truth_readers.py:33`：
```python
All downstream readers (gates/g6 G6.7, truth_index body source,
chapter_loop conditional-resolve) MUST go through :func:`read_pending_hooks` —
no second parser.
```
4b. `records/writer.py:5-7` 首条读者列举：
```python
  1. YAML frontmatter ``hooks`` list — read by pipeline/review_checklist.py,
     truth_readers.read_pending_hooks (via chapter_loop._check_conditional_resolve);
```
4c. `gates/g4/context_composing.py:77-78`：`In pipeline mode, context-composing curates the pre-assembled output` → `In pipeline mode, context-composing consumes the pre-assembled output`
4d. `pyproject.toml` 删除行：`"src/shenbi/pipeline/context_curation.py" = ["BLE001"],`

- [ ] **Step 5: 测试面**

5a. 删除 `tests/unit/pipeline/test_context_curation.py` 整文件。
5b. `test_context_persistence.py` 删除 `test_curated_context_written_on_curation` 与 `test_curated_context_uses_safe_write` 两函数（`tempfile`/`patch` 仍被 assembly 测试使用，import 保留）。
5c. `test_truth_readers.py:114-115` docstring：`All three consumers (context_curation / G6.7 / truth_index)` → `All consumers (G6.7 / truth_index / chapter_loop)`

- [ ] **Step 6: 删除模块 + 双机制刷新生成物**

```bash
git rm src/shenbi/pipeline/context_curation.py
bash tests/lock-tool-hashes.sh
just generate
git diff --stat tests/tiers/deps.json
# 期待：_tool_hashes 面 ~7 行 hash 更新 + context_curation.py 条目移除；
# expected_outputs 面零变化（本 task 不改 SKILL 契约）
```

- [ ] **Step 7: 验收命令全跑**

```bash
uv run pytest tests/unit/pipeline/ tests/unit/records/ tests/unit/gates/ -q   # Expected: all passed
grep -rn "chapter-.*-curated" src/                # Expected: 零输出
grep -rn "curation" src/                          # Expected: 零输出
grep -n "curates" src/shenbi/gates/g4/context_composing.py  # Expected: 零输出
grep -n "context_curation" pyproject.toml         # Expected: 零输出
grep -n "ENDING_PATTERNS" src/shenbi/pipeline/review_checklist.py  # Expected: 定义+消费 ≥2 行
bash tests/lock-tool-hashes.sh && git diff --exit-code tests/tiers/deps.json && echo HASHES-CURRENT
just generate && git diff --exit-code tests/tiers/deps.json && echo GEN-IDEMPOTENT
```

- [ ] **Step 8: Commit**（显式列文件——git rm 已暂存模块删除，此处补列其余）

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/cli.py src/shenbi/pipeline/review_checklist.py src/shenbi/pipeline/truth_readers.py src/shenbi/records/writer.py src/shenbi/gates/g4/context_composing.py pyproject.toml tests/unit/pipeline/test_context_persistence.py tests/unit/pipeline/test_truth_readers.py tests/tiers/deps.json
git commit -m "refactor(pipeline): remove zero-consumer curated layer (F311, spec #67 face 2) — ENDING_PATTERNS relocated to review_checklist"
```
（test_context_curation.py 的删除由 `git rm` 暂存——注意对**已 tracked 文件**的删除用 `git rm tests/unit/pipeline/test_context_curation.py`。）

- [ ] **Step 9: audit_loop**（scope=本 task 改动文件集，sha_range=(上 commit, 本 commit)）→ `.superpowers/sdd/audit-T2.md`

---

### Task 3: T1108 不做裁决 + ledger 四行回写

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（:75 F311、:283 F519、:669 T1108）
- Modify: `docs/superpowers/audit-runs/2026-08-14/findings-ledger.md`（:168 F513）

**Interfaces:** N/A（docs-only）

- [ ] **Step 1: 四行状态列改 closed + 注记追加**（格式对齐既有 closed 行先例 `closed (C-34 spec #48)`；注记列以 `→` 起始——lint_audit_run.py 列前缀约束）

1a. F519（08-15:283）：状态 `open` → `closed (spec #67)`；注记尾追 `→ closed (spec #67 面 1 · 2026-09-18)：legacy 路由快照根对齐 round_dir（executor PROJECT_DIR 常量删除 + run_g2 省参 + 三处测试掩蔽揭除）`
1b. F311（08-15:75）：状态 `open (P1 错位已修 PR #120 链)` → `closed (spec #67)`；注记尾追 `→ closed (spec #67 面 2 裁决 remove · 2026-09-18)：curated 层零消费者——context_curation 模块删除、ENDING_PATTERNS 迁 review_checklist；P 分层/结局多样性/钩子债三增量均已有更精准交付面`
1c. T1108（08-15:669）：状态 `open (移交：离线可执行模式设计裁决)` → `closed (spec #67 裁决：不做)`；注记尾追 `→ closed (spec #67 面 3 裁决不做 · 2026-09-18)：三既有离线 seam（dispatch 边界 mock / trace replay 签名链 / test_run_pipeline_smoke PATH-stub 先例）+ G3.4 独立评分不可离线满足 + stub 误用风险；复活条件：pipeline run --dry-run 产品需求成文时另立 spec`
1d. F513（08-14:168）：状态 `specced` → `closed (spec #67)`；注记尾追 `→ closed (spec #67 面 1 · 2026-09-18)：与 F519 同面同修——legacy 路由快照根 round_dir`

- [ ] **Step 2: lint 验证**

Run: `just audit-lint`
Expected: **PASS**（08-14/08-15/c18-cleanup 三 run 全绿）

- [ ] **Step 3: 全量门禁（本 plan 终验，self-contained）**

Run: `just check`
Expected: **EXIT=0**（两段 pytest + 全 lint 面 + R3 哈希一致性——T1/T2 已各自刷新 _tool_hashes，此处必须绿）

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/audit-runs/2026-08-15/findings-ledger.md docs/superpowers/audit-runs/2026-08-14/findings-ledger.md
git commit -m "docs(audit): close F519/F311/T1108/F513 ledger rows (spec #67 three-face closure)"
```

- [ ] **Step 5: audit_loop**（scope=2 ledger 文件，sha_range=(上 commit, 本 commit)）→ `.superpowers/sdd/audit-T3.md`

---

## Self-Review 记录

1. **Spec coverage**：面 1（Task 1 全部验收项）/ 面 2（Task 2 全清单 22 处映射）/ 面 3 + 边界 ledger 回写（Task 3）——spec 三面 + 边界节全覆盖；spec 头 Status/INDEX 更新属 SDD 归档动作（阶段 12），不在本 plan。
2. **Placeholder scan**：无 TBD/TODO；所有代码步骤含完整代码；所有命令含期望输出。
3. **Type consistency**：`dispatch_with_write_audit` 签名不变；`ENDING_PATTERNS: dict[str, str]` 类型随迁；`gate_G2` 第 5 参省略与 cli.py `arg(3, None)` 一致。
4. **Plan 审查轮 1 修正（2026-09-18）**：deps.json 双机制（lock-tool-hashes.sh 刷 _tool_hashes——T1/T2 各自随 commit 刷新；just generate 管 expected_outputs）；T1 Step 3d 改整句替换（旧句 :287-289 逐字）；T2 Step 8 显式列文件；T3 增 Step 3 `just check` 终验；引用行号校准（:31-32/:133-150/:2661-2662）。
