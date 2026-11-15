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
    """Roster coverage pin (plan I-4, audit-T5 C2 rewrite): a genre-circle-only
    gap must also stop the wave — hoisting the genre roster before wave-1 is
    load-bearing. Uses a REAL genre skill (`shenbi-review-era` via
    auditDimensions.era) and asserts escalation explicitly.
    """
    from shenbi.pipeline import chapter_loop as cl

    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-2.md").write_text("x", encoding="utf-8")
    (tmp_path / "genre-config.json").write_text(
        '{"auditDimensions": {"era": true}}', encoding="utf-8"
    )

    from shenbi.pipeline.audit_layer import get_active_genre_audits as real_roster

    assert "shenbi-review-era" in real_roster({"auditDimensions": {"era": True}})

    def _genre_only_gap(project_dir: Path | str, skill: str, chapter: int | None) -> list[str]:
        if skill == "shenbi-review-era":
            return ["era-reference.md"]
        return []  # core inputs all present (stubbed)

    def _must_not_dispatch(*a: object, **kw: object) -> None:
        raise AssertionError("dispatched with a genre-circle read gap")

    monkeypatch.setattr("shenbi.pipeline.audit_layer.missing_audit_reads", _genre_only_gap)
    monkeypatch.setattr(
        "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel", _must_not_dispatch
    )
    monkeypatch.setattr(cl, "dispatch_serial_reviews", _must_not_dispatch)
    state, _ct = _wave_state(tmp_path)
    assert cl._run_audit_wave_step(state, tmp_path, 9, cl.CHAPTER_STEPS[9], 2) is True
    cp = state.pending_checkpoint
    assert cp is not None and cp.type.value == "escalation", cp.type
    assert "shenbi-review-era" in (cp.context or "")


# ── audit-T5 I4: branch coverage for produces / OPTIONAL / chapter=None / bundle ──


_SELF_CONTRACT = {
    "reads": [
        "chapters/chapter-N.md",
        "truth/resonance_trend.md",  # 自身 updates——首次派发前不存在
        "audits/chapter-N-resonance.md",  # 自身 writes
        "benchmarks/anchors/",  # OPTIONAL_READS 覆盖（resonance 同款声明）
        "arc-*.md",  # OPTIONAL glob 面
    ],
    "writes": ["audits/chapter-N-resonance.md"],
    "updates": ["truth/resonance_trend.md"],
}


def test_self_products_and_optional_branches_exempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reads that are the skill's own writes/updates must be exempt.

    Chapter-1 path: resonance's truth/audit_drift.md does not exist before its
    first dispatch; without this branch the whole wave would hard-stop.
    """
    import shenbi.pipeline.dispatch_helper as dh
    from shenbi.contracts import loader

    monkeypatch.setattr(loader, "load_contract", lambda skill: _SELF_CONTRACT)
    monkeypatch.setattr(
        dh, "OPTIONAL_READS", {"shenbi-review-x": ["benchmarks/anchors/", "arc-*.md"]}
    )
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-1.md").write_text("x", encoding="utf-8")
    assert missing_audit_reads(tmp_path, "shenbi-review-x", 1) == []


def test_chapter_none_keeps_literal_placeholder(tmp_path: Path, _stub_contract: None) -> None:
    """chapter=None mirrors the escalation tri-state substitution.

    chapter-N -> N (revision_router.py:276-278) -- the result is
    `chapters/N.md`, not `chapter-N`.
    """
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "current_state.md").write_text("x", encoding="utf-8")
    (tmp_path / "characters").mkdir()
    (tmp_path / "characters" / "a.md").write_text("x", encoding="utf-8")
    assert missing_audit_reads(tmp_path, "shenbi-review-x", None) == ["chapters/N.md"]


def test_bundle_chapters_checked_per_chapter(tmp_path: Path, _stub_contract: None) -> None:
    """Bundle mode checks per wave chapter: follower gaps are reported."""
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-1.md").write_text("x", encoding="utf-8")
    (tmp_path / "truth").mkdir()
    (tmp_path / "truth" / "current_state.md").write_text("x", encoding="utf-8")
    (tmp_path / "characters").mkdir()
    (tmp_path / "characters" / "a.md").write_text("x", encoding="utf-8")
    assert missing_audit_reads(tmp_path, "shenbi-review-x", 1) == []
    assert missing_audit_reads(tmp_path, "shenbi-review-x", 2) == ["chapters/chapter-2.md"]


def test_dispatch_integrity_minor_anchor_with_path_is_green(tmp_path: Path) -> None:
    """audit-T5 I1: a MINOR anchor with path+action must not invalidate (BLOCKING only)."""
    f = tmp_path / "chapter-3-x.md"
    f.write_text(
        "- [MINOR] 与 BLOCKING 条目的边界：请核对 `chapters/chapter-3.md` 后重跑\n",
        encoding="utf-8",
    )
    assert check_audit_dispatch_integrity(f) == []


def test_dispatch_integrity_unanchored_legend_is_green(tmp_path: Path) -> None:
    """audit-T5 I1: an unanchored severity legend must not invalidate."""
    f = tmp_path / "chapter-3-x.md"
    f.write_text(
        "严重度：BLOCKING/CRITICAL/MINOR；请补齐 `chapters/chapter-3.md` 后重跑\n",
        encoding="utf-8",
    )
    assert check_audit_dispatch_integrity(f) == []


def test_dispatch_integrity_compound_blocking_label_red(tmp_path: Path) -> None:
    """Compound label `[BLOCKING-流程]` (5 vol1 live hits) still invalidates."""
    f = tmp_path / "chapter-18-texture.md"
    f.write_text(
        "- [BLOCKING-流程] 正文未提供：请补发 `chapters/chapter-18.md` 后重跑\n",
        encoding="utf-8",
    )
    assert any(i.startswith("G4.av.dispatch_integrity:") for i in issues_of(f))


# ── audit-T5 M4: pwi revalidation routes (regression pins) ───────────────────


def test_pwi_routes_vocab_and_dispatch_integrity(tmp_path: Path) -> None:
    """Three G4.av.* routes hit their own checker; unknown ids pass conservatively (M2)."""
    from shenbi.gates.g4.generic import _revalidate_finding

    (tmp_path / "audits").mkdir()
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-3.md").write_text("# 第三章\n\n正文。\n", encoding="utf-8")

    vocab_file = tmp_path / "audits" / "chapter-3-x.md"
    vocab_file.write_text("严重度: 严重\n", encoding="utf-8")
    di_file = tmp_path / "audits" / "chapter-3-y.md"
    di_file.write_text(
        "- [BLOCKING] 派发完整性：请补齐 `chapters/chapter-3.md` 后重跑\n", encoding="utf-8"
    )

    rel_v = "audits/chapter-3-x.md"
    rel_d = "audits/chapter-3-y.md"
    # 各路由仍能复现各自 issue（file:line 前缀 token 匹配）
    assert _revalidate_finding(tmp_path, rel_v, "G4.av.vocab:chapter-3-x.md — L1:x") is True
    assert (
        _revalidate_finding(tmp_path, rel_d, "G4.av.dispatch_integrity:chapter-3-y.md — L1:x")
        is True
    )
    # 未识别 id：保守放行（plan Task 4 Step 7 / audit-T5 M2）
    assert _revalidate_finding(tmp_path, rel_v, "G4.av.future_rule:chapter-3-x.md — L1:x") is True
    # 已消失的 vocab finding：判 stale（不 pardoning）
    clean = tmp_path / "audits" / "chapter-3-z.md"
    clean.write_text("- [MINOR] 措辞建议\n", encoding="utf-8")
    assert (
        _revalidate_finding(tmp_path, "audits/chapter-3-z.md", "G4.av.vocab:chapter-3-z.md — L1:y")
        is False
    )
