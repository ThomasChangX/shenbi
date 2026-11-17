"""spec #72 T9: cluster audit dispatch with per-chapter report artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.audit_layer import audit_report_paths
from shenbi.pipeline.chapter_loop import CHAPTER_STEPS
from shenbi.pipeline.state import PipelineState

CW = json.dumps({"chapter_word": {"default": 3200, "min": 2800, "max": 4000}})


def test_audit_skills_declare_next_chapter_writes() -> None:
    """Audit skills declare {N+1} brace writes (leader single-resolution)."""
    from shenbi.contracts.loader import load_contract
    from shenbi.pipeline.audit_layer import audit_report_paths

    for s in CHAPTER_STEPS:
        if not s.is_audit:
            continue
        writes = load_contract(s.skill).get("writes", [])
        audit_writes = [w for w in writes if "audits/" in str(w)]
        assert any("{N+1}" in str(w) for w in audit_writes), s.skill
    # leader 单解析覆盖 follower：audit_report_paths(N) 含 N+1 路径
    paths = audit_report_paths(2, "shenbi-review-group-character")
    assert "audits/chapter-3-character.md" in paths
    assert "audits/chapter-2-character.md" in paths


def test_no_phantom_paths_beyond_bundle() -> None:
    """Leader resolution yields no paths beyond the bundle (m+1+)."""
    from shenbi.pipeline.audit_layer import audit_report_paths

    paths = audit_report_paths(2, "shenbi-review-group-factual")
    assert not any("chapter-4-" in p for p in paths)  # {N+1} 到 3 为止


@pytest.mark.integration
def test_cluster_savepoint_records_both_chapters(tmp_path: Path) -> None:
    """Cluster savepoint records wave_completed for BOTH bundle chapters
    (a missing N+1 entry is a cascade blind spot).
    """
    import shenbi.pipeline.chapter_loop as cl
    from shenbi.pipeline.dispatch_helper import DispatchResult
    from shenbi.pipeline.parallel_dispatch import ReviewTask

    (tmp_path / "genre-config.json").write_text(CW, encoding="utf-8")
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第1卷 星火（第 1-4 章）\n", encoding="utf-8"
    )
    state = PipelineState.default(str(tmp_path))
    tasks = [
        ReviewTask(
            skill="shenbi-review-group-factual",
            project_dir=tmp_path,
            prompt="cluster",
            output_path="audits/chapter-1-factual.md",
            output_paths=audit_report_paths(1, "shenbi-review-group-factual"),
        )
    ]
    save_state = lambda *a, **kw: None  # noqa: E731
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cl, "save_state", save_state)
        on_complete = cl._wave_savepoint(state, tmp_path, 1, [1, 2])(tasks)
        on_complete(0, DispatchResult(True, 0, "{}", ""))
    for n in (1, 2):
        cs = state.chapter_loop.chapter_states.get(str(n))
        assert cs is not None, n
        done = cs.audit_results.get("wave_completed") or []
        assert "shenbi-review-group-factual" in done, n


def test_audit_skills_declare_next_chapter_reads() -> None:
    """Spec #109 T1: bundle auditors must DECLARE the follower chapter read."""
    from shenbi.contracts.loader import load_contract

    six = [
        "shenbi-review-group-craft",
        "shenbi-review-group-plan",
        "shenbi-review-group-factual",
        "shenbi-review-group-character",
        "shenbi-review-resonance",
        "shenbi-review-sensitivity",
    ]
    for s in six:
        reads = load_contract(s).get("reads", [])
        assert any(str(r).endswith("chapter-{N+1}.md") for r in reads), s
    for s in (
        "shenbi-review-group-craft",
        "shenbi-review-group-plan",
        "shenbi-review-resonance",
    ):
        reads = load_contract(s).get("reads", [])
        assert any(str(r).endswith("chapter-{N+1}-plan.md") for r in reads), s


@pytest.mark.integration
def test_wave_close_routes_follower_blocking(tmp_path: Path, monkeypatch) -> None:
    """Spec #109 T3: a follower-chapter BLOCKING report drives that n's
    blocking_found + revision routing (the serial close loop's wave
    equivalent — unreachable at :4938 under the wave interception).
    """
    import shenbi.pipeline.chapter_loop as cl
    from shenbi.pipeline.state import PipelineState

    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-25.md").write_text("锚", encoding="utf-8")
    (tmp_path / "chapters" / "chapter-26.md").write_text("随", encoding="utf-8")
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第1卷（第 25-26 章）\n", encoding="utf-8"
    )
    audits = tmp_path / "audits"
    audits.mkdir()
    (audits / "chapter-26-texture.md").write_text(
        "# 纹理\n\n**BLOCKING** 未核实：随章正文缺位，无法评估。\n",
        encoding="utf-8",
    )
    routed: list[int] = []
    monkeypatch.setattr(cl, "route_revision_after_resonance", lambda s, p, n: routed.append(n))
    state = PipelineState.default(str(tmp_path))
    cl._wave_close_for_n(
        state,
        tmp_path,
        26,
        results=[],
        skills=["shenbi-review-group-craft"],
        cascade_skipped=[],
    )
    cs26 = state.chapter_loop.chapter_states["26"]
    assert cs26.audit_results["blocking_found"] is True
    assert 26 in routed
    assert (audits / "chapter-26-review-summary.md").exists()


@pytest.mark.integration
def test_wave_close_anchor_equivalence(tmp_path: Path, monkeypatch) -> None:
    """Per-n close keeps the anchor side's behavior (blocking routes anchor
    only when the anchor's own reports carry it).
    """
    import shenbi.pipeline.chapter_loop as cl
    from shenbi.pipeline.state import PipelineState

    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-25.md").write_text("锚", encoding="utf-8")
    (tmp_path / "chapters" / "chapter-26.md").write_text("随", encoding="utf-8")
    (tmp_path / "outline").mkdir()
    (tmp_path / "outline" / "volume_map.md").write_text(
        "## 第1卷（第 25-26 章）\n", encoding="utf-8"
    )
    audits = tmp_path / "audits"
    audits.mkdir()
    (audits / "chapter-25-texture.md").write_text(
        "# 纹理\n\n**BLOCKING** 锚章节奏断裂。\n", encoding="utf-8"
    )
    routed: list[int] = []
    monkeypatch.setattr(cl, "route_revision_after_resonance", lambda s, p, n: routed.append(n))
    state = PipelineState.default(str(tmp_path))
    cl._wave_close_for_n(
        state,
        tmp_path,
        25,
        results=[],
        skills=["shenbi-review-group-craft"],
        cascade_skipped=[],
    )
    cs25 = state.chapter_loop.chapter_states["25"]
    assert cs25.audit_results["blocking_found"] is True
    assert routed == [25]  # n=25 收口只路由 25；26 的报告面不含 BLOCKING 不误路由


@pytest.mark.integration
def test_wave_audit_entry_invalid_from_journal(tmp_path: Path) -> None:
    """Spec #109 T4b: journal FAIL finding on a report file flips valid=False
    while passed stays orthogonal (three-state).
    """
    import shenbi.pipeline.chapter_loop as cl

    (tmp_path / "audits").mkdir()
    rep = tmp_path / "audits" / "chapter-26-texture.md"
    rep.write_text("**判定**: 待补（正文未提供）\n", encoding="utf-8")
    (tmp_path / "audits" / ".integrity-findings-26.jsonl").write_text(
        json.dumps(
            {
                "file": "audits/chapter-26-texture.md",
                "finding": "G4.av.starve_verdict:chapter-26-texture.md — L2:判定行饿死形态「待补」",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    entry = cl._wave_audit_entry(True, 0, ["audits/chapter-26-texture.md"], tmp_path)
    assert entry["passed"] is True and entry["valid"] is False


@pytest.mark.integration
def test_wave_audit_entry_grouped_follower_journal(tmp_path: Path) -> None:
    """C1: grouped outputs span 25/26 — the follower-volume finding must flip
    valid even though the FIRST report path resolves to the 25 journal.
    """
    import shenbi.pipeline.chapter_loop as cl

    (tmp_path / "audits").mkdir()
    paths = ["audits/chapter-25-texture.md", "audits/chapter-26-texture.md"]
    for rel in paths:
        (tmp_path / rel).write_text("**判定**: 通过\n", encoding="utf-8")
    (tmp_path / "audits" / ".integrity-findings-26.jsonl").write_text(
        json.dumps(
            {
                "file": "audits/chapter-26-texture.md",
                "finding": "G4.av.starve_verdict:chapter-26-texture.md — L1:判定行饿死形态「待核」",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    entry = cl._wave_audit_entry(True, 0, paths, tmp_path)
    assert entry["valid"] is False


def test_consolidate_disclosure_when_failed_or_invalid() -> None:
    """Spec #109 T4b: failed>0 or invalid products forbid the clean summary."""
    from shenbi.pipeline.parallel_dispatch import consolidate_review_results

    out = consolidate_review_results([], 26, invalid_reports=["chapter-26-texture.md"])
    assert "No BLOCKING or CRITICAL issues found" not in out
    assert "输入缺口" in out and "chapter-26-texture.md" in out
    ok = consolidate_review_results([], 26)
    assert "No BLOCKING or CRITICAL issues found" in ok
