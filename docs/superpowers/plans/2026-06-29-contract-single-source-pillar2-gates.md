# 契约单源架构 - 支柱二（门改造）实施计划 v1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 G0–G7 门从「信任散文」改为「派生自契约层 + 单一源 + CJK 工具 + 纯函数」：阈值常量集中、`derive_file_type` 用契约 join 修复漏 resolve、G3.4 fail-closed、G6.12 改用 `cjk.find_terms`、G5/G6 顶层 `jload` 加守卫、G1/G7 删写副作用、G0 覆盖率从单一源派生。

**Architecture:** 以**新增派生函数 + 外科手术式修改门体**为主，避免重写门主体（保现有测试全绿）。新建 `src/shenbi/contracts/thresholds.py`（阈值单一源）。`derive_file_type` 改从 `load_contract`（`OutputKind`）+ `bootstrap_registry`（truth-files.yaml concepts）派生（spec New-I join 规则）。G6.12 改 import `shenbi.text.cjk.find_terms`（支柱三已落地）。G7 删写 `summary.json` 副作用，改为在返回 JSON 里带 `audit_warnings`。G1 把 `.bak` 决策抽成纯函数（写动作保留于门调用路径，因 G2.11 truth-diff 依赖 `.bak` 存在；完全迁到 dispatcher 是后续）。

**Tech Stack:** Python 3.11+，Pydantic v2.5+（已依赖），mypy strict（已 CI），pytest+hypothesis（已依赖），pathlib+json。复用已落地模块：`shenbi.contracts.registry`（`bootstrap_registry`/`load_skill_contract`）、`shenbi.text.cjk`（`find_terms`/`TermHit`）。

**关联 spec:** [../specs/2026-06-29-contract-single-source-design.md](../specs/2026-06-29-contract-single-source-design.md) v5.2 支柱二「门的阈值派生与抽取」+ 实现顺序 step 5；成功判据 5（三份门登记表从单一源派生）、判据 13。

**前置依赖:** 支柱一（`src/shenbi/contracts/` 骨架、`enums.py`、`base.py`、`registry.py`、`skills/foreshadowing_resolve.py`）与支柱三（`src/shenbi/text/cjk.py` 含 `find_terms`）均已落地，本计划直接 import。支柱四 Tier A（`trace/`、`g7_trace.audit_trace`）已落地；本计划**不**强制把 `audit_trace` 接入 `gate_G7` 主体（那是行为切换，留给后续），但 G7 写副作用删除（Task 7）为其铺路。

**v1 诚实范围声明:** 本计划实现 spec 支柱二列出的全部门改造点。**范围外**：69 技能全量迁移（支柱一续）、record parser + 判据 12 语义 round-trip（支柱四 Tier B，已落 trace 基建）、`update_progress.py` 命令迁到 trace（行为切换）、subprocess read-provenance（future work）、AST lint 强制 safe_write 唯一（支柱六）、把 `audit_trace` 接入 `gate_G7` 主体。

## Global Constraints

- Python 3.11+；pathlib + json；框架代码无 print()（用 structlog）。
- mypy strict + ruff 必须 CI 干净；函数名/参数/返回类型跨任务一致。
- **不破坏现有行为：** 现有测试集必须全绿。门体修改一律**外科手术式**：新增派生函数 / 新子检查优先；必须改门体时只改目标行。每个 Task 先写失败测试 → 跑红 → 实现 → 跑绿 → 提交。
- **覆盖率门（关键）：** `pyproject.toml`（addopts 第 322 行 `--cov=shenbi`；`[tool.coverage.report]` 第 349 行 `fail_under = 90`）使任何**单文件/子集** `uv run pytest <path>` 因覆盖率不足退出码非零。本计划所有**单文件/子集** pytest 命令必须追加 `--no-cov`（如 `uv run pytest tests/unit/gates/test_g6.py -q --no-cov`）。覆盖率门只在**全量** `uv run pytest -q` 时生效（Task 9）。下面各步为简洁省略 `--no-cov`，执行者一律按此规则补上。
- **禁止伪造测试数。** 任何回归步骤只写「现有测试集全绿 + 新增测试全绿，无 regression」，执行者以实际输出为准，绝不写具体通过数字。
- 复用已落地 API：`shenbi.text.cjk.find_terms(text: str, terms: Iterable[str]) -> list[TermHit]`（`TermHit(term,start,end)`）；`shenbi.contracts.registry.bootstrap_registry() -> dict[str,str]`（返回 truth-files.yaml `concepts` 的 `{name: kind}`）；`shenbi.contract.load_contract(skill) -> Contract`（TypedDict，含 `kind: OutputKind`/`reads`/`writes`/`updates`/`read_fields`）；`shenbi.contract.OutputKind`（StrEnum：`ARTIFACT`/`REPORT`/`EPHEMERAL`，定义在 `contract.py:34-37`）。

## 文件结构

| 文件 | 责任 | 动作 |
|---|---|---|
| `src/shenbi/contracts/thresholds.py` | 框架阈值单一源（`T1_PASS`/`T2_PASS`/`T3_PASS`/`TEST_PASS`/`CONVERGENCE`） | 新建 |
| `tests/unit/contracts/test_thresholds.py` | 阈值常量 + 门引用测试 | 新建 |
| `src/shenbi/dispatcher/executor.py` | `derive_file_type` 改契约 join 派生（修复漏 resolve） | 改 31-48 |
| `tests/unit/test_dispatcher_executor.py` | resolve → truth 新测试 | 追加 |
| `src/shenbi/gates/g3.py` | G3.4 fail-closed（无 SCORE 记录则 FAIL） | 改 144-162 |
| `tests/unit/gates/test_g3.py` | G3.4 fail-closed 新测试 | 追加 |
| `src/shenbi/gates/g6.py` | G6.12 改 `cjk.find_terms`；顶层 `jload` 加守卫 | 改 33、385-408 |
| `tests/unit/gates/test_g6.py` | 嵌入 CJK 敏感词新测试 + jload 守卫测试 | 追加 |
| `src/shenbi/gates/g5.py` | 顶层 `jload`（deps/acceptance）加守卫 | 改 34、38 |
| `tests/unit/gates/test_g5.py` | jload 守卫测试 | 追加 |
| `src/shenbi/gates/g1.py` | `.bak` 决策抽纯函数 `compute_backup_targets` + `BACKUP_SKILLS` 常量 | 改 44-97 |
| `tests/unit/gates/test_g1.py` | 纯决策函数测试 | 追加 |
| `src/shenbi/gates/g7.py` | 删写 `summary.json` 副作用；`audit_warnings` 进返回 JSON | 改 282-300 |
| `tests/unit/gates/test_g7.py` | 改 1 个断言写副作用的测试为断言返回值 | 改 429-446 |
| `src/shenbi/contracts/registry.py` | 加 `known_skill_names` 单一源 API | 改 |
| `src/shenbi/gates/g0.py` | 新增 G0.15：门登记表单一源一致性（判据 5 前置） | 改末尾 |
| `tests/unit/gates/test_g0.py` | G0.15 一致性测试 | 追加 |

---

### Task 1: thresholds.py — 门阈值单一源 + 接入 G3.2/G5.1

**Files:** Create `src/shenbi/contracts/thresholds.py`、`tests/unit/contracts/test_thresholds.py`；Modify `src/shenbi/gates/g3.py:69`、`src/shenbi/gates/g5.py:39`

**Interfaces:** Produces `T1_PASS=94`、`T2_PASS=94`、`T3_PASS=94`、`TEST_PASS=90`、`CONVERGENCE=100`（spec：≥94 tier、≥90 test、100 收敛）。Consumes 无新依赖。spec 要求「数值阈值是具名模块常量，门 import」。

**验证现状：** `g3.py:69` 为 `threshold = acceptance.get("t1", 94)`；`g5.py:39` 为 `threshold = acceptance.get("t2", 94)`。两处裸 `94` 是散落的魔法数。本任务把 fallback 常量集中，行为不变（94==T1_PASS）。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/contracts/test_thresholds.py
from __future__ import annotations

from pathlib import Path

from shenbi.contracts.thresholds import CONVERGENCE, T1_PASS, T2_PASS, T3_PASS, TEST_PASS


def test_thresholds_match_spec_values() -> None:
    """spec: >=94 tier advance, >=90 test pass, 100 convergence target."""
    assert T1_PASS == 94
    assert T2_PASS == 94
    assert T3_PASS == 94
    assert TEST_PASS == 90
    assert CONVERGENCE == 100


def test_gates_import_thresholds_as_fallback() -> None:
    """G3/G5 must import the named constant (single source), not a bare literal."""
    repo = Path(__file__).resolve().parents[3]
    g3_src = (repo / "src" / "shenbi" / "gates" / "g3.py").read_text(encoding="utf-8")
    g5_src = (repo / "src" / "shenbi" / "gates" / "g5.py").read_text(encoding="utf-8")
    assert "T1_PASS" in g3_src, "g3.py must reference thresholds.T1_PASS"
    assert "T2_PASS" in g5_src, "g5.py must reference thresholds.T2_PASS"
```

- [ ] **Step 2: Run → fails**
`uv run pytest tests/unit/contracts/test_thresholds.py -q` → FAIL ModuleNotFoundError

- [ ] **Step 3: Implement**

```python
# src/shenbi/contracts/thresholds.py
"""门阈值单一源（spec 支柱二）。所有数值阈值集中此处；门 import 具名常量，
ruff 禁裸魔法数。值以 spec 为准：>=94 tier 推进、>=90 单测通过、100 收敛。"""
from __future__ import annotations

T1_PASS: int = 94   # T1 tier advancement threshold (acceptance.json fallback)
T2_PASS: int = 94   # T2 phase advancement threshold
T3_PASS: int = 94   # T3 pipeline advancement threshold
TEST_PASS: int = 90  # individual test pass threshold
CONVERGENCE: int = 100  # convergence target
```

- [ ] **Step 4: Wire G3.2 fallback** — 改 `src/shenbi/gates/g3.py`：
  - 文件顶部 import 段（第 11-21 行附近）加：
```python
from shenbi.contracts.thresholds import T1_PASS
```
  - 把第 69 行 `threshold = acceptance.get("t1", 94)` 改为：
```python
            threshold = acceptance.get("t1", T1_PASS)
```

- [ ] **Step 5: Wire G5.1 fallback** — 改 `src/shenbi/gates/g5.py`：
  - 顶部 import 段（第 17-25 行附近）加：
```python
from shenbi.contracts.thresholds import T2_PASS
```
  - 把第 39 行 `threshold = acceptance.get("t2", 94)` 改为：
```python
        threshold = acceptance.get("t2", T2_PASS)
```

- [ ] **Step 6: Run → passes** — `uv run pytest tests/unit/contracts/test_thresholds.py tests/unit/gates/test_g3.py tests/unit/gates/test_g5.py -q` → 全绿，无 regression（值不变）。
- [ ] **Step 7: mypy + ruff**
`uv run mypy src/shenbi/contracts/thresholds.py src/shenbi/gates/g3.py src/shenbi/gates/g5.py && uv run ruff check src/shenbi/contracts/thresholds.py src/shenbi/gates/` → Success / All passed
- [ ] **Step 8: Commit**
```bash
git add src/shenbi/contracts/thresholds.py tests/unit/contracts/test_thresholds.py \
        src/shenbi/gates/g3.py src/shenbi/gates/g5.py
git commit -m "feat(contracts): add thresholds.py single-source + wire G3.2/G5.1 fallbacks"
```

---

### Task 2: derive_file_type 契约 join 修复（spec New-I，修复漏 resolve）

**Files:** Modify `src/shenbi/dispatcher/executor.py`（顶部 import 第 17 行后；函数体 31-48）；Append test `tests/unit/test_dispatcher_executor.py`

**Interfaces:** Consumes `shenbi.contract.load_contract`（已 import 于 executor.py:17）、`shenbi.contract.OutputKind`、`shenbi.contracts.registry.bootstrap_registry`。Produces 重写后的 `derive_file_type(skill: str) -> str`（返回 `"chapter"|"truth"|"report"`）。

**验证现状（已亲手核对）：** `executor.py:31` 定义 `derive_file_type`；`chapter_skills` 块 33-38，`truth_skills` 块 39-43 硬编码 3 个（`state-settling`/`foreshadowing-track`/`foreshadowing-plant`），**漏 `shenbi-foreshadowing-resolve`**，故 resolve 的 truth 输出被当 chapter（G2 跑章节字数门）。`OutputKind`（`contract.py:34-37`）3 成员 `{ARTIFACT, REPORT, EPHEMERAL}`：truth 与 chapter **都是 ARTIFACT**，故 OutputKind 无法区分；区分在 truth-files.yaml `concepts` 的 `kind: truth`。resolve 的 frontmatter（`skills/shenbi-foreshadowing-resolve/SKILL.md:5-13`）：`kind: artifact`、`writes: []`、`updates: [truth/pending_hooks.md]`，而 `truth/pending_hooks.md` 是 truth concept（kind: truth）。**这是新增 join 逻辑（非现成）。**

- [ ] **Step 1: Write failing test** — 追加到 `tests/unit/test_dispatcher_executor.py`：

```python
@pytest.mark.unit
def test_derive_file_type_returns_truth_for_foreshadowing_resolve() -> None:
    """New-I fix: resolve updates truth/pending_hooks.md -> 'truth' (not 'chapter').

    Old hardcoded truth_skills set (executor.py:39-43) missed resolve, so G2 ran
    chapter word-count validation on a truth-file edit. derive now joins contract
    OutputKind + truth-files.yaml concepts.
    """
    assert derive_file_type("shenbi-foreshadowing-resolve") == "truth"


@pytest.mark.unit
def test_derive_file_type_returns_report_for_report_kind_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    """REPORT OutputKind -> 'report'."""
    from shenbi.contract import OutputKind
    import shenbi.dispatcher.executor as exec_mod

    monkeypatch.setattr(
        exec_mod,
        "load_contract",
        lambda s: {
            "kind": OutputKind.REPORT,
            "reads": [],
            "writes": ["audits/r.md"],
            "updates": [],
            "read_fields": {},
        },
    )
    assert derive_file_type("shenbi-review-arc-payoff") == "report"


@pytest.mark.unit
def test_derive_file_type_returns_chapter_for_ephemeral_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    """EPHEMERAL has no persisted output -> default 'chapter' (G2 skipped upstream)."""
    from shenbi.contract import OutputKind
    import shenbi.dispatcher.executor as exec_mod

    monkeypatch.setattr(
        exec_mod,
        "load_contract",
        lambda s: {
            "kind": OutputKind.EPHEMERAL,
            "reads": [],
            "writes": [],
            "updates": [],
            "read_fields": {},
        },
    )
    assert derive_file_type("shenbi-ephemeral") == "chapter"
```

- [ ] **Step 2: Run → fails** — `uv run pytest tests/unit/test_dispatcher_executor.py -q` → `test_derive_file_type_returns_truth_for_foreshadowing_resolve` FAIL（当前返回 `"chapter"`）。

- [ ] **Step 3: Implement** — 改 `src/shenbi/dispatcher/executor.py`：
  - 顶部 import（第 17 行 `from shenbi.contract import ContractError, load_contract` 之后）加：
```python
from shenbi.contract import OutputKind
from shenbi.contracts.registry import bootstrap_registry
```
  - 用以下替换第 31-48 行整个 `derive_file_type`：

```python
_TRUTH_FILES_CACHE: set[str] | None = None


def _truth_file_set() -> set[str]:
    """truth-files.yaml concepts 中 kind=='truth' 的文件集合。

    truth 与 chapter 都是 OutputKind.ARTIFACT，无法用 OutputKind 区分；
    区分在 truth-files.yaml（spec New-I join 规则）。
    """
    global _TRUTH_FILES_CACHE
    if _TRUTH_FILES_CACHE is None:
        _TRUTH_FILES_CACHE = {
            name for name, kind in bootstrap_registry().items() if kind == "truth"
        }
    return _TRUTH_FILES_CACHE


def derive_file_type(skill: str) -> str:
    """Derive G2 FILE_TYPE from the contract layer (spec New-I).

    Join rule: load contract kind. REPORT -> report. ARTIFACT -> truth iff the
    skill writes/updates a file that truth-files.yaml lists as kind=truth, else
    chapter. EPHEMERAL (no persisted output) -> chapter default. This replaces
    the hardcoded skill-name sets that missed shenbi-foreshadowing-resolve.
    """
    try:
        c = load_contract(skill)
    except ContractError:
        return "chapter"
    kind = c["kind"]
    if kind == OutputKind.REPORT:
        return "report"
    if kind == OutputKind.EPHEMERAL:
        return "chapter"
    outputs = {*c["writes"], *c["updates"]}
    if outputs & _truth_file_set():
        return "truth"
    return "chapter"
```

- [ ] **Step 4: Run → passes** — `uv run pytest tests/unit/test_dispatcher_executor.py -q` → 全绿。确认既有测试仍过：`test_derive_file_type_returns_chapter_for_drafting`（chapter-drafting ARTIFACT 写 `chapters/chapter-N.md`，非 truth 文件 → chapter）、`test_derive_file_type_returns_truth_for_state_settling`（updates truth 文件 → truth）、`test_derive_file_type_defaults_to_chapter_for_unknown`（ContractError → chapter）。
- [ ] **Step 5: mypy + ruff** — `uv run mypy src/shenbi/dispatcher/executor.py && uv run ruff check src/shenbi/dispatcher/` → Success / All passed
- [ ] **Step 6: Commit**
```bash
git add src/shenbi/dispatcher/executor.py tests/unit/test_dispatcher_executor.py
git commit -m "fix(dispatcher): derive_file_type from contract+truth-files.yaml (fix resolve misclassified)"
```

---

### Task 3: G3.4 fail-closed — 无独立 SCORE 记录则 FAIL

**Files:** Modify `src/shenbi/gates/g3.py:144-162`；Append test `tests/unit/gates/test_g3.py`

**Interfaces:** Consumes `jload`/`fail`（已 import）。改 G3.4 分支逻辑。

**验证现状（已核对 g3.py:144-162）：** 当前 `if gen_agent and scorer_agent and str(gen_agent) == str(scorer_agent): FAIL`。Bug：若 `gen_agent` 存在（生成器跑过）但 `scorer_agent` 为 falsy（dispatcher 自评、无 SCORE 记录），整个条件为假 → **PASS（空转）**。spec：scoring MUST use independent subagent；dispatcher-scored 无效；加 fail-closed 检查。

**跨计划一致性（Kant I2 修复）：** pillar5 Task 8 已创建 `gates/g3_independence.py::scoring_independence_status`。本 Task 应优先调用该纯函数（单一源），避免内联重写。若 pillar5 未执行则可临时内联但须标注接入点。

**外科策略（不破坏现有测试）：** 仅当「生成器有记录但无独立 scorer」时 FAIL。对 `gen_agent` 为 None（无生成记录，G3.4 不适用）仍 PASS，保持 `test_g33_passes_with_valid_output_files` 等现有测试不变。

- [ ] **Step 1: Write failing test** — 追加到 `tests/unit/gates/test_g3.py`：

```python
@pytest.mark.unit
def test_g34_fail_closed_when_generator_recorded_but_no_scorer(tmp_path: Path) -> None:
    """generator ran (agent_trace[skill]) but no current_scorer_agent -> G3.4 FAIL.

    This is the dispatcher-scored 'idle' bug: the old condition
    `gen_agent and scorer_agent and ...` is False when scorer_agent is absent,
    so a dispatcher grading its own output passed G3.4.
    """
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text(
        json.dumps({"agent_trace": {"shenbi-worldbuilding": "agent-gen"}}),
        encoding="utf-8",
    )
    result = _result_dict(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
    assert any("G3.4" in m for m in result.get("must_fix", []))
```

- [ ] **Step 2: Run → fails** — 该测试 FAIL（当前 G3.4 返回 PASS）。
- [ ] **Step 3: Implement** — 改 `src/shenbi/gates/g3.py` 第 155-158 行。把：
```python
            if gen_agent and scorer_agent and str(gen_agent) == str(scorer_agent):
                mf.append({"id": "G3.4", "s": "FAIL", "r": "scorer agent same as generator"})
            else:
                c.append({"id": "G3.4", "s": "PASS"})
```
替换为：
```python
            # G3.4 fail-closed (spec): a generator ran but no independent SCORE
            # record exists -> dispatcher-scored results are invalid.
            if gen_agent and not scorer_agent:
                mf.append(
                    {
                        "id": "G3.4",
                        "s": "FAIL",
                        "r": "generator recorded but no independent scorer agent",
                    }
                )
            elif gen_agent and str(gen_agent) == str(scorer_agent):
                mf.append({"id": "G3.4", "s": "FAIL", "r": "scorer agent same as generator"})
            else:
                c.append({"id": "G3.4", "s": "PASS"})
```
- [ ] **Step 4: Run → passes** — `uv run pytest tests/unit/gates/test_g3.py -q` → 全绿。确认既有 G3.4 测试仍 FAIL：`test_g34_fails_when_scorer_same_as_generator`（scorer==gen → FAIL）、`test_g34_fails_when_scorer_agent_equals_generator`（同）、`test_g34_skips_without_progress_json`（无 pp → SKIP）；`test_g33_passes_with_valid_output_files`（gen_agent=None → 走 else PASS）不变。
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/gates/g3.py && uv run ruff check src/shenbi/gates/g3.py
git add src/shenbi/gates/g3.py tests/unit/gates/test_g3.py
git commit -m "fix(g3): G3.4 fail-closed when generator recorded but no independent scorer"
```

---

### Task 4: G6.12 改用 cjk.find_terms（修复 CJK 嵌入敏感词失效）

**Files:** Modify `src/shenbi/gates/g6.py`（顶部 import 第 16 行块；G6.12 体 385-408）；Append test `tests/unit/gates/test_g6.py`

**Interfaces:** Consumes `shenbi.text.cjk.find_terms`（已落地，`find_terms(text: str, terms: Iterable[str]) -> list[TermHit]`，`TermHit(term,start,end)`）。

**验证现状（已亲手核对）：** `g6.py:399` 用 `re.search(rf"(?:^|[^\w]){re.escape(word)}(?:$|[^\w])", content)`。Python 默认 Unicode 模式下 `\w` **包含 CJK 字符**，故 `[^\w]` 在 CJK 之间不匹配 → 嵌入在中文正文里的敏感词（无空格）**检不出**。实测：`re.search(...)` 对 `反对台独行径是底线` 找 `台独` 返回 `False`；`find_terms` 找到 1 处。现有测试 `test_g6_sensitive_words_detected` 因测试文本带空格/标点（`正文内容。 台独 。\n`）才碰巧通过。

- [ ] **Step 1: Write failing test** — 追加到 `tests/unit/gates/test_g6.py`。复用该文件已有的 `_make_chapter` 帮助函数（其它 G6 测试用它创建章节）：

```python
@pytest.mark.unit
def test_g612_detects_sensitive_word_embedded_in_cjk(tmp_path: Path) -> None:
    """Sensitive word embedded mid-sentence (no spaces) -> G6.12 finds it.

    Old \\w-anchored regex missed this because \\w matches CJK in Python's
    Unicode mode. cjk.find_terms uses exact substring match.
    """
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    project_dir = tmp_path / "project"
    _make_chapter(project_dir, 1, "正文反对台独行径是底线内容\n")
    result = _result_dict(gate_G6("long-form", str(round_dir), str(project_dir)))
    assert any(mf.startswith("G6.12:台独") for mf in result["must_fix"])
```

- [ ] **Step 2: Run → fails** — 该测试 FAIL（旧 regex 对嵌入 CJK 返回 False → G6.12 PASS，无 must_fix）。
- [ ] **Step 3: Implement** — 改 `src/shenbi/gates/g6.py`：
  - 顶部 import 段（第 11-14 行 `import json` / `import re` / `from pathlib import Path` / `from typing import Any` 之后，或紧邻现有 `from shenbi.gates.g6_checks import ...`）加：
```python
from shenbi.text.cjk import find_terms
```
  - 把 G6.12 内层循环（第 393-400 行）替换。原：
```python
        sw_found = []
        for ch in chapters:
            content = ch.read_text(encoding="utf-8")
            for word in sensitive:
                # Only flag as standalone token (surrounded by whitespace/punctuation),
                # not as substring of other words
                if re.search(rf"(?:^|[^\w]){re.escape(word)}(?:$|[^\w])", content):
                    sw_found.append(f"{word}:{ch.name}")
```
改为：
```python
        sw_found = []
        for ch in chapters:
            content = ch.read_text(encoding="utf-8")
            # cjk.find_terms: exact substring match. For CJK every char position
            # is a valid boundary, fixing the \w-anchored regex that missed words
            # embedded mid-sentence (spec pillar 3 / G6.12).
            hits = find_terms(content, sensitive)
            sw_found.extend(f"{hit.term}:{ch.name}" for hit in hits)
```
（G6.12 其余行——`if sw_found: mf.extend(...)` 与 `else: c.append(...)`——保持不变。）
- [ ] **Step 4: Run → passes** — `uv run pytest tests/unit/gates/test_g6.py -q` → 全绿。确认既有 `test_g6_sensitive_words_detected`（带空格）仍 FAIL 检出。
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/gates/g6.py && uv run ruff check src/shenbi/gates/g6.py
git add src/shenbi/gates/g6.py tests/unit/gates/test_g6.py
git commit -m "fix(g6): G6.12 use cjk.find_terms for embedded CJK sensitive-word scan"
```

---

### Task 5: G5/G6 顶层 jload 加守卫（防 crash）

**Files:** Modify `src/shenbi/gates/g5.py:34,38`、`src/shenbi/gates/g6.py:33`；Append tests `tests/unit/gates/test_g5.py`、`tests/unit/gates/test_g6.py`

**Interfaces:** 仅加 try/except 守卫，返回干净 FAIL 而非抛异常。

**验证现状（已核对）：** `g5.py:34` `deps = jload(TESTS / "tiers" / "deps.json")`、`g5.py:38` `acceptance = jload(TESTS / "tiers" / "acceptance.json")`、`g6.py:33` `deps = jload(TESTS / "tiers" / "deps.json")` 均**无 try/except**；若文件缺失/损坏，整个门函数抛 `JSONDecodeError`/`OSError`/`ValueError`（jload 对非 dict 抛 ValueError）而非返回 FAIL。

- [ ] **Step 1: Write failing tests** — 追加到 `tests/unit/gates/test_g6.py`：

```python
@pytest.mark.unit
def test_g6_returns_fail_not_crash_when_deps_json_malformed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed deps.json -> G6 returns FAIL JSON, never raises."""
    import shenbi.gates.g6 as g6_mod

    def boom(_p: object) -> dict[str, object]:
        raise json.JSONDecodeError("bad", "doc", 0)

    monkeypatch.setattr(g6_mod, "jload", boom)
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    result = _result_dict(gate_G6("long-form", str(round_dir), str(tmp_path)))
    assert result["status"] == "FAIL"
```

追加到 `tests/unit/gates/test_g5.py`（该文件已有 `_result_dict`/`gate_G5` import 与 `@pytest.mark.unit` 模式）：

```python
@pytest.mark.unit
def test_g5_returns_fail_not_crash_when_deps_json_malformed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed deps.json -> G5 returns FAIL JSON, never raises."""
    import shenbi.gates.g5 as g5_mod

    def boom(_p: object) -> dict[str, object]:
        raise json.JSONDecodeError("bad", "doc", 0)

    monkeypatch.setattr(g5_mod, "jload", boom)
    round_dir = tmp_path / "round"
    round_dir.mkdir()
    result = json.loads(gate_G5("some-phase", str(round_dir), str(tmp_path)))
    assert result["status"] == "FAIL"
```

- [ ] **Step 2: Run → fails** — 两测试均 FAIL（当前 jload 抛异常被 pytest 当 error，非 status FAIL）。
- [ ] **Step 3: Implement G6** — 改 `src/shenbi/gates/g6.py` 第 33 行。把：
```python
    deps = jload(TESTS / "tiers" / "deps.json")
```
改为：
```python
    try:
        deps = jload(TESTS / "tiers" / "deps.json")
    except (json.JSONDecodeError, OSError, ValueError):
        return fail("G6", [], "scoring", ["G6.0:deps.json unreadable or malformed"])
```
- [ ] **Step 4: Implement G5** — 改 `src/shenbi/gates/g5.py` 第 34、38 行。把：
```python
    deps = jload(TESTS / "tiers" / "deps.json")
    phase_data = deps.get("t2-phases", {}).get(phase_name)
    if not phase_data:
        return fail("G5", [], "scoring", [f"unknown phase: {phase_name}"])
    acceptance = jload(TESTS / "tiers" / "acceptance.json")
```
改为：
```python
    try:
        deps = jload(TESTS / "tiers" / "deps.json")
    except (json.JSONDecodeError, OSError, ValueError):
        return fail("G5", [], "scoring", ["G5.0:deps.json unreadable or malformed"])
    phase_data = deps.get("t2-phases", {}).get(phase_name)
    if not phase_data:
        return fail("G5", [], "scoring", [f"unknown phase: {phase_name}"])
    try:
        acceptance = jload(TESTS / "tiers" / "acceptance.json")
    except (json.JSONDecodeError, OSError, ValueError):
        return fail("G5", [], "scoring", ["G5.0:acceptance.json unreadable or malformed"])
```
- [ ] **Step 5: Run → passes** — `uv run pytest tests/unit/gates/test_g6.py tests/unit/gates/test_g5.py -q` → 全绿，无 regression。
- [ ] **Step 6: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/gates/g5.py src/shenbi/gates/g6.py && uv run ruff check src/shenbi/gates/
git add src/shenbi/gates/g5.py src/shenbi/gates/g6.py tests/unit/gates/test_g5.py tests/unit/gates/test_g6.py
git commit -m "fix(gates): guard top-level jload in G5/G6 against crash on malformed json"
```

---

### Task 6: G1 .bak 决策抽纯函数（向纯度靠拢）

**Files:** Modify `src/shenbi/gates/g1.py`（G1.4 体 44-97）；Append test `tests/unit/gates/test_g1.py`

**Interfaces:** Produces `BACKUP_SKILLS: frozenset[str]`（模块级常量，原 `inplace_skills` 内容不变）、`compute_backup_targets(skill: str | None, file_paths: list[str], round_dir: str | None) -> list[tuple[str, str]]`（纯函数：返回应创建的 `(src_path, bak_path)` 列表，无 I/O）。

**验证现状（已核对 g1.py:44-97）：** `inplace_skills` 硬编码集在函数体内（45-55）；`shutil.copy2(fp, bak)`（line 90）是 G1 的写副作用。**关键耦合：** `g2.py:188-189` G2.11 truth-diff 读 `Path(str(fp)+".bak")`，依赖这些 `.bak` 在 dispatch 前存在。故**不能**直接删写（会破坏 G2.11 编排）。诚实方案：把**决策**抽为纯函数（可单测、向纯度靠拢），写动作保留于门调用路径以保行为/现有测试；完全迁到 dispatcher（dispatcher 在 G1 前创建 `.bak`，门只读检查）是**后续编排重构**，本计划范围外。

- [ ] **Step 1: Write failing test** — 追加到 `tests/unit/gates/test_g1.py`（顶部加 `from shenbi.gates.g1 import compute_backup_targets`）：

```python
@pytest.mark.unit
def test_compute_backup_targets_is_pure_decision() -> None:
    """Pure decision: which (src, bak) pairs to create. No I/O."""
    targets = compute_backup_targets(
        "shenbi-faction-builder", ["/abs/world/factions.md"], "/abs/round"
    )
    assert targets == [("/abs/world/factions.md", "/abs/world/factions.md.bak")]


@pytest.mark.unit
def test_compute_backup_targets_empty_without_round_dir() -> None:
    """No round_dir -> no backups targeted."""
    assert compute_backup_targets("shenbi-faction-builder", ["/x.md"], None) == []


@pytest.mark.unit
def test_compute_backup_targets_skips_non_backup_skill() -> None:
    """A skill not in BACKUP_SKILLS -> no targets."""
    assert compute_backup_targets("shenbi-chapter-drafting", ["/x.md"], "/r") == []
```

- [ ] **Step 2: Run → fails** — `uv run pytest tests/unit/gates/test_g1.py -q` → ModuleNotFoundError / ImportError（`compute_backup_targets` 不存在）。
- [ ] **Step 3: Implement** — 改 `src/shenbi/gates/g1.py`：
  - 在 `gate_G1` 函数**之前**（文件 import 段之后）加模块级常量 + 纯函数：
```python
BACKUP_SKILLS: frozenset[str] = frozenset(
    {
        "shenbi-faction-builder",
        "shenbi-location-builder",
        "shenbi-relationship-map",
        "shenbi-volume-outlining",
        "shenbi-power-system",
        "shenbi-foreshadowing-track",
        "shenbi-truth-sync",
        "shenbi-state-settling",
        "shenbi-genre-config",
    }
)


def compute_backup_targets(
    skill_name: str | None, file_paths: list[str], round_dir: str | None
) -> list[tuple[str, str]]:
    """Pure decision: which (src_path, bak_path) pairs to create for an in-place skill.

    Extracted from G1.4 so the backup decision is testable without I/O. The
    gate still performs the copy (G2.11 truth-diff depends on the .bak
    existing pre-dispatch); moving the write fully to the dispatcher is a
    follow-up orchestration refactor (out of scope here).
    """
    if not skill_name or skill_name not in BACKUP_SKILLS or not round_dir:
        return []
    return [(fp, str(fp) + ".bak") for fp in file_paths]
```
  - 删掉 `gate_G1` 函数体内的 `inplace_skills = {...}` 定义（原 45-55 行）。在 `fps = normalize_file_paths(...)` 之后、`for fp in fps:` 之前算一次：
```python
    targets = compute_backup_targets(skill_name, fps, str(rd) if rd else None)
```
  - 循环内的 G1.4 分支改为（用 `fp in dict(targets)` 判断当前文件是否在目标集）：
```python
        # G1.4 — create .bak for in-place modifying skills (decision via pure helper)
        if fp in dict(targets):
            bak_path = Path(str(fp) + ".bak")
            if not bak_path.exists():
                try:
                    shutil.copy2(fp, str(bak_path))
                    c.append({"id": "G1.4", "file": fp, "s": "PASS", "r": ".bak created"})
                except OSError:
                    mf.append({"id": "G1.4", "file": fp, "s": "FAIL", "r": "cannot create .bak"})
            else:
                c.append({"id": "G1.4", "file": fp, "s": "PASS", "r": ".bak exists"})
        else:
            c.append({"id": "G1.4", "file": fp, "s": "SKIP", "r": "not in-place skill"})
```
（这保行为：in-place skill 的输入文件 → 创建 .bak；其它 → SKIP。）
- [ ] **Step 4: Run → passes** — `uv run pytest tests/unit/gates/test_g1.py -q` → 全绿。确认既有 `test_g14_creates_bak_for_inplace_skill`（两处）仍创建 `.bak` 并 PASS。
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/gates/g1.py && uv run ruff check src/shenbi/gates/g1.py
git add src/shenbi/gates/g1.py tests/unit/gates/test_g1.py
git commit -m "refactor(g1): extract pure compute_backup_targets (purity step toward no-write gate)"
```

---

### Task 7: G7 删写 summary.json 副作用（audit_warnings 进返回 JSON）

**Files:** Modify `src/shenbi/gates/g7.py:282-300`；Modify `tests/unit/gates/test_g7.py:429-446`

**Interfaces:** G7 改为只读：不写 `summary.json`，把 `audit_warnings` 作为一条 check 放进返回 JSON。

**验证现状（已核对 g7.py:282-300）：** G7 末尾「Write audit_warnings to summary.json」块对 `summary.json` 做 `open("w")` + `json.dump`，是写副作用（spec：门必须纯）。现有测试 `test_g715_duplicate_score_pattern_warns_only`（test_g7.py:429-446）断言 summary.json 被写入；删除写副作用后**必须**同步更新该测试为断言返回 JSON 含 `audit_warnings`（这是该任务的预期行为变更）。

- [ ] **Step 1: Update the affected test first (documents intended behavior change)** — 改 `tests/unit/gates/test_g7.py` 第 429-446 行的 `test_g715_duplicate_score_pattern_warns_only`。把末尾：
```python
    # audit_warnings were written back into summary.json
    written = json.loads((round_dir / "summary.json").read_text(encoding="utf-8"))
    assert "audit_warnings" in written
    assert written["audit_warnings"]
```
替换为：
```python
    # G7 is now pure: audit_warnings are returned in the gate JSON, NOT written
    # to summary.json (spec: gates must not have write side-effects).
    audit_check = next(
        (chk for chk in result["checks"] if chk.get("id") == "G7.AUDIT"), None
    )
    assert audit_check is not None
    assert audit_check.get("audit_warnings")
    # summary.json must be untouched by the gate
    assert "audit_warnings" not in json.loads(
        (round_dir / "summary.json").read_text(encoding="utf-8")
    )
```
（函数顶部的 `g715_warns` 断言保持不变。）

- [ ] **Step 2: Run → fails** — `uv run pytest tests/unit/gates/test_g7.py::test_g715_duplicate_score_pattern_warns_only -q` → FAIL（当前写 summary.json 且无 G7.AUDIT check）。
- [ ] **Step 3: Implement** — 改 `src/shenbi/gates/g7.py` 第 282-300 行。把：
```python
    # Write audit_warnings to summary.json
    audit_warnings = []
    for check in c:
        if check.get("s") == "WARN" and check.get("id") in ("G7.14", "G7.15"):
            audit_warnings.append(
                {
                    "type": check.get("type", check["id"]),
                    "severity": check.get("severity", "warn"),
                    "message": check.get("message", check.get("detail", "")),
                }
            )
    if audit_warnings and summary_path.exists():
        try:
            s = jload(str(summary_path))
            s["audit_warnings"] = audit_warnings
            with summary_path.open("w", encoding="utf-8") as sf:
                json.dump(s, sf, indent=2, ensure_ascii=False)
        except Exception:
            pass
```
替换为（纯：只算，不写）：
```python
    # G7 is pure: collect audit_warnings into the returned JSON, never write to
    # summary.json (spec: gates must not have write side-effects).
    audit_warnings = []
    for check in c:
        if check.get("s") == "WARN" and check.get("id") in ("G7.14", "G7.15"):
            audit_warnings.append(
                {
                    "type": check.get("type", check["id"]),
                    "severity": check.get("severity", "warn"),
                    "message": check.get("message", check.get("detail", "")),
                }
            )
    c.append(
        {
            "id": "G7.AUDIT",
            "s": "WARN" if audit_warnings else "PASS",
            "audit_warnings": audit_warnings,
        }
    )
```
- [ ] **Step 4: Run → passes** — `uv run pytest tests/unit/gates/test_g7.py -q` → 全绿，无 regression。
- [ ] **Step 5: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/gates/g7.py && uv run ruff check src/shenbi/gates/g7.py
git add src/shenbi/gates/g7.py tests/unit/gates/test_g7.py
git commit -m "fix(g7): remove summary.json write side-effect; return audit_warnings in gate JSON"
```

---

### Task 8: G0.15 — 门登记表单一源一致性检查（判据 5 前置）

**Files:** Modify `src/shenbi/contracts/registry.py`（加 `known_skill_names`）；Modify `src/shenbi/gates/g0.py`（G0.13 之后加 G0.15）；Append test `tests/unit/gates/test_g0.py`

**Interfaces:** Produces `shenbi.contracts.registry.known_skill_names() -> set[str]`（单一源：扫描 `SKILLS` 目录，与 `shared.ALL_SKILLS` 同源但归契约层所有）。G0 加新子检查 G0.15：断言 `G4_CHECKER_SKILLS ⊆ known_skill_names()`。

**验证现状（已核对）：** `shared.py:198-202` `ALL_SKILLS` 扫描 `SKILLS` 目录；`shared.py:205-228` `G4_CHECKER_SKILLS` 硬编码 22 个；`contracts/registry.py` 已有 `bootstrap_registry`（import 了 `PROJECT`，但未 import `SKILLS`）。判据 5 要求「三份门登记表从单一源派生，diff 为空」。本任务建单一源 API + G0 一致性门（捕获 G4 checker 引用了不存在的 skill 这类漂移），是为判据 5 铺路的可测增量。

- [ ] **Step 1: Write failing test** — 追加到 `tests/unit/gates/test_g0.py`（若该文件已 import `gate_G0`/`json` 等则复用）：

```python
@pytest.mark.unit
def test_g015_gate_registry_consistency_passes_on_current_repo() -> None:
    """G0.15 asserts G4_CHECKER_SKILLS is a subset of the single-source skill set."""
    result = json.loads(gate_G0(None, None))
    g015 = next((chk for chk in result["checks"] if chk.get("id") == "G0.15"), None)
    assert g015 is not None
    assert g015["s"] == "PASS"


@pytest.mark.unit
def test_known_skill_names_is_single_source() -> None:
    """known_skill_names owns the authoritative skill vocabulary (judgement 5)."""
    from shenbi.contracts.registry import known_skill_names
    from shenbi.gates.shared import ALL_SKILLS

    assert known_skill_names() == set(ALL_SKILLS)
```

- [ ] **Step 2: Run → fails** — `uv run pytest tests/unit/gates/test_g0.py -q` → FAIL（无 G0.15 / 无 `known_skill_names`）。
- [ ] **Step 3: Implement known_skill_names** — 在 `src/shenbi/contracts/registry.py`：
  - 顶部 import（第 15 行 `from shenbi.gates.shared import PROJECT`）改为：
```python
from shenbi.gates.shared import PROJECT, SKILLS
```
  - 文件末尾加：
```python
def known_skill_names() -> set[str]:
    """Authoritative skill-name set — single source for gate registries (judgement 5).

    Scans skills/ for directories with a SKILL.md. Owned by the contract layer
    so G0 coverage, G4 checker sets, and the contract registry all derive from
    one place.
    """
    if not SKILLS.exists():
        return set()
    return {
        d.name for d in SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    }
```
- [ ] **Step 4: Implement G0.15** — 在 `src/shenbi/gates/g0.py` 的 `gate_G0` 末尾（G0.14 之后、`return passed("G0", checks)` 之前）加：
```python
    # G0.15 — gate registry single-source consistency (judgement 5 precursor).
    # G4_CHECKER_SKILLS must reference only real skills. Catches drift across
    # the gate registries.
    from shenbi.contracts.registry import known_skill_names

    known = known_skill_names()
    g4_drift = sorted(G4_CHECKER_SKILLS - known)
    if g4_drift:
        return fail(
            "G0",
            checks + [{"id": "G0.15", "s": "FAIL", "r": f"G4 checker skills not in skill set: {g4_drift}"}],
            "round_creation",
            [f"G0.15: G4_CHECKER_SKILLS drifted from skills/ — remove {g4_drift}"],
        )
    checks.append(
        {"id": "G0.15", "s": "PASS", "note": "gate registries derive from single skill source"}
    )
```
（`G4_CHECKER_SKILLS` 已在 g0.py:27 import。）
- [ ] **Step 5: Run → passes** — `uv run pytest tests/unit/gates/test_g0.py -q` → 全绿，无 regression。
- [ ] **Step 6: mypy + ruff + commit**
```bash
uv run mypy src/shenbi/contracts/registry.py src/shenbi/gates/g0.py && uv run ruff check src/shenbi/contracts/ src/shenbi/gates/g0.py
git add src/shenbi/contracts/registry.py src/shenbi/gates/g0.py tests/unit/gates/test_g0.py
git commit -m "feat(g0): G0.15 gate-registry single-source consistency + known_skill_names"
```

---

### Task 9: 全量回归 + 支柱二完成确认

**Files:** 无。仅验证。

- [ ] **Step 1: Full test suite（覆盖率门在此生效，不加 --no-cov）**
`uv run pytest -q` → 现有测试集全绿 + 本计划新增测试全绿，无 regression。执行者以实际输出为准，只断言「无失败、无 regression」，不引用具体数字。
- [ ] **Step 2: Type check + lint whole repo**
`uv run mypy src/shenbi && uv run ruff check .` → Success / All passed
- [ ] **Step 3: Verify spec 对齐（本支柱范围）**
  - G3.4 fail-closed + 读 trace（无 SCORE 记录则 FAIL）：Task 3 ✓（读 trace 依赖见前置：`current_scorer_agent`/`agent_trace`）
  - G5/G6 顶层 jload 加守卫：Task 5 ✓
  - G6.12 用 `cjk.find_terms`：Task 4 ✓
  - G1/G7 删写副作用：G7 完全删除（Task 7 ✓）；G1 决策抽纯（Task 6 ✓），完全迁出写动作是后续编排重构（范围外，已声明）
  - G0 覆盖率从 REGISTRY 派生（单一源一致性）：Task 8 ✓
  - derive_file_type join fix：Task 2 ✓
  - 门阈值派生化：Task 1（thresholds.py）✓；逐技能 parser 注册基建属支柱四 Tier B（record parser，已落 trace），范围外
  - 判据 5（三份门登记表单一源 diff 空）：Task 8 建单一源 API + G0.15 一致性门（前置，全量 diff 锁定随 69 迁移）
- [ ] **Step 4: Empty marker commit**
```bash
git commit --allow-empty -m "chore(gates): pillar 2 gate refactor complete"
```

---

## Self-Review

**1. Spec coverage（支柱二范围）：** spec 支柱二列举的改造点逐条有对应 Task——阈值派生(Task1)、derive_file_type join(Task2)、G3.4 fail-closed(Task3)、G6.12 cjk(Task4)、G5/G6 jload 守卫(Task5)、G1/G7 删写副作用(Task6/7)、G0 单一源(Task8)。**范围外（已声明）：** 69 技能全量迁移（支柱一续）、record parser + 判据 12（支柱四 Tier B）、update_progress.py 迁 trace、audit_trace 接入 gate_G7 主体、AST lint 强制 safe_write（支柱六）、subprocess read-provenance（future work）、G1 `.bak` 写动作完全迁到 dispatcher（G2.11 编排耦合，后续）。

**2. Placeholder scan：** 无 TBD/TODO；每个 code step 含完整代码与精确命令；CI/lint 接入无残留（本计划不加新 CI 文件，复用现有 `uv run mypy`/`ruff`）。

**3. Type consistency：** `derive_file_type(skill:str)->str`（Task2 跨 executor + 测试一致）；`compute_backup_targets(skill:str|None, file_paths:list[str], round_dir:str|None)->list[tuple[str,str]]`（Task6 一致）；`known_skill_names()->set[str]`（Task8 registry↔g0↔test 一致）；`find_terms` 复用支柱三既有签名 `TermHit(term,start,end)`；`T1_PASS/T2_PASS:int`（Task1↔g3↔g5）。

**4. 已知限制与诚实声明：**
  - Task 6（G1）：写动作仍保留在门调用路径，因 `g2.py:188-189` G2.11 truth-diff 依赖 `.bak` 存在；纯决策已抽出可单测，完全无写门需 dispatcher 编排重构（范围外）。
  - Task 2（derive_file_type）：依赖 truth-files.yaml `concepts` 的 `kind` 字段为真值源；当前 concepts 已含全部 truth 文件（已核对）。`bootstrap_registry` 此前标注「未接入生产」——本 Task 正是迁移顺序 step 5「contract.py 的 REGISTRY 改从 contracts/REGISTRY 派生」的接入点。
  - Task 8（G0.15）：单一源一致性是判据 5 的前置；当前 `known_skill_names()==set(ALL_SKILLS)`（同源扫描，trivially 相等），其价值在于为后续「G4_CHECKER_SKILLS / 契约 skill 集 全部从 known_skill_names 派生」锁定 diff；真正三表 diff 锁定随 69 迁移。
  - 所有门体修改均为外科手术式，每个 Task 先验证既有测试不变（已在 Steps 列出受影响既有测试名与预期）。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-contract-single-source-pillar2-gates.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
