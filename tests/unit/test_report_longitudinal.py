"""Spec #68 T1: report_longitudinal 解析层（novel 目标 / resonance 行 / 分段）。

G0.9: resonance_trend.md 经真实生产写方构造（build_resonance_trend_row +
write_truth_file insert_markdown_row）；契约表头是 SKILL.md:174 定义的
文件格式面，由测试代码写入（先例 tests/unit/skill_utils/test_drift_detection.py）。
"""

from __future__ import annotations

from pathlib import Path

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
