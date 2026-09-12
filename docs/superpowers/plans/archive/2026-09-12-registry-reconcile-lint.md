# C22 平行登记表对账门禁（registry-reconcile）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 单一对账 lint（R1-R5）收口五族平行登记表与磁盘现实的双向闭包，修 F432 生产假 FAIL 与 F1004 master.json 缺口/DEPRECATED 路由等 29 条簇成员。

**Architecture:** 先做 T0 结构前置（gate 内局部注册表提升为可 import 的模块级事实 + canonicalizer 统一），再写 `tools/lint_registry_reconcile.py`（五规则一体、repo-root 参数化、机器可读输出），存量数据分表修正转绿（每表一 commit），终态重锁 `_tool_hashes` + 红灯五样本验证，最后双挂载 CI/justfile。

**Tech Stack:** Python 3.11+ (uv)，pytest，纯标准库 lint（json/yaml/pathlib/fnmatch/hashlib），justfile + GitHub Actions ci.yml。

**Spec:** `docs/superpowers/specs/2026-08-16-audit-registry-reconcile-fix.md`（Revised 2026-09-12，设计审查六轮收敛版）

## Global Constraints

- 框架代码（`src/shenbi/`）无 `print()`（structlog / cli_utils.echo）；gate 检查器纯函数幂等；pathlib 文件 I/O
- 状态字面量唯一定义于 `src/shenbi/contracts/enums.py`（新代码不引裸状态串，`tools/lint_status_strings.py` 红 = Critical）
- 验证一律 `just`/`uv run`（与 CI `uv run --frozen` 同构）；系统 python 结果不算证据
- 禁真实 LLM dispatch（核心原则 8）；验收全离线可复验
- commit 走 Conventional Commits 且**显式列文件路径**（禁 `git add -A`）
- `_tool_hashes` 的 193 条在 T1/T2 改 src 期间会过期——**仅 Task 14 终态重锁一次**，中途 `just check` 若因哈希红属预期（spec R3 已声明）
- **中途红窗口一个**：_tool_hashes（src 改动起至 Task 14 终态重锁——Task 3 Step 4b 同 task 补花括号 patterns 已消除 lint_contract_graph 窗口）。窗口外的 lint/测试红 = 真缺陷（**例外**：`test_clean_repo_zero_violations` 自 Task 4 起设计性红至 Task 14——数据面转绿前它就是红的）
- master.json 版本单源化取**保守方案：只校验不生成**（pyproject 为源）

## 验收覆盖表（spec 验收 → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1. lint exit 0 + 0 violations（FAIL 级）+ 临时副本五负样本各红 | T4/T5/T14 | `uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume` + tests/unit/test_lint_registry_reconcile.py 负样本测试 |
| 2. master.json == 59 live ∧ ∩ DEPRECATED = ∅；deps 维持；_tool_hashes 193/193 | T6/T14 | R1 lint 面 + `tests/lock-tool-hashes.sh` 复验 |
| 3. F432 回归：缺 glob checker-having → FAIL marker（非 exception） | T3/T4 | tests/unit/gates/test_g5_missing_glob.py |
| 4. AGENTS.md 计数去数字化 | T10 | grep AGENTS.md 无 "72 functional" |
| 5. 双挂载 justfile check + ci.yml lint step | T15 | `just --dry-run check` 含 lint 行；grep ci.yml |

---

### Task 1: T0a-1 — G5_CHECKER_GLOBS 模块级提升（行为保持）

**复杂度: infra**（`src/shenbi/gates/g5.py`）· **test_kind: characterization** · 测试层级 T1

**Files:**
- Modify: `src/shenbi/gates/g5.py:271-295`（dict 字面量移出 `gate_G5`）
- Test: `tests/unit/gates/test_g5_globs_module_level.py`（新建）

**Interfaces:**
- Produces: `from shenbi.gates.g5 import G5_CHECKER_GLOBS` — `dict[str, list[str]]`，模块级常量，19 条现存 + Task 8 再 +9

- [ ] **Step 1: 写特征测试（characterization）**

```python
"""G5_CHECKER_GLOBS is module-level and importable (spec #60 T0a-1)."""
from shenbi.gates.g5 import G5_CHECKER_GLOBS


def test_globs_module_level_importable():
    assert isinstance(G5_CHECKER_GLOBS, dict)
    assert G5_CHECKER_GLOBS["shenbi-worldbuilding"] == ["novel.json", "genre-config.json", "world/*.md", "truth/*.md"]


def test_globs_entry_count_baseline():
    # 19 at extraction time; Task 8 adds 9 → 28. Pin the floor, not the ceiling.
    assert len(G5_CHECKER_GLOBS) >= 19
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/gates/test_g5_globs_module_level.py -v`
Expected: FAIL `ImportError: cannot import name 'G5_CHECKER_GLOBS'`

- [ ] **Step 3: 移动 dict 到模块级**——将 g5.py:271-294 的 `G5_CHECKER_GLOBS = {...}`（19 条整块）从 `def gate_G5` 体内剪切，粘贴到模块级（`gate_G5` 定义之前，带类型注解）：

```python
G5_CHECKER_GLOBS: dict[str, list[str]] = {
    "shenbi-worldbuilding": ["novel.json", "genre-config.json", "world/*.md", "truth/*.md"],
    # ...其余 18 条原样照搬，一字不改...
}
```

`gate_G5` 体内原位置删除该定义；:317 的 `G5_CHECKER_GLOBS.get(pr, ["*.md"])` 引用不变（本 task 不动语义，FAIL 化在 Task 3）。

- [ ] **Step 4: 跑测试 + G5 既有回归**

Run: `uv run pytest tests/unit/gates/test_g5_globs_module_level.py -v && uv run pytest tests/ -k "g5" -q`
Expected: 全 PASS（G5 既有测试证明行为不变）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g5.py tests/unit/gates/test_g5_globs_module_level.py
git commit -m "refactor: hoist G5_CHECKER_GLOBS to module level (spec60 T0a-1, behavior-preserving)"
```

---

### Task 2: T0a-2 — build_checkers() 工厂 + G4_DECISIONS_WIRED 导出 + F1017 派生改造

**复杂度: infra**（`src/shenbi/gates/g4/generic.py`、`tools/lint_repo_consistency.py`）· **test_kind: characterization**（提取）+ **tdd_red_green**（F1017 派生）· T1

**Files:**
- Modify: `src/shenbi/gates/g4/generic.py:289-357`（`gate_G4` 内 checkers 构造提取为模块级工厂）
- Modify: `tools/lint_repo_consistency.py:112-122`（硬编码快照改派生）
- Test: `tests/unit/gates/g4/test_build_checkers.py`（新建）

**Interfaces:**
- Produces: `build_checkers() -> dict[str, Callable]`（模块级工厂，late imports 保留）；`G4_DECISIONS_WIRED: frozenset[str]`（8 条：chapter-drafting/chapter-planning/context-composing/genre-config/chapter-revision/short-drafting/state-settling/market-radar）；`G4_CHECKER_KEYS: frozenset[str]`（30 键，纯字符串无函数引用）

- [ ] **Step 1: 写失败测试**

```python
"""build_checkers() factory + declarative wiring facts (spec #60 T0a-2 / F1017)."""
from shenbi.gates.g4.generic import G4_CHECKER_KEYS, G4_DECISIONS_WIRED, build_checkers


def test_build_checkers_returns_thirty():
    checkers = build_checkers()
    assert len(checkers) == 30
    assert set(checkers) == G4_CHECKER_KEYS


def test_decisions_wired_is_eight():
    assert G4_DECISIONS_WIRED == frozenset({
        "shenbi-chapter-drafting", "shenbi-chapter-planning", "shenbi-context-composing",
        "shenbi-genre-config", "shenbi-chapter-revision", "shenbi-short-drafting",
        "shenbi-state-settling", "shenbi-market-radar",
    })


def test_wired_subset_of_checkers():
    assert G4_DECISIONS_WIRED <= G4_CHECKER_KEYS
```

- [ ] **Step 2: 确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_build_checkers.py -v`
Expected: FAIL `ImportError`

- [ ] **Step 3: 提取工厂**——generic.py：把 `gate_G4` 体内 `from shenbi.gates.g4.decisions_validator import ...` 起到 `register_score_checkers(checkers)` 止的整块构造，移入新模块级函数。**late imports 原样保留在工厂体内**（循环导入规避 + spawn 成本，见 cli.py T1604 记录）：

```python
G4_DECISIONS_WIRED: frozenset[str] = frozenset({
    "shenbi-chapter-drafting", "shenbi-chapter-planning", "shenbi-context-composing",
    "shenbi-genre-config", "shenbi-chapter-revision", "shenbi-short-drafting",
    "shenbi-state-settling", "shenbi-market-radar",
})


def build_checkers() -> dict[str, Callable[..., object]]:
    """Construct the per-skill G4 checker registry.

    Late imports are deliberate (circular-import avoidance; see cli.py T1604).
    G4_DECISIONS_WIRED is asserted against the actual wiring so the declarative
    frozenset cannot drift from the composite construction (F1017 recurrence guard).
    """
    from shenbi.gates.g4.decisions_validator import g4_decisions, make_composite_checker
    # ...其余 late imports 照搬...

    wired: set[str] = set()

    def comp(base: Callable[..., object], name: str, pred=None) -> Callable[..., object]:
        wired.add(name)
        return make_composite_checker(base, g4_decisions) if pred is None else make_composite_checker(base, g4_decisions, pred)

    checkers: dict[str, Callable[..., object]] = {
        # 原字典 27 条照搬；make_composite_checker 两参处改 comp(x, "<同名>")；
        # 三参处（chapter-revision 的 decisions_match 谓词，decisions_validator.py:148-161）改 comp(x, "<同名>", pred) 透传——
        # 漏谓词会静默改变 revision-decisions.json 的路由（plan 审查轮 1 I3）；
        # 凡裸 g4_decisions 赋值处（market-radar 等）跟一行 wired.add("<名>")
        ...
    }
    register_score_checkers(checkers)
    assert wired == set(G4_DECISIONS_WIRED), (
        f"G4_DECISIONS_WIRED drifted: {wired ^ set(G4_DECISIONS_WIRED)}"
    )
    return checkers
```

模块顶部（late-import-free 区域）加：

```python
G4_CHECKER_KEYS: frozenset[str] = frozenset({
    # 27 个静态键照搬自 checkers 字面量 + 3 个 score 键（scoring_sections 的
    # shenbi-score-arc / shenbi-score-stratum / shenbi-score-volume）
})
```

并在 `build_checkers()` 的 assert 后追加 `assert set(checkers) == G4_CHECKER_KEYS`。`gate_G4` 体内改为 `checkers = build_checkers()`。

- [ ] **Step 4: F1017 派生改造**——`tools/lint_repo_consistency.py:112` 删除 `_G4_DECISIONS_SKILLS = frozenset({...7 条...})` 字面量，改为：

```python
from shenbi.gates.g4.generic import G4_DECISIONS_WIRED as _G4_DECISIONS_SKILLS  # noqa: E402
```

（tools/ 脚本 import src 的既有模式见 lint_routing_faces.py:16-21 的 sys.path 注入；lint_repo_consistency 若无则照抄该三行注入。）

- [ ] **Step 5: 跑测试 + G4 全量回归**

Run: `uv run pytest tests/unit/gates/g4/test_build_checkers.py -v && uv run pytest tests/ -k "g4 or repo_consistency" -q && uv run python tools/lint_repo_consistency.py; echo "exit=$?"`
Expected: 全 PASS / lint exit=0

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/gates/g4/generic.py tools/lint_repo_consistency.py tests/unit/gates/g4/test_build_checkers.py
git commit -m "refactor: build_checkers() factory + G4_DECISIONS_WIRED/G4_CHECKER_KEYS exports; F1017 snapshot now derived (spec60 T0a-2)"
```

---

### Task 3: T0b — canonicalizer 统一 + T203 DAG 停用 + F432 G5 FAIL marker

**复杂度: infra**（`src/shenbi/contracts/graph.py`、`src/shenbi/sync_contracts.py`、`src/shenbi/gates/g5.py`）· **test_kind: tdd_red_green** · T1

**Files:**
- Modify: `src/shenbi/contracts/graph.py:42-59`（`dag_key` 改 patterns-first 委托）
- Modify: `src/shenbi/sync_contracts.py`（T203：停用 dependency-dag.json 写出）
- Modify: `src/shenbi/gates/g5.py:315-322`（F432：checker-having 缺 glob → FAIL marker）
- Test: `tests/unit/contracts/test_dag_key_unified.py`、`tests/unit/gates/test_g5_missing_glob.py`（新建）

**Interfaces:**
- Consumes: Task 2 的 `G4_CHECKER_KEYS`
- Produces: `dag_key(path, registry)` 语义 == `normalize_to_glob(path, registry)`（patterns 优先）；G5.5 缺 glob 输出 FAIL marker **字符串** `f"G5.5:{pr}:missing G5_CHECKER_GLOBS entry"`（`mf` 是 `list[str]`，g5.py:343 做 `startswith("G5.5:")` 扫描——dict marker 会在守卫外 AttributeError，plan 轮 3 I2）

**T0b 裁决（写入实现的决策，spec 允许二选一后落定）**：统一为 **patterns-first**。理由：`dag_key` 的 globs-first 会把 `truth/arcs/arc-N.md` 折叠进宽 glob `truth/*.md`，使 DAG 边键与 `expected_outputs` 键（normalize_to_glob 产出）系统性发散——这正是本 spec 要消灭的「两个 canonicalizer 各说各话」；patterns-first 保参数化精度。**T203 裁决：停用 dependency-dag.json 生成**（唯一消费者是 CI codegen-idempotency 对它自身的 diff；lint_contract_graph 仍用 dag_key 做内存内对账，不受影响）。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/contracts/test_dag_key_unified.py
"""dag_key unified to patterns-first (spec #60 T0b)."""
import pytest

from shenbi.contracts.graph import dag_key, normalize_to_glob
from shenbi.contracts import load_registry  # 实际定义在 contracts/loader.py:112，经 shenbi.contracts 重导出


@pytest.mark.parametrize("path", [
    "truth/arcs/arc-N.md",
    "audits/chapter-N-anti-ai.md",
    "truth/pending_hooks.md",
    "world/power_system.md",
])
def test_dag_key_equals_normalize(path):
    reg = load_registry()
    assert dag_key(path, reg) == normalize_to_glob(path, reg)


def test_divergence_example_gone():
    reg = load_registry()
    # 审计分歧实例：统一后不得再折叠进宽 glob
    assert dag_key("truth/arcs/arc-N.md", reg) == normalize_to_glob("truth/arcs/arc-N.md", reg)
```

```python
# tests/unit/gates/test_g5_missing_glob.py
"""F432: checker-having prereq missing glob => FAIL marker, not *.md sweep (spec #60 R5)."""
import json

from shenbi.gates.g5 import gate_G5


def _phase_with_missing_glob(tmp_path, monkeypatch, deps_dict):
    deps = tmp_path / "tiers" / "deps.json"
    deps.parent.mkdir(parents=True)
    deps.write_text(json.dumps(deps_dict), encoding="utf-8")
    monkeypatch.setattr("shenbi.gates.g5.TESTS", tmp_path.parent.parent / "tests" if False else tmp_path.parent)
    # 以 gate_G5 实际读取路径为准（grep g5.py TESTS 定义后对齐 monkeypatch 目标）


def test_missing_glob_checker_having_fails(tmp_path, monkeypatch):
    # prerequisites 含一个 checker-having 但 G5_CHECKER_GLOBS 无条目的技能
    # 构造最小 phase_data + project_dir（参照 tests/ 下既有 g5 测试的 fixture 组装方式）
    out = gate_G5(phase_name="drafting", round_dir=str(tmp_path), project_dir=str(tmp_path))
    assert "missing G5_CHECKER_GLOBS entry" in out
```

（测试组装细节以 `tests/unit/gates/` 既有 G5 测试的真实 fixture 模式为准——写测试前先 `ls tests/unit/gates/ | grep g5` 并读一个既有用例。）

- [ ] **Step 2: 确认失败**

Run: `uv run pytest tests/unit/contracts/test_dag_key_unified.py tests/unit/gates/test_g5_missing_glob.py -v`
Expected: FAIL（dag_key ≠ normalize 于 arc-N；G5 无 marker）

- [ ] **Step 3: dag_key 改委托**

```python
def dag_key(path: str, registry: TruthFilesRegistry) -> str:
    """Canonical matching key for a path in the DAG.

    Unified patterns-first (spec #60 T0b): identical to normalize_to_glob.
    The former globs-first ordering collapsed specific paths into broad
    declared globs (truth/arcs/arc-N.md -> truth/*.md), diverging from the
    expected_outputs keys produced by normalize_to_glob.
    """
    return normalize_to_glob(path, registry)
```

- [ ] **Step 4: T203 停用 DAG 写出**——`grep -n "dependency-dag" src/shenbi/sync_contracts.py`，删除/注释该写出块（保留 dag_key import 若 lint_contract_graph 消费；若 sync_contracts 不再需要则删 import）；同时 `grep -rn "dependency-dag" .github/ justfile tools/ tests/` 清空全部挂载点；`git rm` 仓库内 checked-in 的 dependency-dag.json（若存在）。

- [ ] **Step 4b: yaml 补三条花括号 patterns（C1 修复的强制宿主——patterns-first 统一的同 task 消防）**——`docs/framework/truth-files.yaml` patterns 节追加：

```yaml
  - parametric: chapters/chapter-{N-3}.md
    glob: chapters/chapter-*.md
  - parametric: chapters/chapter-{N-2}.md
    glob: chapters/chapter-*.md
  - parametric: chapters/chapter-{N-1}.md
    glob: chapters/chapter-*.md
```

（花括号 read 归一到与 producer `chapters/chapter-N.md` 相同的 `chapters/chapter-*.md` 键，消除 lint_contract_graph 的 3 个 ORPHAN_READ；patterns 节字段名以现文件为准对齐。）随后 `uv run shenbi-sync-contracts`，若 deps.json/生成物出现 diff 随本 task commit。

- [ ] **Step 5: G5 FAIL marker**——g5.py G5.5 循环内，替换 `globs = G5_CHECKER_GLOBS.get(pr, ["*.md"])`：

```python
from shenbi.gates.g4.generic import G4_CHECKER_KEYS  # 模块顶（纯 frozenset，无循环风险；若 CI 红则降为函数内 late import）

# 循环内：
if pr in G5_CHECKER_GLOBS:
    globs = G5_CHECKER_GLOBS[pr]
elif pr in G4_CHECKER_KEYS:
    mf.append(f"G5.5:{pr}:missing G5_CHECKER_GLOBS entry")  # mf is list[str]; :343 startswith scan
    continue
else:
    globs = ["*.md"]  # checker-less prereq: explicit default -> generic check
```

- [ ] **Step 6: 全量相关回归 + sync 幂等**

Run: `uv run pytest tests/unit/contracts/test_dag_key_unified.py tests/unit/gates/test_g5_missing_glob.py -v && uv run pytest tests/ -k "graph or g5 or sync" -q && uv run python tools/lint_contract_graph.py; echo "graph_exit=$?" && uv run shenbi-sync-contracts && git status --porcelain -- tests/tiers/deps.json docs/framework/ skills/`
Expected: 测试全 PASS；**lint_contract_graph 必须 exit 0**（Step 4b 已同 task 补三条花括号 patterns，无中间红窗口）；sync 后 deps.json/docs 生成物若因键归一变化，diff 随本 task commit

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/contracts/graph.py src/shenbi/sync_contracts.py src/shenbi/gates/g5.py docs/framework/truth-files.yaml tests/tiers/deps.json docs/framework/ tests/unit/contracts/test_dag_key_unified.py tests/unit/gates/test_g5_missing_glob.py
git commit -m "fix: unify canonicalizer patterns-first (T0b) + retire dependency-dag.json (T203) + G5 missing-glob FAIL marker (F432, spec60)"
```

---

### Task 4: Lint-1 — lint_registry_reconcile.py 骨架 + R1 技能闭包 + R5 glob 面

**复杂度: infra**（协调者亲做）· **test_kind: tdd_red_green** · T1

**Files:**
- Create: `tools/lint_registry_reconcile.py`
- Test: `tests/unit/test_lint_registry_reconcile.py`

**Interfaces:**
- Consumes: Task 1 `G5_CHECKER_GLOBS`、Task 2 `build_checkers()/G4_CHECKER_KEYS/G4_DECISIONS_WIRED`、`src/shenbi/skill_utils/deprecated.py: deprecated_skill_names(skills_dir: Path) -> frozenset[str]`
- Produces: `lint_registry_reconcile(repo: Path, allow_missing: frozenset[str] = frozenset()) -> list[str]`（FAIL 级 violations）；`main() -> int`（`--repo`、`--allow-missing` 参数）；机器可读输出行格式 `[RUL] table: direction: entry`

- [ ] **Step 1: 写失败测试**（R1 各面负样本——临时 repo 副本变异）

```python
# tests/unit/test_lint_registry_reconcile.py
"""lint_registry_reconcile R1/R5 faces (spec #60 T1)."""
import json
import shutil
from pathlib import Path

import pytest

from tools.lint_registry_reconcile import lint_registry_reconcile


@pytest.fixture()
def repo_copy(tmp_path: Path) -> Path:
    """Copy the minimal registry set into a temp repo root."""
    src = Path(__file__).resolve().parents[2]
    dst = tmp_path / "repo"
    for rel in ["plugins/master.json", "tests/tiers/deps.json", "docs/skills/index.md",
                "docs/framework/truth-files.yaml", "AGENTS.md",
                "src/shenbi/gates/g5.py", "src/shenbi/gates/shared.py",
                "src/shenbi/gates/g4/generic.py", "src/shenbi/contracts/registry.py",
                "src/shenbi/gates/cli.py",  # SHORT_MAP import face needs the module itself (plan r3 I1)
                "src/shenbi/__init__.py", "src/shenbi/gates/__init__.py"]:  # regular-package precedence (plan r1 I4)
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, dst / rel)
    shutil.copytree(src / "skills", dst / "skills")
    return dst


def test_clean_repo_zero_violations(repo_copy):
    # NOTE: this test stays RED from Task 4 until Tasks 6-11 land (the copy carries
    # the born-red inventory). It is finally green at Task 14. Do NOT data-fix inside Task 4.
    # score-×3 pipeline-internal exemption (Task 9 ruling) is passed here too:
    assert lint_registry_reconcile(
        repo_copy,
        allow_missing=frozenset({"shenbi-score-arc", "shenbi-score-stratum", "shenbi-score-volume"}),
    ) == []


def test_master_json_deprecated_route_fails(repo_copy):
    p = repo_copy / "plugins" / "master.json"
    m = json.loads(p.read_text())
    m["skills"].append("skills/shenbi-review-pov/SKILL.md")  # DEPRECATED
    p.write_text(json.dumps(m))
    vios = lint_registry_reconcile(repo_copy)
    assert any("master" in v and "DEPRECATED" in v for v in vios)


def test_short_map_deletion_fails(repo_copy):
    # SHORT_MAP 是 src 内代码——临时副本策略：lint 从 repo 根读 src/shenbi/gates/cli.py
    # 的 SHORT_MAP（AST/文本解析）或直接 import 前先 sys.path 指向副本 src。
    # 实现取 sys.path 注入法（lint_routing_faces 模式）：
    #   sys.path.insert(0, str(repo / "src"))  再 import shenbi.gates.cli
    p = repo_copy / "src" / "shenbi" / "gates" / "cli.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    import re as _re
    orig = (Path(__file__).resolve().parents[2] / "src/shenbi/gates/cli.py").read_text()
    p.write_text(_re.sub(r'"chapter-drafting": "shenbi-chapter-drafting",\n', "", orig, count=1))
    vios = lint_registry_reconcile(repo_copy)
    assert any("SHORT_MAP" in v for v in vios)
```

（其余面的负样本同构——spec 验收 1 五样本：master.json 加 DEPRECATED 路由（已列）/ SHORT_MAP 删一项（已列）/ **G5_GLOBS 删一条 checker-having 条目**（AST 面文本变异）/ 词表参数化概念 patterns+globs 双删 / _tool_hashes 改一字节（已拷贝目标如 g5.py）——五样本测试函数在本 task 与 Task 5 补齐。）

**缺失文件语义（plan 轮 3 I3）**：R1 seed 面与 R3 哈希面对副本中不存在的目标**跳过**（seed.md 未拷贝 → 该面 skip；`_tool_hashes` 条目目标文件不在副本 → 该条 skip）——副本 greenness 只断言已拷贝面；R3 负样本变异须选**已拷贝**目标的哈希（如 `src/shenbi/gates/g5.py`）。

**读取机制分派（plan 审查轮 2 I4 定案）**：可 import 面（SHORT_MAP 经 cli.py——stdlib-only 模块级）用 sys.path 副本注入 + `sys.modules` 清理；**不可 import 面（g5.py 的 G5_CHECKER_GLOBS、generic.py 的 checkers、shared.py 的 G4_CHECKER_SKILLS、registry/AGENTS/yaml）一律 AST/文本解析**（`ast.literal_eval` 提取 dict/set 字面量；注意 `frozenset({...})` 是 Call 节点不可 literal_eval——取其 `.args[0]`（Set 节点）或退正则，plan 轮 3 M2）——这些模块的 import 闭包（contracts/gates.shared/safe_write）在临时副本不可满足。fixture 拷贝清单相应只补 AST 面所需源文件与 `AGENTS.md`。

- [ ] **Step 2: 确认失败**（模块不存在）

- [ ] **Step 3: 实现 lint 主体**——规则面与不变量逐条（spec T1 R1 每面不变量行 + R5）：

```python
#!/usr/bin/env python3
"""Registry reconciliation lint (spec #60): five rule-faces R1-R5.

R1 skill closure (per-face invariants in spec), R2 word-list closure,
R3 hash freshness, R5 glob validity. R4 is delete-first (no lint rule).
Exit 1 on any FAIL-level violation; WARNs go to stderr and don't count.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def lint_registry_reconcile(repo: Path, allow_missing: frozenset[str] = frozenset()) -> list[str]:
    errs: list[str] = []
    errs += _r1_skill_closure(repo, allow_missing)
    errs += _r2_word_list(repo)
    errs += _r3_hash_freshness(repo)
    errs += _r5_glob_validity(repo)
    return errs
```

R1 各面实现要点（每面一个函数，violation 行格式 `[R1] <table>: <direction>: <entry>`）：
- `master.json ⊇/== live set ∧ ∩ DEPRECATED = ∅`：解析 `plugins/master.json` skills 路径列表 → 技能名，对照 `{p.name for p in skills_dir.iterdir()}` − `deprecated_skill_names(skills_dir)`
- `SHORT_MAP ⊇ checker-having`：sys.path 注入 repo/src 后 `import shenbi.gates.cli`（fresh interpreter 语义靠子进程或 importlib 缓存清理——**用 `importlib` + 显式 `sys.modules` 清理**，测试与 lint 内一致）
- `G5_GLOBS ⊇ checker-having ∧ t2-prereq`：deps.json `t2-phases.*.prerequisites` ∩ `G4_CHECKER_KEYS` ⊆ `G5_CHECKER_GLOBS` keys
- `G4_CHECKER_SKILLS == checkers 30`：`src/shenbi/gates/shared.py` 的 G4_CHECKER_SKILLS（文本解析或 import）== `build_checkers()` keys
- `docs/skills/index.md ⊇ live`、`using-shenbi SKILL.md ⊇ functional live − allow_missing − {2 meta}`、`t2 seed ⊇ prerequisites`（seed.md 文本含技能名字面 token）、`AGENTS.md 计数 = R1 输出（transitional：无数字即 PASS）`

- [ ] **Step 4: 测试过 + 手跑**

Run: `uv run pytest tests/unit/test_lint_registry_reconcile.py -v && uv run python tools/lint_registry_reconcile.py; echo "exit=$?"`

Expected: 负样本测试 PASS；**clean-repo 测试 RED（预期——副本带全量存量红清单，Tasks 6-11 转绿，Task 14 验收）**；真实 repo 跑出**存量 violations 清单**（master 14+14、SHORT_MAP 11、G5 9、backfill 面 21 缺口、seed 15 等——这是 T2 各 task 的转绿对象，此刻**预期红**，输出留档 progress.md）

- [ ] **Step 5: Commit**

```bash
git add tools/lint_registry_reconcile.py tests/unit/test_lint_registry_reconcile.py
git commit -m "feat: lint_registry_reconcile R1 skill-closure + R5 glob faces (spec60 T1)"
```

---

### Task 5: Lint-2 — R2 词表闭包 + R3 哈希新鲜度

**复杂度: infra** · **test_kind: tdd_red_green** · T1

**Files:**
- Modify: `tools/lint_registry_reconcile.py`（补 `_r2_word_list` / `_r3_hash_freshness`）
- Test: `tests/unit/test_lint_registry_reconcile.py`（追加）

**Interfaces:**
- Consumes: `src/shenbi/contracts/graph.py: normalize_to_glob/dag_key`（统一后等价；**副本运行不 import——临时副本 yaml 直接解析，load_registry 仅真实 repo CLI 路径用**（loader.py:112 为 PROJECT-bound 缓存加载器））、`src/shenbi/contracts/registry.py: known_skill_names()`（disk-derived，结构 no-op 面）、`tests/lock-tool-hashes.sh` 的哈希算法（读脚本提取：sha256 envelope `sha256:<hex>`）
- Produces: R2 面violation `[R2] yaml: ...`；R3 面 `[R3] _tool_hashes: stale: <path>`

- [ ] **Step 1: 失败测试**（yaml 双删负样本 + 哈希字节翻负样本 + 磁盘产物模式 ↔ yaml 闭包两向）
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现**——R2：解析 yaml（concepts/patterns/globs 三节）→ 检查 (a) 5 个参数化概念 glob 可解析（patterns 或 globs 二居一）；(b) `truth-files.index.json` 的 producer/consumer 概念名 ⊆ yaml concepts（write-only 报 WARN）；(c) 代码硬编码概念 grep 面（`src/shenbi/` 内 `truth/` 路径字面量）⊆ yaml。R3：deps.json `_tool_hashes` 逐条 sha256 复算。
- [ ] **Step 4: 测试 + 手跑**（预期 R2/R3 面存量红清单留档）
- [ ] **Step 5: Commit**

```bash
git add tools/lint_registry_reconcile.py tests/unit/test_lint_registry_reconcile.py
git commit -m "feat: R2 word-list closure + R3 hash freshness faces (spec60 T1)"
```

---

### Task 6: Data-1 — master.json +14 live / −14 DEPRECATED → 59

**复杂度: leaf** · **test_kind: regression_guard** · T1（负样本测试已在 Task 4）

**Files:**
- Modify: `plugins/master.json`

- [ ] **Step 1: 删 14 条 DEPRECATED 路径**：`skills/shenbi-foreshadowing-plant/SKILL.md`、`skills/shenbi-foreshadowing-track/SKILL.md`、`skills/shenbi-review-anti-ai/SKILL.md`、`skills/shenbi-review-character/SKILL.md`、`skills/shenbi-review-continuity/SKILL.md`、`skills/shenbi-review-dialogue/SKILL.md`、`skills/shenbi-review-foreshadowing/SKILL.md`、`skills/shenbi-review-memo-compliance/SKILL.md`、`skills/shenbi-review-motivation/SKILL.md`、`skills/shenbi-review-pacing/SKILL.md`、`skills/shenbi-review-pov/SKILL.md`、`skills/shenbi-review-reader-pull/SKILL.md`、`skills/shenbi-review-texture/SKILL.md`、`skills/shenbi-review-world-rules/SKILL.md`
- [ ] **Step 2: 补 14 条 live**：`skills/shenbi-anchor-curate/SKILL.md`、`skills/shenbi-book-spine-init/SKILL.md`、`skills/shenbi-escalation-review/SKILL.md`、`skills/shenbi-foreshadowing-lifecycle/SKILL.md`、`skills/shenbi-memory-distill/SKILL.md`、`skills/shenbi-review-arc-payoff/SKILL.md`、`skills/shenbi-review-group-character/SKILL.md`、`skills/shenbi-review-group-craft/SKILL.md`、`skills/shenbi-review-group-factual/SKILL.md`、`skills/shenbi-review-group-plan/SKILL.md`、`skills/shenbi-review-resonance/SKILL.md`、`skills/shenbi-score-arc/SKILL.md`、`skills/shenbi-score-stratum/SKILL.md`、`skills/shenbi-score-volume/SKILL.md`（保持既有排序惯例——先读当前列表顺序风格）
- [ ] **Step 3: 版本校验面**（F1005 保守方案）：lint 的 R1 面加 master.json `version == pyproject [project] version` 校验（`tomllib` 读 pyproject）；master.json version 改 `0.1.0` 对齐
- [ ] **Step 4: 验证**：`uv run python tools/lint_registry_reconcile.py 2>&1 | grep master` → 无 master violations；`uv run pytest tests/unit/test_plugins_generate.py -q`（generate.py 消费面回归，以实际测试名 grep 为准）
- [ ] **Step 5: Commit** `git add plugins/master.json tools/lint_registry_reconcile.py && git commit -m "fix: master.json 59 live closure (+14 live, -14 DEPRECATED routes, version aligned, F1004/F1005, spec60 T2.3)"`

---

### Task 7: Data-2 — t2 seeds + audit seed + rubric-only 登记 + AGENTS 去数字化 + F424 注释

**复杂度: leaf** · **test_kind: regression_guard** · T1

**Files:**
- Modify: `tests/tiers/t2-phase/{genesis,drafting,audit,management}/input/seed.md`、`AGENTS.md`、`src/shenbi/contracts/ownership.py:7`、deps.json `_out_of_pipeline._note`（F758）

- [ ] **Step 1: seed 补缺**——四个 seed 按 lint 输出的缺集（genesis 5：book-spine-init/genre-config/pacing-design/story-architecture/volume-outlining；drafting 2：review-resonance/score-arc；audit 4：review-group-×4；management 4：memory-distill/review-arc-payoff/score-stratum/score-volume）在步骤说明中补行（格式照 seed 既有条目文风）
- [ ] **Step 2: audit seed 清 12 个 DEPRECATED 点名**（"Run all 18 review skills" 段——改为后继 group-review 术语，参照 C21 的 using-shenbi 改写口径）
- [ ] **Step 3: F758**——deps.json `_out_of_pipeline._note` 文本改真实描述（schema-safe：OutOfPipeline `extra: forbid` 无 per-skill 标记位，**只改 `_note` 字符串**——如 "T1 coverage: rubric-only for anchor-curate/book-spine-init/escalation-review/memory-distill/score-arc/score-stratum/score-volume; scenario dirs pending"；不动结构字段；foreshadowing-recall 已不在任何节，无需移除）
- [ ] **Step 4: AGENTS.md:19 去数字化**——`72 functional + 2 meta = 74 total` 改为非数字表述（如 "functional + meta skills — see `skills/` and R1 lint output"）；`src/shenbi/contracts/ownership.py:7` 的「完整 69 技能」注释去数字化
- [ ] **Step 5: 验证**：`uv run python tools/lint_registry_reconcile.py 2>&1 | grep -E "seed|AGENTS"` 无 violations；`grep -n "72 functional\|完整 69" AGENTS.md src/shenbi/contracts/ownership.py` 无命中
- [ ] **Step 6: Commit** `git add tests/tiers/t2-phase AGENTS.md src/shenbi/contracts/ownership.py tests/tiers/deps.json && git commit -m "fix: t2 seed closure (F755/F758) + AGENTS.md de-numericize + F424 comment (spec60 T2.4/5c)"`

---

### Task 8: Data-3 — SHORT_MAP +11 + G5_CHECKER_GLOBS +9

**复杂度: leaf**（数据追加，gates 模块但纯条目）· **test_kind: regression_guard** · T1

**Files:**
- Modify: `src/shenbi/gates/cli.py:23-43`（SHORT_MAP）、`src/shenbi/gates/g5.py`（G5_CHECKER_GLOBS）

- [ ] **Step 1: SHORT_MAP 追加 11 条**（保持既有 alphabetical 风格插入）：

```python
    "book-spine-init": "shenbi-book-spine-init",
    "chapter-revision": "shenbi-chapter-revision",
    "escalation-review": "shenbi-escalation-review",
    "market-radar": "shenbi-market-radar",
    "memory-distill": "shenbi-memory-distill",
    "review-arc-payoff": "shenbi-review-arc-payoff",
    "review-resonance": "shenbi-review-resonance",
    "score-arc": "shenbi-score-arc",
    "score-stratum": "shenbi-score-stratum",
    "score-volume": "shenbi-score-volume",
    "short-drafting": "shenbi-short-drafting",
```

- [ ] **Step 2: G5_CHECKER_GLOBS 追加 9 条**（值对齐 SKILL 契约 writes + deps expected_outputs）：

```python
    "shenbi-book-spine-init": ["truth/book_spine.md"],
    "shenbi-chapter-revision": ["chapters/chapter-*.md", "chapters/chapter-*-revision-decisions.json", "truth/state_snapshot-pre-rev.md"],
    "shenbi-memory-distill": ["truth/arcs/arc-*.md", "truth/book_strata.md", "truth/book_spine.md"],
    "shenbi-review-arc-payoff": ["audits/volume-*-payoff.md"],
    "shenbi-review-resonance": ["audits/chapter-*-resonance.md"],
    "shenbi-score-arc": ["audits/arc-*-score.md"],
    "shenbi-score-stratum": ["audits/stratum-*-score.md"],
    "shenbi-score-volume": ["audits/volume-*-score.md"],
    "shenbi-short-drafting": ["chapters/chapter-*.md", "short/short-*-decisions.json"],
```

- [ ] **Step 3: 验证**：`uv run python tools/lint_registry_reconcile.py 2>&1 | grep -E "SHORT_MAP|globs"` 无 violations（checker-less 24 的 WARN 允许）；`uv run pytest tests/ -k "g5 or cli" -q` 全绿；**glob 包含断言**（R5 lint 面新增，plan 审查轮 1 C2 + 轮 2 定案）：静态规则 = 「同 t2-phase 任意两 checker-having 技能的 glob pattern，若 A 的匹配域**严格包含** B 的匹配域（A≠B 字符串、fnmatch 域 ⊃）→ FAIL」——**相等 pattern 不触发**（drafting 四 checker 共享 `chapters/*.md` 是合法现状）、**contained 侧为无通配 literal 的对不触发**（plan 轮 3 C1：genesis 的 `world/*.md ⊃ world/power_system.md` 等存量嵌套全部是 literal-contained，属合法「宽 checker 收窄产物集」现状；F432 载体 `audits/volume-*.md ⊃ audits/volume-*-score.md` 是 wildcard-vs-wildcard，保留触发）、不相交不触发。域包含检测：对相位 expected_outputs 模式展开的文件名集，`S(A) ⊇ S(B) ∧ S(A) ≠ S(B)`（仅比较双方均含通配符的 pattern 对）；第二防线 = `tests/fixtures/calibration/{arc-payoff,resonance}` 真实 fixture 驱动断言（arc-payoff checker 对 score-volume 产物零命中、反之亦然）
- [ ] **Step 4: Commit** `git add src/shenbi/gates/cli.py src/shenbi/gates/g5.py && git commit -m "fix: SHORT_MAP +11 checker shorthands (F414/F445) + G5_CHECKER_GLOBS +9 checker-having (F432, spec60 T2.5)"`

---

### Task 9: Data-4 — registry backfill 5b（G4_CHECKER_SKILLS +9 / index.md +5 / 触发表 +7）

**复杂度: leaf**（using-shenbi 改动需过两个 C21 lint）· **test_kind: regression_guard** · T1

**Files:**
- Modify: `src/shenbi/gates/shared.py:409-431`、`docs/skills/index.md`、`skills/using-shenbi/SKILL.md`

- [ ] **Step 1: G4_CHECKER_SKILLS 补 9**：book-spine-init、chapter-revision、escalation-review、market-radar、memory-distill、score-arc、score-stratum、score-volume、short-drafting（保持集合字面量既有排序风格）
- [ ] **Step 2: docs/skills/index.md 补 5 行**：foreshadowing-lifecycle、review-group-{character,craft,factual,plan}（行格式照既有条目——读文件头注释与列结构后照写）
- [ ] **Step 3: using-shenbi 触发表补 7 行**：anchor-curate、book-spine-init、escalation-review、memory-distill、score-arc、score-stratum、score-volume——**裁决（定案）**：score-×3 为 pipeline-internal（豁免，不补行），其余 4 个补行——触发表行文照 C21 后继改写口径，description-only when-to-use 风格；豁免经挂载命令的 `--allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume` 传递（Task 15 两处挂载行同 flag，验收 1 命令同 flag——单一豁免清单信源即挂载命令行）
- [ ] **Step 4: 验证**：`uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume 2>&1 | grep -E "G4_CHECKER|index.md|using-shenbi"` 无 violations（豁免口径同挂载——否则 score-×3 的触发表面违例会假红，plan 轮 3 I4）；`uv run python tools/lint_routing_faces.py && uv run python tools/audit-skill-descriptions.py`（C21 两 lint 全绿——新触发表行不得引 DEPRECATED/ghost）
- [ ] **Step 5: Commit** `git add src/shenbi/gates/shared.py docs/skills/index.md skills/using-shenbi/SKILL.md && git commit -m "fix: registry backfill — G4_CHECKER_SKILLS +9, index.md +5, trigger table +4 (score-* exempted, spec60 T2.5b)"`

---

### Task 10: Data-5 — truth-files.yaml 词表修正

**复杂度: leaf** · **test_kind: regression_guard** · T1

**Files:**
- Modify: `docs/framework/truth-files.yaml`
- Modify（生成物，经 `just generate` 不手改）：`docs/framework/truth-files.index.json` 等同步产物

- [ ] **Step 1: patterns 节补 2 条参数化映射**：

```yaml
patterns:
  # ...既有条目后追加...
  - parametric: context/review-checklist-N.json
    glob: context/review-checklist-*.json
  - parametric: context/chapter-pattern-input-N.json
    glob: context/chapter-pattern-input-*.json
```

（patterns 节实际 schema 以 yaml 既有条目字段名为准——先读现文件再对齐。）

- [ ] **Step 2: pipeline-written 节补 3 条 + 概念补 2 条 + 删 3 孤儿**——补 `progress.json`、`config-change-log.jsonl`、`gate-markers/*`（producer: pipeline）、`truth/bridge_tracker.md`、`truth/state_snapshot-pre-rev.md`；删 `short/outline.md`、`short/package.md`、`import/analysis/01_overview.md` 三行
- [ ] **Step 3: 同步生成物**：`uv run shenbi-sync-contracts` 后 `git status --porcelain -- tests/tiers/deps.json docs/framework/ skills/`（yaml 变更传播到生成物属正常——检查变更内容只含预期条目后随 commit；`git diff --exit-code` 在此处必 1，勿用作门）
- [ ] **Step 4: 验证**：`uv run python tools/lint_registry_reconcile.py 2>&1 | grep R2` 无 violations（孤儿概念 F888/F823 随删除消失；F1106/F1152 随补登消失）
- [ ] **Step 5: Commit** `git add docs/framework/truth-files.yaml docs/framework/ tests/tiers/deps.json && git commit -m "fix: word-list closure — 2 parametric patterns, pipeline-written trio, bridge_tracker/state_snapshot-pre-rev; drop 3 orphans (F242/F895/F1106/F1152/F888/F823, spec60 T2.6)"`

---

### Task 11: Data-6 — F1151 模板改名 + T206 worldbuilding 裁决 + F521 OWNERSHIP 死条目

**复杂度: leaf** · **test_kind: regression_guard** · T1

**Files:**
- Rename: `truth/` → `_templates/truth/`（根级模板目录；`truth/character_matrix.md` 零消费者径直删除不迁移）
- Modify: `tests/unit/pipeline/test_bridge_tracker.py:10,19`（template_path 改指 `_templates/truth/`）
- Modify: `src/shenbi/contracts/skills/worldbuilding.py:1`（T206 裁决：**删 "Auto-generated" 声称改手工维护注明**——补真实生成器超 spec 范围，保守裁决）
- Modify: `src/shenbi/contracts/ownership.py:78-80`（删 foundation-review ↔ genre-config.json 死条目）

- [ ] **Step 1: 改名 + 消费者**：`git rm truth/character_matrix.md && git mv truth _templates/truth`（先删零消费者文件再改名）；test_bridge_tracker.py 两处 `template_path` 字面量 `truth/...` 改 `_templates/truth/...`
- [ ] **Step 2: T206**——worldbuilding.py:1 docstring `"""Auto-generated minimal contract model..."""` 改 `"""Hand-maintained minimal contract model (generated provenance claim removed — no generator exists; spec60 T206)."""`
- [ ] **Step 3: F521**——ownership.py 删 OWNERSHIP 表中 foundation-review 的 genre-config.json 行（先 `grep -rn "genre-config" tests/fixtures/ | grep -i foundation` 确认无 fixture 行使该写键）
- [ ] **Step 4: 验证**：`uv run pytest tests/unit/pipeline/test_bridge_tracker.py tests/unit/gates/g4/test_state_settling.py -q` 全绿；`ls truth 2>/dev/null` 不存在；`uv run pytest tests/ -k "ownership or worldbuilding" -q` 绿
- [ ] **Step 5: Commit** `git add _templates/truth tests/unit/pipeline/test_bridge_tracker.py src/shenbi/contracts/skills/worldbuilding.py src/shenbi/contracts/ownership.py && git commit -m "fix: root truth/ template rename (F1151), worldbuilding provenance fix (T206), OWNERSHIP dead entry removal (F521, spec60 T2.7/8/10)"`

---

### Task 12: Data-7 — F354 genesis_outputs 补两文件

**复杂度: infra**（`src/shenbi/pipeline/cli.py`）· **test_kind: tdd_red_green** · T1

**Files:**
- Modify: `src/shenbi/pipeline/cli.py:777-793`（`_verify_truth_integrity` genesis_outputs 列表）
- Test: `tests/unit/pipeline/test_genesis_truth_integrity.py`（或并入既有 genesis 测试文件——grep 后定）

**Interfaces:**
- Produces: genesis_outputs 列表含 `world/factions.md`（genesis step-5，genesis.py:65）与 `foundation/review_report.md`（step-17，genesis.py:81）

- [ ] **Step 1: 失败测试**——构造含全部 genesis 产物（含两新文件）的 tmp 项目 → `_verify_truth_integrity` PASS；缺两文件 → 报缺（注意轮 3 M9 提示：验证 foundation 在长篇排序中晚于 genesis 的相位序，若 review_report 属后期产物则只补 genesis 时点已产出者——**写测试前先读 genesis.py 的 STEPS 序确认两文件确在 genesis 相位产出**）
- [ ] **Step 2: 确认失败 → Step 3: 列表补两项 → Step 4: 测试过 + `uv run pytest tests/ -k genesis -q` 全绿**
- [ ] **Step 5: Commit** `git add src/shenbi/pipeline/cli.py tests/unit/pipeline/test_genesis_truth_integrity.py && git commit -m "fix: genesis_outputs truth-integrity completeness (F354, spec60 batch)"`

---

### Task 13: R4 — 迁移器删除（F1022 + T207）

**复杂度: leaf** · **test_kind: regression_guard** · T1

**Files:**
- Delete: `tools/migrate_contract_to_frontmatter.py`、`tests/unit/test_migrate_contract.py`

- [ ] **Step 1: 删除前终核**：`grep -rn "migrate_contract_to_frontmatter\|CLASSIFICATION" --include="*.py" --include="*.yml" --include="justfile" . 2>/dev/null | grep -v ".venv\|docs/superpowers"` → 仅剩两文件自身
- [ ] **Step 2: `git rm tools/migrate_contract_to_frontmatter.py tests/unit/test_migrate_contract.py`**
- [ ] **Step 3: 验证**：`uv run pytest tests/ -q --timeout=120 -m "not last" -k "not test_clean_repo_zero_violations"`（`last` 是 marker 非 `-k` 关键字——`-k "not last"` 会误杀名字含 last 的真实测试，plan 轮 4 I1） 收集无 ImportError（deselect 设计性红的 clean-repo 测试，plan 轮 3 M1；不用 `-x` 以免它中途 abort）；`uv run python tools/lint_repo_consistency.py` exit 0
- [ ] **Step 4: Commit** `git commit -m "chore: remove one-shot contract migrator + third snapshot + its test (F1022/T207 delete-first, spec60 R4)"`

---

### Task 14: 终态 — _tool_hashes 重锁 + lint 全绿 + 验收 1 红灯五样本

**复杂度: infra** · **test_kind: regression_guard** · T1

**Files:**
- Modify: `tests/tiers/deps.json`（`_tool_hashes` 重锁，经 `tests/lock-tool-hashes.sh`——先 `cat` 该脚本确认调用方式）
- Test: `tests/unit/test_lint_registry_reconcile.py`（五负样本最终态）

- [ ] **Step 1: 重锁**：`bash tests/lock-tool-hashes.sh`（脚本直调 `python3`——它是 **writer**，writer 用系统 python 可接受，verifier 一律 `uv run`；脚本同时重锁 `_calibration_hashes`，diff 会含两块）→ `git diff tests/tiers/deps.json | head -60` 核对只有哈希行变化
- [ ] **Step 2: 全绿验证**：`uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume; echo "exit=$?"` → **exit 0 且 `0 violations`**（spec 验收 1 前半，豁免口径同挂载命令）——输出全文粘贴 progress.md
- [ ] **Step 3: 红灯五样本**（spec 验收 1 后半；临时副本变异，Task 4/5 测试已覆盖五个负样本——此处实跑确认）：`uv run pytest tests/unit/test_lint_registry_reconcile.py -v` 全 PASS（每个负样本断言 FAIL）
- [ ] **Step 4: 中期回归**：`uv run pytest -n auto -m "not last" -q --timeout=120`（全量；哈希重锁后应全绿）
- [ ] **Step 5: Commit** `git add tests/tiers/deps.json && git commit -m "chore: terminal _tool_hashes relock + lint green (spec60 acceptance 1/2)"`

---

### Task 15: T3 — CI 双挂载

**复杂度: infra** · **test_kind: regression_guard** · T1

**Files:**
- Modify: `justfile`（check recipe 追加一行 `uv run python tools/lint_registry_reconcile.py`）
- Modify: `.github/workflows/ci.yml`（lint step :55-59 区追加同一行——与 lint_contracts 并列）

- [ ] **Step 1: justfile check recipe 末尾（或 lint 块内）追加**：`uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume`
- [ ] **Step 2: ci.yml 的 lint step**（:55-59 `uv run python tools/lint_contracts.py ...` 块）追加同一行（**含同一 `--allow-missing` flag**）；块尾加注释 `# NOTE: dual-list with justfile is C25 debt (spec #63) — systematic single-sourcing deferred`
- [ ] **Step 3: 验证**：`just --dry-run check | grep registry_reconcile`（命中）；`grep -n registry_reconcile .github/workflows/ci.yml`（命中）；`uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume` exit 0（与验收 1 同口径）
- [ ] **Step 4: Commit** `git add justfile .github/workflows/ci.yml && git commit -m "ci: dual-mount lint_registry_reconcile (justfile check + ci.yml lint step, C25 debt noted, spec60 T3)"`

---

## Self-Review 记录

- **Spec 覆盖**：spec 任务 0a→T1/T2，0b→T3，1→T4/T5，3→T6，4→T7，5→T8，5b→T9，5c→T7，6→T10，7/8/10→T11，9→T2，11(T203)→T3 Step 4，12→T15，批量清理 F354→T12、F424→T7、T1306→T6 版本面；R4→T13；验收 1→T14、2→T6/T14、3→T3、4→T7、5→T15。29 成员全覆盖（F231/F905/F756-数据/F759-注册半/F1152-读者半/F424-主体 已闭合于前轮，spec 已标注）。
- **占位符扫描**：Task 2 Step 3 的 checkers 字典「照搬」与 Task 4 的 sys.path 注入细节是「指向源文件的机械移动/既有模式复制」指令（内容在源文件，非凭空 TBD）；其余步骤均有完整代码/精确条目。
- **类型一致性**：`lint_registry_reconcile(repo: Path, allow_missing: frozenset[str]) -> list[str]` 全 plan 一致；`G4_DECISIONS_WIRED/G4_CHECKER_KEYS/build_checkers` 在 Task 2 定义、Task 3/4 消费；`G5_CHECKER_GLOBS` Task 1 产出、Task 3/8 消费。
