# tests/unit/contracts/schemas/test_deps.py
from pathlib import Path

import pytest
from pydantic import ValidationError

from shenbi.contracts.schemas.deps import (
    DepsDoc,
    OutOfPipeline,
    PhaseDeps,
    PipelineDeps,
    phase_of,
)

REAL = Path(__file__).resolve().parents[4] / "tests" / "tiers" / "deps.json"


def _load():
    import json

    return DepsDoc.model_validate(json.loads(REAL.read_text(encoding="utf-8")))


# --- real deps.json load (the canonical correctness check) ---


def test_loads_real_deps_json():
    d = _load()
    assert "genesis" in d.t2_phases


def test_real_phases_have_g4_note():
    d = _load()
    # 5 phases carry _g4_note (phase-0 finding)
    noted = [p for p in d.t2_phases.values() if p.g4_note]
    assert len(noted) >= 1


def test_phase_of_locates_skill():
    d = _load()
    assert phase_of(d, "shenbi-worldbuilding") == "genesis"


def test_phase_of_unknown_returns_none():
    d = _load()
    assert phase_of(d, "shenbi-nonexistent") is None


def test_extra_rejected():
    with pytest.raises(ValidationError):
        DepsDoc.model_validate({"t2-phases": {}, "bogus": True})


# --- deeper shape assertions on the real file ---


def test_real_t2_phases_is_dict():
    # phase-0 fact: t2-phases is a DICT keyed by phase name, not a list.
    d = _load()
    assert isinstance(d.t2_phases, dict)
    assert all(isinstance(v, PhaseDeps) for v in d.t2_phases.values())


def test_real_has_all_top_level_keys():
    d = _load()
    assert set(d.t2_phases)  # non-empty
    assert set(d.t3_pipelines)
    assert d.tool_hashes  # _tool_hashes
    assert d.out_of_pipeline  # _out_of_pipeline
    assert d.calibration_hashes  # _calibration_hashes


def test_real_pipeline_has_min_chapter_ratio():
    d = _load()
    assert d.t3_pipelines["long-form"].min_chapter_ratio == 0.5
    assert d.t3_pipelines["short-form"].min_chapter_ratio == 1.0


def test_real_out_of_pipeline_shape():
    # _out_of_pipeline is a nested dict, NOT a list.
    d = _load()
    oop = d.out_of_pipeline
    assert isinstance(oop, OutOfPipeline)
    assert oop.t1_only_auxiliary
    assert oop.t1_only_meta
    assert oop.t1_only_drafting_phase
    assert oop.note  # _note is non-empty


def test_phase_of_checks_member_roster():
    # 'prerequisites' is a phase's member roster; phase_of finds a phase by member.
    d = _load()
    # 'shenbi-state-settling' is a drafting-phase member (not a phase name itself).
    assert phase_of(d, "shenbi-state-settling") == "drafting"


# --- alias / populate_by_name round-trip ---


def test_populate_by_name_roundtrip():
    # Construct by python name, serialize by alias, reload by alias.
    d = DepsDoc.model_validate(
        {
            "t2-phases": {"genesis": {"prerequisites": ["s1"]}},
            "t3-pipelines": {"long-form": {"min_chapter_ratio": 0.5}},
            "_tool_hashes": {"a": "h"},
            "_out_of_pipeline": {"t1_only_auxiliary": ["s2"], "_note": "n"},
            "_calibration_hashes": {"combined": "h2"},
        }
    )
    dumped = d.model_dump(by_alias=True, exclude_defaults=False)
    assert dumped["t2-phases"]["genesis"]["prerequisites"] == ["s1"]
    assert dumped["_out_of_pipeline"]["_note"] == "n"


# --- nested extra-forbid ---


def test_phase_deps_extra_rejected():
    with pytest.raises(ValidationError):
        PhaseDeps.model_validate({"prerequisites": [], "bogus": 1})


def test_pipeline_deps_extra_rejected():
    with pytest.raises(ValidationError):
        PipelineDeps.model_validate({"min_chapter_ratio": 0.0, "bogus": 1})


def test_out_of_pipeline_extra_rejected():
    with pytest.raises(ValidationError):
        OutOfPipeline.model_validate({"t1_only_auxiliary": [], "bogus": 1})


# --- defaults ---


def test_phase_deps_defaults():
    p = PhaseDeps.model_validate({})
    assert p.prerequisites == []
    assert p.expected_outputs == []
    assert p.g4_checker is None
    assert p.g4_note is None


def test_deps_doc_defaults():
    d = DepsDoc.model_validate({})
    assert d.t2_phases == {}
    assert d.t3_pipelines == {}
    assert d.tool_hashes == {}
    assert isinstance(d.out_of_pipeline, OutOfPipeline)
    assert d.calibration_hashes == {}
