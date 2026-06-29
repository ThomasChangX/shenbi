from __future__ import annotations

import json
from pathlib import Path

from shenbi.audit.snapshot import compute_file_change, parametric_globs, snapshot_tree


def test_parametric_globs_loaded_from_registry() -> None:
    g = parametric_globs()
    # truth-files.yaml patterns 含 chapters/chapter-N.md -> chapters/chapter-*.md
    assert g.get("chapters/chapter-N.md") == "chapters/chapter-*.md"


def test_snapshot_reads_existing_and_missing(tmp_path: Path) -> None:
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")
    snap = snapshot_tree(tmp_path, ["genre-config.json", "absent.json"])
    assert snap["genre-config.json"] == "{}"
    assert snap["absent.json"] is None


def test_snapshot_expands_parametric_glob(tmp_path: Path) -> None:
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-5.md").write_text("c5", encoding="utf-8")
    snap = snapshot_tree(tmp_path, ["chapters/chapter-N.md"])
    assert "chapters/chapter-5.md" in snap
    assert snap["chapters/chapter-5.md"] == "c5"


def test_compute_json_field_change() -> None:
    pre = json.dumps({"version": "1.0", "approval": {"x": 1}})
    post = json.dumps({"version": "2.0", "approval": {"x": 1}})
    ch = compute_file_change("genre-config.json", pre, post)
    assert ch.status == "modified"
    assert ch.changed_top_keys == ("version",)


def test_compute_markdown_record_change() -> None:
    pre = "## hooks\n- id: h1\n  state: PLANTED\n  subtlety: 0.4\n- id: h2\n  state: PLANTED\n"
    post = (
        "## hooks\n"
        "- id: h1\n  state: RELEVANT\n  subtlety: 0.4\n"  # track 改 state（允许）
        "- id: h3\n  state: PLANTED\n"  # 新增
    )
    ch = compute_file_change("truth/pending_hooks.md", pre, post)
    assert ch.status == "modified"
    assert ch.new_record_ids == ("h3",)
    assert ch.deleted_record_ids == ("h2",)
    mods = dict(ch.modified_record_keys)
    assert mods["h1"] == frozenset({"state"})


def test_compute_added_and_deleted() -> None:
    assert compute_file_change("a.md", None, "x").status == "added"
    assert compute_file_change("a.md", "x", None).status == "deleted"
