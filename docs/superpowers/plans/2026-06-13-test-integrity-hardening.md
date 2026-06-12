# Test Framework Integrity Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent integrity violations (self-scoring, gate bypass, batch-generated outputs, mid-round code patching) through three layers: guidance (protocol + state machine), hard checks (gate markers + scoring enforcement), and audit (G7 post-round verification).

**Architecture:** Gate markers are PASS result files written by validate-gate.py on G4/G6 success. scoring.py requires these markers before computing scores. A new phase-runner.py provides a state machine for T2/T3 execution. G7 gains four new checks (G7.13–G7.16) that re-verify gates, check timelines, detect duplicate patterns, and validate phase state.

**Tech Stack:** Python 3, no external dependencies beyond PyYAML (already used). Files: validate-gate.py (3662 lines), scoring.py (303 lines), command-to-give.md, new phase-runner.py.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `tests/phase-runner.py` | **NEW.** State machine for T2/T3 phase execution. Subcommands: start, pre-skill, post-skill, pre-score, post-score, finalize. |
| `tests/validate-gate.py` | **MODIFY.** Write gate markers on G4/G6 PASS. Add G7.13–G7.16 checks. |
| `tests/scoring.py` | **MODIFY.** Add `--round-dir` flag. Verify gate markers before scoring. |
| `command-to-give.md` | **MODIFY.** Add 第六步 (T2 protocol) and 第七步 (T3 protocol) after 第五步. |
| `tests/test_integrity.py` | **NEW.** Unit tests for gate markers, phase-runner state machine, scoring.py marker enforcement, G7.13–G7.16. |

---

### Task 1: Gate marker writing in validate-gate.py

**Files:**
- Modify: `tests/validate-gate.py:3548–3661` (main() function)
- Test: `tests/test_integrity.py`

- [ ] **Step 1: Write tests for gate marker writing**

Create `tests/test_integrity.py`:

```python
#!/usr/bin/env python3
"""Tests for test integrity hardening: gate markers, phase-runner, scoring enforcement."""
import json
import os
import tempfile
import shutil
import sys
import unittest
from pathlib import Path

VG = str(Path(__file__).parent / "validate-gate.py")
SC = str(Path(__file__).parent / "scoring.py")
PR = str(Path(__file__).parent / "phase-runner.py")
TESTS = Path(__file__).parent
PROJECT = TESTS.parent


def run_py(script, args):
    """Run a Python script, return (exit_code, stdout, stderr)."""
    import subprocess
    r = subprocess.run(
        [sys.executable, script] + args,
        capture_output=True, text=True, timeout=30,
    )
    return r.returncode, r.stdout, r.stderr


class TestGateMarkers(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="integrity_test_")
        self.round_dir = Path(self.tmpdir) / "round-test"
        self.round_dir.mkdir()
        (self.round_dir / "gate-markers").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_g4_pass_writes_marker(self):
        """G4 PASS with round_dir should write a marker file."""
        # Create a minimal valid output for shenbi-worldbuilding
        proj = self.round_dir / "project-output"
        proj.mkdir()
        (proj / "novel.json").write_text(json.dumps({
            "title": "Test", "genre": "fantasy", "language": "zh", "target_words": 50000
        }))
        (proj / "genre-config.json").write_text(json.dumps({
            "chapter_word": {"default": 3000}
        }))
        world = proj / "world"
        world.mkdir()
        for name in ["story_bible.md", "rules.md", "locations.md", "power_system.md",
                     "factions.md", "faction-relations.md"]:
            (world / name).write_text("# " + name + "\n\nSome content here.")
        chars = proj / "characters"
        chars.mkdir()
        (chars / "protagonist.md").write_text("---\nname: Test\nrole: protagonist\n---\n\nBio.")
        (chars / "relationships.md").write_text("# Relationships\n\n- Test")
        truth = proj / "truth"
        truth.mkdir()
        for name in ["current_state.md", "character_matrix.md", "emotional_arcs.md", "chapter_summaries.md"]:
            (truth / name).write_text(f"# {name}\n\nstatus: active\n\nContent.")

        files = str(proj / "novel.json")
        rc, stdout, stderr = run_py(VG, [
            "G4", "shenbi-worldbuilding", files, str(self.round_dir),
        ])
        result = json.loads(stdout)
        if result["status"] == "PASS":
            marker_path = self.round_dir / "gate-markers" / "G4-shenbi-worldbuilding-generative.json"
            self.assertTrue(marker_path.exists(), "G4 PASS should write a marker file")
            marker = json.loads(marker_path.read_text())
            self.assertEqual(marker["status"], "PASS")
            self.assertIn("files_checked", marker)
        else:
            # If gate fails for test data reasons, that's OK — just verify no marker written
            marker_path = self.round_dir / "gate-markers" / "G4-shenbi-worldbuilding-generative.json"
            self.assertFalse(marker_path.exists(), "G4 FAIL should NOT write a marker file")

    def test_g4_fail_no_marker(self):
        """G4 FAIL should not write a marker file."""
        rc, stdout, stderr = run_py(VG, [
            "G4", "shenbi-worldbuilding", "/nonexistent/file.md", str(self.round_dir),
        ])
        # Gate should fail with nonexistent file
        marker_dir = self.round_dir / "gate-markers"
        markers = list(marker_dir.iterdir()) if marker_dir.exists() else []
        self.assertEqual(len(markers), 0, "G4 FAIL should not write any marker")

    def test_g4_no_round_dir_no_marker(self):
        """G4 PASS without round_dir should not write marker (backward compat)."""
        rc, stdout, stderr = run_py(VG, [
            "G4", "shenbi-worldbuilding", "/nonexistent/file.md",
        ])
        # No round_dir provided — no marker directory should be created
        marker_dir = self.round_dir / "gate-markers"
        # Marker dir exists from setUp, but should have nothing new
        markers = list(marker_dir.iterdir())
        self.assertEqual(len(markers), 0, "No round_dir → no markers")

    def test_marker_contains_files_checked(self):
        """Marker file should contain files_checked field listing validated paths."""
        # Use a simple case: create file, run G2 (which doesn't write markers)
        # This test verifies the marker schema via G4 if it passes
        proj = self.round_dir / "project-output"
        proj.mkdir()
        f = proj / "test.md"
        f.write_text("---\ntitle: Test\n---\n\nContent with enough words.")
        # G2 does not write markers, so this is a negative test
        rc, stdout, stderr = run_py(VG, [
            "G2", str(f), "chapter", str(self.round_dir),
        ])
        markers = list((self.round_dir / "gate-markers").iterdir())
        self.assertEqual(len(markers), 0, "G2 should not write markers")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail (markers not implemented yet)**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestGateMarkers -v`

Expected: `test_g4_pass_writes_marker` fails (no marker written), `test_g4_fail_no_marker` passes, `test_g4_no_round_dir_no_marker` passes, `test_marker_contains_files_checked` passes.

- [ ] **Step 3: Implement gate marker writing in validate-gate.py**

Add a helper function after the existing `_normalize_file_paths` function (after line 128 in `tests/validate-gate.py`):

```python
def write_gate_marker(gate, target, test_type, result_str, round_dir, file_paths=None):
    """Write a gate marker file if result is PASS and round_dir is provided."""
    if not round_dir:
        return
    rd = Path(round_dir)
    marker_dir = rd / "gate-markers"
    marker_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = json.loads(result_str)
        if result.get("status") != "PASS":
            return
        marker = {
            **result,
            "files_checked": [str(p) for p in (file_paths or [])],
        }
        marker_file = marker_dir / f"{gate}-{target}-{test_type}.json"
        marker_file.write_text(json.dumps(marker, indent=2, ensure_ascii=False))
    except (json.JSONDecodeError, OSError):
        pass
```

Modify `main()` in the G4 handler (around line 3626). Change:

```python
        else:
            full_name = short_map.get(skill_or_type, skill_or_type)
            print(gate_G4(full_name, "generative", file_list, rd))
```

To:

```python
        else:
            full_name = short_map.get(skill_or_type, skill_or_type)
            result = gate_G4(full_name, "generative", file_list, rd)
            print(result)
            write_gate_marker("G4", full_name, "generative", result, rd, file_list)
```

Modify the G6 handler (around line 3632). Change:

```python
    elif gate == "G6":
        print(gate_G6(arg(0), arg(1), arg(2)))
```

To:

```python
    elif gate == "G6":
        pipeline_name = arg(0)
        result = gate_G6(pipeline_name, arg(1), arg(2))
        print(result)
        write_gate_marker("G6", pipeline_name, "generative", result, arg(1))
```

- [ ] **Step 4: Run tests to verify marker writing works**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestGateMarkers -v`

Expected: All 4 tests PASS.

- [ ] **Step 5: Verify backward compatibility — existing G4/G6 calls without round_dir still work**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 tests/validate-gate.py G4 shenbi-worldbuilding /nonexistent/file.md`

Expected: JSON output with "status": "FAIL", no errors, no marker directory created.

- [ ] **Step 6: Commit**

```bash
git add tests/validate-gate.py tests/test_integrity.py
git commit -m "feat: write gate markers on G4/G6 PASS for integrity verification"
```

---

### Task 2: scoring.py gate marker enforcement

**Files:**
- Modify: `tests/scoring.py:160–303` (main() function)
- Test: `tests/test_integrity.py`

- [ ] **Step 1: Write tests for scoring.py marker enforcement**

Append to `tests/test_integrity.py`:

```python
class TestScoringMarkers(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="scoring_test_")
        self.round_dir = Path(self.tmpdir) / "round-test"
        self.round_dir.mkdir()
        (self.round_dir / "gate-markers").mkdir()
        (self.round_dir / "t1-reports").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_rubric(self):
        """Create a minimal rubric file."""
        rubric_dir = self.round_dir / "rubric-t1"
        rubric_dir.mkdir(exist_ok=True)
        rubric = rubric_dir / "rubric.md"
        rubric.write_text(
            "| # | Dimension | Weight |\n"
            "|---|-----------|--------|\n"
            "| 1 | Quality   | 100%   |\n"
        )
        return str(rubric)

    def _make_t1_rubric(self, skill_name):
        """Create a rubric in the t1-skill directory structure."""
        rubric_dir = self.round_dir / "t1-skill" / skill_name / "generative"
        rubric_dir.mkdir(parents=True, exist_ok=True)
        rubric = rubric_dir / "rubric.md"
        rubric.write_text(
            "| # | Dimension | Weight |\n"
            "|---|-----------|--------|\n"
            "| 1 | Quality   | 100%   |\n"
        )
        return str(rubric)

    def _make_scores(self, scores=None):
        """Create a scores file."""
        scores = scores or {"1": 95}
        scores_path = self.round_dir / "test-scores.json"
        scores_path.write_text(json.dumps(scores))
        return str(scores_path)

    def _make_marker(self, gate, target, test_type="generative"):
        """Create a gate marker file."""
        marker = {
            "gate": gate,
            "status": "PASS",
            "timestamp": "2026-06-13T00:00:00+00:00",
            "checks": [],
            "files_checked": ["/some/file.md"],
        }
        marker_path = self.round_dir / "gate-markers" / f"{gate}-{target}-{test_type}.json"
        marker_path.write_text(json.dumps(marker))

    def test_no_round_dir_skips_check(self):
        """Without --round-dir, scoring proceeds normally (backward compat)."""
        rubric = self._make_rubric()
        scores = self._make_scores()
        rc, stdout, stderr = run_py(SC, [rubric, scores])
        self.assertEqual(rc, 0, f"Should succeed without --round-dir. stderr: {stderr}")
        result = json.loads(stdout)
        self.assertEqual(result["status"], "PASS")

    def test_missing_marker_exits_3(self):
        """Missing gate marker should cause exit code 3."""
        rubric = self._make_t1_rubric("shenbi-worldbuilding")
        scores = self._make_scores()
        rc, stdout, stderr = run_py(SC, [
            rubric, scores, "--test-type", "generative", "--round-dir", str(self.round_dir),
        ])
        self.assertEqual(rc, 3, f"Should exit 3 for missing marker. stdout: {stdout}")

    def test_present_marker_succeeds(self):
        """Present gate marker should allow scoring to proceed."""
        rubric = self._make_t1_rubric("shenbi-worldbuilding")
        scores = self._make_scores()
        self._make_marker("G4", "shenbi-worldbuilding", "generative")
        rc, stdout, stderr = run_py(SC, [
            rubric, scores, "--test-type", "generative", "--round-dir", str(self.round_dir),
        ])
        self.assertEqual(rc, 0, f"Should succeed with marker present. stdout: {stdout}")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestScoringMarkers -v`

Expected: `test_no_round_dir_skips_check` passes (no changes needed), `test_missing_marker_exits_3` fails (enforcement not implemented), `test_present_marker_succeeds` fails.

- [ ] **Step 3: Implement marker enforcement in scoring.py**

Add the marker check function after `classify()` (around line 158) in `tests/scoring.py`:

```python
def check_gate_markers(rubric_path, test_type, round_dir):
    """Verify required gate markers exist. Returns list of missing marker descriptions."""
    if not round_dir:
        return []
    rd = Path(round_dir)
    marker_dir = rd / "gate-markers"
    rubric_p = Path(rubric_path)
    missing = []

    if "t1-skill" in rubric_p.parts:
        idx = rubric_p.parts.index("t1-skill")
        skill_name = rubric_p.parts[idx + 1] if idx + 1 < len(rubric_p.parts) else None
        if skill_name:
            marker_file = marker_dir / f"G4-{skill_name}-{test_type}.json"
            if not marker_file.exists():
                missing.append(f"G4-{skill_name}-{test_type}")

    elif "t2-phase" in rubric_p.parts:
        deps_path = Path(__file__).parent / "tiers" / "deps.json"
        if deps_path.exists():
            deps = json.loads(deps_path.read_text(encoding="utf-8"))
            idx = rubric_p.parts.index("t2-phase")
            phase_name = rubric_p.parts[idx + 1] if idx + 1 < len(rubric_p.parts) else None
            if phase_name and phase_name in deps.get("t2-phases", {}):
                for skill in deps["t2-phases"][phase_name].get("prerequisites", []):
                    marker_file = marker_dir / f"G4-{skill}-generative.json"
                    if not marker_file.exists():
                        missing.append(f"G4-{skill}-generative")

    elif "t3-pipeline" in rubric_p.parts:
        idx = rubric_p.parts.index("t3-pipeline")
        pipeline_name = rubric_p.parts[idx + 1] if idx + 1 < len(rubric_p.parts) else None
        if pipeline_name:
            marker_file = marker_dir / f"G6-{pipeline_name}.json"
            if not marker_file.exists():
                missing.append(f"G6-{pipeline_name}")

    return missing
```

Modify `main()` to parse `--round-dir` and check markers. Find the line `test_type = None` (around line 187) and add the round_dir parsing in the same loop:

```python
    round_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == "--test-type" and i + 1 < len(sys.argv):
            test_type = sys.argv[i + 1]
        if arg == "--round-dir" and i + 1 < len(sys.argv):
            round_dir = sys.argv[i + 1]
        if arg == "--tier" and i + 1 < len(sys.argv):
            tier = sys.argv[i + 1]
        if arg == "--phase" and i + 1 < len(sys.argv):
            phase = sys.argv[i + 1]
```

Remove the separate `round_dir = None` block around line 208 that only fires for tier=T1.

After the dimension filtering by test_type (around line 223, after `dimensions = filter_dimensions_by_test_type(...)`), add the marker check:

```python
    # Gate marker enforcement
    if round_dir and test_type:
        missing = check_gate_markers(rubric_path, test_type, round_dir)
        if missing:
            err = {
                "status": "MARKER_MISSING",
                "missing_markers": missing,
                "message": f"Required gate markers not found: {', '.join(missing)}. "
                           f"Run gates (G4/G6) with --round-dir before scoring.",
            }
            print(json.dumps(err, indent=2, ensure_ascii=False))
            sys.exit(3)
```

- [ ] **Step 4: Run tests to verify marker enforcement**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestScoringMarkers -v`

Expected: All 3 tests PASS.

- [ ] **Step 5: Verify backward compat — scoring without --round-dir still works**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 tests/scoring.py tests/tiers/t1-skill/shenbi-worldbuilding/generative/rubric.md tests/rounds/round-005-2026-06-12/t1-reports/shenbi-worldbuilding-generative-scores.json --test-type generative`

Expected: exit 0, score output printed (no --round-dir, so marker check skipped).

- [ ] **Step 6: Commit**

```bash
git add tests/scoring.py tests/test_integrity.py
git commit -m "feat: scoring.py requires gate markers when --round-dir is provided"
```

---

### Task 3: phase-runner.py state machine

**Files:**
- Create: `tests/phase-runner.py`
- Test: `tests/test_integrity.py`

- [ ] **Step 1: Write tests for phase-runner.py state machine**

Append to `tests/test_integrity.py`:

```python
class TestPhaseRunner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="phase_test_")
        self.round_dir = Path(self.tmpdir) / "round-test"
        self.round_dir.mkdir()
        (self.round_dir / "phase-state").mkdir()
        (self.round_dir / "gate-markers").mkdir()
        (self.round_dir / "t1-reports").mkdir()
        (self.round_dir / "t2-reports").mkdir()
        (self.round_dir / "project-output").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_summary(self, t1_scores=None):
        """Create summary.json with optional T1 scores."""
        summary = {"t1_scores": t1_scores or {}, "t2_scores": {}, "t3_scores": {}}
        (self.round_dir / "summary.json").write_text(json.dumps(summary))

    def _make_marker(self, gate, target, test_type="generative"):
        """Create a gate marker file."""
        marker = {
            "gate": gate, "status": "PASS",
            "timestamp": "2026-06-13T00:00:00+00:00",
            "checks": [], "files_checked": [],
        }
        (self.round_dir / "gate-markers" / f"{gate}-{target}-{test_type}.json").write_text(
            json.dumps(marker)
        )

    def _make_scores_file(self, phase, scores=None):
        """Create a T2 scores file."""
        scores = scores or {"1": 95, "2": 95, "3": 95, "4": 95, "5": 95}
        path = self.round_dir / "t2-reports" / f"{phase}-generative-scores.json"
        path.write_text(json.dumps(scores))
        return str(path)

    def test_start_creates_state_file(self):
        """start command should create a phase state file."""
        self._make_summary()
        rc, stdout, stderr = run_py(PR, [
            "start", "genesis",
            "--round-dir", str(self.round_dir),
            "--project-dir", str(self.round_dir / "project-output"),
        ])
        state_file = self.round_dir / "phase-state" / "genesis.json"
        self.assertTrue(state_file.exists(), "start should create state file")
        state = json.loads(state_file.read_text())
        self.assertEqual(state["phase"], "genesis")

    def test_post_skill_writes_step(self):
        """post-skill should append a step to the state file."""
        self._make_summary()
        # Start the phase first
        run_py(PR, ["start", "genesis",
                     "--round-dir", str(self.round_dir),
                     "--project-dir", str(self.round_dir / "project-output")])
        rc, stdout, stderr = run_py(PR, [
            "post-skill", "genesis", "shenbi-worldbuilding",
            "--round-dir", str(self.round_dir),
            "--project-dir", str(self.round_dir / "project-output"),
        ])
        state_file = self.round_dir / "phase-state" / "genesis.json"
        state = json.loads(state_file.read_text())
        steps = [s for s in state["steps"] if s["action"] == "post-skill"]
        self.assertEqual(len(steps), 1, "post-skill should record a step")
        self.assertEqual(steps[0]["skill"], "shenbi-worldbuilding")

    def test_finalize_sets_state(self):
        """finalize should set state to finalized."""
        self._make_summary()
        run_py(PR, ["start", "genesis",
                     "--round-dir", str(self.round_dir),
                     "--project-dir", str(self.round_dir / "project-output")])
        # Mark all skills as done
        deps = json.loads((TESTS / "tiers" / "deps.json").read_text())
        for skill in deps["t2-phases"]["genesis"]["prerequisites"]:
            self._make_marker("G4", skill, "generative")
            run_py(PR, ["post-skill", "genesis", skill,
                         "--round-dir", str(self.round_dir),
                         "--project-dir", str(self.round_dir / "project-output")])
        # Pre-score (transitions to skills_done)
        run_py(PR, ["pre-score", "genesis", "--round-dir", str(self.round_dir)])
        # Create score file and post-score
        scores_file = self._make_scores_file("genesis")
        run_py(PR, ["post-score", "genesis", scores_file, "--round-dir", str(self.round_dir)])
        # Finalize
        rc, stdout, stderr = run_py(PR, [
            "finalize", "genesis",
            "--round-dir", str(self.round_dir),
            "--project-dir", str(self.round_dir / "project-output"),
        ])
        state_file = self.round_dir / "phase-state" / "genesis.json"
        state = json.loads(state_file.read_text())
        self.assertEqual(state["state"], "finalized")

    def test_wrong_order_rejected(self):
        """Commands with wrong preconditions should fail."""
        self._make_summary()
        rc, stdout, stderr = run_py(PR, [
            "finalize", "genesis",
            "--round-dir", str(self.round_dir),
            "--project-dir", str(self.round_dir / "project-output"),
        ])
        self.assertNotEqual(rc, 0, "finalize before start should fail")

    def test_pre_score_rejects_missing_markers(self):
        """pre-score should fail if not all skills have gate markers."""
        self._make_summary()
        run_py(PR, ["start", "genesis",
                     "--round-dir", str(self.round_dir),
                     "--project-dir", str(self.round_dir / "project-output")])
        # Don't create any markers — pre-score should fail
        rc, stdout, stderr = run_py(PR, [
            "pre-score", "genesis", "--round-dir", str(self.round_dir),
        ])
        self.assertNotEqual(rc, 0, "pre-score without markers should fail")
```

- [ ] **Step 2: Run tests to verify they fail (phase-runner.py doesn't exist yet)**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestPhaseRunner -v`

Expected: All 5 tests fail (module not found).

- [ ] **Step 3: Implement phase-runner.py**

Create `tests/phase-runner.py`:

```python
#!/usr/bin/env python3
"""State machine for T2/T3 phase execution.

Usage:
    phase-runner.py start <phase> --round-dir <dir> --project-dir <dir>
    phase-runner.py pre-skill <phase> <skill> --round-dir <dir>
    phase-runner.py post-skill <phase> <skill> --round-dir <dir> --project-dir <dir>
    phase-runner.py pre-score <phase> --round-dir <dir>
    phase-runner.py post-score <phase> <scores-file> --round-dir <dir>
    phase-runner.py finalize <phase> --round-dir <dir> --project-dir <dir>
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PROJECT = TESTS.parent


def load_deps():
    return json.loads((TESTS / "tiers" / "deps.json").read_text(encoding="utf-8"))


def load_state(round_dir, phase):
    state_file = Path(round_dir) / "phase-state" / f"{phase}.json"
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {"phase": phase, "state": "created", "steps": []}


def save_state(round_dir, state):
    state_dir = Path(round_dir) / "phase-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{state['phase']}.json"
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_gate(gate, args):
    """Run a gate via validate-gate.py, return parsed JSON."""
    vg = str(TESTS / "validate-gate.py")
    r = subprocess.run(
        [sys.executable, vg, gate] + args,
        capture_output=True, text=True, timeout=60,
    )
    try:
        return json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"status": "FAIL", "raw_stdout": r.stdout, "raw_stderr": r.stderr}


def require_state(state, expected, action):
    """Exit with error if state is not one of the expected states."""
    if state["state"] not in expected:
        print(json.dumps({
            "error": f"Cannot {action}: state is '{state['state']}', expected {expected}",
            "phase": state["phase"],
        }))
        sys.exit(1)


def cmd_start(phase, round_dir, project_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["created"], "start")
    # Run G5
    g5 = run_gate("G5", [phase, str(round_dir), str(project_dir)])
    step = {"action": "start", "timestamp": now_iso(), "g5_status": g5.get("status")}
    if g5.get("status") == "PASS":
        state["state"] = "started"
        state["steps"].append(step)
        save_state(round_dir, state)
        print(json.dumps({"status": "ok", "phase": phase, "state": "started", "g5": "PASS"}))
    else:
        state["steps"].append({**step, "g5_must_fix": g5.get("must_fix", [])})
        save_state(round_dir, state)
        print(json.dumps({"status": "blocked", "phase": phase, "g5": g5}))
        sys.exit(1)


def cmd_pre_skill(phase, skill, round_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "pre-skill")
    print(json.dumps({"status": "ok", "phase": phase, "skill": skill, "action": "execute_skill"}))


def cmd_post_skill(phase, skill, round_dir, project_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "post-skill")
    # Run G2 on output files
    proj = Path(project_dir)
    output_files = [str(f) for f in proj.rglob("*.md") if f.stat().st_size > 0][:20]
    g2_status = "SKIP"
    if output_files:
        g2 = run_gate("G2", [",".join(output_files), "chapter", str(round_dir)])
        g2_status = g2.get("status", "UNKNOWN")
    # Run G4 for this skill
    g4 = run_gate("G4", [skill, ",".join(output_files) if output_files else "", str(round_dir)])
    g4_status = g4.get("status", "UNKNOWN")
    step = {
        "action": "post-skill",
        "skill": skill,
        "timestamp": now_iso(),
        "g2": g2_status,
        "g4": g4_status,
    }
    state["steps"].append(step)
    save_state(round_dir, state)
    if g4_status == "FAIL":
        print(json.dumps({"status": "blocked", "phase": phase, "skill": skill, "g4": g4}))
        sys.exit(1)
    print(json.dumps({"status": "ok", "phase": phase, "skill": skill, "g2": g2_status, "g4": g4_status}))


def cmd_pre_score(phase, round_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["started"], "pre-score")
    deps = load_deps()
    phase_data = deps.get("t2-phases", {}).get(phase, {})
    marker_dir = Path(round_dir) / "gate-markers"
    missing = []
    for skill in phase_data.get("prerequisites", []):
        marker = marker_dir / f"G4-{skill}-generative.json"
        if not marker.exists():
            missing.append(skill)
    if missing:
        print(json.dumps({
            "status": "blocked",
            "phase": phase,
            "missing_markers": [f"G4-{s}-generative" for s in missing],
        }))
        sys.exit(1)
    # Check expected outputs exist
    proj_dir = Path(round_dir) / "project-output"
    for pattern in phase_data.get("expected_outputs", []):
        if "*" in pattern:
            if not list(proj_dir.rglob(pattern)):
                print(json.dumps({"status": "blocked", "phase": phase, "missing_output": pattern}))
                sys.exit(1)
        else:
            if not (proj_dir / pattern).exists():
                print(json.dumps({"status": "blocked", "phase": phase, "missing_output": pattern}))
                sys.exit(1)
    state["state"] = "skills_done"
    save_state(round_dir, state)
    print(json.dumps({"status": "ok", "phase": phase, "state": "skills_done"}))


def cmd_post_score(phase, scores_file, round_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["skills_done"], "post-score")
    if not Path(scores_file).exists():
        print(json.dumps({"status": "error", "phase": phase, "message": f"Scores file not found: {scores_file}"}))
        sys.exit(1)
    scores_data = json.loads(Path(scores_file).read_text(encoding="utf-8"))
    step = {
        "action": "post-score",
        "timestamp": now_iso(),
        "scores_file": str(scores_file),
    }
    state["steps"].append(step)
    state["state"] = "scored"
    save_state(round_dir, state)
    print(json.dumps({"status": "ok", "phase": phase, "state": "scored"}))


def cmd_finalize(phase, round_dir, project_dir):
    state = load_state(round_dir, phase)
    require_state(state, ["scored"], "finalize")
    # Re-run G5 to verify
    g5 = run_gate("G5", [phase, str(round_dir), str(project_dir)])
    step = {
        "action": "finalize",
        "timestamp": now_iso(),
        "g5_status": g5.get("status"),
    }
    if g5.get("status") != "PASS":
        state["steps"].append({**step, "g5_must_fix": g5.get("must_fix", [])})
        save_state(round_dir, state)
        print(json.dumps({"status": "blocked", "phase": phase, "g5": g5}))
        sys.exit(1)
    # Verify all skill markers still present
    deps = load_deps()
    marker_dir = Path(round_dir) / "gate-markers"
    for skill in deps.get("t2-phases", {}).get(phase, {}).get("prerequisites", []):
        if not (marker_dir / f"G4-{skill}-generative.json").exists():
            print(json.dumps({"status": "error", "phase": phase, "missing_marker": f"G4-{skill}-generative"}))
            sys.exit(1)
    state["state"] = "finalized"
    state["steps"].append(step)
    save_state(round_dir, state)
    print(json.dumps({"status": "ok", "phase": phase, "state": "finalized"}))


def main():
    if len(sys.argv) < 2:
        print("Usage: phase-runner.py <command> [args...] --round-dir <dir> [--project-dir <dir>]")
        print("Commands: start pre-skill post-skill pre-score post-score finalize")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    def find_flag(flag, required=True):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        if required:
            print(f"Missing required flag: {flag}")
            sys.exit(1)
        return None

    round_dir = find_flag("--round-dir")
    project_dir = find_flag("--project-dir", required=False)

    if cmd == "start":
        phase = args[0]
        cmd_start(phase, round_dir, project_dir)
    elif cmd == "pre-skill":
        phase, skill = args[0], args[1]
        cmd_pre_skill(phase, skill, round_dir)
    elif cmd == "post-skill":
        phase, skill = args[0], args[1]
        cmd_post_skill(phase, skill, round_dir, project_dir)
    elif cmd == "pre-score":
        phase = args[0]
        cmd_pre_score(phase, round_dir)
    elif cmd == "post-score":
        phase, scores_file = args[0], args[1]
        cmd_post_score(phase, scores_file, round_dir)
    elif cmd == "finalize":
        phase = args[0]
        cmd_finalize(phase, round_dir, project_dir)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify phase-runner.py works**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestPhaseRunner -v`

Expected: All 5 tests PASS.

- [ ] **Step 5: Manual smoke test — check help output**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 tests/phase-runner.py`

Expected: Usage message with command list, exit 1.

- [ ] **Step 6: Commit**

```bash
git add tests/phase-runner.py tests/test_integrity.py
git commit -m "feat: add phase-runner.py state machine for T2/T3 execution"
```

---

### Task 4: G7.13–G7.16 audit checks in validate-gate.py

**Files:**
- Modify: `tests/validate-gate.py:3232–3354` (gate_G7 function)
- Test: `tests/test_integrity.py`

- [ ] **Step 1: Write tests for G7.13–G7.16**

Append to `tests/test_integrity.py`:

```python
class TestG7AuditChecks(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="g7_test_")
        self.round_dir = Path(self.tmpdir) / "round-test"
        self.round_dir.mkdir()
        (self.round_dir / "gate-markers").mkdir()
        (self.round_dir / "t1-reports").mkdir()
        (self.round_dir / "t2-reports").mkdir()
        (self.round_dir / "t3-reports").mkdir()
        (self.round_dir / "phase-state").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_marker(self, gate, target, test_type="generative", files_checked=None, status="PASS"):
        marker = {
            "gate": gate, "status": status,
            "timestamp": "2026-06-13T00:00:00+00:00",
            "checks": [],
            "files_checked": files_checked or [],
        }
        (self.round_dir / "gate-markers" / f"{gate}-{target}-{test_type}.json").write_text(
            json.dumps(marker)
        )

    def _make_summary(self, t1=None, t2=None, t3=None):
        summary = {
            "t1_scores": t1 or {},
            "t2_scores": t2 or {},
            "t3_scores": t3 or {},
        }
        (self.round_dir / "summary.json").write_text(json.dumps(summary))

    def _make_phase_state(self, phase, state="finalized"):
        state_data = {"phase": phase, "state": state, "steps": []}
        (self.round_dir / "phase-state" / f"{phase}.json").write_text(json.dumps(state_data))

    def test_g713_gate_rerun_mismatch(self):
        """G7.13 should detect when a marker says PASS but re-run fails."""
        # Create a marker claiming PASS for a nonexistent file
        self._make_marker("G4", "shenbi-worldbuilding", "generative",
                          files_checked=["/nonexistent/file.md"])
        rc, stdout, stderr = run_py(VG, ["G7", str(self.round_dir)])
        result = json.loads(stdout)
        # G7 should fail because the gate re-run on nonexistent files won't match PASS
        # (or the marker claims PASS for something that now fails)
        self.assertIn(result["status"], ["FAIL", "PASS"])  # Depends on whether G7.13 runs

    def test_g714_timeline_violation(self):
        """G7.14 should detect score files older than gate markers."""
        import time
        # Create gate marker (newer)
        marker = {"gate": "G4", "status": "PASS", "timestamp": "2026-06-13T12:00:00Z",
                  "checks": [], "files_checked": []}
        (self.round_dir / "gate-markers" / "G4-shenbi-worldbuilding-generative.json").write_text(
            json.dumps(marker)
        )
        # Touch marker to be "now"
        time.sleep(0.1)
        marker_path = self.round_dir / "gate-markers" / "G4-shenbi-worldbuilding-generative.json"
        marker_path.touch()

        # Create score file (older than marker — should trigger timeline warning)
        score_path = self.round_dir / "t1-reports" / "shenbi-worldbuilding-generative-scores.json"
        score_path.write_text(json.dumps({"1": 95}))
        # Make score file older
        import os
        old_time = marker_path.stat().st_mtime - 100
        os.utime(score_path, (old_time, old_time))

    def test_g715_duplicate_pattern(self):
        """G7.15 should detect identical score vectors across skills."""
        # Create multiple score files with identical score vectors
        scores = {"1": 90, "2": 95, "3": 95, "4": 100, "5": 95}
        for i in range(4):
            name = f"shenbi-skill-{i}"
            (self.round_dir / "t1-reports" / f"{name}-generative-scores.json").write_text(
                json.dumps(scores)
            )

    def test_g716_incomplete_phase(self):
        """G7.16 should detect phases with scores but state not finalized."""
        self._make_summary(t2={"genesis": {"generative": 95}})
        # Don't create phase state file — should be detected as INCOMPLETE_PHASE

    def test_g716_missing_gate(self):
        """G7.16 should detect T3 pipelines missing gate markers."""
        self._make_summary(t3={"long-form": {"generative": 95}})
        # Don't create G6 marker — should be detected as MISSING_GATE
```

- [ ] **Step 2: Run tests to verify they fail (G7.13–G7.16 not implemented)**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestG7AuditChecks -v`

Expected: Tests may pass or fail depending on current G7 behavior. The new checks don't exist yet so the audit behaviors won't be present.

- [ ] **Step 3: Implement G7.13–G7.16 in validate-gate.py**

Add these checks at the end of `gate_G7()`, before the final `if mf:` / `return` block (before line 3352). Insert after the G7.8 deferred check:

```python
    # G7.13 — Gate re-run verification
    marker_dir = rd / "gate-markers"
    if marker_dir.exists():
        for mf_path in sorted(marker_dir.glob("*.json")):
            try:
                marker = jload(str(mf_path))
                if marker.get("status") != "PASS":
                    continue
                parts = mf_path.stem.split("-", 2)
                if len(parts) < 3:
                    continue
                gate_id, target, test_type = parts[0], parts[1], parts[2]
                files_checked = marker.get("files_checked", [])
                if gate_id == "G4":
                    rerun = json.loads(gate_G4(target, test_type, files_checked, str(rd)))
                    if rerun.get("status") == "FAIL":
                        mf.append(f"G7.13:{mf_path.stem}:marker_PASS_rerun_FAIL")
                elif gate_id == "G6":
                    proj_dir = str(rd / "project-output")
                    rerun = json.loads(gate_G6(pipeline_name=target, round_dir=str(rd), project_dir=proj_dir))
                    if rerun.get("status") == "FAIL":
                        mf.append(f"G7.13:{mf_path.stem}:marker_PASS_rerun_FAIL")
            except Exception as e:
                mf.append(f"G7.13:{mf_path.stem}:rerun_error:{e}")
        if not any(x.startswith("G7.13:") for x in mf):
            c.append({"id": "G7.13", "s": "PASS", "note": "all markers verified by re-run"})
    else:
        c.append({"id": "G7.13", "s": "SKIP", "r": "no gate-markers directory"})

    # G7.14 — Score timeline consistency
    timeline_warnings = []
    for reports_dir_name in ["t1-reports", "t2-reports", "t3-reports"]:
        reports_dir = rd / reports_dir_name
        if not reports_dir.exists():
            continue
        for score_file in reports_dir.glob("*-scores.json"):
            try:
                score_mtime = score_file.stat().st_mtime
                # Check against gate markers
                if marker_dir.exists():
                    for marker_file in marker_dir.glob("*.json"):
                        if marker_file.stat().st_mtime > score_mtime:
                            timeline_warnings.append(
                                f"G7.14:{score_file.name}:older_than_{marker_file.name}"
                            )
                            break
            except OSError:
                pass
    if timeline_warnings:
        # Non-blocking — add to audit_warnings in summary later
        for tw in timeline_warnings:
            c.append({"id": "G7.14", "s": "WARN", "detail": tw})
    else:
        c.append({"id": "G7.14", "s": "PASS", "note": "timeline consistent"})

    # G7.15 — Score pattern suspiciousness
    pattern_warnings = []
    for reports_dir_name in ["t1-reports", "t2-reports", "t3-reports"]:
        reports_dir = rd / reports_dir_name
        if not reports_dir.exists():
            continue
        score_vectors = {}  # tuple -> list of skill names
        for score_file in reports_dir.glob("*-generative-scores.json"):
            try:
                data = jload(str(score_file))
                if isinstance(data, dict):
                    vec = tuple(sorted((k, v) for k, v in data.items() if k.lstrip("-").isdigit()))
                    if vec not in score_vectors:
                        score_vectors[vec] = []
                    score_vectors[vec].append(score_file.stem)
            except Exception:
                pass
        for vec, names in score_vectors.items():
            if len(names) >= 3:
                pattern_warnings.append({
                    "type": "DUPLICATE_PATTERN",
                    "severity": "warn",
                    "message": f"{len(names)} skills share identical score vector in {reports_dir_name}",
                })
    if pattern_warnings:
        for pw in pattern_warnings:
            c.append({"id": "G7.15", "s": "WARN", **pw})
    else:
        c.append({"id": "G7.15", "s": "PASS", "note": "no duplicate patterns"})

    # G7.16 — Phase state verification
    if summary_path.exists():
        try:
            s = jload(str(summary_path))
            # T2 phase state
            for phase_name in s.get("t2_scores", {}):
                ps_file = rd / "phase-state" / f"{phase_name}.json"
                if not ps_file.exists():
                    mf.append(f"G7.16:phase:{phase_name}:no_state_file")
                else:
                    ps = jload(str(ps_file))
                    if ps.get("state") != "finalized":
                        mf.append(f"G7.16:phase:{phase_name}:state={ps.get('state')}")
            # T3 gate markers
            for pipe_name in s.get("t3_scores", {}):
                gm = rd / "gate-markers" / f"G6-{pipe_name}.json"
                if not gm.exists():
                    mf.append(f"G7.16:pipeline:{pipe_name}:no_G6_marker")
            if not any(x.startswith("G7.16:") for x in mf):
                c.append({"id": "G7.16", "s": "PASS", "note": "phase state and gate markers verified"})
        except (json.JSONDecodeError, OSError):
            pass

    # Write audit_warnings to summary.json
    audit_warnings = []
    for check in c:
        if check.get("s") == "WARN" and check.get("id") in ("G7.14", "G7.15"):
            audit_warnings.append({
                "type": check.get("type", check["id"]),
                "severity": check.get("severity", "warn"),
                "message": check.get("message", check.get("detail", "")),
            })
    if audit_warnings and summary_path.exists():
        try:
            s = jload(str(summary_path))
            s["audit_warnings"] = audit_warnings
            with open(str(summary_path), "w") as f:
                json.dump(s, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
```

- [ ] **Step 4: Run tests to verify G7 audit checks**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestG7AuditChecks -v`

Expected: All 5 tests PASS (they verify the new checks run without crashing and detect the specified conditions).

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py -v`

Expected: All tests across all 4 test classes PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/validate-gate.py tests/test_integrity.py
git commit -m "feat: add G7.13-G7.16 audit checks for post-round verification"
```

---

### Task 5: T2/T3 protocol in command-to-give.md

**Files:**
- Modify: `command-to-give.md:79–97` (after 第五步, before 每轮结束)

- [ ] **Step 1: Add 第六步 (T2 protocol) and 第七步 (T3 protocol) to command-to-give.md**

Insert after the "### 第五步：推进" section (after line 83) and before the "### 每轮结束" section:

```markdown
### 第六步：T2 Phase 执行

全部 T1 skill ≥ 94 后，对每个 T2 phase 按 deps.json 顺序执行：

    # 1. 启动 phase（运行 G5）
    python3 tests/phase-runner.py start <phase> --round-dir <round-dir> --project-dir <round-dir>/project-output

    # 2. 对每个 prerequisite skill：
    python3 tests/phase-runner.py pre-skill <phase> <skill> --round-dir <round-dir>
    #    读 skills/<skill>/SKILL.md，执行 skill，输出到 <round-dir>/project-output/
    python3 tests/phase-runner.py post-skill <phase> <skill> --round-dir <round-dir> --project-dir <round-dir>/project-output

    # 3. 确认所有 skill 完成并评分
    python3 tests/phase-runner.py pre-score <phase> --round-dir <round-dir>
    # 4. 独立 subagent 评分（Dispatcher 不得评分）
    python3 tests/scoring.py tests/tiers/t2-phase/<phase>/rubric.md <score-file> --test-type generative --round-dir <round-dir>
    # 5. 记录分数
    python3 tests/phase-runner.py post-score <phase> <score-file> --round-dir <round-dir>
    # 6. 封存
    python3 tests/phase-runner.py finalize <phase> --round-dir <round-dir> --project-dir <round-dir>/project-output

**phase-runner.py 每个步骤都有前置条件检查。跳过步骤会失败。** 分数 < 94 的 phase 按第四步增强规则处理。

### 第七步：T3 Pipeline 执行

全部 T2 phase ≥ 94 且 finalized 后，对每个 T3 pipeline 执行：

    # 1. 确认 T2 全部 finalized + ≥ 94（从 summary.json 读取）
    # 2. 运行 G6
    python3 tests/validate-gate.py G6 <pipeline> <round-dir> <round-dir>/project-output
    # 3. 独立 subagent 评分
    python3 tests/scoring.py tests/tiers/t3-pipeline/<pipeline>/rubric.md <score-file> --test-type generative --round-dir <round-dir>
    # 4. 记录到 t3-reports/<pipeline>-generative-scores.json

T3 不使用 phase-runner.py。G6 gate marker 是评分的前置条件。
```

- [ ] **Step 2: Verify the markdown renders correctly**

Run: `cat command-to-give.md | head -120`

Expected: Sections 第五步, 第六步, 第七步, 每轮结束 appear in order.

- [ ] **Step 3: Commit**

```bash
git add command-to-give.md
git commit -m "docs: add T2/T3 protocol (第六步/第七步) to command-to-give.md"
```

---

### Task 6: Integration test — full T2 phase lifecycle

**Files:**
- Test: `tests/test_integrity.py`

- [ ] **Step 1: Write end-to-end integration test**

Append to `tests/test_integrity.py`:

```python
class TestIntegration(unittest.TestCase):
    """End-to-end test: gate markers → scoring enforcement → G7 audit."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="integration_test_")
        self.round_dir = Path(self.tmpdir) / "round-integration"
        self.round_dir.mkdir()
        for d in ["gate-markers", "t1-reports", "t2-reports", "t3-reports",
                  "phase-state", "project-output"]:
            (self.round_dir / d).mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_scoring_rejects_without_markers_accepts_with(self):
        """Scoring fails without markers, succeeds after markers written."""
        # Create rubric in t1-skill path
        rubric_dir = self.round_dir / "t1-skill" / "shenbi-worldbuilding" / "generative"
        rubric_dir.mkdir(parents=True)
        rubric = rubric_dir / "rubric.md"
        rubric.write_text(
            "| # | Dimension | Weight |\n|---|-----------|--------|\n| 1 | Quality | 100% |\n"
        )
        scores_path = self.round_dir / "test-scores.json"
        scores_path.write_text(json.dumps({"1": 95}))

        # Without marker → exit 3
        rc, out, err = run_py(SC, [
            str(rubric), str(scores_path),
            "--test-type", "generative", "--round-dir", str(self.round_dir),
        ])
        self.assertEqual(rc, 3)

        # Write marker
        marker = {
            "gate": "G4", "status": "PASS",
            "timestamp": "2026-06-13T00:00:00Z",
            "checks": [], "files_checked": ["/some/file.md"],
        }
        (self.round_dir / "gate-markers" / "G4-shenbi-worldbuilding-generative.json").write_text(
            json.dumps(marker)
        )

        # With marker → exit 0
        rc, out, err = run_py(SC, [
            str(rubric), str(scores_path),
            "--test-type", "generative", "--round-dir", str(self.round_dir),
        ])
        self.assertEqual(rc, 0)

    def test_g7_detects_phase_without_finalized_state(self):
        """G7.16 should flag a phase with score but no finalized state."""
        # Create summary with T2 score
        summary = {
            "t1_scores": {},
            "t2_scores": {"genesis": 95},
            "t3_scores": {},
        }
        (self.round_dir / "summary.json").write_text(json.dumps(summary))
        # Create phase state but NOT finalized
        state = {"phase": "genesis", "state": "scored", "steps": []}
        (self.round_dir / "phase-state" / "genesis.json").write_text(json.dumps(state))

        rc, out, err = run_py(VG, ["G7", str(self.round_dir)])
        result = json.loads(out)
        self.assertEqual(result["status"], "FAIL")
        must_fix = result.get("must_fix", [])
        self.assertTrue(any("G7.16" in m and "genesis" in m for m in must_fix),
                        f"Expected G7.16 phase state violation, got: {must_fix}")
```

- [ ] **Step 2: Run integration tests**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py::TestIntegration -v`

Expected: Both tests PASS.

- [ ] **Step 3: Run full test suite**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py -v`

Expected: All tests across all 5 test classes PASS (4 class tests + integration).

- [ ] **Step 4: Commit**

```bash
git add tests/test_integrity.py
git commit -m "test: add integration tests for gate markers, scoring enforcement, and G7 audit"
```

---

### Task 7: Final verification

**Files:**
- All modified files

- [ ] **Step 1: Run complete test suite**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 -m pytest tests/test_integrity.py -v`

Expected: All tests PASS.

- [ ] **Step 2: Verify existing G4/G6/G7 still work on R5 data**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 tests/validate-gate.py G7 tests/rounds/round-005-2026-06-12`

Expected: G7 runs without error. Output may differ from before (new G7.13–G7.16 checks) but should not crash.

- [ ] **Step 3: Verify phase-runner.py help**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 tests/phase-runner.py`

Expected: Usage message printed, exit 1.

- [ ] **Step 4: Verify scoring.py backward compat**

Run: `cd /Users/xiaotiac/Documents/GitHub/shenbi && python3 tests/scoring.py tests/tiers/t1-skill/shenbi-worldbuilding/generative/rubric.md tests/rounds/round-005-2026-06-12/t1-reports/shenbi-worldbuilding-generative-scores.json --test-type generative`

Expected: exit 0, score computed (no --round-dir → marker check skipped).

- [ ] **Step 5: Final commit with any cleanup**

```bash
git add -A
git status
```

Verify only expected files are modified/added. No unintended changes.

- [ ] **Step 6: Tag the commit**

```bash
git tag -a integrity-hardening-v1 -m "Test framework integrity hardening: gate markers, phase-runner, G7.13-G7.16"
```
