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


def test_parse_trend_three_consumer_header_contract(tmp_path):
    """F524 (spec #27 T5): both consumers (resonance_trend, arc_payoff) parse
    the same writer header shape — column-mapped, not positional.
    """
    from shenbi.skill_utils.drift_detection.compute_drift import (
        ARC_PAYOFF_DIMS,
        RESONANCE_DIMS,
    )

    header = "| 章 | " + " | ".join(sorted(set(RESONANCE_DIMS) | set(ARC_PAYOFF_DIMS))) + " |"
    sep = "|" + "---|" * (len(header.split("|")) - 2)
    row = "| 3 | " + " | ".join(["85"] * (len(header.split("|")) - 3)) + " |"
    trend = tmp_path / "trend.md"
    trend.write_text(f"# trend\n\n{header}\n{sep}\n{row}\n", encoding="utf-8")
    parsed_r = parse_trend(str(trend), dims=RESONANCE_DIMS)
    parsed_a = parse_trend(str(trend), dims=ARC_PAYOFF_DIMS)
    assert all(v == [(85.0, False)] for v in parsed_r.values()), parsed_r
    assert all(v == [(85.0, False)] for v in parsed_a.values()), parsed_a


# --- spec #32 T5 (AC5): linguistic-drift end-to-end regression ---------------
#
# Control-flow inputs constructed in-test (metric ratios), not generative
# fixture surfaces (G0.9 fixture rule does not apply): clean baseline chapters
# → establish_baseline → drifted chapter → _check_linguistic_drift fires and
# the escalation/directive record lands on disk.

_CLEAN_PARA = (
    "他沿着旧城的石板路慢慢走远，风把檐角的灰尘吹落下来。"
    "“你到底去不去？”她在巷口问。他点头，把外衣裹紧了一些。"
    "河水在桥下流过，声音很轻，像有人在远处翻动书页。"
)
# exactly one em-dash per clean chapter so the baseline em_dash_density > 0
_CLEAN_CHAPTER = (_CLEAN_PARA * 4) + "\n" + "他停住脚步——前方有人。" + "\n" + (_CLEAN_PARA * 4)

# A second, entirely distinct clean chapter (different sentences, same style
# profile: one em-dash, some dialogue) — used when the opening-similarity
# check must stay quiet (chapter-4 must not share its opening with chapter-3).
_CLEAN_PARA_ALT = (
    "码头的雾散得很慢，船工们蹲在缆绳边抽烟说笑。"
    "“今晚涨潮吗？”少年问。老人没有回答，只把灯举高了一些。"
    "远处的灯塔亮起来，光在水面碎成许多小块，又慢慢合拢。"
)
_CLEAN_CHAPTER_ALT = (
    (_CLEAN_PARA_ALT * 4) + "\n" + "雾更浓了——他看不见对岸。" + "\n" + (_CLEAN_PARA_ALT * 4)
)


def _write_clean_project(tmp_path, chapters: list[int]):
    from shenbi.skill_utils.drift_detection.baseline import establish_baseline

    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir(parents=True, exist_ok=True)
    for ch in chapters:
        (ch_dir / f"chapter-{ch}.md").write_text(_CLEAN_CHAPTER, encoding="utf-8")
    establish_baseline(tmp_path, chapters)
    return tmp_path


@pytest.mark.unit
def test_linguistic_drift_e2e_warn_writes_directive_to_disk(tmp_path) -> None:
    """Ratio drift (em-dash flood) → WARN → drift-warning directive on disk."""
    from shenbi.pipeline.chapter_loop import _check_linguistic_drift

    project = _write_clean_project(tmp_path, [1, 2, 3])
    drifted = (
        (_CLEAN_PARA * 3) + "\n" + ("他走了——停了——又走了——回头。" * 8) + "\n" + (_CLEAN_PARA * 3)
    )
    (project / "chapters" / "chapter-4.md").write_text(drifted, encoding="utf-8")

    result = _check_linguistic_drift(project, 4)
    assert result is not None
    assert result.is_drift is True
    assert result.severity == "WARN"  # ratio drift, absolute stm density still low

    # escalation record lands on disk for the NEXT chapter
    warning = project / "context" / "drift-warning-5.md"
    assert warning.exists()
    assert "STYLE WARNING" in warning.read_text(encoding="utf-8")


@pytest.mark.unit
def test_linguistic_drift_e2e_escalate_pauses_pipeline(tmp_path) -> None:
    """System-term flood (>100‰) → ESCALATE → DriftEscalationError propagates
    out of the pipeline step (pause for human review).
    """
    from shenbi.pipeline.chapter_loop import DriftEscalationError, _run_linguistic_drift_check

    project = _write_clean_project(tmp_path, [1, 2, 3])
    # ~4 system-term hits per 11 chars → ~360‰ > escalate threshold (100‰)
    polluted = "参数系统在场度冷知道。" * 40
    (project / "chapters" / "chapter-4.md").write_text(polluted, encoding="utf-8")

    with pytest.raises(DriftEscalationError, match="system term density"):
        _run_linguistic_drift_check(project, 4)


@pytest.mark.unit
def test_linguistic_drift_e2e_clean_chapter_no_intervention(tmp_path) -> None:
    """A clean chapter-4 matching the baseline: no drift, nothing written."""
    from shenbi.pipeline.chapter_loop import _check_linguistic_drift

    project = _write_clean_project(tmp_path, [1, 2, 3])
    # distinct prose (same style profile, different sentences) so BOTH the
    # drift check and the opening-similarity check stay quiet
    (project / "chapters" / "chapter-4.md").write_text(_CLEAN_CHAPTER_ALT, encoding="utf-8")

    result = _check_linguistic_drift(project, 4)
    assert result is not None
    assert result.severity == "NONE"
    assert result.is_drift is False
    assert not (project / "context").exists() or not any((project / "context").iterdir())
