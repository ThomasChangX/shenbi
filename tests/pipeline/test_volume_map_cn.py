"""R1: 中文卷图卷级作用域解析(spec #6 修复方向 1).

fixture 是生产 volume_map.md 的精确副本(G0.9 真实产物,G0.11 MIRROR_MAP 镜像).
"""

import shutil
from pathlib import Path

from shenbi.pipeline._shared import _read_cn_volume_boundaries, read_volume_boundaries
from shenbi.pipeline.triggers import is_volume_boundary

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "volume-map-xinghuo.md"


def _mk_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "outline").mkdir(parents=True)
    shutil.copy(FIXTURE, proj / "outline" / "volume_map.md")
    return proj


def test_cn_boundaries_exact_set_on_real_fixture():
    """验收(正):真实项目边界集 == {15,35,55,75,100},卷数 == 5."""
    text = FIXTURE.read_text(encoding="utf-8")
    assert _read_cn_volume_boundaries(text) == {15, 35, 55, 75, 100}


def test_cn_boundaries_via_project_layout(tmp_path):
    proj = _mk_project(tmp_path)
    assert read_volume_boundaries(proj) == {15, 35, 55, 75, 100}


def test_kr_subranges_excluded_negative_acceptance(tmp_path):
    """验收(负):KR 级子范围(5/10/56)不得入边界集."""
    proj = _mk_project(tmp_path)
    for ch in (5, 10, 56):
        assert not is_volume_boundary(ch, proj)
    for ch in (15, 35, 55, 75, 100):
        assert is_volume_boundary(ch, proj)


def test_english_formats_regression(tmp_path):
    """回归护栏:既有英文格式解析行为不变(END_RE 全文优先、命中即短路
    RANGE_RE--两格式混排时只取 END 结果,这是现状语义,本 task 不改).
    """
    end_only = tmp_path / "en1"
    (end_only / "outline").mkdir(parents=True)
    (end_only / "outline" / "volume_map.md").write_text(
        "## Volume 1\n\nChapter End: 15\n", encoding="utf-8"
    )
    assert read_volume_boundaries(end_only) == {15}
    range_only = tmp_path / "en2"
    (range_only / "outline").mkdir(parents=True)
    (range_only / "outline" / "volume_map.md").write_text(
        "## Volume 1\n\nChapters 16-35\n", encoding="utf-8"
    )
    assert read_volume_boundaries(range_only) == {35}
