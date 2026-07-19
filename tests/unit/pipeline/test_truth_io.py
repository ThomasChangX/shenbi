"""Tests for truth_io.py — key-based upsert truth file writer (dual format)."""

from __future__ import annotations

import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from shenbi.pipeline.truth_io import _path_lock, write_truth_file


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
