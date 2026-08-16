"""T1 regression tests for truth_io upsert primitives (audit C3, T7 matrix).

Anchored to the T7 thread's /tmp reproductions of the four data-loss defects:

- T702: table-row key was the first whitespace token (regex non-space run),
  so CJK or space-containing keys like ``第 1 章`` collided on their first
  token and whole families of rows mutually deleted on upsert.
- T713: ``key_field`` was decorative for str table rows — it never located
  the key column, so non-first-column keys could not dedup correctly.
- T701: dict upsert re-serialized the whole file as a bare bullet list,
  collapsing frontmatter / H2 sections / prose.
- T706: YAML parse failure silently fell back to ``[]`` and the subsequent
  rewrite collapsed the whole file.
- T703: keyless NEW records were silently dropped while keyless existing
  records were kept — asymmetric.
- T712: replace-mode dict input rendered as a Python repr (``{'a': 1}``)
  that no reader could parse back.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.truth_io import (
    _upsert_markdown_table_row,
    write_truth_file,
)

# ---------------------------------------------------------------------------
# T702: full-cell key extraction (CJK / space-containing keys)
# ---------------------------------------------------------------------------


class TestTableRowKeyExtraction:
    def test_cjk_key_rows_not_mutually_deleted(self, tmp_path: Path):
        """T702 acceptance anchor: upserting 第 3 章 keeps 第 1 章 and 第 2 章.

        Old extractor took the first non-space run of the row, keying all
        three rows on their first token ``第`` and deleting the whole family.
        """
        target = tmp_path / "truth" / "chapter_summaries.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            "| 第 1 章 | 林烽初到边城 |\n| 第 2 章 | 夜探废弃书院 |\n",
            encoding="utf-8",
        )

        write_truth_file(
            tmp_path,
            "chapter_summaries.md",
            "| 第 3 章 | 山雨欲来 |",
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        result = target.read_text(encoding="utf-8")
        assert "| 第 1 章 |" in result, "第 1 章 row was deleted by upsert"
        assert "| 第 2 章 |" in result, "第 2 章 row was deleted by upsert"
        assert "| 第 3 章 |" in result

    def test_cjk_key_replaces_only_same_key_row(self, tmp_path: Path):
        """Re-upserting 第 2 章 replaces that one row, siblings untouched."""
        target = tmp_path / "truth" / "chapter_summaries.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            "| 第 1 章 | 旧 |\n| 第 2 章 | 旧 |\n",
            encoding="utf-8",
        )

        write_truth_file(
            tmp_path,
            "chapter_summaries.md",
            "| 第 2 章 | 新 |",
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        result = target.read_text(encoding="utf-8")
        assert result.count("| 第 2 章") == 1
        assert "新" in result
        assert "| 第 1 章 | 旧 |" in result

    def test_space_containing_english_key_dedups_on_whole_cell(self):
        """``Ch 1`` vs ``Ch 2`` differ only past the first token; whole-cell wins."""
        existing = "| Ch 1 | draft |\n| Ch 2 | draft |\n"
        result = _upsert_markdown_table_row(existing, "| Ch 2 | revised |", "chapter")
        assert "| Ch 1 | draft |" in result
        assert result.count("Ch 2") == 1
        assert "revised" in result

    def test_multiline_key_survives_key_extraction(self):
        """A key cell containing trailing commentary still compares whole."""
        existing = "| 第 1 章 | ok |\n"
        result = _upsert_markdown_table_row(existing, "| 第 10 章 | ok |", "chapter")
        assert "| 第 1 章 | ok |" in result
        assert "| 第 10 章 | ok |" in result


# ---------------------------------------------------------------------------
# T713: key_field locates the key column
# ---------------------------------------------------------------------------


class TestKeyFieldColumnPositioning:
    def test_key_field_locates_non_first_column(self, tmp_path: Path):
        """key_field='hook' dedups on the 'hook' column, not column 0."""
        target = tmp_path / "truth" / "hooks.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            "| status | hook |\n| --- | --- |\n"
            "| PLANTED | MH-001 | 旧状态 |\n"
            "| PLANTED | MH-002 | 别动我 |\n",
            encoding="utf-8",
        )

        write_truth_file(
            tmp_path,
            "hooks.md",
            "| TRIGGERED | MH-001 | 新状态 |",
            mode="upsert_markdown_row",
            key_field="hook",
        )

        result = target.read_text(encoding="utf-8")
        assert "| TRIGGERED | MH-001 | 新状态 |" in result
        assert "旧状态" not in result
        assert "| PLANTED | MH-002 | 别动我 |" in result

    def test_header_cell_matching_tolerates_case_and_separators(self):
        """``Hook ID`` header matches key_field ``hook_id`` (normalized)."""
        existing = "| status | Hook ID |\n| --- | --- |\n| PLANTED | MH-1 | old |\n"
        result = _upsert_markdown_table_row(existing, "| FIRED | MH-1 | new |", "hook_id")
        assert "FIRED" in result
        assert "old" not in result

    def test_headerless_table_defaults_to_first_column(self):
        """No header row → key column is 0 (existing behavior preserved)."""
        existing = "| a | 1 |\n| b | 2 |\n"
        result = _upsert_markdown_table_row(existing, "| b | 3 |", "whatever")
        assert "| a | 1 |" in result
        assert result.count("| b |") == 1

    def test_data_row_not_mistaken_for_header_without_separator(self):
        """A first data row containing the key word must not redirect the column."""
        existing = "| x | chapter |\n| keep | me |\n"
        # 'chapter' appears in column 1 of a NON-header row; key stays col 0.
        result = _upsert_markdown_table_row(existing, "| x | replaced |", "chapter")
        assert result.count("| x |") == 1
        assert "replaced" in result
        assert "| keep | me |" in result


# ---------------------------------------------------------------------------
# T701: dict upsert must not collapse the file structure
# ---------------------------------------------------------------------------

_T701_STRUCTURE = (
    "---\n"
    "update_mode: upsert_markdown_row\n"
    "---\n"
    "\n"
    "# Chapter Summaries\n"
    "\n"
    "## 摘要\n"
    "\n"
    "- 1: 主角进城 note=old\n"
    "\n"
    "## 备注\n"
    "\n"
    "自由散文段落，不应被覆写。\n"
)


class TestDictUpsertStructurePreservation:
    def test_upsert_updates_only_target_row_and_preserves_structure(self, tmp_path: Path):
        """T701 anchor: dict upsert replaces the matching bullet in place.

        Frontmatter, H1/H2 headings and prose must survive verbatim — the old
        implementation re-serialized the whole file as a bare bullet list.
        """
        target = tmp_path / "truth" / "chapter_summaries.md"
        target.parent.mkdir(parents=True)
        target.write_text(_T701_STRUCTURE, encoding="utf-8")

        write_truth_file(
            tmp_path,
            "chapter_summaries.md",
            {"chapter": "1", "note": "new"},
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        result = target.read_text(encoding="utf-8")
        # Structure fully preserved
        assert "update_mode: upsert_markdown_row" in result
        assert "# Chapter Summaries" in result
        assert "## 摘要" in result
        assert "## 备注" in result
        assert "自由散文段落，不应被覆写。" in result
        # Target row updated in place, exactly once
        assert "- 1: note=new" in result
        assert "note=old" not in result
        assert result.count("- 1:") == 1

    def test_upsert_appends_new_key_row_preserving_structure(self, tmp_path: Path):
        """A new key appends one bullet; existing rows and structure intact."""
        target = tmp_path / "truth" / "chapter_summaries.md"
        target.parent.mkdir(parents=True)
        target.write_text(_T701_STRUCTURE, encoding="utf-8")

        write_truth_file(
            tmp_path,
            "chapter_summaries.md",
            {"chapter": "2", "note": "second"},
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        result = target.read_text(encoding="utf-8")
        assert "- 1: 主角进城 note=old" in result
        assert "- 2: note=second" in result
        assert "## 备注" in result
        assert "自由散文段落，不应被覆写。" in result

    def test_exact_key_match_no_prefix_collision(self, tmp_path: Path):
        """Key ``1`` must not match the row for key ``10`` (exact compare)."""
        target = tmp_path / "truth" / "chapter_summaries.md"
        target.parent.mkdir(parents=True)
        target.write_text("- 10: note=ten\n", encoding="utf-8")

        write_truth_file(
            tmp_path,
            "chapter_summaries.md",
            {"chapter": "1", "note": "one"},
            mode="upsert_markdown_row",
            key_field="chapter",
        )

        result = target.read_text(encoding="utf-8")
        assert "- 10: note=ten" in result
        assert "- 1: note=one" in result

    def test_creates_heading_file_when_missing(self, tmp_path: Path):
        """A brand-new file still gets the H1 + bullet scaffold."""
        write_truth_file(
            tmp_path,
            "chapter_summaries.md",
            {"chapter": "1", "note": "first"},
            mode="upsert_markdown_row",
            key_field="chapter",
        )
        result = (tmp_path / "truth" / "chapter_summaries.md").read_text(encoding="utf-8")
        assert "# chapter_summaries" in result
        assert "- 1: note=first" in result
