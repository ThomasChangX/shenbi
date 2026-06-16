"""Property-based tests for shenbi.phase_runner using Hypothesis."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from shenbi.phase_runner import load_state, now_iso, save_state

# Strategy for filesystem-safe phase names.
_phase_name = st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-", min_size=1, max_size=20)


@given(phase=_phase_name)
def test_load_state_default_phase_round_trips(
    tmp_path_factory: pytest.TempPathFactory, phase: str
) -> None:
    """Default state for an unseen phase is created/steps=[]."""
    round_dir = tmp_path_factory.mktemp("round")
    state = load_state(str(round_dir), phase)
    assert state["phase"] == phase
    assert state["state"] == "created"
    assert state["steps"] == []


@given(phase=_phase_name)
def test_save_then_load_preserves_state(
    tmp_path_factory: pytest.TempPathFactory, phase: str
) -> None:
    round_dir = tmp_path_factory.mktemp("round")
    original = {
        "phase": phase,
        "state": "started",
        "steps": [{"action": "start", "timestamp": "2026-01-01T00:00:00+00:00"}],
    }
    save_state(str(round_dir), original)
    loaded = load_state(str(round_dir), phase)
    assert loaded == original


@given(seed=st.integers(min_value=0, max_value=10**6))
def test_now_iso_always_ends_with_utc_offset(seed: int) -> None:
    """now_iso always returns UTC timestamps regardless of when called."""
    ts = now_iso()
    assert ts.endswith("+00:00")


@given(
    phase=_phase_name,
    state=st.sampled_from(["created", "started", "skills_done", "scored", "finalized"]),
)
def test_state_persistence_round_trips_with_any_state(
    tmp_path_factory: pytest.TempPathFactory, phase: str, state: str
) -> None:
    round_dir = tmp_path_factory.mktemp("round")
    save_state(str(round_dir), {"phase": phase, "state": state, "steps": []})
    loaded = load_state(str(round_dir), phase)
    assert loaded["state"] == state


@given(n_steps=st.integers(min_value=0, max_value=10))
def test_save_preserves_arbitrary_step_count(
    tmp_path_factory: pytest.TempPathFactory, n_steps: int
) -> None:
    """Step lists of any size round-trip through save/load."""
    round_dir = tmp_path_factory.mktemp("round")
    steps = [{"action": "x", "i": i} for i in range(n_steps)]
    save_state(str(round_dir), {"phase": "p", "state": "started", "steps": steps})
    loaded = load_state(str(round_dir), "p")
    assert len(loaded["steps"]) == n_steps


@given(
    step_actions=st.lists(
        st.sampled_from(
            ["start", "pre-skill", "post-skill", "pre-score", "post-score", "finalize"]
        ),
        min_size=0,
        max_size=8,
    )
)
def test_state_steps_are_preserved_in_order(
    tmp_path_factory: pytest.TempPathFactory, step_actions: list[str]
) -> None:
    round_dir = tmp_path_factory.mktemp("round")
    steps = [{"action": a, "timestamp": "t"} for a in step_actions]
    save_state(
        str(round_dir),
        {"phase": "p", "state": "started", "steps": steps},
    )
    loaded = load_state(str(round_dir), "p")
    assert [s["action"] for s in loaded["steps"]] == step_actions


@given(n_calls=st.integers(min_value=2, max_value=5))
def test_consecutive_now_iso_calls_are_non_decreasing(
    tmp_path_factory: pytest.TempPathFactory, n_calls: int
) -> None:
    """Time moves forward — later now_iso() >= earlier now_iso()."""
    timestamps = [now_iso() for _ in range(n_calls)]
    assert timestamps == sorted(timestamps)
