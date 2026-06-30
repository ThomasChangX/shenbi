from __future__ import annotations

from pathlib import Path

from shenbi.contracts.thresholds import CONVERGENCE, T1_PASS, T2_PASS, T3_PASS, TEST_PASS


def test_thresholds_match_spec_values() -> None:
    """spec: >=94 tier advance, >=90 test pass, 100 convergence target."""
    assert T1_PASS == 94
    assert T2_PASS == 94
    assert T3_PASS == 94
    assert TEST_PASS == 90
    assert CONVERGENCE == 100


def test_gates_import_thresholds_as_fallback() -> None:
    """G3/G5 must import the named constant (single source), not a bare literal."""
    repo = Path(__file__).resolve().parents[3]
    g3_src = (repo / "src" / "shenbi" / "gates" / "g3.py").read_text(encoding="utf-8")
    g5_src = (repo / "src" / "shenbi" / "gates" / "g5.py").read_text(encoding="utf-8")
    assert "T1_PASS" in g3_src, "g3.py must reference thresholds.T1_PASS"
    assert "T2_PASS" in g5_src, "g5.py must reference thresholds.T2_PASS"
