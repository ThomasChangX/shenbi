"""Unit tests for G4 score checkers (spec §9.12)."""

from __future__ import annotations

import os
import tempfile

import pytest

from shenbi.gates.g4.score_arc import g4_score_arc
from shenbi.gates.g4.score_stratum import g4_score_stratum
from shenbi.gates.g4.score_volume import g4_score_volume


@pytest.mark.unit
def test_score_arc_passes_with_route_c_and_a():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Arc Score\n## Route C\ncontent\n## Route A\nAC-003")
        f.flush()
        result = g4_score_arc([f.name])
    os.unlink(f.name)
    assert '"status": "PASS"' in result


@pytest.mark.unit
def test_score_arc_fails_without_route_c():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Arc Score\n## Route A\nAC-003")
        f.flush()
        result = g4_score_arc([f.name])
    os.unlink(f.name)
    assert '"status": "FAIL"' in result


@pytest.mark.unit
def test_score_volume_passes_with_sections():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Volume Score\n## Route C\ncontent\n## Route A\nanchor")
        f.flush()
        result = g4_score_volume([f.name])
    os.unlink(f.name)
    assert '"status": "PASS"' in result


@pytest.mark.unit
def test_score_stratum_fails_without_route_c():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Stratum Score\n## some content without route sections")
        f.flush()
        result = g4_score_stratum([f.name])
    os.unlink(f.name)
    assert '"status": "FAIL"' in result
