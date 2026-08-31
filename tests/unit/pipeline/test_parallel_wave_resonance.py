"""F304 (spec #32): parallel review wave must parse the resonance score.

The serial step-loop path parses ``resonance_score`` from the
review-resonance report and persists a resonance_trend.md row
(chapter_loop.py serial branch). The parallel audit wave historically
routed revision with ``cs.resonance_score`` never set — None silently
fail-opened the floor check. These tests pin the parallel-wave wiring.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from shenbi.logging import configure_logging
from shenbi.pipeline.chapter_loop import (
    _FIRST_AUDIT_IDX,
    _LAST_AUDIT_IDX,
    CHAPTER_STEPS,
    run_chapter_step,
)
from shenbi.pipeline.dispatch_helper import DispatchResult
from shenbi.pipeline.revision_router import RevisionRoute
from shenbi.pipeline.state import PipelineState

_REPORT_LOW = """---
resonance_score: 42
---

# Chapter 1 resonance review
"""

_REPORT_HIGH = """---
resonance_score: 88
---

# Chapter 1 resonance review
"""


def _make_state(tmp_path: Path) -> PipelineState:
    state = PipelineState.default(str(tmp_path))
    state.chapter_loop.current_chapter = 1
    state.chapter_loop.step_index = _FIRST_AUDIT_IDX
    state.chapter_loop.current_step = CHAPTER_STEPS[_FIRST_AUDIT_IDX].skill
    return state


def _run_wave(tmp_path: Path, monkeypatch, report_text: str | None) -> PipelineState:
    """Run run_chapter_step at the parallel-audit-wave entry point.

    All external boundaries are stubbed; the serial WRITE_SHARED dispatch
    (review-resonance) writes the report artifact with *report_text*
    (None: report file never created).
    """
    state = _make_state(tmp_path)
    audits_dir = tmp_path / "audits"
    audits_dir.mkdir(exist_ok=True)
    report = audits_dir / "chapter-1-resonance.md"

    def _fake_serial(serial_tasks, project_dir):
        if report_text is not None:
            report.write_text(report_text, encoding="utf-8")
        return [DispatchResult(True, 0, "", "") for _ in serial_tasks]

    ok = lambda tasks: [DispatchResult(True, 0, "", "") for _ in tasks]  # noqa: E731

    monkeypatch.setattr(
        "shenbi.pipeline.audit_context_cache.build_shared_audit_context",
        lambda project_dir, chapter: SimpleNamespace(estimated_tokens=1),
    )
    monkeypatch.setattr("shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel", ok)
    monkeypatch.setattr("shenbi.pipeline.chapter_loop._dispatch_serial_reviews", _fake_serial)
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop._g3_parallel_wave",
        lambda skills, project_dir, chapter: [],
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.collect_audit_issues", lambda *a, **k: ([], False)
    )
    monkeypatch.setattr(
        "shenbi.pipeline.chapter_loop.route_chapter_revision",
        lambda *a, **k: RevisionRoute.NO_REVISION,
    )
    run_chapter_step(state, tmp_path)
    return state


class TestParallelWaveResonance:
    def test_low_score_parsed_and_disclosed(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Below-floor score: parsed into cs.resonance_score + below-floor warning."""
        configure_logging()
        state = _run_wave(tmp_path, monkeypatch, _REPORT_LOW)
        cs = state.chapter_loop.chapter_states["1"]
        assert cs.resonance_score == 42
        assert "resonance_below_floor" in capsys.readouterr().err

    def test_high_score_parsed_no_warning(self, tmp_path: Path, monkeypatch, capsys) -> None:
        configure_logging()
        state = _run_wave(tmp_path, monkeypatch, _REPORT_HIGH)
        cs = state.chapter_loop.chapter_states["1"]
        assert cs.resonance_score == 88
        assert "resonance_below_floor" not in capsys.readouterr().err

    def test_resonance_trend_updated(self, tmp_path: Path, monkeypatch) -> None:
        _run_wave(tmp_path, monkeypatch, _REPORT_HIGH)
        trend = tmp_path / "truth" / "resonance_trend.md"
        assert trend.exists()
        content = trend.read_text(encoding="utf-8")
        assert "88" in content

    def test_missing_report_fail_open_with_none_score(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        """Missing report: score stays None, floor check fail-opens (disclosed)."""
        configure_logging()
        state = _run_wave(tmp_path, monkeypatch, report_text=None)
        cs = state.chapter_loop.chapter_states["1"]
        assert cs.resonance_score is None
        assert "resonance_below_floor" not in capsys.readouterr().err
        # No score -> no placeholder trend row.
        assert not (tmp_path / "truth" / "resonance_trend.md").exists()

    def test_wave_advances_past_last_audit(self, tmp_path: Path, monkeypatch) -> None:
        state = _run_wave(tmp_path, monkeypatch, _REPORT_HIGH)
        assert state.chapter_loop.step_index == _LAST_AUDIT_IDX + 1
