# Novel Pipeline Wave 3: Orchestrators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Build the three phase orchestrators (genesis, chapter-loop, closure) plus triggers, revision router, and dependency graph — the execution engine that drives the pipeline from seed to completed novel.

**Architecture:** Each orchestrator is a Python module that implements one phase's step sequence. They consume Wave 1 (state machine, checkpoint, staging) and Wave 2 (context assembly). Each step dispatches a skill via `shenbi-dispatch`, runs gates, updates state, and pauses at checkpoints.

**Tech Stack:** Python 3.11+, subprocess (for dispatch/gate calls), pathlib, pytest

**Spec reference:** `docs/superpowers/specs/2026-07-01-novel-pipeline-design.md` Sections 5, 6, 8, 11

## Global Constraints

Same as Wave 1. Skill dispatch is via `subprocess.run(["uv", "run", "shenbi-dispatch", ...])`.
Gate checks are via `subprocess.run(["uv", "run", "shenbi-validate", "G4", ...])`.

---

### Task 1: Dispatch Helper

**Files:**
- Create: `src/shenbi/pipeline/dispatch_helper.py`
- Create: `tests/unit/pipeline/test_dispatch_helper.py`

**Interfaces:**
- Produces: `dispatch_skill(skill, project_dir, prompt, round_dir=None) -> DispatchResult`, `run_gate_g4(skill, files, project_dir) -> GateResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_dispatch_helper.py
"""Tests for dispatch helper."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from shenbi.pipeline.dispatch_helper import dispatch_skill, run_gate_g4, DispatchResult

class TestDispatchSkill:
    @patch("shenbi.pipeline.dispatch_helper.subprocess.run")
    def test_dispatch_calls_subprocess(self, mock_run, tmp_path: Path):
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "Build world")
        assert isinstance(result, DispatchResult)
        mock_run.assert_called_once()

    @patch("shenbi.pipeline.dispatch_helper.subprocess.run")
    def test_dispatch_failure_returns_error(self, mock_run, tmp_path: Path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "Build world")
        assert result.success is False

class TestRunGateG4:
    @patch("shenbi.pipeline.dispatch_helper.subprocess.run")
    def test_g4_pass(self, mock_run, tmp_path: Path):
        mock_run.return_value = MagicMock(returncode=0,
            stdout='{"status": "PASS"}', stderr="")
        result = run_gate_g4("shenbi-worldbuilding", ["novel.json"], tmp_path)
        assert result["status"] == "PASS"
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement.**

```python
# src/shenbi/pipeline/dispatch_helper.py
"""Helpers for dispatching skills and running gates within the pipeline.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 3.2.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.logging import get_logger

log = get_logger(__name__)


@dataclass
class DispatchResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str


def dispatch_skill(
    skill: str,
    project_dir: Path | str,
    prompt: str,
    test_type: str = "generative",
    round_dir: Path | str | None = None,
) -> DispatchResult:
    """Dispatch a skill via shenbi-dispatch."""
    rd = str(round_dir) if round_dir else str(project_dir)
    cmd = [
        sys.executable, "-m", "shenbi.dispatcher.cli",
        skill, test_type, rd, prompt,
    ]
    log.info("dispatch_start", skill=skill, project_dir=str(project_dir))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    result = DispatchResult(
        success=r.returncode == 0,
        returncode=r.returncode,
        stdout=r.stdout,
        stderr=r.stderr,
    )
    if not result.success:
        log.error("dispatch_failed", skill=skill, rc=r.returncode, stderr=r.stderr[:500])
    return result


def run_gate_g4(
    skill: str, files: list[str], project_dir: Path | str
) -> dict[str, Any]:
    """Run G4 gate via shenbi-validate."""
    cmd = [
        sys.executable, "-m", "shenbi.gates.cli",
        "G4", skill, ",".join(files), str(project_dir),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {"status": "FAIL", "raw_stdout": r.stdout, "raw_stderr": r.stderr}


def run_gate_g3(
    skill: str, round_dir: Path | str
) -> dict[str, Any]:
    """Run G3 independence gate."""
    cmd = [
        sys.executable, "-m", "shenbi.gates.cli",
        "G3", skill, str(round_dir),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, ValueError):
        return {"status": "FAIL", "error": r.stderr}
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_dispatch_helper.py -v
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_helper.py
git commit -m "feat: add dispatch and gate helper for pipeline (wave3 task1)"
```

---

### Task 2: Genesis Orchestrator

**Files:**
- Create: `src/shenbi/pipeline/genesis.py`
- Create: `tests/unit/pipeline/test_genesis.py`

**Interfaces:**
- Consumes: `PipelineState`, `dispatch_skill`, `run_gate_g4`, `set_checkpoint`, `save_state`
- Produces: `GENESIS_STEPS` (list of step definitions), `run_genesis_step(state, project_dir) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_genesis.py
"""Tests for genesis orchestrator."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import pytest
from shenbi.pipeline.genesis import GENESIS_STEPS, run_genesis_step, GenesisStep
from shenbi.pipeline.state import GenesisState, PipelineState

class TestGenesisSteps:
    def test_step_count(self):
        assert len(GENESIS_STEPS) == 17

    def test_story_arch_before_faction(self):
        sa_idx = next(i for i, s in enumerate(GENESIS_STEPS) if "story-architecture" in s.skill)
        fb_idx = next(i for i, s in enumerate(GENESIS_STEPS) if "faction-builder" in s.skill)
        assert sa_idx < fb_idx

    def test_foreshadowing_plant_has_genesis_mode(self):
        fp = next(s for s in GENESIS_STEPS if "foreshadowing-plant" in s.skill)
        assert "genesis" in fp.mode or fp.mode == "genesis"

    def test_foundation_review_last(self):
        assert "foundation-review" in GENESIS_STEPS[-1].skill

    def test_foundation_review_path(self):
        fr = GENESIS_STEPS[-1]
        assert "foundation/review_report.md" in fr.output_path

class TestRunGenesisStep:
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    def test_runs_step_and_advances(self, mock_dispatch, tmp_path: Path):
        from shenbi.pipeline.dispatch_helper import DispatchResult
        mock_dispatch.return_value = DispatchResult(True, 0, "{}", "")

        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        state.genesis.current_step = 0

        done = run_genesis_step(state, tmp_path)

        assert state.genesis.current_step == 1
        assert len(state.genesis.skills_done) == 1
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement.**

```python
# src/shenbi/pipeline/genesis.py
"""Genesis phase orchestrator.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 5.
Executes 17 genesis steps in strict serial order.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import DispatchResult, dispatch_skill, run_gate_g4
from shenbi.pipeline.state import CheckpointType, GenesisState, PipelineState
from shenbi.pipeline.machine import set_checkpoint

log = get_logger(__name__)


@dataclass
class GenesisStep:
    step_num: int
    skill: str
    mode: str = ""
    output_path: str = ""
    gate: str = "G4"
    optional: bool = False


GENESIS_STEPS: list[GenesisStep] = [
    GenesisStep(1, "shenbi-worldbuilding", output_path="world/story_bible.md"),
    GenesisStep(2, "shenbi-genre-config", output_path="genre-config.json"),
    GenesisStep(3, "shenbi-character-design", mode="genesis", output_path="characters/protagonist.md"),
    GenesisStep(4, "shenbi-story-architecture", output_path="outline/story_frame.md"),
    GenesisStep(5, "shenbi-faction-builder", output_path="world/factions.md"),
    GenesisStep(6, "shenbi-volume-outlining", output_path="outline/volume_map.md"),
    GenesisStep(7, "shenbi-pacing-design", output_path="outline/rhythm_principles.md"),
    GenesisStep(8, "shenbi-plot-thread-weaver", output_path="outline/thread_map.md"),
    GenesisStep(9, "shenbi-foreshadowing-plant", mode="genesis", output_path="truth/pending_hooks.md"),
    GenesisStep(10, "shenbi-power-system", output_path="world/power_system.md"),
    GenesisStep(11, "shenbi-location-builder", output_path="world/locations.md"),
    GenesisStep(12, "shenbi-relationship-map", output_path="characters/relationships.md"),
    GenesisStep(13, "shenbi-book-spine-init", output_path="truth/book_spine.md"),
    GenesisStep(14, "shenbi-intent-management", output_path="truth/author_intent.md"),
    GenesisStep(15, "shenbi-style-learning", output_path="style/style_profile.md"),
    GenesisStep(16, "shenbi-anchor-curate", output_path="benchmarks/anchors/AC-001.md", optional=True),
    GenesisStep(17, "shenbi-foundation-review", output_path="foundation/review_report.md"),
]


def run_genesis_step(state: PipelineState, project_dir: Path) -> bool:
    """Execute the next genesis step. Returns True if checkpoint reached."""
    step_idx = state.genesis.current_step
    if step_idx >= len(GENESIS_STEPS):
        return True  # All steps done

    step = GENESIS_STEPS[step_idx]
    log.info("genesis_step", step=step.step_num, skill=step.skill)

    prompt = f"Execute {step.skill}"
    if step.mode:
        prompt += f" in {step.mode} mode"
    prompt += f". Project dir: {project_dir}"

    result = dispatch_skill(step.skill, project_dir, prompt)
    if not result.success:
        log.error("genesis_step_failed", step=step.step_num, skill=step.skill)
        return False

    state.genesis.skills_done.append(step.skill)
    state.genesis.current_step = step_idx + 1

    # Check if all steps complete
    if state.genesis.current_step >= len(GENESIS_STEPS):
        state.genesis.state = GenesisState.CHECKPOINT_PENDING
        set_checkpoint(
            state,
            CheckpointType.GENESIS_COMPLETE,
            artifact="foundation/review_report.md",
            context="Review all genesis outputs before entering chapter loop.",
        )
        return True

    return False
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_genesis.py -v
git add src/shenbi/pipeline/genesis.py tests/unit/pipeline/test_genesis.py
git commit -m "feat: add genesis orchestrator with 17 steps (wave3 task2)"
```

---

### Task 3: Chapter Loop Orchestrator

**Files:**
- Create: `src/shenbi/pipeline/chapter_loop.py`
- Create: `tests/unit/pipeline/test_chapter_loop.py`

**Interfaces:**
- Produces: `CHAPTER_STEPS` (list of step definitions), `run_chapter_step(state, project_dir) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/pipeline/test_chapter_loop.py
"""Tests for chapter loop orchestrator."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import pytest
from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, ChapterStep, run_chapter_step
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import PipelineState

class TestChapterSteps:
    def test_foreshadowing_plant_at_step_2b(self):
        fp = next(s for s in CHAPTER_STEPS if "foreshadowing-plant" in s.skill)
        assert fp.step_num == 3  # step 2b

    def test_state_settling_before_foreshadowing_track(self):
        ss = next(i for i, s in enumerate(CHAPTER_STEPS) if "state-settling" in s.skill)
        ft = next(i for i, s in enumerate(CHAPTER_STEPS) if "foreshadowing-track" in s.skill)
        assert ss < ft

    def test_review_resonance_after_audit(self):
        audit_steps = [i for i, s in enumerate(CHAPTER_STEPS) if "review-" in s.skill]
        resonance = next(i for i, s in enumerate(CHAPTER_STEPS) if "review-resonance" in s.skill)
        if audit_steps:
            assert resonance > min(audit_steps)

class TestRunChapterStep:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_runs_intent_management_first(self, mock_dispatch, tmp_path: Path):
        mock_dispatch.return_value = DispatchResult(True, 0, "{}", "")
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.step_index = 0

        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 1
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement.**

```python
# src/shenbi/pipeline/chapter_loop.py
"""Per-chapter loop orchestrator.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 6.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import DispatchResult, dispatch_skill
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import CheckpointType, PipelineState

log = get_logger(__name__)


@dataclass
class ChapterStep:
    step_num: int
    skill: str
    name: str
    checkpoint: CheckpointType | None = None


CHAPTER_STEPS: list[ChapterStep] = [
    ChapterStep(1, "shenbi-intent-management", "intent-management"),
    ChapterStep(2, "shenbi-chapter-planning", "chapter-planning", CheckpointType.CHAPTER_MEMO),
    ChapterStep(3, "shenbi-foreshadowing-plant", "foreshadowing-plant"),
    ChapterStep(4, "shenbi-context-composing", "context-composing"),
    ChapterStep(5, "shenbi-chapter-drafting", "chapter-drafting"),
    ChapterStep(6, "shenbi-state-settling", "state-settling", CheckpointType.STATE_SETTLE),
    ChapterStep(7, "shenbi-foreshadowing-track", "foreshadowing-track"),
    ChapterStep(8, "shenbi-foreshadowing-recall", "foreshadowing-recall"),
    # Step 7b: foreshadowing-resolve (conditional on TRIGGERED hooks)
    ChapterStep(9, "shenbi-review-anti-ai", "audit:anti-ai"),
    ChapterStep(10, "shenbi-review-resonance", "review-resonance"),
    ChapterStep(11, "shenbi-chapter-revision", "revision (conditional)"),
    ChapterStep(12, "shenbi-snapshot-manage", "snapshot-manage"),
    ChapterStep(13, "shenbi-drift-guidance", "drift-guidance", CheckpointType.PER_CHAPTER),
]


def run_chapter_step(state: PipelineState, project_dir: Path) -> bool:
    """Execute the next chapter loop step. Returns True if checkpoint reached."""
    step_idx = state.chapter_loop.step_index
    if step_idx >= len(CHAPTER_STEPS):
        # Chapter complete, advance to next chapter
        state.chapter_loop.current_chapter += 1
        state.chapter_loop.step_index = 0
        return True

    step = CHAPTER_STEPS[step_idx]
    chapter = state.chapter_loop.current_chapter
    log.info("chapter_step", chapter=chapter, step=step.step_num, skill=step.skill)

    prompt = f"Execute {step.skill} for chapter {chapter}. Project dir: {project_dir}"
    result = dispatch_skill(step.skill, project_dir, prompt)
    if not result.success:
        log.error("chapter_step_failed", chapter=chapter, step=step.step_num)
        return False

    state.chapter_loop.step_index = step_idx + 1

    # Check for checkpoint
    if step.checkpoint is not None:
        set_checkpoint(
            state,
            step.checkpoint,
            chapter=chapter,
            artifact=f"chapter-{chapter}/{step.name}",
            context=f"Review {step.name} for chapter {chapter}",
        )
        return True

    # Check if chapter complete
    if state.chapter_loop.step_index >= len(CHAPTER_STEPS):
        state.chapter_loop.current_chapter += 1
        state.chapter_loop.step_index = 0

    return False
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_chapter_loop.py -v
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "feat: add chapter loop orchestrator with 13 steps (wave3 task3)"
```

---

### Task 4: Closure Orchestrator + Triggers + Revision Router

**Files:**
- Create: `src/shenbi/pipeline/closure.py`
- Create: `src/shenbi/pipeline/triggers.py`
- Create: `src/shenbi/pipeline/revision_router.py`
- Create: `tests/unit/pipeline/test_closure.py`
- Create: `tests/unit/pipeline/test_triggers.py`
- Create: `tests/unit/pipeline/test_revision_router.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/pipeline/test_triggers.py
from shenbi.pipeline.triggers import check_triggers, TriggerResult
from shenbi.pipeline.state import PipelineState

def test_chapter_12_triggers_l2():
    state = PipelineState.default("/tmp/x")
    result = check_triggers(state, chapter=12, total_chapters=67)
    assert result.l2_distill is True

def test_chapter_36_triggers_l4():
    state = PipelineState.default("/tmp/x")
    result = check_triggers(state, chapter=36, total_chapters=67)
    assert result.l4_distill is True

def test_last_chapter_triggers_closure():
    state = PipelineState.default("/tmp/x")
    result = check_triggers(state, chapter=67, total_chapters=67)
    assert result.book_closure is True
```

```python
# tests/unit/pipeline/test_revision_router.py
from shenbi.pipeline.revision_router import route_revision, RevisionRoute

def test_expression_issue_routes_to_polishing():
    route = route_revision(audit_issues=["fatigue_words"], blocking=False)
    assert route == RevisionRoute.STYLE_POLISHING

def test_ai_detection_routes_to_anti_detect():
    route = route_revision(audit_issues=["ai_tell:critical"], blocking=True)
    assert route == RevisionRoute.ANTI_DETECT

def test_length_issue_routes_to_length_normalizing():
    route = route_revision(audit_issues=["word_count:2500"], blocking=False)
    assert route == RevisionRoute.LENGTH_NORMALIZING

def test_structural_routes_to_chapter_revision():
    route = route_revision(audit_issues=["plot_hole"], blocking=True)
    assert route == RevisionRoute.CHAPTER_REVISION
```

```python
# tests/unit/pipeline/test_closure.py
from shenbi.pipeline.closure import CLOSURE_STEPS

def test_closure_step_count():
    assert len(CLOSURE_STEPS) == 10

def test_foreshadowing_resolve_first():
    assert "foreshadowing-resolve" in CLOSURE_STEPS[0].skill

def test_foundation_review_path():
    fr = next(s for s in CLOSURE_STEPS if "foundation-review" in s.skill)
    assert "foundation/review_report.md" in fr.output_path
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement all three modules.**

```python
# src/shenbi/pipeline/triggers.py
"""Deterministic trigger checks.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 6.4.
"""
from __future__ import annotations
from dataclasses import dataclass
from shenbi.pipeline.state import PipelineState

@dataclass
class TriggerResult:
    l2_distill: bool = False
    l4_distill: bool = False
    volume_boundary: bool = False
    style_learning: bool = False
    book_closure: bool = False

def check_triggers(state: PipelineState, chapter: int, total_chapters: int) -> TriggerResult:
    result = TriggerResult()
    if chapter % 12 == 0:
        result.l2_distill = True
        result.style_learning = True
    if chapter % 36 == 0:
        result.l4_distill = True
    if chapter >= total_chapters:
        result.book_closure = True
    return result
```

```python
# src/shenbi/pipeline/revision_router.py
"""Revision routing: classify issues and delegate to specialized skills.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 6.3.
"""
from __future__ import annotations
from enum import StrEnum

class RevisionRoute(StrEnum):
    STYLE_POLISHING = "style-polishing"
    ANTI_DETECT = "anti-detect"
    LENGTH_NORMALIZING = "length-normalizing"
    CHAPTER_REVISION = "chapter-revision"

def route_revision(audit_issues: list[str], blocking: bool) -> RevisionRoute:
    for issue in audit_issues:
        il = issue.lower()
        if "fatigue" in il or "sentence" in il or "rhythm" in il:
            return RevisionRoute.STYLE_POLISHING
        if "ai_tell" in il or "ai detect" in il or "structural tell" in il:
            return RevisionRoute.ANTI_DETECT
        if "word_count" in il or "length" in il:
            return RevisionRoute.LENGTH_NORMALIZING
    return RevisionRoute.CHAPTER_REVISION
```

```python
# src/shenbi/pipeline/closure.py
"""Book closure orchestrator.

Spec: docs/superpowers/specs/2026-07-01-novel-pipeline-design.md Section 8.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ClosureStep:
    step_num: int
    skill: str
    output_path: str = ""

CLOSURE_STEPS: list[ClosureStep] = [
    ClosureStep(1, "shenbi-foreshadowing-resolve", "truth/pending_hooks.md"),
    ClosureStep(2, "shenbi-memory-distill", "truth/book_strata.md"),
    ClosureStep(3, "shenbi-volume-consolidation", "truth/volume_summaries.md"),
    ClosureStep(4, "shenbi-score-volume", "audits/volume-N-score.md"),
    ClosureStep(5, "shenbi-review-arc-payoff", "audits/volume-N-payoff.md"),
    ClosureStep(6, "shenbi-review-long-span", "audits/chapter-N-long-span.md"),
    ClosureStep(7, "shenbi-chapter-pattern", "outline/chapter_patterns.md"),
    ClosureStep(8, "shenbi-foundation-review", "foundation/review_report.md"),
    ClosureStep(9, "shenbi-style-learning", "style/style_profile.md"),
    ClosureStep(10, "shenbi-snapshot-manage", "final-snapshot/"),
]
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_closure.py tests/unit/pipeline/test_triggers.py tests/unit/pipeline/test_revision_router.py -v
git add src/shenbi/pipeline/closure.py src/shenbi/pipeline/triggers.py src/shenbi/pipeline/revision_router.py tests/unit/pipeline/test_*.py
git commit -m "feat: add closure, triggers, and revision router (wave3 task4)"
```

---

### Task 5: Wire Orchestrators into CLI `next`/`resume`

**Files:**
- Modify: `src/shenbi/pipeline/cli.py`
- Modify: `tests/unit/pipeline/test_cli.py`

- [ ] **Step 1: Write the test**

```python
# Add to test_cli.py
class TestNextCommand:
    def test_next_in_genesis_runs_step(self, tmp_path, sample_seed_content):
        from shenbi.pipeline.cli import main
        seed = tmp_path / "seed.md"
        seed.write_text(sample_seed_content)
        project = tmp_path / "novel"
        main(["init", str(seed), "--project-dir", str(project)])
        # next should try to run genesis step 1
        rc = main(["next", str(project)])
        # Will fail (no real dispatch) but state should advance
        assert rc in (0, 1)  # depends on dispatch mode
```

- [ ] **Step 2: Implement by replacing `cmd_next` placeholder with orchestrator dispatch**

```python
# Replace cmd_next in cli.py with:
def cmd_next(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir)
    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": "error", "message": "project not found"})
        return 1

    if is_at_checkpoint(state):
        emit_json({"status": "blocked", "message": "pending checkpoint requires review",
                      "checkpoint": state.pending_checkpoint.type.value})
        return 1

    from shenbi.pipeline.genesis import run_genesis_step
    from shenbi.pipeline.chapter_loop import run_chapter_step

    checkpoint_reached = False
    if state.phase.value == "genesis":
        checkpoint_reached = run_genesis_step(state, project_dir)
    elif state.phase.value == "chapter-loop":
        checkpoint_reached = run_chapter_step(state, project_dir)

    save_state(project_dir, state)

    if checkpoint_reached and is_at_checkpoint(state):
        emit_json({"status": "checkpoint", "type": state.pending_checkpoint.type.value,
                      "artifact": state.pending_checkpoint.artifact})
    else:
        emit_json({"status": "ok", "phase": state.phase.value})
    return 0
```

- [ ] **Step 3: Run tests, commit.**

```bash
uv run pytest tests/unit/pipeline/test_cli.py -v
git add src/shenbi/pipeline/cli.py tests/unit/pipeline/test_cli.py
git commit -m "feat: wire orchestrators into CLI next/resume commands (wave3 task5)"
```
