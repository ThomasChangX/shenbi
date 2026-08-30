"""Unit tests for skill_utils/drift_detection/compute_drift.py (spec §8.3, §10)."""

from __future__ import annotations

import textwrap

import pytest

from shenbi.skill_utils.drift_detection.compute_drift import (
    DriftFinding,
    detect_chapter_drift,
    detect_volume_drift,
    main,
    parse_trend,
    smooth,
)


@pytest.mark.unit
def test_smooth_3_point_window() -> None:
    assert smooth([10.0, 10.0, 7.0, 7.0, 7.0]) == [10.0, 9.0, 8.0, 7.0, 7.0]


@pytest.mark.unit
def test_smooth_boundary_2_point() -> None:
    # first/last use 2-point (self + sole neighbor)
    assert smooth([10.0, 12.0]) == [11.0, 11.0]


@pytest.mark.unit
def test_smooth_empty() -> None:
    assert smooth([]) == []


@pytest.mark.unit
def test_smooth_single_element() -> None:
    assert smooth([5.0]) == [5.0]


@pytest.mark.unit
def test_chapter_drift_monotonic_decline_triggers() -> None:
    scores = [24.0, 23.0, 21.0, 18.0]  # smoothed: ~24, 22.67, 20.67, 18.0 — monotonic decline >=3
    f = detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6)
    assert any(f.kind == "monotonic_decline" for f in f)


@pytest.mark.unit
def test_chapter_drift_sigma_requires_min_samples() -> None:
    scores = [24.0, 10.0]  # only 2 samples — sigma trigger must NOT fire
    f = detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6)
    assert all(f.kind != "below_mean_2sigma" for f in f)


@pytest.mark.unit
def test_chapter_drift_stable_series_no_trigger() -> None:
    scores = [22.0] * 8
    assert detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6) == []


@pytest.mark.unit
def test_volume_drift_two_volume_decline_triggers() -> None:
    assert len(detect_volume_drift([82.0, 74.0])) == 1  # consecutive 2-volume decline
    assert detect_volume_drift([74.0, 82.0]) == []


@pytest.mark.unit
def test_chapter_drift_human_overridden_excluded() -> None:
    # spec §8.3: human_overridden chapters excluded from trigger stats.
    # Chapter index 2 overridden -> must break the decline run (no false trigger),
    # even though the raw series would otherwise fire monotonic_decline.
    scores = [24.0, 23.0, 21.0, 18.0]
    assert (
        detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6, exclude_indices={2}) == []
    )
    # and without exclusion it DOES fire (sanity):
    assert detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6) != []


# --- parser tests (trend file format contract) ---


@pytest.mark.unit
def test_parse_resonance_trend_excludes_overridden(tmp_path) -> None:
    """human_overridden=true rows are flagged excluded from trigger stats."""
    trend = tmp_path / "resonance_trend.md"
    trend.write_text(
        textwrap.dedent(
            """\
            | chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |
            | 1 | 高潮 | 22 | 20 | 18 | 15 | 75 | high |  |
            | 2 | 过渡 | 14 | 18 | 20 | 13 | 65 | mid |  |
            | 3 | 高潮 | 12 | 16 | 18 | 10 | 56 | high | true |
            """
        ),
        encoding="utf-8",
    )
    parsed = parse_trend(trend, dims=["情感落地"])
    assert parsed["情感落地"][0] == (22.0, False)
    assert parsed["情感落地"][1] == (14.0, False)
    assert parsed["情感落地"][2] == (12.0, True)  # excluded=True


@pytest.mark.unit
def test_parse_skips_pending_rows(tmp_path) -> None:
    """Rows with non-numeric scores (e.g. overall=pending) are skipped entirely —
    not coerced, not counted toward sample N.
    """
    trend = tmp_path / "resonance_trend.md"
    trend.write_text(
        textwrap.dedent(
            """\
            | chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |
            | 1 | 高潮 | 22 | 20 | 18 | 15 | 75 | high |  |
            | 2 | 过渡 | 14 | 18 | 20 | 13 | pending | mid |  |
            | 3 | 高潮 | 12 | 16 | 18 | 10 | 56 | high |  |
            """
        ),
        encoding="utf-8",
    )
    parsed = parse_trend(trend, dims=["overall"])
    # the pending row (chapter 2) is skipped -> only 2 samples
    assert parsed["overall"] == [(75.0, False), (56.0, False)]


# --- CLI tests (main entry point + --write-audit-drift) ---


@pytest.mark.unit
def test_main_cli_no_findings_exits_zero(tmp_path, capsys, monkeypatch) -> None:
    """Stable series -> no findings, exit code 0."""
    trend = tmp_path / "resonance_trend.md"
    trend.write_text(
        textwrap.dedent(
            """\
            | chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |
            | 1 | 高潮 | 22 | 20 | 18 | 15 | 75 | high |  |
            | 2 | 高潮 | 22 | 20 | 18 | 15 | 75 | high |  |
            """
        ),
        encoding="utf-8",
    )
    arc = tmp_path / "arc_payoff_trend.md"
    arc.write_text(
        textwrap.dedent(
            """\
            | volume | 弧情感交付 | 伏笔兑现质量 | 线索收束 | 期待债务结算 | 角色弧推进 | overall |
            | 1 | 20 | 22 | 16 | 12 | 13 | 83 |
            | 2 | 20 | 22 | 16 | 12 | 13 | 83 |
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "compute_drift",
            "--resonance",
            str(trend),
            "--arc-payoff",
            str(arc),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert capsys.readouterr().out == ""


@pytest.mark.unit
def test_main_cli_findings_exit_nonzero_and_audit(tmp_path, capsys, monkeypatch) -> None:
    """Declining series -> findings printed, exit code 1, audit file appended."""
    trend = tmp_path / "resonance_trend.md"
    trend.write_text(
        textwrap.dedent(
            """\
            | chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | overall | confidence | human_overridden |
            | 1 | 高潮 | 24 | 20 | 18 | 15 | 75 | high |  |
            | 2 | 过渡 | 23 | 18 | 18 | 13 | 65 | mid |  |
            | 3 | 高潮 | 21 | 16 | 18 | 10 | 56 | high |  |
            | 4 | 高潮 | 18 | 14 | 18 | 8 | 48 | high |  |
            """
        ),
        encoding="utf-8",
    )
    arc = tmp_path / "arc_payoff_trend.md"
    arc.write_text(
        "| volume | 弧情感交付 | 伏笔兑现质量 | 线索收束 | 期待债务结算 | 角色弧推进 | overall |\n"
        "| 1 | 20 | 22 | 16 | 12 | 13 | 83 |\n"
        "| 2 | 20 | 22 | 16 | 12 | 13 | 74 |\n",
        encoding="utf-8",
    )
    audit = tmp_path / "truth" / "audit_drift.md"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "compute_drift",
            "--resonance",
            str(trend),
            "--arc-payoff",
            str(arc),
            "--write-audit-drift",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "monotonic_decline" in out
    assert "volume_decline" in out
    audit_text = audit.read_text(encoding="utf-8")
    assert "drift findings" in audit_text
    assert "monotonic_decline" in audit_text
    assert "volume_decline" in audit_text
    assert DriftFinding is not None  # exercise the import


@pytest.mark.unit
def test_chapter_drift_below_mean_2sigma_triggers() -> None:
    # 10 tight highs (20) + sustained deep dip (0): smoothed tail [0.0, 0.0]
    # falls below mean-2sigma (0.24), >= 2 consecutive -> sigma trigger fires.
    scores = [20.0] * 10 + [0.0, 0.0, 0.0]
    f = detect_chapter_drift(scores, dim="情感落地", min_samples_sigma=6)
    assert any(f.kind == "below_mean_2sigma" for f in f)


class TestSpec16VolumeExclusion:
    def test_volume_drift_ignores_human_overridden(self, tmp_path):
        """F657: excluded (human_overridden) chapters must not feed volume drift."""
        md = (
            "| chapter | overall | human_overridden |\n"
            "|---|---|---|\n"
            "| 1 | 90 | false |\n"
            "| 2 | 60 | true |\n"
            "| 3 | 95 | false |\n"
        )
        trend = tmp_path / "trend.md"
        trend.write_text(md, encoding="utf-8")
        from shenbi.skill_utils.drift_detection.compute_drift import ARC_PAYOFF_DIMS

        parsed = parse_trend(trend, ARC_PAYOFF_DIMS)
        series = parsed.get("overall", [])
        scores = [s for s, overridden in series if not overridden]
        assert scores == [90.0, 95.0]
        assert detect_volume_drift(scores) == []


# --- spec #32 Task 2: F646 non-finite floats / F653 short-chain backtracking ---


class TestSpec32TryFloatNonFinite:
    def test_nan_returns_none(self):
        """F646: float("nan") parses but is not finite — must be rejected."""
        from shenbi.skill_utils.drift_detection.compute_drift import _try_float

        assert _try_float("nan") is None

    def test_inf_returns_none(self):
        from shenbi.skill_utils.drift_detection.compute_drift import _try_float

        assert _try_float("inf") is None
        assert _try_float("Infinity") is None

    def test_negative_inf_returns_none(self):
        from shenbi.skill_utils.drift_detection.compute_drift import _try_float

        assert _try_float("-inf") is None

    def test_finite_values_still_parse(self):
        from shenbi.skill_utils.drift_detection.compute_drift import _try_float

        assert _try_float("7.3") == 7.3
        assert _try_float("90") == 90.0
        assert _try_float("pending") is None


class TestSpec32ShortChain:
    def test_long_sentence_tail_fragment_not_chain(self):
        """F653: unanchored regex backtracks a <=15-char tail out of a long
        sentence — a single long sentence must not count as a short chain.
        """
        from shenbi.skill_utils.drift_detection.linguistic_drift import _short_chain_chars

        long_para = (
            "林风站在废料场边缘久久望着远处燃烧的天际线而手指无意识地"
            "摩挲着口袋里的金属碎片不知过了多久。"
        )
        assert _short_chain_chars(long_para) == 0

    def test_mid_paragraph_real_short_chain_detected(self):
        """A genuine run of 3 consecutive short (<=15 char) sentences embedded
        after a long sentence must still be detected.
        """
        from shenbi.skill_utils.drift_detection.linguistic_drift import _short_chain_chars

        text = (
            "林风站在废料场边缘久久望着远处燃烧的天际线而手指无意识地摩挲着口袋里的金属碎片。"
            "风起了。他回头。没有人。"
        )
        counted = _short_chain_chars(text)
        # exactly the three short sentences (with terminators) — the long
        # sentence's <=15-char tail must NOT be absorbed into the chain
        # (current regex matches 28 chars here via backtracking)
        assert counted == len("风起了。他回头。没有人。")

    def test_two_short_sentences_not_chain(self):
        from shenbi.skill_utils.drift_detection.linguistic_drift import _short_chain_chars

        assert _short_chain_chars("风起了。他回头。") == 0

    def test_long_tails_plus_two_shorts_not_chain(self):
        """F653: two long sentences each contribute a <=15-char tail to the
        regex, so even a mere 2-sentence short run must not count as a chain.
        """
        from shenbi.skill_utils.drift_detection.linguistic_drift import _short_chain_chars

        text = (
            "林风站在废料场边缘久久望着远处燃烧的天际线而手指无意识地摩挲着口袋里的金属碎片。"
            "陈维民的声音从身后传来带着一丝不易察觉的颤抖似乎想说什么却又停住了。"
            "风起了。他回头。"
        )
        assert _short_chain_chars(text) == 0
