"""Tests for G4 Enum classification and SoftFailTracker sliding window."""

from __future__ import annotations

from shenbi.pipeline.chapter_loop import (
    G4_CHECK_MAP,
    G4Severity,
    SoftFailTracker,
    _classify_g4_failures,
)


class TestG4SeverityEnum:
    """G4Severity enum should classify checks correctly."""

    def test_transition_is_soft(self):
        assert G4_CHECK_MAP.get("transition") == G4Severity.SOFT

    def test_fatigue_is_soft(self):
        assert G4_CHECK_MAP.get("fatigue") == G4Severity.SOFT

    def test_not_found_is_hard(self):
        assert G4_CHECK_MAP.get("not_found") == G4Severity.HARD

    def test_meta_is_hard(self):
        assert G4_CHECK_MAP.get("meta") == G4Severity.HARD

    def test_golden_is_warn(self):
        assert G4_CHECK_MAP.get("cp.golden") == G4Severity.WARN

    def test_unknown_key_defaults_to_hard(self):
        """Conservative default: unknown check IDs are HARD."""
        assert G4_CHECK_MAP.get("unknown_future_check", G4Severity.HARD) == G4Severity.HARD


class TestG4FailureClassification:
    """_classify_g4_failures partitions must_fix by severity."""

    def test_hard_and_soft_split(self):
        hard, soft, warn = _classify_g4_failures(
            [
                "G4.not_found:path/file.md",
                "G4.transition:path/file.md:8>7",
                "G4.cp.golden:path/file.md",
                "G4.meta:path/file.md:{'让人感悟': 1}",
            ]
        )
        assert len(hard) == 2  # not_found, meta
        assert len(soft) == 1  # transition
        assert len(warn) == 1  # golden

    def test_all_soft_no_retry_needed(self):
        hard, soft, warn = _classify_g4_failures(
            [
                "G4.transition:path/file.md:8>7",
                "G4.fatigue:path/file.md:10>8",
            ]
        )
        assert len(hard) == 0
        assert len(soft) == 2
        assert len(warn) == 0


class TestSoftFailTracker:
    """SoftFailTracker should use sliding window to prevent stale escalations."""

    def test_single_occurrence_no_escalation(self):
        tracker = SoftFailTracker(check_id="transition")
        assert tracker.record(chapter=5) is False

    def test_three_in_window_escalates(self):
        tracker = SoftFailTracker(check_id="transition")
        tracker.record(chapter=1)
        tracker.record(chapter=2)
        result = tracker.record(chapter=3)
        assert result is True  # 3 in 5-chapter window

    def test_window_prunes_stale_entries(self):
        tracker = SoftFailTracker(check_id="transition")
        tracker.record(chapter=1)
        tracker.record(chapter=2)
        result = tracker.record(chapter=50)
        # ch1 and ch2 are outside 5-chapter window from ch50, so only 1 active
        assert result is False
        assert len(tracker.occurrences) == 1  # only ch50 remains

    def test_mixed_window(self):
        tracker = SoftFailTracker(check_id="fatigue")
        tracker.record(chapter=3)
        tracker.record(chapter=5)
        tracker.record(chapter=7)
        result = tracker.record(chapter=8)
        # ch3 pruned (8-3=5 > window_size), ch5,7,8 = 3 active → escalation
        assert result is True
