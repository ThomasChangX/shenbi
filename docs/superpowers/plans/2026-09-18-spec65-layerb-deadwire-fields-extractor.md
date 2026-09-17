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
- Test file placement: dispatch-loop behavior tests → `tests/unit/pipeline/test_dispatch_layerb_live.py` (new; deviation from spec §3.0's literal mention of test_field_filtering.py — that file is pure-function scoped by its own docstring, new dispatch-loop cases get a dedicated file; logged in spec-deviations); loader extractor tests → `tests/unit/contract/test_loader_extractors.py` (create; note the directory is `tests/unit/contract/` SINGULAR, existing home of test_dict_reads.py).
- All new test files carry `pytestmark = pytest.mark.unit` (pyproject markers: unit/integration/property/benchmark/slow/last; `just test` selects `-m unit`).
- structlog in this repo writes via `PrintLoggerFactory(file=sys.stderr)` (logging.py:52) — stdlib logging handlers CANNOT capture events. WARN assertions use the repo's spy pattern (tests/unit/contracts/test_fields.py:71-83): monkeypatch `log.warning` on the emitting module. `field_filter_missing_fields` is emitted from `shenbi.contracts.fields`'s module logger; `extractor_failed_fulltext` from `shenbi.pipeline.dispatch_helper`'s.
- AGENTS.md Layer B face: after T1 the existing AGENTS.md claim ("The dispatcher filters file content...") becomes TRUE — no AGENTS.md edit needed; listed here per spec §6.2.
- 36-declaration blast radius (spec §6.1 duty): at-risk set = `truth/current_state.md` family (chapter-planning + review-continuity declare [系统演化阶段, 参数当前位置, 进行中的情节线]; zero overlap with chapter-025 snapshot lineage, 3/3 with xinghuo sample — miss → escape-hatch fulltext, correct behavior per spec §8.2 lineage exemption). T1 Step 5's full regression is the enforcement; no repo test today dispatches chapter-planning against a foreign-lineage current_state (verified by grep at plan time).

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
| §3.0 零 WARN（scoped：shenbi-native + fixtures） | T1/T2 | spy-based WARN asserts in test_dispatch_layerb_live.py (both T1 escape-hatch-negative and T2 zero-WARN cases) |
| §3 power_system fields 声明 + lint 样本接线 | T2 | `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -k power_system -v`; `uv run python scripts/lint_contract_fields.py` exit 0 |
| §3 字节度量（合成 fixture 58,113B → 27,807B kept（4-field, 47.8%）；spec §7 的 15,500B 为历史真实文件口径，测试用合成 fixture 同断言形态） | T2 | measurement test asserts ratio band via baseline subtraction |
| §3 G4 契约面无副作用 | T2 | `uv run shenbi-validate G4 shenbi-review-group-factual "$(pwd)/tests/fixtures/world-power-system-example.md"` |
| §4 loader extractor 旁路 + closed registry + 互斥 | T3 | `uv run pytest tests/unit/contract/test_loader_extractors.py -v` |
| §4 dispatcher 三分支（happy/None/失败） | T4 | `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -k volume -v` |
| §4 字节度量（26,334B → ≤2KB） | T4 | measurement test asserts |
| §4 G4 契约面无副作用 | T4 | `uv run shenbi-validate G4 shenbi-chapter-planning "$(pwd)/tests/fixtures/chapter-plan-example.md"` |
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
fixture products (real fixture file contents; trivial declared-header
seeding only).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.contracts import fields as fields_mod
from shenbi.pipeline import dispatch_helper as dh
from shenbi.pipeline.dispatch_helper import _build_skill_prompt

pytestmark = pytest.mark.unit


@pytest.fixture()
def warn_spy(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Spy WARN events on both emitting module loggers (repo structlog
    writes via PrintLoggerFactory — stdlib handlers see nothing; this is
    the tests/unit/contracts/test_fields.py:71-83 pattern applied to both
    emitters: fields module -> field_filter_missing_fields; dispatch_helper
    -> extractor_failed_fulltext)."""
    events: dict[str, list[str]] = {"fields": [], "dispatch": []}

    def _spy(bucket: list[str], orig):
        def inner(event: str, **kw: object) -> None:
            bucket.append(event)
            orig(event, **kw)

        return inner

    monkeypatch.setattr(
        fields_mod.log, "warning", _spy(events["fields"], fields_mod.log.warning)
    )
    monkeypatch.setattr(
        dh.log, "warning", _spy(events["dispatch"], dh.log.warning)
    )
    return events


@pytest.fixture()
def project_tree(tmp_path: Path) -> Path:
    """Minimal shenbi-chapter-planning read set, real fixture content."""
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
    project_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    # Sabotage: remove a declared field's header -> escape hatch must fire
    (project_tree / "truth" / "pending_hooks.md").write_text(
        "## 别的节\n\n无声明节。\n", encoding="utf-8"
    )
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    assert "field_filter_missing_fields" in warn_spy["fields"]
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
    factual_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    from shenbi.cost.estimate import estimate_prompt_tokens

    ps_full = POWER_SYSTEM_FIXTURE.read_text(encoding="utf-8")
    full_len = len(ps_full.encode("utf-8"))
    assert full_len > 50_000  # fixture sanity (synthetic sample, 58,113B)
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-review-group-factual", factual_tree, "audit ch26", chapter=26
    )
    # Declared sections survive, undeclared filtered away
    assert "力量天花板" in user_prompt and "代价机制" in user_prompt
    assert "等级表" not in user_prompt  # undeclared section (appears only at fixture :38)
    # All four declared fields matched -> escape hatch silent
    assert warn_spy["fields"] == [], warn_spy["fields"]
    # Spec §7 byte metric: isolate the power_system CONTRIBUTION by
    # subtracting a no-power_system baseline prompt.
    (factual_tree / "world" / "power_system.md").unlink()
    _, baseline, _ = _build_skill_prompt(
        "shenbi-review-group-factual", factual_tree, "audit ch26", chapter=26
    )
    contribution = len(user_prompt.encode("utf-8")) - len(baseline.encode("utf-8"))
    assert 4_000 < contribution < full_len * 0.75  # deep cut, bounded below
    assert estimate_prompt_tokens(user_prompt) < estimate_prompt_tokens(baseline + ps_full)
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
uv run shenbi-validate G4 shenbi-review-group-factual "$(pwd)/tests/fixtures/world-power-system-example.md"
```
Expected: tests pass; LINT_OK; GEN_DIFF_EMPTY; G4 PASS. (No `python -m shenbi` — the package has no `__main__.py`; entry point is `shenbi-validate`. `resolve_input_path` needs an ABSOLUTE path when no round_dir is given — hence `$(pwd)`.) The review-group-factual route uses the generic G4 checker; probe-verified to PASS on the power fixture (it carries frontmatter).

- [ ] **Step 6: Commit**

```bash
git add skills/shenbi-review-group-factual/SKILL.md scripts/lint_contract_fields.py tests/unit/pipeline/test_dispatch_layerb_live.py
git commit -m "feat(spec65): review-group-factual power_system fields (template-8 subset) + lint sample wiring (§3)"
```

---

### Task 3: loader `extractor:` sidecar — closed registry, mutex (§4.2)

**Files:**
- Modify: `src/shenbi/contracts/loader.py:46-53` (Contract TypedDict), `:72-87` (_normalize_read_item), `:191-239` (_validate)
- Test: `tests/unit/contract/test_loader_extractors.py` (create — directory `tests/unit/contract/` SINGULAR)

**Interfaces:**
- Produces: `Contract.read_extractors: dict[str, str]` (path → extractor name); `READ_EXTRACTORS: frozenset[str] = frozenset({"volume_chapter"})` registry constant in loader.py; `ContractError` on unknown extractor name or fields+extractor co-declaration.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/contract/test_loader_extractors.py` using the STAGED-SKILL pattern from `tests/unit/contract/test_dict_reads.py:14-29` (`_write_skill` + `monkeypatch.setattr("shenbi.contracts.loader.SKILLS", tmp_path / "skills")`). NEVER place throwaway skills under `tests/fixtures/` (G0.9 reserves it for real products):

```python
"""Loader extractor sidecar tests (spec #65 §4.2): closed registry,
fields/extractor mutex, sidecar normalization. Staged-skill pattern from
tests/unit/contract/test_dict_reads.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.contracts.loader import ContractError, load_contract

pytestmark = pytest.mark.unit


def _write_skill(root: Path, name: str, reads_yaml: str) -> None:
    skills = root / "skills"
    d = skills / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ncontract:\n  kind: report\n  reads:\n{reads_yaml}"
        "\n  writes: [audits/chapter-N-x.md]\n  updates: []\n---\n# body\n",
        encoding="utf-8",
    )  # --- delimiters REQUIRED (loader.read_frontmatter_contract rejects text
        # not starting with '---'; without them test_unknown_extractor_name_
        # fails_loud false-passes: ShenbiError.__str__ renders the skill-name
        # kwarg, and "shenbi-test-bad-extractor" matches match="extractor")


EXTRACTOR_READS = "    - {file: outline/volume_map.md, extractor: volume_chapter}\n"


def test_extractor_lands_in_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_skill(tmp_path, "shenbi-test-extractor", EXTRACTOR_READS)
    monkeypatch.setattr("shenbi.contracts.loader.SKILLS", tmp_path / "skills")
    c = load_contract("shenbi-test-extractor")
    assert all(isinstance(r, str) for r in c["reads"])
    assert c["read_extractors"] == {"outline/volume_map.md": "volume_chapter"}
    assert c["read_fields"] == {}


def test_unknown_extractor_name_fails_loud(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(
        tmp_path,
        "shenbi-test-bad-extractor",
        "    - {file: outline/volume_map.md, extractor: volume_chapters}\n",  # typo
    )
    monkeypatch.setattr("shenbi.contracts.loader.SKILLS", tmp_path / "skills")
    with pytest.raises(ContractError, match="extractor"):
        load_contract("shenbi-test-bad-extractor")


def test_fields_and_extractor_mutex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(
        tmp_path,
        "shenbi-test-bad-mutex",
        "    - {file: outline/volume_map.md, fields: [汇总], extractor: volume_chapter}\n",
    )
    monkeypatch.setattr("shenbi.contracts.loader.SKILLS", tmp_path / "skills")
    with pytest.raises(ContractError, match="mutually exclusive"):
        load_contract("shenbi-test-bad-mutex")
```

(The real chapter-planning `extractor:` declaration lands in T4 — T3's green state is fully self-contained via staged skills, no dependency on T4's SKILL.md edit.)

- [ ] **Step 2: Run to verify red**

Run: `uv run pytest tests/unit/contract/test_loader_extractors.py -v`
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

Run: `uv run pytest tests/unit/contract/test_loader_extractors.py -v && uv run pytest tests/ -x -q 2>&1 | tail -3`
Expected: all pass (no existing skill declares extractor yet — pure additive).

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/loader.py tests/unit/contract/test_loader_extractors.py
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
def test_volume_extractor_happy_path(
    project_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    from shenbi.cost.estimate import estimate_prompt_tokens

    vm_text = (project_tree / "outline" / "volume_map.md").read_text(encoding="utf-8")
    full = len(vm_text.encode("utf-8"))
    assert full > 26_000
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # ch26 in the xinghuo map falls in volume 2 (第16-35章). Assert on the
    # distinctive volume TITLES (not 第N卷 numerals — bridge rows mention those).
    assert "铁与火" in user_prompt      # current volume 2 title survived
    assert "觉醒之火" not in user_prompt  # volume 1 title filtered away
    # Spec §7: extractor_failed_fulltext appears ONLY in the failure case —
    # the happy path must be WARN-free.
    assert "extractor_failed_fulltext" not in warn_spy["dispatch"]
    # Spec §4.4/§7 byte metric: volume_map contribution must drop to the
    # ~500B-2KB band. Isolate by no-volume_map baseline subtraction.
    (project_tree / "outline" / "volume_map.md").unlink()
    _, baseline, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    contribution = len(user_prompt.encode("utf-8")) - len(baseline.encode("utf-8"))
    assert 300 < contribution <= 2_048  # spec target band (500B-2KB, CJK-tolerant floor)
    assert estimate_prompt_tokens(user_prompt) < estimate_prompt_tokens(baseline + vm_text)


def test_volume_extractor_chapter_none_fulltext(project_tree: Path) -> None:
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "no chapter", chapter=None
    )
    assert "第一卷" in user_prompt and "第五卷" in user_prompt  # full text


def test_volume_extractor_failure_fulltext_and_warn(
    project_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    # Existing file, unresolvable chapter -> full text + named WARN (no silent drop)
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch9999", chapter=9999
    )
    assert "第一卷" in user_prompt  # full-text fallback
    assert "extractor_failed_fulltext" in warn_spy["dispatch"]


def test_real_chapter_planning_contract_has_extractor() -> None:
    # T3's sidecar wired to the REAL skill contract (lands with Step 5 below)
    from shenbi.contracts.loader import load_contract

    c = load_contract("shenbi-chapter-planning")
    assert c["read_extractors"]["outline/volume_map.md"] == "volume_chapter"
```

NOTE (accepted redundancy): `load_volume_context` re-reads volume_map.md from disk (once inside itself, once inside `_resolve_volume_at_runtime` via `read_volume_boundaries`) on top of the loop's own read — three reads per dispatch. Idempotent, read-only, µs-scale on an OS page cache; accepted now, a text-parameter refactor is a future optimization (spec-deviations note).

- [ ] **Step 2: Run to verify red**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_layerb_live.py -k volume -v`
Expected: happy-path FAIL (full text — no extractor branch yet); failure-WARN test FAIL (no WARN).

- [ ] **Step 3: Move `_load_volume_context` to `_shared.py` (pure move)**

All of the function's dependencies (`_resolve_volume_at_runtime`, `read_chapter_node`, `read_bridges`, `bridges_for_chapter` at _shared.py:261) ALREADY live in `_shared.py`; every regex it uses is function-local. Cut `_load_volume_context` (context_assemble.py:207-262) and paste into `_shared.py` as public `load_volume_context` (docstring unchanged; add "spec #65 §4: dispatcher extractor face"). **Add `load_volume_context` to `_shared.__all__`** (:22-37, the module maintains it explicitly). In context_assemble.py, replace BOTH the removed definition AND the now-dead 4-name `_shared` import block (:27-30 imports `_resolve_volume_at_runtime`, `bridges_for_chapter`, `read_bridges`, `read_chapter_node` — used ONLY inside the removed function; leaving them = ruff F401 = `just check` red) with:

```python
from shenbi.pipeline._shared import load_volume_context as _load_volume_context
```

(verify with `grep -n "_resolve_volume_at_runtime\|bridges_for_chapter\|read_bridges\|read_chapter_node" src/shenbi/pipeline/context_assemble.py` — zero remaining uses expected. All existing tests importing `_load_volume_context` from context_assemble keep working untouched — verified: tests/unit/pipeline/test_context_assemble.py:20 and tests/pipeline/test_cn_extract.py:75/96 import it from context_assemble; `context_assemble.__all__` (:402) stays valid via the alias.)

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
uv run shenbi-validate G4 shenbi-chapter-planning "$(pwd)/tests/fixtures/chapter-plan-example.md"
just check
```
Expected: all green; G4 PASS; GEN_DIFF_EMPTY; just check EXIT=0.

(G4 input is a REAL chapter-plan product — `tests/fixtures/chapter-plan-example.md` — because `g4_chapter_planning` checks 8 numbered `## N.` sections + a `chapter_role` token; feeding it a volume map is a category error. Absolute path required: `resolve_input_path` raises on relative paths without a round_dir. No `python -m shenbi` form — package has no `__main__.py`.)

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
