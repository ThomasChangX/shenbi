"""Unit tests for G4 score checkers (spec §9.12)."""

from __future__ import annotations

import os
import tempfile

import pytest

from shenbi.gates.g4.scoring_sections import g4_scoring_sections

# Characterization (C37 F427): unified checker must behave identically to the
# three former copy-paste checkers (arc/volume/stratum differed only in
# gate-name/code-prefix strings).


def _g4_score_arc(fps):
    return g4_scoring_sections(fps, "G4-score-arc", "G4.arc")


def _g4_score_volume(fps):
    return g4_scoring_sections(fps, "G4-score-volume", "G4.vol")


def _g4_score_stratum(fps):
    return g4_scoring_sections(fps, "G4-score-stratum", "G4.str")


@pytest.mark.unit
def test_score_arc_passes_with_route_c_and_a():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Arc Score\n## Route C\ncontent\n## Route A\nAC-003")
        f.flush()
        result = _g4_score_arc([f.name])
    os.unlink(f.name)
    assert '"status": "PASS"' in result


@pytest.mark.unit
def test_score_arc_fails_without_route_c():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Arc Score\n## Route A\nAC-003")
        f.flush()
        result = _g4_score_arc([f.name])
    os.unlink(f.name)
    assert '"status": "FAIL"' in result


@pytest.mark.unit
def test_score_volume_passes_with_sections():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Volume Score\n## Route C\ncontent\n## Route A\nanchor")
        f.flush()
        result = _g4_score_volume([f.name])
    os.unlink(f.name)
    assert '"status": "PASS"' in result


@pytest.mark.unit
def test_score_stratum_fails_without_route_c():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Stratum Score\n## some content without route sections")
        f.flush()
        result = _g4_score_stratum([f.name])
    os.unlink(f.name)
    assert '"status": "FAIL"' in result


@pytest.mark.unit
def test_router_registers_all_three_score_family_skills(tmp_path):
    """C37 F427 dead-wire guard: gate_G4 must route score-family skills."""
    from shenbi.gates.g4.generic import gate_G4

    out = tmp_path / "arc-score.md"
    out.write_text("## Route C\ncontent\n## Route A\nAC-001", encoding="utf-8")
    result = gate_G4("shenbi-score-arc", "generative", [str(out)])
    assert '"status": "PASS"' in result
    missing = gate_G4("shenbi-score-stratum", "generative", [])
    assert '"SKIP"' in missing or '"FAIL"' in missing
