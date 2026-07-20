"""Tests for G4 chapter_revision checker.

Revision decisions conform to DecisionsDoc: selections + adjustments arrays
(NOT a changes array). The checker validates adjustment content semantics
within that schema and returns a JSON result string for make_composite_checker.
"""

import json
import tempfile
from pathlib import Path
from typing import Any

from shenbi.gates.g4.chapter_revision import g4_chapter_revision


def _write_json(tmpdir: Path, filename: str, data: dict[str, Any]) -> Path:
    path = tmpdir / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return path


def _parse_result(result: str) -> dict[str, Any]:
    """The checker returns a JSON result string — parse it for assertions."""
    return json.loads(result)


def test_valid_spot_fix_revision_passes():
    """Spot-fix with non-empty adjustments (each rationale >= 20 chars) passes."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(
            d,
            "chapter-5-revision-decisions.json",
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-chapter-revision",
                "chapter": 5,
                "selections": [],
                "adjustments": [
                    {
                        "issue_id": "resonance.sentiment",
                        "severity": "high",
                        "handling": "explicit_callout",
                        "rationale": "Replace parameterized prose with human sensory scene.",
                    },
                    {
                        "issue_id": "resonance.immersion",
                        "severity": "medium",
                        "handling": "explicit_callout",
                        "rationale": "Remove system-term enumeration, add dialogue setup.",
                    },
                ],
                "produced_at": "2026-07-19T00:00:00+00:00",
            },
        )

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "PASS"
        assert parsed["must_fix"] == []


def test_valid_no_op_revision_passes():
    """No-op with empty adjustments but a documented skip in selections passes."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(
            d,
            "chapter-5-revision-decisions.json",
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-chapter-revision",
                "chapter": 5,
                "selections": [
                    {
                        "target": "no_revision_needed",
                        "selected": [],
                        "basis": "arc_relevance",
                        "severity": "low",
                        "omitted": [],
                    }
                ],
                "adjustments": [],
                "produced_at": "2026-07-19T00:00:00+00:00",
            },
        )

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "PASS"


def test_empty_adjustments_without_skip_documentation_fails():
    """Empty adjustments with no skip selection in selections is HARD FAIL."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(
            d,
            "chapter-5-revision-decisions.json",
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-chapter-revision",
                "chapter": 5,
                "selections": [],
                "adjustments": [],
                "produced_at": "2026-07-19T00:00:00+00:00",
            },
        )

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "HARD_FAIL"
        assert any("empty_adjustments" in m for m in parsed["must_fix"])


def test_adjustment_with_thin_rationale_fails():
    """An adjustment whose rationale is < 20 chars is a HARD FAIL."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(
            d,
            "chapter-5-revision-decisions.json",
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-chapter-revision",
                "chapter": 5,
                "selections": [],
                "adjustments": [
                    {
                        "issue_id": "x",
                        "severity": "high",
                        "handling": "compensate_via_pacing",
                        "rationale": "too short",
                    },
                ],
                "produced_at": "2026-07-19T00:00:00+00:00",
            },
        )

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "HARD_FAIL"
        assert any("thin_rationale" in m for m in parsed["must_fix"])


def test_invalid_json_fails():
    """JSON syntax error in revision output is reported (g4_decisions also catches it)."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = d / "chapter-5-revision-decisions.json"
        path.write_text("{invalid json")

        result = g4_chapter_revision([str(path)])
        parsed = _parse_result(result)
        assert parsed["status"] == "HARD_FAIL"
        assert any("invalid_json" in m for m in parsed["must_fix"])


def test_result_is_json_string_compatible_with_composite_checker():
    """Return value is a JSON string parseable into {status, checks, must_fix}."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path = _write_json(
            d,
            "chapter-5-revision-decisions.json",
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-chapter-revision",
                "chapter": 5,
                "selections": [],
                "adjustments": [],
                "produced_at": "2026-07-19T00:00:00+00:00",
            },
        )
        result = g4_chapter_revision([str(path)])
        # make_composite_checker (decisions_validator.py:87) does json.loads(existing_result)
        parsed = json.loads(result)
        assert set(parsed.keys()) >= {"status", "checks", "must_fix"}
        assert parsed["status"] in ("PASS", "HARD_FAIL")
