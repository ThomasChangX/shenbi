"""Routing semantics guards (probe21 adjudication #009 附记):

1. ``blocking_found=True`` must disable the NO_REVISION route — the ghost
   chain's audits found blocking findings yet the chapter was routed
   no-revision and marked complete. ``route_chapter_revision``'s *blocking*
   parameter was dead (never read in the body).
2. A resonance report whose verdict is 待人机复核 (resonance_pending — the
   hard gate could not evaluate, e.g. its inputs were absent) must be
   recorded as PENDING, never as passed, and must block the chapter's silent
   completion by raising an ESCALATION for human adjudication.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline import chapter_loop as cl
from shenbi.pipeline.revision_router import route_chapter_revision
from shenbi.pipeline.state import CheckpointType, PipelinePhase, PipelineState
from shenbi.skill_utils.revision_routing.route import RevisionMode

PENDING_REPORT = """# 共鸣评估

```verdict
**章节**: 第 2 章 | **计划角色**: 推进 | **判定**: 待人机复核 (resonance_pending)
```

硬门无法评估：chapter-2.md 与 chapter-2-plan.md 均未传入。
"""


def test_blocking_flag_forces_a_revision_route():
    """blocking=True with unparseable issues still routes revision (SPOT_FIX
    floor); blocking=False keeps the empty→NO_REVISION semantics.
    """
    assert route_chapter_revision([], blocking=False) == RevisionMode.NO_REVISION
    assert route_chapter_revision([], blocking=True) != RevisionMode.NO_REVISION
    assert route_chapter_revision([], blocking=True) == RevisionMode.SPOT_FIX


def test_resonance_pending_report_records_pending_not_passed(tmp_path: Path):
    report = tmp_path / "audits" / "chapter-2-resonance.md"
    report.parent.mkdir(parents=True)
    report.write_text(PENDING_REPORT, encoding="utf-8")

    assert cl._parse_resonance_score(report) is None  # no score to adopt

    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 2
    cl._parse_and_persist_resonance(state, tmp_path, 2, source="serial_step")

    cs = state.chapter_loop.chapter_states["2"]
    assert cs.resonance_score is None
    assert cs.audit_results.get("resonance_pending") is True


def test_resonance_pending_blocks_chapter_completion(tmp_path: Path):
    """The per-chapter checkpoint must not rise silently over an
    unevaluatable hard gate — routing raises ESCALATION for adjudication.
    """
    report = tmp_path / "audits" / "chapter-2-resonance.md"
    report.parent.mkdir(parents=True)
    report.write_text(PENDING_REPORT, encoding="utf-8")

    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 2
    cl._parse_and_persist_resonance(state, tmp_path, 2, source="serial_step")
    assert state.pending_checkpoint.type == CheckpointType.NONE  # parsing alone does not block

    cl._route_revision_after_resonance(state, tmp_path, 2)
    cp = state.pending_checkpoint
    assert cp is not None and cp.type == CheckpointType.ESCALATION, cp
    assert "resonance_pending" in (cp.context or "") or "待人机复核" in (cp.context or "")


def test_resonance_normal_verdict_still_completes(tmp_path: Path):
    """Regression: a normal scored verdict records the score, no pending flag,
    no escalation.
    """
    report = tmp_path / "audits" / "chapter-2-resonance.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        "# 共鸣评估\n\n```verdict\n**章节**: 第 2 章 | **判定**: 通过 (82/100)\n共振: 82/100\n```\n",
        encoding="utf-8",
    )

    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 2
    cl._parse_and_persist_resonance(state, tmp_path, 2, source="serial_step")
    cs = state.chapter_loop.chapter_states["2"]
    assert cs.resonance_score == 82
    assert not cs.audit_results.get("resonance_pending")

    cl._route_revision_after_resonance(state, tmp_path, 2)
    assert state.pending_checkpoint.type == CheckpointType.NONE


def test_wave_audit_entry_marks_resonance_pending_not_passed(tmp_path: Path):
    """The parallel wave's per-audit entry recorded ``passed=True`` for the
    resonance report whose verdict was 待人机复核 (probe21 ghost ch2) — a
    pending hard gate is not a pass.
    """
    report = tmp_path / "audits" / "chapter-2-resonance.md"
    report.parent.mkdir(parents=True)
    report.write_text(PENDING_REPORT, encoding="utf-8")

    entry = cl._wave_audit_entry(True, 0, ["audits/chapter-2-resonance.md"], tmp_path)
    assert entry == {"passed": False, "hard_failures": 0, "resonance_pending": True}


def test_wave_audit_entry_clean_resonance_report_passes(tmp_path: Path):
    report = tmp_path / "audits" / "chapter-2-resonance.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        "# 共鸣评估\n\n```verdict\n**章节**: 第 2 章 | **判定**: 通过 (82/100)\n共振: 82/100\n```\n",
        encoding="utf-8",
    )

    entry = cl._wave_audit_entry(True, 0, ["audits/chapter-2-resonance.md"], tmp_path)
    assert entry == {"passed": True, "hard_failures": 0}


def test_wave_audit_entry_hard_failure_still_fails(tmp_path: Path):
    report = tmp_path / "audits" / "chapter-2-factual.md"
    report.parent.mkdir(parents=True)
    report.write_text("| P1 | x | **BLOCKING** |\n", encoding="utf-8")

    entry = cl._wave_audit_entry(True, 1, ["audits/chapter-2-factual.md"], tmp_path)
    assert entry == {"passed": False, "hard_failures": 1}
