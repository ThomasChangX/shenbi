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


# 9 single-compare sites (r3 审查 M2: 1597/4063 pinned in Task 2)
SITES = [
    ("triggers.py:505/_gate_passed", _res("PASS"), True),
    ("triggers.py:505/_gate_passed", _res("SKIP"), True),  # SKIP passes HERE ONLY
    ("triggers.py:505/_gate_passed", _res("FAIL"), False),
    ("closure.py:125/_gate_passed", _res("SKIP"), True),
    ("chapter_loop.py:1446/_gate_passed", _res("SKIP"), False),  # SKIP fails here
    ("audit_layer.py:209/_gate_passed", _res("SKIP"), False),
    ("genesis.py:284/_gate_passed", _res("SKIP"), False),
    ("phase_runner.py:146/'PASS'", _res("SKIP"), False),
    ("phase_runner.py:378/'PASS'", _res("SKIP"), False),
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


def test_semantics_table_covers_all_sites():
    assert len(SITES) == 9
    for site, res, expected in SITES:
        assert isinstance(expected, bool) and site
