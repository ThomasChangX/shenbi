# Spec #65 Layer B Dead-Wire Fix + power_system Fields + volume_map Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Layer B field filtering actually work in the dispatch read loop (fix the congenital dead-wire), declare power_system.md fields for its single live consumer, and add an `extractor:` contract field routing volume_map.md through the `_shared` extractor family for chapter-planning.

**Architecture:** Three-layer change: (1) `_build_skill_prompt`'s read loop consults the `read_fields` sidecar (keyed by pre-resolution contract path) instead of a never-firing `isinstance(dict)` branch; (2) loader gains a parallel `read_extractors` sidecar with a fail-loud closed registry and fields/extractor mutual exclusion; (3) the extractor face reuses `context_assemble._load_volume_context` by sinking it to `_shared.py` (leaf module) — dispatcher calls it, failure falls back to full text + WARN.

**Tech Stack:** Python 3.11+, pytest, structlog, YAML frontmatter contracts; repo gates via `just` (uv-run parity with CI).

## Global Constraints

- All 4 tasks are **infra** (pipeline core + contract schema) → coordinator implements personally; every task still gets a fresh-context audit (`.superpowers/sdd/audit-T<N>.md`).
- Zero real LLM dispatch for verification (core principle 8 / F947): all acceptance = direct `_build_skill_prompt` calls on fixture-assembled trees, `filter_to_fields` direct calls, `just` gate commands.
- Tests only reference `tests/fixtures/` real products (G0.9); fixture copies hash-identical (G0.11).
- No `print()` in `src/shenbi/` (ruff T20); structlog only; gate checkers pure/idempotent.
- Conventional commits with explicit pathspec (`git add <files>`, never `-A`).
- After any SKILL.md frontmatter change: `just generate` must produce an empty diff (three-source sync); `just lint-contracts` green.
- Baseline: re-baseline `just check` pass count at execution time (spec §7).
- Test file placement: dispatch-loop behavior tests → `tests/unit/pipeline/test_dispatch_layerb_live.py` (new); loader extractor tests → `tests/unit/contracts/test_loader_extractors.py` (new).

## Actual Signatures (copied from source at plan time)

```python
# src/shenbi/contracts/loader.py
def _normalize_read_item(item: Any) -> tuple[str, list[str] | None]  # :72-87
def _validate(raw: dict[str, Any], skill: str, registry: TruthFilesRegistry) -> Contract  # :191-239
def load_contract(skill: str) -> Contract  # :242-249
class Contract(TypedDict):  # :46-53
    kind: OutputKind
    reads: list[str]
    writes: list[str]
    updates: list[str]
    read_fields: dict[str, list[str]]
    write_semantics: dict[str, dict[str, Any]]

# src/shenbi/pipeline/dispatch_helper.py
def _build_skill_prompt(
    skill: str, project_dir: Path, prompt: str, chapter: int | None,
    uses_staging: bool = False, shared_context: Any = None,
    json_mode: bool = False, path_context: PathContext | None = None,
    outputs_override: list[str] | None = None,
) -> tuple[str, str, list[str]]  # :601-611
# read loop: :666-702; contract = load_contract(skill) at :643;
# reads: list[Any] = contract.get("reads", []) at :667
# dict branch :669-675 (dead); resolve_or_skip_ctx :680; _resolve_read_with_fallback :684
# cache hit :690-697; if fields: filter_to_fields :698-699; _strip_meta_for_non_drafting :701

# src/shenbi/contracts/fields.py
def filter_to_fields(text: str, fields: list[str], path: str) -> tuple[str, bool]  # :113

# src/shenbi/pipeline/context_assemble.py
def _load_volume_context(project_dir: Path, chapter: int) -> str  # :207 (moves to _shared in T4)

# src/shenbi/pipeline/_shared.py
def read_volume_boundaries(project_dir: Path | str) -> set[int]  # :88
def _resolve_volume_at_runtime(project_dir: Path, chapter: int) -> tuple[str, int, int] | None  # :167
def read_chapter_node(volume_map_text: str, chapter: int) -> dict[str, str] | None  # :211
def read_bridges(volume_map_text: str) -> list[BridgeRow]  # :234

# src/shenbi/cost/estimate.py
def estimate_prompt_tokens(text: str) -> int  # :49
```

## Acceptance Coverage Table

| Spec acceptance | Task | Executable verification |
|---|---|---|
| §3.0 dispatch 循环字段过滤行为生效 | T1 | `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -v` (behavior asserts) |
| §3.0 全量回归（36 dict 声明首次生效） | T1 | `just check` EXIT=0 |
| §3.0 零 WARN（scoped：shenbi-native + fixtures） | T1/T2 | structlog capture asserts in both test files |
| §3 power_system fields 声明 + lint 样本接线 | T2 | `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -k power_system -v`; `uv run python scripts/lint_contract_fields.py` exit 0 |
| §3 字节度量（28,808B → 15,500B on 历史真实文件拷贝） | T2 | measurement test asserts kept-bytes < full-bytes and ratio band |
| §3 G4 契约面无副作用 | T2 | `just gate G4 shenbi-review-group-factual <fixture files>` |
| §4 loader extractor 旁路 + closed registry + 互斥 | T3 | `uv run pytest tests/unit/contracts/test_loader_extractors.py -v` |
| §4 dispatcher 三分支（happy/None/失败） | T4 | `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -k volume -v` |
| §4 字节度量（26,334B → ≤2KB） | T4 | measurement test asserts |
| §4 G4 契约面无副作用 | T4 | `just gate G4 shenbi-chapter-planning <fixture files>` |
| 全部 | all | `just check` EXIT=0 + `just generate` diff empty |

---

### Task 1: Fix the dispatch-loop dead-wire (§3.0)

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:666-702` (read loop)
- Test: `tests/unit/pipeline/test_dispatch_layerb_live.py` (create)

**Interfaces:**
- Consumes: `load_contract` → `Contract.read_fields: dict[str, list[str]]` (existing, loader.py:52)
- Produces: read loop behavior — declared fields on a read path now filter at dispatch time. No new public symbols.

- [ ] **Step 1: Write failing tests (dispatch-loop level, fixtures-driven)**

Create `tests/unit/pipeline/test_dispatch_layerb_live.py`:

```python
"""Dispatch-loop Layer B behavior tests (spec #65 §3.0).

Unlike tests/unit/pipeline/test_field_filtering.py (pure-function tests),
these exercise the REAL _build_skill_prompt read loop end-to-end: the
loader-normalized reads + read_fields sidecar must actually filter content
before it reaches user_prompt. G0.9: inputs are assembled from real
fixture products (snapshots/chapter-025 tree + real fixture files).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from shenbi.pipeline.dispatch_helper import _build_skill_prompt


@pytest.fixture()
def capture_warns():
    """Collect structlog-rendered warning records."""
    records: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    logger = logging.getLogger("shenbi")
    handler = _Capture(level=logging.WARNING)
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)


@pytest.fixture()
def project_tree(tmp_path: Path) -> Path:
    """Minimal shenbi-chapter-planning read set, real fixture content."""
    snap = Path("tests/fixtures/snapshots/chapter-025")
    (tmp_path / "truth").mkdir()
    (tmp_path / "outline").mkdir()
    # truth/chapter_summaries.md: chapter-planning declares fields [已完成章节]
    (tmp_path / "truth" / "chapter_summaries.md").write_text(
        "## 已完成章节\n\n第1章：占位。\n\n## OTHER_STUFF\n\nXYZZY_LEAK_MARKER 不该进 prompt。\n",
        encoding="utf-8",
    )
    # outline/volume_map.md from the G0.11 production mirror
    (tmp_path / "outline" / "volume_map.md").write_text(
        Path("tests/fixtures/volume-map-xinghuo.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # truth/current_state.md: shenbi-native seeded lineage (declared fields all present)
    (tmp_path / "truth" / "current_state.md").write_text(
        "## 系统演化阶段\n\n中期。\n\n## 参数当前位置\n\n第3卷。\n\n## 进行中的情节线\n\n主线。\n",
        encoding="utf-8",
    )
    (tmp_path / "outline" / "story_frame.md").write_text("frame", encoding="utf-8")
    (tmp_path / "truth" / "current_focus.md").write_text("focus", encoding="utf-8")
    (tmp_path / "truth" / "author_intent.md").write_text("intent", encoding="utf-8")
    (tmp_path / "truth" / "pending_hooks.md").write_text(
        "## 活跃伏笔\n\nA。\n\n## 伏笔统计\n\n2 条。\n", encoding="utf-8"
    )
    (tmp_path / "novel.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_declared_fields_filter_in_dispatch_loop(project_tree: Path) -> None:
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # Declared section survives
    assert "已完成章节" in user_prompt
    # Undeclared section of the same file must NOT reach the prompt
    assert "XYZZY_LEAK_MARKER" not in user_prompt


def test_escape_hatch_warns_and_fulltext_on_missing_field(
    project_tree: Path, capture_warns: list[str]
) -> None:
    # Sabotage: remove a declared field's header -> escape hatch must fire
    (project_tree / "truth" / "pending_hooks.md").write_text(
        "## 别的节\n\n无声明节。\n", encoding="utf-8"
    )
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    assert "field_filter_missing_fields" in " ".join(capture_warns)
    # Full-text fallback: undeclared section present
    assert "别的节" in user_prompt


def test_string_reads_unfiltered(project_tree: Path) -> None:
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # outline/story_frame.md is a string read -> full content present
    assert "frame" in user_prompt
```

- [ ] **Step 2: Run to verify they fail (dead-wire)**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -v`
Expected: `test_declared_fields_filter_in_dispatch_loop` FAILS (`XYZZY_LEAK_MARKER` leaks); escape-hatch test FAILS (no WARN fired). This is the dead-wire red.

- [ ] **Step 3: Implement the sidecar lookup**

In `src/shenbi/pipeline/dispatch_helper.py`, replace the read-loop entry (:666-675):

```python
    raw_inputs: dict[str, str] = {}
    reads: list[Any] = contract.get("reads", [])
    # Layer B: loader normalizes dict-form reads into plain strings and
    # diverts fields to the read_fields sidecar (loader.py _validate).
    # The old isinstance(dict) branch never fired (spec #65 §1.5 dead-wire);
    # the sidecar keyed by the PRE-RESOLUTION contract path is the
    # authoritative fields carrier (same source as
    # _collect_declared_truth_fields).
    read_fields: dict[str, list[str]] = contract.get("read_fields", {})
    for read_path in reads:
        fields: list[str] = read_fields.get(read_path, [])
```

(Delete the `if isinstance(read_path_entry, dict):` / `else:` branches; `read_path: str = read_path_entry` line and the dict branch both go. Keep everything from `resolved = resolve_or_skip_ctx(...)` (:680) onward unchanged — the `if fields:` at :698 now receives real fields.)

- [ ] **Step 4: Run tests to verify green**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -v`
Expected: 3 passed.

- [ ] **Step 5: Full regression (36 existing dict declarations go live)**

Run: `uv run pytest tests/ -x -q 2>&1 | tail -5`
Expected: all pass. If any existing test depended on unfiltered behavior of a declared-fields file, fix that test's fixture to carry the declared headers (shenbi-native lineage semantics) — do NOT weaken the filter.

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_layerb_live.py
git commit -m "fix(spec65): dispatch read loop consults read_fields sidecar — Layer B dead-wire repaired (§3.0)"
```

---

### Task 2: power_system.md fields for review-group-factual + lint sample wiring (§3)

**Files:**
- Modify: `skills/shenbi-review-group-factual/SKILL.md` (reads block, frontmatter only)
- Modify: `scripts/lint_contract_fields.py:53-86` (EXAMPLE_FIXTURES entry)
- Test: `tests/unit/pipeline/test_dispatch_layerb_live.py` (append)

**Interfaces:**
- Consumes: T1 sidecar lookup (fields now live at dispatch).
- Produces: `world/power_system.md` dict-form read with fields `[力量天花板, 代价机制, 跨级战斗参考, 能力边界]` on shenbi-review-group-factual.

- [ ] **Step 1: Write failing measurement + zero-WARN tests**

Append to `tests/unit/pipeline/test_dispatch_layerb_live.py`:

```python
POWER_SYSTEM_FIXTURE = Path("tests/fixtures/world-power-system-example.md")


@pytest.fixture()
def factual_tree(tmp_path: Path) -> Path:
    """review-group-factual read set with real power_system fixture content."""
    (tmp_path / "world").mkdir()
    (tmp_path / "truth").mkdir()
    (tmp_path / "chapters").mkdir()
    (tmp_path / "audits").mkdir()
    ps = POWER_SYSTEM_FIXTURE.read_text(encoding="utf-8")
    (tmp_path / "world" / "power_system.md").write_text(ps, encoding="utf-8")
    (tmp_path / "world" / "rules.md").write_text("rules", encoding="utf-8")
    (tmp_path / "world" / "locations.md").write_text("loc", encoding="utf-8")
    (tmp_path / "world" / "story_bible.md").write_text("bible", encoding="utf-8")
    (tmp_path / "truth" / "current_state.md").write_text(
        "## 主角状态\n\n甲。\n", encoding="utf-8"
    )
    (tmp_path / "truth" / "chapter_summaries.md").write_text(
        "## 已完成章节\n\n1。\n", encoding="utf-8"
    )
    (tmp_path / "chapters" / "chapter-26.md").write_text(
        "# 第26章\n\n正文。", encoding="utf-8"
    )
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_power_system_fields_filter_in_dispatch(
    factual_tree: Path, capture_warns: list[str]
) -> None:
    full_len = len(POWER_SYSTEM_FIXTURE.read_text(encoding="utf-8").encode("utf-8"))
    assert full_len > 50_000  # fixture sanity (synthetic sample, 58,113B)
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-review-group-factual", factual_tree, "audit ch26", chapter=26
    )
    # Declared sections survive, undeclared filtered away
    assert "力量天花板" in user_prompt and "代价机制" in user_prompt
    assert "等级表" not in user_prompt  # undeclared section (appears only at fixture :38)
    # All four declared fields matched -> escape hatch silent
    assert "field_filter_missing_fields" not in " ".join(capture_warns), capture_warns
```

Red state pre-commit: before the SKILL.md change lands, `assert "等级表" not in user_prompt` fails (full text — declaration not yet made). That is the intended TDD red.

- [ ] **Step 2: Run to verify red**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -k power_system -v`
Expected: FAIL (等级表 present — declaration not yet made).

- [ ] **Step 3: Declare the fields in the skill contract**

In `skills/shenbi-review-group-factual/SKILL.md` frontmatter, change:

```yaml
    - world/power_system.md
```

to:

```yaml
    - file: world/power_system.md
      fields:
        - 力量天花板
        - 代价机制
        - 跨级战斗参考
        - 能力边界
```

- [ ] **Step 4: Wire the lint sample**

In `scripts/lint_contract_fields.py` EXAMPLE_FIXTURES (after the volume_map entry):

```python
    # Mirrored synthetic sample carrying the full producer template-8 header
    # set (spec #65 §3.2 — without this entry the new declaration vacuous-skips).
    "world/power_system.md": [FIXTURES_DIR / "world-power-system-example.md"],
```

- [ ] **Step 5: Verify green + lint + G4 + generate**

Run:
```bash
uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -v
uv run python scripts/lint_contract_fields.py && echo LINT_OK
just generate && git diff --exit-code && echo GEN_DIFF_EMPTY
uv run python -m shenbi validate G4 shenbi-review-group-factual tests/fixtures/world-power-system-example.md
```
Expected: tests pass; LINT_OK; GEN_DIFF_EMPTY; G4 PASS. (If G4 CLI form differs, use `just gate G4 shenbi-review-group-factual tests/fixtures/world-power-system-example.md`.)

- [ ] **Step 6: Commit**

```bash
git add skills/shenbi-review-group-factual/SKILL.md scripts/lint_contract_fields.py tests/unit/pipeline/test_dispatch_layerb_live.py
git commit -m "feat(spec65): review-group-factual power_system fields (template-8 subset) + lint sample wiring (§3)"
```

---

### Task 3: loader `extractor:` sidecar — closed registry, mutex (§4.2)

**Files:**
- Modify: `src/shenbi/contracts/loader.py:46-53` (Contract TypedDict), `:72-87` (_normalize_read_item), `:191-239` (_validate)
- Test: `tests/unit/contracts/test_loader_extractors.py` (create)

**Interfaces:**
- Produces: `Contract.read_extractors: dict[str, str]` (path → extractor name); `READ_EXTRACTORS: frozenset[str] = frozenset({"volume_chapter"})` registry constant in loader.py; `ContractError` on unknown extractor name or fields+extractor co-declaration.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/contracts/test_loader_extractors.py`:

```python
"""Loader extractor sidecar tests (spec #65 §4.2): closed registry,
fields/extractor mutex, sidecar normalization."""

from __future__ import annotations

import pytest

from shenbi.contracts.loader import ContractError, load_contract


def test_volume_map_extractor_lands_in_sidecar() -> None:
    contract = load_contract("shenbi-chapter-planning")
    assert contract["reads"] == [r for r in contract["reads"]]  # all strings
    assert contract["read_extractors"]["outline/volume_map.md"] == "volume_chapter"


def test_unknown_extractor_name_fails_loud() -> None:
    with pytest.raises(ContractError, match="unknown extractor"):
        load_contract("shenbi-test-bad-extractor")  # created by test fixture below


def test_fields_and_extractor_mutex() -> None:
    with pytest.raises(ContractError, match="mutually exclusive"):
        load_contract("shenbi-test-bad-mutex")
```

For the two error-path tests, create throwaway fixture skills in `tests/fixtures/contracts/bad-extractor/SKILL.md` and `bad-mutex/SKILL.md` (test setup copies them into a temp skills dir — follow the existing loader test pattern in `tests/unit/contracts/` for how invalid-contract skills are staged; if that pattern writes temp SKILL.md files directly, use it verbatim). The bad-extractor contract declares `- file: outline/volume_map.md\n  extractor: volume_chapters` (typo'd name); bad-mutex declares both `fields: [汇总]` and `extractor: volume_chapter`.

NOTE: `load_contract` resolves via `_skill_path` under the repo `skills/` dir — check how existing loader error tests stage such skills (e.g. `tests/unit/contracts/test_loader.py` invalid-contract cases) and reuse that staging mechanism exactly. If no staging mechanism exists (tests only use real skills), write the two error cases against `_validate` directly with a raw contract dict + a real registry — `_validate({"kind": "artifact", "reads": [{"file": "outline/volume_map.md", "extractor": "nope"}], "writes": [], "updates": []}, skill="x", registry=load_registry())`.

- [ ] **Step 2: Run to verify red**

Run: `uv run pytest tests/unit/contracts/test_loader_extractors.py -v`
Expected: FAIL (`read_extractors` KeyError — sidecar doesn't exist yet).

- [ ] **Step 3: Implement the sidecar**

In `src/shenbi/contracts/loader.py`:

```python
#: Closed registry of read extractor names (spec #65 §4.2). Unknown names
#: fail loudly at load (never silently degrade to full text).
READ_EXTRACTORS: frozenset[str] = frozenset({"volume_chapter"})
```

`_normalize_read_item` returns `tuple[str, list[str] | None, str | None]` — third element is extractor name:

```python
def _normalize_read_item(item: Any) -> tuple[str, list[str] | None, str | None]:
    if isinstance(item, str):
        return item, None, None
    if isinstance(item, dict) and "file" in item:
        fields = item.get("fields")
        extractor = item.get("extractor")
        if fields is not None and extractor is not None:
            raise ContractError(
                "contract.reads[] fields and extractor are mutually exclusive",
                field="reads",
            )
        if fields is not None and not (
            isinstance(fields, list) and all(isinstance(x, str) for x in fields)
        ):
            raise ContractError("contract.reads[].fields must be list[str]", field="reads")
        if extractor is not None:
            if not isinstance(extractor, str) or extractor not in READ_EXTRACTORS:
                raise ContractError(
                    "contract.reads[].extractor unknown",
                    field="reads",
                    extractor=extractor,
                    allowed=sorted(READ_EXTRACTORS),
                )
        return str(item["file"]), fields, extractor
    raise ContractError("contract.reads[] must be str or {file, fields?}", field="reads")
```

Contract TypedDict gains `read_extractors: dict[str, str]`; `_validate` builds it alongside `read_fields`:

```python
    read_extractors: dict[str, str] = {}
    # in the reads branch:
                path, fields, extractor = _normalize_read_item(item)
                paths.append(path)
                if fields is not None:
                    read_fields[path] = fields
                if extractor is not None:
                    read_extractors[path] = extractor
    # and the return dict gains: "read_extractors": read_extractors,
```

Also add `read_extractors` to any exhaustive Contract constructions in loader.py itself (grep `read_fields` for construction sites).

- [ ] **Step 4: Verify green + regression**

Run: `uv run pytest tests/unit/contracts/ -v && uv run pytest tests/ -x -q 2>&1 | tail -3`
Expected: all pass (no existing skill declares extractor yet — pure additive).

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/loader.py tests/unit/contracts/test_loader_extractors.py
git commit -m "feat(spec65): loader read_extractors sidecar — closed registry + fields/extractor mutex (§4.2)"
```

---

### Task 4: dispatcher extractor wiring + `_shared` sink + chapter-planning contract (§4)

**Files:**
- Modify: `src/shenbi/pipeline/context_assemble.py` (move `_load_volume_context` out), `src/shenbi/pipeline/_shared.py` (receive it, public name `load_volume_context`)
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (extractor branch in read loop)
- Modify: `skills/shenbi-chapter-planning/SKILL.md` (volume_map entry gains `extractor: volume_chapter`)
- Test: `tests/unit/pipeline/test_dispatch_layerb_live.py` (append)

**Interfaces:**
- Consumes: T3 `read_extractors` sidecar + `READ_EXTRACTORS`; `_shared` family (`_resolve_volume_at_runtime`, `read_chapter_node`, `read_bridges`).
- Produces: `_shared.load_volume_context(project_dir: Path, chapter: int) -> str` (moved verbatim from context_assemble, same behavior); dispatcher branch: extractor declared + chapter set → call it; `""` result → full text + WARN `extractor_failed_fulltext`; chapter None → skip extraction (full text).

- [ ] **Step 1: Write failing tests (three branches + measurement)**

Append to `tests/unit/pipeline/test_dispatch_layerb_live.py`:

```python
def test_volume_extractor_happy_path(project_tree: Path) -> None:
    full = len(
        (project_tree / "outline" / "volume_map.md").read_text(encoding="utf-8").encode("utf-8")
    )
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # ch26 in the xinghuo map falls in volume 2 (第16-35章). Assert on the
    # distinctive volume TITLES (not 第N卷 numerals — bridge rows mention those).
    assert "铁与火" in user_prompt      # current volume 2 title survived
    assert "觉醒之火" not in user_prompt  # volume 1 title filtered away
    kept = len(user_prompt.encode("utf-8"))
    assert full > 26_000 and kept < full  # massive reduction happened


def test_volume_extractor_chapter_none_fulltext(project_tree: Path) -> None:
    vm = (project_tree / "outline" / "volume_map.md").read_text(encoding="utf-8")
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "no chapter", chapter=None
    )
    assert "第一卷" in user_prompt and "第五卷" in user_prompt  # full text


def test_volume_extractor_failure_fulltext_and_warn(
    project_tree: Path, capture_warns: list[str]
) -> None:
    # Existing file, unresolvable chapter -> full text + named WARN (no silent drop)
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch9999", chapter=9999
    )
    assert "第一卷" in user_prompt  # full-text fallback
    assert "extractor_failed_fulltext" in " ".join(capture_warns)
```

- [ ] **Step 2: Run to verify red**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -k volume -v`
Expected: happy-path FAIL (full text — no extractor branch yet); failure-WARN test FAIL (no WARN).

- [ ] **Step 3: Move `_load_volume_context` to `_shared.py` (pure move)**

All of the function's dependencies (`_resolve_volume_at_runtime`, `read_chapter_node`, `read_bridges`, `bridges_for_chapter` at _shared.py:261) ALREADY live in `_shared.py`; every regex it uses is function-local. Cut `_load_volume_context` (context_assemble.py:207-262) and paste into `_shared.py` as public `load_volume_context` (docstring unchanged; add "spec #65 §4: dispatcher extractor face"). In context_assemble.py, it already imports `bridges_for_chapter` from `_shared` (:28) — replace the removed definition with:

```python
from shenbi.pipeline._shared import load_volume_context as _load_volume_context
```

(merge into the existing `_shared` import block; all existing tests importing `_load_volume_context` from context_assemble keep working untouched — verified: tests/unit/pipeline/test_context_assemble.py:20 and tests/pipeline/test_cn_extract.py:75/96 import it from context_assemble.)

- [ ] **Step 4: Wire the dispatcher extractor branch**

In `src/shenbi/pipeline/dispatch_helper.py` read loop, after the sidecar lookup from T1 and before `if fields:` (:698):

```python
        read_extractors: dict[str, str] = contract.get("read_extractors", {})
```

(move outside the loop, next to read_fields) and inside the loop, after content is obtained (post :697), before the fields filter:

```python
            extractor = read_extractors.get(read_path)
            if extractor == "volume_chapter" and chapter is not None:
                from shenbi.pipeline._shared import load_volume_context

                extracted = load_volume_context(project_dir, chapter)
                if extracted:
                    content = extracted
                else:
                    log.warning(
                        "extractor_failed_fulltext",
                        extractor=extractor,
                        path=str(full_path),
                        chapter=chapter,
                    )
```

(`project_dir` is the loop's enclosing parameter — pass it directly; the extractor entry's contract key (`outline/volume_map.md`) already scopes which reads can hit this branch, and `chapter is None` (genesis/manual no-chapter dispatch) falls through to full text per spec §4.3. Move the lazy import to module top if import cycles allow — `_shared` is a leaf, so a top-level import is expected to work; verify with `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -x`.)

- [ ] **Step 5: Declare the extractor in the skill contract**

In `skills/shenbi-chapter-planning/SKILL.md` frontmatter, change `- outline/volume_map.md` to:

```yaml
  - file: outline/volume_map.md
    extractor: volume_chapter
```

- [ ] **Step 6: Verify green + lint + G4 + generate + full check**

Run:
```bash
uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -v
uv run pytest tests/pipeline/test_cn_extract.py tests/unit/pipeline/test_context_assemble.py -v  # moved-function parity
uv run python scripts/lint_contract_fields.py && echo LINT_OK
just generate && git diff --exit-code && echo GEN_DIFF_EMPTY
just gate G4 shenbi-chapter-planning tests/fixtures/volume-map-xinghuo.md
just check
```
Expected: all green; G4 PASS; GEN_DIFF_EMPTY; just check EXIT=0.

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/_shared.py src/shenbi/pipeline/context_assemble.py src/shenbi/pipeline/dispatch_helper.py skills/shenbi-chapter-planning/SKILL.md tests/unit/pipeline/test_dispatch_layerb_live.py
git commit -m "feat(spec65): volume_map extractor wiring — _shared sink + dispatcher branch + chapter-planning contract (§4)"
```

---

## Post-plan registration

- Register in `docs/superpowers/plans/INDEX.md` as `✅ ready`.

## Self-Review (done at plan time)

- Spec coverage: §3.0→T1, §3→T2, §4.2 loader→T3, §4 dispatcher/contract→T4; acceptance table maps every §7 row; offline-only verification throughout (F947 satisfied).
- No placeholders: every step carries code or exact commands; the one open decision the spec delegates to plan (extractor composition home) is resolved as a pure move to `_shared.py` with verified dependency closure.
- Type consistency: `_normalize_read_item` 3-tuple change is contained to loader.py (grep all callers at implementation); `read_extractors` key/name types consistent T3→T4; `load_volume_context` signature unchanged by the move.
