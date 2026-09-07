"""Genesis auto-mode G4-continue path coverage (F332, spec #53 C15).

Auto mode (per_chapter_review_enabled=False): a G4 failure retries once, then
continues despite the failure instead of escalating (genesis.py auto branch).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.genesis import run_genesis_step
from shenbi.pipeline.state import CheckpointType, GenesisState, PipelineState


def _auto_state(tmp_path: Path) -> PipelineState:
    state = PipelineState.default(str(tmp_path))
    state.genesis.state = GenesisState.IN_PROGRESS
    state.config.per_chapter_review_enabled = False  # auto mode
    return state


@patch("shenbi.pipeline.genesis.dispatch_skill")
@patch("shenbi.pipeline.genesis.run_gate_g4")
def test_auto_mode_g4_failure_retries_once_then_continues(
    mock_g4, mock_disp, tmp_path: Path
) -> None:
    mock_disp.return_value = DispatchResult(True, 0, "{}", "")
    mock_g4.return_value = {"status": "FAIL", "must_fix": ["x"]}
    state = _auto_state(tmp_path)

    # 1st G4 failure in auto mode: retry once (returns control, retry counted)
    result1 = run_genesis_step(state, tmp_path)
    assert result1 is False
    assert state.genesis.retry_counts.get("shenbi-worldbuilding") == 1
    # retry feedback stored for the retry dispatch
    assert "G4 check failed" in state.genesis.retry_feedback["shenbi-worldbuilding"]
    # no escalation checkpoint — that is the review-enabled branch
    assert state.pending_checkpoint.type == CheckpointType.NONE

    # 2nd failure on the same skill: continue despite G4 failure
    # (genesis_g4_continue_auto) — success path runs, retry counter cleared,
    # cursor advances past the step
    run_genesis_step(state, tmp_path)
    assert "shenbi-worldbuilding" not in state.genesis.retry_counts
    assert state.genesis.current_step == 1
    assert state.pending_checkpoint.type == CheckpointType.NONE


@patch("shenbi.pipeline.genesis.dispatch_skill")
@patch("shenbi.pipeline.genesis.run_gate_g4")
def test_auto_mode_g4_failure_does_not_escalate_to_checkpoint(
    mock_g4, mock_disp, tmp_path: Path
) -> None:
    """Contrast with review mode: auto mode never raises an escalation
    checkpoint on G4 failure, even across repeated attempts.
    """
    mock_disp.return_value = DispatchResult(True, 0, "{}", "")
    mock_g4.return_value = {"status": "FAIL", "must_fix": ["y"]}
    state = _auto_state(tmp_path)
    for _ in range(3):
        run_genesis_step(state, tmp_path)
    assert state.pending_checkpoint.type == CheckpointType.NONE
    assert state.genesis.state == GenesisState.IN_PROGRESS
