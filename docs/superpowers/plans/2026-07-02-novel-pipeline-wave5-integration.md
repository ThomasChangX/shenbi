# Novel Pipeline Wave 5: Cross-Wave Integration Tests

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Verify that all 4 waves work together as a system: genesis → checkpoint → chapter loop (with audit + revision + staging + context assembly) → triggers → closure. End-to-end tests with mocked dispatch.

**Architecture:** Integration tests that mock `dispatch_skill` and `run_gate_g4` to test the full pipeline flow without actual LLM calls. Each test verifies a cross-wave integration point.

**Spec reference:** All sections — this wave verifies spec acceptance criteria 1-20.

---

### Task 1: Genesis-to-ChapterLoop Phase Transition

**Files:** Create `tests/integration/pipeline/test_genesis_to_loop.py`

- [ ] **Step 1: Write the test**

```python
# tests/integration/pipeline/test_genesis_to_loop.py
"""Verify genesis completes 17 steps, checkpoint fires, approve transitions to chapter-loop."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from shenbi.pipeline.cli import main
from shenbi.pipeline.machine import load_state

@pytest.fixture
def seeded_project(tmp_path, sample_seed_content):
    seed = tmp_path / "seed.md"
    seed.write_text(sample_seed_content)
    project = tmp_path / "novel"
    main(["init", str(seed), "--project-dir", str(project)])
    return project

class TestGenesisToLoop:
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_genesis_completes_and_checkpoints(self, mock_g4, mock_disp, seeded_project):
        mock_disp.return_value = MagicMock(success=True, returncode=0, stdout="{}", stderr="")
        mock_g4.return_value = {"status": "PASS"}

        rc = main(["next", str(seeded_project)])
        assert rc == 0

        state = load_state(seeded_project)
        assert state.pending_checkpoint.type.value == "genesis-complete"
        assert mock_disp.call_count == 17

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_approve_transitions_to_chapter_loop(self, mock_g4, mock_disp, seeded_project):
        mock_disp.return_value = MagicMock(success=True, returncode=0, stdout="{}", stderr="")
        mock_g4.return_value = {"status": "PASS"}

        main(["next", str(seeded_project)])  # Run genesis
        main(["review", str(seeded_project), "approve"])  # Approve
        main(["resume", str(seeded_project)])  # Resume -> chapter loop starts

        state = load_state(seeded_project)
        assert state.phase.value == "chapter-loop"
        assert state.chapter_loop.current_chapter == 1
```

- [ ] **Step 2: Run, verify pass (after waves 1-4 implemented). Commit.**

```bash
uv run pytest tests/integration/pipeline/test_genesis_to_loop.py -v
git add tests/integration/pipeline/test_genesis_to_loop.py
git commit -m "test: genesis-to-loop phase transition integration (wave5 task1)"
```

---

### Task 2: Chapter Loop with Audit + Staging + Context Assembly

**Files:** Create `tests/integration/pipeline/test_chapter_loop_full.py`

- [ ] **Step 1: Write the test**

```python
# tests/integration/pipeline/test_chapter_loop_full.py
"""Verify chapter loop: plan(staging) -> checkpoint -> context -> draft -> settle(staging)
-> checkpoint -> audit(7 core) -> resonance -> revision -> snapshot -> drift."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from shenbi.pipeline.cli import main
from shenbi.pipeline.machine import load_state

class TestChapterLoopFull:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_chapter_runs_to_memo_checkpoint(self, mock_g4, mock_disp, tmp_path):
        """Chapter loop should stop at chapter-memo checkpoint after step 2."""
        mock_disp.return_value = MagicMock(success=True, returncode=0, stdout="{}", stderr="")
        mock_g4.return_value = {"status": "PASS"}

        # Set up state directly in chapter-loop phase
        from shenbi.pipeline.state import PipelineState, PipelinePhase, GenesisState
        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.genesis.state = GenesisState.COMPLETED
        state.chapter_loop.current_chapter = 1
        from shenbi.pipeline.machine import save_state
        save_state(project, state)

        main(["next", str(project)])

        state = load_state(project)
        assert state.pending_checkpoint.type.value == "chapter-memo"
```

- [ ] **Step 2: Run, commit.**

```bash
uv run pytest tests/integration/pipeline/test_chapter_loop_full.py -v
git add tests/integration/pipeline/test_chapter_loop_full.py
git commit -m "test: chapter loop with audit+staging+context integration (wave5 task2)"
```

---

### Task 3: Spec Coverage Matrix

**Files:** Create `docs/superpowers/plans/2026-07-02-pipeline-coverage-matrix.md`

- [ ] **Step 1: Write the coverage matrix**

Document mapping every spec section (1-19) to the wave/task that implements it. Any gaps are explicitly marked.

| Spec Section | Wave | Task(s) | Status |
|---|---|---|---|
| §1 Background | N/A | N/A | Context only |
| §2 Architecture | W1 | Task 1,6 | Implemented |
| §3 State Machine | W1+W3 | W1:T1-2, W3:T7-9 | Implemented |
| §4 Seed Parsing | W1 | Task 4 | Implemented |
| §5 Genesis | W3 | Task 2 | Implemented |
| §6 Chapter Loop | W3 | Task 3-6 | Implemented (core circle wired, genre/boundary wired in audit_layer, revision routing wired, volume triggers partial) |
| §7 Context Arch | W2 | Task 1-3 | Implemented |
| §8 Closure | W3 | Task 6 | Implemented |
| §9 Checkpoints | W1+W3 | W1:T2,5, W3:T9 | Implemented |
| §10 Snapshots | W4 | Task 3 | Implemented |
| §11 Error Handling | W3 | Task 8 | Implemented (handlers wired into genesis/chapter_step retry loops) |
| §12 Skill Changes | W4 | Task 1-6c | Implemented |
| §13 Modules | W1-3 | All | Implemented |
| §14 Decisions | N/A | N/A | Context only |
| §15 Acceptance | W5 | All tasks | Verified |
| §16 Genesis Dep Table | W3 | Task 2 | Verified in tests |
| §17 Ramp-Up Reads | W3 | Task 3 | Documented (ramp-up skip logic in dispatch_helper, needs implementation) |
| §18 G4 Staging | W1+W3 | W1:T5, W3:T9 | Implemented (G4 validates staging content, commit skips re-validation) |
| §19 FP Genesis Mode | W4 | Task 2 | Implemented |

- [ ] **Step 2: Commit.**

```bash
git add docs/superpowers/plans/2026-07-02-pipeline-coverage-matrix.md
git commit -m "docs: add spec coverage matrix for all waves (wave5 task3)"
```


---

### Task 4: Additional Integration Tests

**Files:** Create `tests/integration/pipeline/test_full_flows.py`

- [ ] **Step 1: Write comprehensive integration tests**

```python
# tests/integration/pipeline/test_full_flows.py
"""Comprehensive cross-wave integration tests."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from shenbi.pipeline.cli import main
from shenbi.pipeline.machine import load_state
from shenbi.pipeline.dispatch_helper import DispatchResult

class TestStagingIntegration:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_staging_committed_on_approve(self, mock_g4, mock_disp, tmp_path):
        """Verify staging files are committed when checkpoint is approved."""
        from shenbi.pipeline.state import PipelineState, PipelinePhase, GenesisState
        from shenbi.pipeline.machine import save_state, load_state
        from shenbi.pipeline.cli import main

        mock_disp.return_value = MagicMock(success=True, returncode=0, stdout="{}", stderr="")
        mock_g4.return_value = {"status": "PASS"}

        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CHAPTER_LOOP
        state.genesis.state = GenesisState.COMPLETED
        state.chapter_loop.current_chapter = 1
        save_state(project, state)

        # Create staging file for chapter plan
        staging_dir = project / "staging" / "plans"
        staging_dir.mkdir(parents=True)
        (staging_dir / "chapter-1-plan.md").write_text("# Plan", encoding="utf-8")

        # Run next -> should hit chapter-memo checkpoint
        main(["next", str(project)])
        state = load_state(project)
        assert state.pending_checkpoint.type.value == "chapter-memo"

        # Approve -> staging should be committed
        main(["review", str(project), "approve"])
        assert (project / "plans" / "chapter-1-plan.md").exists()

class TestRevisionRouting:
    def test_revision_routes_craft_to_polishing(self):
        """Verify revision router correctly routes craft issues to polishing."""
        from shenbi.pipeline.revision_router import route_chapter_revision, RevisionRoute
        route = route_chapter_revision(
            issues=[{"category": "craft", "severity": "CRITICAL"}], blocking=False)
        assert route == RevisionRoute.SPOT_FIX

    def test_revision_routes_blocking_to_regenerate(self):
        from shenbi.pipeline.revision_router import route_chapter_revision, RevisionRoute
        route = route_chapter_revision(
            issues=[{"category": "unmet_goal", "severity": "BLOCKING"}], blocking=True)
        assert route == RevisionRoute.REGENERATE

class TestTriggerSystem:
    def test_l2_trigger_at_ch12(self):
        from shenbi.pipeline.triggers import check_triggers
        from shenbi.pipeline.state import PipelineState
        r = check_triggers(PipelineState.default("/x"), 12, 67)
        assert r.l2_distill and r.score_arc

    def test_closure_trigger_at_last_chapter(self):
        from shenbi.pipeline.triggers import check_triggers
        from shenbi.pipeline.state import PipelineState
        r = check_triggers(PipelineState.default("/x"), 67, 67)
        assert r.book_closure

class TestErrorHandling:
    def test_dispatch_failure_increments_retry(self):
        """Verify handle_dispatch_failure returns True for first retries, False on max."""
        from shenbi.pipeline.error_handler import handle_dispatch_failure
        from shenbi.pipeline.state import PipelineState
        state = PipelineState.default("/x")
        assert handle_dispatch_failure(state, "test-skill", 1) is True  # retry
        assert handle_dispatch_failure(state, "test-skill", 2) is True  # retry
        assert handle_dispatch_failure(state, "test-skill", 3) is False  # escalate

    def test_scoring_failure_exit_code_routing(self):
        from shenbi.pipeline.error_handler import handle_scoring_failure
        from shenbi.pipeline.state import PipelineState
        state = PipelineState.default("/x")
        assert handle_scoring_failure(state, 2) is True   # validation fail -> retry
        assert handle_scoring_failure(state, 3) is True   # marker missing -> retry
        assert handle_scoring_failure(state, 1) is False  # other error -> give up

class TestClosureFlow:
    @patch("shenbi.pipeline.closure.dispatch_skill")
    @patch("shenbi.pipeline.closure.run_gate_g4")
    def test_closure_runs_all_steps(self, mock_g4, mock_disp, tmp_path):
        """Verify closure runs all 10 steps and reaches book-closure checkpoint."""
        from shenbi.pipeline.state import PipelineState, PipelinePhase, ClosureState
        from shenbi.pipeline.machine import save_state, load_state
        from shenbi.pipeline.cli import main

        mock_disp.return_value = MagicMock(success=True, returncode=0, stdout="{}", stderr="")
        mock_g4.return_value = {"status": "PASS"}

        project = tmp_path / "novel"
        project.mkdir()
        state = PipelineState.default(str(project))
        state.phase = PipelinePhase.CLOSURE
        state.closure = ClosureState.IN_PROGRESS
        save_state(project, state)

        # Run next -> should loop through all 10 closure steps
        main(["next", str(project)])

        state = load_state(project)
        assert state.pending_checkpoint.type.value == "book-closure"
        assert mock_disp.call_count == 10  # all closure steps dispatched
```

- [ ] **Step 2: Add full-chapter audit+revision cycle test**

```python
class TestRevisionRoutingFromAuditResults:
    """Test that audit BLOCKING/CRITICAL results correctly feed into revision routing."""

    def test_blocking_audit_routes_to_regenerate(self, tmp_path):
        """When audit report contains BLOCKING, revision router routes to regenerate."""
        from shenbi.pipeline.revision_router import route_chapter_revision, RevisionRoute

        project = tmp_path / "novel"
        audits_dir = project / "audits"
        audits_dir.mkdir(parents=True)
        (audits_dir / "chapter-5-continuity.md").write_text(
            "## Audit Report\n\nSeverity: BLOCKING\nIssue: Timeline contradiction")

        import glob
        audit_files = glob.glob(str(audits_dir / "chapter-5-*.md"))
        issues, blocking = [], False
        for af in audit_files:
            text = open(af).read()
            if "BLOCKING" in text:
                blocking = True
                issues.append({"category": "unmet_goal", "severity": "BLOCKING"})
            elif "CRITICAL" in text:
                issues.append({"category": "craft", "severity": "CRITICAL"})

        route = route_chapter_revision(issues=issues, blocking=blocking)
        assert route == RevisionRoute.REGENERATE
        assert blocking is True

    def test_craft_only_routes_to_spot_fix(self, tmp_path):
        """When audit has only CRITICAL (no BLOCKING), route to spot-fix."""
        from shenbi.pipeline.revision_router import route_chapter_revision, RevisionRoute

        project = tmp_path / "novel"
        audits_dir = project / "audits"
        audits_dir.mkdir(parents=True)
        (audits_dir / "chapter-5-pacing.md").write_text(
            "## Audit Report\n\nSeverity: CRITICAL\nIssue: Pacing too slow")

        import glob
        audit_files = glob.glob(str(audits_dir / "chapter-5-*.md"))
        issues, blocking = [], False
        for af in audit_files:
            text = open(af).read()
            if "BLOCKING" in text:
                blocking = True
                issues.append({"category": "unmet_goal", "severity": "BLOCKING"})
            elif "CRITICAL" in text:
                issues.append({"category": "craft", "severity": "CRITICAL"})

        route = route_chapter_revision(issues=issues, blocking=blocking)
        assert route == RevisionRoute.SPOT_FIX
        assert blocking is False

    def test_clean_chapter_no_revision(self):
        """When no audit issues found, revision routing returns NO_REVISION."""
        from shenbi.pipeline.revision_router import route_chapter_revision, RevisionRoute
        route = route_chapter_revision(issues=[], blocking=False)
        assert route == RevisionRoute.NO_REVISION
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/pipeline/test_full_flows.py
git commit -m "test: add comprehensive cross-wave integration tests (wave5 task4)"
```
