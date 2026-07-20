# P0 阻断性缺陷修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 4 blocking dead-code/stub defects that prevent the T1/T2/T3 test harness and pipeline CLI from running, then remove the misleading rollback CLI registration — making the codebase runnable and honest.

**Architecture:** All 4 fixes are surgical edits to existing functions/modules. No new modules, no architectural changes. The fixes redirect dead subprocess paths (`tests/validate-gate.py`) to the live gate CLI (`python -m shenbi.gates.cli`), replace a call to a non-existent entry point (`shenbi-progress`) with a direct `progress.json` update, remove an unreachable code branch (`codex-api`), and delete a CLI subparser that advertises an unimplemented command (`rollback`). Each fix is independently testable.

**Tech Stack:** Python 3.11+, subprocess (stdlib), pathlib, json, pytest, existing `shenbi.gates.cli` / `safe_write` / `emit_json`

**Spec reference:** `docs/superpowers/specs/2026-07-16-pipeline-maturity-and-bp-fixes-design.md` §4 (Steps P0.1–P0.4)

## Global Constraints

- Python 3.11+, `from __future__ import annotations` in any modified file that lacks it
- `pathlib.Path` for all file I/O, `json` for structured output
- No `print()` in framework code; use structlog (stderr) + `cli_utils.emit_json` (stdout)
- `safe_write` for all state-file writes (atomic, fsync, lock)
- Typed enums via `StrEnum` (matching `status.py` pattern)
- Tests in `tests/unit/` alongside existing test files
- Conventional Commits: `fix:` for these defect repairs
- `just check` must pass after every task (ruff + mypy + basedpyright + pytest --cov-fail-under=85)

---

## File Structure

```
src/shenbi/
    phase_runner.py          # MODIFY run_gate(): dead path → live gate CLI (Task 1)
    scoring.py               # MODIFY --gate-only + tier-gate blocks: same dead path (Task 2)
    dispatcher/modes/
        codex.py             # MODIFY: replace shenbi-progress subprocess → direct progress.json (Task 3)
        executor.py          # MODIFY: remove dead codex-api branch (Task 4)
        codex_api.py         # MODIFY: docstring → DEPRECATED marker (Task 4)
    pipeline/cli.py          # MODIFY: remove rollback subparser + docstring line (Task 5)

tests/unit/
    phase_runner/            # existing dir — add test_run_gate_uses_cli_module.py (Task 1)
    test_scoring.py          # existing file — add gate-path tests (Task 2)
    dispatcher/              # existing dir — add test_codex_mark_done.py (Task 3)
    pipeline/                # existing dir — add test_cli_rollback_removed.py (Task 5)
```

No new files under `src/shenbi/`. All changes are modifications to existing modules.

---

### Task 1: Fix `phase_runner.run_gate()` dead path (P0.1 — primary)

**Files:**
- Modify: `src/shenbi/phase_runner.py:54-66` (the `run_gate` function)
- Test: `tests/unit/phase_runner/test_run_gate_uses_cli_module.py` (new file)

**Interfaces:**
- Consumes: `shenbi.gates.cli` (the live gate CLI, entry point `shenbi-validate`)
- Produces: `run_gate(gate, args)` returns `dict[str, Any]` with a `"status"` key — **signature unchanged**, only the internal subprocess target changes. Callers (`cmd_start`, `cmd_post_skill`, `cmd_pre_score`, `cmd_finalize`) are unaffected.

**Context:** `run_gate()` subprocess-calls `tests/validate-gate.py` (`:56`), but that file was deleted in PR-19 (gate logic extracted to `src/shenbi/gates/`). The newer pipeline code (`dispatch_helper.run_gate_g3/g4`) already targets `shenbi.gates.cli` correctly — we mirror that.

**Important nuance on the failure mode (verified empirically):** `subprocess.run([sys.executable, "/nonexistent.py", ...])` does **not** raise — it returns `returncode=2`, `stdout=""`, `stderr="can't open file..."`. So the current `except (json.JSONDecodeError, ValueError)` at `:65` already catches `json.loads("")` and returns a FAIL dict. The bug is therefore **not a crash** but a *misleading* result: every gate returns `FAIL` with a stale `raw_stderr` about a missing file, regardless of the actual gate logic. This blocks the T2/T3 harness because `cmd_start`/`cmd_finalize` treat the FAIL as a real gate failure.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/phase_runner/test_run_gate_uses_cli_module.py`:

```python
"""Verify run_gate() targets the live shenbi.gates.cli module, not the deleted
tests/validate-gate.py file.

Regression guard for the PR-19 migration that extracted gate logic into
src/shenbi/gates/ but left phase_runner.py calling the old path.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from shenbi.phase_runner import run_gate


class TestRunGateTarget:
    @patch("shenbi.phase_runner.subprocess.run")
    def test_calls_gates_cli_module_not_validate_gate_py(self, mock_run, tmp_path):
        """run_gate must invoke `python -m shenbi.gates.cli`, never tests/validate-gate.py."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"status": "PASS"}', stderr=""
        )
        run_gate("G5", ["some-phase", str(tmp_path), str(tmp_path)])
        called_cmd = mock_run.call_args[0][0]
        # The command list must contain "-m" and "shenbi.gates.cli"
        assert "-m" in called_cmd, f"expected -m flag, got {called_cmd}"
        assert "shenbi.gates.cli" in called_cmd, (
            f"expected shenbi.gates.cli module, got {called_cmd}"
        )
        # Must NOT reference the deleted file
        assert not any("validate-gate.py" in str(part) for part in called_cmd), (
            f"run_gate still references deleted tests/validate-gate.py: {called_cmd}"
        )

    @patch("shenbi.phase_runner.subprocess.run")
    def test_returns_parsed_json_on_success(self, mock_run, tmp_path):
        """Non-regression: success path still returns parsed JSON."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"status": "PASS", "checks": []}', stderr=""
        )
        result = run_gate("G2", ["file.md", "chapter", str(tmp_path)])
        assert result["status"] == "PASS"

    @patch("shenbi.phase_runner.subprocess.run")
    def test_returns_fail_dict_on_oserror(self, mock_run, tmp_path):
        """If subprocess.run raises OSError (e.g. python binary missing), run_gate
        must return a FAIL dict, not propagate the exception.

        NOTE: FileNotFoundError subclasses OSError (NOT subprocess.SubprocessError).
        This test guards the except clause catches the right hierarchy.
        """
        mock_run.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'python3'")
        result = run_gate("G4", ["skill", "file.md", str(tmp_path)])
        assert result["status"] == "FAIL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/phase_runner/test_run_gate_uses_cli_module.py -v`
Expected: **Test 1 (`test_calls_gates_cli_module_not_validate_gate_py`) FAILs** — the current code's command list contains `"validate-gate.py"` (assertion fails). Test 2 passes already (non-regression). **Test 3 (`test_returns_fail_dict_on_oserror`) errors** — the current `except (json.JSONDecodeError, ValueError)` does not catch `FileNotFoundError` (an `OSError`), so the mock's side_effect propagates as an unhandled exception.

- [ ] **Step 3: Write minimal implementation**

Replace `run_gate` in `src/shenbi/phase_runner.py:54-66` with:

```python
def run_gate(gate: str, args: list[str]) -> dict[str, Any]:
    """Run a gate via the live ``shenbi.gates.cli`` module, return parsed JSON.

    Gate logic was extracted from the legacy ``tests/validate-gate.py`` into
    ``src/shenbi/gates/`` (PR-19). This function targets the module directly
    via ``python -m shenbi.gates.cli``, matching ``dispatch_helper.run_gate_g3/g4``.
    """
    r = subprocess.run(
        [sys.executable, "-m", "shenbi.gates.cli", gate] + args,
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        return cast(dict[str, Any], json.loads(r.stdout))
    except (json.JSONDecodeError, ValueError, OSError):
        return {"status": GateStatus.FAIL, "raw_stdout": r.stdout, "raw_stderr": r.stderr}
```

Key changes: (1) `[sys.executable, "-m", "shenbi.gates.cli", gate]` replaces `[sys.executable, vg, gate]`; (2) `OSError` added to the except clause to catch `FileNotFoundError` (which subclasses `OSError`, **not** `subprocess.SubprocessError` — verified empirically). This makes run_gate robust if `sys.executable` itself is ever missing.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/phase_runner/test_run_gate_uses_cli_module.py -v`
Expected: PASS (3 tests) — test 1 now passes (command uses `shenbi.gates.cli`), test 3 now passes (`OSError` in the except clause catches `FileNotFoundError`).

- [ ] **Step 5: Run full check**

Run: `just check`
Expected: PASS (ruff + mypy + basedpyright + pytest --cov-fail-under=85). If coverage drops, the new test file adds coverage for `run_gate`.

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/phase_runner.py tests/unit/phase_runner/test_run_gate_uses_cli_module.py
git commit -m "fix(phase_runner): redirect run_gate to live shenbi.gates.cli module

run_gate() subprocess-called tests/validate-gate.py, deleted in PR-19 when
gate logic moved to src/shenbi/gates/. subprocess.run against the missing
file returned returncode=2 + empty stdout, so json.loads('') threw
JSONDecodeError → every gate returned a misleading FAIL regardless of real
gate logic, blocking shenbi-phase start/finalize. Now targets
python -m shenbi.gates.cli (matching dispatch_helper), and adds OSError to
the except clause to catch FileNotFoundError if sys.executable is missing."
```

---

### Task 2: Fix `scoring.py` dead gate paths (P0.1 — secondary)

**Files:**
- Modify: `src/shenbi/scoring.py:295-308` (`--gate-only` block) and `:328-350` (tier-gate integration block)
- Test: `tests/unit/test_scoring.py` (existing file — add two test functions)

**Interfaces:**
- Consumes: `shenbi.gates.cli`
- Produces: no interface change — `scoring.main()` behavior unchanged, only internal subprocess targets fixed.

**Context:** Two blocks in `scoring.py` construct `vg = str(Path(__file__).resolve().parents[2] / "tests" / "validate-gate.py")` (`:303` and `:332`) — the same dead path as Task 1. These fire when `shenbi-score` is called with `--gate-only` or `--tier T1`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_scoring.py` (append at end of file, inside a new test class):

```python
class TestScoringGatePath:
    """Regression: scoring.py --gate-only and --tier blocks must not reference
    the deleted tests/validate-gate.py. They must target shenbi.gates.cli."""

    def test_gate_only_uses_cli_module(self, tmp_path, monkeypatch):
        """--gate-only must invoke python -m shenbi.gates.cli, not validate-gate.py."""
        import shenbi.scoring as scoring_mod

        captured_cmds: list[list[str]] = []

        class FakeCompleted:
            returncode = 0
            stdout = '{"status": "PASS"}'
            stderr = ""

        def fake_run(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            return FakeCompleted()

        # NOTE: scoring.py imports subprocess INSIDE its functions (line 296, 330),
        # so shenbi.scoring has no module-level `subprocess` attribute. Patch the
        # global subprocess.run instead — the function-local import binds to the
        # same shared module object.
        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr(scoring_mod.sys, "argv", [
            "shenbi-score", "--gate-only", "G2", "--files", str(tmp_path / "f.md"),
            "--type", "chapter",
        ])

        try:
            scoring_mod.main()
        except SystemExit:
            pass  # --gate-only calls sys.exit()

        assert captured_cmds, "no subprocess captured — --gate-only path not reached"
        # Check the last captured command (the gate call)
        cmd = captured_cmds[-1]
        assert "-m" in cmd, f"expected -m flag, got {cmd}"
        assert "shenbi.gates.cli" in cmd
        assert not any("validate-gate.py" in str(p) for p in cmd), (
            f"scoring --gate-only still references deleted validate-gate.py: {cmd}"
        )

    def test_tier_t1_gate_uses_cli_module(self, tmp_path, monkeypatch):
        """The --tier T1 integration block (scoring.py:332) must also target
        shenbi.gates.cli, not validate-gate.py. This covers the second dead-path
        site that test_gate_only_uses_cli_module does not exercise."""
        import shenbi.scoring as scoring_mod

        captured_cmds: list[list[str]] = []

        class FakeCompleted:
            returncode = 0
            stdout = '{"status": "PASS"}'
            stderr = ""

        def fake_run(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            return FakeCompleted()

        monkeypatch.setattr("subprocess.run", fake_run)
        # Build a minimal rubric file so load_rubric doesn't crash
        rubric = tmp_path / "rubric.md"
        rubric.write_text(
            "| # | Dimension | Weight |\n|---|---|---|\n| 1 | Quality | 100% |\n",
            encoding="utf-8",
        )
        scores = tmp_path / "scores.json"
        scores.write_text('{"1": 90}', encoding="utf-8")
        round_dir = tmp_path / "round"
        round_dir.mkdir()
        monkeypatch.setattr(scoring_mod.sys, "argv", [
            "shenbi-score", str(rubric), str(scores),
            "--test-type", "generative", "--tier", "T1",
            "--round-dir", str(round_dir),
        ])

        try:
            scoring_mod.main()
        except SystemExit:
            pass

        gate_cmds = [c for c in captured_cmds if "gates.cli" in c or "validate-gate" in " ".join(c)]
        if gate_cmds:  # only assert if the tier path fired a gate subprocess
            cmd = gate_cmds[-1]
            assert not any("validate-gate.py" in str(p) for p in cmd), (
                f"scoring --tier T1 still references deleted validate-gate.py: {cmd}"
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_scoring.py::TestScoringGatePath -v`
Expected: `test_gate_only_uses_cli_module` FAILs (current code's captured command contains `validate-gate.py`). `test_tier_t1_gate_uses_cli_module` may pass vacuously if the tier path doesn't fire without a real round_dir setup — that's acceptable; it guards against regression once the path fires.

- [ ] **Step 3: Write minimal implementation**

**Fix 1 — `--gate-only` block (`scoring.py:303`):** Replace:

```python
        vg = str(Path(__file__).resolve().parents[2] / "tests" / "validate-gate.py")
        proc_result = subprocess.run(
            [sys.executable, vg, gate_type, ",".join(files), ftype], capture_output=True, text=True
        )
```

with:

```python
        proc_result = subprocess.run(
            [sys.executable, "-m", "shenbi.gates.cli", gate_type, ",".join(files), ftype],
            capture_output=True,
            text=True,
        )
```

**Fix 2 — tier-gate block (`scoring.py:332`):** Replace:

```python
        vg = str(Path(__file__).resolve().parents[2] / "tests" / "validate-gate.py")
        if tier == "T1" and test_type:
```

with:

```python
        if tier == "T1" and test_type:
```

and update the subprocess call at `:340` from `[sys.executable, vg, "G3", ...]` to `[sys.executable, "-m", "shenbi.gates.cli", "G3", ...]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_scoring.py::TestScoringGatePath -v`
Expected: PASS.

- [ ] **Step 5: Run full check**

Run: `just check`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/scoring.py tests/unit/test_scoring.py
git commit -m "fix(scoring): redirect --gate-only and --tier blocks to shenbi.gates.cli

Same dead-path bug as phase_runner: scoring.py constructed a path to the
deleted tests/validate-gate.py in its --gate-only and --tier T1 blocks.
Now targets python -m shenbi.gates.cli."
```

---

### Task 3: Replace dead `shenbi-progress` subprocess with direct `progress.json` update (P0.2)

**Files:**
- Modify: `src/shenbi/dispatcher/modes/codex.py:83-87` (the `shenbi-progress mark-done` call)
- Test: `tests/unit/dispatcher/test_codex_mark_done.py` (new file)

**Interfaces:**
- Consumes: `shenbi.safe_write.safe_write`, `pathlib.Path`, `json`
- Produces: `dispatch_codex()` return behavior unchanged (still returns 0 on success). The side effect changes from "call a non-existent CLI" to "directly update `progress.json`".

**Context:** `codex.py:84-87` calls `uv run shenbi-progress mark-done <round_dir> <skill> <test_type> <final>`, but `shenbi-progress` is **not registered** in `pyproject.toml [project.scripts]` and no such module exists in `src/shenbi/`. The historical `tests/update-progress.py` that implemented `mark-done` was deleted. The `codex.py` path is the T1 test-harness dispatch mode (fires when `codex` CLI is on PATH); it runs after `shenbi-score` succeeds (line 64-79) and extracts the final score (line 83). The fix: write the completion record directly to `progress.json` using the project's `safe_write` utility, appending to `completed_skill_names` and recording the score in the `skills` dict — mirroring how `g_dispatch.py` reads it.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/dispatcher/test_codex_mark_done.py`:

```python
"""Verify dispatch_codex records completion via direct progress.json update,
not via the non-existent shenbi-progress CLI subprocess.

Regression for the shenbi-progress entry point that was never registered in
pyproject.toml (historical tests/update-progress.py was deleted).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from shenbi.dispatcher.modes.codex import dispatch_codex


class TestCodexMarkDone:
    def test_writes_completion_to_progress_json(self, tmp_path):
        """After a successful codex dispatch+score, progress.json must contain
        the skill in completed_skill_names with its score — written directly,
        not via a shenbi-progress subprocess."""
        round_dir = tmp_path / "round-001"
        round_dir.mkdir()
        (round_dir / "t1-reports").mkdir()

        # Mock the two real subprocesses: codex exec + shenbi-score.
        # codex exec writes a raw scores file; shenbi-score outputs final JSON.
        def fake_run(cmd, **kwargs):
            class FakeResult:
                returncode = 0
                # shenbi-score outputs a JSON with final_score
                stdout = json.dumps({"final_score": 92, "status": "ok"})
                stderr = ""

            return FakeResult()

        # Pre-create the raw output file that codex exec would produce
        # (dispatch_codex reads it to extract scores JSON)
        raw_file = round_dir / "t1-reports" / "shenbi-worldbuilding-generative-scores-subagent.raw"
        raw_file.write_text('{"1": 90, "2": 95}', encoding="utf-8")

        with patch("shenbi.dispatcher.modes.codex.subprocess.run", side_effect=fake_run):
            rc = dispatch_codex(
                "shenbi-worldbuilding", "generative", round_dir,
                "test prompt", "agent-001",
            )

        assert rc == 0
        # progress.json must now exist and record completion
        progress_path = round_dir / "progress.json"
        assert progress_path.exists(), "progress.json was not written"
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        assert "shenbi-worldbuilding" in progress.get("completed_skill_names", []), (
            f"skill not in completed_skill_names: {progress}"
        )

    def test_does_not_call_shenbi_progress_subprocess(self, tmp_path):
        """No subprocess command may contain 'shenbi-progress'."""
        round_dir = tmp_path / "round-002"
        round_dir.mkdir()
        (round_dir / "t1-reports").mkdir()
        raw_file = round_dir / "t1-reports" / "shenbi-worldbuilding-generative-scores-subagent.raw"
        raw_file.write_text('{"1": 90}', encoding="utf-8")

        captured_cmds: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            class FakeResult:
                returncode = 0
                stdout = json.dumps({"final_score": 90})
                stderr = ""
            return FakeResult()

        with patch("shenbi.dispatcher.modes.codex.subprocess.run", side_effect=fake_run):
            dispatch_codex("shenbi-worldbuilding", "generative", round_dir, "p", "a")

        for cmd in captured_cmds:
            assert not any("shenbi-progress" in str(part) for part in cmd), (
                f"shenbi-progress subprocess still called: {cmd}"
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/dispatcher/test_codex_mark_done.py -v`
Expected: FAIL — (1) `test_writes_completion_to_progress_json` fails because the current code calls `shenbi-progress` with `check=True`, which raises `CalledProcessError`/`FileNotFoundError` since the script doesn't exist. (2) `test_does_not_call_shenbi_progress_subprocess` fails because the command list contains `"shenbi-progress"`.

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/dispatcher/modes/codex.py`, replace lines 83-87:

```python
    final = json.loads(result.stdout).get("final_score", 0)
    subprocess.run(
        ["uv", "run", "shenbi-progress", "mark-done", str(round_dir), skill, test_type, str(final)],
        check=True,
    )
```

with a direct `progress.json` update:

```python
    final = json.loads(result.stdout).get("final_score", 0)
    _record_completion(round_dir, skill, test_type, final)
```

And add this helper function above `dispatch_codex` (after the imports):

```python
def _record_completion(
    round_dir: Path, skill: str, test_type: str, score: float
) -> None:
    """Record skill completion directly into progress.json.

    Replaces the historical ``shenbi-progress mark-done`` subprocess, which
    invoked an entry point never registered in pyproject.toml. Mirrors how
    gate logic (g_dispatch.py) reads completed_skill_names.
    """
    from shenbi.safe_write import safe_write

    progress_path = round_dir / "progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    else:
        progress = {"completed_skill_names": [], "skills": {}}

    completed = progress.setdefault("completed_skill_names", [])
    if skill not in completed:
        completed.append(skill)

    skills = progress.setdefault("skills", {})
    skill_entry = skills.setdefault(skill, {})
    skill_entry[test_type] = {"score": score, "status": "done"}

    safe_write(progress_path, json.dumps(progress, indent=2, ensure_ascii=False))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/dispatcher/test_codex_mark_done.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run full check**

Run: `just check`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/dispatcher/modes/codex.py tests/unit/dispatcher/test_codex_mark_done.py
git commit -m "fix(dispatcher/codex): replace dead shenbi-progress call with direct progress.json update

codex.py called 'uv run shenbi-progress mark-done', but shenbi-progress was
never registered in pyproject.toml [project.scripts] (the historical
tests/update-progress.py that implemented it was deleted). The call used
check=True so it crashed on every codex-mode dispatch. Now writes
completed_skill_names + score directly to progress.json via safe_write,
mirroring how g_dispatch.py reads it."
```

---

### Task 4: Remove dead `codex-api` branch from `executor.py` (P0.4)

**Files:**
- Modify: `src/shenbi/dispatcher/executor.py:237-240` (remove the `codex-api` branch)
- Modify: `src/shenbi/dispatcher/modes/codex_api.py:1-15` (add DEPRECATED marker)
- Modify: `tests/unit/test_dispatcher_executor.py:249-268` (delete obsolete `test_dispatch_routes_to_codex_api` — the route no longer exists)
- Test: `tests/unit/dispatcher/test_executor_no_codex_api.py` (new file)

**Interfaces:**
- Consumes: `shenbi.dispatcher.modes.codex.dispatch_codex`, `shenbi.dispatcher.modes.internal.dispatch_internal`
- Produces: `dispatch()` no longer has a `codex-api` code path. `detect_mode()` is unchanged (already only returns `"codex"` or `"internal"`).

**Context:** `executor.py:237-240` has a branch `if mode == "codex-api": ...` that imports and calls `dispatch_codex_api`, which is a `NoReturn` raise stub. But `detect_mode()` (`:164-174`) only ever returns `"codex"` or `"internal"` — so this branch is **unreachable dead code**. The spec decision (§3) is that API dispatch is handled by `dispatch_helper._dispatch_via_api`, not a separate codex_api mode.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/dispatcher/test_executor_no_codex_api.py`:

```python
"""Verify dispatch() has no reachable codex-api code path.

detect_mode() only returns 'codex' or 'internal'. The codex-api branch was
unreachable dead code. This test verifies the behavior (not source text): even
if detect_mode returned 'codex-api', dispatch must fall through to internal,
never call dispatch_codex_api.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch


class TestNoCodexApiBranch:
    def test_codex_api_mode_falls_through_to_internal(self, monkeypatch, tmp_path):
        """Behavioral test: if detect_mode somehow returned 'codex-api', dispatch()
        must NOT call dispatch_codex_api — it must fall through to internal mode.

        This is stronger than a source grep: it proves runtime unreachability
        and won't break on cosmetic edits (e.g. a comment mentioning codex-api).
        """
        import shenbi.dispatcher.executor as exec_mod
        import shenbi.dispatcher.modes.codex_api as codex_api_mod
        from shenbi.dispatcher.executor import dispatch

        # Force detect_mode to return the removed mode value
        monkeypatch.setattr(exec_mod, "detect_mode", lambda: "codex-api")
        # Stub G1 (run_g1) so dispatch doesn't crash on missing files
        monkeypatch.setattr(exec_mod, "run_g1", lambda *a, **kw: {"status": "PASS"})
        # Spy on dispatch_codex_api — if called, the dead branch survived
        codex_api_called: list[bool] = []

        def spy(*a, **kw):
            codex_api_called.append(True)
            return 0

        monkeypatch.setattr(codex_api_mod, "dispatch_codex_api", spy)

        round_dir = tmp_path / "round"
        round_dir.mkdir()
        # dispatch should return without calling codex_api (falls to internal)
        rc = dispatch("shenbi-worldbuilding", "generative", round_dir, "test")
        assert not codex_api_called, (
            "dispatch_codex_api was called — the dead codex-api branch still routes to it"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/dispatcher/test_executor_no_codex_api.py -v`
Expected: FAIL — before the fix, `dispatch()` with `detect_mode() == "codex-api"` still hits the `if mode == "codex-api"` branch (line 237) and calls the spied `dispatch_codex_api`, so `codex_api_called` is `[True]` and the assertion fails.

- [ ] **Step 3: Write minimal implementation**

In `src/shenbi/dispatcher/executor.py`, delete lines 237-240:

```python
    if mode == "codex-api":
        from shenbi.dispatcher.modes.codex_api import dispatch_codex_api

        return dispatch_codex_api(skill, test_type, round_dir, prompt, agent_id)
```

The function now flows directly from the `codex` branch (line 233-236) to the `internal` fallback (line 241-243).

In `src/shenbi/dispatcher/modes/codex_api.py`, replace the module docstring (line 1) with:

```python
"""DEPRECATED: codex-api dispatch mode — superseded by unified API executor.

This mode was never reachable: detect_mode() only returns 'codex' or
'internal', and the executor.py branch that referenced it was removed (P0.4).
API dispatch is handled by pipeline/dispatch_helper._dispatch_via_api.

Safe to delete entirely in the next minor release.
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/dispatcher/test_executor_no_codex_api.py -v`
Expected: PASS.

- [ ] **Step 5: Delete the obsolete test for the removed route**

The existing test `test_dispatch_routes_to_codex_api` in `tests/unit/test_dispatcher_executor.py:249-268` asserts that `dispatch()` routes to `dispatch_codex_api` when `detect_mode` returns `"codex-api"`. Since we just removed that route, this test is obsolete and must be deleted — otherwise it still passes (internal returns 0) but tests nothing real, or fails depending on the spy.

Delete the entire function `test_dispatch_routes_to_codex_api` (lines 249-268, including its `@pytest.mark.unit` decorator at line 249). Do not leave a stub.

(Note: `test_dispatch_codex_api_raises_dispatcher_error` in `tests/unit/test_dispatcher_modes.py:32-35` tests `codex_api.py` *directly* — not via `dispatch()` — so it survives and correctly documents that the stub raises. Leave it.)

- [ ] **Step 6: Run full check**

Run: `just check`
Expected: PASS. If `test_dispatch_routes_to_codex_api` was not fully deleted, pytest will error on the removed route — re-check Step 5.

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/dispatcher/executor.py src/shenbi/dispatcher/modes/codex_api.py tests/unit/dispatcher/test_executor_no_codex_api.py tests/unit/test_dispatcher_executor.py
git commit -m "fix(dispatcher): remove unreachable codex-api dead branch

executor.py had a 'codex-api' mode branch that imported dispatch_codex_api
(a NoReturn stub), but detect_mode() only returns 'codex' or 'internal' —
so the branch was unreachable. API dispatch lives in
pipeline/dispatch_helper._dispatch_via_api. codex_api.py marked DEPRECATED.
Deleted the obsolete test_dispatch_routes_to_codex_api (route no longer exists)."
```

---

### Task 5: Remove misleading `rollback` CLI registration (P0.3)

**Files:**
- Modify: `src/shenbi/pipeline/cli.py:12` (remove `rollback` from docstring commands)
- Modify: `src/shenbi/pipeline/cli.py:784-798` (change `cmd_rollback` to return error code)
- Modify: `src/shenbi/pipeline/cli.py:839-842` (remove the `rollback` subparser registration)
- Modify: `tests/unit/pipeline/test_cli.py:528` (update `TestRollbackCommand` assertion: `rc == 0` → `rc != 0`)
- Modify: `tests/unit/pipeline/test_e2e.py:178` (remove `"rollback"` from the command-iteration loop — the subcommand is no longer registered)
- Test: `tests/unit/pipeline/test_cli_rollback_removed.py` (new file)

**Interfaces:**
- Consumes: nothing new
- Produces: `pipeline --help` no longer lists `rollback`. Calling `pipeline rollback ...` now returns exit code 1 with a clear "not implemented" error (instead of exit 0 masquerading as success).

**Context:** `cmd_rollback` (`:784-798`) returns `{"status": "not_implemented"}` but exit code 0 — misleadingly signaling success. The CLI docstring (`:12`) and subparser (`:839-842`) advertise it as a real command. Per spec P0.3, we remove the subparser registration now (so `--help` is honest) and make `cmd_rollback` return a non-zero exit code with a clear message. The actual snapshot-based rollback implementation is deferred (spec §9).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/pipeline/test_cli_rollback_removed.py`:

```python
"""Verify the rollback subcommand is removed from CLI registration.

cmd_rollback still exists (for direct callers) but returns a non-zero exit
code. The subparser is removed so 'pipeline --help' doesn't advertise an
unimplemented command.
"""

from __future__ import annotations

import io
from pathlib import Path

from shenbi.pipeline.cli import main


class TestRollbackRemoved:
    def test_help_does_not_list_rollback(self, capsys):
        """'pipeline --help' output must not contain 'rollback'."""
        with __import__("pytest").raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "rollback" not in captured.out.lower(), (
            f"--help still advertises rollback: {captured.out}"
        )

    def test_cmd_rollback_returns_nonzero(self, tmp_path):
        """Direct cmd_rollback call must return exit code >= 1 (not 0)."""
        from shenbi.pipeline.cli import cmd_rollback
        import argparse

        args = argparse.Namespace(project_dir=str(tmp_path), chapter=5)
        rc = cmd_rollback(args)
        assert rc != 0, f"cmd_rollback returned {rc}, expected non-zero (not faking success)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/pipeline/test_cli_rollback_removed.py -v`
Expected: FAIL — (1) `test_help_does_not_list_rollback` fails because the subparser is still registered. (2) `test_cmd_rollback_returns_nonzero` fails because `cmd_rollback` returns 0.

- [ ] **Step 3: Write minimal implementation**

**Fix 1 — docstring (`cli.py:12`):** Remove the line:

```
    rollback <project-dir> --chapter <N>
```

**Fix 2 — subparser (`cli.py:839-842`):** Delete:

```python
    p_rollback = sub.add_parser("rollback", help="Rollback to chapter snapshot")
    p_rollback.add_argument("project_dir", type=str)
    p_rollback.add_argument("--chapter", type=int, required=True)
    p_rollback.set_defaults(func=cmd_rollback)
```

**Fix 3 — `cmd_rollback` (`cli.py:784-798`):** Replace the function body to return 1:

```python
def cmd_rollback(args: argparse.Namespace) -> int:
    """Rollback to a chapter snapshot.

    Not yet implemented — requires snapshot integration (deferred to a future
    spec, see docs/superpowers/specs/2026-07-16-pipeline-maturity-and-bp-fixes-design.md §9).
    The subparser registration has been removed so 'pipeline --help' does not
    advertise this command. This function is retained for direct callers and
    returns a non-zero exit code.
    """
    project_dir = Path(args.project_dir)
    log.info("rollback_not_implemented", project_dir=str(project_dir), chapter=args.chapter)
    emit_json(
        {
            "status": "not_implemented",
            "message": (
                "Rollback requires snapshot integration (deferred to future spec). "
                "See docs/superpowers/specs/2026-07-16-pipeline-maturity-and-bp-fixes-design.md §9."
            ),
        }
    )
    return 1
```

Key change: `return 0` → `return 1`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/pipeline/test_cli_rollback_removed.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Update existing tests that depend on the removed/changed rollback behavior**

Two existing tests break after the implementation changes in Step 3. Fix them:

**Fix 5a — `tests/unit/pipeline/test_cli.py:528`:** The `TestRollbackCommand.test_rollback_not_implemented` test asserts `rc == 0`. Since `cmd_rollback` now returns 1, change the assertion. In `tests/unit/pipeline/test_cli.py`, find line 528:

```python
        assert rc == 0
        assert result["status"] == "not_implemented"
```

Replace with:

```python
        assert rc != 0, "rollback should return non-zero (not faking success)"
        assert result["status"] == "not_implemented"
```

Also update the test's docstring (line 522) from "reports not_implemented until snapshot integration lands" to "returns non-zero not_implemented until snapshot integration lands".

**Fix 5b — `tests/unit/pipeline/test_e2e.py:178`:** The `test_pipeline_commands_emit_valid_json` test iterates over a tuple of commands including `"rollback"`. Since the `rollback` subparser is removed, argparse will raise `SystemExit(2)` for it. Remove it from the tuple. In `tests/unit/pipeline/test_e2e.py`, find lines 173-178:

```python
            for argv in (
                ["status", str(project_dir)],
                ["chapters", str(project_dir)],
                ["next", str(project_dir)],
                ["resume", str(project_dir)],
                ["rollback", str(project_dir), "--chapter", "1"],
            ):
```

Replace with (remove the rollback line):

```python
            for argv in (
                ["status", str(project_dir)],
                ["chapters", str(project_dir)],
                ["next", str(project_dir)],
                ["resume", str(project_dir)],
            ):
```

- [ ] **Step 6: Run full check**

Run: `just check`
Expected: PASS. If it fails, grep for any remaining `rollback` references in tests and remove them — the subcommand is gone.

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/cli.py tests/unit/pipeline/test_cli_rollback_removed.py tests/unit/pipeline/test_cli.py tests/unit/pipeline/test_e2e.py
git commit -m "fix(pipeline/cli): remove misleading rollback subcommand registration

cmd_rollback returned exit 0 with status 'not_implemented' — faking success.
The CLI docstring and subparser advertised it as a real command. Now: (1)
subparser removed so --help doesn't list it, (2) cmd_rollback returns exit 1,
(3) docstring updated. Updated test_cli.py (rc != 0) and test_e2e.py (removed
rollback from command loop). Real rollback deferred to future snapshot spec."
```

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/cli.py tests/unit/pipeline/test_cli_rollback_removed.py
git commit -m "fix(pipeline/cli): remove misleading rollback subcommand registration

cmd_rollback returned exit 0 with status 'not_implemented' — faking success.
The CLI docstring and subparser advertised it as a real command. Now: (1)
subparser removed so --help doesn't list it, (2) cmd_rollback returns exit 1,
(3) docstring updated. Real rollback deferred to future snapshot-integration spec."
```

---

## Self-Review

**1. Spec coverage (§4 P0.1–P0.4):**
- P0.1 (phase_runner dead path) → Task 1 ✓ (primary) + Task 2 ✓ (scoring.py secondary — same bug, two locations)
- P0.2 (shenbi-progress unregistered) → Task 3 ✓
- P0.3 (rollback stub) → Task 5 ✓
- P0.4 (codex_api dead branch) → Task 4 ✓
- P0.5 (end-to-end run) → **intentionally not in this plan** — it's an execution milestone, not a code task; depends on Tasks 1-4 + API key + spec §3 backend. Listed in spec §4 as the capstone.

**2. Placeholder scan:** No "TBD", "TODO", "add error handling", or code-less steps. Every step has actual code. ✓

**3. Type consistency:**
- `run_gate(gate: str, args: list[str]) -> dict[str, Any]` — unchanged signature across Task 1 ✓
- `_record_completion(round_dir: Path, skill: str, test_type: str, score: float) -> None` — defined in Task 3, no later task references it ✓
- `cmd_rollback(args: argparse.Namespace) -> int` — returns int in both old and new (Task 5) ✓
- `dispatch_codex(...) -> int` — unchanged (Task 3 only changes internal side effect) ✓

**4. Code-review fixes applied (post-review):**
- C1+C2: Task 1 except clause `subprocess.SubprocessError` → `OSError` (FileNotFoundError subclasses OSError, NOT SubprocessError — verified empirically); defect narrative corrected from "crash" to "misleading FAIL" (subprocess.run against missing file returns rc=2, doesn't raise).
- C3: Task 2 test patch target `scoring_mod.subprocess.run` → `"subprocess.run"` (scoring.py imports subprocess function-local, so no module attribute).
- C4-a: Task 4 added Step 5 to delete obsolete `test_dispatch_routes_to_codex_api`.
- C4-b: Task 5 added Step 5 to update `test_cli.py` (rc==0→!=0) and `test_e2e.py` (remove rollback from command loop).
- I3: Task 4 test changed from fragile source-grep to behavioral (proves runtime unreachability).
- I4: Task 2 added `test_tier_t1_gate_uses_cli_module` for the second dead-path site.

No gaps found. Plan is ready.
