"""Spec #105 T3: audit-dispatch read-readiness pre-check + dispatch-integrity G4."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.audit_layer import missing_audit_reads
from shenbi.pipeline.llm_output_integrity import (
    check_audit_dispatch_integrity,
    check_audit_severity_vocab,
)

_STUB_CONTRACT = {
    "reads": [
        "chapters/chapter-N.md",
        "truth/current_state.md",
        "characters/*.md",
    ],
    "writes": ["audits/chapter-N-x.md"],
    "updates": [],
}


@pytest.fixture()
def _stub_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from shenbi.contracts import loader

    monkeypatch.setattr(loader, "load_contract", lambda skill: _STUB_CONTRACT)  # type: ignore[arg-type]
    monkeypatch.setattr("shenbi.pipeline.dispatch_helper.OPTIONAL_READS", {})


def test_missing_required_read_reported(tmp_path: Path, _stub_contract: None) -> None:
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "current_state.md").write_text("x", encoding="utf-8")
    (tmp_path / "characters").mkdir()
    (tmp_path / "characters" / "a.md").write_text("x", encoding="utf-8")
    missing = missing_audit_reads(tmp_path, "shenbi-review-x", 9)
    assert missing == ["chapters/chapter-9.md"]


def test_glob_read_expanded_and_self_products_exempt(tmp_path: Path, _stub_contract: None) -> None:
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-9.md").write_text("x", encoding="utf-8")
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "current_state.md").write_text("x", encoding="utf-8")
    (tmp_path / "characters").mkdir()
    (tmp_path / "characters" / "a.md").write_text("x", encoding="utf-8")
    # chapters + truth + characters(glob 命中) 齐；audits 产物（writes）不算缺
    assert missing_audit_reads(tmp_path, "shenbi-review-x", 9) == []


def test_dispatch_integrity_signature_red(tmp_path: Path) -> None:
    f = tmp_path / "chapter-40-reader-pull.md"
    f.write_text(
        "- [BLOCKING] 派发完整性：请补齐 `chapters/chapter-40.md` 与 "
        "`plans/chapter-40-plan.md` 后重跑本维度；本报告不作通过判定。",
        encoding="utf-8",
    )
    issues = check_audit_dispatch_integrity(f)
    assert any(i.startswith("G4.av.dispatch_integrity:") for i in issues)


def test_dispatch_integrity_bare_backtick_path_red(tmp_path: Path) -> None:
    f = tmp_path / "chapter-10-character.md"
    f.write_text(
        "- [BLOCKING] 输入缺失：请补入 `chapters/chapter-10.md` 后重跑本审计",
        encoding="utf-8",
    )
    assert any(i.startswith("G4.av.dispatch_integrity:") for i in issues_of(f))


def issues_of(f: Path) -> list[str]:
    return check_audit_dispatch_integrity(f)


def test_content_finding_without_path_green(tmp_path: Path) -> None:
    f = tmp_path / "chapter-3-craft.md"
    f.write_text("- [BLOCKING] 字数不足，请补齐至 3200 字", encoding="utf-8")
    assert check_audit_dispatch_integrity(f) == []


def test_non_blocking_line_green(tmp_path: Path) -> None:
    f = tmp_path / "chapter-3-craft.md"
    f.write_text("- [MINOR] 派发完整性相关表述（非 BLOCKING 行）", encoding="utf-8")
    assert check_audit_dispatch_integrity(f) == []


def test_vocab_checker_still_green_on_these(tmp_path: Path) -> None:
    # 交差保险：dispatch-integrity 样例不触发 vocab 门（词表内词/无 severity 槽）
    f = tmp_path / "chapter-40-reader-pull.md"
    f.write_text(
        "- [BLOCKING] 派发完整性：请补齐 `chapters/chapter-40.md` 后重跑",
        encoding="utf-8",
    )
    assert check_audit_severity_vocab(f) == []


# ── Wave pre-check: zero-dispatch red tests (spec #105 T3 判据). ──────────────


def _wave_state(tmp_path: Path):
    from shenbi.pipeline.state import CheckpointType, PipelineState

    state = PipelineState.default(str(tmp_path))
    from shenbi.pipeline.chapter_loop import CHAPTER_STEPS

    # public-name only (lint_private_imports): first audit step index
    state.chapter_loop.current_chapter = 2
    state.chapter_loop.step_index = next(i for i, s in enumerate(CHAPTER_STEPS) if s.is_audit)
    return state, CheckpointType


def test_wave_precheck_blocks_dispatch_when_reads_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty project → every audit skill's required reads missing → zero
    dispatch, escalation names the precheck (#51 control-flow precedent).
    """
    from shenbi.pipeline import chapter_loop as cl

    def _must_not_dispatch(*a: object, **kw: object) -> None:
        raise AssertionError("dispatched an audit wave with missing required reads")

    monkeypatch.setattr(
        "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel", _must_not_dispatch
    )
    monkeypatch.setattr(cl, "dispatch_serial_reviews", _must_not_dispatch)
    state, _ct = _wave_state(tmp_path)
    assert cl._run_audit_wave_step(state, tmp_path, 9, cl.CHAPTER_STEPS[9], 2) is True
    cp = state.pending_checkpoint
    assert cp is not None and cp.type.value == "escalation", cp.type
    assert "spec #105 T3" in (cp.context or "")


def test_wave_precheck_covers_genre_circle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Roster coverage pin (plan I-4): a genre-circle-only gap must also stop
    the wave — hoisting the genre roster before wave-1 is load-bearing.
    """
    from shenbi.pipeline import chapter_loop as cl
    from shenbi.pipeline.audit_layer import missing_audit_reads as real_fn

    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-2.md").write_text("x", encoding="utf-8")
    (tmp_path / "genre-config.json").write_text('{"auditDimensions": {}}', encoding="utf-8")

    def _only_genre_gap(project_dir: Path | str, skill: str, chapter: int | None) -> list[str]:
        gaps = real_fn(project_dir, skill, chapter)
        if gaps:
            return []  # pretend core inputs all exist
        # fabricate a genre-skill gap: the genre roster member's reads missing
        return ["truth/current_state.md"] if "genre" in skill.lower() else []

    import shenbi.pipeline.audit_layer as al

    monkeypatch.setattr(al, "missing_audit_reads", _only_genre_gap)
    state, _ct = _wave_state(tmp_path)
    cl._run_audit_wave_step(state, tmp_path, 9, cl.CHAPTER_STEPS[9], 2)
    cp = state.pending_checkpoint
    assert cp is not None, "genre 圈缺口必须停波（名册圈定 I-4）"
