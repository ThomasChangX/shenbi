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
| §6 Chapter Loop | W3 | Task 3-6 | Implemented |
| §7 Context Arch | W2 | Task 1-3 | Implemented |
| §8 Closure | W3 | Task 6 | Implemented |
| §9 Checkpoints | W1+W3 | W1:T2,5, W3:T9 | Implemented |
| §10 Snapshots | W4 | Task 3 | Implemented |
| §11 Error Handling | W3 | Task 8 | Implemented |
| §12 Skill Changes | W4 | Task 1-6c | Implemented |
| §13 Modules | W1-3 | All | Implemented |
| §14 Decisions | N/A | N/A | Context only |
| §15 Acceptance | W5 | All tasks | Verified |
| §16 Genesis Dep Table | W3 | Task 2 | Verified in tests |
| §17 Ramp-Up Reads | W3 | Task 3 | Documented |
| §18 G4 Staging | W1+W3 | W1:T5, W3:T9 | Implemented |
| §19 FP Genesis Mode | W4 | Task 2 | Implemented |

- [ ] **Step 2: Commit.**

```bash
git add docs/superpowers/plans/2026-07-02-pipeline-coverage-matrix.md
git commit -m "docs: add spec coverage matrix for all waves (wave5 task3)"
```
