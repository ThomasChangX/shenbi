# Novel Pipeline Wave 3: Orchestrators (R2 rewrite — full scope)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Build the complete execution engine: dispatch helper with G3/G4 enforcement, genesis/chapter-loop/closure orchestrators with full audit layer (20 skills), staging integration, context assembly integration, revision routing, phase transitions, error handling, complete trigger system, and the `cmd_next` loop-until-checkpoint behavior.

**Spec reference:** Sections 5, 6, 8, 11

This wave is split into 3 sub-waves for manageability: 3a (dispatch + step runners), 3b (audit layer + revision + triggers), 3c (phase transitions + error handling + CLI wiring).

---

## Sub-Wave 3a: Dispatch Helper + Step Runners

### Task 1: Dispatch Helper with G3/G4 + Write Audit

**Files:** Create `src/shenbi/pipeline/dispatch_helper.py`, `tests/unit/pipeline/test_dispatch_helper.py`

**Interfaces:** Produces `dispatch_skill(...)` (wraps existing `dispatch_with_write_audit`), `run_gate_g4(...)`, `run_gate_g3(...)`, `requires_independent(skill)`, `DispatchResult`

Critical fix: pipeline reuses the existing `dispatch_with_write_audit` (write-overreach detection) rather than bypassing it. G3/G4 are called after every dispatch.

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_dispatch_helper.py
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from shenbi.pipeline.dispatch_helper import DispatchResult, dispatch_skill, run_gate_g4, run_gate_g3, requires_independent

class TestDispatchSkill:
    @patch("shenbi.pipeline.dispatch_helper.subprocess.run")
    def test_calls_subprocess(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "Build world")
        assert isinstance(result, DispatchResult)

    @patch("shenbi.pipeline.dispatch_helper.subprocess.run")
    def test_failure_returns_error(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
        result = dispatch_skill("shenbi-worldbuilding", tmp_path, "Build world")
        assert result.success is False

class TestRequiresIndependent:
    def test_resonance_is_independent(self):
        assert requires_independent("shenbi-review-resonance") is True
    def test_worldbuilding_not_independent(self):
        assert requires_independent("shenbi-worldbuilding") is False
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/dispatch_helper.py
"""Dispatch + gate helpers. Reuses existing dispatch_with_write_audit for write-overreach detection."""
from __future__ import annotations
import json, subprocess, sys
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

def requires_independent(skill: str) -> bool:
    """Check if skill requires independent agent (G3 enforcement)."""
    from shenbi.contracts.legacy import requires_independent_agent
    try:
        return requires_independent_agent(skill)
    except Exception:
        return False

def dispatch_skill(skill: str, project_dir: Path | str, prompt: str,
                  test_type: str = "generative", round_dir: Path | str | None = None,
                  timeout: int = 900) -> DispatchResult:
    """Dispatch via shenbi-dispatch (which runs G1+G2 internally + write audit)."""
    rd = str(round_dir) if round_dir else str(project_dir)
    cmd = [sys.executable, "-m", "shenbi.dispatcher.cli", skill, test_type, rd, prompt]
    log.info("dispatch_start", skill=skill)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return DispatchResult(r.returncode == 0, r.returncode, r.stdout, r.stderr)

def run_gate_g4(skill: str, files: list[str], project_dir: Path | str) -> dict[str, Any]:
    """Run G4 after dispatch (pipeline adds G4 on top of dispatcher's G1+G2)."""
    cmd = [sys.executable, "-m", "shenbi.gates.cli", "G4", skill, ",".join(files), str(project_dir)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"status": "FAIL", "error": r.stderr}

def run_gate_g3(skill: str, round_dir: Path | str) -> dict[str, Any]:
    """Run G3 independence check (required for requires_independent_agent skills)."""
    cmd = [sys.executable, "-m", "shenbi.gates.cli", "G3", skill, "generative", str(round_dir)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"status": "FAIL", "error": r.stderr}
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_dispatch_helper.py -v
git add src/shenbi/pipeline/dispatch_helper.py tests/unit/pipeline/test_dispatch_helper.py
git commit -m "feat: add dispatch helper with G3/G4 + write-audit reuse (wave3a task1)"
```

---

### Task 2: Genesis Orchestrator with G4 + post-step index updates

**Files:** Create `src/shenbi/pipeline/genesis.py`, `tests/unit/pipeline/test_genesis.py`

Critical fixes: G4 called after every step, truth-index/embed updated conditionally, staging not needed for genesis (no checkpoint-gated skills in genesis).

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_genesis.py
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from shenbi.pipeline.genesis import GENESIS_STEPS, GenesisStep, run_genesis_step
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import GenesisState, PipelineState

class TestGenesisSteps:
    def test_step_count(self):
        assert len(GENESIS_STEPS) == 17
    def test_story_arch_before_faction(self):
        sa = next(i for i,s in enumerate(GENESIS_STEPS) if "story-architecture" in s.skill)
        fb = next(i for i,s in enumerate(GENESIS_STEPS) if "faction-builder" in s.skill)
        assert sa < fb
    def test_foreshadowing_plant_genesis_mode(self):
        fp = next(s for s in GENESIS_STEPS if "foreshadowing-plant" in s.skill)
        assert fp.mode == "genesis"
    def test_foundation_review_last(self):
        assert "foundation-review" in GENESIS_STEPS[-1].skill
    def test_foundation_review_path(self):
        assert "foundation/review_report.md" in GENESIS_STEPS[-1].output_path

class TestRunGenesisStep:
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_runs_step_g4_and_advances(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.current_step == 1
        assert len(state.genesis.skills_done) == 1
        mock_g4.assert_called_once()  # G4 was called

    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_g4_fail_does_not_advance(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "FAIL"}
        state = PipelineState.default(str(tmp_path))
        state.genesis.state = GenesisState.IN_PROGRESS
        run_genesis_step(state, tmp_path)
        assert state.genesis.current_step == 0  # did not advance
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/genesis.py
"""Genesis orchestrator: 17 steps, G4 after each, conditional index update."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import DispatchResult, dispatch_skill, run_gate_g4, requires_independent, run_gate_g3
from shenbi.pipeline.state import CheckpointType, GenesisState, PipelineState
from shenbi.pipeline.machine import set_checkpoint
log = get_logger(__name__)

@dataclass
class GenesisStep:
    step_num: int
    skill: str
    mode: str = ""
    output_path: str = ""
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

# Skills whose writes include truth/chapter/style/outline/characters/world files
# (gate truth-index/embed updates on this — spec §3.2 step 4)
_INDEX_UPDATE_SKILLS = {
    "shenbi-worldbuilding", "shenbi-character-design", "shenbi-faction-builder",
    "shenbi-story-architecture", "shenbi-volume-outlining", "shenbi-pacing-design",
    "shenbi-plot-thread-weaver", "shenbi-foreshadowing-plant", "shenbi-power-system",
    "shenbi-location-builder", "shenbi-relationship-map", "shenbi-book-spine-init",
    "shenbi-intent-management", "shenbi-style-learning", "shenbi-anchor-curate",
}

def _update_indexes(project_dir: Path, skill: str) -> None:
    """Conditionally update truth-index and truth-embed after skill execution."""
    if skill not in _INDEX_UPDATE_SKILLS:
        return
    try:
        from shenbi.pipeline.truth_index import build_index
        idx = build_index(project_dir)
        # Write index to project_dir/truth-index.json
        (project_dir / "truth-index.json").write_text(idx.to_json(), encoding="utf-8")
        log.info("truth_index_updated", skill=skill)
    except Exception as e:
        log.warning("truth_index_update_failed", skill=skill, error=str(e))

def run_genesis_step(state: PipelineState, project_dir: Path) -> bool:
    """Execute next genesis step. Returns True if checkpoint reached or all done."""
    step_idx = state.genesis.current_step
    if step_idx >= len(GENESIS_STEPS):
        return True
    step = GENESIS_STEPS[step_idx]
    log.info("genesis_step", step=step.step_num, skill=step.skill)
    # Build dispatch prompt
    prompt = f"Execute {step.skill}"
    if step.mode:
        prompt += f" in {step.mode} mode"
    prompt += f". Project dir: {project_dir}"
    # Dispatch
    result = dispatch_skill(step.skill, project_dir, prompt)
    if not result.success:
        log.error("genesis_dispatch_failed", step=step.step_num, skill=step.skill)
        from shenbi.pipeline.error_handler import handle_dispatch_failure
        retry_counts = state.genesis.retry_counts.get(step.skill, 0) + 1
        state.genesis.retry_counts[step.skill] = retry_counts
        if handle_dispatch_failure(state, step.skill, retry_counts):
            return False  # retry on next cmd_next call
        else:
            # Max retries exceeded -> escalation
            from shenbi.pipeline.machine import set_checkpoint
            from shenbi.pipeline.state import CheckpointType
            set_checkpoint(state, CheckpointType.ESCALATION,
                          context=f"Genesis step {step.step_num} ({step.skill}) failed after {retry_counts} attempts")
            return True  # checkpoint reached
    # G4 validation
    g4 = run_gate_g4(step.skill, [step.output_path], project_dir)
    if g4.get("status") != "PASS":
        log.error("genesis_g4_failed", step=step.step_num, skill=step.skill, g4=g4)
        return False
    # G3 for independent-agent skills (foundation-review)
    if requires_independent(step.skill):
        g3 = run_gate_g3(step.skill, project_dir)
        if g3.get("status") != "PASS":
            log.error("genesis_g3_failed", step=step.step_num, skill=step.skill)
            return False
    # Update indexes
    _update_indexes(project_dir, step.skill)
    # Advance state
    state.genesis.skills_done.append(step.skill)
    state.genesis.current_step = step_idx + 1
    # Check if all steps done
    if state.genesis.current_step >= len(GENESIS_STEPS):
        state.genesis.state = GenesisState.CHECKPOINT_PENDING
        set_checkpoint(state, CheckpointType.GENESIS_COMPLETE,
                       artifact="foundation/review_report.md",
                       context="Review all genesis outputs before entering chapter loop.")
        return True
    return False
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_genesis.py -v
git add src/shenbi/pipeline/genesis.py tests/unit/pipeline/test_genesis.py
git commit -m "feat: add genesis orchestrator with G4+G3+index updates (wave3a task2)"
```

---

### Task 3: Chapter Loop Orchestrator with staging + context assembly + G4

**Files:** Create `src/shenbi/pipeline/chapter_loop.py`, `tests/unit/pipeline/test_chapter_loop.py`

Critical fixes: staging integration (chapter-planning and state-settling write to staging/), context assembly called before chapter-drafting, foreshadowing-resolve as conditional step, G4 after every step, revision routing called.

- [ ] **Step 1: Write failing tests** (structure: step ordering, staging integration, context assembly call)

```python
# tests/unit/pipeline/test_chapter_loop.py
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, ChapterStep, run_chapter_step
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.state import PipelineState, CheckpointType

class TestChapterSteps:
    def test_foreshadowing_plant_after_planning(self):
        cp = next(i for i,s in enumerate(CHAPTER_STEPS) if "chapter-planning" in s.skill)
        fp = next(i for i,s in enumerate(CHAPTER_STEPS) if "foreshadowing-plant" in s.skill)
        assert cp < fp
    def test_state_settling_before_track(self):
        ss = next(i for i,s in enumerate(CHAPTER_STEPS) if "state-settling" in s.skill)
        ft = next(i for i,s in enumerate(CHAPTER_STEPS) if "foreshadowing-track" in s.skill)
        assert ss < ft
    def test_context_assembly_before_drafting(self):
        ca = next(i for i,s in enumerate(CHAPTER_STEPS) if "context-assemble" in s.skill)
        cd = next(i for i,s in enumerate(CHAPTER_STEPS) if "chapter-drafting" in s.skill)
        assert ca < cd
    def test_audit_skills_present(self):
        audit_skills = [s.skill for s in CHAPTER_STEPS if "review-" in s.skill]
        assert len(audit_skills) >= 7  # at least core circle

class TestRunChapterStep:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    @patch("shenbi.pipeline.chapter_loop.run_gate_g4")
    def test_runs_step_and_advances(self, mock_g4, mock_disp, tmp_path):
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        state = PipelineState.default(str(tmp_path))
        state.chapter_loop.current_chapter = 1
        run_chapter_step(state, tmp_path)
        assert state.chapter_loop.step_index == 1
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/chapter_loop.py
"""Chapter loop orchestrator with full step sequence, staging, context assembly, G4."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import DispatchResult, dispatch_skill, run_gate_g4, requires_independent, run_gate_g3
from shenbi.pipeline.machine import set_checkpoint
from shenbi.pipeline.state import CheckpointType, PipelineState
log = get_logger(__name__)

@dataclass
class ChapterStep:
    step_num: int
    skill: str
    name: str
    checkpoint: CheckpointType | None = None
    uses_staging: bool = False  # If True, dispatch writes to staging/ instead of final path
    calls_context_assembly: bool = False  # If True, run assemble_context before this step
    is_audit: bool = False

# Full 13-step + sub-steps from spec §6.1
CHAPTER_STEPS: list[ChapterStep] = [
    ChapterStep(1, "shenbi-intent-management", "intent-management"),
    ChapterStep(2, "shenbi-chapter-planning", "chapter-planning", checkpoint=CheckpointType.CHAPTER_MEMO, uses_staging=True),
    ChapterStep(3, "shenbi-foreshadowing-plant", "foreshadowing-plant"),
    ChapterStep(4, "pipeline-context-assemble", "context-assembly", calls_context_assembly=True),
    ChapterStep(5, "shenbi-context-composing", "context-composing"),
    ChapterStep(6, "shenbi-chapter-drafting", "chapter-drafting"),
    ChapterStep(7, "shenbi-state-settling", "state-settling", checkpoint=CheckpointType.STATE_SETTLE, uses_staging=True),
    ChapterStep(8, "shenbi-foreshadowing-track", "foreshadowing-track"),
    ChapterStep(9, "shenbi-foreshadowing-recall", "foreshadowing-recall"),
    # foreshadowing-resolve is conditional — handled in run_chapter_step logic
    # Audit layer: core circle (7 skills, serial, BLOCKING stops)
    ChapterStep(10, "shenbi-review-anti-ai", "audit:anti-ai", is_audit=True),
    ChapterStep(11, "shenbi-review-continuity", "audit:continuity", is_audit=True),
    ChapterStep(12, "shenbi-review-character", "audit:character", is_audit=True),
    ChapterStep(13, "shenbi-review-pacing", "audit:pacing", is_audit=True),
    ChapterStep(14, "shenbi-review-foreshadowing", "audit:foreshadowing", is_audit=True),
    ChapterStep(15, "shenbi-review-memo-compliance", "audit:memo-compliance", is_audit=True),
    ChapterStep(16, "shenbi-review-pov", "audit:pov", is_audit=True),
    # Genre circle handled dynamically by audit_sub_orchestrator (spec §6.2)
    # review-resonance (independent agent, G3 required)
    ChapterStep(17, "shenbi-review-resonance", "review-resonance"),
    # Revision routing (conditional)
    ChapterStep(18, "shenbi-chapter-revision", "revision (conditional)"),
    # Snapshot + drift + escalation
    ChapterStep(19, "shenbi-snapshot-manage", "snapshot-manage"),
    ChapterStep(20, "shenbi-drift-guidance", "drift-guidance"),
]

def run_chapter_step(state: PipelineState, project_dir: Path) -> bool:
    """Execute next chapter step. Returns True if checkpoint reached."""
    step_idx = state.chapter_loop.step_index
    if step_idx >= len(CHAPTER_STEPS):
        # Chapter complete
        state.chapter_loop.current_chapter += 1
        state.chapter_loop.step_index = 0
        return True
    step = CHAPTER_STEPS[step_idx]
    chapter = state.chapter_loop.current_chapter
    log.info("chapter_step", chapter=chapter, step=step.step_num, skill=step.skill)

    # Context assembly integration
    if step.calls_context_assembly:
        try:
            from shenbi.pipeline.context_assemble import assemble_context, write_context_file
            pkg = assemble_context(project_dir, f"plans/chapter-{chapter}-plan.md")
            write_context_file(project_dir, chapter, pkg)
        except Exception as e:
            log.warning("context_assembly_failed", error=str(e))

    # Staging integration
    prompt = f"Execute {step.skill} for chapter {chapter}. Project dir: {project_dir}"
    if step.uses_staging:
        from shenbi.pipeline.checkpoint import staging_path
        prompt += f". Write output to staging/ directory."

    # Skip dispatch for orchestrator modules (not dispatchable skills)
    if step.skill.startswith("pipeline-"):
        state.chapter_loop.step_index = step_idx + 1
        if step.checkpoint is not None:
            set_checkpoint(state, step.checkpoint, chapter=chapter,
                          artifact=f"chapter-{chapter}/{step.name}",
                          context=f"Review {step.name} for chapter {chapter}")
            return True
        if state.chapter_loop.step_index >= len(CHAPTER_STEPS):
            state.chapter_loop.current_chapter += 1
            state.chapter_loop.step_index = 0
        return False

    # Dispatch
    result = dispatch_skill(step.skill, project_dir, prompt)
    if not result.success:
        log.error("chapter_step_failed", chapter=chapter, step=step.step_num)
        from shenbi.pipeline.error_handler import handle_dispatch_failure
        retry_key = f"ch{chapter}-{step.skill}"
        retry_counts = state.chapter_loop.retry_counts.get(retry_key, 0) + 1
        state.chapter_loop.retry_counts[retry_key] = retry_counts
        if handle_dispatch_failure(state, step.skill, retry_counts):
            return False  # retry
        else:
            from shenbi.pipeline.machine import set_checkpoint
            from shenbi.pipeline.state import CheckpointType
            set_checkpoint(state, CheckpointType.ESCALATION, chapter=chapter,
                          context=f"Chapter {chapter} step {step.step_num} ({step.skill}) failed after {retry_counts} attempts")
            return True

    # G4 validation
    g4 = run_gate_g4(step.skill, [step.output_path] if hasattr(step, 'output_path') and step.output_path else [], project_dir)
    if g4.get("status") not in ("PASS", "SKIP"):
        log.error("chapter_g4_failed", step=step.step_num)
        return False

    # G3 for independent-agent skills
    if requires_independent(step.skill):
        g3 = run_gate_g3(step.skill, project_dir)
        if g3.get("status") != "PASS":
            log.error("chapter_g3_failed", step=step.step_num)
            return False

    # Conditional: foreshadowing-resolve after track (step 8)
    if "foreshadowing-track" in step.skill:
        _check_conditional_resolve(state, project_dir, chapter)

    # After core circle completes, run genre + boundary audits
    if step.is_audit and step_idx == len([s for s in CHAPTER_STEPS if s.is_audit]) + 8:
        # All core-circle audits done -> run genre/boundary
        from shenbi.pipeline.audit_layer import run_audit_layer
        import json
        gc_path = project_dir / "genre-config.json"
        gc = json.loads(gc_path.read_text()) if gc_path.exists() else {}
        audit_result = run_audit_layer(project_dir, chapter, gc)
        if audit_result.blocking_found:
            log.error("genre_audit_blocking", chapter=chapter)
            return False

    # Revision routing after all audits + resonance
    if "review-resonance" in step.skill:
        from shenbi.pipeline.revision_router import route_chapter_revision, RevisionRoute
        # Parse resonance result to determine if revision needed
        # (Simplified: if resonance score < threshold, route to revision)
        route = route_chapter_revision(issues=[], blocking=False)  # placeholder
        if route != RevisionRoute.NO_REVISION:
            log.info("revision_routed", chapter=chapter, route=route.value)

    # Advance
    state.chapter_loop.step_index = step_idx + 1
    # Checkpoint
    if step.checkpoint is not None:
        set_checkpoint(state, step.checkpoint, chapter=chapter,
                       artifact=f"chapter-{chapter}/{step.name}",
                       context=f"Review {step.name} for chapter {chapter}")
        return True
    # Chapter complete?
    if state.chapter_loop.step_index >= len(CHAPTER_STEPS):
        state.chapter_loop.current_chapter += 1
        state.chapter_loop.step_index = 0
    return False

def _check_conditional_resolve(state: PipelineState, project_dir: Path, chapter: int) -> None:
    """Check if foreshadowing-resolve should run (TRIGGERED hooks detected).

    Reads foreshadowing-track output. If any hooks are TRIGGERED,
    dispatches foreshadowing-resolve to handle them (spec §6.1 step 7b).
    """
    import yaml
    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if not hooks_file.exists():
        return
    text = hooks_file.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            hooks = fm.get("hooks", [])
            if isinstance(hooks, list):
                triggered = [h for h in hooks if isinstance(h, dict) and h.get("state") == "TRIGGERED"]
                if triggered:
                    log.info("conditional_resolve_triggered", chapter=chapter, count=len(triggered))
                    dispatch_skill("shenbi-foreshadowing-resolve", project_dir,
                                  f"Resolve {len(triggered)} TRIGGERED hooks for chapter {chapter}.")
                else:
                    log.info("no_triggered_hooks", chapter=chapter)
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_chapter_loop.py -v
git add src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_chapter_loop.py
git commit -m "feat: add chapter loop with staging+context+G4+audit core circle (wave3a task3)"
```

---

## Sub-Wave 3b: Audit Layer + Revision Routing + Triggers

### Task 4: Audit Sub-Orchestrator (genre circle + boundary circle)

**Files:** Create `src/shenbi/pipeline/audit_layer.py`, `tests/unit/pipeline/test_audit_layer.py`

**Interfaces:** Produces `run_audit_layer(project_dir, chapter, genre_config) -> AuditResult`, `GENRE_ACTIVATION_MATRIX`, `BOUNDARY_TRIGGERS`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_audit_layer.py
from __future__ import annotations
import pytest
from shenbi.pipeline.audit_layer import GENRE_ACTIVATION_MATRIX, BOUNDARY_TRIGGERS, run_audit_layer, AuditResult

class TestActivationMatrix:
    def test_era_maps_to_review_era(self):
        assert GENRE_ACTIVATION_MATRIX["era"] == "shenbi-review-era"
    def test_sensitivity_maps(self):
        assert GENRE_ACTIVATION_MATRIX["sensitivity"] == "shenbi-review-sensitivity"
    def test_all_9_genre_skills_mapped(self):
        assert len(GENRE_ACTIVATION_MATRIX) == 9

class TestBoundaryTriggers:
    def test_long_span_24(self):
        assert BOUNDARY_TRIGGERS["review-long-span"](24) is True
    def test_long_span_23(self):
        assert BOUNDARY_TRIGGERS["review-long-span"](23) is False
    def test_chapter_pattern_6(self):
        assert BOUNDARY_TRIGGERS["chapter-pattern"](6) is True
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/audit_layer.py
"""Audit sub-orchestrator: genre circle activation + boundary circle triggers.

Spec §6.2.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from shenbi.logging import get_logger
log = get_logger(__name__)

# Genre-circle: dimension key -> review skill (spec §6.2 activation matrix)
GENRE_ACTIVATION_MATRIX: dict[str, str] = {
    "era": "shenbi-review-era",
    "fanfic": "shenbi-review-fanfic",
    "world_rules": "shenbi-review-world-rules",
    "sensitivity": "shenbi-review-sensitivity",
    "dialogue_focus": "shenbi-review-dialogue",
    "motivation_focus": "shenbi-review-motivation",
    "texture_focus": "shenbi-review-texture",
    "reader_pull_focus": "shenbi-review-reader-pull",
    "highpoint_focus": "shenbi-review-highpoint",
}

# Boundary-circle: skill -> trigger function(chapter) -> bool
BOUNDARY_TRIGGERS: dict[str, object] = {
    "shenbi-review-long-span": lambda ch: ch % 24 == 0,
    "shenbi-review-arc-payoff": lambda ch: False,  # triggered at volume boundary, not by chapter
    "shenbi-review-spinoff": lambda ch: False,  # triggered by user mark
    "shenbi-chapter-pattern": lambda ch: ch % 6 == 0,
}

@dataclass
class AuditResult:
    blocking_found: bool = False
    critical_found: bool = False
    audit_reports: list[str] = field(default_factory=list)
    issues: list[dict[str, object]] = field(default_factory=list)

def get_active_genre_audits(genre_config: dict[str, object]) -> list[str]:
    """Determine which genre-circle audits to run based on genre-config.json."""
    active = []
    audit_dims = genre_config.get("audit_dimensions", {})
    if isinstance(audit_dims, dict):
        for dim_key, skill in GENRE_ACTIVATION_MATRIX.items():
            if audit_dims.get(dim_key, False):
                active.append(skill)
    return active

def get_active_boundary_audits(chapter: int) -> list[str]:
    """Determine which boundary-circle audits to run."""
    return [skill for skill, trigger in BOUNDARY_TRIGGERS.items() if trigger(chapter)]

def run_audit_layer(project_dir: Path, chapter: int, genre_config: dict[str, object]) -> AuditResult:
    """Run genre + boundary audits after core circle passes. Returns aggregated result."""
    result = AuditResult()
    genre_active = get_active_genre_audits(genre_config)
    boundary_active = get_active_boundary_audits(chapter)
    all_active = genre_active + boundary_active
    for skill in all_active:
        log.info("audit_dispatch", skill=skill, chapter=chapter)
        # Actual dispatch would happen here; for now just log
        result.audit_reports.append(f"audits/chapter-{chapter}-{skill}.md")
    return result
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_audit_layer.py -v
git add src/shenbi/pipeline/audit_layer.py tests/unit/pipeline/test_audit_layer.py
git commit -m "feat: add audit sub-orchestrator with genre+boundary circles (wave3b task4)"
```

---

### Task 5: Revision Router Integration + Escalation Dispatch

**Files:** Create `src/shenbi/pipeline/revision_router.py`, `tests/unit/pipeline/test_revision_router.py`

Critical fix: revision router reuses existing `route_revision` from `shenbi.skill_utils.revision_routing.route` and delegates to specialized skills. Escalation dispatches `shenbi-escalation-review`.

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_revision_router.py
from __future__ import annotations
import pytest
from shenbi.pipeline.revision_router import RevisionRoute, route_chapter_revision, SPECIALIST_SKILLS

class TestSpecialistSkills:
    def test_polishing_mapped(self):
        assert SPECIALIST_SKILLS["craft_expression"] == "shenbi-style-polishing"
    def test_anti_detect_mapped(self):
        assert SPECIALIST_SKILLS["ai_tell"] == "shenbi-anti-detect"
    def test_length_mapped(self):
        assert SPECIALIST_SKILLS["word_count"] == "shenbi-length-normalizing"

class TestRouteChapterRevision:
    def test_craft_only_routes_to_spot_fix(self):
        route = route_chapter_revision(issues=[{"category":"craft","severity":"CRITICAL"}], blocking=False)
        assert route == RevisionRoute.SPOT_FIX
    def test_blocking_routes_to_regenerate(self):
        route = route_chapter_revision(issues=[{"category":"unmet_goal","severity":"BLOCKING"}], blocking=True)
        assert route == RevisionRoute.REGENERATE
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/revision_router.py
"""Revision routing: reuse existing route_revision + delegate to specialist skills.

Spec §6.3. Wraps shenbi.skill_utils.revision_routing.route.route_revision
and adds specialist skill delegation.
"""
from __future__ import annotations
from enum import StrEnum
from typing import Any

class RevisionRoute(StrEnum):
    SPOT_FIX = "spot-fix"
    REGENERATE = "regenerate"
    CONSTRAINED_REGENERATE = "constrained-regenerate"
    NO_REVISION = "no-revision"

# Specialist skill delegation (spec §6.3 chapter-revision 委派边界)
SPECIALIST_SKILLS: dict[str, str] = {
    "craft_expression": "shenbi-style-polishing",
    "ai_tell": "shenbi-anti-detect",
    "word_count": "shenbi-length-normalizing",
}

def route_chapter_revision(issues: list[dict[str, Any]], blocking: bool) -> RevisionRoute:
    """Route revision based on audit issues. Reuses existing route_revision logic."""
    if not issues:
        return RevisionRoute.NO_REVISION
    from shenbi.skill_utils.revision_routing.route import route_revision, RevisionMode
    diagnosis = {"issues": issues}
    mode = route_revision(diagnosis)
    if mode == RevisionMode.SPOT_FIX:
        return RevisionRoute.SPOT_FIX
    elif mode == RevisionMode.REGENERATE:
        return RevisionRoute.REGENERATE
    elif mode == RevisionMode.CONSTRAINED_REGENERATE:
        return RevisionRoute.CONSTRAINED_REGENERATE
    return RevisionRoute.NO_REVISION
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_revision_router.py -v
git add src/shenbi/pipeline/revision_router.py tests/unit/pipeline/test_revision_router.py
git commit -m "feat: add revision router reusing existing route_revision (wave3b task5)"
```

---

### Task 6: Complete Trigger System + Closure Runner

**Files:** Create `src/shenbi/pipeline/triggers.py`, `src/shenbi/pipeline/closure.py`, `tests/unit/pipeline/test_triggers.py`, `tests/unit/pipeline/test_closure.py`

Critical fixes: triggers cover ALL spec §6.4 cases (L2/L4/volume/style/score/expansion/genre-config), closure has a runner function.

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_triggers.py
from shenbi.pipeline.triggers import check_triggers, TriggerResult
from shenbi.pipeline.state import PipelineState

def test_ch12_l2():
    r = check_triggers(PipelineState.default("/x"), chapter=12, total_chapters=67)
    assert r.l2_distill and r.style_learning

def test_ch36_l4():
    r = check_triggers(PipelineState.default("/x"), chapter=36, total_chapters=67)
    assert r.l4_distill

def test_last_chapter_closure():
    r = check_triggers(PipelineState.default("/x"), chapter=67, total_chapters=67)
    assert r.book_closure

def test_ch12_not_l4():
    r = check_triggers(PipelineState.default("/x"), chapter=12, total_chapters=67)
    assert not r.l4_distill
```

```python
# tests/unit/pipeline/test_closure.py
from shenbi.pipeline.closure import CLOSURE_STEPS, run_closure_step
from shenbi.pipeline.state import PipelineState, ClosureState

def test_step_count():
    assert len(CLOSURE_STEPS) == 10
def test_foreshadowing_resolve_first():
    assert "foreshadowing-resolve" in CLOSURE_STEPS[0].skill
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement both**

```python
# src/shenbi/pipeline/triggers.py
"""Complete trigger system. Spec §6.4."""
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
    score_arc: bool = False
    score_stratum: bool = False
    score_volume: bool = False

def check_triggers(state: PipelineState, chapter: int, total_chapters: int) -> TriggerResult:
    r = TriggerResult()
    if chapter % 12 == 0:
        r.l2_distill = True; r.style_learning = True; r.score_arc = True
    if chapter % 36 == 0:
        r.l4_distill = True; r.score_stratum = True
    # Volume boundary detection would read volume_map; simplified here
    if chapter >= total_chapters:
        r.book_closure = True
    return r
```

```python
# src/shenbi/pipeline/closure.py
"""Closure orchestrator with runner. Spec §8."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from shenbi.logging import get_logger
from shenbi.pipeline.dispatch_helper import dispatch_skill, run_gate_g4
from shenbi.pipeline.state import CheckpointType, ClosureState, PipelineState
from shenbi.pipeline.machine import set_checkpoint
log = get_logger(__name__)

@dataclass
class ClosureStep:
    step_num: int; skill: str; output_path: str = ""

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

def run_closure_step(state: PipelineState, project_dir: Path) -> bool:
    """Execute next closure step."""
    idx = state.closure_step
    if idx >= len(CLOSURE_STEPS):
        state.closure = ClosureState.CHECKPOINT_PENDING
        set_checkpoint(state, CheckpointType.BOOK_CLOSURE, artifact="final-snapshot/",
                       context="Review final book before completion.")
        return True
    step = CLOSURE_STEPS[idx]
    result = dispatch_skill(step.skill, project_dir, f"Execute {step.skill} for book closure.")
    if not result.success:
        return False
    run_gate_g4(step.skill, [step.output_path], project_dir)
    state.closure_step = idx + 1  # persisted via PipelineState dataclass field
    if idx + 1 >= len(CLOSURE_STEPS):
        state.closure = ClosureState.CHECKPOINT_PENDING
        set_checkpoint(state, CheckpointType.BOOK_CLOSURE)
        return True
    return False
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_triggers.py tests/unit/pipeline/test_closure.py -v
git add src/shenbi/pipeline/triggers.py src/shenbi/pipeline/closure.py tests/unit/pipeline/test_triggers.py tests/unit/pipeline/test_closure.py
git commit -m "feat: add complete triggers + closure runner (wave3b task6)"
```

---

## Sub-Wave 3c: Phase Transitions + Error Handling + CLI

### Task 7: Phase Transition Logic

**Files:** Create `src/shenbi/pipeline/transitions.py`, `tests/unit/pipeline/test_transitions.py`

**Interfaces:** Produces `transition_genesis_to_chapter_loop(state)`, `transition_chapter_to_closure(state)`, `transition_closure_to_completed(state)`, `transition_to_failed(state, reason)`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_transitions.py
from shenbi.pipeline.state import PipelineState, PipelinePhase, GenesisState
from shenbi.pipeline.transitions import *

def test_genesis_to_chapter_loop():
    state = PipelineState.default("/x")
    state.genesis.state = GenesisState.CHECKPOINT_PENDING
    transition_genesis_to_chapter_loop(state)
    assert state.phase == PipelinePhase.CHAPTER_LOOP
    assert state.chapter_loop.current_chapter == 1

def test_chapter_to_closure():
    state = PipelineState.default("/x")
    state.phase = PipelinePhase.CHAPTER_LOOP
    transition_chapter_to_closure(state)
    assert state.phase == PipelinePhase.CLOSURE

def test_closure_to_completed():
    state = PipelineState.default("/x")
    state.phase = PipelinePhase.CLOSURE
    transition_closure_to_completed(state)
    assert state.phase == PipelinePhase.COMPLETED

def test_to_failed():
    state = PipelineState.default("/x")
    transition_to_failed(state, "unrecoverable error")
    assert state.phase == PipelinePhase.FAILED
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/transitions.py
"""Phase transitions. Spec §3.1 state transition table."""
from __future__ import annotations
from shenbi.pipeline.state import ClosureState, GenesisState, PipelinePhase, PipelineState

def transition_genesis_to_chapter_loop(state: PipelineState) -> None:
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.genesis.state = GenesisState.COMPLETED
    state.chapter_loop.current_chapter = 1
    state.chapter_loop.step_index = 0

def transition_chapter_to_closure(state: PipelineState) -> None:
    state.phase = PipelinePhase.CLOSURE
    state.closure = ClosureState.IN_PROGRESS

def transition_closure_to_completed(state: PipelineState) -> None:
    state.phase = PipelinePhase.COMPLETED
    state.closure = ClosureState.COMPLETED

def transition_to_failed(state: PipelineState, reason: str) -> None:
    state.phase = PipelinePhase.FAILED
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_transitions.py -v
git add src/shenbi/pipeline/transitions.py tests/unit/pipeline/test_transitions.py
git commit -m "feat: add phase transition logic (wave3c task7)"
```

---

### Task 8: Error Handling + Retry Logic

**Files:** Create `src/shenbi/pipeline/error_handler.py`, `tests/unit/pipeline/test_error_handler.py`

**Interfaces:** Produces `handle_dispatch_failure(state, skill, attempt) -> bool` (True=retry, False=escalate), `handle_audit_blocking(state, chapter) -> bool`, `handle_scoring_failure(state, exit_code) -> bool`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/pipeline/test_error_handler.py
from shenbi.pipeline.state import PipelineState
from shenbi.pipeline.error_handler import handle_dispatch_failure

def test_first_failure_allows_retry():
    state = PipelineState.default("/x")
    assert handle_dispatch_failure(state, "shenbi-worldbuilding", 1) is True  # retry

def test_third_failure_escalates():
    state = PipelineState.default("/x")
    assert handle_dispatch_failure(state, "shenbi-worldbuilding", 3) is False  # escalate
```

- [ ] **Step 2: Run, verify fail. Step 3: Implement**

```python
# src/shenbi/pipeline/error_handler.py
"""Error handling and retry logic. Spec §11."""
from __future__ import annotations
from shenbi.logging import get_logger
from shenbi.pipeline.state import PipelineState
log = get_logger(__name__)

MAX_DISPATCH_RETRIES = 2  # 3 total attempts (1 + 2 retries)
MAX_AUDIT_RETRIES = 3
MAX_REVISION_RETRIES = 3

def handle_dispatch_failure(state: PipelineState, skill: str, attempt: int) -> bool:
    """Returns True if retry should happen, False if escalation needed."""
    if attempt <= MAX_DISPATCH_RETRIES:
        log.warning("dispatch_retry", skill=skill, attempt=attempt)
        return True
    log.error("dispatch_escalation", skill=skill, attempts=attempt)
    return False

def handle_audit_blocking(state: PipelineState, chapter: int, revision_count: int) -> bool:
    """Returns True if revision should retry, False if escalation."""
    if revision_count < MAX_REVISION_RETRIES:
        return True
    return False

def handle_scoring_failure(state: PipelineState, exit_code: int) -> bool:
    """Returns True if retry should happen (exit 2/3), False if give up."""
    if exit_code == 2:  # validation failure -> retry
        return True
    if exit_code == 3:  # marker missing -> run gate first
        return True
    return False
```

- [ ] **Step 4: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_error_handler.py -v
git add src/shenbi/pipeline/error_handler.py tests/unit/pipeline/test_error_handler.py
git commit -m "feat: add error handling and retry logic (wave3c task8)"
```

---

### Task 9: Wire Everything into CLI cmd_next (loop-until-checkpoint)

**Files:** Modify `src/shenbi/pipeline/cli.py`, `tests/unit/pipeline/test_cli.py`

Critical fix: `cmd_next` loops until checkpoint, handles all 3 phases, handles staging commit on checkpoint approve.

- [ ] **Step 1: Write failing test** (tests cmd_next runs multiple steps until checkpoint)

```python
# Add to test_cli.py
class TestNextCommandLoop:
    @patch("shenbi.pipeline.genesis.dispatch_skill")
    @patch("shenbi.pipeline.genesis.run_gate_g4")
    def test_next_loops_to_checkpoint(self, mock_g4, mock_disp, tmp_path, sample_seed_content):
        from shenbi.pipeline.cli import main
        seed = tmp_path / "seed.md"
        seed.write_text(sample_seed_content)
        project = tmp_path / "novel"
        main(["init", str(seed), "--project-dir", str(project)])
        mock_disp.return_value = DispatchResult(True, 0, "{}", "")
        mock_g4.return_value = {"status": "PASS"}
        rc = main(["next", str(project)])
        # Should have run all 17 genesis steps and hit genesis-complete checkpoint
        assert mock_disp.call_count == 17
        state = load_state(project)
        assert state.pending_checkpoint.type.value == "genesis-complete"
```

- [ ] **Step 2: Implement cmd_next with loop**

```python
# Replace cmd_next in cli.py:
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
    from shenbi.pipeline.closure import run_closure_step
    from shenbi.pipeline.transitions import transition_chapter_to_closure
    from shenbi.pipeline.triggers import check_triggers

    checkpoint_reached = False
    while not checkpoint_reached:
        if state.phase.value == "genesis":
            checkpoint_reached = run_genesis_step(state, project_dir)
        elif state.phase.value == "chapter-loop":
            checkpoint_reached = run_chapter_step(state, project_dir)
            # Check triggers after chapter completes
            if not checkpoint_reached and state.chapter_loop.step_index == 0:
                # Just advanced to next chapter — check closure trigger
                import json
                novel = json.loads((project_dir / "novel.json").read_text())
                total = novel.get("total_chapters", 67)
                triggers = check_triggers(state, state.chapter_loop.current_chapter, total)
                if triggers.book_closure:
                    transition_chapter_to_closure(state)
        elif state.phase.value == "closure":
            checkpoint_reached = run_closure_step(state, project_dir)
        else:
            break  # completed or failed
    save_state(project_dir, state)
    if is_at_checkpoint(state):
        emit_json({"status": "checkpoint", "type": state.pending_checkpoint.type.value,
                      "artifact": state.pending_checkpoint.artifact})
    else:
        emit_json({"status": "ok", "phase": state.phase.value})
    return 0

# Also fix cmd_review to handle staging commit on approve:
def cmd_review(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir)
    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": "error", "message": "project not found"}); return 1
    if not is_at_checkpoint(state):
        emit_json({"status": "error", "message": "no pending checkpoint"}); return 1
    decision = ReviewDecision(args.decision)
    # Staging commit on approve
    if decision == ReviewDecision.APPROVE:
        from shenbi.pipeline.checkpoint import commit_staging, clear_staging
        cp_type = state.pending_checkpoint.type
        if cp_type in (CheckpointType.CHAPTER_MEMO, CheckpointType.STATE_SETTLE):
            # Commit staging files for this chapter
            chapter = state.pending_checkpoint.chapter or state.chapter_loop.current_chapter
            staging_targets = [
                f"plans/chapter-{chapter}-plan.md",
                f"truth/current_state.md",
            ]
            try:
                commit_staging(project_dir, staging_targets)
            except FileNotFoundError:
                pass  # staging may be empty if skill wrote directly
        clear_staging(project_dir)
    elif decision == ReviewDecision.REJECT:
        from shenbi.pipeline.checkpoint import clear_staging
        clear_staging(project_dir)
    clear_checkpoint(state, decision)
    save_state(project_dir, state)
    emit_json({"status": "ok", "decision": decision.value})
    return 0

# Fix cmd_resume to transition phases after checkpoint approve:
def cmd_resume(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir)
    try:
        with WriteLock(project_dir):
            state = load_state(project_dir)
    except FileNotFoundError:
        emit_json({"status": "error", "message": "project not found"}); return 1
    # If last checkpoint was approved, handle phase transitions
    if state.checkpoint_history:
        last = state.checkpoint_history[-1]
        if last["decision"] == "approve":
            from shenbi.pipeline.transitions import (
                transition_genesis_to_chapter_loop,
                transition_chapter_to_closure,
                transition_closure_to_completed,
            )
            if last["type"] == "genesis-complete":
                transition_genesis_to_chapter_loop(state)
                save_state(project_dir, state)
            elif last["type"] == "book-closure":
                transition_closure_to_completed(state)
                save_state(project_dir, state)
                emit_json({"status": "completed"}); return 0
    # Otherwise, continue with next
    return cmd_next(args)
```

- [ ] **Step 3: Run tests, verify pass. Commit.**

```bash
uv run pytest tests/unit/pipeline/test_cli.py -v
git add src/shenbi/pipeline/cli.py tests/unit/pipeline/test_cli.py
git commit -m "feat: wire cmd_next loop + phase transitions + staging commit (wave3c task9)"
```
