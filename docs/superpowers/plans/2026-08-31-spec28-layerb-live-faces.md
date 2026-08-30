# Spec #28 Layer B 存活面修复（R1-R5）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 关闭 F845/F839/F880/F844 四个存活的 fields 声明漂移 + lint fixture-only 盲区（多样本 any-match）+ lint 入 CI。

**Architecture:** lint 从 first-match 单样本升级为多样本 any-match；current_state 声明按生产树（xinghuo-ranqiong）重声明并新增生产树镜像 fixture（G0.11 哈希执法）；volume_map 两声明方改整文件读；两处死引用清理；ci.yml 加一步。

**Tech Stack:** Python 3.11+ / stdlib only（lint 脚本无三方依赖）；yaml frontmatter；just task runner。

**Spec:** `docs/superpowers/specs/2026-08-16-audit-layerb-field-reads-fix.md`（Revised 2026-08-31）

## Global Constraints

- fixture 只能是真实产物精确副本（G0.9）；镜像条目受 MIRROR_MAP sha256 执法（G0.11）
- 改 SKILL.md 契约面后必须 `just generate` 幂等 diff 为空；禁止手改生成物（deps.json/docs/）
- 每个 commit lint 必须绿（原子性约束：样本与声明同 commit）
- 验证走 `uv run` / `just`（与 CI 同构）；系统 python 结果不算证据
- conventional commits；pathspec commit（禁 git add -A）

---

### Task 1: lint 多样本 any-match 升级 + volume_map 样本填充与声明诚实化（R2 + R1 前置）

**复杂度: infra**（共享匹配语义变更，多文件）· **test_kind: tdd_red_green**

**Files:**
- Modify: `scripts/lint_contract_fields.py:112-143`（resolve_sample → resolve_samples）与 `_check_read_item`（:146-170）
- Modify: `scripts/lint_contract_fields.py:82-84`（EXAMPLE_FIXTURES volume_map 条目）
- Modify: `skills/shenbi-review-arc-payoff/SKILL.md:11-14`（去 fields）
- Modify: `skills/shenbi-foreshadowing-lifecycle/SKILL.md:10`（去 fields）
- Test: `tests/unit/skill_utils/test_lint_contract_fields.py`（新建）

**Interfaces:**
- Produces: `resolve_samples(path: str) -> list[Path]`（全部存在样本，literal + 全部候选 + 全部 glob 匹配，排序稳定）；`_check_read_item` 语义变为「声明字段命中**任一**样本即 PASS，全部样本均无命中才 FAIL，零样本 skip」

- [ ] **Step 1: 写失败测试**（新文件 `tests/unit/skill_utils/test_lint_contract_fields.py`）

```python
"""Spec #28: lint_contract_fields multi-sample any-match semantics."""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = REPO_ROOT / "scripts" / "lint_contract_fields.py"


def _load():
    spec = importlib.util.spec_from_file_location("lint_contract_fields", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolve_samples_collects_all_existing_candidates(monkeypatch, tmp_path):
    mod = _load()
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("## X\n", encoding="utf-8")
    b.write_text("## Y\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(
        mod,
        "EXAMPLE_FIXTURES",
        {"truth/current_state.md": [a, b]},
        raising=False,
    )
    samples = mod.resolve_samples("truth/current_state.md")
    assert samples == [a, b]  # both collected, not first-match


def test_resolve_samples_empty_when_none_exist(monkeypatch, tmp_path):
    mod = _load()
    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(mod, "EXAMPLE_FIXTURES", {}, raising=False)
    assert mod.resolve_samples("truth/nope.md") == []


def test_check_read_item_any_match_pass(monkeypatch, tmp_path):
    """Declaration hitting ANY sample passes (spec #28 R1 any-match)."""
    mod = _load()
    sample_a = tmp_path / "old.md"
    sample_a.write_text("## 主角状态\n", encoding="utf-8")
    sample_b = tmp_path / "prod.md"
    sample_b.write_text("## 系统演化阶段\n## 参数当前位置\n", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve_samples", lambda p: [sample_a, sample_b])
    item = {"file": "truth/current_state.md", "fields": ["系统演化阶段"]}
    assert mod._check_read_item("test-skill", item) is None


def test_check_read_item_fails_when_no_sample_matches(monkeypatch, tmp_path):
    mod = _load()
    sample = tmp_path / "s.md"
    sample.write_text("## 别的节\n", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve_samples", lambda p: [sample])
    item = {"file": "truth/current_state.md", "fields": ["系统演化阶段"]}
    issue = mod._check_read_item("test-skill", item)
    assert issue is not None and "系统演化阶段" in issue


def test_check_read_item_skips_when_zero_samples(monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "resolve_samples", lambda p: [])
    item = {"file": "truth/nothing.md", "fields": ["whatever"]}
    assert mod._check_read_item("test-skill", item) is None


def test_volume_map_sample_filled():
    """R2: the None skip hole for outline/volume_map.md is filled."""
    mod = _load()
    assert mod.EXAMPLE_FIXTURES["outline/volume_map.md"] is not None
```

- [ ] **Step 2: 跑测试确认红**

Run: `uv run pytest tests/unit/skill_utils/test_lint_contract_fields.py -v`
Expected: FAIL（`resolve_samples` 不存在 → AttributeError）

- [ ] **Step 3: 实现**

`scripts/lint_contract_fields.py` —— `resolve_sample` 整体替换为：

```python
def resolve_samples(path: str) -> list[Path]:
    """Resolve a declared path to ALL on-disk samples (spec #28 any-match).

    Collects, in order: the literal file under the project root, every
    existing curated fixture candidate, and every glob match for parametric
    paths (``N``/``NNN`` -> ``*``). Deduplicated, order-stable. A declaration
    passes if ANY sample contains the declared heading/key — real-product
    shapes vary across snapshots/projects, so any-match across all real
    samples is the correct semantics; zero samples means skip (no drift).
    """
    found: list[Path] = []
    literal = PROJECT_DIR / path
    if literal.is_file():
        found.append(literal)
    if path in EXAMPLE_FIXTURES:
        for cand in EXAMPLE_FIXTURES[path] or []:
            if cand.is_file():
                found.append(cand)
    pattern = path.replace("NNN", "*").replace("N", "*")
    for m in sorted(globmod.glob(str(PROJECT_DIR / pattern))):
        found.append(Path(m))
    # Deduplicate preserving order.
    seen: set[Path] = set()
    return [p for p in found if not (p in seen or seen.add(p))]
```

`_check_read_item` 中 `sample = resolve_sample(path)` 起的校验块整体替换为（any-match 聚合式：某字段在**全部**样本均无命中才 FAIL）：

```python
    samples = resolve_samples(path)
    if not samples:
        return None  # no representative sample -> not a drift
    declared = [f for f in fields if isinstance(f, str)]
    miss_count: dict[str, int] = {}
    sample_count = 0
    for sample in samples:
        actual = _extract_actual(path, sample)
        if actual is None:
            continue
        sample_count += 1
        for f in declared:
            if _field_unmatched(f, actual):
                miss_count[f] = miss_count.get(f, 0) + 1
    issue = None
    if sample_count:
        truly_missing = sorted(f for f, n in miss_count.items() if n == sample_count)
        if truly_missing:
            rels = ", ".join(
                str(s.relative_to(REPO_ROOT) if s.is_relative_to(REPO_ROOT) else s)
                for s in samples[:3]
            )
            issue = (
                f"{skill_name}: {path} declares fields {truly_missing} "
                f"not found in any sample ({rels})"
            )
    return issue
```

`EXAMPLE_FIXTURES` 的 volume_map 条目替换：

```python
    "outline/volume_map.md": [FIXTURES_DIR / "volume-map-xinghuo.md"],
```

同时更新模块 docstring 与 `EXAMPLE_FIXTURES` 注释中的 first-match 表述为 any-match。

- [ ] **Step 4: R2 声明诚实化（同 commit，保证 lint 绿）**

`skills/shenbi-review-arc-payoff/SKILL.md`（:11-14）：
```yaml
  - file: outline/volume_map.md
    fields:
    - volume_promise
    - arc_beats
```
→ `- outline/volume_map.md`（去 dict-form，整文件读）

`skills/shenbi-foreshadowing-lifecycle/SKILL.md:10`：
```yaml
    - {file: outline/volume_map.md, fields: [cross-volume bridges]}
```
→ `    - outline/volume_map.md`

- [ ] **Step 5: 同步生成物并跑测试**

Run: `uv run shenbi-sync-contracts && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/ && uv run pytest tests/unit/skill_utils/test_lint_contract_fields.py -v && uv run python scripts/lint_contract_fields.py`
Expected: 全 PASS / lint "All contract field declarations match truth files." exit 0

- [ ] **Step 6: Commit**

```bash
git add scripts/lint_contract_fields.py skills/shenbi-review-arc-payoff/SKILL.md skills/shenbi-foreshadowing-lifecycle/SKILL.md tests/unit/skill_utils/test_lint_contract_fields.py docs/superpowers/plans/2026-08-31-spec28-layerb-live-faces.md
git commit -m "feat: lint_contract_fields multi-sample any-match + volume_map sample fill & honest declarations (spec #28 R2)"
```

---

### Task 2: F845 生产树对账——current_state 声明/fixture/镜像/文档四位一体（R1）

**复杂度: infra**（g0.py MIRROR_MAP + 契约 + AGENTS.md）· **test_kind: tdd_red_green**

**Files:**
- Create: `tests/fixtures/truth-current_state-xinghuo.md`（`novel-output/xinghuo-ranqiong/truth/current_state.md` 的逐字节副本）
- Modify: `src/shenbi/gates/g0.py:16-27`（MIRROR_MAP 加条目）
- Modify: `scripts/lint_contract_fields.py:66-68`（current_state 候选列表加新 fixture）
- Modify: `skills/shenbi-chapter-planning/SKILL.md:7-12`、`skills/shenbi-review-continuity/SKILL.md:9-14`、`skills/shenbi-review-group-factual/SKILL.md:53`（fields 换生产树节名）
- Modify: `AGENTS.md:84`（Layer B 示例字段）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1481-1484`（注释示例字段名；改动会使 `tests/tiers/deps.json` 的 `_tool_hashes` 重锁——**须一并提交**）
- Modify: `tests/unit/pipeline/test_dispatch_helper.py:309-321, 343-371`（两个模板种子测试断言旧字段名，同 commit 更新为新字段）
- Test: `tests/unit/contracts/test_fields.py`（追加用例）

**Interfaces:**
- Consumes: Task 1 的 `resolve_samples` any-match
- Produces: 三技能新 fields = `[系统演化阶段, 参数当前位置, 进行中的情节线]`（生产树稳定 H2；「世界状态变化（第N章）」动态节不入 fields，escape-hatch 全文回退）

- [ ] **Step 1: 写失败测试**（追加到 `tests/unit/contracts/test_fields.py`）

```python
def test_production_current_state_declared_fields_hit_no_escape_hatch(monkeypatch):
    """Spec #28 R1/F845: chapter-planning's revised fields hit the production
    tree copy — non-empty output, no escape-hatch WARN (spy on structlog)."""
    from shenbi.contracts import fields as fields_mod

    prod = (
        Path(__file__).resolve().parents[2] / "fixtures" / "truth-current_state-xinghuo.md"
    )
    text = prod.read_text(encoding="utf-8")
    warns: list[str] = []
    monkeypatch.setattr(
        fields_mod.log, "warning",
        lambda event, **kw: warns.append(event),
        raising=True,
    )
    filtered, matched = fields_mod.filter_to_fields(
        text, ["系统演化阶段", "参数当前位置", "进行中的情节线"], str(prod)
    )
    assert matched is True
    assert "系统演化阶段" in filtered
    assert not warns  # no field_filter_missing_fields escape-hatch
```

（文件头补 `from pathlib import Path`；structlog 不经 stdlib caplog，须用 spy——同文件 :65-81 既有模式。）

另：`tests/unit/pipeline/test_dispatch_helper.py` 的 `test_current_state_has_declared_h2_stubs`（:309-321）与 `test_template_satisfies_check_fields_exist`（:343-371）中旧字段名 `主角状态/当前世界局势/活跃线索` 全部替换为 `系统演化阶段/参数当前位置/进行中的情节线`（D21 模板由声明并集派生，声明改则模板种子改，属预期联动）。

- [ ] **Step 2: 跑测试确认红**

Run: `uv run pytest tests/unit/contracts/test_fields.py::test_production_current_state_declared_fields_hit_no_escape_hatch -v`
Expected: FAIL（fixture 文件不存在 → FileNotFoundError）

- [ ] **Step 3: 实现（顺序执行）**

```bash
cp novel-output/xinghuo-ranqiong/truth/current_state.md tests/fixtures/truth-current_state-xinghuo.md
```

`src/shenbi/gates/g0.py` MIRROR_MAP 追加：

```python
    "tests/fixtures/truth-current_state-xinghuo.md": (
        "novel-output/xinghuo-ranqiong/truth/current_state.md"
    ),
```

`scripts/lint_contract_fields.py` current_state 候选列表改为：

```python
    "truth/current_state.md": [
        FIXTURES_DIR / "snapshots" / "chapter-025" / "truth" / "current_state.md",
        FIXTURES_DIR / "truth-current_state.md",
        FIXTURES_DIR / "truth-current_state-xinghuo.md",
    ],
```

三个 SKILL.md 的 `truth/current_state.md` fields 全部替换为：

```yaml
    fields:
    - 系统演化阶段
    - 参数当前位置
    - 进行中的情节线
```

（factual 的 inline 形式：`{file: truth/current_state.md, fields: [系统演化阶段, 参数当前位置, 进行中的情节线]}`）

`AGENTS.md:84` 示例：`fields: [主角状态, 当前世界局势, 活跃线索]` → `fields: [系统演化阶段, 参数当前位置, 进行中的情节线]`

`src/shenbi/pipeline/dispatch_helper.py:1482-1484` 注释中 `truth/current_state.md [主角状态, 当前世界局势, 活跃线索]` → `[系统演化阶段, 参数当前位置, 进行中的情节线]`

- [ ] **Step 4: 验证（测试 + lint + 镜像 + 生成物重锁）**

Run: `uv run pytest tests/unit/contracts/test_fields.py tests/unit/pipeline/test_dispatch_helper.py -v && uv run python scripts/lint_contract_fields.py && uv run python tools/check_fixture_mirror.py && uv run shenbi-sync-contracts && git status --short tests/tiers/deps.json`
Expected: 测试全 PASS / lint exit 0 / mirror OK / deps.json 仅 `_tool_hashes` 中 dispatch_helper.py 哈希变化（dispatch_helper.py 注释改动所致，预期内，随 Step 5 提交）

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/truth-current_state-xinghuo.md src/shenbi/gates/g0.py scripts/lint_contract_fields.py skills/shenbi-chapter-planning/SKILL.md skills/shenbi-review-continuity/SKILL.md skills/shenbi-review-group-factual/SKILL.md AGENTS.md src/shenbi/pipeline/dispatch_helper.py tests/unit/contracts/test_fields.py tests/unit/pipeline/test_dispatch_helper.py tests/tiers/deps.json
git commit -m "fix: reconcile current_state fields declarations to production tree + mirrored fixture (spec #28 R1/F845)"
```

---

### Task 3: F880 幻影键 + F844 死引用清理（R3+R4）

**复杂度: leaf** · **test_kind: regression_guard**

**Files:**
- Modify: `skills/shenbi-style-polishing/SKILL.md:49`（DOT 去 prohibitions）
- Modify: `skills/shenbi-review-pacing/SKILL.md:93`（引用改内联说明）

- [ ] **Step 1: style-polishing DOT 节点**

`"Read genre-config.json (fatigueWords + prohibitions)"` → `"Read genre-config.json (fatigueWords)"`

- [ ] **Step 2: review-pacing 引用行**

`每条缺陷报告必须遵循 \`skills/_shared/REVIEW_EVIDENCE.md\` 定义的四要素格式：` → `每条缺陷报告必须遵循以下四要素格式：`（:95-98 的内联四要素保留）

- [ ] **Step 3: 回归断言（spec 验收 3）**

Run: `git grep -n prohibitions -- skills/shenbi-style-polishing/SKILL.md; git grep -n REVIEW_EVIDENCE -- skills/; uv run shenbi-sync-contracts && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/`
Expected: 两个 grep 零输出；diff 空

- [ ] **Step 4: Commit**

```bash
git add skills/shenbi-style-polishing/SKILL.md skills/shenbi-review-pacing/SKILL.md
git commit -m "fix: remove phantom prohibitions key from style-polishing DOT and dead REVIEW_EVIDENCE reference (spec #28 R3+R4)"
```

---

### Task 4: lint_contract_fields 入 CI（R5）

**复杂度: leaf** · **test_kind: regression_guard**

**Files:**
- Modify: `.github/workflows/ci.yml:53-57`（Contract lints run 块）

- [ ] **Step 1: 加一步**（"Contract + repo-consistency lints" 块内加一行，或紧随其后新步）

```yaml
      - name: Contract + repo-consistency lints (spec §5.5)
        run: |
          uv run python tools/lint_contracts.py
          uv run python scripts/lint_contract_fields.py
          uv run python tools/lint_repo_consistency.py
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run lint_contract_fields in quality workflow (spec #28 R5)"
```

（R5 验收 4 由 PR CI 实跑证明——改动即触发 ci workflow。）

---

### Task 5: 验收收口 + 全量门禁

**复杂度: infra** · **test_kind: regression_guard**

- [ ] **Step 1: spec 验收 1-5 逐条实跑并粘贴输出到 progress.md**
  1. `uv run python scripts/lint_contract_fields.py` exit 0（基准含生产树副本）
  2. `uv run pytest tests/unit/contracts/test_fields.py -v`（F845 断言 PASS）
  3. 两个 grep 零输出（Task 3 已跑，重跑粘贴）
  4. CI 含 lint step（PR checks 展示）
  5. `just check` 全绿 + `uv lock --check` 不适用（未改依赖）

- [ ] **Step 2: Commit（若有收尾改动）** + 更新 progress.md 验收证据
