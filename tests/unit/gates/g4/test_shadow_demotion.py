"""spec #82 T3: shadow demotion unit tests (gates/g4/shadow.py).

Promotion direction is the load-bearing case: shadow:false (promoted) must
stay HARD, unlisted check ids must stay HARD (fail-safe direction), and the
single-gate all-demoted case must leave an empty remaining list.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g4.shadow import apply_shadow, check_id, demote_must_fix

GENRE_CFG = {
    "version": "1",
    "approval": {"decision": "approved"},
    "auditDimensions": {f"d{i}": True for i in range(5)},
    "chapterTypes": {f"t{i}": True for i in range(6)},
    "customRules": [],
    "fatigueWords": {"禁用": []},
    "pacing": {"core_motif_touch": {"max_gap": 6, "shadow": True}},
    "updated": "",
    "market_params": {
        "payoff_density": {"window": 3, "min": 1},
        "hook_grading": {"max_consecutive_micro": 2},
        "cold_streak_cap": {"max": 3, "shadow": True},
        "hook_rotation": {"shadow": True},
        "retention_anchor": {"from_ch": 1, "to_ch": None, "shadow": True},
        "hot_hook_floor": {"window": 10, "min": 1, "shadow": False},  # promoted
    },
}


@pytest.fixture()
def proj(tmp_path: Path) -> Path:
    (tmp_path / "genre-config.json").write_text(
        json.dumps(GENRE_CFG, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


@pytest.mark.unit
def test_check_id_prefix_extraction() -> None:
    assert check_id("G4.cp.cold_streak_window:path:4>3") == "cp.cold_streak_window"
    assert check_id("G4.cd.hook_type_rotation:file:同型") == "cd.hook_type_rotation"


@pytest.mark.unit
def test_shadow_true_demotes(proj: Path) -> None:
    out = apply_shadow(proj, "G4.cp.cold_streak_window:plans/ch37:4>3")
    assert out is not None and out.startswith("[shadow]")


@pytest.mark.unit
def test_promoted_stays_hard(proj: Path) -> None:
    """Promotion direction: shadow:false → HARD (the load-bearing case)."""
    assert apply_shadow(proj, "G4.cp.hot_hook_window:plans/ch37:0/10") is None


@pytest.mark.unit
def test_unlisted_stays_hard(proj: Path) -> None:
    """Fail-safe direction: unlisted check ids never demote."""
    assert apply_shadow(proj, "G4.cd.no_hook:chapters/ch37:未检出钩") is None


@pytest.mark.unit
def test_key_absent_defaults_to_shadow(proj: Path) -> None:
    """Spec L-D default-shadow semantics: key absent → shadow:true (demote).

    The plan rev4 sketch comment said "key absent → stays HARD" — that
    contradicts spec L-D ("新 FAIL 门默认 shadow: true" + 配置缺席退 WARN);
    spec governs (deviation logged). Explicit shadow:false is the promotion.
    """
    cfg = json.loads((proj / "genre-config.json").read_text(encoding="utf-8"))
    del cfg["market_params"]["hook_rotation"]
    (proj / "genre-config.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    assert apply_shadow(proj, "G4.cd.hook_type_rotation:ch37:同型") is not None


@pytest.mark.unit
def test_pacing_block_source(proj: Path) -> None:
    out = apply_shadow(proj, "G4.cp.core_motif_touch:plans/ch37:7>6")
    assert out is not None  # pacing.core_motif_touch.shadow=true demotes


@pytest.mark.unit
def test_single_gate_all_demoted_leaves_empty(proj: Path) -> None:
    dem, rem = demote_must_fix(proj, ["G4.cp.cold_streak_window:a:4>3"])
    assert dem and not rem
    dem2, rem2 = demote_must_fix(proj, ["G4.cp.cold_streak_window:a:4>3", "G4.cd.no_hook:b:x"])
    assert len(dem2) == 1 and len(rem2) == 1


@pytest.mark.unit
def test_trace_writer_accepts_warn_action(tmp_path: Path) -> None:
    """Spec #82 T3: the #81 trace face accepts action="WARN" (free string).

    Writes one WARN event through TraceWriter and verifies chain integrity.
    """
    from shenbi.trace.compaction import verify_chain
    from shenbi.trace.event import TraceEvent
    from shenbi.trace.writer import TraceWriter

    TraceWriter(tmp_path).append(
        actor="chapter-loop",
        actor_role="SYSTEM",
        action="WARN",
        target="ch37",
        gate="shadow",
        payload={"chapter": 37, "item": "G4.cp.cold_streak_window:4>3"},
    )
    import json as _json

    lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
    events = [TraceEvent.model_validate(_json.loads(ln)) for ln in lines]
    assert events and events[-1].action == "WARN"
    assert verify_chain(events) == []


@pytest.mark.unit
def test_wiring_all_demoted_routes_pass_with_warnings(tmp_path: Path) -> None:
    """audit-T3/I3 wiring test (mutation-pinned): drives the REAL shared
    routing function `_shadow_route_g4` — delete its demotion block and
    this goes red.

    Single-gate shadow FAIL → PASS-with-warnings: retry_feedback cleared,
    manifest re-recorded PASS (latest-wins), trace WARN on the real face.
    """
    from shenbi.gates.gate_manifest import record_gate_result  # noqa: F401 -- route re-records
    from shenbi.pipeline.chapter_loop import _gate_passed, _shadow_route_g4
    from shenbi.pipeline.state import PipelineState

    (tmp_path / "genre-config.json").write_text(
        json.dumps(GENRE_CFG, ensure_ascii=False), encoding="utf-8"
    )
    rk = "ch37-shenbi-chapter-planning"
    state = PipelineState.default(str(tmp_path))
    state.chapter_loop.retry_feedback[rk] = "stale"
    fail_result = {
        "status": "FAIL",
        "must_fix": ["G4.cp.cold_streak_window:plans/ch37:4>3"],
        "checks": [],
    }

    routed, remaining = _shadow_route_g4(
        state,
        tmp_path,
        fail_result,  # type: ignore[arg-type]
        chapter=37,
        skill="shenbi-chapter-planning",
        rk=rk,
    )
    assert remaining == []  # all-demoted precondition pinned
    assert _gate_passed(routed)  # PASS-with-warnings, never generic_failure
    assert rk not in state.chapter_loop.retry_feedback  # cleanup replicated
    # trace WARN landed on the real face
    lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert any(json.loads(ln)["action"] == "WARN" for ln in lines)
    # manifest re-recorded with the demoted outcome (latest-wins)
    from shenbi.gates.gate_manifest import get_gate_result

    latest = get_gate_result(tmp_path, "chapter_loop", 37, "shenbi-chapter-planning", "G4")
    assert latest is not None and str(latest.get("status")) in {"PASS", "pass"}


@pytest.mark.unit
def test_wiring_partial_demotion_keeps_hard_items_only(tmp_path: Path) -> None:
    """audit-T3/I3+C1: mixed must_fix → demoted items never reach the classifier."""
    from shenbi.pipeline.chapter_loop import _classify_g4_failures, _shadow_route_g4
    from shenbi.pipeline.state import PipelineState

    (tmp_path / "genre-config.json").write_text(
        json.dumps(GENRE_CFG, ensure_ascii=False), encoding="utf-8"
    )
    mixed = [
        "G4.cp.cold_streak_window:plans/ch37:4>3",  # mapped → demoted
        "G4.cp.missing_emotion_tone:plans/ch37",  # unmapped → stays
    ]
    fail_result = {"status": "FAIL", "must_fix": mixed, "checks": []}
    routed, remaining = _shadow_route_g4(
        PipelineState(),
        tmp_path,
        fail_result,  # type: ignore[arg-type]
        chapter=37,
        skill="shenbi-chapter-planning",
        rk="ch37-x",
    )
    assert remaining is not None and len(remaining) == 1
    hard, soft, warn = _classify_g4_failures(remaining)  # classifier input = remaining ONLY
    assert not any("cold_streak_window" in h for h in hard)  # demoted never HARD
    assert any("missing_emotion_tone" in h for h in hard)
    assert "cold_streak_window" not in routed.get("must_fix", [])  # rewritten g4 carries rem only
