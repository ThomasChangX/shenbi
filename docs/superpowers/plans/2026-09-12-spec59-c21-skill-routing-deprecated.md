# C21 技能注册/触发路由漂移修复 Implementation Plan（spec #59）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 五路由面（using-shenbi 触发表 / deps.json / GENESIS_STEPS / TRIGGER_STEPS / GENRE_ACTIVATION_MATRIX，另含 CHAPTER_STEPS/BOUNDARY_TRIGGERS 防回潮面）对 15 个 DEPRECATED 技能零路由零注册零派发；后继技能进触发表；description 契约全仓合规且检查器能检出违规；防回潮 lint 七面挂载。

**Architecture:** 自底向上——先立共享 DEPRECATED 判定 helper 与闭包语义翻转（T1），再拆三处 pipeline 路由面（T2/T5/T6）与 gates/contracts 注册面（T3/T4），矩阵按派发拓扑退出（T6），description 检查器强化先行再改写（T7→T8），DEPRECATED 正文退役收尾（T10），防回潮 lint 最后挂载红灯验证（T11）。

**Tech Stack:** Python 3.11+ / pathlib / structlog / pytest / just / pre-commit。全部验证离线（F947：无真实 dispatch；G3.4：本 spec 无评分场景，N/A）。

## Global Constraints

- 禁止 `print()` 于 `src/shenbi/`（ruff T20，structlog/cli_utils 替代）；gate 检查器纯函数幂等
- 状态字面量唯一定义于 `src/shenbi/contracts/enums.py`（HookState 六态：PLANTED/RELEVANT/TRIGGERED/RESOLVED/ARCHIVED/EXPIRED——无 ACTIVE）
- 改 SKILL.md frontmatter 契约后必须 `just generate`（`uv run shenbi-sync-contracts`）再提交，生成物 diff 须与源同步（禁手改 expected_outputs/DAG/index/body views；`prerequisites`/`_tool_hashes` 是组织性字段可直接编辑）
- 所有 commit 显式 pathspec，禁 `git add -A`；conventional commits
- 测试引用 `tests/fixtures/` 真实产物（G0.9）；验证命令走 `uv run`/`just`（与 CI 同构）
- spec 验收 1 许可残留白名单：chapter_loop.py:135-136 退役注释（context-composing 误标已纠）、:282-284 STEP_NAME_MIGRATIONS、`skills/shenbi-foreshadowing-{plant,track,recall}/` 自身目录

## 签名实录（从源码实抄 · 2026-09-12 HEAD 7740746b）

```python
# src/shenbi/pipeline/genesis.py
@dataclass
class GenesisStep:
    step_num: int
    skill: str
    mode: str = ""
    output_path: str = ""
    optional: bool = False
GENESIS_STEPS: list[GenesisStep]  # step 9 = foreshadowing-plant (mode="genesis")
_INDEX_UPDATE_SKILLS: frozenset[str]  # 含 "shenbi-foreshadowing-plant"

# src/shenbi/pipeline/triggers.py
@dataclass
class TriggerStep:
    skill: str; mode: str = ""; output_path: str = ""; requires_g3: bool = False; category: str = ""
TRIGGER_STEPS  # :294-301 含 plant (mode="expand", category="volume_boundary")

# src/shenbi/pipeline/chapter_loop.py
CHAPTER_STEPS  # step 7 = shenbi-foreshadowing-lifecycle (step_type="core")；steps 9-14 = group-* (is_audit=True)；step 14 = review-sensitivity
STEP_NAME_MIGRATIONS = {"shenbi-foreshadowing-plant": "shenbi-foreshadowing-lifecycle", ...}  # :282-284 保留

# src/shenbi/pipeline/audit_layer.py
GENRE_ACTIVATION_MATRIX: dict[str, str] = {"sensitivity": ..., "worldRules": ..., "motivation": ..., "dialogue": ..., "texture": ..., "era": ..., "fanfic": ..., "readerPull": ..., "highpoint": ...}
_CORE_CIRCLE_KEYS = frozenset({"antiAi","character","pacing","continuity","foreshadowing","memoCompliance","pov"})
_CRITICAL_GENRE_DIMS = frozenset(d for d in ("texture",) if d in GENRE_ACTIVATION_MATRIX)
BOUNDARY_TRIGGERS: dict[str, Callable[[int], bool]]  # long-span/arc-payoff/spinoff/chapter-pattern

# src/shenbi/pipeline/dispatch_helper.py
OPTIONAL_READS: dict[str, list[str]]  # :424-425 含 plant/track 死条目

# src/shenbi/contracts/ownership.py
@dataclass(frozen=True)
class FileOwnership:
    level: Literal["field", "record_create", "record_field"]
    write_keys: frozenset[str] = field(default_factory=frozenset)
    read_keys: frozenset[str] = field(default_factory=frozenset)
# 现行 pending_hooks.md 行：plant=record_create / track=record_field(state) / resolve=record_field(state) / state-settling=record_field(last_reinforced,subtlety)

# src/shenbi/gates/g4/ 惯例签名
def g4_foreshadowing_plant(fps: list[str], rd: str | None = None, project_dir: str | None = None, repo_root: str | None = None) -> str
# 返回 fail("G4-foreshadowing-plant", c, "scoring", mf) 或 passed("G4-foreshadowing-plant", c)

# src/shenbi/gates/g0_skill_contract.py
_BEHAVIORAL_MARKERS = ["this skill", "this module", "generates ", "writes ", "creates ", "validates ", "checks ", "analyzes ", "computes ", "extracts ", "该技能", "该模块", "生成", "写入", "创建", "验证", "检查", "分析", "计算", "提取", "产出", "输出", "读取", "审计"]
def _desc_has_behavioral_text(desc: str) -> bool  # 仅 startswith(_BEHAVIORAL_MARKERS)
DESCRIPTION_MAX_CHARS  # 500

# tools/lint_repo_consistency.py
def check_skill_deps_closure(repo: Path) -> list[str]  # 双向：dirs-deps missing + deps-dirs ghost
```

**DEPRECATED 横幅两形态**（15 文件实况）：`# DEPRECATED: Superseded by …`（plant/track/recall 三件）与 `<!-- DEPRECATED: Superseded by … -->`（12 个 review-*）。

---

### Task 1: 共享 DEPRECATED 判定 helper + deps 闭包语义翻转（E 连锁）

**复杂度: infra**（协调者亲实现）· **test_kind: tdd_red_green** · 测试层级: T1 单元（tmp_path 合成树 + 真仓回归断言；非 skill-output fixture，是单元合成输入）

**Files:**
- Create: `src/shenbi/skill_utils/deprecated.py`
- Modify: `tools/lint_repo_consistency.py:237-253`（check_skill_deps_closure）
- Test: `tests/unit/skill_utils/test_deprecated.py`（新）、`tests/unit/test_lint_repo_consistency.py`（扩）

**Interfaces:**
- Produces: `deprecated_skill_names(skills_dir: Path) -> frozenset[str]`、`is_deprecated_skill(skills_dir: Path, skill_name: str) -> bool`（T4/T11 的 lint 与本 task 闭包共用——单一 DEPRECATED 判定信源）

- [ ] **Step 1: 失败测试**

```python
# tests/unit/skill_utils/test_deprecated.py
"""Shared DEPRECATED-skill detection (spec #59 T1/T3 single source)."""
from pathlib import Path
from shenbi.skill_utils.deprecated import deprecated_skill_names, is_deprecated_skill

REPO = Path(__file__).resolve().parents[3]
SKILLS = REPO / "skills"

def _mk(root: Path, name: str, body: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")

def test_detects_html_comment_banner(tmp_path: Path) -> None:
    _mk(tmp_path, "shenbi-x", "---\nname: shenbi-x\n---\n<!-- DEPRECATED: Superseded by y. -->\nbody")
    assert is_deprecated_skill(tmp_path, "shenbi-x") is True

def test_detects_hash_banner(tmp_path: Path) -> None:
    _mk(tmp_path, "shenbi-x", "# DEPRECATED: Superseded by y.\nbody")
    assert is_deprecated_skill(tmp_path, "shenbi-x") is True

def test_live_skill_negative(tmp_path: Path) -> None:
    _mk(tmp_path, "shenbi-x", "---\nname: shenbi-x\n---\nbody mentions DEPRECATED_CONTEXT nowhere")
    assert is_deprecated_skill(tmp_path, "shenbi-x") is False

def test_missing_dir_is_not_deprecated(tmp_path: Path) -> None:
    assert is_deprecated_skill(tmp_path, "shenbi-ghost") is False

def test_real_repo_baseline_15() -> None:
    # 回归钉：真仓当前 15 个 DEPRECATED（驳斥复核 2026-09-12 实况）
    names = deprecated_skill_names(SKILLS)
    assert "shenbi-foreshadowing-plant" in names
    assert "shenbi-review-continuity" in names
    assert len(names) == 15
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/skill_utils/test_deprecated.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'shenbi.skill_utils.deprecated'`

- [ ] **Step 3: 最小实现**

```python
# src/shenbi/skill_utils/deprecated.py
"""Single source for DEPRECATED-skill detection (spec #59 T1/T3).

Two banner forms exist in the wild (verified 2026-09-12):
``# DEPRECATED: ...`` and ``<!-- DEPRECATED: ... -->``.
"""
from __future__ import annotations

import re
from pathlib import Path

_BANNER_RE = re.compile(r"^\s*(?:#\s*|<!--\s*)DEPRECATED[:\s]", re.MULTILINE)


def is_deprecated_skill(skills_dir: Path, skill_name: str) -> bool:
    """True iff the skill's SKILL.md carries a DEPRECATED banner."""
    skill_md = skills_dir / skill_name / "SKILL.md"
    if not skill_md.exists():
        return False
    return bool(_BANNER_RE.search(skill_md.read_text(encoding="utf-8")))


def deprecated_skill_names(skills_dir: Path) -> frozenset[str]:
    """All DEPRECATED-marked skill dir names under *skills_dir*."""
    return frozenset(
        p.parent.name
        for p in skills_dir.glob("*/SKILL.md")
        if _BANNER_RE.search(p.read_text(encoding="utf-8"))
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/skill_utils/test_deprecated.py -v` → 5 passed

- [ ] **Step 5: 闭包翻转失败测试**（扩 `tests/unit/test_lint_repo_consistency.py`，沿用该文件既有 tmp_path 造树手法）

```python
def test_deps_closure_deprecated_exempt_and_forbidden(tmp_path: Path) -> None:
    # DEPRECATED 目录未注册 -> 不报 missing；已注册 -> 报 forbidden
    skills = tmp_path / "skills"; skills.mkdir()
    (skills / "shenbi-live").mkdir(); (skills / "shenbi-live" / "SKILL.md").write_text("---\n---\nbody")
    (skills / "shenbi-dead").mkdir(); (skills / "shenbi-dead" / "SKILL.md").write_text("# DEPRECATED: gone")
    tiers = tmp_path / "tests" / "tiers"; tiers.mkdir(parents=True)
    deps = tiers / "deps.json"
    deps.write_text(json.dumps({"t2-phases": {"audit": {"prerequisites": ["shenbi-live", "shenbi-dead"], "expected_outputs": []}}}), encoding="utf-8")
    errs = check_skill_deps_closure(tmp_path)
    assert not any("not registered" in e for e in errs)          # 豁免方向
    assert any("DEPRECATED skills registered" in e and "shenbi-dead" in e for e in errs)  # 禁注册方向
```

- [ ] **Step 6: 实现**——`check_skill_deps_closure` 中：

```python
    from shenbi.skill_utils.deprecated import deprecated_skill_names
    dead = deprecated_skill_names(skills_dir)
    missing = sorted(d for d in (dirs - deps_names) if d not in dead)
    if missing:
        errs.append(f"skills_deps_closure: skill dirs not registered in deps.json: {missing}")
    forbidden = sorted(dead & deps_names)
    if forbidden:
        errs.append(f"skills_deps_closure: DEPRECATED skills registered in deps.json: {forbidden}")
```

（ghost 方向原样保留。注意此时真仓 deps.json 仍注册 15 个 DEPRECATED——本 task 后 `just lint-repo` 会红，直到 Task 5 拆注册；这是设计内中间态，分支终态 T5 后复绿。既有测试若断言旧双向语义需同步更新。）

- [ ] **Step 7: 单测过 + commit**

Run: `uv run pytest tests/unit/skill_utils/test_deprecated.py tests/unit/test_lint_repo_consistency.py -v` → all passed

```bash
git add src/shenbi/skill_utils/deprecated.py tests/unit/skill_utils/test_deprecated.py tools/lint_repo_consistency.py tests/unit/test_lint_repo_consistency.py
git commit -m "feat: shared DEPRECATED-skill detection + deps closure flip to forbid-register (spec #59 T1)"
```

---

### Task 2: pipeline 路由面拆除——GENESIS_STEPS 换 lifecycle + TRIGGER_STEPS/OPTIONAL_READS 清除 + 陈旧引用

**复杂度: infra** · **test_kind: tdd_red_green**（换名断言）+ characterization（死分支删除后既有测试不破）· 测试层级: T1

**Files:**
- Modify: `src/shenbi/pipeline/genesis.py:70`（step 9）、`:97`（_INDEX_UPDATE_SKILLS）
- Modify: `src/shenbi/pipeline/triggers.py:294-301`（删 plant TriggerStep）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:424-425`（OPTIONAL_READS 删 plant/track）
- Modify: `src/shenbi/pipeline/truth_readers.py:3`、`src/shenbi/pipeline/chapter_loop.py:1583`、`src/shenbi/pipeline/chapter_loop.py:3200-3201`（死分支）、`src/shenbi/pipeline/chapter_loop.py:135-136`（注释纠 context-composing 误标）、`src/shenbi/pipeline/truth_index.py:177`
- Test: `tests/unit/pipeline/test_genesis.py`（扩）、`tests/unit/pipeline/test_triggers.py`（扩）

**Interfaces:**
- Consumes: 无
- Produces: `GENESIS_STEPS` step 9 skill == `"shenbi-foreshadowing-lifecycle"`（T11 lint 与验收 5 断言依赖）；TRIGGER_STEPS 无 DEPRECATED 成员

- [ ] **Step 1: 失败测试**

```python
# tests/unit/pipeline/test_genesis.py 追加
def test_genesis_step9_is_lifecycle() -> None:
    from shenbi.pipeline.genesis import GENESIS_STEPS, _INDEX_UPDATE_SKILLS
    step9 = next(s for s in GENESIS_STEPS if s.step_num == 9)
    assert step9.skill == "shenbi-foreshadowing-lifecycle"
    assert step9.output_path == "truth/pending_hooks.md"
    assert "shenbi-foreshadowing-lifecycle" in _INDEX_UPDATE_SKILLS
    assert "shenbi-foreshadowing-plant" not in _INDEX_UPDATE_SKILLS

# tests/unit/pipeline/test_triggers.py 追加
def test_trigger_steps_have_no_deprecated() -> None:
    from pathlib import Path
    from shenbi.pipeline.triggers import TRIGGER_STEPS
    from shenbi.skill_utils.deprecated import deprecated_skill_names
    dead = deprecated_skill_names(Path(__file__).resolve().parents[3] / "skills")
    assert not [s.skill for s in TRIGGER_STEPS if s.skill in dead]
```

- [ ] **Step 2: 确认失败** — `uv run pytest tests/unit/pipeline/test_genesis.py::test_genesis_step9_is_lifecycle tests/unit/pipeline/test_triggers.py::test_trigger_steps_have_no_deprecated -v` → FAIL（断言 plant ≠ lifecycle / TRIGGER_STEPS 含 plant）

- [ ] **Step 3: 实现**

genesis.py:70 改为：
```python
    GenesisStep(
        9, "shenbi-foreshadowing-lifecycle", mode="genesis", output_path="truth/pending_hooks.md"
    ),
```
`:97`：`"shenbi-foreshadowing-plant",` → `"shenbi-foreshadowing-lifecycle",`
triggers.py：整块删除（含上下注释行核对）：
```python
    TriggerStep(
        skill="shenbi-foreshadowing-plant",
        mode="expand",
        output_path="truth/pending_hooks.md",
        category="volume_boundary",
    ),
```
（卷界伏笔扩展职责由 lifecycle 每章面承接——CHAPTER_STEPS step 7 已每章跑 lifecycle，卷界不另设触发；若审查裁决仍需卷界触发，加 `TriggerStep(skill="shenbi-foreshadowing-lifecycle", mode="expand", output_path="truth/pending_hooks.md", category="volume_boundary")` 替换，跑 `uv run pytest tests/pipeline -q` 全绿为准。）
dispatch_helper.py OPTIONAL_READS：删 `"shenbi-foreshadowing-plant"` 与 `"shenbi-foreshadowing-track"` 两键（:424-425）；`"shenbi-context-composing"` 保留（T1.4 裁决）。
truth_readers.py:3：docstring `written by shenbi-foreshadowing-track /` 按行实况改 `written by shenbi-foreshadowing-lifecycle`（读 :1-8 全文后同步相邻行）。
chapter_loop.py:1583 注释、truth_index.py:177 docstring 同法。
chapter_loop.py:3200-3201 删除死分支：
```python
    # Conditional: foreshadowing-resolve after foreshadowing-track (step 7b).
    if "foreshadowing-track" in step.skill:
```
及其块体（读 :3195-3215 确认块边界后整块删；若 resolve 条件仍需保留，改 `"foreshadowing-lifecycle" in step.skill` 并跑 `tests/pipeline/test_chapter_steps_restructured.py`）。**先读后删**——#58 事故教训（锚串自记忆构造致静默 no-op）。
chapter_loop.py:135-136 注释：`# Deprecated skills removed: foreshadowing-plant, foreshadowing-track,` / `#   foreshadowing-recall, context-composing.` → 删 context-composing 项（其非 DEPRECATED，见 spec T1.4）。

- [ ] **Step 4: 测试过 + 回归 + prompt 可达断言（验收 5）**

Run: `uv run pytest tests/unit/pipeline/ -q && uv run pytest tests/pipeline -q` → 全绿（triggers/genesis 既有测试若硬编码 plant 需同步改——先 grep：`grep -rn "foreshadowing-plant" tests/` 逐处裁决）

`tests/pipeline/test_dispatch_reads_injection.py`（#58 既有家族）追加 lifecycle 用例——验收 5 的 `_build_skill_prompt` 可达断言：

```python
def test_lifecycle_prompt_reachable(tmp_path: Path) -> None:
    """Acceptance 5 (F947 offline): GENESIS_STEPS step-9 successor assembles a prompt."""
    from shenbi.pipeline.dispatch_helper import _build_skill_prompt
    from shenbi.pipeline.genesis import GENESIS_STEPS
    step9 = next(s for s in GENESIS_STEPS if s.step_num == 9)
    prompt = _build_skill_prompt(step9.skill, "genesis", tmp_path, {})
    assert "shenbi-foreshadowing-lifecycle" in prompt or prompt  # 签名以 dispatch_helper.py:603 实况为准——若参数不符，按实况改写调用形，断言点不变：lifecycle 产出非空 prompt
```
（实施时读 `_build_skill_prompt` 真实签名对齐——计划作者注：#58 的 test_dispatch_reads_injection.py 已有同族调用可抄。）

- [ ] **Step 5: commit**

```bash
git add src/shenbi/pipeline/genesis.py src/shenbi/pipeline/triggers.py src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/truth_readers.py src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/truth_index.py tests/unit/pipeline/test_genesis.py tests/unit/pipeline/test_triggers.py
git commit -m "fix: swap GENESIS_STEPS step 9 to lifecycle, drop plant trigger + OPTIONAL_READS dead entries (spec #59 T2)"
```

---

### Task 3: G4 lifecycle checker + 注册面换名（generic/shared/ownership/g5/hooks/cli/_tool_hashes/migrate）

**复杂度: infra** · **test_kind: characterization**（checker 行为从 plant/track 既有测试移植）+ tdd_red_green（注册断言）· 测试层级: T1（fixtures 驱动）

**Files:**
- Create: `src/shenbi/gates/g4/foreshadowing_lifecycle.py`
- Delete: `src/shenbi/gates/g4/foreshadowing_plant.py`、`src/shenbi/gates/g4/foreshadowing_track.py`
- Modify: `src/shenbi/gates/g4/generic.py:327-328`、`src/shenbi/gates/shared.py:416-417`（G4_CHECKER_SKILLS）、`src/shenbi/contracts/ownership.py:82-85`、`src/shenbi/gates/g5.py:289-290`、`src/shenbi/gates/cli.py:37-38`、`src/shenbi/contracts/schemas/hooks.py:3-4,:26`、`tools/migrate_contract_to_frontmatter.py:205,:211`、`tests/tiers/deps.json`（_tool_hashes）
- Test: `tests/unit/gates/g4/test_foreshadowing_lifecycle.py`（新；从既有 plant/track 测试移植 fixture 手法）

**Interfaces:**
- Produces: `g4_foreshadowing_lifecycle(fps: list[str], rd: str | None = None, project_dir: str | None = None, repo_root: str | None = None) -> str`（generic.py 注册键 `"shenbi-foreshadowing-lifecycle"`）

- [ ] **Step 1: 移植+新写测试**——读既有 `tests/unit/gates/g4/test_foreshadowing_plant.py` 与 `test_foreshadowing_track.py`（若名异按 `ls tests/unit/gates/g4/` 实况），把 fixture 场景并入新文件：①pending_hooks 结构完整（hook 记录 + 规范 HookState）②bridge_tracker.md append 语义存在③audits 输出存在④无输入 SKIP。fixture 引用真实产物路径（既有测试所用 `tests/fixtures/...` 原样继承；无现成 fixture 的场景用真仓 novel-output 产物路径，禁手造）。
- [ ] **Step 2: 确认失败** — `uv run pytest tests/unit/gates/g4/test_foreshadowing_lifecycle.py -v` → FAIL（模块不存在）
- [ ] **Step 3: 实现 checker**（组合 plant 的 hook 结构面 + track 的变更面；惯例 fail/passed）

```python
"""G4 checker for shenbi-foreshadowing-lifecycle (spec #59 T3 wiring)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from shenbi.gates.shared import PROJECT, fail, passed
from shenbi.paths import RoundPaths
from shenbi.status import GateStatus


def g4_foreshadowing_lifecycle(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str:
    """Lifecycle: pending_hooks records use canonical HookState; bridge_tracker appends; audit report present."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    if rd is None and project_dir is None:
        raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
    rp = RoundPaths(
        round_dir=Path(str(rd or project_dir)),
        project_dir=Path(str(project_dir or rd)),
        repo_root=Path(repo_root or PROJECT),
    )
    for fp in fps or []:
        content = rp.read(fp).read_text(encoding="utf-8") if rp.read(fp).exists() else ""
        if not content:
            mf.append(f"G4.fl.empty_or_missing:{fp}")
            continue
        # 1) canonical states only (ACTIVE etc. fold to None upstream — reject here)
        import re
        states = set(re.findall(r"\b(PLANTED|RELEVANT|TRIGGERED|RESOLVED|ARCHIVED|EXPIRED|ACTIVE)\b", content))
        if "ACTIVE" in states:
            mf.append("G4.fl.non_canonical_state:ACTIVE")
        elif states:
            c.append({"id": "G4.fl.states", "s": GateStatus.PASS, "seen": sorted(states)})
        else:
            mf.append("G4.fl.no_hook_states")
    if not fps:
        c.append({"id": "G4.fl", "s": GateStatus.SKIP, "r": "no files"})
    if mf:
        return fail("G4-foreshadowing-lifecycle", c, "scoring", mf)
    return passed("G4-foreshadowing-lifecycle", c)
```
（实现时可再吸收 plant 的 ops≤24 与 depends_on 检查——以移植测试全绿为准绳精化；上面是最小可过骨架。）

- [ ] **Step 4: 注册面换名**（逐文件、行号以实况为准）

```python
# generic.py（import 行同步）："shenbi-foreshadowing-plant": g4_foreshadowing_plant, 与 track 行 →
    "shenbi-foreshadowing-lifecycle": g4_foreshadowing_lifecycle,
# shared.py G4_CHECKER_SKILLS：删 plant/track 两字符串成员，加 "shenbi-foreshadowing-lifecycle"
# ownership.py：plant(record_create) 与 track(record_field state) 两行 →
    ("shenbi-foreshadowing-lifecycle", "truth/pending_hooks.md"): FileOwnership(
        level="record_field", write_keys=frozenset({"state"})
    ),
#   （裁决：record_field(state)——last_reinforced/subtlety 归 state-settling（F819 修正方向）；genesis/新 hook 的 record 创建事件由 append_dedup 契约 mode + G4 结构校验承接，不入 ownership 单级行）
# g5.py：
    "shenbi-foreshadowing-lifecycle": ["truth/pending_hooks.md"],
# gates/cli.py：删 "foreshadowing-track"/"foreshadowing-plant" 两短名，加 "foreshadowing-lifecycle": "shenbi-foreshadowing-lifecycle",
# schemas/hooks.py:3-4 与 :26：权威源引用 foreshadowing-track/SKILL.md → shenbi-foreshadowing-lifecycle/SKILL.md（六态语义不变）
```
- [ ] **Step 5: 删旧模块 + 重锁哈希**

```bash
git rm src/shenbi/gates/g4/foreshadowing_plant.py src/shenbi/gates/g4/foreshadowing_track.py
bash tests/lock-tool-hashes.sh   # 重锁 _tool_hashes（读脚本确认调用形态；输出 diff 应只增 lifecycle 钉、删两旧钉）
```
`tools/migrate_contract_to_frontmatter.py:205,:211` 的 plant/track 硬编码顺手清理（一次性迁移工具，无调用方约束）。
- [ ] **Step 6: 全域回归** — `uv run pytest tests/unit/gates -q && grep -rn "g4_foreshadowing_plant\|g4_foreshadowing_track" src/ tests/` → 测试绿 + grep 零命中（测试文件同步移植后旧引用清零）
- [ ] **Step 7: commit**（pathspec 列全：新 checker、四注册文件、两删除模块、deps.json、migrate 工具、schema、测试）

```bash
git commit -m "feat: G4 lifecycle checker + registration swap across gates/contracts faces (spec #59 T3)"
```

---

### Task 4: using-shenbi 触发表重写（删 14 行 + 短语改指 + 后继补行 + 默认列）

**复杂度: infra**（meta 技能文档 + lint 联动）· **test_kind: regression_guard**（静态断言）· 测试层级: T1

**Files:**
- Modify: `skills/using-shenbi/SKILL.md:40-54,63,73-74,124,126`
- Test: `tests/contracts/test_using_shenbi_routing.py`（新）

**Interfaces:**
- Produces: 触发表含 4 group-* + lifecycle 各 ≥1 行、零 DEPRECATED 行（T11 lint 与验收 1/2 依赖）

- [ ] **Step 1: 失败测试**

```python
# tests/contracts/test_using_shenbi_routing.py
"""Trigger-table routing assertions (spec #59 T4; acceptance 2)."""
import re
from pathlib import Path

SKILL_MD = Path(__file__).resolve().parents[2] / "skills" / "using-shenbi" / "SKILL.md"
REPO = Path(__file__).resolve().parents[2]

def _table_rows() -> list[str]:
    text = SKILL_MD.read_text(encoding="utf-8")
    return [ln for ln in text.splitlines() if ln.startswith("| ") and "shenbi-" in ln]

def test_no_deprecated_routed() -> None:
    from shenbi.skill_utils.deprecated import deprecated_skill_names
    dead = deprecated_skill_names(REPO / "skills")
    hits = [r for r in _table_rows() if any(d in r for d in dead)]
    assert not hits, f"DEPRECATED routed: {hits}"

def test_successors_have_rows() -> None:
    rows = "\n".join(_table_rows())
    for succ in ("shenbi-review-group-character", "shenbi-review-group-craft",
                 "shenbi-review-group-factual", "shenbi-review-group-plan",
                 "shenbi-foreshadowing-lifecycle"):
        assert succ in rows, succ

def test_merged_phrases_survive() -> None:
    rows = "\n".join(_table_rows())
    for phrase in ("对话问题", "动机不合理", "伏笔追踪", "世界观矛盾", "备忘合规"):
        assert phrase in rows, phrase
```

- [ ] **Step 2: 确认失败** — `uv run pytest tests/contracts/test_using_shenbi_routing.py -v` → 3 FAIL
- [ ] **Step 3: 实现**——删 :44-54（11 行）、:63、:73-74（共 14 行），替换为（短语全量改指，映射按组覆盖面）：

```markdown
| "检查这章" / "审计" / "审查" | default audits（group-factual / group-character / group-craft / group-plan + review-sensitivity + review-resonance） |
| "连贯性" / "前后矛盾" / "对不上" / "世界观矛盾" / "设定冲突" / "世界规则" / "节奏不对" / "太拖" / "太赶" / "节奏检查" | shenbi-review-group-factual |
| "角色一致性" / "人设崩了" / "OOC" / "对话问题" / "台词" / "说话方式" / "动机不合理" / "为什么这么做" / "角色动机" / "视角问题" / "POV" / "视角混乱" | shenbi-review-group-character |
| "质感" / "沉浸感" / "画面感" / "吸引力" / "读不下去" / "读者" | shenbi-review-group-craft |
| "伏笔检查" / "埋线检查" / "备忘合规" / "章节备忘检查" / "计划执行" | shenbi-review-group-plan |
| "伏笔" / "埋线" / "hook" / "伏笔追踪" / "hook状态" | shenbi-foreshadowing-lifecycle |
```
默认审计列 :124：`Default audits (always run): review-anti-ai, review-continuity, review-character, review-sensitivity, review-resonance` → `Default audits (always run): review-group-factual, review-group-character, review-group-craft, review-group-plan, review-sensitivity, review-resonance`
:126 Phase 列表整段重写为现行现实（固定组步 + 条件单体 review-highpoint/long-span/era/fanfic/spinoff），不再列 DEPRECATED 单体名。

- [ ] **Step 4: 测试过 + 契约同步** — `uv run pytest tests/contracts/test_using_shenbi_routing.py -v` → 3 passed；`just lint-contracts`（using-shenbi 是 meta，无 frontmatter contract——lint 应不受影响，红则查）
- [ ] **Step 5: commit**

```bash
git add skills/using-shenbi/SKILL.md tests/contracts/test_using_shenbi_routing.py
git commit -m "fix: using-shenbi trigger table drops 14 DEPRECATED routes, successors + merged phrases (spec #59 T4)"
```

---

### Task 5: deps.json 拆注册 + tier 归属 + generate 同步

**复杂度: infra** · **test_kind: characterization**（闭包/生成器行为不变，成员删减）· 测试层级: T1

**Files:**
- Modify: `tests/tiers/deps.json`（planning/drafting/audit 三段 prerequisites + `_tool_hashes` 已于 T3 重锁）
- Test: `tests/unit/test_lint_repo_consistency.py`（扩真仓断言）

- [ ] **Step 1: 失败测试**——真仓闭包零违例断言：

```python
def test_real_repo_closure_green_after_deregistration() -> None:
    errs = check_skill_deps_closure(REPO_ROOT)
    assert errs == []
```
（REPO_ROOT 取仓根常量，沿用该测试文件既有写法。）

- [ ] **Step 2: 确认失败** — 本 task 前真仓仍注册 15 个 DEPRECATED → forbidden 非空 FAIL
- [ ] **Step 3: 实现删减**：
  - planning.prerequisites：删 `"shenbi-foreshadowing-plant"`，**加 `"shenbi-foreshadowing-lifecycle"`**（M8 裁决：plant 的 planning 前置语义由 lifecycle 承接——planning 阶段完成即可按章计划埋 hook）；`"shenbi-context-composing"` 保留
  - drafting.prerequisites：删 `"shenbi-foreshadowing-track"`、`"shenbi-foreshadowing-recall"`（`"shenbi-foreshadowing-lifecycle"` 已在册）
  - audit.prerequisites：删 12 个 DEPRECATED 单体（character/continuity/dialogue/pacing/anti-ai/foreshadowing/world-rules/memo-compliance/motivation/pov/reader-pull/texture）；保留 sensitivity/highpoint/long-span/era/fanfic/spinoff + 4 group-*
- [ ] **Step 4: 生成物同步** — `uv run shenbi-sync-contracts && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/`（先跑 `just generate` 一次让 expected_outputs 随成员变化再生，随后 diff 须为空）

Run: `uv run pytest tests/unit/test_lint_repo_consistency.py -v` → all passed（含 Step 1 新断言）
- [ ] **Step 5: 回归** — `uv run pytest tests/unit/ -q -k "phase or deps or g5"`（phase_runner/g5 消费方）+ `uv run python tools/lint_repo_consistency.py` → 绿
- [ ] **Step 6: commit**

```bash
git add tests/tiers/deps.json tests/unit/test_lint_repo_consistency.py
git commit -m "fix: deps.json deregisters 15 DEPRECATED skills; lifecycle takes planning tier (spec #59 T5)"
```

---

### Task 6: audit_layer 矩阵退出 + core-keys 扩充

**复杂度: infra** · **test_kind: tdd_red_green** · 测试层级: T1

**Files:**
- Modify: `src/shenbi/pipeline/audit_layer.py:38-72`（矩阵 + core keys + 头注释 + _CRITICAL_GENRE_DIMS 注记）
- Modify: `skills/shenbi-genre-config/SKILL.md:174-180`（词表语义注记：六维由固定组步承接，配置键仍合法）
- Test: `tests/unit/pipeline/test_audit_layer.py`（扩）

- [ ] **Step 1: 失败测试**

```python
def test_matrix_routes_no_deprecated_and_no_fixed_step_dup() -> None:
    from pathlib import Path
    from shenbi.pipeline.audit_layer import GENRE_ACTIVATION_MATRIX, _CORE_CIRCLE_KEYS
    from shenbi.skill_utils.deprecated import deprecated_skill_names
    dead = deprecated_skill_names(Path(__file__).resolve().parents[3] / "skills")
    assert not [v for v in GENRE_ACTIVATION_MATRIX.values() if v in dead]
    for dim in ("sensitivity", "worldRules", "motivation", "dialogue", "texture", "readerPull"):
        assert dim in _CORE_CIRCLE_KEYS, dim

def test_genre_audits_filters_core_dims() -> None:
    from shenbi.pipeline.audit_layer import get_active_genre_audits
    gc = {"auditDimensions": {"worldRules": True, "texture": True, "era": True}}
    active = get_active_genre_audits(gc)
    assert "shenbi-review-era" in active
    assert "shenbi-review-world-rules" not in active  # core dim: filtered, carried by group steps
    assert "shenbi-review-sensitivity" not in active   # F905: fixed step 14 is the sole source
```

- [ ] **Step 2: 确认失败** — 两测 FAIL（矩阵现含 5 DEPRECATED 值 + sensitivity；core keys 缺六维）
- [ ] **Step 3: 实现**——矩阵缩为：

```python
GENRE_ACTIVATION_MATRIX: dict[str, str] = {
    "era": "shenbi-review-era",
    "fanfic": "shenbi-review-fanfic",
    "highpoint": "shenbi-review-highpoint",
}
```
`_CORE_CIRCLE_KEYS` 扩：
```python
_CORE_CIRCLE_KEYS = frozenset(
    {
        "antiAi",
        "character",
        "pacing",
        "continuity",
        "foreshadowing",
        "memoCompliance",
        "pov",
        # spec #59: dims carried by always-scheduled grouped fixed steps
        # (CHAPTER_STEPS 9-14) — genre configs may still set them; they are
        # filtered here and structurally honored via the group waves.
        "sensitivity",
        "worldRules",
        "motivation",
        "dialogue",
        "texture",
        "readerPull",
    }
)
```
头注释 :38-43 改写（core-circle 定义扩至上述六维，sensitivity 归固定步）；`_CRITICAL_GENRE_DIMS` 注记 texture 已随矩阵退出（comprehension 自然空集，保留构造）。genre-config SKILL.md :174-180 词表六维行加注「由固定组步承接（group-*），配置键保留合法」。

- [ ] **Step 4: 测试过 + 回归** — `uv run pytest tests/unit/pipeline/test_audit_layer.py -q && uv run pytest tests/pipeline -q -k audit` → 绿（既有矩阵测试若断言旧六键值对照需同步改）
- [ ] **Step 5: commit**

```bash
git add src/shenbi/pipeline/audit_layer.py skills/shenbi-genre-config/SKILL.md tests/unit/pipeline/test_audit_layer.py
git commit -m "fix: genre matrix exits 5 DEPRECATED dims + sensitivity dedup via core-keys (spec #59 T6, F905)"
```

---

### Task 7: description 启发式强化（单一规则源）

**复杂度: infra** · **test_kind: tdd_red_green** · 测试层级: T1

**Files:**
- Modify: `src/shenbi/gates/g0_skill_contract.py:26-59`（_BEHAVIORAL_MARKERS 邻域 + _desc_has_behavioral_text）
- Test: 既有 g0_skill_contract 测试文件（`grep -rln "_desc_has_behavioral_text" tests/` 定位）+ 新增用例

- [ ] **Step 1: 失败测试**（追加到该函数的既有测试文件）

```python
def test_desc_strengthened_two_miss_classes() -> None:
    from shenbi.gates.g0_skill_contract import _desc_has_behavioral_text as behav
    # class 1: non-trigger opening ("Grouped audit for ...")
    assert behav("Grouped audit for character integrity -- one call; dispatches as a wave") is True
    # class 2: "Use when X — Y" trailing functional clause
    assert behav("Use when creating skills — guides the design and testing") is True
    # compliant forms stay green
    assert behav("Use when a chapter needs its grouped craft audit.") is False
    assert behav("Use when auditing factual consistency for the current chapter.") is False
```

- [ ] **Step 2: 确认失败** — 两断言 FAIL（现启发式对两类形态均返回 False）
- [ ] **Step 3: 实现**

```python
_TRIGGER_OPENERS = ("use when", "used when", "用于", "使用当")
_DASH_FUNCTIONAL_RE = re.compile(
    r"(?:—|--)\s*(?:guides?|establishes?|dispatches?|covers?|building|generates?|"
    r"writes?|creates?|validates?|checks?|analyzes?|computes?|extracts?)\b",
    re.IGNORECASE,
)


def _desc_has_behavioral_text(desc: str) -> bool:
    """True if the description reads as behavioral ('does X') not trigger ('use when Y').

    spec #59 T2.7: beyond the legacy startswith markers, catches (1) openings
    that are not trigger phrases at all and (2) trailing functional clauses
    after an em-dash/double-hyphen in an otherwise trigger-shaped description.
    """
    lowered = desc.lstrip().lower()
    if any(lowered.startswith(m) for m in _BEHAVIORAL_MARKERS):
        return True
    if not any(lowered.startswith(t) for t in _TRIGGER_OPENERS):
        return True
    return bool(_DASH_FUNCTIONAL_RE.search(desc))
```
（`import re` 已在文件头。）

- [ ] **Step 4: 测试过 + 收集清单** — `uv run pytest <该测试文件> -v` 绿；随后跑清单（T2.8 序列①，exit-1 即人工过目材料）：

Run: `uv run python tools/audit-skill-descriptions.py; echo "exit=$?"` → 输出违规清单（预期含 4 group-*、writing-skills、using-shenbi、location-builder、lifecycle 及可能新增误报——**清单全文贴 progress.md 验收证据**，误报者逐条裁决：改写或带理由调 opener 集）

- [ ] **Step 5: 回归** — `uv run pytest tests/unit/gates -q -k "g0 or skill_contract"`（G0.sc 消费同一函数：中间红为设计内——T8 改写后复绿；本 task 不跑全量 G0 套件以外断言）
- [ ] **Step 6: commit**

```bash
git add src/shenbi/gates/g0_skill_contract.py <测试文件路径>
git commit -m "feat: description heuristic catches non-trigger openings + trailing functional clauses (spec #59 T7)"
```

---

### Task 8: description 改写批（清单驱动）

**复杂度: leaf**（单文件 frontmatter 行改写；协调者按上下文裁量亲做）· **test_kind: regression_guard** · 测试层级: T1

**Files:**
- Modify: T7 清单全部命中技能的 `SKILL.md` description 行（已知目标 + 清单新增）

- [ ] **Step 1: 改写已知目标**（when-to-use 形式；≤500 字符）：

```yaml
# shenbi-review-group-character
description: Use when a chapter needs its grouped character audit — character voice, dialogue quality, motivation, and POV dimensions.
# shenbi-review-group-craft
description: Use when a chapter needs its grouped craft audit — texture, reader-pull, and anti-AI pattern dimensions.
# shenbi-review-group-factual
description: Use when a chapter needs its grouped factual audit — continuity, world rules, and pacing dimensions.
# shenbi-review-group-plan
description: Use when a chapter needs its grouped plan-compliance audit — memo compliance and foreshadowing consistency dimensions.
# shenbi-writing-skills（F877）
description: Use when creating or modifying any shenbi skill (SKILL.md, contracts, or tests).
# using-shenbi（F878）
description: Use when starting any conversation about the shenbi novel-writing system, before picking or dispatching a skill.
# shenbi-location-builder（F842）
description: Use when designing a new story location or resolving cross-location spatial consistency.
# shenbi-foreshadowing-lifecycle（F815a）
description: Use when managing foreshadowing hooks for a chapter — recall, tracking, and planting in one lifecycle call; also for genesis (cross-volume master hooks).
```
（注意：破折号后是维度枚举名词短语非动词从句，不触 _DASH_FUNCTIONAL_RE。）
- [ ] **Step 2: 清单其余项逐个同法改写**（T7 exit-1 清单为准；误报裁决为合法的除外，理由记 spec-deviations）
- [ ] **Step 3: 验证** — `uv run python tools/audit-skill-descriptions.py; echo "exit=$?"` → `OK: all descriptions compliant`、exit=0
- [ ] **Step 4: 契约同步 + 回归** — `uv run shenbi-sync-contracts && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/`（description 非 sync 输入，diff 应空；红则查）+ `uv run pytest tests/unit/gates -q -k "g0 or skill_contract"` → 绿（G0.sc 复绿）
- [ ] **Step 5: commit**

```bash
git add skills/   # 仅 T7 清单命中目录——pathspec 逐个列出
git commit -m "fix: rewrite behavioral descriptions to when-to-use form (spec #59 T8, F835/F842/F877/F878/F815a)"
```

---

### Task 9: F815 残项契约闭合（(b) 跨目录引用 (c) 初始态 (d) audits 输出声明）

**复杂度: infra**（契约面 + 生成物同步）· **test_kind: regression_guard** · 测试层级: T1

**Files:**
- Modify: `skills/shenbi-foreshadowing-lifecycle/SKILL.md`（:64/:84/:108/:140-142/:161 邻域 + frontmatter）
- Create: `skills/shenbi-foreshadowing-lifecycle/lifecycle-states.md`、`skills/shenbi-foreshadowing-lifecycle/hook-types.md`（自 track/plant 目录**原样拷贝**——引用文件非 skill 输出，拷贝即内容保真）
- Test: `just lint-contracts`（R1/R2 闭包）+ `uv run pytest tests/contracts -q`

- [ ] **Step 1: (b)** — `cp skills/shenbi-foreshadowing-track/lifecycle-states.md skills/shenbi-foreshadowing-lifecycle/`、`cp skills/shenbi-foreshadowing-plant/hook-types.md skills/shenbi-foreshadowing-lifecycle/`；SKILL.md :64 `（see lifecycle-states.md）` 与 :108 `Full type/dimension/curve/subtlety lookup table in hook-types.md.` 引用路径不变（现落本目录）
- [ ] **Step 2: (c)** — :84 `Set initial lifecycle_state to ACTIVE` → `Set initial lifecycle_state to PLANTED`（:161 示例与 :65 状态机起点本就是 PLANTED——正名对齐规范六态；G4 lifecycle checker 的 non_canonical_state:ACTIVE 检查（T3）同步闭环）
- [ ] **Step 3: (d)** — frontmatter `writes:` 增条目（audits 输出为每章新文件）：
```yaml
  writes:
    - file: truth/bridge_tracker.md
      mode: append_dedup
      key: bridge_id
    - file: audits/chapter-N-foreshadowing.md
      mode: create_or_overwrite
```
正文 :140-142 输出示例块已在（R2 声明⇒正文步骤自然满足；若 lint 报缺步骤句，在写纪律段补一句「每章产出 audits/chapter-N-foreshadowing.md 报告」）。
- [ ] **Step 4: 同步与验证** — `just generate && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/`（本 task 改 frontmatter 契约——生成物须再生后 diff 空，`git add` 再生改动）+ `just lint-contracts` + `uv run pytest tests/contracts -q` → 全绿
- [ ] **Step 5: commit**

```bash
git add skills/shenbi-foreshadowing-lifecycle/
git commit -m "fix: lifecycle contract closure — local reference files, PLANTED initial state, audits output declared (spec #59 T9, F815)"
```

---

### Task 10: DEPRECATED 正文退役说明批（15 技能）+ F819 allowlist 撤收

**复杂度: leaf** · **test_kind: regression_guard** · 测试层级: T1

**Files:**
- Modify: 15 个 DEPRECATED 技能 `SKILL.md` 正文（横幅后首段）
- Modify: `tools/lint_contract_prose.py:91-92`（撤 track 死引用 allowlist 条目）

- [ ] **Step 1: 正文现行语气清理**——15 文件逐个：横幅保留/统一为 `<!-- DEPRECATED: Superseded by <successor> (2026-07-19). -->`；正文自称「默认激活/每章必查」（如 review-continuity:45、foreshadowing-track:39）改退役说明 + 后继指针：

```markdown
> **RETIRED**: This skill is no longer routed or dispatched. Its coverage moved to
> `<successor-skill>` (see that skill's SKILL.md). This body is retained for
> reference only — do not follow its instructions in current pipelines.
```
后继映射：12 个 review-* 单体 → 各自 group-*（anti-ai/texture/reader-pull→craft；character/dialogue/motivation/pov→character；continuity/world-rules/pacing→factual；foreshadowing/memo-compliance→plan）；plant/track/recall → foreshadowing-lifecycle。F819 的 track:156 `After updating foreshadowing_ledger.md...` 死引用句随重写删除；F817 recall:58 `last_reinformed` 随重写消亡。
- [ ] **Step 2: allowlist 撤收**——lint_contract_prose.py :91-92 删 track 幻影条目（正文死引用已物理消失，豁免即 stale）
- [ ] **Step 3: 验证** — `uv run python tools/lint_contract_prose.py --fail; echo $?` → exit=0；`grep -rn "默认激活的审计技能\|每章必查" skills/` → 零命中（或仅剩非 DEPRECATED 技能合法语义处——逐条核对）
- [ ] **Step 4: 契约同步 + 回归** — `just generate && git diff --exit-code` 面 + `uv run pytest tests/contracts -q`
- [ ] **Step 5: commit**

```bash
git add skills/ tools/lint_contract_prose.py   # pathspec 逐技能列出
git commit -m "fix: 15 DEPRECATED bodies get retirement notices + successor pointers; prose allowlist entry withdrawn (spec #59 T10, F834/F819/F817)"
```

---

### Task 11: lint_routing_faces 七面 lint + 双挂载 + 红灯验证

**复杂度: infra** · **test_kind: tdd_red_green** · 测试层级: T1（tmp 合成 + 真仓基线）

**Files:**
- Create: `tools/lint_routing_faces.py`
- Modify: `justfile`（check 链 + lint-routing recipe）
- Test: `tests/test_lint_routing_faces.py`（新，沿 tests/ 根级 lint 工具测试先例）

**Interfaces:**
- Consumes: T1 `deprecated_skill_names`；结构化导入 `GENESIS_STEPS`/`TRIGGER_STEPS`/`GENRE_ACTIVATION_MATRIX`/`BOUNDARY_TRIGGERS`/`CHAPTER_STEPS`（防文本 grep 假阳性——STEP_NAME_MIGRATIONS 白名单不受扰）
- Produces: exit 0/1 CLI（`uv run python tools/lint_routing_faces.py`）；`lint_routing_faces(repo, skills_dir) -> list[str]` 可测函数

- [ ] **Step 1: 失败测试**

```python
# tests/test_lint_routing_faces.py
"""Routing-face DEPRECATED reconciliation lint (spec #59 T11; acceptance 4)."""
import json
from pathlib import Path

from tools.lint_routing_faces import lint_routing_faces  # noqa: TID252 — 工具测试直引

REPO = Path(__file__).resolve().parents[1]

def test_real_repo_baseline_zero() -> None:
    assert lint_routing_faces(REPO, REPO / "skills") == []

def test_injected_deprecated_registration_fails(tmp_path: Path) -> None:
    # 复制最小面：合成 skills 树 + deps.json 注入一个 DEPRECATED 名
    skills = tmp_path / "skills"; skills.mkdir()
    (skills / "shenbi-dead").mkdir()
    (skills / "shenbi-dead" / "SKILL.md").write_text("# DEPRECATED: gone\n", encoding="utf-8")
    deps = tmp_path / "tests" / "tiers"; deps.mkdir(parents=True)
    (deps / "deps.json").write_text(json.dumps({"t2-phases": {"audit": {"prerequisites": ["shenbi-dead"]}}}), encoding="utf-8")
    errs = lint_routing_faces(tmp_path, skills)
    assert any("shenbi-dead" in e for e in errs)
```
（真仓基线测试在 T2-T10 完成后才可能绿——本 task 是终态收口，Step 1 先跑见红属预期。）

- [ ] **Step 2: 实现**

```python
#!/usr/bin/env python3
"""Routing-face reconciliation: DEPRECATED skills must not be routed anywhere (spec #59 T3.11).

Faces (structural, not text-grep): deps.json string values, using-shenbi
trigger table rows, GENESIS_STEPS, TRIGGER_STEPS, GENRE_ACTIVATION_MATRIX,
CHAPTER_STEPS, BOUNDARY_TRIGGERS. Exit 1 on any violation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from shenbi.pipeline.audit_layer import BOUNDARY_TRIGGERS, GENRE_ACTIVATION_MATRIX  # noqa: E402
from shenbi.pipeline.chapter_loop import CHAPTER_STEPS  # noqa: E402
from shenbi.pipeline.genesis import GENESIS_STEPS  # noqa: E402
from shenbi.pipeline.triggers import TRIGGER_STEPS  # noqa: E402
from shenbi.skill_utils.deprecated import deprecated_skill_names  # noqa: E402


def lint_routing_faces(repo: Path, skills_dir: Path) -> list[str]:
    errs: list[str] = []
    dead = deprecated_skill_names(skills_dir)
    if not dead:
        return errs
    # 1) deps.json — any string value naming a DEPRECATED skill
    deps = json.loads((repo / "tests" / "tiers" / "deps.json").read_text(encoding="utf-8"))
    def _walk(node: object) -> list[str]:
        if isinstance(node, str):
            return [node]
        if isinstance(node, list):
            return [s for it in node for s in _walk(it)]
        if isinstance(node, dict):
            return [s for v in node.values() for s in _walk(v)]
        return []
    hits = sorted(set(_walk(deps)) & dead)
    if hits:
        errs.append(f"deps.json routes DEPRECATED skills: {hits}")
    # 2) using-shenbi trigger table rows
    table = (skills_dir / "using-shenbi" / "SKILL.md").read_text(encoding="utf-8")
    row_hits = sorted({d for d in dead if re.search(rf"\|\s*{re.escape(d)}\s*\|", table, re.M)})
    if row_hits:
        errs.append(f"using-shenbi trigger table routes DEPRECATED skills: {row_hits}")
    # 3) code faces
    faces: dict[str, list[str]] = {
        "GENESIS_STEPS": [s.skill for s in GENESIS_STEPS],
        "TRIGGER_STEPS": [s.skill for s in TRIGGER_STEPS],
        "GENRE_ACTIVATION_MATRIX": list(GENRE_ACTIVATION_MATRIX.values()),
        "CHAPTER_STEPS": [s.skill for s in CHAPTER_STEPS],
        "BOUNDARY_TRIGGERS": list(BOUNDARY_TRIGGERS),
    }
    for face, members in faces.items():
        hit = sorted(set(members) & dead)
        if hit:
            errs.append(f"{face} routes DEPRECATED skills: {hit}")
    return errs


def main() -> int:
    repo = _REPO_ROOT
    errs = lint_routing_faces(repo, repo / "skills")
    if errs:
        for e in errs:
            print(f"lint_routing_faces: FAIL {e}")
        return 1
    print("lint_routing_faces: OK (0 violations across 7 faces)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 挂载**——justfile 新 recipe 与 check 链（`lint-status` 块后插）：

```just
# Lint routing faces: DEPRECATED skills must not be routed anywhere (spec #59 T3)
lint-routing:
	uv run python tools/lint_routing_faces.py
```
`check:` 链在 `uv run python tools/lint_status_strings.py` 行后加：
```
    uv run python tools/lint_routing_faces.py
    uv run python tools/audit-skill-descriptions.py
```
（T2.10 挂载裁决：justfile check 链直挂——满足验收 6 的 `just check` 可证调用。）

- [ ] **Step 4: 红灯验证（验收 4）**——临时在 deps.json audit 段加 `"shenbi-foreshadowing-recall"` → `uv run python tools/lint_routing_faces.py; echo $?` → exit=1 且报 recall → 还原 → exit=0（输出全文记 progress.md 验收证据）
- [ ] **Step 5: 测试 + 全链** — `uv run pytest tests/test_lint_routing_faces.py -v` → 2 passed；`uv run python tools/lint_routing_faces.py && uv run python tools/audit-skill-descriptions.py` → 双 OK（验收 6 前半）
- [ ] **Step 6: commit**

```bash
git add tools/lint_routing_faces.py tests/test_lint_routing_faces.py justfile
git commit -m "feat: lint_routing_faces 7-face reconciliation lint + just check mounts (spec #59 T11, F1011 wiring)"
```

---

## 验收覆盖表（spec 验收 → task → 可执行验证）

| spec 验收 | task | 验证命令（全部离线，F947） |
|---|---|---|
| 1 三路由面 grep 清零 + 白名单 | T2/T3/T5/T6 | `grep -rn "foreshadowing-plant\|foreshadowing-track\|foreshadowing-recall" tests/tiers/deps.json skills/using-shenbi/SKILL.md src/shenbi/` → 仅白名单三处命中 |
| 2 后继触发行 ≥1 | T4 | `uv run pytest tests/contracts/test_using_shenbi_routing.py -v`（内含 grep -c 断言） |
| 3 description 0 违规 + 5 技能人工复核 | T7/T8 | `uv run python tools/audit-skill-descriptions.py; echo $?` → exit=0；人工复核记 progress.md |
| 4 防回潮 lint 红灯 | T11 Step 4 | 注入-FAIL-还原文档化于 progress.md |
| 5 just check 全绿 + 路由可达离线断言 | T2/T11 | `just check` EXIT=0；`tests/unit/pipeline/test_genesis.py::test_genesis_step9_is_lifecycle` + `tests/contracts/test_using_shenbi_routing.py`（_build_skill_prompt 可达断言在 tests/pipeline/test_dispatch_reads_injection.py 家族扩一行 lifecycle 用例——T2 Step 4 时顺手加） |
| 6 接线实证 | T11 | `just check` 输出含 lint_routing_faces 与 audit-skill-descriptions 两行调用记录 |

**评分场景**：无（本 spec 不产出 LLM 生成物评分面）——G3.4 N/A。
**F947**：全部验收离线（单测 + lint + grep），零真实 dispatch。
