"""spec #34 T907/T910/T909: ownerless-domain wiring tests.

- ChapterState.status load-side normalization (completed→complete + WARN,
  unknown value → structured ValueError)
- RevisionMode single domain (route.py/revision_router.py twins collapsed)
- genre-config approval.decision validated against enums.ApprovalDecision
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.contracts.enums import REVISION_MODE_ALIASES, ApprovalDecision, RevisionMode
from shenbi.pipeline.state import PipelineState
from shenbi.skill_utils.revision_routing.route import route_revision


def _state_with_status(status: str) -> PipelineState:
    return PipelineState.from_dict({"chapter_loop": {"chapter_states": {"7": {"status": status}}}})


def test_legacy_completed_normalized_to_complete() -> None:
    state = _state_with_status("completed")
    cs = state.chapter_loop.chapter_states["7"]
    assert cs.status == "complete"


def test_canonical_values_load_untouched() -> None:
    for value in ("pending", "in-progress", "complete", "settling_failed"):
        cs = _state_with_status(value)
        assert cs.chapter_loop.chapter_states["7"].status == value


def test_unknown_status_raises_structured() -> None:
    with pytest.raises(ValueError, match=r"chapter_states\[7\]\.status invalid"):
        _state_with_status("finishing")


def test_revision_mode_single_domain() -> None:
    # route.py local twin collapsed: import is the enums domain
    assert {m.value for m in RevisionMode} == {
        "spot-fix",
        "regenerate",
        "constrained-regenerate",
        "reconstruction",
        "no-revision",
    }
    assert route_revision({"issues": []}) == "spot-fix"
    # legacy alias mapping registered for read-side normalization
    assert REVISION_MODE_ALIASES == {"no_op": "no-revision"}


def test_genre_config_approval_uses_registered_domain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shenbi.contracts.skills.genre_config import GenreConfig

    # G0.9: real skill output fixture, not a hand-crafted payload
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "genre-config-example.json"
    ok = GenreConfig.model_validate(json.loads(fixture.read_text(encoding="utf-8")))
    assert ok.approval["decision"] in ApprovalDecision.__args__
    bad = json.loads(fixture.read_text(encoding="utf-8"))
    bad["approval"]["decision"] = "approve"  # command verb, not a value
    with pytest.raises(ValueError, match=r"approval\.decision"):
        GenreConfig.model_validate(bad)
    assert set(ApprovalDecision.__args__) == {"approved", "rejected"}
