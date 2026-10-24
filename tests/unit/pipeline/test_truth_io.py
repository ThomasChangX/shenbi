"""Tests for truth_io.py — key-based upsert truth file writer (dual format)."""

from __future__ import annotations

import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from shenbi.pipeline.truth_io import (
    _path_lock,
    _read_yaml_records,
    _upsert_by_key,
    sync_thread_overview_rows,
    upsert_markdown_row,
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
            write_truth_file(tmp_path, "test.md", [{"a": 1}], mode="upsert_yaml")

    def test_upsert_yaml_non_list_raises(self, tmp_path: Path):
        """upsert_yaml with non-list new_data must raise ValueError."""
        with pytest.raises(ValueError, match="list"):
            write_truth_file(tmp_path, "test.md", "not a list", mode="upsert_yaml", key_field="id")

    def test_upsert_yaml_with_dict_raises(self, tmp_path: Path):
        """upsert_yaml with dict (not list) new_data must raise ValueError."""
        with pytest.raises(ValueError, match="list"):
            write_truth_file(tmp_path, "test.md", {"a": 1}, mode="upsert_yaml", key_field="id")

    def test_upsert_markdown_row_missing_key_field_raises(self, tmp_path: Path):
        """upsert_markdown_row with dict data and no key_field must raise."""
        (tmp_path / "truth").mkdir()
        with pytest.raises(ValueError, match="key_field"):
            write_truth_file(tmp_path, "test.md", {"chapter": "1"}, mode="upsert_markdown_row")

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
        write_truth_file(tmp_path, "items.md", [{"a": 1}, {"b": 2}], mode="replace")
        content = (tmp_path / "truth" / "items.md").read_text()
        assert "a" in content


# ---------------------------------------------------------------------------
# Low-level helper tests
# ---------------------------------------------------------------------------


class TestUpsertMarkdownTableRow:
    def test_non_table_row_appended_as_is(self):
        """A non-table new_row is appended without dedup."""
        existing = "# Header\n\nSome prose.\n"
        new = "Just a plain line"
        result = upsert_markdown_row(existing, new, "chapter")
        assert "Some prose." in result
        assert "Just a plain line" in result

    def test_matching_key_row_is_replaced(self):
        existing = "| Ch1 | old | data |\n| Ch2 | old2 | data2 |\n"
        new = "| Ch2 | new | stuff |"
        result = upsert_markdown_row(existing, new, "chapter")
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

    def test_thematic_break_body_is_not_frontmatter(self, tmp_path: Path):
        """A body starting with a ``----`` thematic break (no frontmatter)
        yields ``[]`` — the frontmatter gate is an EXACT first-line ``---``
        match, not a ``startswith("---")`` prefix test (final review T4 M2:
        the prefix test misparsed ``----`` bodies as frontmatter and raised
        TruthFileParseError on files that carry no frontmatter at all).
        """
        f = tmp_path / "thematic.md"
        # Later ``---`` rules in the body make the pre-fix misparse reach the
        # YAML loader; without one it misraised "unterminated" instead.
        f.write_text("----\n\n正文第一段。\n\n---\n\n第二段。\n")
        assert _read_yaml_records(f) == []

    def test_thematic_break_only_body_is_not_frontmatter(self, tmp_path: Path):
        """``----`` with no second ``---`` in the body: also ``[]`` (the
        pre-fix path misraised "frontmatter unterminated" here).
        """
        f = tmp_path / "thematic_only.md"
        f.write_text("----\n\n正文。\n")
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
    def test_same_path_shares_registry_entry(self, tmp_path: Path):
        from shenbi.pipeline.truth_io import _PATH_LOCKS

        key = str(tmp_path / "current_state.md")
        with _path_lock(tmp_path / "current_state.md"):
            entry_a = _PATH_LOCKS[key]
        with _path_lock(tmp_path / "current_state.md"):
            entry_b = _PATH_LOCKS[key]
        assert entry_a[0] is entry_b[0]  # same thread-lock object

    def test_different_paths_get_different_locks(self, tmp_path: Path):
        from shenbi.pipeline.truth_io import _PATH_LOCKS

        with (
            _path_lock(tmp_path / "current_state.md"),
            _path_lock(tmp_path / "character_matrix.md"),
        ):
            a = _PATH_LOCKS[str(tmp_path / "current_state.md")]
            b = _PATH_LOCKS[str(tmp_path / "character_matrix.md")]
            assert a[0] is not b[0]

    def test_refcount_releases_and_lockfile_created(self, tmp_path: Path):
        import sys

        from shenbi.pipeline.truth_io import _PATH_LOCKS

        key = str(tmp_path / "current_state.md")
        with _path_lock(tmp_path / "current_state.md"):
            assert _PATH_LOCKS[key][1] == 1  # held
            if sys.platform != "win32":
                assert (tmp_path / "current_state.md.lockfile").exists()
        assert _PATH_LOCKS[key][1] == 0  # released

    def test_registry_lock_is_not_a_path_lock(self, tmp_path: Path):
        # The registry guard lock must not collide with a path named like it.
        from shenbi.pipeline.truth_io import _PATH_LOCKS, _REGISTRY_LOCK

        with _path_lock(tmp_path / "_REGISTRY_LOCK"):
            assert all(_REGISTRY_LOCK is not entry[0] for entry in _PATH_LOCKS.values())


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


# --- SDD #21 R1: insert_markdown_row mode -----------------------------------


def test_insert_mode_appends_when_key_absent(tmp_path: Path) -> None:
    from shenbi.pipeline.truth_io import write_truth_file

    write_truth_file(
        tmp_path, "trend.md", "| 1 | a |", mode="insert_markdown_row", key_field="chapter"
    )
    write_truth_file(
        tmp_path, "trend.md", "| 2 | b |", mode="insert_markdown_row", key_field="chapter"
    )
    text = (tmp_path / "truth" / "trend.md").read_text(encoding="utf-8")
    assert "| 1 | a |" in text
    assert "| 2 | b |" in text


def test_insert_mode_skips_when_key_exists(tmp_path: Path) -> None:
    from shenbi.pipeline.truth_io import write_truth_file

    write_truth_file(
        tmp_path, "trend.md", "| 1 | rich |", mode="insert_markdown_row", key_field="chapter"
    )
    write_truth_file(
        tmp_path, "trend.md", "| 1 | placeholder |", mode="insert_markdown_row", key_field="chapter"
    )
    text = (tmp_path / "truth" / "trend.md").read_text(encoding="utf-8")
    assert "rich" in text
    assert "placeholder" not in text


def test_has_markdown_row_whole_cell_semantics() -> None:
    from shenbi.pipeline.truth_io import has_markdown_row

    existing = "| chapter | x |\n|---|---|\n| 55 | a |"
    assert has_markdown_row(existing, "| 55 | b |", "chapter")
    assert not has_markdown_row(existing, "| Ch55 | b |", "chapter")  # whole-cell key
    assert not has_markdown_row(existing, "not a table row", "chapter")


def test_insert_mode_rejects_dict_data(tmp_path: Path) -> None:
    import pytest

    from shenbi.pipeline.truth_io import write_truth_file

    with pytest.raises(ValueError):
        write_truth_file(
            tmp_path, "trend.md", {"chapter": 1}, mode="insert_markdown_row", key_field="chapter"
        )


# ---------------------------------------------------------------------------
# Probe escalation #5/#6 (novel-xinghuo-probe, 2026-09-28): the state-settling
# increment merge corrupted truth/pending_hooks.md twice. The skill re-emits a
# per-chapter status table whose HEADER's first cell is "Hook ID" — the upsert
# keyed-matched that header against the live 8-column registry header and
# deleted it, and replaced rows were relocated to EOF, dangling after the
# Genesis notes prose.
# ---------------------------------------------------------------------------


def test_upsert_header_shaped_increment_row_is_skipped() -> None:
    """An increment row whose key cell IS the key field name (a re-emitted
    table header) must never delete the live header or append a ragged copy.
    """
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = (
        "---\ntype: truth\n---\n\n# 伏笔池\n\n"
        "## 伏笔总览\n\n"
        "| Hook ID | 内容 | type | dimension | 埋设章 | 预期激活 | 计划回收 | 状态 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| MH-001 | 账感即接口 | GENUINE | INFORMATION | 第1章 | 第10章 | 第120章 | 已种植 |\n"
        "| MH-002 | 名单真相 | GENUINE | INFORMATION | 第5章 | 第113章 | 第131章 | 已种植 |\n"
    )
    increment_header = "| Hook ID | 操作 | 推进方式 | 沉默章数 |"
    result = upsert_markdown_row(existing, increment_header, "hook_id")
    assert result == existing, "header-shaped increment rows must be a no-op"
    assert result.count("| Hook ID") == 1


def test_upsert_replaces_row_in_place_not_at_eof() -> None:
    """A keyed replacement lands at the replaced row's position — the old
    primitive moved it to EOF, dangling after trailing prose sections.
    """
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = (
        "| Hook ID | 内容 | 状态 |\n"
        "|---|---|---|\n"
        "| MH-001 | 账感即接口 | 待种植 |\n"
        "| MH-002 | 名单真相 | 待种植 |\n"
        "\n## Genesis 备注\n\n- 全书 32 条总登记。\n"
    )
    updated = "| MH-001 | 账感即接口 | 已种植（第1章，subtlety 0.85） |"
    result = upsert_markdown_row(existing, updated, "hook_id")
    lines = result.split("\n")
    assert updated in lines
    assert lines.index(updated) < lines.index("## Genesis 备注"), "row must stay in its table"
    assert result.count("| MH-001") == 1, "no duplicate of the replaced row"
    assert "- 全书 32 条总登记。" in result


def test_upsert_new_key_row_inserts_into_keys_table() -> None:
    """A new-key row joins the table carrying the key column instead of
    dangling at EOF after prose (and after OTHER tables it does not belong to).
    """
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = (
        "## 格式约定\n\n"
        "| 项 | 说明 |\n"
        "|---|---|\n"
        "| 状态 | 五值枚举 |\n"
        "\n## 伏笔总览（共 32 条）\n\n"
        "| Hook ID | 内容 | 状态 |\n"
        "|---|---|---|\n"
        "| MH-001 | 账感即接口 | 已种植 |\n"
        "\n## Genesis 备注\n\n- 备注\n"
    )
    new_row = "| MH-002 | 名单真相 | 已种植 |"
    result = upsert_markdown_row(existing, new_row, "hook_id")
    lines = result.split("\n")
    assert new_row in lines
    assert lines.index(new_row) > lines.index("| MH-001 | 账感即接口 | 已种植 |")
    assert lines.index(new_row) < lines.index("## Genesis 备注"), (
        "new row must land inside the hook table, not after trailing prose"
    )


def test_upsert_duplicate_section_block_is_skipped() -> None:
    """Probe escalation #14: alternating state-settling/foreshadowing writers
    re-emitted the same-headed "### MH-NNN" section per run — three duplicate
    ch3 blocks accumulated. A block whose first line already exists is a
    duplicate, not new data.
    """
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = "| Hook ID | 状态 |\n|---|---|\n| MH-001 | 已种植 |\n"
    block = "### MH-001｜静海回响\n- lifecycle_state: RELEVANT\n- 本章推进: 外部命名\n"
    once = upsert_markdown_row(existing, block, "hook_id")
    twice = upsert_markdown_row(once, block, "hook_id")
    assert once.count("### MH-001｜静海回响") == 1
    assert twice == once, "re-emitted same-headed block must not duplicate"
    assert twice.count("### MH-001｜静海回响") == 1


def test_upsert_shape_mismatch_row_keeps_existing() -> None:
    """Probe escalation #14: an 8-column registry row replaced by a 10-column
    status row corrupts the table. Shape-mismatched rewrites are skipped;
    same-width and append-only enrichments still replace in place.
    """
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = "| Hook ID | 内容 | 状态 |\n|---|---|---|\n| MH-001 | 账感即接口 | 已种植 |\n"
    # different shape, cells rewritten -> keep old row
    bad = "| MH-001 | 账感即接口 | RELEVANT | 第3章 | 0.85 | RISING | 30 | 60 | X | Y |"
    result = upsert_markdown_row(existing, bad, "hook_id")
    assert "| MH-001 | 账感即接口 | 已种植 |" in result
    assert "RELEVANT" not in result

    # append-only enrichment -> replaces in place
    enrich = "| MH-001 | 账感即接口 | 已种植 | last_reinforced: 第3章 |"
    result2 = upsert_markdown_row(existing, enrich, "hook_id")
    assert enrich in result2
    assert result2.count("| MH-001") == 1


def test_increment_units_chapter_section_swallows_subsections() -> None:
    """probe6 ch2 (2026-10-01): the settle contract prescribes ``one
    ## 第N章状态增量 section block (heading + its rows/prose)``, but the
    splitter broke at EVERY heading — the ``###`` children became
    independent units, and a same-named child (``### 陈砚``, the protagonist
    recurs every chapter) hit ``_replace_section`` across chapters,
    overwriting the PREVIOUS chapter's state under its heading. Deterministic
    from ch2 onward. A ``##``-anchored block must swallow its deeper
    NON-hook sub-headings so the chapter section stays atomic.
    """
    from shenbi.pipeline.dispatch_helper import _increment_units
    from shenbi.pipeline.truth_io import upsert_markdown_row

    live = (
        "---\ntype: truth\n---\n\n# 角色交互矩阵\n\n"
        "| 角色A | 角色B | 关系状态 | 章节 |\n|---|---|---|---|\n"
        "| 陈砚 | 矿监 | 被登记方 | 第 1 章 |\n"
        "| 陈砚 | 白袍人 | 受予者 | 第 1 章 |\n"
        "## 第 1 章状态增量\n"
        "### 陈砚 ／ 丙字七三二九（主角）\n"
        "- 公开身份: 矿工，编号「丙字七三二九」\n"
        "- Current Location: 七号矿洞坑口\n"
        "- Last Updated Ch: 第 1 章\n"
    )
    increment = (
        "| 陈砚 | 监工 | 被点方 | 第 2 章 |\n"
        "## 第 2 章状态增量\n"
        "### 陈砚 ／ 丙字七三二九（主角）\n"
        "- 公开身份: 洗矿棚丙区矿工，编号「丙字七三二九」\n"
        "- Current Location: 灰脊城洗矿棚丙区\n"
        "- Last Updated Ch: 第 2 章\n"
        "### 柳氏\n- 公开身份: 丙区名册代管者\n"
    )
    units = _increment_units(increment)
    # The chapter section is ONE atomic unit (heading + both sub-sections).
    chapter_units = [u for u in units if u.startswith("## 第 2 章状态增量")]
    assert len(chapter_units) == 1
    assert "### 陈砚" in chapter_units[0] and "### 柳氏" in chapter_units[0]

    merged = live
    for unit in units:
        merged = upsert_markdown_row(merged, unit, "角色A,角色B")

    # ch1 section survives VERBATIM (no cross-chapter replacement)...
    assert "- 公开身份: 矿工，编号「丙字七三二九」" in merged
    assert "## 第 1 章状态增量" in merged and "## 第 2 章状态增量" in merged
    # ...interaction rows accumulate (composite keys never collapse)...
    for pair in ("| 陈砚 | 矿监 |", "| 陈砚 | 白袍人 |", "| 陈砚 | 监工 |"):
        assert pair in merged
    # ...and the ch2 protagonist state lands under the ch2 section only.
    assert merged.count("- 公开身份: 洗矿棚丙区矿工") == 1
    ch2_span = merged.split("## 第 2 章状态增量")[1]
    assert "洗矿棚丙区矿工" in ch2_span


def test_increment_units_hook_sections_stay_independent_under_parent() -> None:
    """Escalation #16 regression guard under the sibling-level rule: hook
    sections (``### MH-xxx``) must remain independent units even when the
    increment carries a parent ``##`` heading — the hook bullet merge keys
    on the hook id, a swallowed hook section would dedup on the parent.
    """
    from shenbi.pipeline.dispatch_helper import _increment_units

    increment = (
        "## 第3章 状态变化\n\n总述行。\n\n"
        "### MH-001｜静海回响\n- last_reinforced: 第3章\n\n"
        "### MH-005｜名字的保存方式\n- last_reinforced: 第3章\n"
    )
    units = _increment_units(increment)
    assert any(u.startswith("### MH-001｜") for u in units)
    assert any(u.startswith("### MH-005｜") for u in units)
    # the parent ## heading did NOT swallow them
    parent = [u for u in units if u.startswith("## 第3章")]
    assert len(parent) == 1
    assert "MH-001" not in parent[0]


def test_increment_units_h1_block_does_not_swallow_h2() -> None:
    """A re-emitted document title (``# 角色交互矩阵``) must not anchor a
    whole-file replacement unit: swallowing ``##`` sections under an h1
    block would make partial title-led outputs destructive (span-to-EOF
    replace). h1 blocks stay atomic at their own level only.
    """
    from shenbi.pipeline.dispatch_helper import _increment_units

    increment = "# 角色交互矩阵\n\n> 占位说明\n\n## 第 1 章状态增量\n### 陈砚\n- x: 1\n"
    units = _increment_units(increment)
    assert any(u.startswith("# 角色交互矩阵") for u in units)
    assert any(u.startswith("## 第 1 章状态增量") for u in units)
    title_unit = next(u for u in units if u.startswith("# 角色交互矩阵"))
    assert "第 1 章状态增量" not in title_unit


def test_increment_units_split_at_heading_boundaries() -> None:
    """Probe escalation #16: a multi-section increment grouped as ONE block
    dedups only on its first heading — a re-emitted duplicate section deeper
    in the block slipped past the block-level dedup. Sections must become
    independent units.
    """
    from shenbi.pipeline.dispatch_helper import _increment_units
    from shenbi.pipeline.truth_io import upsert_markdown_row

    increment = (
        "## 第3章 状态变化\n\n总述行。\n\n"
        "### MH-001｜静海回响\n- lifecycle_state: RELEVANT\n\n"
        "### MH-005｜名字的保存方式\n- lifecycle_state: RELEVANT\n"
    )
    units = _increment_units(increment)
    assert any(u.startswith("### MH-001｜") for u in units), "sections must be separate units"
    assert any(u.startswith("### MH-005｜") for u in units)

    # duplicate section deeper in a later block is skipped by first-line dedup
    base = "## 第3章 状态变化\n\n总述行。\n\n### MH-001｜静海回响\n- lifecycle_state: RELEVANT\n"
    dup_block = "### MH-001｜静海回响\n- lifecycle_state: RELEVANT（重复）\n"
    result = upsert_markdown_row(base, dup_block, "hook_id")
    assert result.count("### MH-001｜静海回响") == 1


def test_increment_units_drop_separator_rows() -> None:
    """Probe esc (resonance 碎表 root cause): a skill increment carries its
    own table HEADER + SEPARATOR + row. The separator unit was upserted as
    if it were data — old code appended it at EOF (fragment-table look),
    current code inserts it mid-table. Separators are structural, never
    data: the existing table already has one.
    """
    import shutil
    import tempfile
    from pathlib import Path

    from shenbi.pipeline.dispatch_helper import _route_append_dedup_write

    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "truth").mkdir()
        live = tmp / "truth" / "resonance_trend.md"
        live.write_text(
            "---\ntype: truth\n---\n\n"
            "| chapter | role | overall |\n|---|---|---|\n"
            "| 1 | 过渡 | 83 |\n| 13 | 推进 | 88 |\n",
            encoding="utf-8",
        )
        increment = "| chapter | role | overall |\n|---|---|---|\n| 14 | 推进 | 89 |\n"
        _route_append_dedup_write(tmp, "truth/resonance_trend.md", increment, key_field="chapter")
        out = live.read_text(encoding="utf-8")
        lines = [l for l in out.split("\n") if l.strip().startswith("|")]
        separators = [
            l
            for l in lines
            if all(
                __import__("re").fullmatch(r":?-{3,}:?", c.strip())
                for c in l.strip().strip("|").split("|")
                if c.strip()
            )
        ]
        assert len(separators) == 1, f"exactly one separator expected, got {len(separators)}"
        assert any(l.startswith("| 14 |") for l in lines)
        # row 14 must sit INSIDE the table (after row 13, before EOF prose)
        assert lines.index("| 14 | 推进 | 89 |") > lines.index("| 13 | 推进 | 88 |")
    finally:
        shutil.rmtree(tmp)


def test_upsert_section_replace_semantics() -> None:
    """Probe defect (twice bitten): a re-emitted same-heading section was
    SKIPPED whole by the block dedup — approved section updates could never
    reach live through the commit merge (the empty-shell heading that
    landed first blocked every later filled version). Headed blocks now
    REPLACE the existing same-heading section: dedup (no accumulation) and
    update propagation in one semantics.
    """
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = (
        "## 伏笔详情\n\n"
        "### MH-001｜静海回响\n- lifecycle_state: PLANTED\n- 旧证据\n\n"
        "### MH-005｜名字\n- lifecycle_state: PLANTED\n"
    )
    updated = "### MH-001｜静海回响\n- lifecycle_state: RELEVANT\n- 新证据（第 9 章）"
    result = upsert_markdown_row(existing, updated, "hook_id")

    assert result.count("### MH-001｜静海回响") == 1
    assert "RELEVANT" in result and "新证据" in result, "updated section must replace the old"
    assert "PLANTED｜旧证据" not in result and "旧证据" not in result, "old body must not linger"
    assert "### MH-005" in result, "sibling section untouched"


def test_upsert_heading_less_block_keeps_dedup_behavior() -> None:
    """Heading-less prose blocks keep the append-if-missing / skip-if-present
    fallback — replace semantics apply ONLY to headed sections.
    """
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = "## 备注\n\n- 第一条\n"
    result = upsert_markdown_row(existing, "- 第一条", "hook_id")
    assert result.count("- 第一条") == 1


@pytest.mark.unit
def test_upsert_markdown_row_key_match_is_whitespace_insensitive():
    """Fixcheck ch3: two settle attempts emitted the same chapter key with
    different spacing (``第 3 章`` vs ``第3章``); the exact-string key
    compare treated them as distinct keys and both rows landed. Key
    identity must be whitespace-normalized — a re-run of the same chapter
    replaces that chapter's row (re-runs are safe, per the skill contract).
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        truth_dir = project_dir / "truth"
        truth_dir.mkdir()
        target = truth_dir / "chapter_summaries.md"
        target.write_text("| 章号 | 摘要 |\n|---|---|\n| 第 3 章 | 首次结算 |\n", encoding="utf-8")

        new = "| 第3章 | 修订后结算 |"
        write_truth_file(
            project_dir,
            "chapter_summaries.md",
            new,
            mode="upsert_markdown_row",
            key_field="章号",
        )

        result = target.read_text(encoding="utf-8")
        assert "修订后结算" in result
        assert "首次结算" not in result, "same chapter key must replace, not duplicate"
        assert result.count("| 第 3 章 |") + result.count("| 第3章 |") == 1


@pytest.mark.unit
def test_has_markdown_row_key_match_is_whitespace_insensitive():
    """insert_markdown_row's existence probe must use the same normalized
    key semantics as the upsert (SDD #21 R1 symmetry).
    """
    from shenbi.pipeline.truth_io import has_markdown_row

    existing = "| 章号 | 摘要 |\n|---|---|\n| 第 3 章 | 首次结算 |\n"
    assert has_markdown_row(existing, "| 第3章 | x |", "章号") is True
    assert has_markdown_row(existing, "| 第 4 章 | x |", "章号") is False


def test_composite_key_field_upserts_on_column_tuple():
    """Probe2 settle capacity fix: the 交互矩阵 keys rows on (角色A, 角色B) —
    a single-column key on 角色A would collapse every row sharing the same
    first character into one. Comma-separated key_field selects a column
    TUPLE; rows match only when every key column matches.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()
        target = project_dir / "truth" / "character_matrix.md"
        existing = (
            "## 一、信任度矩阵\n\n"
            "| 角色A | 角色B | 关系类型 | 信任度(0-10) | 最近变化章节 |\n"
            "|-------|-------|----------|--------------|--------------|\n"
            "| 陆见星 | 柳箩 | 镜子 | 7 | 第1章 |\n"
            "| 陆见星 | 韩老栓 | 试探 | 5 | 第1章 |\n"
            "| 陆见星 | 纪听澜 | 对手 | 2 | 第1章 |\n"
        )
        target.write_text(existing)

        # Update ONLY the 柳箩 row; the other two 陆见星 rows must survive.
        new = "| 陆见星 | 柳箩 | 镜子·协作 | 8 | 第2章 |"
        write_truth_file(
            project_dir,
            "character_matrix.md",
            new,
            mode="upsert_markdown_row",
            key_field="角色A,角色B",
        )

        result = target.read_text()
        assert "镜子·协作" in result  # updated in place
        assert "| 陆见星 | 韩老栓 | 试探 | 5 | 第1章 |" in result
        assert "| 陆见星 | 纪听澜 | 对手 | 2 | 第1章 |" in result
        assert result.count("| 陆见星 | 柳箩") == 1  # replaced, not duplicated


def test_composite_key_falls_back_to_first_column_when_headers_absent():
    """A table whose header names none of the composite key columns (e.g. the
    信息边界表 keyed on 角色对) falls back to the first column — single-key
    semantics preserved for mixed-table increments.
    """
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = (
        "| 角色对 | 信息状态 |\n|--------|----------|\n"
        "| 陆见星–柳箩 | ASYMMETRIC |\n| 陆见星–韩老栓 | ASYMMETRIC |\n"
    )
    merged = upsert_markdown_row(
        existing, "| 陆见星–柳箩 | MUTUAL_SECRET（第2章起） |", "角色A,角色B"
    )
    assert "MUTUAL_SECRET" in merged
    assert "| 陆见星–韩老栓 | ASYMMETRIC |" in merged
    assert merged.count("陆见星–柳箩") == 1


def test_resonance_trend_bootstrap_header_on_create():
    """Probe2: the first trend row created a headerless file — the keyed
    upsert appended to an empty base, and the longitudinal reader requires
    a `chapter`+`overall` header row (the probe run had to be hand-repaired
    before e2e-report could parse it). Creating the file through the upsert
    path must bootstrap the contract header.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()
        write_truth_file(
            project_dir,
            "resonance_trend.md",
            "| 1 | - | - | - | - | - | 84 | mid |  |",
            mode="insert_markdown_row",
            key_field="chapter",
        )
        text = (project_dir / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
        # Frontmatter-guarantee invariant (phase3 P2): created truth files
        # carry the canonical block FIRST; the bootstrap header follows.
        assert text.startswith("---\n")
        lines = [l for l in text.splitlines() if l.strip()]
        assert any(l.startswith("| chapter |") for l in lines)
        assert any("overall" in l and l.startswith("| chapter |") for l in lines)
        assert any(l.startswith("| 1 |") for l in lines)

        # A second row must not duplicate the header
        write_truth_file(
            project_dir,
            "resonance_trend.md",
            "| 2 | - | - | - | - | - | 83 | mid |  |",
            mode="insert_markdown_row",
            key_field="chapter",
        )
        text = (project_dir / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
        assert text.count("| chapter |") == 1
        assert "| 1 |" in text and "| 2 |" in text


def test_bridge_tracker_bootstrap_header_on_create():
    """probe17 ch1 step 7 (adjudication #006): the compliant rows-only first
    write of truth/bridge_tracker.md lands on an empty base — without a
    registered contract header the file is created headerless and the
    bridge-id key column resolution has nothing to anchor to (kernel-of-truth
    wart the adjudicator flagged, resonance_trend probe2 precedent). The
    create-path must bootstrap the 8-column bridge header.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir()
        write_truth_file(
            project_dir,
            "bridge_tracker.md",
            "| BR-02 | 腕骨星痕与常九的不安 | 信息 | 第二卷 | 27-34 | PENDING | — | 第1章种植 |",
            mode="insert_markdown_row",
            key_field="bridge_id",
        )
        text = (project_dir / "truth" / "bridge_tracker.md").read_text(encoding="utf-8")
        # Frontmatter-guarantee invariant (phase3 P2): canonical block first,
        # bootstrap header after.
        assert text.startswith("---\n")
        lines = [l for l in text.splitlines() if l.strip()]
        assert any(l.startswith("| Bridge ID |") for l in lines)
        assert any("实际激活章" in l and l.startswith("| Bridge ID |") for l in lines)
        assert any(l.startswith("| BR-02 |") for l in lines)

        # A second bridge row must not duplicate the header
        write_truth_file(
            project_dir,
            "bridge_tracker.md",
            "| BR-05 | 报表亏空破口 | 事件 | 第二卷 | 35 | PENDING | — | 第19章种植 |",
            mode="insert_markdown_row",
            key_field="bridge_id",
        )
        text2 = (project_dir / "truth" / "bridge_tracker.md").read_text(encoding="utf-8")
        assert text2.count("| Bridge ID |") == 1
        assert "| BR-05 |" in text2


def test_section_replace_large_shrink_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wholesale section replacement that shrinks the span below half must
    WARN (session30 调试①: the ch60 pool compaction dropped 43% with zero log
    output — designed compaction was indistinguishable from data loss until
    an hour of log archaeology). Compaction is designed; invisibility is not
    (degrade-loudly discipline, spec #65 §4.3 kin).
    """
    from shenbi.pipeline import truth_io
    from shenbi.pipeline.truth_io import upsert_markdown_row

    existing = (
        "### MH01（灵印）\n\n"
        + "\n".join(f"- 证据: 第{n}章 某次强化的完整重述。{'长' * 40}" for n in range(4, 50))
        + "\n\n### MH02（灵誓）\n\n- lifecycle_state: PLANTED\n"
    )
    # free-form line forces the replace path (bullet-merge rejects non-bullets)
    condensed = "### MH01（灵印）\n\n- lifecycle_state: RELEVANT\n最新一章的完整重述。\n"
    warned: list[str] = []

    def _spy(event: str, **kw: object) -> None:
        warned.append(event)

    monkeypatch.setattr(truth_io.log, "warning", _spy)

    out = upsert_markdown_row(existing, condensed, "hook_id")

    assert "### MH02（灵誓）" in out, "sibling section untouched"
    assert "最新一章的完整重述。" in out, "replacement landed"
    assert "truth_section_replace_shrank" in warned


class TestPoolOverviewDerivation:
    """GO① root fix (phase3 终报): the pending_hooks 总览 table froze ch15-36
    because track/resolve/settling are contract-forbidden from emitting
    overview rows (anti-whole-pool-rewrite) while lifecycle only covers its
    own chapter's hooks — and post-genesis planted hooks (CP-004..009) never
    got rows at all. Derivation-on-write: when a hook detail section lands,
    the merge layer mechanically reflects its stable fields into the 总览
    row, making the table a derived mirror instead of a second writer
    discipline.
    """

    BASE = (
        "---\ntype: truth\n---\n\n# 伏笔池\n\n## 总览\n\n"
        "| Hook ID（钩书名） | 当前生命周期 | 种植章 | 兑现章（卷） | 类型 | 微妙度 | max_distance(14) | 升级曲线 |\n"
        "|------|------|------|------|------|------|------|------|\n"
        "| MH01（灵印） | PLANTED | 4 |  | MYSTERY | 0.5 | 10 | STAIRCASE |\n"
        "\n## 详情\n\n### MH01（灵印）\n\n"
        "- type: MYSTERY\n- lifecycle_state: PLANTED\n- plant_chapter: 4\n"
        "- subtlety: 0.5\n- max_distance: 10\n- escalation_curve: STAIRCASE\n"
    )

    def test_detail_field_patch_reflects_into_overview_row(self) -> None:
        out = upsert_markdown_row(
            self.BASE,
            "### MH01（灵印）\n- lifecycle_state: RESOLVED\n- resolve_chapter: 104\n",
            "hook_id",
        )
        row = next(l for l in out.splitlines() if l.startswith("| MH01"))
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert cells[1] == "RESOLVED"
        assert cells[3] == "104"

    def test_new_hook_section_appends_derived_overview_row(self) -> None:
        out = upsert_markdown_row(
            self.BASE,
            "### CP-010（码头的新账）\n- type: ITEM\n- lifecycle_state: PLANTED\n"
            "- plant_chapter: 60\n- subtlety: 0.4\n- max_distance: 12\n"
            "- escalation_curve: RISING\n",
            "hook_id",
        )
        rows = [l for l in out.splitlines() if l.startswith("| CP-010")]
        assert len(rows) == 1, "derived row appended exactly once"
        cells = [c.strip() for c in rows[0].strip().strip("|").split("|")]
        assert cells[0] == "CP-010（码头的新账）"
        assert cells[1] == "PLANTED"
        assert cells[2] == "60"
        assert cells[3] == "-"
        assert cells[4] == "ITEM"

    def test_resolve_chapter_preserves_volume_suffix(self) -> None:
        base = self.BASE.replace(
            "| MH01（灵印） | PLANTED | 4 |  | MYSTERY",
            "| MH01（灵印） | TRIGGERED | 4 | 107（五卷） | MYSTERY",
        ).replace("- lifecycle_state: PLANTED", "- lifecycle_state: TRIGGERED")
        out = upsert_markdown_row(
            base,
            "### MH01（灵印）\n- lifecycle_state: RESOLVED\n- resolve_chapter: 107\n",
            "hook_id",
        )
        row = next(l for l in out.splitlines() if l.startswith("| MH01"))
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert cells[3] == "107（五卷）"

    def test_missing_overview_section_is_safe_noop(self) -> None:
        base = "### MH01（灵印）\n\n- lifecycle_state: PLANTED\n"
        out = upsert_markdown_row(
            base, "### MH01（灵印）\n- lifecycle_state: RELEVANT\n", "hook_id"
        )
        assert "- lifecycle_state: RELEVANT" in out
        assert out.count("## 总览") == 0

    def test_non_hook_key_skips_derivation(self) -> None:
        out = upsert_markdown_row(
            self.BASE,
            "### MH01（灵印）\n- lifecycle_state: RESOLVED\n",
            "some_other_key",
        )
        assert "RESOLVED" in out  # section patched
        row = next(l for l in out.splitlines() if l.startswith("| MH01"))
        assert "PLANTED" in row  # row untouched for non-hook keys


class TestThreadOverviewDerivation:
    """B 批: the GO① derivation mirrored onto outline/thread_map.md — a
    landed ``### <ID>: <名称>`` section mechanically reflects into its
    线索总览表 row (状态/优先级/max_gap from bullets, 起始章/终点章 from the
    跨度 bullet, 名称 from the heading on creation). The weaver's increment
    contract never touches overview rows.
    """

    BASE = """---
total_chapters: 118
---

# 线索地图

## 线索总览表

| ID | 名称 | 优先级 | 类型 | max_gap | 起始章 | 终点章 | 状态 |
|----|------|--------|------|---------|--------|--------|------|
| A1 | 灵印与残句 | P0 | 长线 | 2 | 1 | 118 | RELEVANT |
| C1 | 册上多报的名字 | P2 | 短线 | 8 | 3 | 40 | RELEVANT |

## 线索详情

### A1: 灵印与《灵律》残句

- **状态**: RELEVANT
- **跨度**: 第1章 - 第118章
- **优先级**: P0
- **max_gap**: 2

### C1: 册上多报的名字

- **状态**: RELEVANT
- **跨度**: 第3章 - 第40章
- **优先级**: P2
- **max_gap**: 8
"""

    def test_section_update_reflects_into_overview_row(self) -> None:
        out = upsert_markdown_row(
            self.BASE,
            "### C1: 册上多报的名字\n\n- **状态**: RESOLVED\n- **跨度**: 第3章 - 第17章\n- **优先级**: P2\n- **max_gap**: 8\n",
            "thread",
        )
        row = next(l for l in out.splitlines() if l.startswith("| C1"))
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert cells[7] == "RESOLVED"
        assert cells[5] == "3" and cells[6] == "17"

    def test_new_thread_section_appends_derived_overview_row(self) -> None:
        out = upsert_markdown_row(
            self.BASE,
            "### B7: 新开的商路\n\n- **状态**: PLANTED\n- **跨度**: 第50章 - 第80章\n- **优先级**: P1\n- **max_gap**: 4\n",
            "thread",
        )
        row = next(l for l in out.splitlines() if l.startswith("| B7"))
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert cells[0] == "B7"
        assert cells[1] == "新开的商路"
        assert cells[2] == "P1"
        assert cells[5] == "50" and cells[6] == "80"
        assert cells[7] == "PLANTED"

    def test_tombstoned_section_never_resurrects_a_row(self) -> None:
        from shenbi.pipeline.truth_io import sync_thread_overview_rows

        base = self.BASE.replace(
            "- **状态**: RELEVANT\n- **跨度**: 第3章 - 第40章",
            "- **状态**: RESOLVED\n- **跨度**: 第3章 - 第17章\n- archived_to: outline/thread_map_archive.md",
        ).replace("| C1 | 册上多报的名字 | P2 | 短线 | 8 | 3 | 40 | RELEVANT |", "")

        out = sync_thread_overview_rows(base)

        assert "| C1 |" not in out, "archived thread must not regain a row"

    def test_retitle_updates_name_cell_only_via_derivation(self) -> None:
        out = upsert_markdown_row(
            self.BASE,
            "### C1: 册上多报的那个名字（改题）\n\n- **状态**: RELEVANT\n- **跨度**: 第3章 - 第40章\n- **优先级**: P2\n- **max_gap**: 8\n",
            "thread",
        )
        assert "### C1: 册上多报的那个名字（改题）" in out
        assert "### C1: 册上多报的名字" not in out, "old heading replaced, not duplicated"
        # existing row keeps its 名称 cell (creation-only field)
        row = next(l for l in out.splitlines() if l.startswith("| C1"))
        assert "册上多报的名字" in row

    def test_missing_overview_table_bootstraps_on_section_landing(self) -> None:
        """vol1 genesis escalation #001: the old "missing table = safe
        no-op" contract left a scaffold-less creation write permanently
        without overview rows (G4.pt.lines death loop, repair tool equally
        no-op). A landed section now bootstraps the canonical table and
        mirrors every existing section's row.
        """
        base = "### A1: 名\n\n- **状态**: RELEVANT\n"
        out = upsert_markdown_row(base, "### A1: 名\n- **状态**: PAYING_OFF\n", "thread")
        assert "- **状态**: PAYING_OFF" in out
        assert "## 线索总览表" in out, "table bootstrapped"
        row = next(l for l in out.splitlines() if l.startswith("| A1 "))
        assert "PAYING_OFF" in row

    def test_missing_overview_table_without_sections_stays_noop(self) -> None:
        out = sync_thread_overview_rows("无任何线索区段的文件。\n")
        assert out == "无任何线索区段的文件。\n", "never invents a table without sections"

    def test_off_tier_thread_id_still_derives(self) -> None:
        r"""Rebudget-drill find: the locator/validator charset is
        ``[A-Za-z]+\d`` while the derivation only accepted ``[ABC]`` — an
        off-tier id (``D1``) merged but silently skipped its 总览行. The
        id charset is now single-sourced and tolerant.
        """
        out = upsert_markdown_row(
            self.BASE,
            "### D1: 溢出梯队的新线\n\n- **状态**: PLANTED\n- **跨度**: 第50章 - 第80章\n- **优先级**: P2\n",
            "thread",
        )
        row = next(l for l in out.splitlines() if l.startswith("| D1 |"))
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert cells[0] == "D1" and cells[1] == "溢出梯队的新线"
        assert cells[5] == "50" and cells[6] == "80" and cells[7] == "PLANTED"

    def test_new_thread_section_lands_inside_details(self) -> None:
        """Rebudget-drill find: the EOF append landed a NEW thread section
        after the trailing validator sections, outside ``## 线索详情`` —
        the details-bounded threads_overview slice never served it.
        """
        base = (
            self.BASE
            + "\n---\n\n## 章节线索推进表\n\n| 章节区间 | 主推 |\n|---|---|\n| 1-8（一卷 KR1） | A1 |\n"
        )
        out = upsert_markdown_row(
            base,
            "### C4: 新开的短线\n\n- **状态**: PLANTED\n- **跨度**: 第50章 - 第60章\n",
            "thread",
        )
        i_det = out.index("## 线索详情")
        i_c4 = out.index("### C4: 新开的短线")
        i_plan = out.index("## 章节线索推进表")
        assert i_det < i_c4 < i_plan, "new section lands inside 线索详情"
        row = next(l for l in out.splitlines() if l.startswith("| C4 |"))
        assert "PLANTED" in row
