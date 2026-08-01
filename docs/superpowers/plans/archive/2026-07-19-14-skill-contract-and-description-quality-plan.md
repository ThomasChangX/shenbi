# Skill Contract and Description Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a G0 contract-linting check for all 69 skills, extend skill frontmatter with explicit write semantics (`mode`/`no_op_behavior`/`key`), enforce declared semantics in the dispatch write path, and ship a description-compliance audit tool.

**Architecture:** Four layers. (1) A `G0.skill_contract` check (next free ID is **G0.16**) that walks every `skills/*/SKILL.md`, parses frontmatter via the existing `read_frontmatter_contract`/`yaml` loader, and reports description-length, write/update-overlap, and missing-semantics issues. (2) Extend the `contract:` block so `writes`/`updates` entries may be dicts `{file, mode, no_op_behavior?, key?}` (string entries remain valid; the new sub-fields are opt-in). (3) `_write_parsed_outputs` reads the dispatched skill's declared `mode` for each output path and routes to the matching writer. (4) A standalone `tools/audit-skill-descriptions.py` report generator. The contract YAML format already has `reads`/`writes`/`updates` (see `src/shenbi/contracts/legacy.py`); only `mode`/`no_op_behavior`/`key` sub-fields are new.

**Tech Stack:** Python 3.11+, pathlib, pyyaml, pytest, structlog

## Global Constraints

- Skill `description` MUST be ≤500 chars and contain only when-to-use trigger conditions, never behavioral description (spec §2.1, `AGENTS.md`).
- `writes:` (create new) and `updates:` (modify existing) paths MUST be disjoint per skill (spec §2.1).
- New write-semantics sub-fields (`mode`, `no_op_behavior`, `key`) live UNDER existing `contract.writes`/`contract.updates` entries as dict-form. Existing string-form entries remain valid — this is additive, not a migration (spec §3.2, and `legacy.py:_validate` already allows dict-form for `reads`).
- Valid `mode` values are a closed set: `create_or_overwrite`, `merge_prose`, `append_dedup`. `no_op_behavior` is `skip_write` (only meaningful where a no-op route exists). `key` names the dedup key column for `append_dedup` (spec §3.2).
- The next free G0 check ID is **G0.16** (G0.13 independence, G0.14 calibration hash, G0.15 gate-registry consistency are taken — confirmed in `src/shenbi/gates/g0.py`).
- Contract loading goes through the existing `shenbi.contracts` loader (`load_contract`, `read_frontmatter_contract`, `ContractError`) — do not add a second frontmatter reader (loader-uniqueness lint).
- `just check` must pass fully after each task.

---

### Task 1: G0.skill_contract checker (description + overlap + semantics)

**Files:**
- Create: `src/shenbi/gates/g0_skill_contract.py`
- Modify: `src/shenbi/gates/g0.py:594-615` (wire `G0.16` after `G0.15`, before the final `return passed`)
- Test: `tests/unit/gates/test_g0_skill_contract.py`

**Interfaces:**
- Consumes: `ALL_SKILLS`, `SKILLS` from `shenbi.gates.shared`; `read_frontmatter_contract`, `ContractError` from `shenbi.contracts.legacy`; `yaml`.
- Produces: `check_skill_contracts() -> list[str]` (issue strings, empty = pass), `_desc_has_behavioral_text(desc) -> bool`, `DESCRIPTION_MAX_CHARS = 500`. `gate_G0` calls `check_skill_contracts()` and emits `G0.16`.

**Context:** There is no automated check today that descriptions are ≤500 chars / trigger-only, that writes/updates are disjoint, or that update paths declare `mode` (spec §2.1, §2.3). The check must be tolerant: a skill whose contract raises `ContractError` is skipped (its contract issues surface in their own checks), and a description without behavioral markers passes. The `_has_behavioral_description` heuristic in the spec is loose; this implementation uses a concrete marker list (imperative openers like "This skill", "Generates", "Writes") which is deterministic and testable.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/gates/test_g0_skill_contract.py
"""Tests for G0.skill_contract check (spec §3.1)."""
from __future__ import annotations

from pathlib import Path

import yaml

from shenbi.gates.g0_skill_contract import (
    DESCRIPTION_MAX_CHARS,
    _desc_has_behavioral_text,
    check_skill_contracts,
)


def _make_skill(tmp_path: Path, name: str, body: dict) -> Path:
    """Write a synthetic skills/<name>/SKILL.md and return the skills dir."""
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True)
    fm = "---\n" + yaml.safe_dump(body, sort_keys=False) + "---\n\n# body\n"
    (skill_dir / "SKILL.md").write_text(fm, encoding="utf-8")
    return tmp_path


class TestDescriptionLength:
    def test_max_chars_is_500(self):
        assert DESCRIPTION_MAX_CHARS == 500

    def test_too_long_description_flagged(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {"name": "shenbi-x", "description": "x" * 501, "contract": {"kind": "ephemeral"}},
        )
        issues = check_skill_contracts(skills_dir)
        assert any("desc_too_long" in i for i in issues)

    def test_exactly_500_passes(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {"name": "shenbi-x", "description": "x" * 500, "contract": {"kind": "ephemeral"}},
        )
        issues = check_skill_contracts(skills_dir)
        assert not any("desc_too_long" in i for i in issues)


class TestBehavioralText:
    def test_trigger_only_passes(self):
        assert not _desc_has_behavioral_text("Use when a chapter fails the audit gate.")

    def test_behavioral_flagged(self):
        assert _desc_has_behavioral_text("This skill rewrites the chapter prose.")

    def test_generates_flagged(self):
        assert _desc_has_behavioral_text("Generates a new plot outline.")


class TestWriteUpdateOverlap:
    def test_overlap_flagged(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when y",
                "contract": {
                    "kind": "artifact",
                    "writes": ["chapters/chapter-N.md"],
                    "updates": ["chapters/chapter-N.md"],
                },
            },
        )
        issues = check_skill_contracts(skills_dir)
        assert any("write_update_overlap" in i for i in issues)

    def test_disjoint_passes(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when y",
                "contract": {
                    "kind": "artifact",
                    "writes": ["chapters/chapter-N-decisions.json"],
                    "updates": ["chapters/chapter-N.md"],
                },
            },
        )
        issues = check_skill_contracts(skills_dir)
        assert not any("write_update_overlap" in i for i in issues)


class TestMissingWriteSemantics:
    def test_update_without_mode_flagged(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when y",
                "contract": {
                    "kind": "artifact",
                    "updates": [{"file": "chapters/chapter-N.md"}],  # no mode
                },
            },
        )
        issues = check_skill_contracts(skills_dir)
        assert any("missing_write_semantics" in i for i in issues)

    def test_update_with_mode_passes(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when y",
                "contract": {
                    "kind": "artifact",
                    "updates": [
                        {"file": "chapters/chapter-N.md", "mode": "merge_prose"}
                    ],
                },
            },
        )
        issues = check_skill_contracts(skills_dir)
        assert not any("missing_write_semantics" in i for i in issues)


class TestEmptyIssuesOnCleanContract:
    def test_clean_contract_no_issues(self, tmp_path: Path):
        skills_dir = _make_skill(
            tmp_path,
            "shenbi-x",
            {
                "name": "shenbi-x",
                "description": "Use when the chapter needs revision after audit",
                "contract": {
                    "kind": "artifact",
                    "reads": ["audits/chapter-N-*.md"],
                    "writes": [
                        {"file": "chapters/chapter-N-revision-decisions.json", "mode": "create_or_overwrite"}
                    ],
                    "updates": [
                        {"file": "chapters/chapter-N.md", "mode": "merge_prose", "no_op_behavior": "skip_write"}
                    ],
                },
            },
        )
        assert check_skill_contracts(skills_dir) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/gates/test_g0_skill_contract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shenbi.gates.g0_skill_contract'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/shenbi/gates/g0_skill_contract.py
"""G0.skill_contract: validate all skill contracts + descriptions (spec §3.1).

Checks, for every skills/*/SKILL.md:
  - description <= 500 chars (AGENTS.md)
  - description is trigger-only (no behavioral "This skill does X" text)
  - writes: and updates: paths are disjoint (write=create vs update=modify)
  - every writes/updates entry declares a write mode (mode sub-field)
Issues are returned as "G0.sc.<check>:<skill>:<detail>" strings; empty == pass.
Skills whose frontmatter fails to parse are skipped (their own checks surface
those errors).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DESCRIPTION_MAX_CHARS = 500

# Imperative/behavioral openers that indicate the description describes what
# the skill DOES rather than when to USE it. Deterministic, not a full NLP
# heuristic — keeps the check cheap and the failures explainable.
_BEHAVIORAL_MARKERS = [
    # English
    "this skill",
    "this module",
    "generates ",
    "writes ",
    "creates ",
    "validates ",
    "checks ",
    "analyzes ",
    "computes ",
    "extracts ",
    # Chinese
    "该技能",
    "该模块",
    "生成",
    "写入",
    "创建",
    "验证",
    "检查",
    "分析",
    "计算",
    "提取",
    "产出",
    "输出",
    "读取",
    "审计",
]


def _desc_has_behavioral_text(desc: str) -> bool:
    """True if the description reads as behavioral ('does X') not trigger ('use when Y')."""
    lowered = desc.lstrip().lower()
    return any(lowered.startswith(m) for m in _BEHAVIORAL_MARKERS)


def _parse_frontmatter(skill_md: Path) -> dict[str, Any] | None:
    """Parse SKILL.md frontmatter using the existing contract loader.
    Returns None (skip) on any ContractError, keeping the tolerant behavior.
    """
    from shenbi.contracts.legacy import read_frontmatter_contract
    try:
        return read_frontmatter_contract(skill_md)
    except Exception:
        return None


def _normalize_paths(entries: list[Any]) -> list[tuple[str, dict[str, Any]]]:
    """Normalize writes/updates entries to [(path, meta_dict)].

    Accepts plain strings ("path") or dicts ({"file": "path", "mode": ...}).
    """
    out: list[tuple[str, dict[str, Any]]] = []
    for e in entries or []:
        if isinstance(e, str):
            out.append((e, {}))
        elif isinstance(e, dict) and "file" in e:
            meta = {k: v for k, v in e.items() if k != "file"}
            out.append((str(e["file"]), meta))
    return out


def check_skill_contracts(skills_dir: Path | None = None) -> list[str]:
    """Validate all skill SKILL.md files. Returns issue strings (empty == pass).

    Args:
        skills_dir: directory containing skill subdirs. Defaults to the
            project skills/ dir (shenbi.gates.shared.SKILLS).
    """
    if skills_dir is None:
        from shenbi.gates.shared import SKILLS

        skills_dir = SKILLS

    issues: list[str] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_md.parent.name
        fm = _parse_frontmatter(skill_md)
        if fm is None:
            continue  # malformed frontmatter surfaces in its own checks

        desc = str(fm.get("description", ""))
        if len(desc) > DESCRIPTION_MAX_CHARS:
            issues.append(f"G0.sc.desc_too_long:{skill_name}:{len(desc)}")
        if desc and _desc_has_behavioral_text(desc):
            issues.append(f"G0.sc.desc_has_behavior:{skill_name}")

        contract = fm.get("contract")
        if not isinstance(contract, dict):
            continue  # missing contract surfaces in its own checks

        writes = _normalize_paths(contract.get("writes", []))
        updates = _normalize_paths(contract.get("updates", []))

        # writes / updates disjoint
        write_paths = {p for p, _ in writes}
        update_paths = {p for p, _ in updates}
        overlap = write_paths & update_paths
        if overlap:
            issues.append(f"G0.sc.write_update_overlap:{skill_name}:{sorted(overlap)}")

        # every write/update entry must declare a mode (semantics)
        for path, meta in writes + updates:
            if "mode" not in meta:
                issues.append(f"G0.sc.missing_write_semantics:{skill_name}:{path}")

    return issues
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/gates/test_g0_skill_contract.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Wire G0.16 into gate_G0**

In `src/shenbi/gates/g0.py`, immediately before the final `return passed("G0", checks)` (after the G0.15 block), add:

```python
    # G0.16 — skill contract + description quality (spec §3.1). Validates every
    # skills/*/SKILL.md: description <= 500 chars and trigger-only, writes/
    # updates disjoint, write semantics (mode) declared.
    from shenbi.gates.g0_skill_contract import check_skill_contracts

    sc_issues = check_skill_contracts()
    if sc_issues:
        return fail(
            "G0",
            checks
            + [
                {
                    "id": "G0.16",
                    "s": "FAIL",
                    "r": "; ".join(sc_issues),
                }
            ],
            "round_creation",
            [
                "G0.16: shorten descriptions to <=500 chars (trigger-only), "
                "remove writes/updates overlap, add mode: to declared writes/updates"
            ],
        )
    checks.append(
        {"id": "G0.16", "s": "PASS", "note": "all skills pass contract + description checks"}
    )
```

- [ ] **Step 6: Run g0 tests + verify G0.16 wiring**

Run: `uv run pytest tests/unit/gates/test_g0_skill_contract.py tests/unit/gates/test_g0.py -v`
Expected: PASS.

Note: If existing skill descriptions/contracts do not yet satisfy G0.16, `test_g0.py` integration tests that invoke the full `gate_G0` may fail. That is expected and is fixed in Task 2 by adding `mode:` to real skill contracts. Do not relax the check to make existing skills pass — fix the skills.

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/gates/g0_skill_contract.py src/shenbi/gates/g0.py tests/unit/gates/test_g0_skill_contract.py
git commit -m "feat(g0): add G0.16 skill contract + description quality check

Spec 14 §3.1. Validates all 69 skills: description <=500 chars and
trigger-only, writes/updates disjoint, write mode declared. New check
is G0.16 (next free id after G0.15)."
```

---

### Task 2: Add write semantics to skill contract frontmatter

**Files:**
- Modify: all 69 `skills/*/SKILL.md` frontmatter `contract.writes`/`contract.updates` entries — convert string entries that need semantics to dict-form `{file, mode, no_op_behavior?, key?}`. Concretely start with the skills named in the spec findings: `skills/shenbi-chapter-revision/SKILL.md`, `skills/shenbi-state-settling/SKILL.md`, `skills/shenbi-foreshadowing-track/SKILL.md`.
- Test: `tests/unit/gates/test_g0_skill_contract.py` (extend with a real-skills regression test)

**Interfaces:**
- Consumes: `check_skill_contracts` from Task 1, the closed `mode` set
- Produces: every skill that touches mutable files declares `mode` (and `no_op_behavior`/`key` where relevant). G0.16 now passes against the real skills/ tree.

**Context:** The contract YAML format already supports dict-form for `reads` (`legacy.py:_validate` calls `_normalize_read_item`). `writes`/`updates` are currently validated as `list[str]` (see `legacy.py:_validate` lines 158-161). Task 3 extends that validator to accept dict-form for writes/updates. Until then, this task only edits frontmatter; the legacy validator must be relaxed in Task 3 BEFORE running the full suite, or `load_contract` will raise on dict-form writes. **Do Task 3's validator edit before running `just check` in this task's Step 4.** Per the spec note: only `mode`/`no_op_behavior`/`key` are new; `reads`/`writes`/`updates` already exist.

- [ ] **Step 1: Write the failing test (real-skills regression)**

Append to `tests/unit/gates/test_g0_skill_contract.py`:

```python
class TestRealSkillsTree:
    def test_all_real_skills_pass_contract_check(self):
        """Every skill in the real skills/ tree passes G0.16.

        This is the regression gate: after frontmatter is updated to declare
        write semantics, the whole tree must be clean.
        """
        from shenbi.gates.shared import SKILLS

        issues = check_skill_contracts(SKILLS)
        # If this fails, the failing skill needs its writes/updates given a
        # 'mode:' (and the description shortened/triggerified if flagged).
        assert issues == [], (
            "G0.16 contract violations in real skills tree:\n  "
            + "\n  ".join(issues)
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/gates/test_g0_skill_contract.py::TestRealSkillsTree -v`
Expected: FAIL with a list of `G0.sc.missing_write_semantics:...` (and possibly `desc_too_long`/`desc_has_behavior`) issues for real skills.

- [ ] **Step 3: Update skill frontmatter to declare write semantics**

For each skill flagged by the failing test, edit its `skills/<skill>/SKILL.md` frontmatter. Convert string `writes`/`updates` entries to dict-form with a `mode`. The closed `mode` set:

| mode | meaning | when to use |
|------|---------|-------------|
| `create_or_overwrite` | write new or replace existing | reports, decisions JSON, snapshots |
| `merge_prose` | merge revision into existing prose (content-preserving) | `chapters/chapter-N.md` revision |
| `append_dedup` | append row, dedup by `key` | truth files via upsert |

Concrete edits for the spec-called-out skills. For `skills/shenbi-chapter-revision/SKILL.md`, change:

```yaml
  writes:
    - truth/state_snapshot-pre-rev.md
    - chapters/chapter-N-revision-decisions.json
  updates:
    - chapters/chapter-N.md
```
to:

```yaml
  writes:
    - file: truth/state_snapshot-pre-rev.md
      mode: create_or_overwrite
    - file: chapters/chapter-N-revision-decisions.json
      mode: create_or_overwrite
  updates:
    - file: chapters/chapter-N.md
      mode: merge_prose
      no_op_behavior: skip_write
```

For `skills/shenbi-state-settling/SKILL.md`, give every `updates:` truth-file entry `mode: append_dedup` with the matching `key` (e.g. `key: chapter` for row-keyed truth files).

For `skills/shenbi-foreshadowing-track/SKILL.md`, give the `pending_hooks.md` update `mode: append_dedup` with `key: hook_id` (or the field the skill dedups on).

For any `writes:`/`updates:` entry in any flagged skill, add the appropriate `mode`. For descriptions flagged `desc_too_long` or `desc_has_behavior`, rewrite to a ≤500-char trigger-only form (e.g. "Use when <condition>" — no "This skill …" / "Generates …").

Repeat until `check_skill_contracts(SKILLS)` returns `[]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/gates/test_g0_skill_contract.py::TestRealSkillsTree -v`
Expected: PASS (empty issues list).

Note: `load_contract` (legacy validator) must already accept dict-form writes/updates by this point — that relaxation is done in Task 3 Step 3. Run Task 3 first if `load_contract` raises on the new frontmatter.

- [ ] **Step 5: Commit**

```bash
git add skills/ tests/unit/gates/test_g0_skill_contract.py
git commit -m "feat(contracts): declare write semantics (mode/no_op_behavior/key) in skill frontmatter

Spec 14 §3.2. Converts writes/updates entries to dict-form with mode for the
spec-called-out skills (chapter-revision, state-settling, foreshadowing-track)
and any others flagged by G0.16. Only mode/no_op_behavior/key sub-fields are
new; reads/writes/updates already existed."
```

---

### Task 3: Relax contract validator to accept write semantics + dispatch path enforcement

**Files:**
- Modify: `src/shenbi/contracts/legacy.py:142-168` (`_validate` — accept dict-form for `writes`/`updates`, return parsed semantics)
- Modify: `src/shenbi/contracts/legacy.py:43-49` (`Contract` TypedDict — add `write_semantics: dict[str, dict[str, Any]]`)
- Modify: `src/shenbi/pipeline/dispatch_helper.py:294-323` (`_write_parsed_outputs` — route by declared `mode`)
- Test: `tests/unit/pipeline/test_dispatch_write_semantics.py`

**Interfaces:**
- Consumes: `load_contract` (now returning `write_semantics`), `_write_parsed_outputs`, `safe_write`.
- Produces: `Contract.write_semantics: dict[str, dict]` keyed by path; `_write_parsed_outputs(response, output_paths, project_dir, skill)` honors `no_op_behavior: skip_write` via the new `skip_paths` parameter. All declared modes (including `append_dedup`) write the whole file via `safe_write` — truth-file upsert is the caller's (state-settling skill's) responsibility, not the generic dispatch path's.

**Context:** Today `_write_parsed_outputs` always overwrites via `safe_write` regardless of contract (spec §2.2 contract-behavior mismatch). `no_op_behavior: skip_write` means: in a no-op route, do NOT write the file even if the LLM emitted content for it. Because `_write_parsed_outputs` does not currently know the revision route, this task adds an optional `skip_paths: set[str]` parameter (populated by the revision router's no-op decision) so the caller enforces `skip_write`; the contract declares the intent and G0 verifies it.

> **`append_dedup` is NOT routed in the dispatch write path.** The generic `_write_parsed_outputs` dispatch path writes WHOLE FILES (`### FILE: <path>\n<body>`), not structured rows. Truth-file append/upsert semantics are owned by Spec 1's `write_truth_file`, which is called EXPLICITLY from the state-settling skill (the skill body constructs the row dict with the real key). Routing `append_dedup` here would mean fabricating a structured key from raw prose (e.g. `content[:32]`), which is wrong: the key is a semantic field (`chapter`, `hook_id`) that only the calling skill knows. Therefore truth-file `append_dedup` mode is ENFORCED AT THE CALLER LEVEL (state-settling skill calls `write_truth_file` directly), NOT at the generic `_write_parsed_outputs` write level. The contract still declares `mode: append_dedup` on truth-file update entries so G0.16 can verify the skill declares the semantics — but the dispatch write path only honors `no_op_behavior: skip_write`; for everything else it writes the whole file via `safe_write`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_dispatch_write_semantics.py
"""Tests for contract-driven write semantics in _write_parsed_outputs (spec §3.3)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline.dispatch_helper import _write_parsed_outputs


class TestCreateOrOverwrite:
    def test_default_mode_overwrites(self, tmp_path: Path):
        """create_or_overwrite (and undeclared) -> safe_write, current behavior."""
        # NOTE: _parse_file_outputs expects the real marker format
        # "### FILE: <path>" (see dispatch_helper._parse_file_outputs).
        out = _write_parsed_outputs(
            response="### FILE: chapters/c-1.md\nnew body\n",
            output_paths=["chapters/c-1.md"],
            project_dir=tmp_path,
            skill="shenbi-chapter-drafting",
        )
        assert "chapters/c-1.md" in out
        assert "new body" in (tmp_path / "chapters" / "c-1.md").read_text()


class TestAppendDedupNotRoutedInDispatch:
    """The generic dispatch write path does NOT route append_dedup to
    write_truth_file. Truth-file append semantics are enforced at the caller
    (state-settling skill calls write_truth_file explicitly with a real key),
    NOT by fabricating a key from prose in the generic write path.

    Here a declared mode: append_dedup truth-file path is still written as a
    WHOLE FILE via safe_write — the contract declares the mode for G0.16, but
    the dispatch path does not interpret it as an upsert."""

    def test_append_dedup_truth_file_is_written_whole_not_upserted(self, tmp_path: Path):
        """A truth/ path declared mode: append_dedup is written as a whole file
        by _write_parsed_outputs (safe_write), NOT routed to write_truth_file.
        Upsert is the caller's (state-settling skill's) responsibility."""
        truth = tmp_path / "truth" / "current_state.md"
        truth.parent.mkdir(parents=True)
        truth.write_text("# Current State\n\n- chapter: ch0\n", encoding="utf-8")

        with patch(
            "shenbi.pipeline.dispatch_helper.write_truth_file"
        ) as mock_wtf:
            mock_wtf.return_value = None
            out = _write_parsed_outputs(
                response="### FILE: truth/current_state.md\nrow\n",
                output_paths=["truth/current_state.md"],
                project_dir=tmp_path,
                skill="shenbi-state-settling",
            )
            # write_truth_file must NOT be invoked from the dispatch path.
            mock_wtf.assert_not_called()
            # The file is written whole instead.
            assert "truth/current_state.md" in out
            assert (tmp_path / "truth" / "current_state.md").read_text() == "row\n"


class TestNoOpSkipWrite:
    def test_skip_write_paths_not_written(self, tmp_path: Path):
        """A path in skip_paths is not written even if content is present."""
        out = _write_parsed_outputs(
            response="### FILE: chapters/c-1.md\nbody\n",
            output_paths=["chapters/c-1.md"],
            project_dir=tmp_path,
            skill="shenbi-chapter-revision",
            skip_paths={"chapters/c-1.md"},
        )
        assert out == []
        assert not (tmp_path / "chapters" / "c-1.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_write_semantics.py -v`
Expected: FAIL with `TypeError: _write_parsed_outputs() got an unexpected keyword argument 'skip_paths'` (and `write_truth_file` not imported/routed).

- [ ] **Step 3: Write minimal implementation**

First, relax the contract validator in `src/shenbi/contracts/legacy.py`. Update the `Contract` TypedDict:

```python
class Contract(TypedDict):
    kind: OutputKind
    reads: list[str]
    writes: list[str]
    updates: list[str]
    read_fields: dict[str, list[str]]
    write_semantics: dict[str, dict[str, Any]]
```

Add a normalizer near `_normalize_read_item`:

```python
def _normalize_write_item(item: Any, field: str, skill: str) -> tuple[str, dict[str, Any]]:
    """Normalize a writes/updates entry into (path, semantics_meta).

    Accepts a plain string (no declared semantics -> empty meta) or a dict
    {file, mode?, no_op_behavior?, key?}. Dict-form is the new write-semantics
    declaration (spec §3.2).
    """
    if isinstance(item, str):
        return item, {}
    if isinstance(item, dict) and "file" in item:
        meta = {k: v for k, v in item.items() if k != "file"}
        return str(item["file"]), meta
    raise ContractError(
        f"contract.{field}[] must be str or {{file, mode?}}", skill=skill, field=field
    )
```

In `_validate`, change the `writes`/`updates` handling (the `else` branch that currently requires `all(isinstance(x, str) ...)`) to use the normalizer and collect semantics:

```python
    validated: dict[str, list[str]] = {}
    read_fields: dict[str, list[str]] = {}
    write_semantics: dict[str, dict[str, Any]] = {}
    for field in ("reads", "writes", "updates"):
        val = raw.get(field)
        if not isinstance(val, list):
            raise ContractError(f"contract.{field} must be a list", skill=skill, field=field)
        if field == "reads":
            paths: list[str] = []
            for item in val:
                path, fields = _normalize_read_item(item)
                paths.append(path)
                if fields is not None:
                    read_fields[path] = fields
            items = paths
        else:
            items: list[str] = []
            for item in val:
                path, meta = _normalize_write_item(item, field, skill)
                items.append(path)
                if meta:
                    write_semantics[path] = meta
        for p in items:
            if not resolves(p, registry):
                raise ContractError(
                    "contract path does not resolve in registry", skill=skill, field=field, path=p
                )
        validated[field] = items
    return {
        "kind": kind,
        "reads": validated["reads"],
        "writes": validated["writes"],
        "updates": validated["updates"],
        "read_fields": read_fields,
        "write_semantics": write_semantics,
    }
```

Then update `_write_parsed_outputs` in `src/shenbi/pipeline/dispatch_helper.py`. Change the signature and body. Add the import at top of the function (lazy, to avoid import cycles):

```python
def _write_parsed_outputs(
    response: str,
    output_paths: list[str],
    project_dir: Path,
    create_truth_templates: bool = False,
    *,
    skill: str | None = None,
    skip_paths: set[str] | None = None,
) -> list[str]:
    """Parse agent response and write per-file content, honoring no_op_behavior.

    This generic dispatch path writes WHOLE FILES (one ``### FILE: <path>`` block
    per output). It honors only ``no_op_behavior: skip_write`` (paths in
    *skip_paths* are not written). For all declared modes — including
    ``append_dedup`` — it writes the whole file via ``safe_write``.

    Truth-file append/upsert (``mode: append_dedup``) is NOT routed here. That
    mode is declared in the contract so G0.16 can verify it, but the upsert
    itself is the CALLER's responsibility: the state-settling skill calls
    ``write_truth_file`` directly with a real semantic key field (``chapter``,
    ``hook_id``, ...). Fabricating a key from raw prose in this generic path
    would be wrong — the key is semantic and only the calling skill knows it.
    ``merge_prose`` content-preservation is likewise enforced by G4 / the caller;
    the dispatch write itself replaces the file.

    Returns list of successfully written paths.
    """
    parsed = _parse_file_outputs(response)
    written: list[str] = []
    skip = skip_paths or set()

    semantics: dict[str, dict] = {}
    if skill is not None:
        try:
            from shenbi.contracts import load_contract

            semantics = load_contract(skill).get("write_semantics", {})
        except Exception:
            semantics = {}  # contract issues surface in G0; never block dispatch here

    for rel_path in output_paths:
        if "*" in rel_path:
            continue
        if rel_path in skip:
            log.info("write_skipped_noop", path=rel_path, skill=skill)
            continue
        content = parsed.get(rel_path, parsed.get("__stdout__", ""))
        if not content.strip():
            log.warning("output_empty", path=rel_path)
            continue
        full_path = project_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        mode = semantics.get(rel_path, {}).get("mode")
        # NOTE: append_dedup is intentionally NOT branched here. The dispatch
        # path writes whole files; truth-file upsert is the caller's job
        # (state-settling skill calls write_truth_file with a real key).
        safe_write(full_path, content)
        written.append(rel_path)
        log.info("output_written", path=rel_path, size=len(content), mode=mode)

    if create_truth_templates and any("*" in p for p in output_paths):
        _init_truth_templates(project_dir)

    return written
```

Then update the two call sites in `_dispatch_via_api` (line ~449) and `_dispatch_via_ide` (line ~527) to pass `skill=skill`:

```python
    written = _write_parsed_outputs(
        output_text, output_paths, project_dir,
        create_truth_templates=True, skill=skill,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_dispatch_write_semantics.py tests/unit/pipeline/test_dispatch_helper.py tests/unit/gates/test_g0_skill_contract.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/contracts/legacy.py src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_write_semantics.py
git commit -m "feat(dispatch): enforce declared write semantics + relax contract validator

Spec 14 §3.2-3.3. _validate now accepts dict-form writes/updates and returns
write_semantics. _write_parsed_outputs honors no_op_behavior via
skip_paths; all modes write whole files via safe_write (truth-file upsert
stays the caller's job). Callers pass skill= so the contract is consulted."
```

---

### Task 4: Skill description audit tool

**Files:**
- Create: `tools/audit-skill-descriptions.py`
- Test: `tests/unit/tools/test_audit_skill_descriptions.py`

**Interfaces:**
- Consumes: `_parse_frontmatter`, `DESCRIPTION_MAX_CHARS`, `_desc_has_behavioral_text` from `shenbi.gates.g0_skill_contract`
- Produces: a CLI script `python tools/audit-skill-descriptions.py [--skills-dir skills]` that prints a per-skill compliance report and exits non-zero if any description violates the rules.

**Context:** Spec §3.4 wants a report surfacing descriptions > 500 chars and behavioral (non-trigger) descriptions. Reusing the Task 1 helpers keeps a single source of truth. The tool is a thin wrapper, not a second implementation of the checks.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/tools/test_audit_skill_descriptions.py
"""Tests for the skill-description audit tool (spec §3.4)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[3] / "tools" / "audit-skill-descriptions.py"


class TestAuditTool:
    def test_tool_exists(self):
        assert _TOOLS.exists(), f"audit tool missing at {_TOOLS}"

    def test_tool_runs_against_synthetic_dir(self, tmp_path: Path):
        """The tool emits a report and exits non-zero on a violation."""
        skill = tmp_path / "shenbi-bad"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: shenbi-bad\n"
            "description: |\n  This skill generates a huge plot. " + ("x" * 600) + "\n"
            "contract: {kind: ephemeral}\n---\n# body\n",
            encoding="utf-8",
        )
        r = subprocess.run(
            [sys.executable, str(_TOOLS), "--skills-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert r.returncode != 0, "tool must exit non-zero when violations exist"
        assert "shenbi-bad" in r.stdout

    def test_clean_dir_exits_zero(self, tmp_path: Path):
        skill = tmp_path / "shenbi-good"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            '---\nname: shenbi-good\ndescription: "Use when a chapter fails the audit"\n'
            "contract: {kind: ephemeral}\n---\n# body\n",
            encoding="utf-8",
        )
        r = subprocess.run(
            [sys.executable, str(_TOOLS), "--skills-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, f"clean dir must pass: {r.stdout}\n{r.stderr}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/tools/test_audit_skill_descriptions.py -v`
Expected: FAIL (`_TOOLS` does not exist).

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Audit skill descriptions for AGENTS.md compliance (spec §3.4).

Report (and exit non-zero on):
  - description longer than 500 chars
  - description that reads as behavioral ('This skill does X') rather than
    trigger-only ('Use when Y')

Reuses the G0.skill_contract helpers so there is one source of truth for the
rules. Run:  python tools/audit-skill-descriptions.py [--skills-dir skills]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root without install.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from shenbi.gates.g0_skill_contract import (  # noqa: E402
    DESCRIPTION_MAX_CHARS,
    _desc_has_behavioral_text,
    _parse_frontmatter,
)


def audit(skills_dir: Path) -> list[tuple[str, str]]:
    """Return [(skill_name, issue)] for every description violation."""
    violations: list[tuple[str, str]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        name = skill_md.parent.name
        fm = _parse_frontmatter(skill_md)
        if fm is None:
            continue
        desc = str(fm.get("description", ""))
        if len(desc) > DESCRIPTION_MAX_CHARS:
            violations.append((name, f"desc_too_long:{len(desc)}"))
        if desc and _desc_has_behavioral_text(desc):
            violations.append((name, "desc_has_behavior"))
    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit skill descriptions for compliance.")
    ap.add_argument(
        "--skills-dir",
        type=Path,
        default=_REPO_ROOT / "skills",
        help="Directory of skill subdirs (default: repo skills/)",
    )
    args = ap.parse_args()

    if not args.skills_dir.is_dir():
        print(f"error: skills dir not found: {args.skills_dir}", file=sys.stderr)
        return 2

    violations = audit(args.skills_dir)
    if not violations:
        print(f"OK: all descriptions compliant in {args.skills_dir}")
        return 0

    print(f"# Skill Description Audit — {len(violations)} violation(s)\n")
    for name, issue in violations:
        print(f"- {name}: {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Make it executable: `chmod +x tools/audit-skill-descriptions.py`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/tools/test_audit_skill_descriptions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/audit-skill-descriptions.py tests/unit/tools/test_audit_skill_descriptions.py
git commit -m "feat(tools): add skill description audit report (spec §3.4)

python tools/audit-skill-descriptions.py flags descriptions > 500 chars and
behavioral text, exits non-zero on violations. Reuses G0.skill_contract helpers."
```

---

### Task 5: Regression verification

**Files:**
- No new files.

**Interfaces:**
- Consumes: all four prior tasks.

**Context:** Spec §5 verification: G0.skill_contract passes for all 69 skills; all descriptions ≤500 chars; no write/update overlap; all update paths declare semantics; dispatch path honors `no_op_behavior: skip_write` (truth-file `append_dedup` upsert is enforced at the caller level, not in the dispatch write path); `just check` passes.

- [ ] **Step 1: Run the new tests together**

Run: `uv run pytest tests/unit/gates/test_g0_skill_contract.py tests/unit/pipeline/test_dispatch_write_semantics.py tests/unit/tools/test_audit_skill_descriptions.py -v`
Expected: PASS.

- [ ] **Step 2: Run the audit tool against the real tree**

Run: `python tools/audit-skill-descriptions.py`
Expected: exit 0, "all descriptions compliant".

- [ ] **Step 3: Run the full check suite**

Run: `just check`
Expected: PASS (G0.16 green; contract loading green with dict-form writes/updates).

- [ ] **Step 4: Commit (only if fixes were needed)**

```bash
git add -A
git commit -m "test(skill-contract): full regression green for spec 14"
```
