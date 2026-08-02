"""Tests for parallel_dispatch backoff jitter (spec §5.3)."""

from __future__ import annotations

from shenbi.pipeline.parallel_dispatch import RETRY_BACKOFF_BASE, RETRY_JITTER


def test_jitter_same_magnitude_as_base():
    """Jitter range must be ≥ backoff base to decorrelate workers (spec §5.3/§2.8).

    Old: RETRY_JITTER=1.0, RETRY_BACKOFF_BASE=2.0 → jitter was half the base,
    workers near-lockstep. Fix: jitter ≥ base so workers decorrelate.
    """
    assert RETRY_JITTER >= RETRY_BACKOFF_BASE, (
        f"RETRY_JITTER={RETRY_JITTER} should be ≥ RETRY_BACKOFF_BASE={RETRY_BACKOFF_BASE} "
        f"to decorrelate parallel workers (spec §2.8 thundering herd fix)"
    )
