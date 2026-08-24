# Spec #9 契约单一信源 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 spec #9（docs/superpowers/specs/2026-08-14-contract-single-source-design.md）的 5 条契约单一信源断裂：deps.json 闭包 lint（R1）、死契约模型删除 + defer-silence 接线（R2）、字段过滤 escape-hatch 兑现（R3）、scoring 适用性表头兼容（R4）、skills 计数同步（R5）。

**Architecture:** R1 在 tools/lint_repo_consistency.py 增加第 5 类检查（skills 目录↔deps.json 双向闭包）并补登 5 个 skill；R2 删除三个零消费者的 pydantic 契约模型（spec 明示的合法方向「删除死模型」——真实产物为 markdown 且 fixture 列名与模板不一致，模型消费方向不可行；把模型独有的 defer-silence 规则以 markdown 级检查补进 g4_chapter_planning，SKILL.md 段 7 模板已声明该规则「可自动检查」）；R3 按 AGENTS.md:87-89 权威契约改 `_filter_md`/`_filter_json`（任一声明字段缺失 → 全文 + WARN + 缺失清单；spec 原文 WARN-only 记 deviation）；R4 `load_applicability` 兼容 `| # | Dimension | <Type> Standard |` 表头；R5 三文档计数 69→74 同步。

**Tech Stack:** Python 3.11 / pytest / structlog / pydantic（仅删除）/ uv。

## Global Constraints

- 框架代码无 `print()`，用 structlog；pathlib 文件 I/O；gate 检查器纯函数幂等
- 禁手改 `just generate` 生成物；deps.json 是 sync-contracts 的 organizational 输入（手改其结构字段合法，改后须 `just generate` 幂等 diff 空）
- 测试只用 `tests/fixtures/` 真实产物（G0.9）；验证命令走 `just`/`uv run`
- Conventional commits；所有 commit 显式列文件路径（禁 `git add -A`）
- 全程禁真实 dispatch / pipeline 子命令（核心原则 8）

---

### Task 1: R1 — deps.json 闭包 lint + 登记 5 skill

**Files:**
- Modify: `tools/lint_repo_consistency.py`（新增第 5 类检查 `skill_deps_closure`）
- Modify: `tests/tiers/deps.json`（drafting prerequisites += `shenbi-foreshadowing-lifecycle`；audit prerequisites += 4 个 `shenbi-review-group-*`）
- Test: `tests/unit/test_lint_repo_consistency.py`（追加）

**Interfaces:**
- Produces: `check_skill_deps_closure(repo: Path) -> list[str]`（返回错误字符串列表，空 = 通过）；被 `main()` 以与其他检查相同的模式调用

- [ ] **Step 1: 写失败测试**

```python
class TestSkillDepsClosure:
    def test_all_registered_passes(self, tmp_path):
        from tools.lint_repo_consistency import check_skill_deps_closure
        # 完整闭包：目录与 deps.json 一致
        repo = tmp_path
        (repo / "skills" / "shenbi-alpha").mkdir(parents=True)
        (repo / "skills" / "shenbi-alpha" / "SKILL.md").write_text("x")
        (repo / "tests" / "tiers").mkdir(parents=True)
        (repo / "tests" / "tiers" / "deps.json").write_text(
            '{"t2-phases": {"p": {"prerequisites": ["shenbi-alpha"]}}}'
        )
        assert check_skill_deps_closure(repo) == []

    def test_missing_registration_fails(self, tmp_path):
        from tools.lint_repo_consistency import check_skill_deps_closure
        repo = tmp_path
        (repo / "skills" / "shenbi-beta").mkdir(parents=True)
        (repo / "skills" / "shenbi-beta" / "SKILL.md").write_text("x")
        (repo / "tests" / "tiers").mkdir(parents=True)
        (repo / "tests" / "tiers" / "deps.json").write_text('{"t2-phases": {}}')
        errs = check_skill_deps_closure(repo)
        assert len(errs) == 1
        assert "shenbi-beta" in errs[0]

    def test_deps_name_without_dir_fails(self, tmp_path):
        from tools.lint_repo_consistency import check_skill_deps_closure
        repo = tmp_path
        (repo / "skills").mkdir()
        (repo / "tests" / "tiers").mkdir(parents=True)
        (repo / "tests" / "tiers" / "deps.json").write_text(
            '{"t2-phases": {"p": {"prerequisites": ["shenbi-ghost"]}}}'
        )
        errs = check_skill_deps_closure(repo)
        assert any("shenbi-ghost" in e for e in errs)
```

（若现有测试文件用别的导入约定，跟随现有模式。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_lint_repo_consistency.py -k closure -q`
Expected: FAIL（ImportError / AttributeError）

- [ ] **Step 3: 实现 check_skill_deps_closure**

在 `tools/lint_repo_consistency.py` 中新增（模式对齐既有检查器；deps.json 收集 = 递归遍历所有 list[str] 值）：

```python
def _collect_deps_names(deps: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(deps, dict):
        for v in deps.values():
            names |= _collect_deps_names(v)
    elif isinstance(deps, list):
        for v in deps:
            if isinstance(v, str) and v.startswith("shenbi-"):
                names.add(v)
            else:
                names |= _collect_deps_names(v)
    return names


def check_skill_deps_closure(repo: Path) -> list[str]:
    """Spec #9 R1: skills/ dir <-> deps.json closure (both directions)."""
    import json
    errs: list[str] = []
    skills_dir = repo / "skills"
    dirs = {p.name for p in skills_dir.iterdir() if p.is_dir() and p.name.startswith("shenbi-")}
    deps_path = repo / "tests" / "tiers" / "deps.json"
    if not deps_path.exists():
        return [f"skills_deps_closure: deps.json not found: {deps_path}"]
    deps_names = _collect_deps_names(json.loads(deps_path.read_text(encoding="utf-8")))
    missing = sorted(dirs - deps_names)
    if missing:
        errs.append(f"skills_deps_closure: skill dirs not registered in deps.json: {missing}")
    ghost = sorted(deps_names - dirs)
    if ghost:
        errs.append(f"skills_deps_closure: deps.json names without skill dir: {ghost}")
    return errs
```

在 `main()` 里与其他检查同样调用并汇总错误。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_lint_repo_consistency.py -q`
Expected: PASS（含既有测试）

- [ ] **Step 5: 登记 5 skill（让 lint 在真实仓库通过）**

编辑 `tests/tiers/deps.json`：
- `t2-phases.drafting.prerequisites` 列表追加 `"shenbi-foreshadowing-lifecycle"`（chapter_loop.py:191 在 drafting 波派发它）
- `t2-phases.audit.prerequisites` 列表追加 `"shenbi-review-group-character"`, `"shenbi-review-group-craft"`, `"shenbi-review-group-factual"`, `"shenbi-review-group-plan"`（chapter_loop.py:209-230 在审计波派发；audit 相已列被其 supersede 的旧 review-*，风格一致）

- [ ] **Step 6: 幂等与全量验证**

Run: `just generate && git status --short tests/tiers/deps.json docs/framework/ skills/` 然后 `uv run python tools/lint_repo_consistency.py`
Expected: lint 退出码 0。若 `just generate` 重新生成了 `expected_outputs` 变化（新增 prerequisites 可能派生新 glob/路径），**提交再生成的输出**（生成物是单一信源，不回滚）；organizational 字段（prerequisites 本身）须保留。随后跑 `uv run pytest -n auto -m "not last" -q`（g5/check_gate_markers 消费 prerequisites，须全量确认零破坏——若真实 T2 轮次因此新增 G4 marker 要求，属预期行为变化，记 spec-deviations）。

- [ ] **Step 7: Commit**

```bash
git add tools/lint_repo_consistency.py tests/unit/test_lint_repo_consistency.py tests/tiers/deps.json
git commit -m "fix: skill-dir<->deps.json closure lint + register 5 missing skills (spec #9 R1, F0-02)"
```

---

### Task 2: R2 — 删除三个死契约模型 + g4 接线 defer-silence

**Files:**
- Delete: `src/shenbi/contracts/skills/chapter_planning.py`, `src/shenbi/contracts/skills/context_composing.py`, `src/shenbi/contracts/skills/volume_outlining.py`
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（新增 defer-silence 检查）
- Test: `tests/unit/gates/g4/test_chapter_planning_defer.py`（新建；若 g4 已有测试目录则跟随放置）

**Interfaces:**
- Consumes: `shenbi.gates.shared.fail/passed/resolve_input_path`（既有）
- Produces: g4_chapter_planning 新增 marker `G4.cp.s7_defer_silence:<fp>`（defer 且沉默章数≥4 而段 7 无 激活方案/ABANDON 时 fail）

- [ ] **Step 1: 确认零引用（删除安全性）**

Run: `grep -rn "contracts.skills.chapter_planning\|contracts.skills.context_composing\|contracts.skills.volume_outlining\|ChapterPlanning\|ContextComposing\|VolumeOutlining" src/ tools/ scripts/ tests/ --include='*.py' | grep -v coverage`
Expected: 仅三模型文件自身（test_skill_integration.py:188 的类名 `TestContextComposingPipelineMode` 是巧合命名，不 import 模型——打开确认）

- [ ] **Step 2: 写 defer-silence 失败测试**

```python
"""G4 chapter_planning defer-silence rule (spec #9 R2; was dead-wired in
contracts.skills.chapter_planning.ChapterPlanning._defer_silence_warning)."""
import pytest
from shenbi.gates.g4.chapter_planning import g4_chapter_planning

def _plan(hook_table: str, tail: str = "") -> str:
    # Sections 1-6 first, then section 7 (hook table), then a SINGLE section 8.
    # (Checker regex `## 7\..*?\n(?=## 8\.|\Z)` stops at the FIRST `## 8.` —
    # the hook table must be inside section 7's span.)
    head = "\n".join(f"## {i}. s" for i in range(1, 7))
    return (
        f"{head}\nchapter_role: 推进\n"
        f"## 7. 本章 hook 账\n{hook_table}\n{tail}\n## 8. 不要做\n无"
    )

GOOD_TABLE = """| ID | 操作 | 推进方式 | 沉默章数 |
|----|------|---------|---------|
| H01 | defer | 延迟原因 | 4 |
"""

class TestDeferSilence:
    def test_defer_silent4_without_activation_fails(self, tmp_path):
        f = tmp_path / "chapter-5-plan.md"
        f.write_text(_plan(GOOD_TABLE), encoding="utf-8")
        out = g4_chapter_planning([str(f)], rd=str(tmp_path))
        assert "G4.cp.s7_defer_silence" in out

    def test_defer_silent4_with_activation_passes(self, tmp_path):
        f = tmp_path / "chapter-5-plan.md"
        f.write_text(_plan(GOOD_TABLE, tail="激活方案：第 6 章通过……"), encoding="utf-8")
        out = g4_chapter_planning([str(f)], rd=str(tmp_path))
        assert "G4.cp.s7_defer_silence" not in out

    def test_defer_silent3_not_flagged(self, tmp_path):
        f = tmp_path / "chapter-5-plan.md"
        f.write_text(_plan(GOOD_TABLE.replace("| 4 |", "| 3 |")), encoding="utf-8")
        out = g4_chapter_planning([str(f)], rd=str(tmp_path))
        assert "G4.cp.s7_defer_silence" not in out

    def test_abandon_annotation_passes(self, tmp_path):
        f = tmp_path / "chapter-5-plan.md"
        f.write_text(_plan(GOOD_TABLE, tail="ABANDON：放弃此伏笔"), encoding="utf-8")
        out = g4_chapter_planning([str(f)], rd=str(tmp_path))
        assert "G4.cp.s7_defer_silence" not in out
```

（先读现有 g4_chapter_planning 全文与 shared 的输出约定，确保测试断言方式与其他 g4 测试一致——mf 非空时 fail 输出形态。）

- [ ] **Step 3: 跑测试确认失败**

Run: `uv run pytest tests/unit/gates/g4/test_chapter_planning_defer.py -q`
Expected: FAIL（marker 不存在，前 2 个断言失败）

- [ ] **Step 4: 实现 defer-silence 检查**

在 `src/shenbi/gates/g4/chapter_planning.py` 段 7 检查后追加（幂等纯检查）：

```python
# defer-silence rule (SKILL.md 段 7 可自动检查规则; spec #9 R2):
# 操作=defer 且 沉默章数 ≥ 4 的行，段 7 末尾须附激活方案或 ABANDON 标注。
s7 = _section_body(content, "## 7")  # 若无该 helper 则用现有提取方式
defer_rows = re.findall(r"\|\s*[^|]*\|\s*defer\s*\|[^|]*\|\s*(\d+)\s*\|", s7)
if any(int(n) >= 4 for n in defer_rows) and not re.search(
    r"激活方案|ABANDON", s7, re.IGNORECASE
):
    mf.append(f"G4.cp.s7_defer_silence:{fp}")
else:
    c.append({"id": "G4.cp.s7_defer_silence", "file": fp, "s": "PASS"})
```

列序按 SKILL.md EXACT 模板（ID | 操作 | 推进方式 | 沉默章数）；真实 fixture（Phase-1 占位，列名不同）不匹配正则 → 不触发，安全。

- [ ] **Step 5: 删除三个死模型**

```bash
git rm src/shenbi/contracts/skills/chapter_planning.py src/shenbi/contracts/skills/context_composing.py src/shenbi/contracts/skills/volume_outlining.py
```

确认 `src/shenbi/contracts/skills/__init__.py` 无相关导出需清理。

- [ ] **Step 6: 全量验证**

Run: `uv run pytest tests/unit/gates/g4/ tests/unit/contracts/ -q && uv run basedpyright && uv run mypy src/shenbi/`
Expected: 全 PASS

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/contracts/skills/chapter_planning.py src/shenbi/contracts/skills/context_composing.py src/shenbi/contracts/skills/volume_outlining.py src/shenbi/gates/g4/chapter_planning.py tests/unit/gates/g4/test_chapter_planning_defer.py
git commit -m "fix: delete 3 dead contract models, wire defer-silence rule into g4 (spec #9 R2, F201)"
```

---

### Task 3: R3 — 字段过滤 escape-hatch 兑现（任一缺失→全文+WARN）

**Files:**
- Modify: `src/shenbi/contracts/fields.py:55-80`（`_filter_md`、`_filter_json`）
- Test: `tests/unit/contracts/test_fields.py`（追加）

**Interfaces:**
- 不变：`filter_to_fields(text: str, fields: list[str], path: str) -> tuple[str, bool]`
- 语义变更（AGENTS.md:87-89 权威契约）：部分匹配不再返回片段，返回 `(text, False)` + WARN 含缺失清单

- [ ] **Step 1: 写失败测试**

```python
class TestPartialMatchEscapeHatch:
    def test_partial_match_returns_full_text_with_warn(self, caplog):
        from shenbi.contracts.fields import filter_to_fields
        text = "## A\na\n\n## B\nb\n\n## C\nc"
        out, matched = filter_to_fields(text, ["A", "B", "MISSING"], "x.md")
        assert matched is False
        assert out == text  # 全文回退，非片段

    def test_full_match_still_filters(self):
        from shenbi.contracts.fields import filter_to_fields
        text = "## A\na\n\n## B\nb"
        out, matched = filter_to_fields(text, ["A", "B"], "x.md")
        assert matched is True
        assert "## A" in out and "## B" in out

    def test_json_partial_returns_full_with_warn(self):
        from shenbi.contracts.fields import filter_to_fields
        out, matched = filter_to_fields('{"a": 1, "b": 2}', ["a", "z"], "x.json")
        assert matched is False
        assert '"b"' in out  # 全文回退
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/contracts/test_fields.py -k escape -q` 及新增类
Expected: FAIL

- [ ] **Step 3: 实现**

`_filter_md`：

```python
def _filter_md(text: str, fields: list[str]) -> tuple[str, bool]:
    sections = extract_h2_sections(text)
    matched: dict[str, str] = {}
    for heading, body in sections.items():
        if any(match_field(f, heading) for f in fields):
            matched[heading] = body
    missing = [f for f in fields if not any(match_field(f, h) for h in sections)]
    if missing:
        # AGENTS.md field-level reads contract: ANY declared field missing
        # -> escape hatch returns the full file + WARN (spec #9 R3 / F218).
        log.warning(
            "field_filter_missing_fields",
            missing=missing,
            matched=list(matched.keys()),
            available=list(sections.keys()),
        )
        return text, False
    return "\n\n".join(f"## {h}\n{b}" for h, b in matched.items()), True
```

`_filter_json` 同理：`missing = [f for f in fields if f not in data]`，非空 → WARN（事件 `field_filter_missing_fields`，含 missing/matched/available）→ `return text, False`。注意：`missing` 非空已涵盖原 `not matched` 全缺分支（missing=全部字段），**删除旧 `field_filter_no_match` 分支，勿留两套 WARN**。

最后一个 task（T5/T6 合并 commit 前统一跑一次）：
```bash
uv run bash tests/lock-tool-hashes.sh 2>/dev/null || uv run python tests/lock-tool-hashes.py 2>/dev/null || echo "no lock-tool-hashes runner — check deps.json _tool_hashes staleness manually"
```
`deps.json:_tool_hashes` 锁定了 `src/shenbi/scoring.py` 与 `src/shenbi/gates/g4/chapter_planning.py`（T2/T4 修改对象），且 G0 校验其完整性（g0.py:80）——必须运行 `uv run bash tests/lock-tool-hashes.sh` 刷新哈希并随对应 task 提交，否则 G0 假 FAIL。

- [ ] **Step 4: 验证**

Run: `uv run pytest tests/unit/contracts/test_fields.py -q && uv run pytest tests/unit -k "field" -q`
Expected: PASS（既有 escape-hatch 测试 `test_escape_hatch_returns_full_when_no_match` 语义不变）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/fields.py tests/unit/contracts/test_fields.py
git commit -m "fix: field filter escape hatch honors any-missing->full-text+WARN contract (spec #9 R3, F218)"
```

---

### Task 4: R4 — scoring 适用性表头兼容 `| # | Dimension |`

**Files:**
- Modify: `src/shenbi/scoring.py:72-98`（`load_applicability`）
- Test: `tests/unit/test_scoring_applicability.py`（新建或跟随既有 scoring 测试文件）

**Interfaces:**
- 不变：`load_applicability(rubric_path: str) -> dict[str, dict[str, bool]]`、`filter_dimensions_by_test_type(dimensions, rubric_path, test_type) -> list[Dimension]`
- 新增解析形态：表头 `| # | Dimension | <TestType> Standard | ...`（如 worldbuilding 的 `| # | Dimension | Bug-hunt Standard | Clean Standard |`）；行 = `| 4 | Prose quality | N/A — exempted ... | ... |`；类型键规范化 `<TestType> Standard` → 小写去 " standard"（`Bug-hunt Standard` → `bug-hunt`，与 filter 的 `test_type` 小写匹配路径一致）；scope 存 `dim <num>` 使既有 `re.findall(r"dim\s+(\d+)")` 排除路径直接生效。无 Applicability 节 → 返回 `{}` → 不过滤（豁免），维持现状。

- [ ] **Step 1: 写失败测试**

```python
"""Spec #9 R4: per-dim-row applicability tables must not be a silent no-op."""
from pathlib import Path
import textwrap

from shenbi.scoring import filter_dimensions_by_test_type, load_applicability

REPO = Path(__file__).resolve().parents[2]
WORLDBUILDING = REPO / "tests/tiers/t1-skill/shenbi-worldbuilding/rubric.md"

def _write_rubric(tmp_path, header_row, data_rows):
    body = "# r\n\n## Dimensions\n\n" + header_row + "\n" + "\n".join(data_rows) + "\n"
    p = tmp_path / "rubric.md"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return str(p)

PER_DIM_HEADER = "| # | Dimension | Bug-hunt Standard | Clean Standard |"
PER_DIM_ROWS = [
    "|---|---|---|---|",
    "| 1 | World depth | standard | standard |",
    "| 4 | Prose quality | N/A — exempted | standard |",
]

class TestPerDimRowApplicability:
    def test_real_worldbuilding_bug_hunt_excludes_dim4(self):
        dims = [{"num": 1, "name": "A", "weight": 20.0}, {"num": 4, "name": "B", "weight": 20.0}]
        out = filter_dimensions_by_test_type(dims, str(WORLDBUILDING), "bug-hunt")
        assert [d["num"] for d in out] == [1]

    def test_synthetic_per_dim_header_parsed(self, tmp_path):
        p = _write_rubric(tmp_path, PER_DIM_HEADER, PER_DIM_ROWS)
        app = load_applicability(p)
        assert app["bug-hunt"]["dim 4"] is False
        assert app["clean"]["dim 1"] is True

    def test_no_applicability_section_exempt(self, tmp_path):
        p = tmp_path / "rubric.md"
        p.write_text("# r\n\n## Dimensions\n\n| # | Dimension |\n|---|---|\n| 1 | A |\n", encoding="utf-8")
        assert load_applicability(str(p)) == {}

    def test_legacy_dimension_scope_still_parsed(self, tmp_path):
        p = _write_rubric(
            tmp_path,
            "| Dimension scope | bug-hunt | clean |",
            ["|---|---|---|", "| dim 2 | No | Yes |"],
        )
        app = load_applicability(p)
        assert app["bug-hunt"]["dim 2"] is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_scoring_applicability.py -q`
Expected: 前两个 FAIL（真实 worldbuilding 现在不过滤；合成表头解析为 {}）

- [ ] **Step 3: 实现**

`load_applicability` 重构循环体（引入 `mode: str = ""` 局部变量，两种表互斥；**per-dim 行分支必须排在 legacy 行分支之前**，否则 `cells[0]="4"` 的 per-dim 数据行会被 legacy 分支用旧 header_dims 吞掉）：

```python
# 表头分支（进入新表头时重置/设置 mode）：
if len(cells) >= 4 and cells[0] == "Dimension scope":
    mode = "legacy"
    header_dims = cells[1:]
elif len(cells) >= 3 and cells[0] == "#" and cells[1] == "Dimension":
    # Per-dim-row table (spec #9 R4 / F115):
    # | # | Dimension | <Type> Standard | ...  →  "Bug-hunt Standard" -> "bug-hunt"
    mode = "per_dim"
    header_dims = [c.removesuffix("Standard").strip().lower() for c in cells[2:]]
# 数据行分支（per_dim 在前）：
elif (
    mode == "per_dim"
    and len(cells) >= 3
    and not cells[0].startswith("---")
    and cells[0].strip().isdigit()
):
    scope = f"dim {cells[0].strip()}"
    for i, test_type in enumerate(header_dims):
        cell_val = cells[i + 2] if i + 2 < len(cells) else "Yes"
        applicability.setdefault(test_type, {})[scope] = (
            not cell_val.strip().upper().startswith("N/A")
        )
elif mode == "legacy" and len(cells) >= 4 and not cells[0].startswith("---"):
    # 原 legacy 行解析逻辑，逐字保留
```

进入新的 `## Dimension Applicability` 节时重置 `mode = ""`、`header_dims = []`（保留既有重置行为）。补充一条表头重置测试：同一文件中 legacy 表后跟 per-dim 表，两者都被正确解析。

- [ ] **Step 4: 行为半径验证（验收）**

Run: `uv run pytest tests/unit -k scoring -q && uv run pytest tests/unit/test_scoring_applicability.py -q`
Expected: PASS。另跑前后对比取证（记入 progress.md 验收证据）：

```bash
uv run python -c "
from shenbi.scoring import filter_dimensions_by_test_type, load_rubric
d = load_rubric('tests/tiers/t1-skill/shenbi-worldbuilding/rubric.md')
print('before:', [x['num'] for x in d])
print('bug-hunt after:', [x['num'] for x in filter_dimensions_by_test_type(d, 'tests/tiers/t1-skill/shenbi-worldbuilding/rubric.md', 'bug-hunt')])
"
```

Expected: after 输出不含 dim 4。

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/scoring.py tests/unit/test_scoring_applicability.py
git commit -m "fix: applicability parser recognizes per-dim-row rubric tables (spec #9 R4, F115)"
```

---

### Task 5: R5 — skills 计数同步

**Files:**
- Modify: `AGENTS.md:19`、`README.md:16,18,22,88`、`docs/skills/index.md:3,5,189`（以实际 grep 为准）

- [ ] **Step 1: 取证当前计数与漂移点**

Run: `ls -d skills/*/ | wc -l`（=74；73 shenbi-* + using-shenbi）与 `grep -rn -E '\b(67|69|68)\b' AGENTS.md README.md docs/skills/index.md`
- [ ] **Step 2: 同步计数**

统一口径：`72 functional (shenbi-*) + 2 meta (using-shenbi, shenbi-writing-skills) = 74 total`（shenbi-writing-skills 虽带 shenbi- 前缀但按既有文档口径计为 meta；functional=73−1=72）。逐处替换，保持各文档原句式。
- [ ] **Step 3: 验证**

Run: `uv run python -c "import pathlib; n=sum(1 for p in pathlib.Path('skills').iterdir() if p.is_dir()); print(n)"`
Expected: 74，与三文档一致；`uv run pytest tests/unit/test_lint_repo_consistency.py -q` 仍绿
- [ ] **Step 4: Commit**

```bash
git add AGENTS.md README.md docs/skills/index.md
git commit -m "docs: sync skills count 69->74 across three docs (spec #9 R5, F0-01)"
```

---

### Task 6: INDEX 边界注记（#9 ↔ #27/#28/#60/#61）

**Files:**
- Modify: `docs/superpowers/specs/INDEX.md`（#9 条目 + #27/#28/#60/#61 条目各加一行边界注记）

- [ ] **Step 1: 注记内容**

- #9 内容行尾追加：`——R1 闭包 lint/R4 表头兼容/R5 计数同步/R3 escape-hatch 由 #9 先行实施（PR 见归档），#60 R1 规则面/#27 rubric 适用性 lint 面/#61 计数去数字化/#28 T2 各自价值门时收窄`
- #27 内容行尾追加：`；#9 R4 已实施表头解析兼容，#27 保留 F104/F757 lint 面`
- #28 内容行尾追加：`；T2（escape-hatch）已由 #9 R3 按 AGENTS.md 语义实施，T2 价值门时核销`
- #60 内容行尾追加：`；#9 R1 已实现 skill↔deps.json 闭包 lint，R1 并入时以 #9 实现为基线扩展`
- #61 内容行尾追加：`；#9 R5 已做计数同步，#61 去数字化时直接替换`
- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/INDEX.md
git commit -m "docs: boundary notes spec #9 vs #27/#28/#60/#61 (contract single-source)"
```

---

## 验收覆盖表

| spec 验收 | task | 可执行验证 |
|---|---|---|
| R1 lint 对缺失登记报错 | T1 | `uv run pytest tests/unit/test_lint_repo_consistency.py -k closure -q` + 真实仓库 lint 退出 0 |
| R2 单源规则 | T2 | 三模型删除（grep 零引用）+ defer-silence 测试；g4 为唯一实现源 |
| R3 部分匹配 → WARN + 缺失清单（升级为全文回退，deviation） | T3 | `uv run pytest tests/unit/contracts/test_fields.py -q` |
| R4 worldbuilding bug-hunt 排除 dim4 | T4 | `uv run pytest tests/unit/test_scoring_applicability.py -q` + 前后对比命令 |
| R5 计数一致 | T5 | grep 三文档 == 目录计数 74 |

评分场景：本 plan 无需评分（纯代码/文档修复，T1-T5 全部以 pytest/只读 CLI 验证，不涉 G3.4 评分场景）。
