"""Tests for truth_io.py — key-based upsert truth file writer (dual format)."""

from __future__ import annotations

import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from shenbi.pipeline.truth_io import (
    _path_lock,
    _read_truth_rows,
    _read_yaml_records,
    _upsert_by_key,
    _upsert_markdown_table_row,
    write_truth_file,
)


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


def test_init_templates_include_update_mode_frontmatter():
    """Truth file templates include update_mode in YAML frontmatter."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        from shenbi.pipeline.dispatch_helper import _init_truth_templates

        _init_truth_templates(project_dir)

        # Cumulative markdown-table files must have update_mode: upsert_markdown_row
        arcs = (project_dir / "truth" / "emotional_arcs.md").read_text()
        assert "update_mode: upsert_markdown_row" in arcs, (
            "emotional_arcs should be upsert_markdown_row-mode"
        )

        # Snapshot files must have update_mode: replace
        current = (project_dir / "truth" / "current_state.md").read_text()
        assert "update_mode: replace" in current, "current_state should be replace-mode"


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


# ---------------------------------------------------------------------------
# Error handling / validation tests
# ---------------------------------------------------------------------------


class TestWriteTruthFileValidation:
    def test_unknown_mode_raises_valueerror(self, tmp_path: Path):
        """Unrecognized mode must raise ValueError immediately."""
        with pytest.raises(ValueError, match="Unknown mode"):
            write_truth_file(tmp_path, "test.md", "data", mode="invalid_mode")

    def test_upsert_yaml_missing_key_field_raises(self, tmp_path: Path):
        """upsert_yaml without key_field must raise ValueError."""
        with pytest.raises(ValueError, match="key_field"):
            write_truth_file(
                tmp_path, "test.md", [{"a": 1}], mode="upsert_yaml"
            )

    def test_upsert_yaml_non_list_raises(self, tmp_path: Path):
        """upsert_yaml with non-list new_data must raise ValueError."""
        with pytest.raises(ValueError, match="list"):
            write_truth_file(
                tmp_path, "test.md", "not a list", mode="upsert_yaml", key_field="id"
            )

    def test_upsert_yaml_with_dict_raises(self, tmp_path: Path):
        """upsert_yaml with dict (not list) new_data must raise ValueError."""
        with pytest.raises(ValueError, match="list"):
            write_truth_file(
                tmp_path, "test.md", {"a": 1}, mode="upsert_yaml", key_field="id"
            )

    def test_upsert_markdown_row_missing_key_field_raises(self, tmp_path: Path):
        """upsert_markdown_row with dict data and no key_field must raise."""
        (tmp_path / "truth").mkdir()
        with pytest.raises(ValueError, match="key_field"):
            write_truth_file(
                tmp_path, "test.md", {"chapter": "1"}, mode="upsert_markdown_row"
            )

    def test_replace_mode_with_dict_produces_bullet_format(self, tmp_path: Path):
        """Replace mode with dict new_data writes bullet-format content."""
        (tmp_path / "truth").mkdir()
        write_truth_file(
            tmp_path, "current_state.md", {"chapter": 1, "resonance": 65}, mode="replace"
        )
        content = (tmp_path / "truth" / "current_state.md").read_text()
        assert "chapter" in content
        assert "resonance" in content

    def test_replace_mode_with_list_data(self, tmp_path: Path):
        """Replace mode with list new_data writes str() representation."""
        (tmp_path / "truth").mkdir()
        write_truth_file(
            tmp_path, "items.md", [{"a": 1}, {"b": 2}], mode="replace"
        )
        content = (tmp_path / "truth" / "items.md").read_text()
        assert "a" in content


# ---------------------------------------------------------------------------
# Low-level helper tests
# ---------------------------------------------------------------------------


class TestReadTruthRows:
    def test_empty_file_returns_empty_list(self, tmp_path: Path):
        f = tmp_path / "empty.md"
        f.write_text("")
        assert _read_truth_rows(f) == []

    def test_nonexistent_file_returns_empty_list(self, tmp_path: Path):
        assert _read_truth_rows(tmp_path / "nonexistent.md") == []

    def test_bullet_rows_parsed_correctly(self, tmp_path: Path):
        f = tmp_path / "bullets.md"
        f.write_text("- ch1: some data\n- ch2: other data\n")
        rows = _read_truth_rows(f)
        assert len(rows) == 2
        assert rows[0] == {"ch1": "some data"}
        assert rows[1] == {"ch2": "other data"}

    def test_table_rows_parsed_correctly(self, tmp_path: Path):
        f = tmp_path / "table.md"
        f.write_text("| Ch1 | 60 | high |\n| Ch2 | 58 | medium |\n")
        rows = _read_truth_rows(f)
        assert len(rows) == 2
        assert rows[0] == {"Ch1": "60 high"}
        assert rows[1] == {"Ch2": "58 medium"}

    def test_header_row_skipped(self, tmp_path: Path):
        """The table header row 'chapter' is skipped."""
        f = tmp_path / "table.md"
        f.write_text("| chapter | score |\n| Ch1 | 60 |\n")
        rows = _read_truth_rows(f)
        # Only the Ch1 data row, not the header
        assert len(rows) == 1
        assert "Ch1" in rows[0]


class TestUpsertMarkdownTableRow:
    def test_non_table_row_appended_as_is(self):
        """A non-table new_row is appended without dedup."""
        existing = "# Header\n\nSome prose.\n"
        new = "Just a plain line"
        result = _upsert_markdown_table_row(existing, new, "chapter")
        assert "Some prose." in result
        assert "Just a plain line" in result

    def test_matching_key_row_is_replaced(self):
        existing = "| Ch1 | old | data |\n| Ch2 | old2 | data2 |\n"
        new = "| Ch2 | new | stuff |"
        result = _upsert_markdown_table_row(existing, new, "chapter")
        assert "| Ch2 | new | stuff |" in result
        assert "| Ch2 | old2 | data2 |" not in result
        assert "| Ch1 | old | data |" in result


class TestReadYamlRecords:
    def test_empty_file_returns_empty_list(self, tmp_path: Path):
        f = tmp_path / "empty.md"
        f.write_text("")
        assert _read_yaml_records(f) == []

    def test_no_frontmatter_returns_empty_list(self, tmp_path: Path):
        f = tmp_path / "nofm.md"
        f.write_text("# Just a header\n\nbody text\n")
        assert _read_yaml_records(f) == []

    def test_reads_records_from_hooks_key(self, tmp_path: Path):
        f = tmp_path / "hooks.md"
        f.write_text("---\nhooks:\n  - id: H1\n    state: active\n---\n\nbody\n")
        records = _read_yaml_records(f)
        assert len(records) == 1
        assert records[0]["id"] == "H1"

    def test_reads_records_from_items_key(self, tmp_path: Path):
        f = tmp_path / "items.md"
        f.write_text("---\nitems:\n  - id: I1\n    name: test\n---\n\nbody\n")
        records = _read_yaml_records(f)
        assert len(records) == 1
        assert records[0]["id"] == "I1"


class TestUpsertByKey:
    def test_new_record_replaces_existing(self):
        existing = [{"id": "a", "val": 1}, {"id": "b", "val": 2}]
        new = [{"id": "a", "val": 99}]
        result = _upsert_by_key(existing, new, "id")
        assert len(result) == 2
        assert {"id": "a", "val": 99} in result
        assert {"id": "b", "val": 2} in result

    def test_record_without_key_preserved(self):
        """Records missing the key_field are preserved at front."""
        existing = [{"id": "a", "val": 1}, {"other": "field"}]
        new = [{"id": "b", "val": 3}]
        result = _upsert_by_key(existing, new, "id")
        assert len(result) == 3
        assert {"other": "field"} in result


# ---------------------------------------------------------------------------
# Task 1 (Plan 08): path-keyed lock registry and concurrent write safety tests
# ---------------------------------------------------------------------------


class TestPathLockRegistry:
    def test_same_path_returns_same_lock(self, tmp_path: Path):
        a = _path_lock(tmp_path / "current_state.md")
        b = _path_lock(tmp_path / "current_state.md")
        assert a is b

    def test_different_paths_return_different_locks(self, tmp_path: Path):
        a = _path_lock(tmp_path / "current_state.md")
        b = _path_lock(tmp_path / "character_matrix.md")
        assert a is not b

    def test_registry_lock_is_not_a_path_lock(self, tmp_path: Path):
        # The registry guard lock must not collide with a path named like it.
        from shenbi.pipeline.truth_io import _REGISTRY_LOCK

        assert _REGISTRY_LOCK is not _path_lock(tmp_path / "_REGISTRY_LOCK")


class TestConcurrentUpsertNoLostRows:
    def test_eight_concurrent_writes_no_lost_rows(self, tmp_path: Path):
        """8 threads each upsert a distinct-key row to the same truth file.

        Without the path-keyed lock this is a classic lost-update race:
        threads read the same prior content and the last writer wins. With
        the lock, all 8 rows survive. Uses a barrier so all threads start
        in the same read-merge-write window to maximize contention.
        """
        filename = "test_concurrent.md"

        def upsert(key: str) -> None:
            write_truth_file(
                tmp_path,
                filename,
                {"chapter": key, "note": f"row-{key}"},
                mode="upsert_markdown_row",
                key_field="chapter",
            )

        barrier = threading.Barrier(8)

        def runner(key: str) -> str:
            barrier.wait()  # release all threads into the race window together
            upsert(key)
            return key

        keys = [f"ch{i}" for i in range(8)]
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(runner, k): k for k in keys}
            for fut in as_completed(futures):
                fut.result()

        # Verify all 8 rows present (no lost updates).
        content = (tmp_path / "truth" / filename).read_text(encoding="utf-8")
        for k in keys:
            assert f"row-{k}" in content, f"row for {k} was lost"
        # Exactly 8 data rows (discount heading/blank lines).
        data_lines = [
            ln
            for ln in content.splitlines()
            if ln.strip().startswith("- ") or ln.strip().startswith("| ")
        ]
        assert len(data_lines) == 8, f"expected 8 rows, got {len(data_lines)}: {data_lines}"

    def test_upsert_dedups_same_key(self, tmp_path: Path):
        """Two concurrent writes with the SAME key produce one row, not two."""
        filename = "dedup.md"
        barrier = threading.Barrier(2)

        def runner():
            barrier.wait()
            write_truth_file(
                tmp_path,
                filename,
                {"chapter": "ch1", "note": "same-key"},
                mode="upsert_markdown_row",
                key_field="chapter",
            )

        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = [ex.submit(runner) for _ in range(2)]
            for f in futs:
                f.result()

        content = (tmp_path / "truth" / filename).read_text(encoding="utf-8")
        assert content.count("same-key") == 1, "duplicate key not deduplicated"
