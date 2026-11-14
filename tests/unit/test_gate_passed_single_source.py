"""Spec #91 T1: gate_passed single-source characterization.

Pins the CURRENT per-site semantics BEFORE rewiring (spec r2.3c):
- triggers/closure sites: SKIP counts as passed (accept_skip=True target)
- chapter_loop/audit_layer/genesis + phase_runner/cli direct compares:
  only PASS counts (accept_skip=False target)
- chapter_loop:1597 compound: status None also passes
"""

from shenbi.status import GateStatus, gate_passed


def _res(status):
    return {"status": status}


# 11 rows pinning the 9 single-compare sites (audit-T1 C1: cli.py rows were
# dropped in the first landing; 1597/4063 compound/negative sites are pinned
# in Task 2's rewiring, not here).
SITES = [
    ("triggers.py:505/_gate_passed", _res("PASS"), True),
    (
        "triggers.py:505/_gate_passed",
        _res("SKIP"),
        True,
    ),  # SKIP passes in the triggers/closure family
    ("triggers.py:505/_gate_passed", _res("FAIL"), False),
    ("closure.py:125/_gate_passed", _res("SKIP"), True),
    ("chapter_loop.py:1446/_gate_passed", _res("SKIP"), False),  # SKIP fails here
    ("audit_layer.py:209/_gate_passed", _res("SKIP"), False),
    ("genesis.py:284/_gate_passed", _res("SKIP"), False),
    ("phase_runner.py:146/'PASS'", _res("SKIP"), False),
    ("phase_runner.py:378/'PASS'", _res("SKIP"), False),
    ("cli.py:223/GateStatus.PASS", _res("SKIP"), False),
    ("cli.py:255/GateStatus.PASS", _res("SKIP"), False),
]


def test_gate_passed_default_rejects_skip():
    assert gate_passed(_res(GateStatus.PASS)) is True
    assert gate_passed(_res(GateStatus.FAIL)) is False
    assert gate_passed(_res(GateStatus.SKIP)) is False
    assert gate_passed({}) is False


def test_gate_passed_accept_skip():
    assert gate_passed(_res(GateStatus.SKIP), accept_skip=True) is True
    assert gate_passed(_res(GateStatus.PASS), accept_skip=True) is True
    assert gate_passed(_res(GateStatus.FAIL), accept_skip=True) is False


# NOTE (plan r4-M2 / audit-T1 M2): test_semantics_table_covers_all_sites is
# deliberately near-tautological — it pins the TABLE SHAPE (11 rows = 9
# single-compare sites) and serves as Task 2's rewiring map; the real
# behavior pinning lives in the two behavioral tests above.
def test_semantics_table_covers_all_sites():
    assert len(SITES) == 11
    for site, res, expected in SITES:
        assert isinstance(expected, bool) and site
