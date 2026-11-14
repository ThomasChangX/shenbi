# Spec #90 契约数据面单源 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「哪些技能挂 G4 checker」的 5 处手工名册收敛为 shared.py 单一权威集合 + 派生（零构建基础设施），同批收缩 lint 对账面、换源 decisions 三源 lint、外置 contract-prose allowlist。

**Architecture:** `gates/shared.py` 的 `G4_CHECKER_KEYS` frozenset 字面量为权威集合（lint AST 提取器只认解点名下的字面量）；`generic.py` re-import、`G4_CHECKER_SKILLS = G4_CHECKER_KEYS` 别名行（g0 零改动）、`SHORT_MAP` 派生式移入 cli 的 G4 懒加载分支内。lint 侧守卫分层：结构级（改名/搬迁→非空守卫红）归 lint，成员级（删一行）归运行时三重守卫（generic assert / test_build_checkers / G0.12）。

**Tech Stack:** Python 3.11+（pathlib/ast/fnmatch/json）、pytest、just task runner。tools/ lint 可 `sys.path.insert` import src（lint_contracts.py:15 先例）。

## Global Constraints

- 契约纪律：本批**不触任何 SKILL.md frontmatter contract:**（T4 附带只改正文节——writing-skills 无 contract: 块）；若意外触及须 `just lint-contracts` 绿 + `just generate` diff 空。
- 框架纯度：`src/shenbi/` 无 `print()`（structlog）；tools/ lint 可 print（现行惯例）。gate 检查器保持纯函数幂等。
- 环境同构：一切验证走 `uv run` / `just`；系统 python 不算证据。
- G0.9：不造手写 fixture；测试注入用 tmp_path 构造结构输入（本仓允许形态）或引用真实文件副本。
- 提交纪律：conventional commits；pathspec 显式列文件，禁 `git add -A`。
- **F947 规则声明**：本 plan 全部验收离线可复验（lint/pytest/AST 断言/演练回滚），零真实 LLM dispatch，无 G3.4 评分场景。
- 中间态纪律：Task 2 是原子迁移 commit（名册迁移+lint 改指向同一 commit 完成，无红中间态）；Task 1 在现状树上独立全绿。

## 验收覆盖表（spec §2 AC1-7 → task → 验证命令）

| AC | Task | 验证命令 |
|---|---|---|
| 1 编辑面演练（3 处；GENERIC_ONLY_ROSTER 场景 4 处） | Task 5 | 演练 commit 上跑 `uv run pytest tests/unit/gates/g4/test_build_checkers.py -q` + `uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume`，随后 `git revert` |
| 2 单定义点 grep（pattern `G4_CHECKER_KEYS *[:=][^=]` 排除 import 行） | Task 2 完成时 | `grep -rnE "G4_CHECKER_KEYS *[:=][^=]" src/shenbi/ \| grep -v import`（恰 1 行 shared.py）+ `grep -rnE -e "G4_CHECKER_SKILLS *=" -e "SHORT_MAP *=" src/shenbi/gates/ \| grep -v import`（G4_CHECKER_SKILLS 别名行恰 1=shared.py；SHORT_MAP 顶层定义 0——派生在分支内小写形态；`-e` 形态免 markdown 表格转义陷阱）+ `grep -n "G4_CHECKER_KEYS" src/shenbi/gates/g4/generic.py`（仅 re-import+注释，零本地 frozenset 字面量） |
| 3 lint_decisions_sources 无自有 frontmatter 解析+STEM 零手条目+二义即 fail | Task 3 | `uv run python -c "import ast,...AST 断言..."` + `uv run python tools/lint_decisions_sources.py` exit 0 + 二义红测 |
| 4 值集对账红测（临时加 Handling 值→lint 红） | Task 3 | `uv run pytest tests/unit/test_lint_decisions_sources.py::test_value_set_drift_red -q`（tmp 副本注入 extra_probe→值集面红） |
| 5 writing-skills lint 面缺节红现状绿 | Task 4 | `uv run python tools/lint_repo_consistency.py` 现状绿；删节红测 |
| 6 T2 守卫锚：结构级红测 + 成员级运行时红测 | Task 1（lint 结构级）+ Task 5（运行时演练） | Task 1 tests；Task 5 演练 |
| 7 just check exit 0 | Task 5 Step 4（SDD 阶段 7 全量复跑） | `just check` |

---

### Task 1: lint_registry_reconcile 三面删除 + 非空守卫 + 测试改写（T2 前半，现状树独立绿）

**复杂度: infra**（lint 基建，多文件）｜ **test_kind: tdd_red_green + regression_guard**

**Files:**
- Modify: `tools/lint_registry_reconcile.py`（删 `_face_short_map:214`/`_face_g4_checker_skills:232`/`_face_agents_counts:274-283` 三面与 `_r1_skill_closure` 内三行调用；`_checker_keys:136-141` 加非空守卫；删孤儿 `_short_map_keys:108`；docstring :4-13 三面行更新；:33-36 Reading mechanisms 注释更新）
- Modify: `tests/unit/test_lint_registry_reconcile.py`（`test_short_map_deletion_fails:68-76` 与 `test_g4_checker_skills_gap_fails:94-99` 改写为结构级守卫红测+成员级绿钉[终审清偿字面：落地为超集]；`_COPY_LIST:28` 注释更新+cli.py/generic.py copy 行处置——generic.py 行保留[守卫仍读]，cli.py 行删除）
- Test: `tests/unit/test_lint_registry_reconcile.py`

**Interfaces:**
- Consumes: `_literal_str_set(source: str, assign_target: str) -> set[str]`（:68，不变）；`_checker_keys(repo: Path) -> set[str]`（:136，本 task 加守卫行为）
- Produces: `_checker_keys` 语义变更——**解出空集时返回前记 violation**（实现形态：`_checker_keys(repo)` 改 `(repo) -> tuple[set[str], list[str]]` 或守卫放 `_r1_skill_closure`/R5 调用点后统一判空——**采用后者**：两调用点后 `if not checkers: errs.append("[R1] G4_CHECKER_KEYS: extraction-empty: ...")`，`_checker_keys` 签名不变）；Task 2 依赖本 task 的守卫语义（迁移后守卫指向 shared.py 仍由同一函数承载）

- [ ] **Step 1: 写结构级守卫红测（先红后绿序——本步写的是「守卫不存在时必红」的新测试，运行应 FAIL）**

替换 `test_short_map_deletion_fails` 与 `test_g4_checker_skills_gap_fails` 为一个合并测试（并删原两函数）：

```python
def test_checker_keys_relocation_fails(repo_copy: Path) -> None:
    """Structure-level guard: G4_CHECKER_KEYS literal moved away (alias left) → FAIL.

    Member-level drift (deleting one entry) is runtime-guarded by
    generic.py build_checkers assert + test_build_checkers + G0.12 — lint
    deliberately does NOT guard it (spec #90 r2.3c).
    """
    p = repo_copy / "src" / "shenbi" / "gates" / "g4" / "generic.py"
    orig = (_SRC / "src/shenbi/gates/g4/generic.py").read_text(encoding="utf-8")
    # Relocation shape: literal renamed to _MOVED, original name left as alias.
    relocated = orig.replace(
        "G4_CHECKER_KEYS: frozenset[str] = frozenset(",
        "G4_CHECKER_KEYS_MOVED: frozenset[str] = frozenset(",
        1,
    ).replace(
        "G4_CHECKER_SKILLS = G4_CHECKER_KEYS",  # no-op today; future alias line
        "G4_CHECKER_SKILLS = G4_CHECKER_KEYS",
        1,
    )
    # Append alias line right after the moved definition block closes.
    relocated = relocated.replace(
        '        "shenbi-score-volume",\n    }\n)',
        '        "shenbi-score-volume",\n    }\n)\nG4_CHECKER_KEYS = G4_CHECKER_KEYS_MOVED\n',
        1,
    )
    p.write_text(relocated, encoding="utf-8")
    vios = lint_registry_reconcile(repo_copy)
    assert any("extraction-empty" in v for v in vios), vios
```

- [ ] **Step 2: 跑测试验证红**

Run: `uv run pytest tests/unit/test_lint_registry_reconcile.py::test_checker_keys_relocation_fails -q`
Expected: FAIL（`AssertionError`——守卫尚未实现，`vios` 无 extraction-empty 行）

- [ ] **Step 3: 实现守卫 + 删三面**

`tools/lint_registry_reconcile.py`：
1. `_r1_skill_closure`（:305）内：删 `errs += _face_short_map(repo, checkers)`、`errs += _face_g4_checker_skills(repo, checkers)`、`errs += _face_agents_counts(repo, all_dirs)` 三行；在 `checkers = _checker_keys(repo)` 后加：

```python
    checkers = _checker_keys(repo)
    if not checkers:
        errs.append(
            "[R1] G4_CHECKER_KEYS: extraction-empty: literal not found at "
            "expected site — renamed/moved away? (spec #90 structure guard)"
        )
```

2. `_r5_glob_validity`（:510）内 `checkers = _checker_keys(repo)`（:515）后加同样的空集 FAIL 行（`[R5] G4_CHECKER_KEYS: extraction-empty: ...`）。
3. 删函数 `_face_short_map`（:214-220）、`_face_g4_checker_skills`（:232-240）、`_face_agents_counts`（:274-283）、孤儿 `_short_map_keys`（:108-134，`_face_short_map` 删除后零调用）。
4. docstring（:4-13）R1 清单删三面行（`SHORT_MAP ⊇ ...`/`G4_CHECKER_SKILLS == ...`/`AGENTS.md counts == ...`），加一行 `G4_CHECKER_KEYS extraction non-empty (structure guard, spec #90)`。
5. `:33-36` Reading mechanisms 段 `SHORT_MAP via cli.py, stdlib-only module level` 措辞删（cli.py 不再被读）。
6. `tests/unit/test_lint_registry_reconcile.py` `_COPY_LIST`（:28）注释改 `generic.py  # G4_CHECKER_KEYS extraction`，删 `cli.py` copy 行（若 `_COPY_LIST` 含它——以现文件为准：保留 lint 实际仍读的文件项）。

- [ ] **Step 4: 跑测试验证绿 + 全文件测试**

Run: `uv run pytest tests/unit/test_lint_registry_reconcile.py -q`
Expected: 全 PASS（新守卫红测绿 + 其余 face 测试不受伤）

- [ ] **Step 5: 跑 lint 本体验证现状树绿**

Run: `uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume; echo "exit=$?"`
Expected: `exit=0`（0 violations——现状 generic.py 字面量仍在，守卫不触发）

- [ ] **Step 6: Commit**

```bash
git add tools/lint_registry_reconcile.py tests/unit/test_lint_registry_reconcile.py
git commit -m "refactor: spec #90 T2 前半——lint_registry_reconcile 删三恒真面+G4_CHECKER_KEYS 非空结构守卫+两破裂测试合并改写"
```

---

### Task 2: 名册单源迁移（T1+T2 后半，原子 commit）

**复杂度: infra**（gates 核心，import 图敏感）｜ **test_kind: tdd_red_green + characterization（30 项等价）**

**Files:**
- Modify: `src/shenbi/gates/shared.py`（:776 `G4_CHECKER_SKILLS = {...30...}` 字面量升格为 `G4_CHECKER_KEYS: frozenset[str] = frozenset({...30...})` + `G4_CHECKER_SKILLS = G4_CHECKER_KEYS` 别名行）
- Modify: `src/shenbi/gates/g4/generic.py`（:369-405 删本地 frozenset 定义改 `from shenbi.gates.shared import G4_CHECKER_KEYS`；「27 static + 3」注释改 len() 自述）
- Modify: `src/shenbi/gates/cli.py`（:23-54 删顶层 SHORT_MAP dict；G4 分支内（:115 附近 import 群）加派生）
- Modify: `tools/lint_registry_reconcile.py`（`_checker_keys` :138-139 解析目标 generic.py→shared.py）
- Modify: `tests/unit/test_lint_registry_reconcile.py`（`test_checker_keys_relocation_fails` 注入目标同步改 shared.py relocate 形态——Task 1 建立的测试在本 task 迁移后注入串对 generic.py 变 no-op 必红；`_COPY_LIST` generic.py copy 行注释二次清理[改指向后 generic 不再被 lint 读]）
- Test: `tests/unit/gates/g4/test_build_checkers.py`（现存断言即 characterization——不改应仍绿）+ 新增派生等价断言

**Interfaces:**
- Consumes: Task 1 的守卫语义（指向切换后自动生效）
- Produces: `shared.G4_CHECKER_KEYS: frozenset[str]`（权威，30 项）、`shared.G4_CHECKER_SKILLS`（别名）、`generic.G4_CHECKER_KEYS`（re-import，向后兼容 g5.py:6/:341）、`cli` G4 分支内 `SHORT_MAP`（局部派生 dict）

- [ ] **Step 1: 写红测——单源形态断言（迁移前红：shared 无 G4_CHECKER_KEYS 定义）**

追加到 `tests/unit/gates/g4/test_build_checkers.py`：

```python
def test_roster_single_source() -> None:
    """Spec #90 T1: shared.py holds the authoritative literal; generic re-imports."""
    import ast
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    shared_src = (repo / "src/shenbi/gates/shared.py").read_text(encoding="utf-8")
    tree = ast.parse(shared_src)
    targets = {
        t.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Name)
    }
    ann = {
        node.target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, (ast.Call, ast.Set))
    }
    assert "G4_CHECKER_KEYS" in (targets | ann), "shared.py must define the literal"
    assert "G4_CHECKER_SKILLS" in targets, "shared.py must keep alias line"

    from shenbi.gates.g4 import generic
    from shenbi.gates.shared import G4_CHECKER_KEYS

    assert generic.G4_CHECKER_KEYS is G4_CHECKER_KEYS, "generic must re-import, not copy"
    assert len(G4_CHECKER_KEYS) == 30
```

Run: `uv run pytest tests/unit/gates/g4/test_build_checkers.py::test_roster_single_source -q`
Expected: FAIL（`shared.py must define the literal`——现状字面量在 generic）

- [ ] **Step 2: 写红测——cli SHORT_MAP 派生等价（迁移前红：顶层 dict 尚存/分支内无派生）**

追加同文件：

```python
def test_short_map_derived_in_g4_branch() -> None:
    """Spec #90 T1: SHORT_MAP is derived inside the G4 lazy branch, not a top-level dict."""
    import ast
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    src = (repo / "src/shenbi/gates/cli.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    top_assigns = [
        t.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for t in node.targets
        if isinstance(t, ast.Name)
    ]
    assert "SHORT_MAP" not in top_assigns, "no top-level SHORT_MAP dict (spec #90 T1)"
    assert "short_map = {k.removeprefix(" in src, "derived form must exist in G4 branch"
```

Run: `uv run pytest tests/unit/gates/g4/test_build_checkers.py::test_short_map_derived_in_g4_branch -q`
Expected: FAIL（顶层 dict 尚存）

- [ ] **Step 3: 实施迁移（一个 commit 内完成四处+lint 改指向）**

1. `shared.py`：`G4_CHECKER_SKILLS = {` (:776) 改为注释块+权威定义（保留原 30 项成员与排序）：

```python
# Spec #90 T1: authoritative G4 checker roster (single source). The literal
# MUST stay under the G4_CHECKER_KEYS name — tools/lint_registry_reconcile.py
# extracts it by AST from this file; G4_CHECKER_SKILLS is a compatibility
# alias (g0.py module-level import stays untouched). String-only so lint
# tooling (and g5) can import it without pulling the per-skill checker modules.
G4_CHECKER_KEYS: frozenset[str] = frozenset(
    {
        "shenbi-anti-detect",
        # ... 全部 30 项原样照搬（与现 G4_CHECKER_SKILLS 成员集完全一致） ...
    }
)
G4_CHECKER_SKILLS = G4_CHECKER_KEYS
```

2. `generic.py`：删 :369-405 本地定义（含旧注释），import 块（:14-20）扩为：

```python
from shenbi.gates.shared import (
    G4_CHECKER_KEYS,
    chapter_no,
    chapter_no_raw,
    fail,
    passed,
    resolve_input_path,
)
```

并在原定义处留注释：`# G4_CHECKER_KEYS lives in shared.py (spec #90 single source); len() == 30`（len() 自述替换「27 static + 3」手写计数；score-* 三键同为字面量成员——register_score_checkers 只注册 checker 函数不改名册）。
3. `cli.py`：删顶层 :23-54 SHORT_MAP；G4 分支 import 群（:115-117）加一行 `from shenbi.gates.g4.generic import G4_CHECKER_KEYS`，:169 消费点前加：

```python
            short_map = {k.removeprefix("shenbi-"): k for k in G4_CHECKER_KEYS}
            full_name = short_map.get(skill_or_type, skill_or_type)
```

（:169 原 `full_name = SHORT_MAP.get(...)` 行替换。注意：G4 分支已 import `from shenbi.gates.g4 import gate_G4, ...`——包 init 已拉 generic 全链，直接从 generic import G4_CHECKER_KEYS 零边际成本。）
4. `tools/lint_registry_reconcile.py` `_checker_keys`（:138-139）：`generic = repo / "src" / "shenbi" / "gates" / "g4" / "generic.py"` 改 `shared = repo / "src" / "shenbi" / "gates" / "shared.py"`，`_literal_str_set(shared.read_text(...), "G4_CHECKER_KEYS")`。
5. `tests/unit/test_lint_registry_reconcile.py` `test_checker_keys_relocation_fails` 注入目标同步改写——relocate 对象从 generic.py 换 **shared.py**（迁移后权威字面量所在地）：

```python
def test_checker_keys_relocation_fails(repo_copy: Path) -> None:
    """Structure-level guard: G4_CHECKER_KEYS literal moved away (alias left) → FAIL.

    Member-level drift (deleting one entry) is runtime-guarded by
    generic.py build_checkers assert + test_build_checkers + G0.12 — lint
    deliberately does NOT guard it (spec #90 r2.3c).
    """
    p = repo_copy / "src" / "shenbi" / "gates" / "shared.py"
    orig = (_SRC / "src/shenbi/gates/shared.py").read_text(encoding="utf-8")
    relocated = orig.replace(
        "G4_CHECKER_KEYS: frozenset[str] = frozenset(",
        "G4_CHECKER_KEYS_MOVED: frozenset[str] = frozenset(",
        1,
    ).replace(
        "G4_CHECKER_SKILLS = G4_CHECKER_KEYS\n",
        "G4_CHECKER_SKILLS = G4_CHECKER_KEYS_MOVED\nG4_CHECKER_KEYS = G4_CHECKER_KEYS_MOVED\n",
        1,
    )
    p.write_text(relocated, encoding="utf-8")
    vios = lint_registry_reconcile(repo_copy)
    assert any("extraction-empty" in v for v in vios), vios
```

   同批：`_COPY_LIST` 删 generic.py copy 行（lint 不再读它——注意保留其他面仍读的文件项，以现文件为准）。

（Task 1 Step 1 的初版测试注入 generic.py 在现状树正确；本 task 迁移落地时**同 commit** 改为上述 shared.py 形态——Task 1→Task 2 之间该测试始终绿。）

- [ ] **Step 4: `_tool_hashes` 重锁（plan 审查轮 2 R1/轮 3 时序修正——deps.json 锁 216 个 src/shenbi/**/*.py 含本 task 三编辑目标，不重锁则 Step 5 的 `test_clean_repo_zero_violations`[repo_copy 内 R3 face 对 shared.py 比对旧锁值]必红）**

Run: `bash tests/lock-tool-hashes.sh && uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume; echo exit=$?`
Expected: 脚本重写 `tests/tiers/deps.json` 的 `_tool_hashes` 三个 src 条目；lint exit 0（R3 fresh）
**Step 7 git add 必须含 `tests/tiers/deps.json`**（重锁产物入提交，否则提交树永久 R3 红）。

- [ ] **Step 5: 跑全部相关测试验证绿**

Run: `uv run pytest tests/unit/gates/g4/test_build_checkers.py tests/unit/test_lint_registry_reconcile.py tests/unit/test_gates_cli.py -q`
Expected: 全 PASS（30 项等价/单源断言/守卫红测/g0 相关——含 `test_clean_repo_zero_violations`：重锁已在前，R3 fresh）

- [ ] **Step 6: 冷启动验收锚**

Run: `uv run python -c "import time; t=time.perf_counter(); import shenbi.gates.cli; print(f'{(time.perf_counter()-t)*1000:.1f}ms')"` 与 `uv run python -c "import shenbi.gates.g0, sys; print([m for m in sys.modules if m.startswith('shenbi.gates.g4')])"`
Expected: cli 冷启动量级与迁移前同阶（无 generic 全链拉入——对比迁移前基线）；g0 导入后 g4 模块列表为空

- [ ] **Step 6b: lint 本体验证 + AC2 grep**

Run: `uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume && grep -rnE "G4_CHECKER_KEYS *[:=][^=]" src/shenbi/ | grep -v import`
Expected: lint exit 0；grep 恰 1 行（shared.py 权威定义）

- [ ] **Step 7: Commit（原子）**

```bash
git add src/shenbi/gates/shared.py src/shenbi/gates/g4/generic.py src/shenbi/gates/cli.py tools/lint_registry_reconcile.py tests/unit/gates/g4/test_build_checkers.py tests/unit/test_lint_registry_reconcile.py tests/tiers/deps.json
git commit -m "refactor: spec #90 T1——G4 checker 名册单源迁移 shared.py（字面量+别名+generic re-export+cli 分支内派生+lint 改指向+守卫测试同步改写+_tool_hashes 重锁，原子迁移零红中间态）"
```

---

### Task 3: lint_decisions_sources 换源 + STEM 派生 + 值集对账 + 第四源（T3）

**复杂度: infra**（跨 tools/contracts/docs 四域）｜ **test_kind: tdd_red_green**

**Files:**
- Modify: `tools/lint_decisions_sources.py`（`_skill_names_from_writes:23-50` 旧手扫器删除改 load_contract 遍历；`STEM_TO_SKILL:54-63` 删改派生；main 加值集对账+第四源对账）
- Test: `tests/unit/test_lint_decisions_sources.py`（新建——二义即 fail 红测+值集红测+AST 无自有解析断言）
- Read-only refs: `src/shenbi/contracts/loader.py:295 load_contract`、`tools/lint_contracts.py:22 META_SKILLS`、`src/shenbi/contracts/schemas/decisions.py:15-19`、`docs/framework/decisions-schema.md:60-82`、`src/shenbi/gates/g4/generic.py:356 G4_DECISIONS_WIRED`

**Interfaces:**
- Consumes: `load_contract(skill: str) -> Contract`（loader.py:295；Contract 为 7 键 TypedDict，`contract["writes"]`/`contract["updates"]` 索引成立）；`META_SKILLS: set[str]`（lint_contracts.py:22——**import 消费，先例形态**：`tools/lint_contract_prose.py:48` 的 `from tools.lint_contracts import META_SKILLS`——repo root 进 sys.path 后按包名导入，tools/ 有 `__init__.py`；**不**用「tools 目录进 path + 裸 `from lint_contracts import`」双模块名形态）
- Produces: `derive_stem_to_skill() -> dict[str, str]`（严格 {N}/{N+1}→N 归一，二义 raise）；main() 四对账（三源+值集+G4_DECISIONS_WIRED）

- [ ] **Step 1: 写红测——二义即 fail + 派生等价（新建测试文件）**

```python
"""Spec #90 T3: STEM_TO_SKILL derivation + value-set + fourth-source reconciliation."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
LINT = REPO / "tools" / "lint_decisions_sources.py"


def _load_lint():
    spec = importlib.util.spec_from_file_location("lds", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stem_derivation_matches_hand_table() -> None:
    mod = _load_lint()
    derived = mod.derive_stem_to_skill()
    expected = {
        "chapter-N-context-decisions": "context-composing",
        "market-radar-decisions": "market-radar",
        "chapter-N-decisions": "chapter-drafting",
        "chapter-N-plan-decisions": "chapter-planning",
        "chapter-N-revision-decisions": "chapter-revision",
        "state-settling-decisions": "state-settling",
        "genre-config-decisions": "genre-config",
        "short-N-decisions": "short-drafting",
    }
    assert derived == expected


def test_ambiguous_glob_raises() -> None:
    """Naive N→* would map chapter-N-decisions.json onto chapter-N-revision-…; strict normalization must fail loudly."""
    mod = _load_lint()
    try:
        mod._resolve_stem(
            "chapter-3-decisions", {"chapter-drafting": ["chapters/chapter-N-decisions.json"]}
        )
        raised = False
    except SystemExit:
        raised = True
    # 二义场景构造见实现——naive 形态下 chapter-N-decisions.json 也匹配 revision 技能时应 exit
    assert raised or True  # 具体断言由实现形态定——见 Step 3 实现后的精化
```

（注：第二个测试的具体注入形态在 Step 3 实现后精化为确定断言——红测先行以「实现缺函数 import 即红」为准。）

Run: `uv run pytest tests/unit/test_lint_decisions_sources.py -q`
Expected: FAIL（`AttributeError: module 'lds' has no attribute 'derive_stem_to_skill'`）

- [ ] **Step 2: 实现——旧手扫器换 load_contract + STEM 派生**

`tools/lint_decisions_sources.py` 重写核心：

```python
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from tools.lint_contracts import META_SKILLS  # noqa: E402 — lint_contract_prose.py:48 precedent
from shenbi.contracts.loader import load_contract  # noqa: E402


def _skill_names_from_writes() -> set[str]:
    """Skills whose contract writes/updates declare a *decisions*.json output.

    Spec #90 T3: load_contract replaces the retired hand-rolled YAML walk (new
    write-semantics keys silently broke it). Malformed functional contracts
    raise here — a deliberate fail-loud side-sentry, not accidental coupling.
    """
    result: set[str] = set()
    for skill_md in sorted((REPO / "skills").glob("*/SKILL.md")):
        skill_dir = skill_md.parent.name
        if skill_dir in META_SKILLS:
            continue  # meta skills carry no contract block (loader would raise)
        contract = load_contract(skill_dir)
        if any(p.endswith("-decisions.json") for p in (*contract["writes"], *contract["updates"])):
            result.add(skill_dir.removeprefix("shenbi-"))
    return result
```

STEM 派生（严格归一——`{N}`/`{N+1}` 占位符统一为 N；裸 `N`（fnmatch 数字通配）同样归一；**多技能同 stem 归一后冲突即 print+exit 1**）：

```python
import re

_NORM = re.compile(r"\{N\+1\}|\{N\}|(?<![A-Za-z-])N(?![A-Za-z-])")


def _normalize_pattern(path: str) -> str:
    """`chapter-{N+1}-decisions.json` / `chapter-N-decisions.json` → chapter-N-…"""
    return _NORM.sub("N", path)


def derive_stem_to_skill() -> dict[str, str]:
    mapping: dict[str, str] = {}
    holder: dict[str, str] = {}
    for skill_md in sorted((REPO / "skills").glob("shenbi-*/SKILL.md")):
        skill_dir = skill_md.parent.name
        if skill_dir in META_SKILLS:
            continue
        contract = load_contract(skill_dir)
        for p in (*contract["writes"], *contract["updates"]):
            if p.endswith("-decisions.json"):
                stem = Path(_normalize_pattern(p)).stem
                if stem in mapping and mapping[stem] != skill_dir.removeprefix("shenbi-"):
                    print(
                        f"lint_decisions_sources: ambiguous decisions stem '{stem}' "
                        f"claimed by {mapping[stem]} and {skill_dir} — tighten patterns"
                    )
                    sys.exit(1)
                mapping[stem] = skill_dir.removeprefix("shenbi-")
                holder[stem] = p
    return mapping
```

`_truth_file_skills`（:66-80）改用 `derive_stem_to_skill()`（删 STEM_TO_SKILL 手表与 .get-unmapped 逻辑——派生即权威）。main() 三源对账保持（writes/truth/doc 六向差集不变）。

- [ ] **Step 3: 精化二义红测（实现落定后）**

把 Step 1 第二测试改为确定形态：tmp_path 构造假技能目录（结构性输入，G0.9 允许）使两技能 writes 归一后同 stem，断言 `SystemExit`。**patch 面两个（plan 审查轮 2 Y2）**：① `monkeypatch.setattr(mod, "REPO", fake)`（遍历面）；② `monkeypatch.setattr("shenbi.contracts.loader.SKILLS", fake / "skills")`——`load_contract` 经 loader 模块级 `SKILLS` 常量解析技能目录并按真实 truth registry 校验路径，只 shadow REPO 不够；假技能 writes 须用 registry 可解析形（如 `chapters/chapter-N-decisions.json` 与 `chapters/chapter-N-revision-decisions.json` 归一后分别为不同 stem——构造同 stem 二义用 `chapters/chapter-{N+1}-decisions.json` vs `chapters/chapter-N-decisions.json` 同技能不触、**跨技能同归一 stem** 如两技能都写 `chapter-N-plan-decisions.json`）。跑红绿验证：先在无二义守卫的旧实现上红、新实现上绿（若 Step 2 已含守卫则此步为验证绿）。

Run: `uv run pytest tests/unit/test_lint_decisions_sources.py -q`
Expected: PASS

- [ ] **Step 4: 值集对账（status-vocab 模板）**

main() 内追加（对齐 lint_status_strings 面 3 先例的「值集精确相等」语义）：

```python
def _value_set_face() -> list[str]:
    """Spec #90 T3: decisions-schema.md enums == contracts/schemas/decisions.py Literals."""
    import re as _re  # noqa: PLC0415 — function-local per lint_registry_reconcile precedent

    schema_src = (REPO / "src/shenbi/contracts/schemas/decisions.py").read_text(encoding="utf-8")
    doc_src = (REPO / "docs/framework/decisions-schema.md").read_text(encoding="utf-8")
    errs: list[str] = []
    for lit_name, section in [
        ("Handling", "adjustments[].handling"),
        ("SeverityLevel", "selections[].severity"),
        ("Basis", "selections[].basis"),
        ("Trim", "budget.trim_applied"),
    ]:
        m = _re.search(rf"^{lit_name} = Literal\[(.*?)\]", schema_src, _re.MULTILINE | _re.DOTALL)
        code_vals = set(_re.findall(r'"([\w]+)"', m.group(1))) if m else set()
        # Section headers contain [] — re.escape is mandatory. Boundary must stop
        # at both ### and ## level headings. NOTE: this is an f-string — the
        # brace quantifier MUST be doubled ({{2,3}}) or it becomes a replacement
        # field (plan review round-2 R2: `{2,3}` compiled to `#(2, 3) ` and the
        # lookahead never matched).
        doc_sec = _re.search(
            rf"### `{_re.escape(section)}`(.*?)(?=\n#{{2,3}} |\Z)",
            doc_src,
            _re.DOTALL,
        )
        doc_vals = set(_re.findall(r"`([\w]+)`", doc_sec.group(1))) if doc_sec else set()
        if code_vals != doc_vals:
            errs.append(f"value-set: {lit_name} code={sorted(code_vals)} doc={sorted(doc_vals)}")
    return errs
```

（doc 节名以 `docs/framework/decisions-schema.md` 实际节头为准——`budget.trim_applied` 是 Enums 节实况（plan 审查轮 1 I1(ii) 实锤）；若施工时节头有出入，以 doc 实况校准 section 字符串，`re.escape` 保证 `[]` 安全。`doc_sec is None` 视为 doc_vals 空集 != code_vals → 红（缺节即漂移）。）
main() `return 0` 前：`errs = _value_set_face() + _wired_face(writes); if errs: print("\n".join(errs)); return 1`（两 face 串联；writes 即 `_skill_names_from_writes()` 结果）。

**AC4 红测（本步同批落成，tmp 副本注入）**——`tests/unit/test_lint_decisions_sources.py` 追加：

```python
def test_value_set_drift_red(tmp_path, monkeypatch) -> None:
    """AC4: adding one Handling value to the pydantic model → value-set face red."""
    import shutil

    mod = _load_lint()
    # Shadow REPO with a tmp copy carrying an extra Handling value.
    fake = tmp_path / "repo"
    (fake / "src/shenbi/contracts/schemas").mkdir(parents=True)
    shutil.copytree(REPO / "docs", fake / "docs")
    schemas = (REPO / "src/shenbi/contracts/schemas/decisions.py").read_text(encoding="utf-8")
    schemas_drift = schemas.replace(
        'Handling = Literal["compensate_via_pacing", "explicit_callout", "defer_to_next_chapter", "ignore"]',
        'Handling = Literal["compensate_via_pacing", "explicit_callout", "defer_to_next_chapter", "ignore", "extra_probe"]',
        1,
    )
    assert schemas_drift != schemas, "anchor string drifted — recalibrate"
    (fake / "src/shenbi/contracts/schemas/decisions.py").write_text(schemas_drift, encoding="utf-8")
    monkeypatch.setattr(mod, "REPO", fake)
    errs = mod._value_set_face()
    assert any("Handling" in e and "extra_probe" in e for e in errs), errs
```

Run: `uv run pytest tests/unit/test_lint_decisions_sources.py::test_value_set_drift_red -q`
Expected: PASS（红测：注入 extra_probe 后值集面产出漂移行——红即守卫生效）

- [ ] **Step 5: 第四源对账（producers == G4_DECISIONS_WIRED）**

main() 追加：

```python
def _wired_face(producers: set[str]) -> list[str]:
    """Spec #90 T3: derived producers == G4_DECISIONS_WIRED (generic.py:356)."""
    import ast  # noqa: PLC0415 — tools/ scope enforces it (plan review round-3)

    generic_src = (REPO / "src/shenbi/gates/g4/generic.py").read_text(encoding="utf-8")
    tree = ast.parse(generic_src)
    wired: set[str] | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and getattr(node.target, "id", "") == "G4_DECISIONS_WIRED"
        ):
            if isinstance(node.value, ast.Call) and isinstance(
                node.value.args[0], (ast.Set, ast.List)
            ):
                wired = {
                    el.value
                    for el in node.value.args[0].elts
                    if isinstance(el, ast.Constant) and isinstance(el.value, str)
                }
    if wired is None:
        return ["G4_DECISIONS_WIRED: extraction-empty: literal not found"]
    wired_short = {w.removeprefix("shenbi-") for w in wired}
    if wired_short != producers:
        return [f"G4_DECISIONS_WIRED: wired={sorted(wired_short)} producers={sorted(producers)}"]
    return []
```

（producers 传 `_skill_names_from_writes()` 结果。）

- [ ] **Step 6: 跑 lint 本体+测试全绿**

Run: `uv run python tools/lint_decisions_sources.py; echo exit=$?` + `uv run pytest tests/unit/test_lint_decisions_sources.py -q`
Expected: `OK (8 producers aligned across 3 sources)` exit 0 + 值集/第四源零输出；测试 PASS

- [ ] **Step 7: AC3 AST 断言（无自有 frontmatter 解析逻辑）**

`tests/unit/test_lint_decisions_sources.py` 追加：

```python
def test_no_own_frontmatter_parser() -> None:
    """AC3: the lint must not carry its own frontmatter parsing (load_contract instead).

    AST-level assertion per spec ruling — a bare text grep on a keyword is NOT
    sufficient (deleting a comment must not be what passes this check).
    """
    src = LINT.read_text(encoding="utf-8")
    import ast as _ast

    tree = _ast.parse(src)
    fn = next(
        (
            n
            for n in _ast.walk(tree)
            if isinstance(n, _ast.FunctionDef) and n.name == "_skill_names_from_writes"
        ),
        None,
    )
    assert fn is not None
    # No re.search/re.match/read_text parsing of frontmatter inside the function:
    call_names = {
        getattr(c.func, "attr", getattr(c.func, "id", ""))
        for c in _ast.walk(fn)
        if isinstance(c, _ast.Call)
    }
    assert not ({"search", "match", "findall"} & call_names), (
        "must delegate parsing to load_contract"
    )
    assert "load_contract" in src
```

Run: `uv run pytest tests/unit/test_lint_decisions_sources.py::test_no_own_frontmatter_parser -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add tools/lint_decisions_sources.py tests/unit/test_lint_decisions_sources.py
git commit -m "feat: spec #90 T3——lint_decisions_sources 换源 load_contract+STEM_TO_SKILL 严格归一派生+值集对账+G4_DECISIONS_WIRED 第四源"
```

---

### Task 4: contract-prose allowlist 迁 JSON + writing-skills 机器契约面（T4a+T4 附带）

**复杂度: infra**（lint 载体切换+技能文档）｜ **test_kind: tdd_red_green + regression_guard（9 条迁移等价）**

**Files:**
- Create: `tools/contract_prose_allowlist.json`（9 条三元组平铺）
- Modify: `tools/lint_contract_prose.py`（:64-106 ALLOWLIST tuple 删改 JSON 装载+fail-loud+未知 skill 键 FAIL+未命中条目 WARN；:195/:247 两消费点改读装载结果）
- Modify: `skills/shenbi-writing-skills/SKILL.md`（补「机器契约」节）
- Modify: `tools/lint_repo_consistency.py`（新增 writing-skills 缺节红面）
- Test: `tests/unit/tools/test_lint_contract_prose.py`（**现存 19 测试文件——向其追加**，不新建平行文件；fail-loud 红测+未知键红测；plan 审查轮 3 🟡-1）

**Interfaces:**
- Produces: `load_allowlist() -> tuple[tuple[str, str, str], ...]`（lint_contract_prose 内；JSON 缺失/不可解析/未知 skill 键 → print+exit 1；未命中条目 → stderr WARN 不计 FAIL）

- [ ] **Step 1: 写红测（JSON 不存在 fail-loud / 未知键 FAIL / 9 条等价）**

**向现存文件追加**（plan 审查轮 4 N1：复用现存包导入形态 `from tools.lint_contract_prose import ...`——不用 importlib 双装载，路径常量取自模块本身）：

```python
# --- appended: spec #90 T4a allowlist JSON carrier (fail-loud semantics) ---


def test_json_carrier_exists_and_has_nine_entries() -> None:
    import json

    data = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 9
    for entry in data:
        assert set(entry) == {"category", "pattern", "reason"}


def test_missing_json_fails_loud(tmp_path, monkeypatch) -> None:
    """Carrier file missing → exit 1 (never silently fall back to empty allowlist)."""
    import tools.lint_contract_prose as lcp

    monkeypatch.setattr(lcp, "ALLOWLIST_PATH", tmp_path / "nonexistent.json")
    try:
        lcp.load_allowlist()
        raised = False
    except SystemExit:
        raised = True
    assert raised
```

（文件头部已 import `from tools.lint_contract_prose import find_violations, main`——追加 `ALLOWLIST_PATH` 到该 import 行，或如上在函数内 `import tools.lint_contract_prose as lcp`；未知 skill 键 FAIL 测试同 monkeypatch 形态：tmp JSON 写 `[{"category": "x", "pattern": "shenbi-not-a-skill:foo.md", "reason": "r"}]` 后 `monkeypatch.setattr(lcp, "ALLOWLIST_PATH", tmp_json)`，期望 SystemExit。）

Run: `uv run pytest tests/unit/tools/test_lint_contract_prose.py -q`
Expected: FAIL（JSON 文件不存在/函数未定义——新追加的测试红）

- [ ] **Step 2: 建 JSON（9 条从 ALLOWLIST tuple 机械迁移）**

`tools/contract_prose_allowlist.json`：

```json
[
  {"category": "skill-bundle", "pattern": "*:anti-ai-reference.md", "reason": "捆绑参考文件, dispatcher 不注入 (T1.1 裁决 b)"},
  {"category": "skill-bundle", "pattern": "shenbi-review-era:skills/shenbi-review-era/era-reference.md", "reason": "捆绑参考文件全路径消歧 (spec62 F857), dispatcher 不注入"},
  {"category": "anti-example", "pattern": "shenbi-context-composing:chapters/chapter-*.md", "reason": "anti-rationalization 反例行引用, 非真实读依赖"},
  {"category": "anti-example", "pattern": "shenbi-foundation-review:characters/villain.md", "reason": "证据引用格式的示例路径, 非真实读依赖"},
  {"category": "anti-example", "pattern": "shenbi-book-spine-init:author_intent.md", "reason": "铁律 1 显式否定引用(创世层不读此文件), 非读依赖——reads 补声明即死声明"},
  {"category": "repo-docs", "pattern": "shenbi-chapter-drafting:docs/framework/chapter-file-format.md", "reason": "仓库框架文档引用, 开发者参考, dispatcher 不注入"},
  {"category": "repo-docs", "pattern": "shenbi-chapter-drafting:docs/framework/style-directives.md", "reason": "仓库框架文档引用(style_directives 规范), 开发者/用户参考, dispatcher 不注入"},
  {"category": "repo-docs", "pattern": "shenbi-chapter-revision:docs/framework/status-vocab.md", "reason": "仓库框架文档引用, 开发者参考, dispatcher 不注入"},
  {"category": "anti-example", "pattern": "shenbi-review-anti-ai:checklist.md", "reason": "否定引用(原文件已随 spec #33 T2 死资产清理删除), 非读依赖"}
]
```

- [ ] **Step 3: 实现 load_allowlist + fail-loud + 消费点改读**

`tools/lint_contract_prose.py`：删 :64-106 tuple；加：

```python
import json as _json
import sys as _sys

ALLOWLIST_PATH = Path(__file__).resolve().parent / "contract_prose_allowlist.json"
_SKILL_KEY = re.compile(r"^([a-z0-9-]+|\*):")


def load_allowlist() -> tuple[tuple[str, str, str], ...]:
    """Spec #90 T4a: external JSON carrier. Missing/unparseable/unknown-skill-key → exit 1."""
    if not ALLOWLIST_PATH.exists():
        print(f"lint_contract_prose: allowlist carrier missing: {ALLOWLIST_PATH}", file=_sys.stderr)
        _sys.exit(1)
    try:
        data = _json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except _json.JSONDecodeError as exc:
        print(f"lint_contract_prose: allowlist JSON unparseable: {exc}", file=_sys.stderr)
        _sys.exit(1)
    known = {
        p.name for p in ALLOWLIST_PATH.parent.parent.joinpath("skills").iterdir() if p.is_dir()
    }
    out: list[tuple[str, str, str]] = []
    for entry in data:
        key = (
            _SKILL_KEY.match(entry["pattern"]).group(1)
            if _SKILL_KEY.match(entry["pattern"])
            else None
        )
        if key not in (None, "*") and f"shenbi-{key}" not in known and key not in known:
            print(
                f"lint_contract_prose: unknown skill key '{key}' in allowlist entry",
                file=_sys.stderr,
            )
            _sys.exit(1)
        out.append((entry["category"], entry["pattern"], entry["reason"]))
    return tuple(out)
```

（`known` 集合以 skills/ 目录现名为准；meta 技能 using-shenbi 也在目录内故天然放行。）模块级 `ALLOWLIST = load_allowlist()`（:195/:247 消费点不改——名字保持）。未命中条目 WARN：主 lint 流程末尾若某 pattern 全程零命中 → stderr WARN（实现处放 main() 汇总段，一处）。

- [ ] **Step 4: 跑 lint 本体+测试（回归等价——0 violations 不变）**

Run: `uv run python tools/lint_contract_prose.py --fail; echo exit=$?` + `uv run pytest tests/unit/tools/test_lint_contract_prose.py -q`
Expected: exit 0（9 条豁免行为与 in-code 时代逐条等价——0 violations）+ 测试 PASS

- [ ] **Step 5: writing-skills 机器契约节 + lint_repo_consistency 面**

1. `skills/shenbi-writing-skills/SKILL.md` 末尾追加节（不改 frontmatter——无 contract: 块不触生成物同步）：

```markdown
## 机器契约（Machine Contract）

技能作者必须遵守的机器可检契约，本节为入口索引：

- **`contract:` 块**：每个 functional 技能的 SKILL.md frontmatter 必须声明 `reads`/`writes`/`updates`（`shenbi.contract` 装载器消费；缺失/畸形在 G0 契约子门与 lint_contracts 红——具体子门编号施工时以 `shenbi-validate G0` 输出实况校准，不预设）。
- **decisions 边车**：产出自然语言/易变输出的技能须声明 `*-decisions.json` 写件（schema 见 docs/framework/decisions-schema.md；三源对账由 tools/lint_decisions_sources.py 执法）。
- **write-semantics / plan_format**：字段级约束与 plan 版本契约由 loader `_validate` 与 G4 各 checker 消费。
```

（G0 子门编号以施工时 `shenbi-validate G0` 输出实况校准——不虚构编号。）
2. `tools/lint_repo_consistency.py` 新面（挂进现有 main 面列表）：

```python
def find_missing_machine_contract_section(repo: Path) -> list[str]:
    """Spec #90 T4: shenbi-writing-skills SKILL.md must carry the 机器契约 section."""
    skill_md = repo / "skills" / "shenbi-writing-skills" / "SKILL.md"
    if not skill_md.exists():
        return []
    text = skill_md.read_text(encoding="utf-8")
    if "机器契约" not in text or "decisions" not in text:
        return ["writing-skills: machine-contract section missing (spec #90)"]
    return []
```

- [ ] **Step 6: 验证 AC5 双态（定为测试形态——tmp copy 注入缺节红测）**

新建 `tests/unit/test_lint_repo_consistency_writing_skills.py`：

```python
"""Spec #90 T4: writing-skills machine-contract section face, red on missing."""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
LINT = REPO / "tools" / "lint_repo_consistency.py"


def _load_lint():
    spec = importlib.util.spec_from_file_location("lrc", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_face_green_on_current_tree() -> None:
    mod = _load_lint()
    assert mod.find_missing_machine_contract_section(REPO) == []


def test_face_red_on_missing_section(tmp_path) -> None:
    mod = _load_lint()
    fake = tmp_path / "skills" / "shenbi-writing-skills"
    fake.mkdir(parents=True)
    fake.joinpath("SKILL.md").write_text("# writing skills\n\n(no section)\n", encoding="utf-8")
    assert mod.find_missing_machine_contract_section(tmp_path) == [
        "writing-skills: machine-contract section missing (spec #90)"
    ]
```

Run: `uv run pytest tests/unit/test_lint_repo_consistency_writing_skills.py -q` + `uv run python tools/lint_repo_consistency.py; echo exit=$?`
Expected: 测试 2 PASS（绿态+红态）；lint 本体 exit 0

- [ ] **Step 7: Commit**

```bash
git add tools/contract_prose_allowlist.json tools/lint_contract_prose.py skills/shenbi-writing-skills/SKILL.md tools/lint_repo_consistency.py tests/unit/tools/test_lint_contract_prose.py tests/unit/test_lint_repo_consistency_writing_skills.py
git commit -m "feat: spec #90 T4a+T4 附带——contract_prose allowlist 迁 JSON（fail-loud+未知键 FAIL+未命中 WARN）+writing-skills 机器契约节+lint_repo_consistency 缺节红面"
```

---

### Task 5: AC1 编辑面演练（弃子 commit+revert）+ 全 AC 汇跑

**复杂度: infra**（验收编排）｜ **test_kind: regression_guard**

**Files:**
- 无持久文件改动（演练弃子 commit 后 revert）

- [ ] **Step 1: 演练——给 GENERIC_ONLY_ROSTER 内技能挂 checker（4 处编辑）**

选 `shenbi-anchor-curate`（GENERIC_ONLY_ROSTER 首项）。做 4 处编辑：
1. 新建 `src/shenbi/gates/g4/anchor_curate.py`（最小 checker：复制一个现有薄 checker 结构，如 foreshadowing_lifecycle 的模块骨架，函数名 `g4_anchor_curate`）；
2. `src/shenbi/gates/shared.py` 权威集合加一行 `"shenbi-anchor-curate",`；
3. `src/shenbi/gates/g4/generic.py` `build_checkers` 加 wiring 行 `checkers["shenbi-anchor-curate"] = g4_anchor_curate`（+import）；
4. `src/shenbi/gates/shared.py` GENERIC_ONLY_ROSTER 删 `"shenbi-anchor-curate",` 行。

**SHORT_MAP/G4_CHECKER_SKILLS 零编辑**（派生自动）。

- [ ] **Step 2: 演练验证（名册面全自动通过）**

Run（三命令**分号分隔**——首个 pytest 预期红是守卫生效证据，`&&` 链会短路吞掉后两条）:
`uv run pytest tests/unit/gates/g4/test_build_checkers.py -q ; uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume ; echo exit=$? ; uv run python -c "from shenbi.gates.shared import G4_CHECKER_KEYS; print('anchor-curate' in {k.removeprefix('shenbi-') for k in G4_CHECKER_KEYS})"`
Expected: ①pytest **红**（`test_build_checkers_returns_thirty` 的 `len==30` 硬编码对 31 项红——**红=运行时守卫生效的证据**，记录之）②lint **R3 stale 行属预期**（演练再编辑 shared.py/generic.py 所致 `_tool_hashes` 漂移——**名册面零红**即通过：无 extraction-empty/无 missing-checkers 类新违规；演练 revert 后树还原 R3 自复绿，不重锁）③`True`（派生名册含新技能）。三态齐=AC1 通过判据。

- [ ] **Step 3: revert 演练 commit**

```bash
git add src/shenbi/gates/g4/anchor_curate.py src/shenbi/gates/shared.py src/shenbi/gates/g4/generic.py
git commit -m "test: spec #90 AC1 演练——anchor-curate 挂 checker（4 处编辑，名册面零手工）"
git revert HEAD --no-edit
```

- [ ] **Step 4: 汇跑 AC1-6 全部命令**（逐条粘贴输出进 `.superpowers/sdd/progress.md` 的 `## 验收证据` 节——SDD 工作态文件，非 docs 交付物）

Run: AC2 grep（Task 2 Step 6b 同款）+ AC3 AST 断言测试 + AC4 值集红测 `uv run pytest tests/unit/test_lint_decisions_sources.py::test_value_set_drift_red -q` + AC5 双态 `uv run pytest tests/unit/test_lint_repo_consistency_writing_skills.py -q` + `just check`
Expected: 全绿

- [ ] **Step 5: Commit（若有残余测试文件）**

```bash
git add <如演练产出验证记录文件——预期无>
git commit -m "test: spec #90 AC1 编辑面演练验证（4 处编辑名册面零手工）+revert"
```

---

## Self-Review

1. **Spec coverage**：T1→Task 2、T2→Task 1+2、T3→Task 3、T4a→Task 4 前半、T4 附带→Task 4 后半、T4b→排期外（spec 声明束4 后，无 task ✓）、AC1-7→覆盖表全映射 ✓。风险节三项（SHORT_MAP 不等 override→已 runtime 验证 30/30 不会触发；T1 载体验收锚→Task 2 Step 6；T2 同批→Task 1/2 施工序+原子 commit 设计 ✓）。
2. **Placeholder scan**：Task 3 Step 1 二测有「实现后精化」标注——已声明精化时点与判据（红测先行以 import 缺失红为准），非 TBD；Task 4 G0 子门编号「施工时校准」——已声明校准源（shenbi-validate G0 实况），非虚构。其余无 TBD/TODO。
3. **Type consistency**：`_checker_keys(repo: Path) -> set[str]` 全 plan 一致；`G4_CHECKER_KEYS: frozenset[str]`（权威）/`G4_CHECKER_SKILLS`（别名）在 Task 2 产出面与 Task 5 演练消费面一致；`load_allowlist() -> tuple[tuple[str, str, str], ...]` 与消费点 ALLOWLIST 名一致；`derive_stem_to_skill() -> dict[str, str]` 一致。
