"""Spec #91 T2: classify_dispatch_failure relocation (contracts layer)."""

from shenbi.contracts.enums import FailureClass
from shenbi.contracts.failure import classify_dispatch_failure
from shenbi.pipeline.dispatch_helper import classify_dispatch_failure as re_exported


def test_rc2_gate():
    assert (
        classify_dispatch_failure(returncode=2, stderr="write-audit GATE_FAIL x")
        is FailureClass.DETERMINISTIC_GATE
    )


def test_rc2_plain():
    assert classify_dispatch_failure(returncode=2) is FailureClass.DETERMINISTIC_CONTENT


def test_transient_default():
    assert classify_dispatch_failure(returncode=1) is FailureClass.TRANSIENT
    assert classify_dispatch_failure(exc=RuntimeError("x")) is FailureClass.TRANSIENT
    assert classify_dispatch_failure() is FailureClass.TRANSIENT


def test_reexport_identity():
    assert re_exported is classify_dispatch_failure
