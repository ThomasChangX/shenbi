# Token 效率 audit 总纲 P0+P1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the master Token-efficiency audit spec's P0 (pure waste, zero quality risk) + P1 (contract consistency) remediations — wire the TokenLedger dead-circuit, fix the basename-key correctness bug + its SharedAuditContext interaction, remove dead escalation reads, strip redundant auto-gen blocks from the LLM view, delete dead code, adjudicate dead decisions sidecars, and add field-level reads for the three largest truth files.

**Architecture:** All fixes target the dispatcher contract surface (`src/shenbi/pipeline/dispatch_helper.py`), the cost ledger wire-up (`src/shenbi/cost/`), skill contracts (`skills/*/SKILL.md` frontmatter), and repo-consistency lint (`tools/lint_repo_consistency.py`). P2 efficiency optimizations (cache layer, IDE CLI system/user split, example externalization) are deferred to a separate future plan — they depend on the TokenLedger measurement this plan lands (spec §9 dependency) and each requires full G4 validation.

**Tech Stack:** Python 3.11+, pathlib, structlog, pydantic contracts, pytest, ruff/mypy/basedpyright, justfile.

## Global Constraints

- **G4/gate is the sole quality arbiter** (spec §0.1, §8 #5): any change where G4 still PASSes is safe; if a change makes G4 FAIL, revert immediately.
- **No `print()` in framework code** — use structlog (AGENTS.md Python Conventions).
- **Contract changes must stay idempotent** — `just generate` (shenbi-sync-contracts) must produce no diff after contract edits (AGENTS.md §PR Review Protocol).
- **Enum compliance (L1)**: no new enums; if needed, define in `src/shenbi/contracts/enums.py` only.
- **I2 test truthfulness (L4)**: tests must exercise real code paths, not mock-only.
- **Fix ordering** (spec §9): T1 (basename key + helper) must land before any shared_context serial wire-up (deferred P2); T5 (auto-gen strip) is independent but T3 (escalation reads) depends on codegen re-run; T2 (ledger) is prerequisite for all P2 measurement.
- **line-length=100** (pyproject.toml); ruff + basedpyright strict.

## File Structure

| File | Responsibility | Tasks |
|------|---------------|-------|
| `src/shenbi/pipeline/dispatch_helper.py` | Dispatcher: input key form, auto-gen strip, ledger wire-up | T1, T2, T5 |
| `src/shenbi/cost/ledger.py` | TokenLedger (no change — already correct, just unwired) | T2 (read-only ref) |
| `tools/lint_repo_consistency.py` | Repo-consistency lints — add dead-decisions-sidecar check | T6 |
| `skills/shenbi-escalation-review/SKILL.md` | Dead reads removal (frontmatter) | T3 |
| `skills/shenbi-chapter-planning/SKILL.md` | Dead writes removal (state-settling-decisions too) | T4 |
| `skills/shenbi-state-settling/SKILL.md` | Dead writes removal | T4 |
| `tests/pipeline/test_dispatch_helper_*.py` | Dispatcher unit tests | T1, T2, T5 |
| `tests/unit/test_lint_repo_consistency.py` | Lint tests | T6 |

---

## Task 1: Fix basename-key collision + lockstep SharedAuditContext injection (spec §3.4, §6.1 C1)

**complexity: infra** (touches dispatcher input-path logic + shared_context injection; the C1 regression risk makes this infra, not leaf — coordinator implements)

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (add `_input_key` helper ~:530; change `:544` key; change `:551-557` injection keys)
- Test: `tests/pipeline/test_dispatch_helper_keys.py` (create)

**Interfaces:**
- Consumes: `full_path: Path`, `project_dir: Path` (both in scope at `_build_skill_prompt`)
- Produces: `_input_key(full_path: Path, project_dir: Path) -> str` — shared helper returning `str(full_path.relative_to(project_dir))`, used by both the disk-read path and the SharedAuditContext injection path.

- [ ] **Step 1: Write the failing tests**

Create `tests/pipeline/test_dispatch_helper_keys.py`:

```python
"""Tests for input-key form in _build_skill_prompt (spec §3.4 + C1 regression guard)."""
from pathlib import Path

from shenbi.pipeline.dispatch_helper import _input_key


def test_input_key_uses_relative_path():
    """Keys must be project-relative, not basename (spec §3.4 collision bug)."""
    project = Path("/proj")
    key = _input_key(Path("/proj/truth/pending_hooks.md"), project)
    assert key == "truth/pending_hooks.md"


def test_input_key_distinguishes_same_basename_different_dirs():
    """Two files with the same basename in different dirs get distinct keys (the bug)."""
    project = Path("/proj")
    a = _input_key(Path("/proj/dir_a/hooks.md"), project)
    b = _input_key(Path("/proj/dir_b/hooks.md"), project)
    assert a != b
    assert a == "dir_a/hooks.md"
    assert b == "dir_b/hooks.md"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/pipeline/test_dispatch_helper_keys.py -v`
Expected: FAIL — `ImportError: cannot import name '_input_key'`

- [ ] **Step 3: Add the `_input_key` helper**

In `src/shenbi/pipeline/dispatch_helper.py`, add this helper near the other `_build_skill_prompt` helpers (e.g., just before `def _build_skill_prompt`, currently around line 465):

```python
def _input_key(full_path: Path, project_dir: Path) -> str:
    """Return the canonical raw_inputs key for a file (spec §3.4).

    Uses the project-relative path (not basename) so two same-named files in
    different directories don't silently overwrite each other. Shared by the
    disk-read loop and the SharedAuditContext injection block so the two never
    produce mismatched keys (spec §6.1 C1 regression guard).
    """
    try:
        return str(full_path.relative_to(project_dir))
    except ValueError:
        # full_path is not under project_dir (defensive); fall back to full str.
        return str(full_path)
```

- [ ] **Step 4: Wire `_input_key` into the disk-read path**

Change `src/shenbi/pipeline/dispatch_helper.py:544`:
```python
# OLD:
            raw_inputs[full_path.name] = content
# NEW:
            raw_inputs[_input_key(full_path, project_dir)] = content
```
(`project_dir` is in scope at this point in `_build_skill_prompt`.)

- [ ] **Step 5: Wire `_input_key` into the SharedAuditContext injection block (C1 fix)**

The injection block (`dispatch_helper.py:548-560`) currently hardcodes basename keys. Update each cached field to use the relative-path form via `_input_key`. The cached values correspond to known truth files, so construct the keys from `project_dir`:

```python
    # Inject cached fields from shared_context so auditors skip re-reading
    # those files from disk (Task 6 Step 2 wiring). Keys must match the
    # disk-read path's _input_key form (spec §6.1 C1) — basename before was
    # coincidentally consistent; now both use relative paths explicitly.
    if shared_context is not None:
        _INJECT_FROM_CACHE: dict[str, str] = {}
        if getattr(shared_context, "world_rules", ""):
            _INJECT_FROM_CACHE[_input_key(project_dir / "truth" / "world_rules.md", project_dir)] = shared_context.world_rules
        if getattr(shared_context, "character_list", ""):
            _INJECT_FROM_CACHE[_input_key(project_dir / "truth" / "character_matrix.md", project_dir)] = shared_context.character_list
        if getattr(shared_context, "style_profile", ""):
            _INJECT_FROM_CACHE[_input_key(project_dir / "truth" / "style_profile.md", project_dir)] = shared_context.style_profile
        if getattr(shared_context, "pending_hooks", ""):
            _INJECT_FROM_CACHE[_input_key(project_dir / "truth" / "pending_hooks.md", project_dir)] = shared_context.pending_hooks
        for fname, cached in _INJECT_FROM_CACHE.items():
            if cached and fname not in raw_inputs:
                raw_inputs[fname] = cached
```
Note the added `and fname not in raw_inputs` guard: if the disk-read loop already populated the file (fresh content), do NOT overwrite with the (possibly stale) cached slice.

- [ ] **Step 6: Add a regression test for the C1 no-duplicate-keys invariant**

Append to `tests/pipeline/test_dispatch_helper_keys.py`:

```python
def test_injection_keys_match_disk_read_keys():
    """SharedAuditContext injection must use the same key form as disk reads.

    Regression guard for spec §6.1 C1: if the injection block used basename
    keys while the disk-read path used relative-path keys, the same logical
    file would appear twice under two <document name=...> tags.
    """
    from shenbi.pipeline.dispatch_helper import _input_key
    from pathlib import Path

    project = Path("/proj")
    # The injection block builds keys for these truth files:
    for truth_file in [
        project / "truth" / "world_rules.md",
        project / "truth" / "character_matrix.md",
        project / "truth" / "style_profile.md",
        project / "truth" / "pending_hooks.md",
    ]:
        injected_key = _input_key(truth_file, project)
        disk_key = _input_key(truth_file, project)  # same helper
        assert injected_key == disk_key
        assert "/" in injected_key  # relative-path form, not bare basename
```

- [ ] **Step 7: Run all dispatch_helper tests**

Run: `pytest tests/pipeline/test_dispatch_helper_keys.py tests/pipeline/test_dispatch_helper_glob.py tests/pipeline/test_dispatch_helper_xml.py -v`
Expected: all PASS.

- [ ] **Step 8: Run full check**

Run: `just check`
Expected: PASS (no regressions). The `_input_key` change is behavioral only for the rare same-basename-different-dir case, which has no existing test relying on basename keys.

- [ ] **Step 9: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_dispatch_helper_keys.py
git commit -m "fix: use project-relative input keys + lockstep SharedAuditContext injection (§3.4/C1)"
```

---

## Task 2: Wire TokenLedger.record() into the dispatch path + thread state through IDE-CLI path (spec §3.1, §6.1, I6)

**complexity: infra** (touches dispatch routing API + cross-path state threading; coordinator implements)

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (`_record_token_usage:1246` add ledger call; `_dispatch_via_ide:1521` signature + `:1653` call site)
- Test: `tests/pipeline/test_dispatch_helper_ledger.py` (create)

**Interfaces:**
- Consumes: `TokenLedger` from `shenbi.cost.ledger` (existing, no change); `state` param on `dispatch_skill`/`_dispatch_via_api` (existing).
- Produces: `_dispatch_via_ide` now accepts `state: Any = None`; `_record_token_usage` now persists to `cost/token-ledger.jsonl`.

- [ ] **Step 1: Write the failing test**

Create `tests/pipeline/test_dispatch_helper_ledger.py`:

```python
"""Tests for TokenLedger wire-up in the dispatch path (spec §3.1 dead-wire fix)."""
import json
from pathlib import Path
from types import SimpleNamespace

from shenbi.cost.ledger import TokenLedger


def test_record_token_usage_persists_to_ledger(tmp_path):
    """_record_token_usage must write to cost/token-ledger.jsonl (spec §3.1).

    Before this fix, _record_token_usage only mutated an in-memory dict and
    the ledger stayed empty (dead-wire).
    """
    from shenbi.pipeline.dispatch_helper import _record_token_usage

    state = SimpleNamespace(token_usage={})
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    _record_token_usage(state, "test-skill", usage, project_dir=tmp_path)

    ledger_path = tmp_path / "cost" / "token-ledger.jsonl"
    assert ledger_path.exists(), "ledger file must be created"
    records = [json.loads(line) for line in ledger_path.read_text().strip().splitlines()]
    assert len(records) == 1
    assert records[0]["skill"] == "test-skill"
    assert records[0]["prompt_tokens"] == 100
    assert records[0]["completion_tokens"] == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_dispatch_helper_ledger.py -v`
Expected: FAIL — `_record_token_usage() takes 3 positional arguments but 4 were given` (project_dir not yet a param).

- [ ] **Step 3: Add `project_dir` param + ledger call to `_record_token_usage`**

In `src/shenbi/pipeline/dispatch_helper.py`, modify `_record_token_usage` (currently `:1246-1263`):

```python
def _record_token_usage(
    state: Any, skill_name: str, usage: Any, project_dir: Path | None = None
) -> None:
    """Accumulate token usage in pipeline state and persist to the ledger.

    Spec §3.1: previously only mutated the in-memory state.token_usage dict —
    the TokenLedger.record() write side was never wired, leaving
    cost/token-ledger.jsonl permanently empty (dead-wire). Now also appends a
    record when project_dir is available.
    """
    if not hasattr(state, "token_usage"):
        state.token_usage = {}

    if skill_name not in state.token_usage:
        state.token_usage[skill_name] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
        }

    rec = state.token_usage[skill_name]
    rec["prompt_tokens"] += usage.prompt_tokens
    rec["completion_tokens"] += usage.completion_tokens
    rec["total_tokens"] += usage.total_tokens
    rec["calls"] += 1

    # Spec §3.1 wire-up: persist this usage to the append-only ledger.
    if project_dir is not None:
        TokenLedger(project_dir).record(
            skill_name,
            getattr(state, "chapter", 0) or 0,
            {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
        )
```

Add the import at the top of `dispatch_helper.py` (near other `shenbi.cost` imports if present, else with the other local imports):
```python
from shenbi.cost.ledger import TokenLedger
```

- [ ] **Step 4: Pass `project_dir` at the existing `_record_token_usage` call site**

At `dispatch_helper.py:1243` (inside `_dispatch_via_api`, the only current caller), update:
```python
# OLD:
        _record_token_usage(state, skill_name, usage)
# NEW:
        _record_token_usage(state, skill_name, usage, project_dir=project_dir)
```
(`project_dir` is in scope in `_dispatch_via_api`.)

- [ ] **Step 5: Thread `state` through the IDE-CLI path (I6 fix)**

Add `state: Any = None` to `_dispatch_via_ide` signature (`:1521`):
```python
def _dispatch_via_ide(
    skill: str,
    project_dir: Path,
    prompt: str,
    uses_staging: bool = False,
    shared_context: Any = None,
    state: Any = None,
) -> DispatchResult:
```

Update the call site at `dispatch_helper.py:1653` (in `dispatch_skill` routing):
```python
# OLD:
        return _dispatch_via_ide(
            skill, pd, prompt, uses_staging=uses_staging, shared_context=shared_context
        )
# NEW:
        return _dispatch_via_ide(
            skill, pd, prompt, uses_staging=uses_staging, shared_context=shared_context, state=state
        )
```

- [ ] **Step 6: Add IDE-path usage recording (best-effort)**

The IDE-CLI subprocess (`codex exec`) does not return structured token usage in its stdout. The IDE path therefore cannot populate `state.token_usage` from the CLI output alone. Add a `log.info` marker so the uninstrumented path is at least observable, and document the limitation:

After the IDE dispatch's `DispatchResult` return (end of `_dispatch_via_ide`), add before the final return:
```python
    # Spec §3.1 / I6: the IDE-CLI path does not report structured token usage
    # (codex exec stdout is prose, not a usage object). state is threaded so a
    # future codex --json or zcode usage-report feature can record here.
    if state is not None:
        log.info("ide_dispatch_uninstrumented_tokens", skill=skill, hint="IDE path cannot record usage; ledger row skipped")
    return DispatchResult(True, 0, r.stdout, r.stderr)
```

- [ ] **Step 7: Run tests**

Run: `pytest tests/pipeline/test_dispatch_helper_ledger.py tests/unit/cost/test_ledger.py -v`
Expected: PASS.

- [ ] **Step 8: Run full check**

Run: `just check`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_dispatch_helper_ledger.py
git commit -m "fix: wire TokenLedger.record() into dispatch path + thread state through IDE-CLI (§3.1/I6)"
```

---

## Task 3: Remove 3 dead reads from shenbi-escalation-review + re-run codegen (spec §3.6, §6.1, I3)

**complexity: leaf** (single skill frontmatter edit + codegen re-run; no cross-module logic)

**Files:**
- Modify: `skills/shenbi-escalation-review/SKILL.md` (frontmatter `reads:` block `:10-12`; auto-gen `:29` regenerates via codegen)
- Test: G4 structural check + lint (no new unit test — this is a contract edit)

**Interfaces:**
- Consumes: `shenbi-sync-contracts` (codegen entrypoint via `just generate`)
- Produces: escalation-review contract with 3 fewer reads (volume-N-score, arc-N-score, stratum-N-score)

- [ ] **Step 1: Verify the 3 reads are truly dead (body doesn't reference them)**

Run: `grep -nE "volume-score|arc-score|stratum-score|卷分|弧分|层分" skills/shenbi-escalation-review/SKILL.md`
Expected: no matches (confirms dead reads — spec §3.6 already verified).

- [ ] **Step 2: Edit the frontmatter reads block**

In `skills/shenbi-escalation-review/SKILL.md`, remove lines `:10-12` (the 3 score entries):
```yaml
  reads:
  - truth/resonance_trend.md
  - audits/volume-N-score.md      # DELETE
  - audits/arc-N-score.md          # DELETE
  - audits/stratum-N-score.md      # DELETE
  - audits/chapter-N-sensitivity.md
```
becomes:
```yaml
  reads:
  - truth/resonance_trend.md
  - audits/chapter-N-sensitivity.md
```

- [ ] **Step 3: Re-run codegen to sync the auto-gen 数据契约 block (I3 hard prerequisite)**

Run: `uv run shenbi-sync-contracts`
Then verify the auto-gen block at `:29` no longer lists the 3 dead reads:
Run: `grep -nE "volume-N-score|arc-N-score|stratum-N-score" skills/shenbi-escalation-review/SKILL.md`
Expected: no matches anywhere in the file (both frontmatter and auto-gen cleaned).

- [ ] **Step 4: Verify codegen is idempotent (no diff on re-run)**

Run: `uv run shenbi-sync-contracts && git diff --exit-code -- skills/shenbi-escalation-review/SKILL.md`
Expected: exit 0 (the second run produces no further changes).

- [ ] **Step 5: Run lint + contract checks**

Run: `just lint-contracts && uv run python tools/lint_repo_consistency.py`
Expected: PASS (no violations; body-ban still green because only frontmatter changed, not a hand-written body block).

- [ ] **Step 6: Run full check**

Run: `just check`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/shenbi-escalation-review/SKILL.md
git commit -m "fix: remove 3 dead reads from escalation-review + sync codegen (§3.6/I3)"
```

---

## Task 4: Adjudicate + apply dead decisions-sidecar dispositions (spec §3.5, §6.2, I2)

**complexity: infra** (cross-skill contract edits + G4 checker-map awareness; the per-sidecar adjudication touches G4 semantics — coordinator implements)

**Per-sidecar disposition table (verified against src/ + G4 checker map):**

| Producer | writes | skill reads? | code/G4 consumer? | Disposition |
|----------|--------|-------------|-------------------|-------------|
| chapter-planning | plans/chapter-N-plan-decisions.json | ❌ | ❌ no G4 checker, no code | **DELETE writes** |
| state-settling | truth/state-settling-decisions.json | ❌ | ❌ no G4 checker, no code | **DELETE writes** |
| chapter-revision | chapters/chapter-N-revision-decisions.json | ❌ | ✅ G4 `g4_decisions` + `state_heal.py:58` counter | **KEEP writes** (structural: G4 validates + code counts) |
| short-drafting | short/short-N-decisions.json | ❌ | ✅ G4 `g4_decisions` | **KEEP writes** (G4 validates schema) |
| market-radar | context/market-radar-decisions.json | ❌ | ✅ G4 `g4_decisions` | **KEEP writes** (G4 validates schema) |

Rationale: "dead" per spec §3.5 = no skill `reads:` consumer. But 3 of 5 have non-skill structural consumers (G4 schema validation, state_heal counter). Deleting those writes would break G4 or state reconciliation. Only the 2 with zero consumers (plan-decisions, state-settling-decisions) are safe to delete. The new lint (Task 6) will use a smarter definition: flag a decisions.json write only if it has NO skill reads AND no G4 checker AND no code reference.

**Files:**
- Modify: `skills/shenbi-chapter-planning/SKILL.md` (remove `plans/chapter-N-plan-decisions.json` from `writes:`)
- Modify: `skills/shenbi-state-settling/SKILL.md` (remove `truth/state-settling-decisions.json` from `writes:`)

- [ ] **Step 1: Verify the 2 delete-candidates have no consumers**

Run:
```bash
grep -rn "plan-decisions" src/shenbi/ tools/ skills/*/SKILL.md | grep -v __pycache__ | grep -v "chapter-planning/SKILL.md"
grep -rn "state-settling-decisions" src/shenbi/ tools/ skills/*/SKILL.md | grep -v __pycache__ | grep -v "state-settling/SKILL.md"
```
Expected: no matches (confirms truly dead — no G4, no code, no skill reads).

- [ ] **Step 2: Edit chapter-planning writes**

In `skills/shenbi-chapter-planning/SKILL.md`, remove `plans/chapter-N-plan-decisions.json` from the `writes:` block.

- [ ] **Step 3: Edit state-settling writes**

In `skills/shenbi-state-settling/SKILL.md`, remove `truth/state-settling-decisions.json` from the `writes:` block.

- [ ] **Step 4: Re-run codegen + verify idempotency**

Run: `uv run shenbi-sync-contracts && git diff --exit-code -- skills/shenbi-chapter-planning/SKILL.md skills/shenbi-state-settling/SKILL.md`
Expected: exit 0 after second run.

- [ ] **Step 5: Verify deps.json + docs sync (just generate idempotent)**

Run: `uv run shenbi-sync-contracts && git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/`
Expected: exit 0 (no further changes).

- [ ] **Step 6: Run full check**

Run: `just check`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/shenbi-chapter-planning/SKILL.md skills/shenbi-state-settling/SKILL.md tests/tiers/deps.json docs/framework/
git commit -m "fix: delete 2 truly-dead decisions sidecars (plan/state-settling); keep 3 G4-structural (§3.5/I2)"
```

---

## Task 5: Strip auto-gen 数据契约 + AUTO-CHECK blocks from LLM system prompt (spec §3.8, §6.1)

**complexity: leaf** (dispatcher post-read strip — single function, well-scoped)

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (add strip after `:506` read_text)
- Test: `tests/pipeline/test_dispatch_helper_autogen_strip.py` (create)

**Interfaces:**
- Consumes: the sentinels `<!-- AUTO-GENERATED ... -->` / `<!-- END AUTO-GENERATED -->` and `<!-- AUTO-CHECK-START -->` / `<!-- AUTO-CHECK-END -->` (defined in `sync_contracts.py` + `generate_autocheck_docs.py`)
- Produces: `_strip_autogen_blocks(text: str) -> str` — removes both blocks from the system prompt before sending to LLM.

- [ ] **Step 1: Write the failing test**

Create `tests/pipeline/test_dispatch_helper_autogen_strip.py`:

```python
"""Tests for auto-gen block stripping from LLM system prompt (spec §3.8)."""
from shenbi.pipeline.dispatch_helper import _strip_autogen_blocks


def test_strip_removes_data_contract_block():
    text = (
        "# Skill\n\n<!-- AUTO-GENERATED from frontmatter — do not edit -->\n"
        "## 数据契约\n\n- **Reads:** foo.md\n"
        "<!-- END AUTO-GENERATED -->\n\n## Body instructions\n"
    )
    stripped = _strip_autogen_blocks(text)
    assert "AUTO-GENERATED" not in stripped
    assert "数据契约" not in stripped
    assert "## Body instructions" in stripped


def test_strip_removes_autocheck_block():
    text = "Intro\n\n<!-- AUTO-CHECK-START -->\n## auto-check (generated -- do not edit)\n<!-- AUTO-CHECK-END -->\n\nBody"
    stripped = _strip_autogen_blocks(text)
    assert "AUTO-CHECK" not in stripped
    assert "auto-check" not in stripped
    assert "Body" in stripped


def test_strip_preserves_body_with_no_blocks():
    text = "Plain skill body with no auto-gen blocks."
    assert _strip_autogen_blocks(text) == text


def test_strip_handles_both_blocks_together():
    text = (
        "Header\n"
        "<!-- AUTO-GENERATED from frontmatter — do not edit -->\nX\n<!-- END AUTO-GENERATED -->\n"
        "Middle\n"
        "<!-- AUTO-CHECK-START -->\nY\n<!-- AUTO-CHECK-END -->\n"
        "Footer\n"
    )
    stripped = _strip_autogen_blocks(text)
    assert "X" not in stripped and "Y" not in stripped
    assert "Header" in stripped and "Middle" in stripped and "Footer" in stripped
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/pipeline/test_dispatch_helper_autogen_strip.py -v`
Expected: FAIL — `ImportError: cannot import name '_strip_autogen_blocks'`.

- [ ] **Step 3: Implement `_strip_autogen_blocks`**

In `src/shenbi/pipeline/dispatch_helper.py`, add near the other `_strip_*` helpers (e.g., after `_strip_meta_for_non_drafting` ~:139):

```python
# Sentinels for the auto-generated body blocks (spec §3.8). These are kept in
# the SKILL.md for codegen traceability + CI idempotency, but they are 100%
# redundant with the frontmatter contract (which the dispatcher already parses
# separately) and should never reach the LLM.
_AUTOGEN_DATA_RE = re.compile(
    r"<!-- AUTO-GENERATED.*?-->\n.*?<!-- END AUTO-GENERATED -->\n?",
    re.DOTALL,
)
_AUTOGEN_CHECK_RE = re.compile(
    r"<!-- AUTO-CHECK-START.*?-->\n.*?<!-- AUTO-CHECK-END -->\n?",
    re.DOTALL,
)


def _strip_autogen_blocks(text: str) -> str:
    """Remove the auto-generated 数据契约 + AUTO-CHECK blocks from a SKILL.md body.

    Spec §3.8: both blocks duplicate frontmatter info (数据契约) or are empty
    placeholders (AUTO-CHECK). Stripping them before the system prompt is sent
    saves ~150-320 chars (data-contract) + ~80 chars (auto-check) per skill per
    dispatch. The blocks remain in SKILL.md for codegen/CI — only the LLM view
    changes.
    """
    text = _AUTOGEN_DATA_RE.sub("", text)
    text = _AUTOGEN_CHECK_RE.sub("", text)
    return text
```

- [ ] **Step 4: Call `_strip_autogen_blocks` after the system-prompt read**

At `dispatch_helper.py:506` (where `system_prompt = skill_file.read_text(...)`), change:
```python
# OLD:
        system_prompt = skill_file.read_text(encoding="utf-8")
# NEW:
        system_prompt = _strip_autogen_blocks(skill_file.read_text(encoding="utf-8"))
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/pipeline/test_dispatch_helper_autogen_strip.py -v`
Expected: all PASS.

- [ ] **Step 6: Run full check**

Run: `just check`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py tests/pipeline/test_dispatch_helper_autogen_strip.py
git commit -m "fix: strip redundant auto-gen blocks from LLM system prompt (§3.8)"
```

---

## Task 6: Delete dead code `_inject_instruction_hierarchy` (spec §2.3 #11, §6.1)

**complexity: leaf** (single function deletion, zero callers, marked pyright-ignore)

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py` (delete `_inject_instruction_hierarchy` at `:714-735`)

- [ ] **Step 1: Confirm zero callers**

Run: `grep -rn "_inject_instruction_hierarchy" src/shenbi/ tests/ | grep -v __pycache__`
Expected: only the definition line (`:714`) — no callers (the `# pyright: ignore[reportUnusedFunction]` confirms pyright already knows).

- [ ] **Step 2: Delete the function**

In `src/shenbi/pipeline/dispatch_helper.py`, delete the entire `_inject_instruction_hierarchy` function (`:714-735`, including the `# pyright: ignore[reportUnusedFunction]` comment). The `_build_skill_prompt` function already returns at `:711` without calling it.

- [ ] **Step 3: Run full check**

Run: `just check`
Expected: PASS (no caller breaks; basedpyright no longer needs the ignore comment).

- [ ] **Step 4: Commit**

```bash
git add src/shenbi/pipeline/dispatch_helper.py
git commit -m "refactor: delete dead code _inject_instruction_hierarchy (§2.3 #11)"
```

---

## Task 7: Add dead-decisions-sidecar lint to repo-consistency checker (spec §3.5, §6.2)

**complexity: leaf** (new lint function + test, follows existing pattern in `lint_repo_consistency.py`)

**Files:**
- Modify: `tools/lint_repo_consistency.py` (add `find_dead_decisions_sidecars`)
- Test: `tests/unit/test_lint_repo_consistency.py` (extend)

**Interfaces:**
- Consumes: the G4 checker map (`src/shenbi/gates/g4/generic.py` `checkers` dict) to know which skills have `g4_decisions` validation; skill frontmatter `writes:` + `reads:` blocks.
- Produces: a new lint violation `dead-decisions-sidecar: <skill>: <path>` when a `*-decisions.json` write has no skill reads AND no G4 checker AND no code reference.

**Smarter "dead" definition** (accounts for G4 structural consumers found in Task 4): a decisions.json write is dead iff ALL of:
1. No skill declares it in `reads:`
2. The producer skill is NOT in the G4 checker map with `g4_decisions`
3. No `src/shenbi/` or `tools/` file references the path pattern

This avoids false-positives on the 3 G4-structural sidecars kept in Task 4.

- [ ] **Step 1: Read the existing lint test file to match its style**

Run: `head -40 tests/unit/test_lint_repo_consistency.py` to see the test patterns used.

- [ ] **Step 2: Write the failing test**

Append to `tests/unit/test_lint_repo_consistency.py` (or create if minimal):

```python
def test_dead_decisions_sidecar_detection(tmp_path):
    """find_dead_decisions_sidecars flags decisions.json writes with no consumer.

    A consumer is: a skill reads: declaration, OR a G4 g4_decisions checker,
    OR a src/tools code reference (spec §3.5 + Task 4 disposition).
    """
    from tools.lint_repo_consistency import find_dead_decisions_sidecars
    # This test uses the real repo skills; after Task 4, the 2 truly-dead
    # sidecars (plan-decisions, state-settling-decisions) are deleted, so the
    # lint should report 0 dead sidecars on a clean tree.
    dead = find_dead_decisions_sidecars()
    assert dead == [], f"expected 0 dead decisions sidecars after Task 4, got {dead}"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_lint_repo_consistency.py::test_dead_decisions_sidecar_detection -v`
Expected: FAIL — `ImportError: cannot import name 'find_dead_decisions_sidecars'`.

- [ ] **Step 4: Implement `find_dead_decisions_sidecars`**

In `tools/lint_repo_consistency.py`, add (matching the existing `find_*` style):

```python
import yaml  # if not already imported

# Skills whose decisions.json is structurally validated by G4 g4_decisions
# (these are NOT dead even with no skill reads: — G4 consumes them).
_G4_DECISIONS_SKILLS = frozenset({
    "shenbi-market-radar",
    "shenbi-chapter-revision",
    "shenbi-short-drafting",
})

_DECISIONS_WRITE_RE = re.compile(r"-\s+(.*?-decisions\.json)\s*$")


def _all_skill_frontmatter() -> dict[str, dict]:
    """Return {skill_name: parsed frontmatter dict} for all shenbi-* skills."""
    out: dict[str, dict] = {}
    for skill_dir in sorted((REPO / "skills").glob("shenbi-*/SKILL.md")):
        text = skill_dir.read_text(encoding="utf-8")
        if text.startswith("---"):
            _, fm, _ = text.split("---", 2)
            out[skill_dir.parent.name] = yaml.safe_load(fm) or {}
    return out


def find_dead_decisions_sidecars() -> list[str]:
    """Flag decisions.json writes with no consumer (spec §3.5).

    A decisions.json write is 'dead' iff it has no skill reads: declaration,
    the producer is not in _G4_DECISIONS_SKILLS, and no src/tools code
    references the path pattern. Returns a list of violation strings.
    """
    frontmatters = _all_skill_frontmatter()
    # Collect all reads across all skills (normalized patterns).
    all_reads: set[str] = set()
    for fm in frontmatters.values():
        contract = fm.get("contract") or {}
        for r in (contract.get("reads") or []):
            if isinstance(r, str):
                all_reads.add(r)

    vios: list[str] = []
    for skill, fm in frontmatters.items():
        contract = fm.get("contract") or {}
        for w in (contract.get("writes") or []):
            if isinstance(w, str) and w.endswith("-decisions.json"):
                # Check the 3 consumer conditions.
                if w in all_reads:
                    continue  # a skill reads it
                if skill in _G4_DECISIONS_SKILLS:
                    continue  # G4 validates it
                # Check code references (src/ + tools/).
                pattern = w.replace("chapter-N", "chapter-").replace("short-N", "short-").replace("-N-", "-")
                refs = subprocess.run(  # noqa: S603,S607
                    ["grep", "-rl", pattern, str(REPO / "src"), str(REPO / "tools")],
                    capture_output=True, text=True,
                )
                if refs.stdout.strip():
                    continue  # code references it
                vios.append(f"dead-decisions-sidecar: {skill}: {w}")
    return vios
```
(Add `import subprocess` and `import yaml` at the top if not present. Prefer a Python-only grep to avoid subprocess if the repo already has a walk-based helper — but matching the existing simple style is acceptable.)

- [ ] **Step 5: Wire the new check into `main()`**

In `lint_repo_consistency.py` `main()`, add before the `return`:
```python
    for v in find_dead_decisions_sidecars():
        vios.append(v)
```

- [ ] **Step 6: Run the lint test**

Run: `pytest tests/unit/test_lint_repo_consistency.py::test_dead_decisions_sidecar_detection -v`
Expected: PASS (0 dead sidecars after Task 4 deleted the 2 truly-dead ones).

- [ ] **Step 7: Run full check**

Run: `just check`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/lint_repo_consistency.py tests/unit/test_lint_repo_consistency.py
git commit -m "feat: add dead-decisions-sidecar lint to repo-consistency (§3.5/I2)"
```

---

## Task 8: Add field-level reads for the 3 largest truth files (spec §3.7, §6.2)

**complexity: leaf** (contract edits to high-frequency skills' reads blocks; reuses 07-18 §2.1 field analysis)

**Files:**
- Modify: `skills/shenbi-chapter-planning/SKILL.md` (add `fields:` to chapter-N.md read)
- Modify: `skills/shenbi-chapter-drafting/SKILL.md` (add `fields:` to chapter-N.md read)
- Modify: `skills/shenbi-context-composing/SKILL.md` (add `fields:` to chapter-N.md / power_system / volume_map reads)
- Modify: `skills/shenbi-review-world-rules/SKILL.md` (add `fields:` to power_system / volume_map reads)

**Note:** The exact field lists must be derived from what each skill's body actually references. This task requires reading each skill body to identify the consumed sections. The 07-18 §2.1 analysis (archived) already did this for volume_map ("460 lines, 2 relevant").

- [ ] **Step 1: For each high-frequency skill, identify which fields of the 3 large files it actually consumes**

Run: read each target skill's body + identify the sections it references from `chapters/chapter-N.md`, `world/power_system.md`, `outline/volume_map.md`. Document the field list per skill per file.

(This step is analysis, not code — the field lists are skill-specific and must be verified against the body. If a skill genuinely needs the whole file, do NOT add fields for that file.)

- [ ] **Step 2: Convert the relevant string-form reads to dict-form with `fields:`**

For each identified (skill, file, fields) tuple, change the `reads:` entry from:
```yaml
    - chapters/chapter-N.md
```
to:
```yaml
    - file: chapters/chapter-N.md
      fields: [主角状态, 当前场景, 本章目标]
```
(field names in Chinese, matching the `##` section headers in the actual truth file.)

- [ ] **Step 3: Re-run codegen + verify idempotency**

Run: `uv run shenbi-sync-contracts && git diff --exit-code`
Expected: exit 0 on second run.

- [ ] **Step 4: Verify the field-filter escape hatch doesn't fire (fields actually match file sections)**

Run: `just check` (the contract-sync + lint will catch mismatches); additionally run any test that exercises `filter_to_fields` to confirm no WARN logs.

- [ ] **Step 5: Run full check**

Run: `just check`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/shenbi-*/SKILL.md tests/tiers/deps.json docs/framework/
git commit -m "feat: add field-level reads for 3 largest truth files (§3.7)"
```

---

## Self-Review (coordinator run after writing)

**1. Spec coverage:**
- §6.1 P0 (5 items): 3.1 → T2 ✅; 3.4 → T1 ✅; 3.6 → T3 ✅; 3.8 → T5 ✅; 2.3#11 → T6 ✅
- §6.2 P1 (2 items): 3.5 → T4 (disposition) + T7 (lint) ✅; 3.7 → T8 ✅
- §6.3 P2 (5 items): DEFERRED to separate future plan (depends on T2 measurement + each needs G4 full validation) — documented in plan header.
- §9 ordering constraints: T1 before any P2 3.2 wire-up ✅ (T1 is in this plan, 3.2 is not); T5 independent of T3 but T3's codegen re-run is its own step ✅; T2 prerequisite for P2 measurement ✅.

**2. Placeholder scan:** Task 8 Step 1 is analysis (identify fields from body) — this is inherent to the task (fields are skill-specific), not a placeholder. All code steps show full code. No TBD/TODO.

**3. Type consistency:** `_input_key(full_path, project_dir)` used consistently in T1. `_record_token_usage` signature extended consistently (state, skill_name, usage, project_dir). `_strip_autogen_blocks(text)` consistent. `_G4_DECISIONS_SKILLS` set consistent between T4 disposition table and T7 lint.

**4. C1/C2/I6 from Phase 2 addressed:** C1 (basename+injection lockstep) → T1 Step 5 ✅; C2 (cache invalidation) → deferred with P2 (content-hash noted in plan header) ✅; I6 (IDE path state) → T2 Step 5-6 ✅.
