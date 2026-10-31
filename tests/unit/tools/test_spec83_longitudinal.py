"""spec #83 T8: follower completion + bundle_merged longitudinal face."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.pipeline.chapter_loop import _complete_chapter
from shenbi.pipeline.state import ChapterStatus, PipelineState
from tools.report_longitudinal import chapter_verdicts, emit_ledger_rows, parse_resonance_trend

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "spec83"


def _proj(tmp_path: Path) -> Path:
    d = tmp_path
    (d / "outline").mkdir(parents=True, exist_ok=True)
    (d / "truth").mkdir(exist_ok=True)
    (d / "chapters").mkdir(exist_ok=True)
    # 卷跨度标题形（parse_volume_spans 契约）：## 第N卷（第a-第b章）
    (d / "outline" / "volume_map.md").write_text(
        "## 第一卷（第1-第4章）\n| 第1章 | a |\n| 第2章 | b |\n", encoding="utf-8"
    )
    return d


@pytest.fixture()
def _no_contracts(monkeypatch):  # z11 产品契约/汇总面在最小工程上会 raise——隔离（源模块 patch）
    import shenbi.pipeline.chapter_loop as cl
    import shenbi.pipeline.product_contracts as pc

    monkeypatch.setattr(pc, "check_product_contracts", lambda pd: [])
    monkeypatch.setattr(cl, "_check_world_file_freshness", lambda pd, ch: None)
    monkeypatch.setattr(cl, "_print_timing_summary", lambda st: None)
    import shenbi.cost.report as cr

    monkeypatch.setattr(cr, "write_report", lambda pd: None)


def test_bundle_completion_writes_all_member_status(tmp_path, _no_contracts) -> None:
    # 双章束（volume_map span 覆盖 1-4 → ch1 束={1,2}）：_complete_chapter(1) 两章均 complete
    d = _proj(tmp_path)
    st = PipelineState(project_dir=str(d))
    _complete_chapter(st, 1)
    assert st.chapter_loop.chapter_states["1"].status == ChapterStatus.COMPLETE
    assert (
        st.chapter_loop.chapter_states["2"].status == ChapterStatus.COMPLETE
    )  # follower 修 18/18 假 pending
    assert st.chapter_loop.current_chapter == 3  # 游标跳过 follower（既有）


def test_bundle_merged_face_and_bundle_level_assertion(tmp_path) -> None:
    # follower 行 bundle_merged=True + resonance 借 leader；缺 leader 行=束级 fail-closed 理由
    d = _proj(tmp_path)
    (d / "truth" / "resonance_trend.md").write_text(
        "| chapter | seg | overall | note |\n| 1 | a | 90 | x |\n", encoding="utf-8"
    )
    rows = parse_resonance_trend(d / "truth" / "resonance_trend.md")
    state = {
        "chapter_loop": {
            "chapter_states": {
                str(i): {"status": "complete", "audit_retry_count": 0} for i in (1, 2, 3, 4)
            }
        }
    }
    verdicts = chapter_verdicts(d, 4, rows, state)
    by = {v.chapter: v for v in verdicts}
    assert by[1].bundle_merged is False and by[1].resonance == 90
    assert by[2].bundle_merged is True and by[2].resonance == 90  # 束级值
    assert not any("resonance row 2 missing" in r for r in by[2].fail_reasons)  # 单章断言跳过
    # 缺 leader 行 → 束级 fail-closed（非静默）
    rows_no_leader = {}
    v2 = {v.chapter: v for v in chapter_verdicts(d, 4, rows_no_leader, state)}
    assert any("bundle leader 1 resonance row missing" in r for r in v2[2].fail_reasons)


def test_emit_ledger_rows_shape(tmp_path, capsys) -> None:
    d = _proj(tmp_path)
    lines = emit_ledger_rows(d, 1, 2)
    assert lines[0].startswith("| 章 | 实测字数 |")
    assert any(l.startswith("| 1 |") for l in lines)
    assert any("待补" in l for l in lines)  # 手工列占位
    assert any("只报不写" in l for l in lines)
