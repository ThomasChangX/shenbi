"""Test linguistic drift detection via check_linguistic_drift."""

from shenbi.skill_utils.drift_detection.linguistic_drift import check_linguistic_drift


def test_no_chapter_returns_empty(tmp_path):
    """When chapter file doesn't exist, return empty list."""
    issues = check_linguistic_drift(tmp_path, 1)
    assert issues == []


def test_system_term_density_warns(tmp_path):
    """High system term density should produce a warning."""
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir(parents=True)
    chapter_path = chapters_dir / "chapter-1.md"

    # Write text with very high system term density
    chapter_path.write_text(
        "系统 面板 等级 技能 属性 经验 " * 20 + "一些正常文本。" * 3,
        encoding="utf-8",
    )

    issues = check_linguistic_drift(tmp_path, 1)
    # Should have at least a system term density warning
    assert any("System term density" in i for i in issues)


def test_em_dash_density_warns(tmp_path):
    """High em-dash density should produce a warning."""
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir(parents=True)
    chapter_path = chapters_dir / "chapter-1.md"

    # Write text with very high em-dash density
    chapter_path.write_text(
        "——".join(["text"] * 30),
        encoding="utf-8",
    )

    issues = check_linguistic_drift(tmp_path, 1)
    # Should have at least an em-dash density warning
    assert any("Em-dash density" in i for i in issues)
