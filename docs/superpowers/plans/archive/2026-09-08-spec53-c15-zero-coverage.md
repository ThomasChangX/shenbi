# SDD #53 · C15 零覆盖修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 C15 簇修订后 10 个零/低覆盖面建立行为级测试 + per-module 覆盖率底线表（tests-only，不动生产代码）。

**Architecture:** 新增 5 个测试文件（每簇面独立可 revert）+ 1 个覆盖底线校验脚本（tools/，数据源为 pytest --cov JSON）。全部测试走真实代码路径；fixtures 用真实产物；tmp_path 隔离。

**Tech Stack:** pytest（monkeypatch/tmp_path）、coverage.py（json report）、现有 `just check` 门禁链。

**Spec:** `docs/superpowers/specs/archive/2026-08-16-audit-zero-coverage-fix.md`（Revised 2026-09-08）

## Global Constraints

- 不动 `src/shenbi/` 生产代码（spec 风险与回滚节）；本 plan 全部改动在 tests/ + tools/ + 配置
- G0.9：checker 输入只可用真实产物 fixtures（`tests/fixtures/book-spine-example.md`、`tests/fixtures/arc-example.md`）；conftest.py:79 的 book_spine.md 手写脚手架禁止作为 checker 输入
- 红灯验证法：每个新测试文件至少一处「破坏被测逻辑 → 红 → 还原」并记录
- 覆盖率底线只对本簇 10 面，5–10pp 余量；全局 fail_under=85 不变
- 命令一律 `uv run pytest ...` / `just check`（与 CI 同构）
- 所有 commit 走 Conventional Commits + pathspec add（禁 `git add -A`）

---

### Task 1: F112 — sync_contracts render/main 行为级测试（spec T1 项 1）

**Files:**
- Create: `tests/unit/test_sync_contracts_render.py`

**Interfaces:**
- Consumes: `shenbi.sync_contracts` 模块级常量与函数（真实签名，src/shenbi/sync_contracts.py:27-31 常量、:124 `render_body_view(skill: str, contract: dict[str, Any]) -> str`、:137 `render_body_into(skill_md: Path, contract: dict[str, Any]) -> None`、:159 `_write_json(path: Path, data: Any) -> None`、:164 `main() -> int`）；`load_all_contracts()`/`load_registry()`（同模块 :21/:38）
- Produces: 无（测试叶子）

- [ ] **Step 1: 写单元级测试**（render_body_view 语义、render_body_into 幂等注入/替换/无 frontmatter 分支、_write_json mkdir+内容）

```python
"""Behavioral tests for sync_contracts render/main (F112, spec #53 C15).

All writes go through tmp_path copies — sync_contracts is the in-repo
mutator that rewrites deps.json + every SKILL.md (never operate on real files).
"""

from pathlib import Path

import pytest

import shenbi.sync_contracts as sc


def test_render_body_view_lists_roles() -> None:
    view = sc.render_body_view("shenbi-x", {"reads": ["a.md"], "writes": ["b.md"], "updates": []})
    assert "## 数据契约" in view
    assert "- **Reads:** a.md" in view
    assert "- **Writes:** b.md" in view
    assert "- **Updates:** none" in view
    assert view.startswith(sc.BODY_BANNER) and sc.BODY_END in view


def test_render_body_into_prepends_when_missing(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("---\nname: x\n---\n\nbody text\n", encoding="utf-8")
    sc.render_body_into(skill_md, {"reads": [], "writes": ["w.md"], "updates": []})
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---\nname: x\n---")  # frontmatter intact
    assert sc.BODY_BANNER in text and "body text" in text
    # idempotent: re-render is replace not append
    sc.render_body_into(skill_md, {"reads": [], "writes": ["w.md"], "updates": []})
    assert skill_md.read_text(encoding="utf-8") == text


def test_render_body_into_replaces_existing_block(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        "---\nname: x\n---\n" + sc.render_body_view("x", {"reads": [], "writes": ["old"], "updates": []}) + "tail\n",
        encoding="utf-8",
    )
    sc.render_body_into(skill_md, {"reads": [], "writes": ["new"], "updates": []})
    text = skill_md.read_text(encoding="utf-8")
    assert "**Writes:** new" in text and "**Writes:** old" not in text and "tail" in text


def test_render_body_into_no_frontmatter_is_noop_with_warning(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    original = "no frontmatter here\n"
    skill_md.write_text(original, encoding="utf-8")
    sc.render_body_into(skill_md, {"reads": [], "writes": ["w"], "updates": []})
    assert skill_md.read_text(encoding="utf-8") == original  # F130 branch: not silent


def test_write_json_creates_parents_and_content(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "out.json"
    sc._write_json(target, {"k": "值"})
    import json

    assert json.loads(target.read_text(encoding="utf-8")) == {"k": "值"}
    assert target.read_text(encoding="utf-8").endswith("\n")
```

- [ ] **Step 2: 写 main() 端到端测试**（monkeypatch 模块常量指向 tmp 副本）

```python
def _make_tmp_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Point sync_contracts module constants at a tmp copy; return paths."""
    # tiny two-skill fake: one contract-bearing SKILL.md + deps.json with one phase
    skills = tmp_path / "skills"
    (skills / "shenbi-alpha").mkdir(parents=True)
    (skills / "shenbi-alpha" / "SKILL.md").write_text(
        "---\nname: shenbi-alpha\ncontract:\n  kind: artifact\n  reads: [truth/a.md]\n"
        "  writes: [out/alpha.md]\n  updates: []\n---\n\nalpha body\n",
        encoding="utf-8",
    )
    deps = tmp_path / "deps.json"
    deps.write_text(
        json.dumps({"t2-phases": {"p1": {"prerequisites": ["shenbi-alpha"], "expected_outputs": []}}}),
        encoding="utf-8",
    )
    dag = tmp_path / "dag.json"
    index = tmp_path / "index.json"
    monkeypatch.setattr(sc, "SKILLS", skills)
    monkeypatch.setattr(sc, "DEPS_PATH", deps)
    monkeypatch.setattr(sc, "DAG_PATH", dag)
    monkeypatch.setattr(sc, "INDEX_PATH", index)
    return {"skills": skills, "deps": deps, "dag": dag, "index": index}


def test_main_end_to_end_regenerates_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _make_tmp_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(sc, "load_all_contracts", lambda: {
        "shenbi-alpha": {"kind": "artifact", "reads": ["truth/a.md"], "writes": ["out/alpha.md"], "updates": []}
    })
    monkeypatch.setattr(sc, "load_registry", lambda: _real_load_registry())
    assert sc.main() == 0
    # deps.json: expected_outputs regenerated in place, org fields preserved
    deps_out = json.loads(paths["deps"].read_text(encoding="utf-8"))
    assert deps_out["t2-phases"]["p1"]["expected_outputs"] == ["out/alpha.md"]
    # dag + index written
    assert paths["dag"].exists() and paths["index"].exists()
    assert json.loads(paths["index"].read_text(encoding="utf-8"))["truth/a.md"]["reads"] == ["shenbi-alpha"]
    # SKILL.md got the auto block and kept its body
    skill_text = (paths["skills"] / "shenbi-alpha" / "SKILL.md").read_text(encoding="utf-8")
    assert sc.BODY_BANNER in skill_text and "alpha body" in skill_text


def test_main_bails_when_no_contracts(tmp_path, monkeypatch):
    _make_tmp_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(sc, "load_all_contracts", lambda: {})
    assert sc.main() == 1


def test_main_fails_closed_on_corrupt_deps(tmp_path, monkeypatch):
    _make_tmp_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(sc, "load_all_contracts", lambda: {"x": {"kind": "artifact", "reads": [], "writes": ["w"], "updates": []}})
    paths_dir = tmp_path
    (paths_dir / "deps.json").write_text("{corrupt", encoding="utf-8")
    assert sc.main() == 1
    assert not (paths_dir / "dag.json").exists()  # no partial writes
```

注意：`_real_load_registry` 直接 `from shenbi.contracts.loader import load_registry`（真实注册表，只读）；`load_all_contracts` 打桩因其读全仓 SKILLS。若 `derive_expected_outputs` 对 fake contract 需要 registry 命中 `truth/a.md`，按真实 registry glob 调整 fake 写入路径使 bijection 成立（红灯阶段暴露）。

- [ ] **Step 3: 运行** `uv run pytest tests/unit/test_sync_contracts_render.py -v` — 预期先红（模块属性名/行为不符处修测试到符合真实语义）
- [ ] **Step 4: 红灯验证**：临时改 `render_body_view` 本地副本断言（或对 `sc.BODY_END` 换哨兵字符串）→ 测试红 → 还原 → 绿。记录于 progress.md
- [ ] **Step 5: Commit** `git add tests/unit/test_sync_contracts_render.py && git commit -m "test: behavioral coverage for sync_contracts render/main (F112, spec #53)"`

---

### Task 2: F417/F765 — g4 检查器三态用例（spec T1 项 2）

**Files:**
- Create: `tests/unit/gates/g4/test_c15_checker_three_state.py`

**Interfaces:**
- Consumes: `g4_memory_distill(fps: list[str], rd: str | None = None, project_dir: str | None = None, repo_root: str | None = None) -> str`（src/shenbi/gates/g4/memory_distill.py:12）；`g4_book_spine_init`（同签名，src/shenbi/gates/g4/book_spine_init.py:10）；fixtures `tests/fixtures/arc-example.md`（generated_by: shenbi-memory-distill）、`tests/fixtures/book-spine-example.md`
- Produces: 无

- [ ] **Step 1: 三态用例**（每检查器 PASS/FAIL/SKIP；输入真实 fixture 复制件或构造的缺失文件路径——文件路径本身不是 fixture，checker 的 not_found 分支本就以路径为输入）

```python
"""Three-state (PASS/FAIL/SKIP) behavioral tests for zero-coverage G4 checkers (F417/F765, spec #53)."""

import shutil
from pathlib import Path

import pytest

from shenbi.gates.g4.book_spine_init import g4_book_spine_init
from shenbi.gates.g4.memory_distill import g4_memory_distill

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


class TestMemoryDistillChecker:
    def test_pass_on_real_artifact(self, tmp_path: Path) -> None:
        fp = tmp_path / "arc.md"
        shutil.copy(FIXTURES / "arc-example.md", fp)
        out = g4_memory_distill([str(fp)])
        assert '"s": "PASS"' in out or "PASS" in out  # 以 shared.passed 实际序列化形态断言（红灯期校准）

    def test_fail_missing_section(self, tmp_path: Path) -> None:
        fp = tmp_path / "arcs.md"  # arc-named → requires 事件链/伏笔/角色状态
        fp.write_text("第3章 摘要\n", encoding="utf-8")
        out = g4_memory_distill([str(fp)])
        assert "missing_section" in out and "FAIL" in out

    def test_fail_no_chapter_ref(self, tmp_path: Path) -> None:
        fp = tmp_path / "summary.md"
        fp.write_text("事件链 x 伏笔 y 角色状态 z\n", encoding="utf-8")
        out = g4_memory_distill([str(fp)])
        assert "no_chapter_ref" in out

    def test_fail_not_found(self) -> None:
        out = g4_memory_distill(["nonexistent-arc.md"])
        assert "not_found" in out

    def test_skip_when_no_files(self) -> None:
        out = g4_memory_distill([])
        assert "SKIP" in out


class TestBookSpineInitChecker:
    def test_pass_on_real_artifact(self, tmp_path: Path) -> None:
        fp = tmp_path / "book_spine.md"
        shutil.copy(FIXTURES / "book-spine-example.md", fp)
        # 若真实 fixture 缺必需字段/章节 → 该用例断言其真实结果（FAIL 也记录 provenance deviation），禁止改 fixture 凑 PASS
        out = g4_book_spine_init([str(fp)])
        assert "book-spine-init" in out

    def test_fail_missing_required_fields(self, tmp_path: Path) -> None:
        fp = tmp_path / "book_spine.md"
        fp.write_text("# 空壳\n核心冲突 x\nthemes y\n主角弧 z\n主线钩子 w\n", encoding="utf-8")
        out = g4_book_spine_init([str(fp)])
        assert "missing_field" in out and "FAIL" in out

    def test_fail_missing_sections(self, tmp_path: Path) -> None:
        fp = tmp_path / "book_spine.md"
        fp.write_text("---\nupdated: 2026-01-01\ntotal_chapters: 100\nstatus: active\n---\n", encoding="utf-8")
        out = g4_book_spine_init([str(fp)])
        assert "missing_section" in out

    def test_skip_when_no_files(self) -> None:
        out = g4_book_spine_init([])
        assert "SKIP" in out
```

- [ ] **Step 2: 运行** `uv run pytest tests/unit/gates/g4/test_c15_checker_three_state.py -v`；PASS 断言按 `passed()/fail()`（shenbi.gates.shared）真实序列化输出校准
- [ ] **Step 3: 红灯验证**（注释掉 memory_distill 的 no_chapter_ref 检查副本逻辑或等价破坏）→ 红 → 还原 → 绿，记录
- [ ] **Step 4: Commit** `git add tests/unit/gates/g4/test_c15_checker_three_state.py && git commit -m "test: three-state coverage for g4 memory_distill/book_spine_init checkers (F417/F765, spec #53)"`

---

### Task 3: F216 — dispatcher/cli.py + executor 分支（spec T2 项 3）

**Files:**
- Create: `tests/unit/dispatcher/test_c15_cli_and_executor_branches.py`

**Interfaces:**
- Consumes: `shenbi.dispatcher.cli.main() -> int`（src/shenbi/dispatcher/cli.py:15）；`shenbi.dispatcher.executor.dispatch(skill, test_type, round_dir, prompt) -> int`（executor.py:166）；`dispatch_with_write_audit`（executor.py:270+）
- Produces: 无

- [ ] **Step 1: cli.main 矩阵**

```python
"""Branch coverage for dispatcher/cli.py main + executor gate-failure/env branches (F216, spec #53)."""

import sys
from pathlib import Path

import pytest

import shenbi.dispatcher.cli as dcli


def test_main_usage_returns_1(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["shenbi-dispatch", "only-two"])
    assert dcli.main() == 1


def test_main_forwards_with_joined_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {}
    monkeypatch.setattr(sys, "argv", ["shenbi-dispatch", "skill", "generative", "/tmp/rd", "multi", "word", "prompt"])
    monkeypatch.setattr(dcli, "dispatch", lambda s, t, rd, p: (calls.update(args=(s, t, rd, p)), 0)[1])
    assert dcli.main() == 0
    assert calls["args"] == ("skill", "generative", Path("/tmp/rd"), "multi word prompt")  # F267 join


def test_main_propagates_dispatch_rc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["shenbi-dispatch", "s", "t", "/tmp/rd", "p"])
    monkeypatch.setattr(dcli, "dispatch", lambda *a: 2)
    assert dcli.main() == 2
```

- [ ] **Step 2: executor 分支**（G1-fail → rc1；G2-fail → rc1；dispatch-failure rc 透传；SHENBI_G1_SKIP_READS 过滤块）。策略：monkeypatch `executor.run_g1`/`run_g2`/`detect_mode`+`dispatch_internal`（入口桩，被测分支是 executor 自身逻辑）；env 块用真实 `derive_input_files` 输出 + `SHENBI_G1_SKIP_READS=optional-*.md` + 不存在的 optional 文件 → 断言 `run_g1` 收到的列表已过滤（通过捕获参数）。G1-fail：`run_g1` 返回 `{"status": "FAIL"}` → rc==1；G2-fail：`dispatch_internal` rc==0、`run_g2` FAIL、非 pipeline → rc==1；**dispatch-failure 透传（spec T2 项 3 点名）**：`dispatch_internal` 返回 rc==3 → 断言最终 rc==3 且 `run_g2` 未被调用（monkeypatch 计数 0，executor.py:257 的 `rc == 0` 短路分支）
- [ ] **Step 3: 运行** `uv run pytest tests/unit/dispatcher/test_c15_cli_and_executor_branches.py -v` — 红到绿
- [ ] **Step 4: 红灯验证**（反转 G1-fail 返回值一处）→ 红 → 还原，记录
- [ ] **Step 5: Commit** `git add tests/unit/dispatcher/test_c15_cli_and_executor_branches.py && git commit -m "test: dispatcher cli argv matrix + executor G1/G2-fail and skip-reads branches (F216, spec #53)"`

---

### Task 4: F332 + F613 — genesis auto G4-continue 与 revision_routing main（spec T2 项 4/7）

**Files:**
- Create: `tests/unit/pipeline/test_c15_genesis_auto_continue.py`
- Create: `tests/unit/skill_utils/test_revision_routing_main.py`

**Interfaces:**
- Consumes: `shenbi.pipeline.genesis` 内部步骤函数（`genesis.py:349` 起的 G4 段：`run_gate_g4`、`_gate_passed`、`_handle_failure`、`state.config.per_chapter_review_enabled`、`state.genesis.retry_counts/retry_feedback`）；`shenbi.skill_utils.revision_routing.__main__.main() -> None`（`--diagnosis` JSON → stdout `{"mode": ...}`）
- Produces: 无

- [ ] **Step 1: genesis auto-continue**——参照 `tests/unit/pipeline/test_genesis.py:302-316`（`test_optional_step_g4_failure_also_skips`）既有构造方式搭 state/step/project_dir；差异点：`per_chapter_review_enabled=False`。断言序列：首次 `run_gate_g4` FAIL（monkeypatch 返回 `{"status": "FAIL", "must_fix": ["x"]}`）→ 步骤函数返回 False（retry once）；再次调用同步骤 FAIL → 不调 `_handle_failure`（monkeypatch 计数为 0）且继续走成功路径（retry_counts 已 pop、step 推进）。若既有测试的 step 驱动入口是 `_run_single_step(state, step, project_dir)` 之类的私有函数，按真实函数名调用（grep `genesis.py` 定位包裹函数）
- [ ] **Step 2: revision_routing main**——

```python
"""Coverage for revision_routing __main__ main() (F613, spec #53)."""

import json
import subprocess
import sys


def run_module(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "shenbi.skill_utils.revision_routing", *args], capture_output=True, text=True)


def test_main_routes_valid_diagnosis() -> None:
    p = run_module(["--diagnosis", json.dumps({"severity": "low"})])  # payload 按 route_revision 真实入参形态（红灯期核对 route.py）
    assert p.returncode == 0
    assert json.loads(p.stdout)["mode"]  # routed mode emitted


def test_main_invalid_json_exits_nonzero() -> None:
    p = run_module(["--diagnosis", "not-json"])
    assert p.returncode != 0


def test_main_requires_diagnosis_flag() -> None:
    assert run_module([]).returncode != 0
```

（诊断 payload 字段以 `src/shenbi/skill_utils/revision_routing/route.py` 的 `route_revision(diagnosis)` 真实取键为准，红灯期校准）
- [ ] **Step 3: 运行** 两个文件 `-v` — 红到绿
- [ ] **Step 4: 红灯验证**（genesis：把 auto 分支 `count <= 1` 临时改 0；routing：改 stdout 缺 mode 键）→ 红 → 还原，记录
- [ ] **Step 5: Commit** `git add tests/unit/pipeline/test_c15_genesis_auto_continue.py tests/unit/skill_utils/test_revision_routing_main.py && git commit -m "test: genesis auto-mode G4-continue + revision_routing main() coverage (F332/F613, spec #53)"`

---

### Task 5: F738 + F737 + F736 — 并发波异常 / context_cache 域分支 / 中文周标签（spec T2 项 5/6）

**Files:**
- Create: `tests/unit/pipeline/test_c15_wave_and_context_branches.py`
- Create: `tests/gates/g4/test_c15_chinese_week_label.py`

**Interfaces:**
- Consumes: `dispatch_reviews_parallel(tasks, on_task_complete=None) -> list[DispatchResult]`（src/shenbi/pipeline/parallel_dispatch.py:172）；`ReviewTask`/`DispatchResult`（同模块数据类）；`build_shared_audit_context`（src/shenbi/pipeline/audit_context_cache.py，函数名以模块真实导出为准——grep `def build`）；`check_chapter_title`（src/shenbi/gates/g4/chapter_drafting.py）
- Produces: 无

- [ ] **Step 1: 并发波异常**——monkeypatch `_dispatch_with_retry`：任务 0 raise RuntimeError、任务 1 正常成功；断言 `dispatch_reviews_parallel` 返回长度 2、`results[0].success is False and results[0].stderr` 含异常信息、`results[1].success is True`；再加 callback 两分支：成功回调被调、回调自身 raise 不中断波（其余任务仍完成）。`ReviewTask` 构造按数据类真实字段（grep class ReviewTask）
- [ ] **Step 2: audit_context_cache characters/volume**——tmp project_dir 写 `truth/character_matrix.md`（>3000 字符断言 `[TRUNCATED 3000/` 标记 + raw_files 保留原文）与 `outline/volume_map.md`（构造含 `第N章` 节点行，断言 `_extract_volume_chapter` 抽出对应章节文本；不在 raw_files）；其余文件不存在时各域为 None/空
- [ ] **Step 3: 中文周标签**——

```python
"""Chinese week-label regex branch coverage (F736, spec #53)."""

from shenbi.gates.g4.chapter_drafting import check_chapter_title


def test_warns_pure_chinese_week_label() -> None:
    issues = check_chapter_title("第四周周三", {})  # 周[一二三四五六日] 分支，无英文词
    assert any("day_label_instead_of_thematic_name" in i for i in issues)


def test_warns_each_chinese_weekday() -> None:
    for wd in "一二三四五六日":
        assert any("day_label" in i for i in check_chapter_title(f"第2周周{wd}", {}))
```

（若 `第四周周三` 恰又被其他规则先命中，断言保留 day_label 项即可——先跑红确认正则真分支）
- [ ] **Step 4: 运行** 两文件 `-v` — 红到绿
- [ ] **Step 5: 红灯验证**（并行波：注释 future.result 的 except 包装 → 测试 error；周标签：正则删中文类 → 红）→ 还原，记录
- [ ] **Step 6: Commit** `git add tests/unit/pipeline/test_c15_wave_and_context_branches.py tests/gates/g4/test_c15_chinese_week_label.py && git commit -m "test: parallel wave exception branches, context_cache chars/volume, Chinese week label (F738/F737/F736, spec #53)"`

---

### Task 6: T3 — per-module 覆盖率底线表（spec T3 项 8/9；在 Task 1-5 合入本分支后执行）

**Files:**
- Create: `tools/check_module_coverage.py`
- Create: `tools/module-coverage-floors.json`
- Modify: `justfile`（check 链追加 recipe 调用；或 `.github/workflows/ci.yml` 质量步骤——优先 justfile，保持本地/CI 同构）

**Interfaces:**
- Consumes: `uv run pytest --cov=src/shenbi --cov-report=json:coverage.json` 产出的 per-file `summary.percent_covered`
- Produces: exit 0（全部达标）/ exit 1（跌破，stderr 列出模块与实际值 vs floor）

- [ ] **Step 1: 先跑基线** `uv run pytest -n auto -m "not last" --cov=src/shenbi --cov-report=json:/tmp/cov.json`，从 JSON 提取本簇 10 面当前值，按「当前值向下取整到 5 的倍数、且与当前值差距 ≥5pp」生成 `module-coverage-floors.json`：

```json
{
  "_comment": "C15 per-module floors (spec #53 T3). Values = baseline rounded down with >=5pp headroom. Global 85 unchanged.",
  "src/shenbi/sync_contracts.py": <floor>,
  "src/shenbi/dispatcher/cli.py": <floor>,
  "src/shenbi/dispatcher/executor.py": <floor>,
  "src/shenbi/pipeline/genesis.py": <floor>,
  "src/shenbi/gates/g4/memory_distill.py": <floor>,
  "src/shenbi/gates/g4/book_spine_init.py": <floor>,
  "src/shenbi/skill_utils/revision_routing/__main__.py": <floor>,
  "src/shenbi/pipeline/parallel_dispatch.py": <floor>,
  "src/shenbi/pipeline/audit_context_cache.py": <floor>,
  "src/shenbi/gates/g4/chapter_drafting.py": <floor>
}
```

- [ ] **Step 2: 校验脚本**（pathlib + json，无第三方依赖，stderr 报告，无 print 到 stdout 的机器通道外用途——tools/ 不受 src 框架纯度约束但保持同风格）：

```python
#!/usr/bin/env python3
"""Enforce per-module coverage floors (spec #53 C15 T3).

Reads a coverage.py JSON report and compares each floored module against
tools/module-coverage-floors.json. Exit 1 with per-module detail on breach.
Data source is the pytest --cov JSON — no third hand-maintained registry (C22 lesson).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    report = Path(sys.argv[1] if len(sys.argv) > 1 else REPO / "coverage.json")
    floors = json.loads((REPO / "tools" / "module-coverage-floors.json").read_text("utf-8"))
    data = json.loads(report.read_text("utf-8"))
    breaches: list[str] = []
    for path, floor in floors.items():
        if path.startswith("_"):
            continue
        entry = data["files"].get(path)
        pct = entry["summary"]["percent_covered"] if entry else 0.0
        if pct < floor:
            breaches.append(f"{path}: {pct:.2f}% < floor {floor}")
    if breaches:
        print("module coverage floor breaches:", file=sys.stderr)
        for b in breaches:
            print(f"  {b}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: 接线 justfile**——recipe 自足生成 JSON（`just check` 的 pytest 段不带 `--cov-report=json`，pyproject addops 也不产 JSON——本 recipe 必须自带一次完整带 cov 的 pytest run）：

```make
# C15 per-module coverage floors (spec #53 T3). Self-sufficient: generates
# coverage.json (json report) then enforces tools/module-coverage-floors.json.
module-coverage:
    uv run pytest -n auto -m "not last" --cov=src/shenbi --cov-report=json:coverage.json -q
    uv run python tools/check_module_coverage.py coverage.json
```

挂进 `check` 链末尾（紧随现有第二段 pytest coverage 步骤之后独立成行）。CI `ci.yml` 质量步骤若不经 justfile，则在其 pytest 步骤后追加同一行 `uv run python tools/check_module_coverage.py coverage.json`（该 workflow 的 pytest 已带 --cov；若产物路径不同则改为 `--cov-report=json:coverage.json` 追加参数）——按 ci.yml 实际形态接线，未改 ci.yml 时不列入 commit pathspec
- [ ] **Step 4: 绿灯验证** `just module-coverage` → exit 0
- [ ] **Step 5: 红灯验证**（任一 floor 临时 +1 超过当前值 → exit 1 → 还原）并记录；此即 spec 验收条目 2 的可复验证据
- [ ] **Step 6: Commit** `git add tools/check_module_coverage.py tools/module-coverage-floors.json justfile .github/workflows/ci.yml（按 Step 3 实际是否改动 ci.yml 决定是否列入）&& git commit -m "feat: per-module coverage floor table + enforcement script (F717/T3, spec #53)"`

---

## 验收覆盖表（spec → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1 sync_contracts ≥85% | T1+T6 | pytest --cov term 输出 |
| 1 dispatcher/cli.py ≥80% | T3+T6 | 同上 |
| 1 memory_distill ≥80% / book_spine 三分支 >0 | T2+T6 | 同上 + 三态用例存在 |
| 1 genesis G4-continue 覆盖 >0 | T4+T6 | 同上 |
| 1 revision_routing main ≥80% | T4+T6 | 同上 |
| 1 parallel_dispatch 并发波异常 >0 | T5+T6 | 同上 |
| 1 audit_context_cache chars/volume >0 | T5+T6 | 同上 |
| 1 中文周标签分支 >0 | T5+T6 | 同上 |
| 2 floor 红灯验证 | T6 Step 5 | 临时 +1 → FAIL 输出 |
| 3 红灯验证法 | T1-T5 各 Step | progress.md 记录 |
| 4 just check 全绿 + tmp_path | 全部 | 阶段 7 |

复杂度：Task 1-5 = characterization（行为保持，补测）；Task 6 = infra（新门禁脚本）。
test_kind：全部 characterization/regression_guard；无新生产逻辑。
测试层级：全部 T1（per-module 单元级）。评分场景：无（不涉及 generative 评分，G3.4 不适用）。
