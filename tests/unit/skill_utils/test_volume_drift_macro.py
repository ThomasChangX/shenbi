"""Cross-volume drift macro-trigger tests for detect_volume_drift (spec 8.3).

The arc-payoff trend writes one overall row per volume. A consecutive
2-volume decline (last volume overall < previous volume overall) is the
spec 8.3 macro trigger: a non-zero finding set blocks tier advancement /
next-volume release until the decline is addressed. This module pins that
contract against the arc_payoff_trend overall series.
"""

from __future__ import annotations

import pytest

from shenbi.skill_utils.drift_detection.compute_drift import (
    DriftKind,
    detect_volume_drift,
)


@pytest.mark.unit
def test_arc_payoff_declining_sequence_fires_macro_trigger() -> None:
    """82 then 74 then 68: the last two volumes decline (74 to 68), so
    the spec 8.3 macro trigger fires a single VOLUME_DECLINE finding
    that would block the next volume.
    """
    arc_payoff_trend = [82.0, 74.0, 68.0]
    findings = detect_volume_drift(arc_payoff_trend)
    assert len(findings) == 1
    f = findings[0]
    assert f.kind is DriftKind.VOLUME_DECLINE
    assert f.dim == "overall"
    assert "74" in f.detail and "68" in f.detail


@pytest.mark.unit
def test_arc_payoff_stable_sequence_no_fire() -> None:
    """Stable overall across volumes means no macro trigger, next
    volume is not blocked.
    """
    assert detect_volume_drift([82.0, 82.0, 82.0]) == []


@pytest.mark.unit
def test_arc_payoff_ascending_sequence_no_fire() -> None:
    """Improving volumes (68 then 74 then 82) means no trigger."""
    assert detect_volume_drift([68.0, 74.0, 82.0]) == []


@pytest.mark.unit
def test_arc_payoff_two_volume_decline_fires() -> None:
    """Minimum triggering case: exactly 2 volumes, last below previous."""
    findings = detect_volume_drift([82.0, 74.0])
    assert len(findings) == 1
    assert findings[0].kind is DriftKind.VOLUME_DECLINE


@pytest.mark.unit
def test_arc_payoff_single_volume_no_fire() -> None:
    """A lone volume cannot show a 2-volume decline, so no fire."""
    assert detect_volume_drift([82.0]) == []


@pytest.mark.unit
def test_arc_payoff_empty_no_fire() -> None:
    """No volumes means no fire."""
    assert detect_volume_drift([]) == []


@pytest.mark.unit
def test_arc_payoff_plateau_after_decline_no_fire() -> None:
    """82 then 68 then 68: the last pair is flat (68 to 68), not a
    decline, so the macro trigger does NOT fire even though volume 2
    dropped earlier. The helper is a consecutive-pair check, not a
    global trend regression.
    """
    assert detect_volume_drift([82.0, 68.0, 68.0]) == []
