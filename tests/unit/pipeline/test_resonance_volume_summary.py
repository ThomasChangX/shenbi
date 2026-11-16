"""spec #106 T3a: volume-boundary resonance shadow sink + trend completeness."""

from pathlib import Path

from shenbi.pipeline.resonance_policy import (
    check_trend_completeness,
    write_volume_resonance_summary,
)
from shenbi.pipeline.state import ChapterState, PipelineState

HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)


def _seed_trend(tmp_path: Path, rows: list[str]) -> None:
    truth = tmp_path / "truth"
    truth.mkdir(parents=True, exist_ok=True)
    (truth / "resonance_trend.md").write_text(
        "\n".join([HEADER, SEP, *rows]) + "\n", encoding="utf-8"
    )


def test_completeness_reports_pending_and_missing(tmp_path):
    # ch1/5 已评分、ch8 pending → missing ⊇ {2,3,4,6,7}，pending == [8]
    _seed_trend(
        tmp_path,
        [
            "| 1 | 推进 | 21 | 20 | 21 | 15 | 78 | mid |  |",
            "| 5 | 推进 | 21 | 20 | 21 | 15 | 79 | mid |  |",
            "| 8 | 未声明 | - | - | - | - | pending | low |  |",
        ],
    )
    result = check_trend_completeness(tmp_path)
    assert result["pending"] == [8]
    assert set(result["missing"]) >= {2, 3, 4, 6, 7}


def test_volume_summary_written_with_context_note(tmp_path):
    _seed_trend(
        tmp_path,
        [
            f"| {c} | 推进 | 21 | 20 | 21 | 15 | {s} | mid |  |"
            for c, s in [(1, 78), (2, 74), (3, 76)]
        ],
    )
    state = PipelineState()
    for ch, would in [(1, True), (2, True), (3, False)]:
        cs = ChapterState()
        cs.audit_results["resonance_would_route"] = {
            "floor": 78.0,
            "score": 74,
            "reason": "resonance" if would else None,
            "would_route": would,
            "source": "p25",
            "window_rows": 10,
        }
        state.chapter_loop.chapter_states[str(ch)] = cs
    write_volume_resonance_summary(tmp_path, state, 3)
    sink = tmp_path / "truth" / "resonance_shadow.md"
    assert sink.exists()
    text = sink.read_text(encoding="utf-8")
    assert "would_route" in text and "2/3" in text  # 计数行
    assert "pending" in text and "missing" in text  # completeness 聚合行
    assert "双章束" in text  # 束 follower 语境注记
    # 幂等：同卷重写不重复（同状态同输出——frontmatter 无逐次时间戳）
    write_volume_resonance_summary(tmp_path, state, 3)
    assert sink.read_text(encoding="utf-8") == text


def test_summary_never_touches_route(tmp_path):
    _seed_trend(tmp_path, [])
    state = PipelineState()
    cs = ChapterState()
    cs.audit_results["revision_route"] = "no-revision"
    state.chapter_loop.chapter_states["1"] = cs
    write_volume_resonance_summary(tmp_path, state, 1)
    assert cs.audit_results["revision_route"] == "no-revision"
