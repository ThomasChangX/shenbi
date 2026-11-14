# Spec #89 门禁内部性修复（gates-internal-repair）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 spec r2.6 执行门禁内部性修复——CheckContext 一次装载、四窄助手、章号单源、shared.py 出鞘、调用缝说真话、G0.12 真实现。

**Architecture:** 全部 task 为 **infra**（触及 `src/shenbi/gates/g4/`、`gates/shared.py`、`paths.py`），由协调者亲自实现（单模型现实）。判定语义不变——每个 task 先落 characterization/红测再改写。施工序（spec §3 r2.4）：**Task1(T3 助手)→Task2(T2 章号)→Task3(T1 大拆分)→Task4(T4 出鞘)→Task5(T5 正名)→Task6(T6 G0.12)**。

**Tech Stack:** Python 3.11+，pathlib，dataclass，functools.lru_cache，ast（lint 工具），pytest（unit 标记），justfile。

## Global Constraints

- **禁真实 LLM dispatch**（F947）：一切验收用 tests/fixtures/ 真实产物或 tmp_path 构造结构输入（G0.9 结构性输入豁免）驱动测试表达。
- 判定语义不变：所有 WARN/mf/id 文本逐字保持（degrade 五发射点逐字快照钉死）；`ValueError("round_dir or project_dir required for G4 RoundPaths checkers")` 串不得改（test_g4_signatures.py:42 钉串）。
- gate 检查器纯函数幂等；`src/shenbi/` 无 print；structlog 日志；conventional commits；每 task commit 后产 `.superpowers/sdd/audit-T<N>.md`。
- 状态字面量唯一源 `contracts/enums.py`（G0.12 用既有 `GateStatus` 枚举）。
- commit 一律 pathspec 显式列文件，禁 `git add -A`。

## 验收覆盖表（spec AC → task → 验证命令）

| AC | Task | 验证 |
|---|---|---|
| AC1 主函数<300 行+plan 恰读 1 次 | T3 | `uv run python -c "import ast..."` 行数断言 + `uv run pytest tests/gates/g4/test_chapter_drafting_read_count.py -q` |
| AC2 章号归零 | T2 | `uv run python tools/lint_chapter_num_single_source.py` exit 0 + `just check` |
| AC3 RoundPaths 同串 11→1 | T1 | `grep -rln "round_dir or project_dir required" src/shenbi/gates/g4/` 输出空（raise 唯一源在 paths.py；g4 域零同串）+ `uv run pytest tests/unit/gates/test_g4_signatures.py -q` 绿 |
| AC4 shared 无写函数/无 import 扫描/text 2 符号/7 破裂面 | T4 | `uv run pytest tests/unit/gates/test_shared_import_side_effects.py -q` + `grep -n "def write_gate_marker" src/shenbi/gates/shared.py` 空 + `just check`（lint_key_reconciliation --strict 含内） |
| AC5 skill_utils segment_sentences import 归零 | T4 | `grep -n "segment_sentences" src/shenbi/skill_utils/style_learning/compute_stats.py` → import 行指向 text.cjk |
| AC6 G0.12 注入红 | T6 | `uv run pytest tests/unit/gates/test_g0_checker_coverage.py -q`（红测用例） |
| AC7 just check exit 0 | 全部 | `just check` |
| AC8 零 reportPrivateUsage+gates.md 段 | T5 | `grep -c "reportPrivateUsage" src/shenbi/gates/g4/chapter_drafting.py` =0 + `grep -n "g4_cross_chapter" docs/framework/gates.md` 命中 |

---

### Task 1: 四窄助手（spec T3）

**复杂度: infra** ｜ **test_kind: characterization + tdd_red_green**

**Files:**
- Modify: `src/shenbi/gates/shared.py`（CHAPTER_NUM_RE:183 邻近加 chapter_no；新增 load_facts_oracle、degrade）
- Modify: `src/shenbi/paths.py:55`（RoundPaths 加 require_roots 类方法）
- Modify: 11 个 checker 的前导（pacing_design/foreshadowing_lifecycle/faction_builder/story_architecture/location_builder/relationship_map/worldbuilding/plot_thread_weaver/power_system/volume_outlining/character_design）
- Test: `tests/unit/gates/test_narrow_helpers.py`（新建）
- Test: `tests/unit/gates/g4/test_round_paths_require_roots.py`（新建）

**Interfaces:**
- Produces（后续 task 依赖的精确签名）:
  - `def chapter_no(name_or_path: str | Path) -> int | None`（shared.py；`CHAPTER_NUM_RE.search(str(name_or_path))`，命中返回 `int(m.group(1))` 否则 None）
  - `def load_facts_oracle(project_dir: str | Path, dim: FactsDim) -> FactsFile | None`（shared.py；`load_facts(Path(project_dir), dim)` 返回值非 None 且非空时返回该 FactsFile，否则 None；`from shenbi.facts.store import load_facts` 与 `from shenbi.facts.enums import FactsDim` 模块级引入——facts 是零依赖叶，无环）
  - `def degrade(kind: str, cause: str, what_skipped: str, *, tail: str = "", visible: bool = True) -> str`（shared.py；返回 `f"{kind} — {cause}; {what_skipped}{tail}"`，`visible=True` 时追加 `" (degradation visible)"`）
  - `@classmethod def require_roots(cls, rd: str | None, project_dir: str | None, repo_root: str | Path) -> RoundPaths`（paths.py；两者皆 None 时 `raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")`；否则构造 `cls(round_dir=Path(str(rd or project_dir)), project_dir=Path(str(project_dir or rd)), repo_root=Path(repo_root))`）

- [ ] **Step 1: characterization 红测（先钉现状）**

`tests/unit/gates/test_narrow_helpers.py`：

```python
"""Spec #89 T3 narrow helpers: byte-exact degradation strings + oracle triples."""

from __future__ import annotations

import pytest

from shenbi.gates.shared import (
    CHAPTER_NUM_RE,
    chapter_no,
    degrade,
    load_facts_oracle,
)


@pytest.mark.unit
def test_degrade_emission_strings_byte_exact() -> None:
    # 五发射点逐字快照（cd:668/:695/:740、cp:735、xc:964 + cd:706 no_decl 变体）
    assert (
        degrade("no_facts", "props facts absent/empty", "hand-off scan skipped")
        == "no_facts — props facts absent/empty; hand-off scan skipped (degradation visible)"
    )
    assert (
        degrade("no_facts", "counters facts absent/empty", "reconciliation skipped")
        == "no_facts — counters facts absent/empty; reconciliation skipped (degradation visible)"
    )
    assert (
        degrade("no_facts", "props facts absent/empty", "F16 cp legality skipped")
        == "no_facts — props facts absent/empty; F16 cp legality skipped (degradation visible)"
    )
    assert (
        degrade("no_ledger", "particle_ledger.md absent", "balance anchor skipped")
        == "no_ledger — particle_ledger.md absent; balance anchor skipped (degradation visible)"
    )
    assert (
        degrade("no_facts", "identity facts absent/empty", "F15 narration scan skipped")
        == "no_facts — identity facts absent/empty; F15 narration scan skipped (degradation visible)"
    )
    assert (
        degrade(
            "no_decl",
            "memo declares no counters this chapter",
            "reconciliation not activated",
            visible=False,
            tail=" (legacy-memo compat, ch17-class false-red guard)",
        )
        == "no_decl — memo declares no counters this chapter; reconciliation not activated (legacy-memo compat, ch17-class false-red guard)"
    )


@pytest.mark.unit
def test_chapter_no_search_semantics() -> None:
    assert chapter_no("chapter-42.md") == 42
    assert chapter_no("rounds/r1/chapter-7-plan.md") == 7
    assert chapter_no("outline.md") is None
    assert CHAPTER_NUM_RE.search("chapter-3").group(1) == "3"


@pytest.mark.unit
def test_load_facts_oracle_empty_equals_absent(tmp_path) -> None:
    from shenbi.facts.enums import FactsDim

    # 缺席 → None（三连语义：None 或空都折叠为 None）
    assert load_facts_oracle(tmp_path, FactsDim.PROPS) is None
```

`tests/unit/gates/g4/test_round_paths_require_roots.py`：

```python
"""Spec #89 T3: RoundPaths.require_roots collapses the 11-checker preamble."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.paths import RoundPaths


@pytest.mark.unit
def test_require_roots_raises_the_pinned_string() -> None:
    with pytest.raises(ValueError, match="round_dir or project_dir required"):
        RoundPaths.require_roots(None, None, Path("."))


@pytest.mark.unit
def test_require_roots_mutual_defaults() -> None:
    rp = RoundPaths.require_roots("/tmp/rd", None, "/repo")
    assert rp.round_dir == Path("/tmp/rd") and rp.project_dir == Path("/tmp/rd")
    rp2 = RoundPaths.require_roots(None, "/proj", "/repo")
    assert rp2.project_dir == Path("/proj") and rp2.round_dir == Path("/proj")
```

- [ ] **Step 2: 跑红测** — `uv run pytest tests/unit/gates/test_narrow_helpers.py tests/unit/gates/g4/test_round_paths_require_roots.py -q` → 预期 FAIL（ImportError: chapter_no/degrade/load_facts_oracle/require_roots 不存在）

- [ ] **Step 3: 实现 shared.py 三助手**（放 CHAPTER_NUM_RE:183 紧后；模块头部 import 区加 `from shenbi.facts.enums import FactsDim`、`from shenbi.facts.schemas import FactsFile`、`from shenbi.facts.store import load_facts`——先 grep 确认 facts 模块不 import gates：`grep -rn "shenbi.gates" src/shenbi/facts/` 应为空）

- [ ] **Step 4: 实现 paths.py require_roots 类方法**（RoundPaths dataclass 内，`read` 方法前）

- [ ] **Step 5: 跑绿** — 两测试文件全 PASS

- [ ] **Step 6: 11 checker 前导收敛**

每文件把（以 pacing_design.py:36-42 为同构样板）：

```python
    if rd is None and project_dir is None:
        raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
    rp = RoundPaths(  # spec #48 C34: explicit roots, no silent fallthrough
        round_dir=Path(str(rd or project_dir)),
        project_dir=Path(str(project_dir or rd)),
        repo_root=Path(repo_root or PROJECT),
    )
```

替换为：

```python
    rp = RoundPaths.require_roots(rd, project_dir, repo_root or PROJECT)  # spec #48 C34
```

**pacing_design.py 例外**：启发式（:33-34 `if not project_dir: project_dir = rd or (str(Path(fps[0]).parent.parent) if fps else None)`）**保留在调用之前**（先解析、后 require_roots——spec r2.4 调用序）。各文件 `PROJECT` import 保留（require_roots 第三参仍用）。`Path` import 若变孤儿随删（ruff F401 会抓）。

- [ ] **Step 7: 三处事实/降级发射点换源**（本 task 只做助手消费侧的机械换源；degrade 字面量换 `degrade(...)` 调用**全域 6 处**（cd ×4 含 :706 no_decl 变体 + cp:735 + xc:964）、cd:611-626/cp:723-726/xc:947-976 的三连换 `load_facts_oracle`——**注意 cd 三处三连后各接衍生构造（props()/counters()/identity() 投影），换源只换「load+判空」两行，投影行保持原位**；`_loaded = load_facts_oracle(project_dir, FactsDim.PROPS); if _loaded is not None:` 形态）

- [ ] **Step 8: 回归** — `uv run pytest tests/unit/gates/ tests/gates/g4/ -q` 全绿 + `uv run pytest tests/unit/gates/test_g4_signatures.py -q`（钉串测试）绿

- [ ] **Step 9: Commit** — pathspec 逐文件（g4 域逐个列，禁通配）：

```bash
git add src/shenbi/gates/shared.py src/shenbi/paths.py \
  src/shenbi/gates/g4/chapter_drafting.py src/shenbi/gates/g4/chapter_planning.py \
  src/shenbi/gates/g4/cross_chapter.py src/shenbi/gates/g4/pacing_design.py \
  src/shenbi/gates/g4/foreshadowing_lifecycle.py src/shenbi/gates/g4/faction_builder.py \
  src/shenbi/gates/g4/story_architecture.py src/shenbi/gates/g4/location_builder.py \
  src/shenbi/gates/g4/relationship_map.py src/shenbi/gates/g4/worldbuilding.py \
  src/shenbi/gates/g4/plot_thread_weaver.py src/shenbi/gates/g4/power_system.py \
  src/shenbi/gates/g4/volume_outlining.py src/shenbi/gates/g4/character_design.py \
  tests/unit/gates/test_narrow_helpers.py tests/unit/gates/g4/test_round_paths_require_roots.py
git commit -m "feat: spec #89 T3 四窄助手——chapter_no/load_facts_oracle/degrade 落地+RoundPaths.require_roots 11 前导收敛"
```

---

### Task 2: 章号单源（spec T2）

**复杂度: infra** ｜ **test_kind: tdd_red_green（lint 先红）**

**Files:**
- Create: `tools/lint_chapter_num_single_source.py`
- Create: `tests/unit/tools/test_lint_chapter_num_single_source.py`
- Modify: `justfile`（lint 接线，lint_mustfix_emission 行后）
- Modify: 20 处内联（chapter_drafting ×6 :547/:655/:918/:1053/:1190/:1207、cross_chapter ×5 :118/:730/:760/:873/:996、generic ×2 :250/:314、chapter_planning :653、decisions_validator :65、g6 :87/:421/:431、g6_checks :42/:127）+ 2 后缀锚（decisions_validator:65、chapter_planning:889）

**Interfaces:**
- Consumes: Task 1 的 `chapter_no()`。
- Produces: `tools/lint_chapter_num_single_source.py`（exit 0=绿 / 1=红+清单）；justfile `lint` 面。

- [ ] **Step 1: 写 lint 工具（先跑先红——当前 20 处必报）**

```python
#!/usr/bin/env python3
"""Spec #89 T2: gates/ 域 chapter-(\\d+) 内联正则归零 lint（AST 判据）.

唯一允许的定义点：src/shenbi/gates/shared.py 的 CHAPTER_NUM_RE（定义
Assign 节点放行——含其 docstring/注释；其余任何 re.* 调用携带该字面量即红）。
对齐 #85 lint_truth_format_single_source / #88 lint_mustfix_emission 惯例。
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATES = REPO / "src" / "shenbi" / "gates"
ALLOWED_FILE = "shared.py"
PATTERN = "chapter-(\\d+)"
RE_FUNCS = ("compile", "search", "match", "fullmatch", "findall", "sub")


def _is_definition(node: ast.Call) -> bool:
    """CHAPTER_NUM_RE = re.compile(...) 形态（shared.py 唯一合法点）。"""
    return isinstance(node.func, ast.Attribute) and node.func.attr == "compile"


def lint_tree(
    tree: ast.AST, rel: str, hits: list[tuple[str, int]], *, allow_definition: bool
) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in RE_FUNCS:
            continue
        if not (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            continue
        if PATTERN not in node.args[0].value:
            continue
        if allow_definition and _is_definition(node):
            continue
        hits.append((rel, node.lineno))


def main() -> int:
    hits: list[tuple[str, int]] = []
    for py in sorted(GATES.rglob("*.py")):
        rel = str(py.relative_to(REPO))
        tree = ast.parse(py.read_text(encoding="utf-8"))
        lint_tree(tree, rel, hits, allow_definition=py.name == ALLOWED_FILE)
    if hits:
        print(
            f"lint_chapter_num_single_source: {len(hits)} inline chapter-(\\d+) site(s) outside {ALLOWED_FILE} definition:"
        )
        for rel, ln in hits:
            print(f"  {rel}:{ln}")
        print("Replace with chapter_no() from shenbi.gates.shared (spec #89 T2).")
        raise SystemExit(1)
    print("OK: gates/ chapter-number regex is single-sourced (spec #89 T2)")
    return 0


if __name__ == "__main__":
    main()
```

（红清单首跑输出存 `.superpowers/sdd/chapter-num-redlist.txt` 作对账基线——对齐 #88 T2 先例；f-string JoinedStr 形态天然不命中 Constant 分支——精确等值口径见 spec T2。）

- [ ] **Step 2: 首跑红** — `uv run python tools/lint_chapter_num_single_source.py` → 预期 exit 1，清单=20 处（与 spec 清单 diff 对账；不齐=spec 锚失效，停下记 deviation）

- [ ] **Step 3: 写 lint 单测**

`tests/unit/tools/test_lint_chapter_num_single_source.py`：三用例——干净源（tmp 写 `re.search(r"chapter-(\d+)", x)` → 1 hit）；合法形态（`CHAPTER_NUM_RE` 引用零 hit；f-string `f"chapter-{n}-decisions.json"` JoinedStr 零 hit）；shared.py 定义放行。

- [ ] **Step 4: 20 处换源** — `m = re.search(r"chapter-(\d+)", pf.name)` → `n = chapter_no(pf.name)`（各站点的 `int(m.group(1)) if m else None` 折叠进 chapter_no；变量名随站点保持）。两后缀锚：
  - decisions_validator.py:65: `m = re.search(r"chapter-(\d+)-decisions\.json", filepath)` → `n = chapter_no(filepath)` + 判定 `n is not None and f"chapter-{n}-decisions.json" in filepath`（f-string 包含式，r2.5）
  - chapter_planning.py:889: `ch_num = re.search(r"-(\d+)-plan", str(fp))` → `n = chapter_no(fp)` + `n is not None and f"-{n}-plan" in str(fp)`
  - **chapter_planning.py:654 局部变量 `chapter_no` shadow（驳斥 G8）**：改局部变量名为 `_ch_num`
  - import：各文件加 `from shenbi.gates.shared import chapter_no`（g6/g6_checks 域同样自 gates.shared 引）

- [ ] **Step 5: lint 绿** — `uv run python tools/lint_chapter_num_single_source.py` → exit 0

- [ ] **Step 6: justfile 接线** — `just check` 的 lint 链在 lint_mustfix_emission 行后加 `uv run python tools/lint_chapter_num_single_source.py`（对齐 #88 T2 justfile:36 接线形态）

- [ ] **Step 7: 回归** — `uv run pytest tests/unit/gates/ tests/gates/g4/ tests/unit/tools/ -q` 全绿

- [ ] **Step 8: Commit** — pathspec 逐文件：

```bash
git add tools/lint_chapter_num_single_source.py tests/unit/tools/test_lint_chapter_num_single_source.py \
  justfile src/shenbi/gates/shared.py src/shenbi/gates/g4/chapter_drafting.py \
  src/shenbi/gates/g4/cross_chapter.py src/shenbi/gates/g4/generic.py \
  src/shenbi/gates/g4/chapter_planning.py src/shenbi/gates/g4/decisions_validator.py \
  src/shenbi/gates/g6.py src/shenbi/gates/g6_checks.py
git commit -m "feat: spec #89 T2 章号单源——20 内联归零+chapter_no 采纳+AST lint 接线"
```

---

### Task 3: CheckContext 一次装载 + 主函数拆分（spec T1）

**复杂度: infra（本批最大风险 task）** ｜ **test_kind: characterization（既有 cd 测试族全绿不动）+ tdd_red_green（read 计数）**

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（主函数 :584-1379 拆分；`_spec82_hook_rotation` :540-570 一带传参化）
- Test: `tests/gates/g4/test_chapter_drafting_read_count.py`（新建）

**Interfaces:**
- Consumes: Task 1 的 `load_facts_oracle`/`chapter_no`、Task 2 已换常量后的站点。
- Produces: `@dataclass class CheckContext`（同文件；模板=cross_chapter.py:37-50 CrossChapterContext）+ **25 个具名检查函数**（`_check_<slug>(ctx, c, mf)` 形态；23 个 `id:` 行 + 2 个 mf 直发块）。

**CheckContext 字段（真实类型+来源行——循环顶一次性装载，计算顺序保持现相对序）**：

```python
@dataclass
class CheckContext:
    """Per-chapter inputs assembled once at loop top (spec #89 T1).

    Facts oracles are project-level (loaded once before the loop, threaded in);
    everything else is per-file. The project_dir-base plan/memo is read exactly
    once here — the four scattered memo re-reads collapse into ctx.memo_text.
    The scene-hook rd-base plan lookup keeps its own resolution (F407 order)
    and is cached as ctx.scene_hook_plan_text (may be a DIFFERENT file when
    rd≠project_dir — plan review C1: bases must not be unified).
    """

    # per-file, loop top
    pf: Path  # resolved chapter path (resolve_input_path)
    content: str  # pf.read_text once (:650)
    chapter_no: int | None  # chapter_no(pf)
    memo_text: (
        str | None
    )  # project_dir/plans/chapter-N-plan.md ONCE（原 :659/:1060/:1194 + _spec82 :556 四读归一）
    scene_hook_plan_text: (
        str | None
    )  # rd-or-project_root 基 plan 一次（原 :918-924 独立解析基，逐字保持解析顺序）
    # content derivations（现首现行号——提升到循环顶时保持彼此相对序）
    wc: int  # word_count_md(str(pf))（:651）
    total_chars: int  # total_chars_md_text(content)（:885）
    project_root: Path  # next(...) F407 解析序（:844）
    paragraphs: list[str]  # :982 投影
    narrative: str  # strip_narrative_body(content)（:1128）
    pre_block: re.Match | None  # :1178 PRE_WRITE_CHECK 剖取
    post_block: str | None  # :1181 POST 剖取
    memo_v2: bool  # :1186-1198 v3⊇v2 探测（golden_slot 状态链输入）
    # project-level facts oracles（循环前一次，挂 ctx 传递）
    props_facts: dict[str, dict[str, str]] | None
    counters_facts: dict[str, dict[str, int]] | None
    known_names: set[str] | None
    owner_aliases: dict[str, set[str]]
    # roots
    project_dir: str | None
    rd: str | None
    repo_root: str | None
```

（字段装载次序——**依赖序非首现序**：`pf→content→wc→chapter_no→memo_text→project_root→scene_hook_plan_text→total_chars→paragraphs→narrative→pre/post_block→memo_v2`；project_root/total_chars 只依赖 pf/content/project_dir，提前装载无语义影响；**scene_hook_plan_text 的解析基在 rd=None 时依赖 project_root（:920-921）——必须排 project_root 之后**；任何「依赖前块判定结果」的派生一律留在检查函数内部不进 ctx。）

**拆分清单（25 块 → 具名函数；块体逐字搬运不改语义）**：

23 个 `id:` 行：pre_check→`_check_pre_block`、word_count→`_check_word_count`、transition→`_check_transitions`、meta→`_check_meta`、fatigue→`_check_fatigue`、counter→`_check_counters`、balance_value_drift→`_check_balance_drift`、surge→`_check_surge`、simile_band→`_check_simile_band`、protagonist_presence→`_check_protagonist`、golden_slot→`_check_golden_slot`、voice_density→`_check_voice_density`、scene_hook_match→`_check_scene_hook`、scene_count→`_check_scene_count`、scene_concreteness→`_check_scene_concreteness`、payoff_density→`_check_payoff_density`、content_uniqueness→`_check_content_uniqueness`、chapter_end_hook→`_check_chapter_end_hook`、prop_handoff→`_check_prop_handoff`、provenance_anchor→`_check_provenance`、post_wordcount_precision→`_check_post_wordcount`、post_quote_verbatim→`_check_post_quote_verbatim`、post_check→`_check_post_block`。

**2 个 mf 直发块（plan 审查 I4 补——无 `id:` dict 行、#88 finding() 形态 mf 发射）**：quote_verbatim（:1051-1076，`extract_anchor_quotes`/`quote_in_chapter` + mf `G4.cd.quote_verbatim:{fp}` :1069/:1074）→`_check_quote_verbatim`；micro_hook_run（:1204-1242，前章 plan 窗 + mf `G4.cd.micro_hook_run:{fp}:{_run78}>{_micro_cap}` :1240）→`_check_micro_hook_run`。

`G4.file_not_found`（循环顶 :647-649）留在主函数（控制流 continue，非检查块）。

**拆分边界（spec r2.3 驳斥 G1 + plan 审查 C1）**：跨章读三族保留在拆出函数内部（content_uniqueness 的 glob 他章、_spec82_hook_rotation 前窗、micro_hook_run/payoff 前章 plan 读）；golden_slot 状态链（:1316-1379）与 voice_density（:1270-1315）整块拆出（函数内保持局部状态链）；**`_check_scene_hook` 内保留 :918-924 的 rd-or-project_root 独立解析基并消费 `ctx.scene_hook_plan_text`（循环顶装载一次——双基不得归一，归一会在 pipeline 主路径激活/改检 scene_hook 语义）**。`_spec82_hook_rotation(content, pf.name, project_dir, mf, c)` 改签名加 `memo_text: str | None` 参数、函数体删除自身 :556 的 `mp.read_text`（ctx 已读一次）。

**spec 前提精化（记 spec-deviations ### T3）**：spec「plan 同文件每章重读 5 次」实为**四读 project_dir 基 memo + 一读 rd/project_root 基 plan**（两基在 rd=project_dir 时恰同文件）——AC1「恰 1 次」按 memo 面（project_dir 基）断言；scene_hook 基读保持独立（行为不变）。

- [ ] **Step 1: read-count 红测**

`tests/gates/g4/test_chapter_drafting_read_count.py`（抄 tests/gates/g4/test_content_uniqueness_cache.py:19-37 计数模式；输入=tmp_path 构造项目结构——章节文件+plans/chapter-N-plan.md（G0.9 结构性输入豁免））：

```python
"""Spec #89 T1 AC1: plan file is read exactly once per chapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4 import chapter_drafting as cd


@pytest.mark.unit
def test_plan_read_exactly_once_per_chapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = tmp_path / "proj"
    (proj / "chapters").mkdir(parents=True)
    (proj / "plans").mkdir(parents=True)
    (proj / "chapters" / "chapter-1.md").write_text("第一段正文。他说好了。\n", encoding="utf-8")
    plan = proj / "plans" / "chapter-1-plan.md"
    plan.write_text("- 本章目标：过闸\n- 章尾钩型：悬念\n", encoding="utf-8")

    reads = {"n": 0}
    real = Path.read_text
    target = str(plan)

    def counting(self: Path, *a: object, **k: object) -> str:
        if str(self) == target:
            reads["n"] += 1
        return real(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting)  # type: ignore[attr-defined]
    cd.g4_chapter_drafting([str(proj / "chapters" / "chapter-1.md")], project_dir=str(proj))
    assert reads["n"] == 1
```

（若构造输入触发现有检查的额外报错——只要不 raise 即可，本测只钉 read 计数。）首跑红：该 fixture（rd=None）下 memo 基读 **4** 次（:659/:1060/:1194+:556；:924 的 rd/project_root 基在 fixture 下解析到别处不命中）→ `reads["n"] == 4` ≠ 1 FAIL。

- [ ] **Step 2: 跑红** — `uv run pytest tests/gates/g4/test_chapter_drafting_read_count.py -q` → FAIL（计数 4≠1）

- [ ] **Step 3: characterization 基线** — `uv run pytest tests/unit/gates/g4/ tests/gates/g4/ tests/gates/test_invariant_mutants.py -q` 全绿记录（拆分后须逐字复绿；cd 族=tests/unit/gates/g4/{test_chapter_drafting,test_chapter_drafting_detect,test_f16_cd_handoffs,test_f17_counters,test_hook_type_rotation,test_plan_format_v4,test_quote_verbatim,test_scene_checks,test_spec76_voice_quote,test_spec83_counter_anchor,test_word_floor_citation,test_all_skills_parametrized,test_chapter_planning_craft_fields}.py + tests/gates/g4/{test_c15_chinese_week_label,test_hook_fulfillment,test_title_check}.py + **tests/gates/test_invariant_mutants.py**——cd 三符号[_ORDINAL_RE/check_counter_reconciliation/check_prop_handoffs]消费方）

- [ ] **Step 4: 循环顶构造 ctx + memo 四读归一**——memo 在循环顶读一次入 `ctx.memo_text`（project_dir 基）；:659/:1060/:1194 三处 read_text 删除改用 ctx.memo_text；`_spec82_hook_rotation` 加 memo_text 参数、删自身 :556 读。**scene_hook 的 rd-or-project_root 基（:918-924）独立装载一次入 `ctx.scene_hook_plan_text`（解析顺序逐字保持，不与 memo 归一——C1）**。content 派生（wc/project_root/total_chars/paragraphs/narrative/pre_block/post_block/memo_v2）按字段表次序在循环顶装载。facts oracle 三连保持在循环前（项目级一次），结果挂 ctx 字段。

- [ ] **Step 5: read-count 绿** — Step 1 测试 PASS（恰 1 读）

- [ ] **Step 6: 逐块拆出 25 具名函数**——每块「剪切块体 → 粘贴为 `_check_<slug>(ctx, c, mf)`（块内引用的循环局部变量改经 ctx 字段表；mf 直发 #88 形态保持逐字）→ 主函数原位换调用」。**每拆 3-5 块跑一次 characterization**（增量验证，任何红即停修复）。

- [ ] **Step 7: 行数验收** — `uv run python -c "import ast; src=open('src/shenbi/gates/g4/chapter_drafting.py').read(); t=ast.parse(src); n=[n for n in t.body if isinstance(n, ast.FunctionDef) and n.name=='g4_chapter_drafting'][0]; ln=n.end_lineno-n.lineno+1; print(ln); assert ln<300"` → 打印 <300 且断言过

- [ ] **Step 8: 全量 characterization 复绿** — Step 3 基线套件全绿

- [ ] **Step 9: Commit** — `git add src/shenbi/gates/g4/chapter_drafting.py tests/gates/g4/test_chapter_drafting_read_count.py && git commit -m "feat: spec #89 T1 CheckContext 一次装载——796→<300 行+plan 五读归一+23 检查块拆具名函数"`

---

### Task 4: shared.py 出鞘（spec T4）

**复杂度: infra** ｜ **test_kind: regression_guard + characterization**

**Files:**
- Modify: `src/shenbi/gates/gate_manifest.py`（接收 marker_filename+write_gate_marker，头部加 `from shenbi.safe_write import safe_write`）
- Modify: `src/shenbi/text/cjk.py`（接收 QUOTE_PAIR+segment_sentences）
- Modify: `src/shenbi/gates/shared.py`（删 write_gate_marker/marker_filename/segment_sentences/QUOTE_PAIR 原体；留 `from shenbi.text.cjk import QUOTE_PAIR, segment_sentences` 双 re-export；ALL_SKILLS/T1_SCAFFOLD_SKILLS 惰性化）
- Modify: 7 破裂面 + src 6 文件 + 随改点（下详）
- Test: `tests/unit/gates/test_shared_import_side_effects.py`（新建）

**Interfaces:**
- Produces: `from shenbi.gates.gate_manifest import marker_filename, write_gate_marker`（既有签名逐字不变：`marker_filename(gate: str, target: str, test_type: str) -> str`；`write_gate_marker(gate, target, test_type, result_str, round_dir, file_paths=None) -> None`）；`from shenbi.text.cjk import QUOTE_PAIR, segment_sentences`；`all_skills() -> list[str]` / `t1_scaffold_skills() -> tuple[str, ...]`（lru_cache 惰性函数，**小写命名**——常量转函数后 UPPER 违 ruff N802 惯例；shared 不留旧名）。

- [ ] **Step 1: import 副作用红测**

`tests/unit/gates/test_shared_import_side_effects.py`：

```python
"""Spec #89 T4 AC4: importing gates.shared performs zero FS scans and holds no writers."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import shenbi.gates.shared as shared


@pytest.mark.unit
def test_import_shared_performs_no_iterdir(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    real = Path.iterdir

    def spy(self: Path) -> object:
        calls.append(str(self))
        return real(self)

    monkeypatch.setattr(Path, "iterdir", spy)
    importlib.reload(shared)
    assert calls == [], f"import-time FS scan detected: {calls}"
    importlib.reload(shared)  # restore original module state


@pytest.mark.unit
def test_shared_has_no_write_functions() -> None:
    import inspect

    for name, member in vars(shared).items():
        if inspect.isfunction(member) and member.__module__ == "shenbi.gates.shared":
            src = inspect.getsource(member)
            assert ".write_text(" not in src and "safe_write(" not in src, f"{name} writes"
```

首跑红：iterdir spy 捕获 ALL_SKILLS/T1_SCAFFOLD_SKILLS 两处；write 检查抓 write_gate_marker。

- [ ] **Step 2: 惰性化 roster**（shared.py:778-795）

```python
@lru_cache(maxsize=1)
def all_skills() -> list[str]:
    """Known skill names from skills/ (lazy: no import-time FS scan, spec #89 T4).

    Missing directory degrades to [] exactly like the old module-level scan.
    """
    return (
        sorted(d.name for d in SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
        if SKILLS.exists()
        else []
    )


@lru_cache(maxsize=1)
def t1_scaffold_skills() -> tuple[str, ...]:
    """T1-skill scaffold roster (F432) — lazy, degrades to () when dir absent."""
    return tuple(
        sorted(
            d.name
            for d in (TESTS / "tiers" / "t1-skill").iterdir()
            if d.is_dir() and d.name != "_template"
        )
        if (TESTS / "tiers" / "t1-skill").exists()
        else ()
    )
```

- [ ] **Step 3: 换源 7 破裂面 + src 6 文件 + 随改点**（机械表）：

| 面 | 现形态 | 改为 |
|---|---|---|
| g0.py:111 import + :413/:606/:715/:720-721 | `ALL_SKILLS` | `all_skills()`（import 行同步；Task 6 会再改 G0.12 块——本 task 只换调用形态） |
| g7.py:45/:65 | `set(ALL_SKILLS) \| set(T1_SCAFFOLD_SKILLS)` / `set(T1_SCAFFOLD_SKILLS) - report_skills` | `set(all_skills()) \| set(t1_scaffold_skills())` / `set(t1_scaffold_skills()) - report_skills` |
| g_reconcile.py:76 / sync_contracts.py:38 / dispatch_helper.py:3082-3085 | 同上形态 | `all_skills()` |
| g_dispatch.py:48 | `all_skills = set(ALL_SKILLS)`（**函数内局部变量与函数名同名——机械改写会 UnboundLocalError，局部变量须改名**如 `known = set(all_skills())`） | 改名+调用 |
| tools/lint_contracts.py:19/:27 | import + 列表推导 | `all_skills()` |
| tools/lint_key_reconciliation.py:54-66 | 锚串 `"src/shenbi/gates/shared.py: def marker_filename"` ×2 + `"src/shenbi/gates/cli.py: write_gate_marker("` | 改指 `"src/shenbi/gates/gate_manifest.py: def marker_filename"`（×2）；cli 锚不变（cli.py 调用面留 `write_gate_marker(` 字面——换 import 源不改调用文本） |
| tests/round-exec.sh:34-36 | `parse_report_stem(f.stem, ALL_SKILLS)` | `parse_report_stem(f.stem, all_skills())` + import 行同步 |
| tests/unit/gates/test_g0_dynamic_count.py:13 | `assert isinstance(ALL_SKILLS, list \| set)` | 断言三连：`all_skills()` 返回 list；两次调用同值（lru_cache）；「新目录可感知」——monkeypatch `shared.SKILLS` 指向 tmp 目录 → `all_skills.cache_clear()` → 调用断言含新技能 → **finally：恢复 SKILLS 后再 `all_skills.cache_clear()`（lru_cache 跨测试污染防护——plan 审查 I2；不留 finally 会让后续 G0.12 现树断言看到 tmp 陈值误红）** |
| tests/unit/gates/test_g0_config_coherence.py:192 | `monkeypatch.setattr(g0mod, "ALL_SKILLS", [])` | `monkeypatch.setattr(g0mod, "all_skills", lambda: [])` |
| tests/unit/gates/test_g0.py:102 docstring | "module-level constants" | 更新为惰性函数表述 |
| test_g0.py:257/:295、test_g7_reverse_coverage.py:7、test_g7.py:203、test_g_dispatch.py:68 | `ALL_SKILLS` 引用 | `all_skills()`（逐点核形态） |
| tests/unit/gates/test_shared.py:30 import | `from shenbi.gates.shared import write_gate_marker` | `from shenbi.gates.gate_manifest import write_gate_marker` |
| tests/unit/test_scoring.py:1261 | `from shenbi.gates.shared import marker_filename` | `from shenbi.gates.gate_manifest import marker_filename` |
| scoring.py:16 | 同上 | 同上 |
| gates/cli.py:116/:202 | `from shenbi.gates.shared import PROJECT, write_gate_marker` | 拆两行：PROJECT 留 shared，write_gate_marker 改 gate_manifest |

- [ ] **Step 4: marker 迁移**——write_gate_marker+marker_filename 整体（:711-745，含 docstring）剪贴至 gate_manifest.py（record_gate_result :108 附近）；gate_manifest 头部加 `from shenbi.safe_write import safe_write`（先核 gate_manifest 无既有同名符号）。

- [ ] **Step 5: 文本原语迁移**——QUOTE_PAIR（shared:371）+segment_sentences（shared:376）剪贴至 text/cjk.py（count_quote_pairs:73 邻近）；shared 原位留冗余别名 re-export（ruff F401 安全形态，对齐 compute_stats.py:17-19 既有先例）：

```python
from shenbi.text.cjk import (  # re-export（spec #89 T4：保 cd:28/test_shared_prose_primitives 零改）
    QUOTE_PAIR as QUOTE_PAIR,  # noqa: PLC0414
    segment_sentences as segment_sentences,  # noqa: PLC0414
)
```

compute_stats.py:19 换 `from shenbi.text.cjk import segment_sentences`（其 noqa PLC0414 行删除——不再 re-export）；**shared 的 `from shenbi.safe_write import safe_write` import（:9）随 write_gate_marker 迁走删除（唯一消费者 :743，plan 审查 M2）**。

- [ ] **Step 6: import 副作用测试绿** — Step 1 两测 PASS

- [ ] **Step 7: 回归** — `uv run pytest tests/unit/gates/ tests/unit/test_scoring.py tests/unit/tools/ -q` + `uv run python tools/lint_key_reconciliation.py --strict` + `bash tests/round-exec.sh --help` 或 shellcheck 面（`just lint` 内含）+ `just generate` diff 空（契约未动）

- [ ] **Step 8: Commit** — pathspec 逐文件（禁目录通配）：

```bash
git add src/shenbi/gates/shared.py src/shenbi/gates/gate_manifest.py src/shenbi/gates/g0.py \
  src/shenbi/gates/g7.py src/shenbi/gates/g_reconcile.py src/shenbi/gates/cli.py \
  src/shenbi/gates/g_dispatch.py src/shenbi/sync_contracts.py src/shenbi/pipeline/dispatch_helper.py \
  src/shenbi/scoring.py src/shenbi/text/cjk.py src/shenbi/skill_utils/style_learning/compute_stats.py \
  tools/lint_key_reconciliation.py tools/lint_contracts.py \
  tests/round-exec.sh tests/unit/gates/test_shared.py tests/unit/gates/test_g0_dynamic_count.py \
  tests/unit/gates/test_g0_config_coherence.py tests/unit/gates/test_g0.py tests/unit/gates/test_g7_reverse_coverage.py \
  tests/unit/gates/test_g7.py tests/unit/gates/test_g_dispatch.py tests/unit/test_scoring.py \
  tests/unit/gates/test_shared_import_side_effects.py
git commit -m "feat: spec #89 T4 shared 出鞘——marker 迁 gate_manifest+文本原语迁 text/+roster 惰性化+7 破裂面换源"
```

（git add 前逐个核路径存在；测试文件以 Step 3 表实际触面为准增删。）

---

### Task 5: 调用缝说真话（spec T5）

**复杂度: infra（轻）** ｜ **test_kind: regression_guard**

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_planning.py:75`（`_declared_history`→`declared_history` 公共名；自用 :117/:551 同步）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:545/:1209`（两处 import 换公共名、删 `# pyright: ignore[reportPrivateUsage]`）
- Modify: `docs/framework/gates.md`（增 g4_cross_chapter 非注册表门段）

- [ ] **Step 1: 红测先行**——`grep -c "reportPrivateUsage" src/shenbi/gates/g4/chapter_drafting.py`（现值 2；改名后须 0）。新断言入 `tests/unit/gates/g4/test_chapter_drafting.py`（追加一测）：

```python
@pytest.mark.unit
def test_no_report_private_usage_suppressions() -> None:
    """Spec #89 T5 AC8: no pyright reportPrivateUsage suppressions remain."""
    src = Path(cd.__file__).read_text(encoding="utf-8")
    assert "reportPrivateUsage" not in src
```

- [ ] **Step 2: 正名**——三处改名（定义+域内消费+cd 两 import），全仓 grep `_declared_history` 归零（`grep -rn "_declared_history" src/ tests/` 空；若 tests 有引用同步）。

- [ ] **Step 3: gates.md 增段**（文件尾部或 G4 节内）：

```markdown
### g4_cross_chapter —— 非注册表门（spec #89 T5）

`g4_cross_chapter`（src/shenbi/gates/g4/cross_chapter.py）**不在 build_checkers 注册表**：
pipeline 于 chapter_loop.py 直连调用（需跨章上下文装配——上一章内容/前窗 plan——
注册表的 per-round 单文件形态装不下）。注册表口径的「哪些门存在」不包含它；
新增跨章门须同样走直连+本文档登记，不得默默进注册表。
```

- [ ] **Step 4: 回归** — `uv run pytest tests/unit/gates/g4/ -q` 绿 + AC8 两 grep 过

- [ ] **Step 5: Commit** — `git add src/shenbi/gates/g4/chapter_planning.py src/shenbi/gates/g4/chapter_drafting.py docs/framework/gates.md tests/unit/gates/g4/test_chapter_drafting.py && git commit -m "feat: spec #89 T5 调用缝——_declared_history 正名公共+g4_cross_chapter 非注册表门文档化"`

---

### Task 6: G0.12 真实现（spec T6）

**复杂度: infra** ｜ **test_kind: tdd_red_green（注入红测）**

**Files:**
- Modify: `src/shenbi/gates/shared.py`（G4_CHECKER_SKILLS:798 邻近加 GENERIC_ONLY_ROSTER）
- Modify: `src/shenbi/gates/g0.py:708-725`（G0.12 块改真断言）
- Test: `tests/unit/gates/test_g0_checker_coverage.py`（新建；test_g0_dynamic_count.py 同域但不合并）

**Interfaces:**
- Consumes: Task 4 的 `all_skills()`。
- Produces: `GENERIC_ONLY_ROSTER: frozenset[str]`（44 项，下为全清单——**快照值**；与 skills/ 漂移时 G0.12 会红，新技能 PR 须显式登记此处或 G4_CHECKER_SKILLS，这正是设计）。

- [ ] **Step 1: 注入红测**

`tests/unit/gates/test_g0_checker_coverage.py`：

```python
"""Spec #89 T6: G0.12 is falsifiable — injected no-checker skill turns it red."""

from __future__ import annotations

import pytest

import shenbi.gates.g0 as g0mod


@pytest.mark.unit
def test_g012_fails_on_injected_fake_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    real = g0mod.all_skills
    monkeypatch.setattr(g0mod, "all_skills", lambda: [*real(), "shenbi-fake-skill"])
    g012 = g0mod.check_g4_checker_coverage()  # Step 4 提取的纯函数（-> dict）
    assert g012["s"] == g0mod.GateStatus.FAIL
    assert "shenbi-fake-skill" in g012["note"]


@pytest.mark.unit
def test_g012_passes_on_current_tree() -> None:
    g012 = g0mod.check_g4_checker_coverage()
    assert g012["s"] == g0mod.GateStatus.PASS
    assert "roster reconciled" in g012["note"]
```

（接线前提：Step 4 会把 G0.12 段提取为模块级纯函数 `def check_g4_checker_coverage() -> dict`（内部调 `all_skills()`，返回单行 checks dict——签名与 g0.py 既有「单检查助手」先例一致，如 G0.13 委托的 `check_independence_markers` 形态）；提取后主检查函数原位 `checks.append(check_g4_checker_coverage())`。测试与实现同步落地——红测先行指对**未提取前的大函数不可独调**现状，允许先做提取+假断言保持 PASS、再改真断言转红、注入红测证伪三步走 TDD（每步跑测）。）

- [ ] **Step 2: 跑红** — 注入用例 FAIL（现 G0.12 无条件 PASS——红测证伪现状）

- [ ] **Step 3: shared.py 加 GENERIC_ONLY_ROSTER**（44 项全清单，逐项写入）：

```python
# Spec #89 T6: generic-fallback roster — the explicit declaration that G0.12
# reconciles against set(all_skills()) == set(G4_CHECKER_SKILLS) | GENERIC_ONLY_ROSTER.
# A new generic skill MUST be registered here (or in G4_CHECKER_SKILLS if it gets
# a dedicated checker); this turns the implicit FS dependency into a declaration.
GENERIC_ONLY_ROSTER: frozenset[str] = frozenset(
    {
        "shenbi-anchor-curate",
        "shenbi-canon-import",
        "shenbi-chapter-pattern",
        "shenbi-character-extraction",
        "shenbi-drift-guidance",
        "shenbi-foreshadowing-plant",
        "shenbi-foreshadowing-recall",
        "shenbi-foreshadowing-resolve",
        "shenbi-foreshadowing-track",
        "shenbi-foundation-review",
        "shenbi-import-analysis",
        "shenbi-intent-management",
        "shenbi-review-anti-ai",
        "shenbi-review-character",
        "shenbi-review-continuity",
        "shenbi-review-dialogue",
        "shenbi-review-era",
        "shenbi-review-fanfic",
        "shenbi-review-foreshadowing",
        "shenbi-review-group-character",
        "shenbi-review-group-craft",
        "shenbi-review-group-factual",
        "shenbi-review-group-plan",
        "shenbi-review-highpoint",
        "shenbi-review-long-span",
        "shenbi-review-memo-compliance",
        "shenbi-review-motivation",
        "shenbi-review-pacing",
        "shenbi-review-pov",
        "shenbi-review-reader-pull",
        "shenbi-review-sensitivity",
        "shenbi-review-spinoff",
        "shenbi-review-texture",
        "shenbi-review-world-rules",
        "shenbi-sequel-writing",
        "shenbi-short-outline",
        "shenbi-short-packaging",
        "shenbi-snapshot-manage",
        "shenbi-style-learning",
        "shenbi-truth-sync",
        "shenbi-volume-consolidation",
        "shenbi-world-extraction",
        "shenbi-writing-skills",
        "using-shenbi",
    }
)
```

- [ ] **Step 4: G0.12 改真断言**（提取为模块级纯函数 `def check_g4_checker_coverage() -> dict`——对齐 g0.py 既有单检查助手先例 `check_independence_markers`[g0.py:126 委托 :747]；原位 `checks.append(check_g4_checker_coverage())`）：

```python
def check_g4_checker_coverage() -> dict:
    """G0.12 — every skill resolves to a G4 checker (dedicated or generic).

    Spec #89 T6: falsifiable roster reconciliation, no g4 import
    (GENERIC_ONLY_ROSTER lives in shared). Injected/unregistered skills
    surface as FAIL with the precise diff.
    """
    declared = set(G4_CHECKER_SKILLS) | GENERIC_ONLY_ROSTER
    actual = set(all_skills())
    if actual != declared:
        undeclared = sorted(actual - declared)
        missing = sorted(declared - actual)
        return {
            "id": "G0.12",
            "s": GateStatus.FAIL,
            "note": (
                "G4 coverage roster drift: "
                f"undeclared in roster: {undeclared}; missing from skills/: {missing}"
            ),
        }
    dedicated_count = len(G4_CHECKER_SKILLS)
    return {
        "id": "G0.12",
        "s": GateStatus.PASS,
        "note": (
            f"G4 coverage: {dedicated_count}/{len(actual)} dedicated, "
            f"{len(GENERIC_ONLY_ROSTER)} generic fallback (roster reconciled)"
        ),
    }
```

（import 区：g0 从 shared 加 `GENERIC_ONLY_ROSTER`；`all_skills` 已在 Task 4 换入。）

- [ ] **Step 5: 红测转绿** — 注入用例 PASS（FAIL 分支触发）+ 现树用例 PASS；`uv run pytest tests/unit/gates/test_g0.py tests/unit/gates/test_g0_dynamic_count.py tests/unit/gates/test_g0_config_coherence.py tests/unit/gates/test_g0_checker_coverage.py -q` 全绿

- [ ] **Step 6: 端到端 sanity** — `uv run shenbi-validate G0 <任一 seed>`（console-script 入口 `shenbi.gates.cli:main`；或 `just gate G0 <seed>`）跑 G0 只读环境检查，确认 G0.12 行 PASS note 含 "roster reconciled"

- [ ] **Step 7: Commit** — `git add src/shenbi/gates/shared.py src/shenbi/gates/g0.py tests/unit/gates/test_g0_checker_coverage.py && git commit -m "feat: spec #89 T6 G0.12 真实现——GENERIC_ONLY_ROSTER 44 项集合对账+注入红测"`

---

## 执行纪律（全部 task 共通）

- 每 task commit 后**当轮**产 `.superpowers/sdd/audit-T<N>.md`（fresh-context 子 agent 全量重审 findings 表）+ 更新 `spec-deviations.md ### T<N>`。
- 无 audit-T<N>.md 不得开始 T<N+1>；发现 spec 前提不成立 → 停 → 回阶段 1 重裁。
- 验收可执行化：每条 AC 在对应 task 完成时实跑命令并粘贴输出到 progress.md `## 验收证据`。
- just check（阶段 7）是最终门禁；rebase 后须重跑。
