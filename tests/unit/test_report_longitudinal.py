"""Spec #68 T1: report_longitudinal 解析层（novel 目标 / resonance 行 / 分段）。

G0.9: resonance_trend.md 经真实生产写方构造（build_resonance_trend_row +
write_truth_file insert_markdown_row）；契约表头是 SKILL.md:174 定义的
文件格式面，由测试代码写入（先例 tests/unit/skill_utils/test_drift_detection.py）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

TREND_HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报 "
    "| overall | confidence | human_overridden |"
)


def _write_trend(tmp_path: Path, rows: list[tuple[int, int]], header: str = TREND_HEADER) -> Path:
    """经真实写方构造 trend 表；末行补换行（upsert 返回无尾换行的 joined 文本，
    追加行前必须补，否则拼到同一物理行上）。"""
    from shenbi.pipeline.chapter_loop import build_resonance_trend_row
    from shenbi.pipeline.truth_io import write_truth_file

    truth = tmp_path / "truth"
    truth.mkdir(parents=True, exist_ok=True)
    trend = truth / "resonance_trend.md"
    trend.write_text(header + "\n", encoding="utf-8")
    for ch, overall in rows:
        write_truth_file(
            tmp_path,
            "resonance_trend.md",
            build_resonance_trend_row(ch, overall),
            mode="insert_markdown_row",
            key_field="chapter",
        )
    content = trend.read_text(encoding="utf-8")
    if content and not content.endswith("\n"):
        trend.write_text(content + "\n", encoding="utf-8")
    return trend


class TestParseNovelTargets:
    """novel.json 目标键解析：缺键/0/非 dict 全部 exit-2 面。"""

    def test_ok(self):
        from tools.report_longitudinal import parse_novel_targets

        assert parse_novel_targets({"target_word_count": 200000, "total_chapters": 60}) == (
            200000,
            60,
        )

    @pytest.mark.parametrize(
        "bad",
        [
            {},
            {"target_word_count": 200000},
            {"total_chapters": 60},
            {"target_word_count": 0, "total_chapters": 60},
            {"target_word_count": 200000, "total_chapters": 0},
        ],
    )
    def test_missing_or_zero_raises(self, bad):
        from tools.report_longitudinal import LongitudinalDataError, parse_novel_targets

        with pytest.raises(LongitudinalDataError):
            parse_novel_targets(bad)


class TestParseResonanceTrend:
    """trend 行解析：表头名绑定、重复键、非数值行。"""

    def test_rows_keyed_by_chapter(self, tmp_path):
        from tools.report_longitudinal import parse_resonance_trend

        trend = _write_trend(tmp_path, [(1, 92), (2, 88), (3, 95)])
        rows = parse_resonance_trend(trend)
        assert sorted(rows) == [1, 2, 3]
        assert rows[1].overall == 92.0 and rows[1].excluded is False

    def test_missing_file_raises(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, parse_resonance_trend

        with pytest.raises(LongitudinalDataError):
            parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")

    def test_no_header_raises(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, parse_resonance_trend

        trend = _write_trend(tmp_path, [(1, 92)], header="not a table")
        with pytest.raises(LongitudinalDataError):
            parse_resonance_trend(trend)

    def test_zero_rows_raises(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, parse_resonance_trend

        trend = _write_trend(tmp_path, [])
        with pytest.raises(LongitudinalDataError):
            parse_resonance_trend(trend)

    def test_duplicate_key_raises(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, parse_resonance_trend

        trend = _write_trend(tmp_path, [(1, 92)])
        with trend.open("a", encoding="utf-8") as fh:
            fh.write("| 1 | 高潮 | 22 | 20 | 22 | 18 | 84 | high |  |\n")
        with pytest.raises(LongitudinalDataError):
            parse_resonance_trend(trend)

    def test_header_name_binding_survives_column_reorder(self, tmp_path):
        from tools.report_longitudinal import parse_resonance_trend

        header = "| chapter | overall | confidence | human_overridden |"
        trend = tmp_path / "truth" / "resonance_trend.md"
        trend.parent.mkdir(parents=True)
        trend.write_text(header + "\n| 7 | 90 | high | true |\n", encoding="utf-8")
        rows = parse_resonance_trend(trend)
        assert rows[7].overall == 90.0 and rows[7].excluded is True

    def test_nonnumeric_overall_row_excluded(self, tmp_path):
        """pending/- 行不进 dict；既有行仍正常解析（缺章由判层 fail-closed）。"""
        from tools.report_longitudinal import parse_resonance_trend

        trend = _write_trend(tmp_path, [(1, 92), (2, 88)])
        with trend.open("a", encoding="utf-8") as fh:
            fh.write("| 3 | 高潮 | - | - | - | - | pending | high |  |\n")
        rows = parse_resonance_trend(trend)
        assert 3 not in rows and 2 in rows and rows[2].overall == 88.0


class TestSegmentChapters:
    """分段枚举：r=0→(f,f,f)/r=1→(f,f,c)/r=2→(f,c,c)。"""

    @pytest.mark.parametrize(
        "n,expected",
        [
            (3, [1, 1, 1]),
            (4, [1, 1, 2]),
            (5, [1, 2, 2]),
            (6, [2, 2, 2]),
            (7, [2, 2, 3]),
            (8, [2, 3, 3]),
            (60, [20, 20, 20]),
        ],
    )
    def test_enumerated_partition(self, n, expected):
        from tools.report_longitudinal import segment_chapters

        segs = segment_chapters(n)
        lengths = [len(segs["front"]), len(segs["mid"]), len(segs["back"])]
        assert lengths == expected
        assert segs["front"] + segs["mid"] + segs["back"] == list(range(1, n + 1))

    @pytest.mark.parametrize("n", [0, 1, 2])
    def test_insufficient_chapters_raises(self, n):
        from tools.report_longitudinal import LongitudinalDataError, segment_chapters

        with pytest.raises(LongitudinalDataError):
            segment_chapters(n)


def _mk_project(
    tmp_path: Path,
    *,
    chapters: list[int],
    scores: dict[int, int],
    target: int = 200000,
    total: int = 3,
    cjk_per_ch: int = 30000,
    statuses: dict[int, str] | None = None,
    escalations: list[dict[str, Any]] | None = None,
) -> Path:
    """Real-producer construction (G0.9) for a healthy-or-flawed project.

    novel.json written via plain write_text (unit tmp_path face; production
    writer is safe_write at cli.py:482 — identical JSON content contract);
    trend rows and pipeline-state via the real producers.
    """
    from shenbi.pipeline.machine import save_state
    from shenbi.pipeline.state import ChapterState, ChapterStatus, PipelineState

    (tmp_path / "truth").mkdir(parents=True, exist_ok=True)
    novel = {"target_word_count": target, "total_chapters": total}
    (tmp_path / "novel.json").write_text(json.dumps(novel), encoding="utf-8")
    _write_trend(tmp_path, sorted((ch, scores[ch]) for ch in chapters))
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    prose = "星" * cjk_per_ch  # CJK U+4E00-9FFF 内
    for ch in chapters:
        (chapters_dir / f"chapter-{ch}.md").write_text(
            f"# 第{ch}章\n\n{prose}\n\n## POST_WRITE_SELF_CHECK\n\n- 检查项\n",
            encoding="utf-8",
        )
    state = PipelineState(project_dir=str(tmp_path))
    for ch in chapters:
        cs = ChapterState()
        cs.status = ChapterStatus((statuses or {}).get(ch, "complete"))
        state.chapter_loop.chapter_states[str(ch)] = cs
    state.checkpoint_history = escalations or []
    save_state(tmp_path, state)
    return tmp_path


class TestChapterVerdicts:
    """三输入面 fail-closed 逐面验证。"""

    def test_healthy_chapters(self, tmp_path):
        from tools.report_longitudinal import (
            chapter_verdicts,
            load_state_dict,
            parse_resonance_trend,
        )

        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 90, 3: 88})
        rows = parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")
        state = load_state_dict(tmp_path)
        verdicts = chapter_verdicts(tmp_path, 3, rows, state)
        assert all(not v.fail_reasons for v in verdicts)
        assert verdicts[0].cjk_chars > 0  # word_count_md 口径（元节不计）

    def test_missing_state_key_fails_closed(self, tmp_path):
        from tools.report_longitudinal import (
            chapter_verdicts,
            load_state_dict,
            parse_resonance_trend,
        )

        _mk_project(tmp_path, chapters=[1, 2, 4], scores={1: 92, 2: 90, 4: 88})
        state = load_state_dict(tmp_path)
        del state["chapter_loop"]["chapter_states"]["2"]
        rows = parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")
        verdicts = chapter_verdicts(tmp_path, 4, rows, state)
        v2 = next(v for v in verdicts if v.chapter == 2)
        assert any("chapter_states" in r for r in v2.fail_reasons)

    def test_missing_resonance_row_fails_closed(self, tmp_path):
        from tools.report_longitudinal import (
            chapter_verdicts,
            load_state_dict,
            parse_resonance_trend,
        )

        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 90, 3: 88})
        rows = parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")
        del rows[3]
        state = load_state_dict(tmp_path)
        verdicts = chapter_verdicts(tmp_path, 3, rows, state)
        v3 = next(v for v in verdicts if v.chapter == 3)
        assert any("resonance" in r for r in v3.fail_reasons)

    def test_missing_chapter_file_fails_closed(self, tmp_path):
        from tools.report_longitudinal import (
            chapter_verdicts,
            load_state_dict,
            parse_resonance_trend,
        )

        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 90, 3: 88})
        (tmp_path / "chapters" / "chapter-2.md").unlink()
        rows = parse_resonance_trend(tmp_path / "truth" / "resonance_trend.md")
        state = load_state_dict(tmp_path)
        verdicts = chapter_verdicts(tmp_path, 3, rows, state)
        v2 = next(v for v in verdicts if v.chapter == 2)
        assert v2.present is False and v2.fail_reasons


class TestEscalationCounts:
    """escalation 按段计数 + chapter=None 排除。"""

    def test_counts_by_segment_and_unattributed(self):
        from tools.report_longitudinal import escalation_counts_by_segment

        segs = {"front": [1, 2], "mid": [3, 4], "back": [5, 6]}
        hist = [
            {"type": "escalation", "chapter": 1, "decision": "approve"},
            {"type": "escalation", "chapter": 5, "decision": "reject"},
            {"type": "escalation", "chapter": None, "decision": "modify"},
            {"type": "checkpoint", "chapter": 3, "decision": "approve"},
        ]
        counts = escalation_counts_by_segment(hist, segs)
        assert counts == {"front": 1, "mid": 0, "back": 1, "unattributed": 1}


class TestDriftGate:
    """drift 复用——按 detect_chapter_drift 真实语义构造数据。

    smooth() 在排除之前跑：被排除章的原始分会污染保留邻居的平滑值，
    排除只重置被排除下标处的 run。排除测试的保留章分数必须非下滑。
    """

    def test_monotonic_decline_fires(self):
        from tools.report_longitudinal import ResonanceRow, drift_gate

        rows = {
            ch: ResonanceRow(overall=s, excluded=False)
            for ch, s in zip(range(1, 7), [95, 94, 93, 80, 78, 70], strict=True)
        }
        assert drift_gate(rows, 6)  # ≥3 章单调下滑 + 累降 ≥3

    def test_excluded_chapters_do_not_poison(self):
        from tools.report_longitudinal import ResonanceRow, drift_gate

        # 保留章（1-3）平稳；被排除章（4-6）下滑不触发
        rows = {
            ch: ResonanceRow(overall=s, excluded=ch >= 4)
            for ch, s in zip(range(1, 7), [95, 95, 95, 80, 78, 70], strict=True)
        }
        assert drift_gate(rows, 6) == []


class TestEvaluate:
    """判定顺序 + 三条件 + 边界语义。"""

    def test_pass(self, tmp_path):
        from tools.report_longitudinal import evaluate

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 92, 2: 91, 3: 90},
            target=84000,
            cjk_per_ch=28000,
        )
        report = evaluate(tmp_path)
        assert report["verdict"] == "pass" and report["exit_code"] == 0

    def test_back_drop_fails_trend(self, tmp_path):
        from tools.report_longitudinal import evaluate

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 95, 2: 80, 3: 79},
            target=84000,
            cjk_per_ch=28000,
        )
        report = evaluate(tmp_path)
        assert report["verdict"] == "fail" and any("降幅" in r for r in report["reasons"])

    def test_back_escalation_cap_fails_trend(self, tmp_path):
        """零基线语义：前段 0 → cap=0，后段任一 escalation 即 fail；
        chapter=None 事件排除出分段计数并披露（checkpoint_history 主源）。"""
        from tools.report_longitudinal import evaluate

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 92, 2: 91, 3: 90},
            target=84000,
            cjk_per_ch=28000,
            escalations=[
                {"type": "escalation", "chapter": 3, "decision": "approve"},
                {"type": "escalation", "chapter": None, "decision": "modify"},
            ],
        )
        report = evaluate(tmp_path)
        assert any("escalation" in r for r in report["reasons"])
        assert any("chapter=None" in d for d in report["disclosures"])
        assert any("canary 退化情形" in d for d in report["disclosures"])  # N=3 < 6 注记

    def test_n_done_below_target_fails(self, tmp_path):
        from tools.report_longitudinal import evaluate

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 92, 2: 91, 3: 90},
            target=84000,
            total=5,
            cjk_per_ch=28000,
        )
        report = evaluate(tmp_path)
        assert report["verdict"] == "fail" and any("N_done" in r for r in report["reasons"])

    def test_n_done_above_target_discloses_not_fails(self, tmp_path):
        from tools.report_longitudinal import evaluate

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 92, 2: 91, 3: 90},
            target=84000,
            total=2,
            cjk_per_ch=28000,
        )
        report = evaluate(tmp_path)
        assert report["verdict"] == "pass"
        assert any(d.startswith("N_done=3 > N_target=2") for d in report["disclosures"])

    def test_insufficient_chapters_data_error(self, tmp_path):
        from tools.report_longitudinal import LongitudinalDataError, evaluate

        _mk_project(tmp_path, chapters=[1], scores={1: 92})
        with pytest.raises(LongitudinalDataError):
            evaluate(tmp_path)

    def test_data_error_precedes_fail(self, tmp_path):
        """判定顺序：novel.json 坏（exit 2 面）优先于任何 fail 语义。"""
        from tools.report_longitudinal import LongitudinalDataError, evaluate

        _mk_project(tmp_path, chapters=[1, 2, 3], scores={1: 92, 2: 91, 3: 90})
        (tmp_path / "novel.json").write_text("{ broken", encoding="utf-8")
        with pytest.raises(LongitudinalDataError):
            evaluate(tmp_path)

    def test_retry_threshold_v1(self, tmp_path):
        """audit_retry_count != 0 → 逐章 fail（v1 从严）。"""
        from tools.report_longitudinal import evaluate

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 92, 2: 91, 3: 90},
            target=84000,
            cjk_per_ch=28000,
        )
        st = json.loads((tmp_path / "pipeline-state.json").read_text(encoding="utf-8"))
        st["chapter_loop"]["chapter_states"]["2"]["audit_retry_count"] = 1
        (tmp_path / "pipeline-state.json").write_text(json.dumps(st), encoding="utf-8")
        report = evaluate(tmp_path)
        assert report["verdict"] == "fail" and any("audit_retry" in r for r in report["reasons"])

    def test_pending_checkpoint_disclosed_not_counted(self, tmp_path):
        """spec ⑲：pending 非 NONE → 披露不入判据。"""
        from tools.report_longitudinal import evaluate

        _mk_project(
            tmp_path,
            chapters=[1, 2, 3],
            scores={1: 92, 2: 91, 3: 90},
            target=84000,
            cjk_per_ch=28000,
        )
        st = json.loads((tmp_path / "pipeline-state.json").read_text(encoding="utf-8"))
        st["pending_checkpoint"] = {"type": "escalation", "chapter": 2}
        (tmp_path / "pipeline-state.json").write_text(json.dumps(st), encoding="utf-8")
        report = evaluate(tmp_path)
        assert any("pending_checkpoint" in d for d in report["disclosures"])
        assert report["verdict"] == "pass"  # 披露不进判据
