# Spec #8 门禁有效性修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 spec #8（`docs/superpowers/specs/2026-08-14-gate-effectiveness-design.md`）的 R1-R7、R9 与 F402/F158/F417——G3 伪造证据、并行波无 G3、门序回归、GR.2 后缀、P2.5 空串、genre_config 空 rules、G7.1b 全集、G3.3 层级+producer、g4 路径解析、phase 穿越净化。R8/F163 已划归 #48，不在本 plan。

**Architecture:** 全部为既有 gate/校验器内部修复 + 一处 producer 接线（codex `_record_completion` 增可选 `output_files`）+ 一处并行波 G3 接线（chapter_loop 波完成后调 `run_gate_g3`）。无新模块、无契约 schema 变更、无新依赖。

**Tech Stack:** Python 3.11+, pydantic (decisions schema), pytest, structlog。

## Global Constraints

- 所有 task 均为 **infra** 级（gates/、pipeline/、dispatcher/、contracts/schemas/）→ 协调者亲自实现，不分派 implementer
- 验证命令一律 `uv run pytest ...`（与 CI `uv run --frozen` 同构）；系统 python 不算证据
- 禁真实 dispatch/pipeline（费 token + 写状态）；测试用 tmp_path + `tests/fixtures/` 真实产物
- `src/shenbi/` 无 `print()`；gate 检查器纯函数幂等；structlog 日志
- 状态字面量单一信源：不引入新的裸状态字符串
- commit 显式列文件路径（pathspec），禁 `git add -A`
- 执行顺序：**T1 必须先于 T2**（R1→R2 约束，spec 已声明）

---

### Task 1: R1 — 删除 run_gate_g3 伪造 progress 写入 + fail-closed

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:2266-2277`（run_gate_g3 开头的伪造块）
- Test: `tests/unit/pipeline/test_run_gate_g3_failclosed.py`（新建）

**Interfaces:**
- Produces: `run_gate_g3(skill: str, round_dir: Path | str, chapter: int | None = None, phase: str | None = None) -> dict[str, Any]`——progress.json 缺失时返回 `{"status": GateStatus.FAIL, "error": "no progress.json — fail-closed (F408)"}`（不再创建文件）；T2 依赖此行为

- [ ] **Step 1: 写失败测试**

```python
"""F408: run_gate_g3 must not fabricate progress.json evidence (fail-closed)."""
import json
from pathlib import Path

from shenbi.pipeline.dispatch_helper import run_gate_g3


def test_missing_progress_fails_closed_and_writes_nothing(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    result = run_gate_g3("shenbi-review-pacing", rd, chapter=1, phase="chapter_loop")
    assert result["status"] == "FAIL"
    assert not (rd / "progress.json").exists()  # no fabricated evidence written


def test_manifest_records_fail(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    run_gate_g3("shenbi-review-pacing", rd, chapter=1, phase="chapter_loop")
    manifest = rd / "pipeline-manifest.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert any(e.get("gate") == "G3" and e.get("status") == "FAIL" for e in _entries(data))


def _entries(data: dict) -> list[dict]:
    # gate_manifest.record_gate_result 的存储形状以实际实现为准；若为嵌套
    # {phase: {chapter: [...]}} 则递归展平
    out: list[dict] = []
    def walk(v: object) -> None:
        if isinstance(v, dict) and "gate" in v:
            out.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(data)
    return out
```

- [ ] **Step 2: `uv run pytest tests/unit/pipeline/test_run_gate_g3_failclosed.py -v` → FAIL（当前伪造写入使 G3 以 CLI 结果返回非 FAIL）**
- [ ] **Step 3: 实现——删除 dispatch_helper.py:2266-2277 的 `if not pp.exists(): safe_write(...)` 整块，替换为：**

```python
    rd = Path(round_dir)
    pp = rd / "progress.json"
    if not pp.exists():
        # F408: never fabricate scoring evidence. Missing progress.json = FAIL.
        log.error("g3_fail_closed_no_progress", skill=skill, path=str(pp))
        result = {"status": GateStatus.FAIL, "error": "no progress.json — fail-closed (F408)"}
        if chapter is not None and phase is not None:
            _record_gate_manifest(rd, phase, chapter, skill, "G3", result)
        return result
```

（若 `uuid4`/`safe_write` 因此不再被该文件其他处使用，同步清理 import。）

- [ ] **Step 4: `uv run pytest tests/unit/pipeline/test_run_gate_g3_failclosed.py -v` → PASS；再跑 `uv run pytest tests/unit -k run_gate_g3 -q` 确认无既有回归**
- [ ] **Step 5: `git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_run_gate_g3_failclosed.py && git commit -m "fix: F408 — run_gate_g3 fail-closed on missing progress.json, no fabricated scorer evidence (spec #8 R1)"`**

**验收对应（spec R1）：空 progress 目录 G3 FAIL ✓（Step 1 断言）**

---

### Task 2: R2 + F417 — 并行审计波接入 G3 + gate_manifest 行为测试

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:2655-2695`（core_wave / genre_wave 两个 `dispatch_reviews_parallel` 调用点之后）
- Test: `tests/unit/pipeline/test_parallel_wave_g3.py`（新建）、`tests/unit/gates/test_gate_manifest.py`（新建，F417）

**Interfaces:**
- Consumes: T1 的 fail-closed `run_gate_g3`；既有 `requires_independent`（dispatch_helper.py:354）、`_record_gate_manifest`（dispatch_helper.py:2306）、`record_gate_result`（gates/gate_manifest.py）
- Produces: 波完成后 manifest 含每个 `requires_independent` skill 的 G3 记录

- [ ] **Step 1: 写失败测试**

```python
"""F345: parallel audit waves must run G3 for requires_independent skills."""
import json
from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline import parallel_dispatch
# 编排函数名以 chapter_loop.py:2655 附近实际函数为准（审计波调度处）——
# 实施时先读该函数签名，测试直接调用「执行一章审计波」的函数或抽取的辅助函数
from shenbi.pipeline.chapter_loop import _run_audit_waves  # 若不存在则在本 task 抽取
```

（实施说明：2661/2688 两处调用点所在函数体较大、依赖 PipelineState。**本 task 的实现方式**：在 chapter_loop.py 抽取模块级辅助函数

```python
def _g3_parallel_wave(
    results: list[Any], skills: list[str], project_dir: Path, chapter: int
) -> list[dict[str, Any]]:
    """F345: run G3 for requires_independent skills after a parallel wave."""
    from shenbi.pipeline.dispatch_helper import requires_independent, run_gate_g3

    g3_results: list[dict[str, Any]] = []
    for skill in skills:
        if requires_independent(skill):
            g3 = run_gate_g3(skill, project_dir, chapter=chapter, phase="chapter_loop")
            g3_results.append({"skill": skill, "g3": g3})
    return g3_results
```

并在两处 `dispatch_reviews_parallel(...)` 之后各接一行 `_g3_parallel_wave(results, [t.skill for t in core_wave], Path(state.project_dir), chapter)`（genre_wave 同理）。测试直接测 `_g3_parallel_wave`：）

```python
def test_g3_parallel_wave_records_manifest(tmp_path: Path) -> None:
    from shenbi.pipeline.chapter_loop import _g3_parallel_wave

    project = tmp_path / "proj"
    project.mkdir()
    skills = ["shenbi-review-pacing", "shenbi-worldbuilding"]
    # review-* 技能契约为 requires_independent=True；worldbuilding 不是
    g3_results = _g3_parallel_wave([], skills, project, chapter=3)
    manifest = json.loads((project / "pipeline-manifest.json").read_text(encoding="utf-8"))
    g3_gates = [e for e in _flatten(manifest) if e.get("gate") == "G3"]
    assert {e["skill"] for e in g3_gates} == {"shenbi-review-pacing"}
    # T1 fail-closed：空 progress → FAIL 记录在案（真实证据缺失如实暴露）
    assert all(e["status"] == "FAIL" for e in g3_gates)
    assert len(g3_results) == 1
```

`_flatten` 复用 Task 1 测试的递归展平（复制进本文件——子 agent 不共享文件）。

- [ ] **Step 2: 跑测试 → FAIL（`_g3_parallel_wave` 不存在）**
- [ ] **Step 3: 实现抽取 + 两处接线**（如上）
- [ ] **Step 4: `uv run pytest tests/unit/pipeline/test_parallel_wave_g3.py -v` → PASS**
- [ ] **Step 5: F417——新建 `tests/unit/gates/test_gate_manifest.py` 行为级测试（record_gate_result 写入/读取往返、并发两线程写无 lost-update——用 manifest 模块自带的 per-path lock）**
- [ ] **Step 6: `uv run pytest tests/unit/gates/test_gate_manifest.py tests/unit/pipeline -q` → PASS**
- [ ] **Step 7: `git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_parallel_wave_g3.py tests/unit/gates/test_gate_manifest.py && git commit -m "fix: F345+F417 — parallel audit waves run G3 for independent skills; gate_manifest behavior tests (spec #8 R2)"`**

**验收对应（spec R2）：并行波审计后 gate-manifest 含 G3 记录 ✓**

---

### Task 3: R3 — executor G2 移至执行后

**Files:**
- Modify: `src/shenbi/dispatcher/executor.py:209-227`（dispatch 函数内 G2 块与 mode 分派）
- Test: `tests/unit/dispatcher/test_executor_gate_order.py`（新建；目录无 `__init__.py` 需求按既有 tests/unit 布局）

**Interfaces:**
- Produces: `dispatch(...)` 内 G2 仅在「输出文件已存在（预检查已有产物）」或「技能执行返回后」运行；执行前不再对不存在的输出跑 G2

- [ ] **Step 1: 写失败测试（顺序断言：G2 发生在 dispatch 之后）**

```python
"""F227: G2 must not validate outputs before skill execution."""
from pathlib import Path
from unittest.mock import patch

from shenbi.dispatcher import executor


def test_g2_runs_after_dispatch(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []
    rd = tmp_path / "round"
    rd.mkdir()

    def fake_dispatch(skill, test_type, round_dir, prompt, agent_id):
        calls.append("dispatch")
        return 0

    def fake_g2(outputs, file_type, round_dir):
        calls.append("g2")
        return {"status": "PASS"}

    monkeypatch.setenv("SHENBI_DISPATCH_MODE", "internal")
    with (
        patch.object(executor.modes_internal, "dispatch_internal", fake_dispatch)
        if hasattr(executor, "modes_internal")
        else patch("shenbi.dispatcher.modes.internal.dispatch_internal", fake_dispatch),
        patch.object(executor, "run_g2", fake_g2),
        patch.object(executor, "run_g1", lambda *a, **k: {"status": "PASS"}),
    ):
        rc = executor.dispatch("shenbi-worldbuilding", "generative", rd, "p")
    assert rc == 0
    assert calls == ["dispatch", "g2"]  # G2 after execution (fresh round: no pre-existing outputs)
```

（实施时按 executor 实际 import 形状调整 patch 目标；断言核心是 fresh round（无输出文件存在）时 dispatch 先于 g2。）

- [ ] **Step 2: 跑测试 → FAIL（当前顺序 ["g2", "dispatch"]——顺序断言变红）**
- [ ] **Step 3: 实现——dispatch() 中删除执行前 G2 块，改为：预存在输出则照旧预检（保持既有「重入」语义）；执行调用拿到 rc 后、返回前对 rc==0 跑 G2：**

```python
    output_files = derive_output_files(skill, chapter, round_dir, ctx=path_ctx)
    preexisting = [f for f in output_files if Path(f).exists()]
    is_pipeline = (round_dir / "pipeline-state.json").exists()

    mode = detect_mode()
    log.info("dispatch_mode", mode=mode)

    if mode == "codex":
        from shenbi.dispatcher.modes.codex import dispatch_codex
        rc = dispatch_codex(skill, test_type, round_dir, prompt, agent_id)
    else:
        from shenbi.dispatcher.modes.internal import dispatch_internal
        rc = dispatch_internal(skill, test_type, round_dir, prompt, agent_id)

    # F227: G2 runs AFTER execution (or pre-dispatch only for already-present outputs)
    if not is_pipeline and rc == 0:
        outputs = output_files if not preexisting else preexisting
        if outputs:
            g2 = run_g2(outputs, file_type, round_dir)
            if g2.get("status") != "PASS":
                log.error("g2_failed", gate="G2", result=g2)
                return 1
            log.info("gate_passed", gate="G2")
    return rc
```

- [ ] **Step 4: `uv run pytest tests/unit/dispatcher -q`（含新测试）→ PASS；`uv run pytest tests/unit -k executor -q` 无回归**
- [ ] **Step 5: `git add src/shenbi/dispatcher/executor.py tests/unit/dispatcher/test_executor_gate_order.py && git commit -m "fix: F227 — executor G2 moves post-execution; pre-dispatch G2 only for pre-existing outputs (spec #8 R3)"`**

**验收对应（spec R3）：fresh round worldbuilding 派发不再在执行前 G2 FAIL ✓（monkeypatch 驱动真实 dispatch 代码路径）**

---

### Task 4: R4 — g_reconcile GR.2 后缀剥离

**Files:**
- Modify: `src/shenbi/gates/g_reconcile.py:50-68`
- Test: `tests/unit/gates/test_g_reconcile.py`（改既有：删规避注释，加生产命名用例）

- [ ] **Step 1: 修测试——删除 docstring 中「parser does NOT strip...sidesteps the parser bug」类规避说明，新增：**

```python
def test_gr2_production_scores_suffix_not_false_fail(tmp_path: Path) -> None:
    """F401: production names <skill>-generative-scores(-subagent).json must not false-FAIL."""
    skill = "shenbi-worldbuilding"
    for name in (f"{skill}-generative-scores.json", f"{skill}-generative-scores-subagent.json"):
        reports = tmp_path / "t1-reports"
        reports.mkdir(exist_ok=True)
        (reports / name).write_text("{}", encoding="utf-8")
        progress = tmp_path / "progress.json"
        progress.write_text(
            json.dumps({"skills": {skill: {"generative": {"status": "DONE"}}}}), encoding="utf-8"
        )
        result = gate_G_RECONCILE(str(tmp_path))
        assert "GR.2" not in result  # status DONE (uppercase, per F449 boundary) + suffix stripped
        shutil.rmtree(reports)
```

- [ ] **Step 2: 跑 → FAIL（当前后缀未剥离恒报 GR.2）**
- [ ] **Step 3: 实现——stem 解析前剥离后缀：**

```python
            stem = rp.stem
            for suffix in ("-subagent", "-scores"):
                stem = stem.removesuffix(suffix)
            matched = False
```

（rsplit 循环体不变，用剥离后的 stem。）

- [ ] **Step 4: `uv run pytest tests/unit/gates/test_g_reconcile.py -v` → PASS**
- [ ] **Step 5: `git add src/shenbi/gates/g_reconcile.py tests/unit/gates/test_g_reconcile.py && git commit -m "fix: F401 — GR.2 strips -scores/-subagent suffixes; remove test masking (spec #8 R4)"`**

**验收对应（spec R4）：生产命名（含 -subagent）+ DONE → 不因后缀 FAIL ✓（大小写归一属 #27，不在本 task）**

---

### Task 5: R5 — P2.5 rationale 空串（Selection + Adjustment）

**Files:**
- Modify: `src/shenbi/contracts/schemas/decisions.py:33`（Selection._p25）、`:52-58`（Adjustment._rationale）
- Test: `tests/unit/contracts/test_decisions_p25_empty.py`（新建；路径按既有 decisions 测试位置就近）

- [ ] **Step 1: 写失败测试**

```python
"""F404/F458: empty/whitespace rationale must fail P2.5 REQUIRED."""
import pytest
from pydantic import ValidationError

from shenbi.contracts.schemas.decisions import Adjustment, Selection


def test_selection_manual_override_empty_rationale_rejected() -> None:
    with pytest.raises(ValidationError, match="rationale REQUIRED"):
        Selection(item_id="a", basis="manual_override", severity="low", rationale="  ")


def test_adjustment_empty_rationale_rejected() -> None:
    with pytest.raises(ValidationError):
        Adjustment(issue_id="i", severity="low", handling="applied", rationale="")
```

（Selection/Adjustment 字段名以实际 schema 为准——实施时打开文件核对必填字段后再定测试构造。）

- [ ] **Step 2: 跑 → FAIL（空串当前通过）**
- [ ] **Step 3: 实现**

Selection._p25: `has = bool(rationale and rationale.strip())`
Adjustment._rationale 增：

```python
        if not self.rationale or not self.rationale.strip():
            raise ValueError("rationale REQUIRED (non-empty) for adjustments")
```

- [ ] **Step 4: `uv run pytest tests/unit -k decisions -q` → PASS**
- [ ] **Step 5: `git add src/shenbi/contracts/schemas/decisions.py tests/unit/contracts/test_decisions_p25_empty.py && git commit -m "fix: F404+F458 — P2.5 rejects empty/whitespace rationale in Selection and Adjustment (spec #8 R5)"`**

---

### Task 6: R6 — genre_config 空 customRules 不跳过

**Files:**
- Modify: `src/shenbi/contracts/skills/genre_config.py:94`
- Test: `tests/unit/contracts/test_genre_config_contract.py`（既有文件，就近新增用例）

- [ ] **Step 1: 失败测试**（字段构造以 `src/shenbi/contracts/skills/genre_config.py` 实际 schema 为准——实施时打开核对；下例为骨架）：

```python
def test_disabled_dim_with_empty_custom_rules_rejected() -> None:
    """F216: empty customRules must not skip the disabled-dimension rule check."""
    with pytest.raises(ValidationError):
        GenreConfig(
            # ... 禁用某一维度（如 "伏笔"）, custom_rules=[] （customRules 别名默认空）
        )
```
- [ ] **Step 2: 跑 → FAIL**
- [ ] **Step 3: 实现**：`if disabled and self.custom_rules:` → `if disabled:`（循环体内对空 rules 自然产出未命中）
- [ ] **Step 4: `uv run pytest tests/unit -k genre_config -q` → PASS**
- [ ] **Step 5: commit `fix: F216 — disabled-dimension rule check no longer skipped on empty customRules (spec #8 R6)`**

---

### Task 7: R7 — G7.1b 反向覆盖以脚手架全集为准

**Files:**
- Modify: `src/shenbi/gates/g7.py:36-62`（G7.1/G7.1b 的 `set(ALL_SKILLS)` 用法）、`src/shenbi/gates/shared.py`（新增 `T1_SCAFFOLD_SKILLS`）
- Test: `tests/unit/gates/test_g7_reverse_coverage.py`（新建）

**Interfaces:**
- Produces: `T1_SCAFFOLD_SKILLS: tuple[str, ...]`（shared.py，`= tuple(sorted(p.name for p in (TESTS / "tiers" / "t1-skill").iterdir() if p.is_dir() and p.name != "_template"))`，TESTS 常量 shared.py 已有则复用）

- [ ] **Step 1: 失败测试**：summary.json 覆盖全部 69 脚手架技能（从 `tests/tiers/t1-skill` 实际目录名程序化生成——非手写 fixture，满足 G0.9）→ G7.1b 无 `missing_coverage`；且 group-*/lifecycle 5 技能不在 missing 集合。
- [ ] **Step 2: 跑 → FAIL（当前 ALL_SKILLS=74 恒 missing 5）**
- [ ] **Step 3: 实现**（定案）：**G7.1b 用 `set(T1_SCAFFOLD_SKILLS)`；G7.1 幻觉检测用 `set(T1_SCAFFOLD_SKILLS) | set(ALL_SKILLS)` 并集**（不放松幻觉检测）
- [ ] **Step 4: `uv run pytest tests/unit/gates/test_g7* -q` → PASS**
- [ ] **Step 5: commit `fix: F432 — G7.1b reverse coverage anchored to t1-skill scaffold set (69) (spec #8 R7)`**

---

### Task 8: R9 — G3.3 读 test_type 层 + producer 写 output_files + except 补洞

**Files:**
- Modify: `src/shenbi/gates/g3.py:151-156`（读侧）、`:188/:205`（except）、`src/shenbi/dispatcher/modes/codex.py:20-46`（_record_completion + 调用点 :115）
- Test: 改 `tests/unit/gates/test_g3.py:118/:220`（生产形状）

**Interfaces:**
- Produces: `_record_completion(round_dir: Path, skill: str, test_type: str, score: float, output_files: list[str] | None = None) -> None`——写入 `skills[skill][test_type]["output_files"]`；g3.py 读 `skills[skill][test_type or "generative"]["output_files"]`

- [ ] **Step 1: 实证钉死异常类型（spec round-2 要求）**：`uv run python -c "from shenbi.gates.g2 import gate_G2; import tempfile,pathlib,json; p=pathlib.Path(tempfile.mkdtemp())/'x.json'; p.write_text('[1,2]'); print(gate_G2(str(p),'report',str(p.parent)))"` → 观察非 dict JSON 的实际行为（gate_G2 内部已 try/except 则无异常穿透，except 扩展按实证结果决定：若 gate_G2 不抛则 g3.py:188 无需扩 ValueError，改为实证记录 + 注释；若抛 AttributeError 则扩入 AttributeError）——**结论写进 spec-deviations T8 段**
- [ ] **Step 2: 失败测试**——test_g3.py 改用真实 producer 构造 progress：

```python
def test_g33_executes_on_production_shape(tmp_path: Path) -> None:
    from shenbi.dispatcher.modes.codex import _record_completion

    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "skill-output").mkdir()
    out = rd / "skill-output" / "outline.md"
    out.write_text("# 大纲\n\n正文段落。" * 5, encoding="utf-8")
    _record_completion(rd, "shenbi-worldbuilding", "generative", 95.0, output_files=[str(out)])
    result = json.loads(gate_G3("shenbi-worldbuilding", "generative", str(rd)))
    g33 = [c for c in result["checks"] if c["id"] == "G3.3"]
    assert g33 and g33[0]["s"] == "PASS"  # G3.3 actually executed and passed (路径含 outline/ 命中 report 分支时用 outline/ 目录；实施时使 output 落在 outline/ 命名下)
```

（result 结构以 gate_G3 实际返回为准，实施时核对 checks 键名。）
- [ ] **Step 3: 跑 → FAIL（读侧在 skill 层，恒 SKIP）**
- [ ] **Step 4: 实现**：g3.py 读侧 `output_files = (skill_data.get(test_type or "generative", {}) if isinstance(skill_data, dict) else {}).get("output_files", [])`；codex.py `_record_completion` 增可选参并写入；调用点 :115 从 `derive_output_files`/上层传入（若该调用点无现成 output_files 变量，实施时上溯一层取契约 writes 展开值，作为 `output_files=` 实参）
- [ ] **Step 5: `uv run pytest tests/unit/gates/test_g3.py tests/unit/dispatcher -q` → PASS**
- [ ] **Step 6: commit `fix: F444 — G3.3 reads output_files at test_type layer; producer records output_files (spec #8 R9)`**

**验收对应（spec R9）：经真实 producer 写入的 progress + G3 → G3.3 非 SKIP ✓；pipeline materialize 路径 SKIP-by-design 记 spec-deviations**

---

### Task 9: F402 — length_normalizing 用解析后路径计字数

**Files:**
- Modify: `src/shenbi/gates/g4/length_normalizing.py:35`
- Test: 就近新增回归用例（`tests/unit/gates/g4/` 既有测试文件）

- [ ] **Step 1: 失败测试**：`rd` 传绝对 round_dir、fp 传相对名 `skill-output/xxx.md`（真实 fixtures 引用或 tmp_path 构造同形状文件）→ checker 不抛 ValueError，产出检查结果
- [ ] **Step 2: 跑 → FAIL（resolve_input_path 对裸相对名抛 ValueError）**
- [ ] **Step 3: 实现**：`wc = word_count_md(fp)` → `wc = word_count_md(pf)`
- [ ] **Step 4: `uv run pytest tests/unit/gates -k length -q` → PASS**
- [ ] **Step 5: commit `fix: F402 — length_normalizing counts words on resolved path (spec #8 补充)`**

---

### Task 10: F158 — phase_runner phase 参数净化

**Files:**
- Modify: `src/shenbi/phase_runner.py:37`（load_state）与 save_state（同型拼接处）
- Test: `tests/unit/test_phase_runner_sanitize.py`（新建，位置按既有 phase_runner 测试就近）

**Interfaces:**
- Produces: 模块级 `_sanitize_phase(phase: str) -> str`——仅允许 `[A-Za-z0-9_-]+`，违规 `raise ValueError(f"invalid phase name: {phase!r}")`（fail-loud，不静默清洗）；load_state/save_state 入口调用

- [ ] **Step 1: 失败测试**：`load_state("../evil", rd)` → pytest.raises(ValueError)；合法名 `"t2-genesis"` 正常往返
- [ ] **Step 2: 跑 → FAIL（当前写出 round_dir 外）**
- [ ] **Step 3: 实现**（re.fullmatch + raise；CLI main 处 ValueError 自然冒泡为非零退出）
- [ ] **Step 4: `uv run pytest tests/unit -k phase_runner -q` → PASS**
- [ ] **Step 5: commit `fix: F158 — sanitize phase param against path traversal in phase_runner state files (spec #8 补充)`**

---

## 验收覆盖表（spec 验收 → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| R1 空 progress 目录 G3 FAIL | T1 | `uv run pytest tests/unit/pipeline/test_run_gate_g3_failclosed.py -v` |
| R2 并行波后 manifest 含 G3 | T2 | `uv run pytest tests/unit/pipeline/test_parallel_wave_g3.py -v` |
| R3 fresh round worldbuilding 派发 PASS | T3 | `uv run pytest tests/unit/dispatcher/test_executor_gate_order.py -v` |
| R4 生产命名+DONE 不因后缀 FAIL | T4 | `uv run pytest tests/unit/gates/test_g_reconcile.py -v` |
| R5 空串 rationale REJECT（两处） | T5 | `uv run pytest tests/unit -k decisions -q` |
| R6 disabled+空 rules → REJECT | T6 | `uv run pytest tests/unit -k genre_config -q` |
| R7 脚手架全集反推 | T7 | `uv run pytest tests/unit/gates/test_g7_reverse_coverage.py -v` |
| R9 G3.3 非 SKIP | T8 | `uv run pytest tests/unit/gates/test_g3.py -v` |
| F402 相对路径不崩 | T9 | `uv run pytest tests/unit/gates -k length -q` |
| F158 穿越 REJECT | T10 | `uv run pytest tests/unit -k phase_runner -q` |

评分场景：无（全部为确定性校验逻辑，无 LLM 产物评分）→ 无需 G3.4 评分子 agent。
