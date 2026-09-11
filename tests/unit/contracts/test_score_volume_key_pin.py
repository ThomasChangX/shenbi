"""Spec #58 C20 (F871): the score-volume append key pin (moved from the lint
test module — it is a contract-shape pin, not a lint behavior test).
"""

from pathlib import Path


def test_score_volume_append_key_pinned() -> None:
    skill = Path(__file__).resolve().parents[3] / "skills" / "shenbi-score-volume" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    assert "file: truth/volume_score_trend.md" in text
    seg = text[text.find("file: truth/volume_score_trend.md") :]
    assert "key: volume" in seg[: seg.find("updates:") if "updates:" in seg else len(seg)]
