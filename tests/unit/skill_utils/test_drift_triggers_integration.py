"""Integration tests for the full drift-trigger path (spec §8.3, §10 漂移触发).

These exercise the *complete* deterministic path — write a realistic trend
fixture (the markdown ``truth/resonance_trend.md`` / ``arc_payoff_trend.md``
format) → ``parse_trend`` → ``detect_chapter_drift`` / ``detect_volume_drift``
→ findings — and assert that *only* the spec §8.3 positive cases fire and write
to ``audit_drift``, while stable/overridden negative cases do not.

Unlike ``test_drift_detection.py`` (which feeds raw score lists to isolated
functions), these tests read fixtures through the parser the way
``drift-guidance`` / ``chapter-planning`` actually consume them, and they drive
the end-to-end ``main()`` CLI (including ``--write-audit-drift``).
"""

from __future__ import annotations

import pytest

from shenbi.skill_utils.drift_detection import (
    DriftKind,
    detect_chapter_drift,
    detect_volume_drift,
    main,
    parse_trend,
)

# --- trend-fixture helpers (mirror the truth-file markdown contract) ---------

RESONANCE_HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 | "
    "overall | confidence | human_overridden |"
)


def _resonance_row(
    ch: int,
    role: str,
    dim: int,
    overall: int,
    confidence: str = "high",
    overridden: bool = False,
) -> str:
    flag = "true" if overridden else ""
    # keep the non-target dimensions stable so only ``dim`` (情感落地) moves
    return f"| {ch} | {role} | {dim} | 20 | 18 | 15 | {overall} | {confidence} | {flag} |"


def _write_resonance_trend(path, rows: list[str]) -> None:
    path.write_text(
        RESONANCE_HEADER + "\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


ARC_HEADER = (
    "| volume | 弧情感交付 | 伏笔兑现质量 | 线索收束 | 期待债务结算 | 角色弧推进 | overall |"
)


def _write_arc_trend(path, volumes: list[tuple[int, int]]) -> None:
    # volumes: list of (volume_no, overall); other dims held constant
    body = "\n".join(f"| {v} | 20 | 22 | 16 | 12 | 13 | {ov} |" for v, ov in volumes)
    path.write_text(ARC_HEADER + "\n" + body + "\n", encoding="utf-8")


# --- full positive path: monotonic decline (spec §8.3 (a)) -------------------


@pytest.mark.unit
def test_full_path_monotonic_decline_fires(tmp_path) -> None:
    """Declining 情感落地 across a fixture → parse → detect fires MONOTONIC_DECLINE."""
    trend = tmp_path / "resonance_trend.md"
    _write_resonance_trend(
        trend,
        [
            _resonance_row(1, "高潮", 24, 75),
            _resonance_row(2, "过渡", 23, 65, "mid"),
            _resonance_row(3, "高潮", 21, 56),
            _resonance_row(4, "高潮", 18, 48),
        ],
    )
    parsed = parse_trend(trend, dims=["情感落地"])
    raw = [score for score, _ in parsed["情感落地"]]
    findings = detect_chapter_drift(raw, dim="情感落地")

    kinds = {f.kind for f in findings}
    assert DriftKind.MONOTONIC_DECLINE in kinds
    decl = next(f for f in findings if f.kind == DriftKind.MONOTONIC_DECLINE)
    assert decl.dim == "情感落地"
    assert "情感落地" in decl.detail  # detail names the drifted dimension


# --- full positive path: below mean - 2σ (spec §8.3 (b)) --------------------


@pytest.mark.unit
def test_full_path_below_mean_2sigma_fires(tmp_path) -> None:
    """>=6 tight highs then a sustained deep dip → BELOW_MEAN_2SIGMA fires."""
    trend = tmp_path / "resonance_trend.md"
    # 10 stable highs then a sustained deep dip: enough samples (>=6) for the σ
    # rule, and the smoothed tail ([…, 6.7, 0, 0]) sits below mean−2σ for >=2.
    rows = [_resonance_row(i, "高潮", 20, 75) for i in range(1, 11)]
    rows += [_resonance_row(i, "高潮", 0, 30) for i in range(11, 14)]
    _write_resonance_trend(trend, rows)

    parsed = parse_trend(trend, dims=["情感落地"])
    raw = [score for score, _ in parsed["情感落地"]]
    findings = detect_chapter_drift(raw, dim="情感落地")

    assert any(f.kind == DriftKind.BELOW_MEAN_2SIGMA for f in findings)
    sigma = next(f for f in findings if f.kind == DriftKind.BELOW_MEAN_2SIGMA)
    assert "mean-2σ" in sigma.detail


# --- negative path: stable series does not fire (spec §8.3 negative) ---------


@pytest.mark.unit
def test_full_path_stable_series_no_finding(tmp_path) -> None:
    """A flat series across the fixture → no drift findings at all."""
    trend = tmp_path / "resonance_trend.md"
    _write_resonance_trend(
        trend,
        [_resonance_row(i, "高潮", 22, 75) for i in range(1, 9)],
    )
    parsed = parse_trend(trend, dims=["情感落地"])
    raw = [score for score, _ in parsed["情感落地"]]
    assert detect_chapter_drift(raw, dim="情感落地") == []


# --- negative path: human_overridden chapter excluded (spec §8.3 记录语义) ----


@pytest.mark.unit
def test_full_path_overridden_chapter_breaks_decline(tmp_path) -> None:
    """A human_overridden chapter in the decline run is excluded → no trigger."""
    trend = tmp_path / "resonance_trend.md"
    _write_resonance_trend(
        trend,
        [
            _resonance_row(1, "高潮", 24, 75),
            _resonance_row(2, "过渡", 23, 65, "mid", overridden=True),
            _resonance_row(3, "高潮", 21, 56),
            _resonance_row(4, "高潮", 18, 48),
        ],
    )
    parsed = parse_trend(trend, dims=["情感落地"])
    series = parsed["情感落地"]
    raw = [score for score, _ in series]
    excl = {i for i, (_, e) in enumerate(series) if e}
    assert excl == {1}  # the parser surfaced the override flag
    assert detect_chapter_drift(raw, dim="情感落地", exclude_indices=excl) == []


# --- full positive path: volume decline (spec §8.3 macro) -------------------


@pytest.mark.unit
def test_full_path_volume_decline_fires(tmp_path) -> None:
    """arc_payoff overall 82→74 (2-volume decline) → VOLUME_DECLINE fires."""
    arc = tmp_path / "arc_payoff_trend.md"
    _write_arc_trend(arc, [(1, 82), (2, 74)])
    parsed = parse_trend(arc, dims=["overall"])
    volumes = [score for score, _ in parsed["overall"]]

    findings = detect_volume_drift(volumes)
    assert len(findings) == 1
    assert findings[0].kind is DriftKind.VOLUME_DECLINE
    assert "declined" in findings[0].detail


@pytest.mark.unit
def test_full_path_volume_stable_no_finding(tmp_path) -> None:
    """arc_payoff overall rising (74→82) → no volume-drift finding."""
    arc = tmp_path / "arc_payoff_trend.md"
    _write_arc_trend(arc, [(1, 74), (2, 82)])
    parsed = parse_trend(arc, dims=["overall"])
    volumes = [score for score, _ in parsed["overall"]]
    assert detect_volume_drift(volumes) == []


# --- end-to-end CLI: only positive cases write audit_drift (spec §10) --------


@pytest.mark.unit
def test_main_cli_positive_writes_audit_and_exits_nonzero(tmp_path, capsys, monkeypatch) -> None:
    """Declining fixtures → findings printed, exit 1, audit_drift.md written."""
    trend = tmp_path / "resonance_trend.md"
    _write_resonance_trend(
        trend,
        [
            _resonance_row(1, "高潮", 24, 75),
            _resonance_row(2, "过渡", 23, 65, "mid"),
            _resonance_row(3, "高潮", 21, 56),
            _resonance_row(4, "高潮", 18, 48),
        ],
    )
    arc = tmp_path / "arc_payoff_trend.md"
    _write_arc_trend(arc, [(1, 83), (2, 74)])  # volume decline too

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

    audit = (tmp_path / "truth" / "audit_drift.md").read_text(encoding="utf-8")
    assert "drift findings" in audit
    assert "monotonic_decline" in audit
    assert "volume_decline" in audit


@pytest.mark.unit
def test_main_cli_negative_exits_zero_and_writes_nothing(tmp_path, capsys, monkeypatch) -> None:
    """Stable fixtures → no findings, exit 0, audit_drift.md never created."""
    trend = tmp_path / "resonance_trend.md"
    _write_resonance_trend(
        trend,
        [_resonance_row(1, "高潮", 22, 75), _resonance_row(2, "高潮", 22, 75)],
    )
    arc = tmp_path / "arc_payoff_trend.md"
    _write_arc_trend(arc, [(1, 83), (2, 83)])

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
    assert exc.value.code == 0
    assert capsys.readouterr().out == ""
    # §10: only positive cases write audit_drift — a clean series must not create it
    assert not (tmp_path / "truth" / "audit_drift.md").exists()
