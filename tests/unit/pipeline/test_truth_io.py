"""Tests for truth_io.py — key-based upsert truth file writer (dual format)."""

import tempfile
from pathlib import Path

from shenbi.pipeline.truth_io import write_truth_file


def test_replace_mode_overwrites_existing():
    """Replace mode completely overwrites the file with new content."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "current_state.md"
        target.write_text("## Chapter 1 state\nold data")

        write_truth_file(
            project_dir, "current_state.md", "## Chapter 2 state\nnew data", mode="replace"
        )

        result = target.read_text()
        assert "Chapter 2 state" in result
        assert "old data" not in result


def test_upsert_markdown_row_appends_new_key_and_preserves_existing():
    """markdown-row upsert keeps existing rows and adds the new key's row."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "resonance_trend.md"
        existing = "| Ch1 | - | - | - | - | 60 | high |\n"
        target.write_text(existing)

        new = "| Ch2 | - | - | - | - | 58 | medium |"
        write_truth_file(
            project_dir, "resonance_trend.md", new, mode="upsert_markdown_row", key_field="chapter"
        )

        result = target.read_text()
        assert "Ch1" in result
        assert "Ch2" in result
        assert result.index("Ch1") < result.index("Ch2")


def test_upsert_markdown_row_dedups_on_key_not_substring():
    """Re-writing the same key replaces the old row (key-based, not substring)."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "resonance_trend.md"
        target.write_text("| Ch1 | - | - | - | - | 60 | high |")

        # New row for SAME key (Ch1) with DIFFERENT prose — substring would fail,
        # key-based upsert must replace the row in place.
        write_truth_file(
            project_dir,
            "resonance_trend.md",
            "| Ch1 | - | - | - | - | 62 | high |",
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        result = target.read_text()
        # Exactly one Ch1 row, with the new value (62), not duplicated
        assert result.count("| Ch1") == 1
        assert "62" in result
        assert "60" not in result


def test_upsert_markdown_row_creates_file_if_missing():
    """markdown-row upsert creates the file when it does not exist yet."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir(parents=True)

        write_truth_file(
            project_dir,
            "resonance_trend.md",
            "| Ch1 | - | - | - | - | 60 | high |",
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        target = truth_dir / "resonance_trend.md"
        assert target.exists()
        assert "Ch1" in target.read_text()


def test_upsert_markdown_row_preserves_headers_and_prose():
    """Non-table content (frontmatter, headers, prose) is preserved."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "audit_drift.md"
        target.write_text(
            "---\nupdate_mode: upsert_markdown_row\n---\n\n# Audit Drift\n\n## Notes\nSome prose.\n"
        )

        write_truth_file(
            project_dir,
            "audit_drift.md",
            "| Ch1 | finding |",
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        result = target.read_text()
        assert "# Audit Drift" in result
        assert "Some prose." in result
        assert "| Ch1 | finding |" in result


def test_upsert_yaml_dedups_records_by_key_field():
    """Yaml upsert dedups structured records by key_field (hook id)."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "pending_hooks.md"
        # Existing YAML-fronted file with one hook record
        target.write_text("---\nhooks:\n  - id: MH-001\n    state: PLANTED\n---\n\nbody\n")

        new_records = [{"id": "MH-001", "state": "TRIGGERED"}, {"id": "MH-002", "state": "PLANTED"}]
        write_truth_file(
            project_dir, "pending_hooks.md", new_records, mode="upsert_yaml", key_field="id"
        )

        result = target.read_text()
        # MH-001 replaced (not duplicated), MH-002 added
        assert result.count("MH-001") == 1
        assert result.count("MH-002") == 1
        assert "TRIGGERED" in result


def test_write_preserves_utf8_chinese_characters():
    """replace/upsert preserves Chinese characters correctly."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "current_state.md"
        target.write_text("## 主角状态\n林烽在边城")

        write_truth_file(
            project_dir, "current_state.md", "## 主角状态\n林烽离开边城", mode="replace"
        )

        result = target.read_text()
        assert "林烽离开边城" in result
