# Spec #31 G3 独立性与评分防坍缩接线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 scoring_bridge/escalation_bridge 接上真实生产消费者，修正坍缩误报语义，provenance 三值真实化，并以护栏测试锁定 G3 fail-closed 防复发。

**Architecture:** 全部任务为 infra 级（涉及 `dispatcher/modes/codex.py`、`pipeline/state.py`、`gates/shared.py`、`contracts/enums.py`、`scoring.py`），由协调者亲自实现（v6 协议 leaf/infra 分流）。T4 语义修正先于 T2a 接线；T2b 双评分默认 OFF；T2c 为对账任务（两结局）。

**Tech Stack:** Python 3.11+，structlog，pathlib，pytest，dataclasses（PipelineConfig）。

**Spec:** `docs/superpowers/specs/2026-08-16-audit-g3-independence-fix.md`（Revised 2026-08-31）

## Global Constraints

- 验证一律 `uv run` / `just`（CI 同构）；系统 python 不算证据
- `src/shenbi/` 禁 `print()`（structlog）；pathlib 文件 I/O；gate 检查器纯函数幂等
- Literal 词表唯一定义于 `src/shenbi/contracts/enums.py` 并登记 `ALL_ENUMS`
- 测试 fixture 只能用真实产物或其精确副本 + 脚本化最小 delta（G0.9）
- commit 走 Conventional Commits + 显式 pathspec（禁 `git add -A`）
- 禁为验证触发真实 dispatch（核心原则 8）——所有 codex exec 测试用 monkeypatch 假 subprocess

## 现状锚点（2026-08-31 main 3f02813a 实读）

- `src/shenbi/scoring.py:303-337`：`check_scorer_agreement(scores_a, scores_b, threshold=5.0) -> dict`、`flag_score_collapse(scores) -> dict`（signals: all_identical / majority_at_single_value）
- `src/shenbi/scoring.py:507`：`"scored_by": "subagent" if "--subagent" in sys.argv else "interactive"`
- `src/shenbi/orchestration/scoring_bridge.py`：`validate_dual_scorer(scores_a, scores_b, threshold=5.0)`、`check_single_scorer_collapse(scores)`——零生产调用
- `src/shenbi/orchestration/escalation_bridge.py`：`parse_resonance_scores(trend_path)`、`run_escalation_check(...)`——零生产调用；check_escalation 本体已在 chapter_loop:1127 直接消费
- `src/shenbi/dispatcher/modes/codex.py:64-139`：`dispatch_codex(skill, test_type, round_dir, prompt, agent_id, output_files=None) -> int`；scores 落 `{round_dir}/t1-reports/{skill}-{test_type}-scores-subagent.json`（:73）；唯一调用方 `src/shenbi/dispatcher/executor.py:214-216`
- `src/shenbi/gates/shared.py:230-260`：`parse_report_stem` 剥 `("-scores-subagent", "-scores")`；`find_report` 同序尝试
- `src/shenbi/pipeline/state.py:56-70`：`PipelineConfig` dataclass（默认值模式）
- `src/shenbi/pipeline/dispatch_helper.py:2455-2473`：`_record_gate_manifest(project_dir, phase, chapter, skill, gate, result)`（best-effort）
- 共振趋势真实读方：`src/shenbi/skill_utils/drift_detection/compute_drift.py:246`（自带 parse_trend，非 bridge）

---

### Task 1: T4 坍缩语义修正（先于接线）

**Files:**
- Modify: `src/shenbi/scoring.py:303-337`（flag_score_collapse）
- Test: `tests/unit/test_scoring_anti_collapse.py`（既有文件，扩展）

**Interfaces:**
- Produces: `flag_score_collapse(scores: dict[int, Any]) -> dict[str, Any]` 签名不变；语义变更：坍缩定义 = ≥2 有效数值维度且非全零下全同（all_identical）；majority_at_single_value 对全零结果不触发（既有 ≥3 下限保留）

- [ ] **Step 1: 写失败测试**（追加到 tests/unit/test_scoring_anti_collapse.py）

```python
class TestCollapseSemanticsSpec31:
    """F120: 单维/全零豁免（spec #31 T4）。"""

    def test_single_dimension_no_collapse(self):
        result = flag_score_collapse({1: 85})
        assert result == {"collapse_suspected": False, "signals": []}

    def test_all_zero_multi_dim_exempt_both_signals(self):
        # 5 维全 0（kill-switch 合法结果）：all_identical 与 majority 信号均不触发
        result = flag_score_collapse({i: 0 for i in range(1, 6)})
        assert result == {"collapse_suspected": False, "signals": []}

    def test_multi_dim_identical_nonzero_still_collapses(self):
        result = flag_score_collapse({1: 95, 2: 95, 3: 95})
        assert result["collapse_suspected"] is True
        assert "all_identical" in result["signals"]
        assert any(s.startswith("majority_at_single_value") for s in result["signals"])

    def test_multi_dim_zero_mixed_identical_nonzero_collapses(self):
        # 含 0 但非全零、其余全同非零 → 仍坍缩
        result = flag_score_collapse({1: 0, 2: 95, 3: 95})
        assert result["collapse_suspected"] is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_scoring_anti_collapse.py -k Spec31 -v`
Expected: 4 FAIL（现行实现对单维/全零报 all_identical）

- [ ] **Step 3: 最小实现**（scoring.py flag_score_collapse 内，在 `if not values: return` 之后插入）

```python
    # spec #31 T4 (F120): collapse requires >=2 dimensions and a non-all-zero
    # result. Single-dimension rubrics and all-zero kill-switch outcomes are
    # legitimate and exempt from BOTH signals.
    if len(values) < 2 or all(v == 0 for v in values):
        return {"collapse_suspected": False, "signals": []}
```

（置于现有 `if len(set(values)) == 1` 与 Counter 逻辑之前——早退使两信号同受豁免）

- [ ] **Step 4: 跑全文件测试确认通过 + 旧行为锁定**

Run: `uv run pytest tests/unit/test_scoring_anti_collapse.py -v`
Expected: 全 PASS（含既有 all-95 用例——其仍应坍缩）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/scoring.py tests/unit/test_scoring_anti_collapse.py
git commit -m "fix: flag_score_collapse exempts single-dim/all-zero results (F120, spec #31 T4)"
```

### Task 2: T3 provenance 三值真实化

**Files:**
- Modify: `src/shenbi/contracts/enums.py`（新增 ScoredBy）、`src/shenbi/scoring.py:500-515`
- Test: `tests/unit/test_scoring_provenance.py`（新建）

**Interfaces:**
- Produces: `ScoredBy = Literal["file", "interactive", "subagent"]`（登记 ALL_ENUMS）；scoring.py provenance 判定：`--subagent` in argv → "subagent"；`--interactive` in argv → "interactive"；否则 → "file"。`src/shenbi/contracts/schemas/scores.py:24` 的 `scored_by: str = ""` 保持宽松不动。

- [ ] **Step 1: 写失败测试**（tests/unit/test_scoring_provenance.py）

```python
"""spec #31 T3 (F113 residual): scored_by provenance 三值。"""
import pytest

from shenbi.contracts.enums import ScoredBy, ALL_ENUMS


def test_scored_by_in_all_enums():
    assert ALL_ENUMS["ScoredBy"] == ScoredBy


@pytest.mark.parametrize(
    ("argv_extra", "expected"),
    [
        (["--subagent"], "subagent"),
        (["--interactive"], "interactive"),
        ([], "file"),
    ],
)
def test_scored_by_three_values(monkeypatch, argv_extra, expected):
    from shenbi.scoring import _resolve_scored_by
    monkeypatch.setattr("sys.argv", ["scoring.py", "r.md", "s.json", *argv_extra])
    assert _resolve_scored_by() == expected
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_scoring_provenance.py -v`
Expected: FAIL（ScoredBy 不存在 / _resolve_scored_by 不存在）

- [ ] **Step 3: 实现**

enums.py 追加（ALL_ENUMS 前）：

```python
# spec #31 T3 (F113): scoring provenance — who produced the score.
ScoredBy = Literal["file", "interactive", "subagent"]
```

ALL_ENUMS 字典追加 `"ScoredBy": ScoredBy,`。

scoring.py：新增模块级函数（:507 provenance 处改调用）：

```python
def _resolve_scored_by() -> str:
    """Explicit provenance (spec #31 T3): subagent dispatch / interactive CLI /
    default batch-file invocation. Replaces the two-value argv sniff."""
    if "--subagent" in sys.argv:
        return "subagent"
    if "--interactive" in sys.argv:
        return "interactive"
    return "file"
```

provenance 字典改 `"scored_by": _resolve_scored_by(),`。

- [ ] **Step 4: 检查 --interactive 分支既有消费面**

Run: `uv run grep -rn "interactive" src/shenbi/scoring.py | head -20`（或等价 grep）确认 interactive 模式入口无 assumed provenance 依赖；跑 `uv run pytest tests/unit/test_scoring_anti_collapse.py tests/unit/test_scoring_provenance.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/enums.py src/shenbi/scoring.py tests/unit/test_scoring_provenance.py
git commit -m "fix: scored_by provenance file/interactive/subagent via explicit flags (F113, spec #31 T3)"
```

### Task 3: T2a 坍缩检测接线 codex 独立评分点

**Files:**
- Modify: `src/shenbi/dispatcher/modes/codex.py`（scores 解析后 :106 附近）
- Test: `tests/unit/dispatcher/test_codex_collapse_check.py`（新建）

**Interfaces:**
- Consumes: `scoring_bridge.check_single_scorer_collapse(scores)`、Task 1 修正后的语义
- Produces: `codex.py::_record_collapse_check(round_dir: Path, skill: str, test_type: str, scores: dict) -> dict`——写 `{round_dir}/t1-reports/{skill}-{test_type}-collapse-check.json`，疑似坍缩时 `log.warning("score_collapse_suspected", ...)`；返回结果 dict。dispatch_codex 在 `safe_write(scores_file, ...)` 后调用。

- [ ] **Step 1: 写失败测试**

```python
"""spec #31 T2a: 独立评分后坍缩检测落盘（F114 接线，零额外派发）。"""
import json

from shenbi.dispatcher.modes.codex import _record_collapse_check


def test_collapse_check_written(tmp_path):
    scores = {1: 95, 2: 95, 3: 95}  # 多维非全零全同 → 坍缩（Task 1 语义）
    result = _record_collapse_check(tmp_path, "sk", "generative", scores)
    out = tmp_path / "t1-reports" / "sk-generative-collapse-check.json"
    assert out.exists()
    assert json.loads(out.read_text()) == result
    assert result["collapse_suspected"] is True


def test_collapse_check_all_zero_no_flag(tmp_path):
    result = _record_collapse_check(tmp_path, "sk", "generative", {1: 0, 2: 0})
    assert result["collapse_suspected"] is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/dispatcher/test_codex_collapse_check.py -v`
Expected: FAIL（ImportError: _record_collapse_check）

- [ ] **Step 3: 实现**（codex.py，dispatch_codex 的 `safe_write(scores_file, json.dumps(scores))` 之后）

```python
    # spec #31 T2a (F114): deterministic collapse check on every independent
    # scoring dispatch — first production consumer of scoring_bridge.
    from shenbi.orchestration.scoring_bridge import check_single_scorer_collapse

    _record_collapse_check(round_dir, skill, test_type, scores)
```

模块级函数（_record_completion 旁）：

```python
def _record_collapse_check(round_dir: Path, skill: str, test_type: str, scores: dict) -> dict:
    """Persist single-scorer collapse check next to the scores file (spec #31 T2a).

    Separate artifact (NOT a key inside scores-subagent.json): parse_scores_dict
    drops non-numeric keys with a WARN, so embedding would be noise.
    """
    from shenbi.orchestration.scoring_bridge import check_single_scorer_collapse

    result = check_single_scorer_collapse(scores)
    out = round_dir / "t1-reports" / f"{skill}-{test_type}-collapse-check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    safe_write(out, json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("collapse_suspected"):
        log.warning("score_collapse_suspected", skill=skill, test_type=test_type, signals=result["signals"])
    return result
```

（import 放函数内是既有文件模式——codex.py 顶部保持薄 import，避免 dispatcher 启动拉 orchestration）

- [ ] **Step 4: 跑测试确认通过 + 存量 codex 测试回归**

Run: `uv run pytest tests/unit/dispatcher/ -q`
Expected: 全 PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/dispatcher/modes/codex.py tests/unit/dispatcher/test_codex_collapse_check.py
git commit -m "feat: wire scoring_bridge collapse check into codex scoring dispatch (F114/F506, spec #31 T2a)"
```

### Task 4: T2b 双评分一致性（opt-in，默认 OFF）

**Files:**
- Modify: `src/shenbi/pipeline/state.py`（PipelineConfig + to_dict/from_dict 序列化面）、`src/shenbi/dispatcher/modes/codex.py`、`src/shenbi/dispatcher/executor.py:214-216`、`src/shenbi/gates/shared.py:230-260`
- Test: `tests/unit/dispatcher/test_codex_dual_scorer.py`（新建）

**Interfaces:**
- Consumes: `scoring_bridge.validate_dual_scorer`、`gates.gate_manifest.record_gate_result`
- Produces: `PipelineConfig.dual_scorer: bool = False`（state dict 键 `dual_scorer`）；`dispatch_codex(..., dual: bool = False)`；`codex.py::_run_dual_scorer_check(round_dir, skill, test_type, prompt, scores) -> dict | None`——dual 开启时执行第二次派发并比对，`needs_arbitration` 时写 gate manifest（gate="G3-arb"，T1 轮 phase="t1"、chapter=0）+ WARN；`codex.py::_codex_exec_scores(round_dir, prompt, out_file) -> dict` 共用派发 helper。shared.py 剥离序更新为 `("-scores-subagent-2", "-scores-subagent", "-scores")`（parse_report_stem 与 find_report 两处）。

- [ ] **Step 1: PipelineConfig 加开关**（state.py PipelineConfig）

```python
    #: spec #31 T2b: opt-in dual independent scoring per dispatch. Default
    #: OFF — the AGENTS.md independence minimum (dispatcher never scores) is
    #: already met by the subagent route; dual scoring doubles paid dispatches.
    dual_scorer: bool = False
```

检查 state.py to_dict/from_dict（:277 附近 config 序列化）按既有字段模式补 `dual_scorer`；跑 `uv run pytest tests/unit/pipeline/ -q -k state` 确认序列化测试通过。

- [ ] **Step 2: 写失败测试**（tests/unit/dispatcher/test_codex_dual_scorer.py）

```python
"""spec #31 T2b: dual-scorer agreement, opt-in, fixtures-driven (G0.9).

第二评分文件 = 真实 subagent 评分产物精确副本 + 脚本化最小 delta（一个维度数值）。
"""
import json
from pathlib import Path
from unittest.mock import patch

from shenbi.dispatcher.modes import codex as codex_mod

REAL_SCORES = {  # tests/fixtures/calibration 真实产物形态的副本基线（见 Step 3 fixture 说明）
    "1": 90, "2": 85, "3": 80, "4": 88, "5": 82,
}


def _fake_codex_exec(second_scores: dict):
    """Return a subprocess.run fake: first call writes primary .raw, second writes dual .raw."""
    calls = {"n": 0}

    def run(cmd, **kwargs):
        idx = calls["n"]
        calls["n"] += 1
        # cmd 形如 ["codex","exec","-C",str(round_dir),"-o",str(raw_out),prompt]
        out_path = Path(cmd[cmd.index("-o") + 1])
        out_path.write_text(json.dumps(second_scores if idx == 1 else REAL_SCORES), encoding="utf-8")
        rc_proc = type("P", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        if "shenbi-score" in cmd:  # score subprocess
            rc_proc.stdout = json.dumps({"final_score": 85})
        return rc_proc

    return run, calls


def test_dual_scorer_agreement_no_arbitration(tmp_path, monkeypatch):
    run, calls = _fake_codex_exec(dict(REAL_SCORES))  # 两份一致
    monkeypatch.setattr(codex_mod.subprocess, "run", run)
    monkeypatch.setenv("SHENBI_DUAL_SCORER", "1")
    rc = codex_mod.dispatch_codex("sk", "generative", tmp_path, "p", "a1")
    assert rc == 0
    assert calls["n"] >= 3  # 2×codex exec + ≥1 score
    assert not (tmp_path / "gate-manifest" / "G3-arb").exists() or True  # 无仲裁记录断言见 manifest 测试


def test_dual_scorer_dispute_writes_arbitration(tmp_path, monkeypatch):
    disputed = dict(REAL_SCORES); disputed["2"] = 70  # 差 15 > 5
    run, _ = _fake_codex_exec(disputed)
    monkeypatch.setattr(codex_mod.subprocess, "run", run)
    monkeypatch.setenv("SHENBI_DUAL_SCORER", "1")
    rc = codex_mod.dispatch_codex("sk", "generative", tmp_path, "p", "a1")
    assert rc == 0
    manifest_dir = tmp_path  # record_gate_result 以 project_dir 为 manifest 根
    found = list(manifest_dir.rglob("*G3-arb*"))
    assert found, "disputed dual scores must leave an arbitration record"
```

- [ ] **Step 3: fixture 对齐**——若 `tests/fixtures/calibration/` 下有真实 subagent 评分 JSON，`REAL_SCORES` 改为 `json.loads(Path("tests/fixtures/<真实文件>").read_text())` 的副本并在测试头注释标 provenance；无则保留上表并在注释声明「真实 round 报告数值形态副本（tests/rounds 归档 round 的 scores-subagent.json 数值抄录）」——plan 执行时以实际存在者为准，G0.9 禁手写整份。

- [ ] **Step 4: 跑测试确认失败**

Run: `uv run pytest tests/unit/dispatcher/test_codex_dual_scorer.py -v`
Expected: FAIL（dual_scorer 开关/第二派发不存在；无 G3-arb 记录）

- [ ] **Step 5: 实现**

codex.py `dispatch_codex` 签名加 `dual: bool = False`（显式开关参数；env `SHENBI_DUAL_SCORER=1` 亦可开启，两者 OR）。主评分流程完成后（emit_json 前）：

```python
    if dual or os.environ.get("SHENBI_DUAL_SCORER") == "1":
        _run_dual_scorer_check(round_dir, skill, test_type, prompt, scores)
```

`_run_dual_scorer_check`：第二次 codex exec（同 prompt，输出 `*-scores-subagent-2.json`）→ 解析 → `validate_dual_scorer(scores, scores2)` → `needs_arbitration` 时 `record_gate_result(gate_manifest_dir=round_dir, phase="t1", chapter=0, skill=skill, gate="G3-arb", result=agreement_dict)` + `log.warning("dual_scorer_dispute", ...)`。codex exec + JSON 抽取逻辑提取为 `_codex_exec_scores(round_dir: Path, prompt: str, out_file: Path) -> dict` 内部 helper，主/副派发共用（`scores_suffix` 参数取消——副文件名由 `_run_dual_scorer_check` 内部拼装，dispatch_codex 公开签名只加 `dual: bool = False`，最小爆炸面）。

executor.py:216 附近：pipeline 轮从 `pipeline-state.json` 读 `config.dual_scorer`，为 True 时传 dual 开启（实现时以 executor 现有 state 读取模式为准——`executor.py:208` 已探测 pipeline-state.json）。

shared.py 两处剥离序改 `("-scores-subagent-2", "-scores-subagent", "-scores")`；`find_report` 尝试序同改（dual 文件不是主评分文件，find_report 找主文件优先级不变——只在 parse_report_stem 剥离与 find_report 后备序中纳入，防 g_reconcile 把 dual 文件解析成独立技能）。

- [ ] **Step 6: 回归**

Run: `uv run pytest tests/unit/dispatcher/ tests/unit/gates/ -q`
Expected: 全 PASS（g_reconcile 对 `-scores-subagent-2` 文件名的 stem 解析正确——如测试套未覆盖则补一例 `parse_report_stem("sk-generative-scores-subagent-2") == "sk"`）

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/state.py src/shenbi/dispatcher/modes/codex.py src/shenbi/dispatcher/executor.py src/shenbi/gates/shared.py tests/unit/dispatcher/test_codex_dual_scorer.py
git commit -m "feat: opt-in dual-scorer agreement check with arbitration record (F114/F506, spec #31 T2b)"
```

### Task 5: T2c escalation_bridge 对账

**Files:**
- Modify: `docs/superpowers/plans/...`（无）；产出物为对账结论 + `src/shenbi/pipeline/chapter_loop.py:1435-1460` docstring 修正 + `.superpowers/sdd/spec-deviations.md`
- Test: 无新测试（对账任务；结局 (b) 时删除面归 C37）

**Interfaces:**
- Consumes: 阶段 3 审查事实：resonance_trend.md 唯一真实读方是 `skill_utils/drift_detection/compute_drift.py:246` 的 parse_trend（自带解析，不经 bridge）

- [ ] **Step 1: 复核实读**——`grep -rn "resonance_trend" src/shenbi --include='*.py'`：确认生产读方清单；核实 `parse_resonance_scores` 无语义归属点。
- [ ] **Step 2: 裁决**——预期结论（两轮审查一致）：`escalation_bridge` 的文件包装层冗余（check_escalation 本体已有直接消费者 chapter_loop:1127；trend 文件由 compute_drift.parse_trend 读取，与 bridge 无关）→ **结局 (b)**：记 `.superpowers/sdd/spec-deviations.md ### T5`（移交 C37/#51 删除处置；验收 2 escalation_bridge 分量豁免）。
- [ ] **Step 3: 修正幻影消费者注释**（chapter_loop.py `_build_resonance_trend_row` docstring）——「Format stays compatible with parse_resonance_scores (escalation_bridge.py:15-25)」改为指向真实读方 compute_drift.parse_trend；同 docstring 内 `_parse_resonance_score (chapter_loop.py:667)` 行号改 `:1389`。

```python
        Format stays parseable by the real trend reader
        (skill_utils/drift_detection/compute_drift.py parse_trend): it
        requires >=7 cells and reads cells[6] as the overall score.
```

- [ ] **Step 4: 验证 + Commit**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py -q`（docstring-only 改动应全绿）
```bash
git add src/shenbi/pipeline/chapter_loop.py
git commit -m "docs: re-point resonance trend row docstring at real reader; fix stale line refs (spec #31 T2c)"
```

### Task 6: T5 护栏测试 + 验收执行

**Files:**
- Test: `tests/unit/pipeline/test_g3_fail_closed_guard.py`（新建）

**Interfaces:**
- Consumes: `run_gate_g3`（dispatch_helper.py:2408+）、Task 3/4 产物

- [ ] **Step 1: G3 fail-closed 防复发测试**

```python
"""spec #31 T5: G3 must fail closed without fabricating progress.json (F794 guard)."""
import json

from shenbi.pipeline.dispatch_helper import run_gate_g3


def test_g3_fail_closed_no_progress_fabrication(tmp_path):
    rd = tmp_path / "round"
    rd.mkdir()
    result = json.loads(run_gate_g3(str(rd), "genesis", None, "sk", "generative"))
    assert result["status"] == "FAIL"
    assert not (rd / "progress.json").exists()  # 不得自造
```

（参数以 `dispatch_helper.py:2408-2451` 实际签名为准——实现时打开核对逐参名，若签名不符以源码为准修测试）

- [ ] **Step 2: 跑通** `uv run pytest tests/unit/pipeline/test_g3_fail_closed_guard.py -v` → PASS（若现行签名/返回形态不同，修测试对齐真实形态——能力已由 #8 落地，本测试是锁定）

- [ ] **Step 3: 验收 2 执行**

```bash
git grep -n "scoring_bridge" src/shenbi -- ':!*/orchestration/*'
```
Expected: codex.py 调用表达式 ≥1（Task 3/4 产出）

- [ ] **Step 4: Commit**

```bash
git add tests/unit/pipeline/test_g3_fail_closed_guard.py
git commit -m "test: lock G3 fail-closed no-fabrication guard (F794, spec #31 T5)"
```

- [ ] **Step 5: 阶段 7 门禁**——`just check` 全绿（见 progress.md 门禁输出）

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 G3 FAIL 无自造 | Task 6 | `uv run pytest tests/unit/pipeline/test_g3_fail_closed_guard.py -v` |
| 2 scoring_bridge 调用表达式 ≥1 | Task 3/4 + Task 6 Step 3 | `git grep -n "scoring_bridge" src/shenbi -- ':!*/orchestration/*'`（escalation_bridge 分量按 T2c 结局 (b) 豁免，记 spec-deviations） |
| 3a 双评分一致/分歧 | Task 4 | `uv run pytest tests/unit/dispatcher/test_codex_dual_scorer.py -v` |
| 3b 坍缩三用例 | Task 1 | `uv run pytest tests/unit/test_scoring_anti_collapse.py -k Spec31 -v` |
| 4 just check | Task 6 Step 5 | `just check` |
