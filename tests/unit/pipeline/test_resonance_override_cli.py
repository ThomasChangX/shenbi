"""spec #106 T3c: pipeline override-resonance (cell-patch semantics)."""

from pathlib import Path

import pytest

from shenbi.pipeline.resonance_policy import apply_resonance_override

HEADER = (
    "| chapter | chapter_role | 情感落地 | 场景临场感 | 文笔质感 | 读者回报"
    " | overall | confidence | human_overridden |"
)
SEP = (
    "|---------|--------------|---------|-----------|---------|---------"
    "|---------|-----------|------------------|"
)


def _seed(tmp_path: Path, rows: list[str]) -> Path:
    truth = tmp_path / "truth"
    truth.mkdir(parents=True, exist_ok=True)
    trend = truth / "resonance_trend.md"
    trend.write_text("\n".join([HEADER, SEP, *rows]) + "\n", encoding="utf-8")
    return trend


def test_override_rich_row_flips_flag_only(tmp_path):
    _seed(tmp_path, ["| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high |  |"])
    apply_resonance_override(tmp_path, 3, 76)
    text = (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
    assert "| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high | true |" in text


def test_override_rich_row_score_mismatch_refuses(tmp_path):
    _seed(tmp_path, ["| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high |  |"])
    with pytest.raises(ValueError, match="76"):
        apply_resonance_override(tmp_path, 3, 99)
    assert "true" not in (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")


def test_override_pending_row_writes_full_row(tmp_path):
    _seed(tmp_path, ["| 26 | 未声明 | - | - | - | - | pending | low |  |"])
    apply_resonance_override(tmp_path, 26, 70, dims={"情感落地": 18})
    text = (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
    assert "| 26 | 未声明 | 18 | - | - | - | 70 | human | true |" in text


def test_override_row_visible_to_compute_drift_exclusion(tmp_path):
    _seed(tmp_path, ["| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high |  |"])
    apply_resonance_override(tmp_path, 3, 76)
    from shenbi.skill_utils.drift_detection.compute_drift import parse_trend

    pairs = parse_trend(tmp_path / "truth" / "resonance_trend.md", ["overall"])
    assert (76.0, True) in pairs["overall"]


def test_override_idempotent_second_call(tmp_path):
    _seed(tmp_path, ["| 3 | 推进 | 21 | 19 | 20 | 16 | 76 | high |  |"])
    apply_resonance_override(tmp_path, 3, 76)
    first = (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
    apply_resonance_override(tmp_path, 3, 76)  # 二次 override 幂等
    assert (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8") == first
