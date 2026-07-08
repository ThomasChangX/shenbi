# tests/unit/contracts/schemas/test_novel_scores_state.py
import pytest
from pydantic import ValidationError

from shenbi.contracts.schemas.adapt import pydantic_err_to_gate_failures
from shenbi.contracts.schemas.novel import NovelConfig
from shenbi.contracts.schemas.scores import ScoreDimension, ScoreProvenance, ScoreReport
from shenbi.contracts.schemas.state import ProgressDoc, SummaryDoc

# --- NovelConfig (extra: forbid) ---


def test_novel_forbid():
    with pytest.raises(ValidationError):
        NovelConfig.model_validate({"title": "x", "bogus": True})


def test_novel_defaults_load_empty():
    n = NovelConfig.model_validate({})
    assert n.title == ""
    assert n.language == "zh"
    assert n.target_word_count == 0
    assert n.themes == []


def test_novel_target_word_count_field():
    # D26: producer writes target_word_count (authoritative); model uses it.
    n = NovelConfig.model_validate({"target_word_count": 50000})
    assert n.target_word_count == 50000


def test_d26_novel_config_loads_producer_shape():
    """D26 canary: NovelConfig loads the producer-authoritative fixture shape.

    The producer (seed_parser) writes ``target_word_count``; the model uses that
    name (extra: forbid). The canonical fixture tests/fixtures/novel-example.json
    must carry the producer field name (not the legacy ``target_words``), and the
    legacy key must be rejected by the model (forbid) since it is no longer the
    authoritative producer name.

    (A full fixture round-trip is out of scope here — the fixture's ``genre``
    is a list while the model declares ``str``; that is an unrelated shape gap.
    This canary pins only the D26 field-name contract.)
    """
    import json
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "novel-example.json"
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    # Producer-authoritative field present in the fixture.
    assert "target_word_count" in raw, "fixture must use producer shape (D26)"
    assert "target_words" not in raw, "fixture must not carry the legacy key (D26)"
    # The model accepts the producer field directly.
    n = NovelConfig.model_validate({"target_word_count": raw["target_word_count"]})
    assert n.target_word_count == raw["target_word_count"]
    # The legacy key is forbidden (extra: forbid).
    with pytest.raises(ValidationError):
        NovelConfig.model_validate({"target_words": 100000})


def test_d26_g6_reads_target_word_count():
    """D26 canary: g6.py derives expected chapters from target_word_count.

    The producer writes ``target_word_count``; g6.py used to read only
    ``target_words`` (so producer projects always fell back to the 100000
    default). After the fix a project with target_word_count=5000 and a single
    5000-word chapter passes G6.1 (expected=1, min_chapters=1).
    """
    import json
    import tempfile
    from pathlib import Path

    from shenbi.gates.g6 import gate_G6

    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        (project / "novel.json").write_text(
            json.dumps({"target_word_count": 5000}), encoding="utf-8"
        )
        (project / "genre-config.json").write_text(
            json.dumps({"chapter_word": {"default": 5000}}), encoding="utf-8"
        )
        (project / "chapters").mkdir()
        (project / "chapters" / "chapter-001.md").write_text(
            "# 第1章\n\n正文内容。\n", encoding="utf-8"
        )
        result = json.loads(gate_G6("long-form", str(project), str(project)))
        g61 = next((c for c in result["checks"] if c.get("id") == "G6.1"), None)
        assert g61 is not None
        assert g61["s"] == "PASS", (
            f"g6.py must read target_word_count (D26); got {result.get('must_fix', [])}"
        )


# --- ProgressDoc / SummaryDoc (extra: IGNORE — producer-uncontrolled) ---


def test_progress_ignore_allows_extra():
    # producer-uncontrolled (shell heredoc / missing writers): extra ignored, no fail.
    p = ProgressDoc.model_validate({"skills": {"a": 1}, "unknown_key": 1})
    assert p.skills == {"a": 1}
    assert p.completed_skill_names == []
    # extra key silently dropped — never stored on the model
    assert not hasattr(p, "unknown_key")


def test_summary_ignore_allows_extra():
    s = SummaryDoc.model_validate({"t1_scores": {"x": 9}, "anything": 1})
    assert s.t1_scores == {"x": 9}
    assert s.t2_scores == {}
    assert not hasattr(s, "anything")


def test_progress_defaults():
    p = ProgressDoc.model_validate({})
    assert p.skills == {}
    assert p.scoring_history == []


def test_summary_defaults():
    s = SummaryDoc.model_validate({})
    assert s.t3_scores == {}


# --- ScoreReport (extra: forbid, _provenance aliased) ---


def test_score_report_shape():
    r = ScoreReport.model_validate(
        {
            "dimensions": [{"num": 1, "name": "x", "weight": 1.0, "score": 90}],
            "final_score": 90,
            "classification": "pass",
            "_provenance": {"scored_by": "a", "timestamp": "t"},
        }
    )
    assert r.final_score == 90
    assert r.classification == "pass"
    assert r.provenance is not None
    assert r.provenance.scored_by == "a"


def test_score_report_forbids_extra():
    with pytest.raises(ValidationError):
        ScoreReport.model_validate({"final_score": 1, "bogus": True})


def test_score_dimension_requires_score():
    with pytest.raises(ValidationError):
        ScoreDimension.model_validate({"num": 1})


def test_score_provenance_defaults():
    sp = ScoreProvenance.model_validate({})
    assert sp.scored_by == ""
    assert sp.gate_markers_verified is False


# --- adapter: ValidationError -> gate micro-failure dicts ---


def test_adapter_maps_to_gate_failures():
    with pytest.raises(ValidationError) as exc_info:
        NovelConfig.model_validate({"bogus": True})
    fails = pydantic_err_to_gate_failures(exc_info.value, "novel.json", "G2.novel")
    assert any(f["s"] == "FAIL" for f in fails)
    assert all(f["file"] == "novel.json" for f in fails)
    assert all(f["id"].startswith("G2.novel.") for f in fails)
    # each failure has the canonical {id, file, s, r} keys
    assert all(set(f) == {"id", "file", "s", "r"} for f in fails)
    # the reason mentions the offending location and message
    assert any("bogus" in f["r"] for f in fails)
