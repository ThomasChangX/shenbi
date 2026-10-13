"""Genesis fixes from probe3 P2-R findings.

1. Missing declared artifacts must not silently advance skills_done: a G4
   ``not_found`` in auto mode routes to the retry budget → escalation
   checkpoint (probe3: genre-config-decisions.json never materialized — the
   sidecar was excluded from the dispatch instruction AND invisible to the
   G4 file list, so "continue regardless" advanced with it absent).
2. Contract-declared decisions sidecars join the genesis dispatch
   instruction and G4 file list (spec #30 T2 parity with the chapter loop).
3. spine-init's ``total_chapters: 0`` placeholder is deterministically
   synced to novel.json's step-6-fixed total, so the five-way
   reconciliation stops firing a false MUST-FIX on every new project; a
   non-zero divergent value is left for the gate to catch.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.genesis import GENESIS_STEPS, run_genesis_step
from shenbi.pipeline.state import CheckpointType, GenesisState, PipelineState


def _auto_state(tmp_path: Path, skill: str) -> PipelineState:
    state = PipelineState.default(str(tmp_path))
    state.genesis.state = GenesisState.IN_PROGRESS
    state.config.per_chapter_review_enabled = False  # auto mode
    state.genesis.current_step = next(i for i, s in enumerate(GENESIS_STEPS) if s.skill == skill)
    return state


def _seed_genre_config_project(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")


@patch("shenbi.pipeline.genesis.dispatch_skill")
@patch("shenbi.pipeline.genesis.run_gate_g4")
def test_auto_mode_not_found_escalates_instead_of_advancing(
    mock_g4, mock_disp, tmp_path: Path
) -> None:
    _seed_genre_config_project(tmp_path)
    mock_disp.return_value = DispatchResult(True, 0, "{}", "")
    mock_g4.return_value = {
        "status": "FAIL",
        "must_fix": ["G4.dec.not_found:genre-config-decisions.json"],
    }
    state = _auto_state(tmp_path, "shenbi-genre-config")

    for _ in range(3):
        run_genesis_step(state, tmp_path)

    assert state.pending_checkpoint.type == CheckpointType.ESCALATION
    assert "shenbi-genre-config" not in state.genesis.skills_done


@patch("shenbi.pipeline.genesis.dispatch_skill")
@patch("shenbi.pipeline.genesis.run_gate_g4")
def test_auto_mode_structural_failure_still_continues(mock_g4, mock_disp, tmp_path: Path) -> None:
    """The not_found routing must not reinstate review-mode semantics for
    fixable structural nits — auto mode's continue-regardless survives
    (pinned by test_c15 as well; this pins it next to the new branch).
    """
    _seed_genre_config_project(tmp_path)
    mock_disp.return_value = DispatchResult(True, 0, "{}", "")
    mock_g4.return_value = {"status": "FAIL", "must_fix": ["G4.ln.below_floor:x:1<1700"]}
    state = _auto_state(tmp_path, "shenbi-genre-config")

    run_genesis_step(state, tmp_path)  # first failure: auto retry
    assert state.genesis.retry_counts.get("shenbi-genre-config") == 1
    run_genesis_step(state, tmp_path)  # second: continue regardless
    assert "shenbi-genre-config" in state.genesis.skills_done
    assert state.pending_checkpoint.type == CheckpointType.NONE


@patch("shenbi.pipeline.genesis.dispatch_skill")
@patch("shenbi.pipeline.genesis.run_gate_g4")
def test_genre_config_sidecar_in_instruction_and_g4_list(
    mock_g4, mock_disp, tmp_path: Path
) -> None:
    _seed_genre_config_project(tmp_path)
    mock_disp.return_value = DispatchResult(True, 0, "{}", "")
    mock_g4.return_value = {"status": "PASS"}
    state = _auto_state(tmp_path, "shenbi-genre-config")

    run_genesis_step(state, tmp_path)

    outputs_override = mock_disp.call_args.kwargs.get("outputs_override")
    assert outputs_override is not None
    assert "genre-config.json" in outputs_override
    assert "genre-config-decisions.json" in outputs_override

    g4_files = mock_g4.call_args.args[1] if mock_g4.call_args.args else None
    assert g4_files is not None
    assert "genre-config-decisions.json" in g4_files


@patch("shenbi.pipeline.genesis.dispatch_skill")
@patch("shenbi.pipeline.genesis.run_gate_g4")
def test_spine_placeholder_total_synced_at_spine_init(mock_g4, mock_disp, tmp_path: Path) -> None:
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "novel.json").write_text(
        json.dumps({"total_chapters": 118, "target_word_count": 200000}),
        encoding="utf-8",
    )
    (tmp_path / "truth" / "book_spine.md").write_text(
        "---\nupdated: 2026-10-01\ntotal_chapters: 0\nstatus: pending_intent\n---\n\n# 书脊\n",
        encoding="utf-8",
    )
    mock_disp.return_value = DispatchResult(True, 0, "{}", "")
    mock_g4.return_value = {"status": "PASS"}
    state = _auto_state(tmp_path, "shenbi-book-spine-init")

    run_genesis_step(state, tmp_path)

    spine = (tmp_path / "truth" / "book_spine.md").read_text(encoding="utf-8")
    assert "total_chapters: 118" in spine
    assert "status: pending_intent" in spine, "status vocabulary is memory-distill's, not ours"


@patch("shenbi.pipeline.genesis.dispatch_skill")
@patch("shenbi.pipeline.genesis.run_gate_g4")
def test_spine_divergent_nonzero_total_left_for_gate(mock_g4, mock_disp, tmp_path: Path) -> None:
    """Only the 0 placeholder is synced — a real divergence must stay
    visible to the five-way reconciliation.
    """
    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "novel.json").write_text(json.dumps({"total_chapters": 118}), encoding="utf-8")
    (tmp_path / "truth" / "book_spine.md").write_text(
        "---\ntotal_chapters: 50\nstatus: pending_intent\n---\n\n# 书脊\n",
        encoding="utf-8",
    )
    mock_disp.return_value = DispatchResult(True, 0, "{}", "")
    mock_g4.return_value = {"status": "PASS"}
    state = _auto_state(tmp_path, "shenbi-book-spine-init")

    run_genesis_step(state, tmp_path)

    spine = (tmp_path / "truth" / "book_spine.md").read_text(encoding="utf-8")
    assert "total_chapters: 50" in spine
