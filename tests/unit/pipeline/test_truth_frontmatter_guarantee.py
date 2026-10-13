"""Truth-file scaffolding as a program invariant (phase3 data point #2,
second recurrence — adjudication 004 character_matrix + live
truth/resonance_anchors.md 57 headerless/frontmatter-less chapters).

Root cause: the create surfaces (keyed upsert / staging merge / sanctioned
creation form / staged-priority commit merge) guaranteed at most a
registered TABLE header — frontmatter presence was left to the LLM's
creation form or a pre-existing shell. One helper, three surfaces:

- ensure_table_header (upsert/insert create-path + staging merge base)
- write_truth_file replace (sanctioned creation forms, whole-file rewrites)
- _merge_staged_rows_keyed (commit surface: live frontmatter survives a
  staged snapshot that lacks it)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from shenbi.pipeline.checkpoint import _merge_staged_rows_keyed
from shenbi.pipeline.confidence_calibration import record_anchor_outcome
from shenbi.pipeline.truth_io import (
    base_is_shell,
    ensure_table_header,
    ensure_truth_frontmatter,
    write_truth_file,
)

pytestmark = pytest.mark.unit


def test_ensure_truth_frontmatter_prepends_when_missing() -> None:
    out = ensure_truth_frontmatter("x.md", "# 标题\n\n正文\n")
    assert out.startswith("---\n")
    assert "type: truth" in out.split("---")[1]
    assert "# 标题" in out


def test_ensure_truth_frontmatter_noop_when_present() -> None:
    text = "---\ntype: truth\ncategory: hook\n---\n\n# 池\n"
    assert ensure_truth_frontmatter("x.md", text) == text


def test_unregistered_truth_file_creation_gains_frontmatter() -> None:
    """resonance_anchors incident: unregistered in _TABLE_HEADER_BOOTSTRAP,
    so ensure_table_header returned "" verbatim — the framework's own
    calibration writer created a bare table with no header and no
    frontmatter.
    """
    out = ensure_table_header("resonance_anchors.md", "")
    assert out.startswith("---\n")
    assert "type: truth" in out


def test_record_anchor_outcome_creates_anchored_truth_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        record_anchor_outcome(project_dir, chapter=1, high_conf_anchors=4, correct=3)
        text = (project_dir / "truth" / "resonance_anchors.md").read_text(encoding="utf-8")
        assert text.startswith("---\n")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        assert any(ln.startswith("| chapter |") for ln in lines), lines[:4]
        assert any(ln.startswith("| 1 | 4 | 3 |") for ln in lines)


def test_write_truth_file_replace_guarantees_frontmatter() -> None:
    """Sanctioned creation forms are written verbatim — an LLM form without
    frontmatter used to commit as-is (adjudication 004: staged
    character_matrix lost live's frontmatter at the keyed-merge commit).
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        (project_dir / "truth").mkdir(exist_ok=True)
        write_truth_file(
            project_dir,
            "character_matrix.md",
            "# 角色矩阵\n\n| 角色A | 角色B | 关系 |\n|---|---|\n| 阿烬 | 沉砚 | 对峙 |\n",
            mode="replace",
        )
        text = (project_dir / "truth" / "character_matrix.md").read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert "# 角色矩阵" in text


def test_merge_staged_rows_keyed_repends_live_frontmatter() -> None:
    """The staged snapshot is the merge subject — when it lacks frontmatter
    but live carries one, the commit must not drop it (裁决 004 实锤).
    """
    live = "---\ntype: truth\ncategory: state\nstatus: filled\n---\n\n# 矩阵\n\n| 角色A | 角色B | 关系 |\n|---|---|\n| 阿烬 | 沉砚 | 对峙 |\n"
    staged = "# 矩阵\n\n| 角色A | 角色B | 关系 |\n|---|---|\n| 阿烬 | 沉砚 | 敌对 |\n"
    merged = _merge_staged_rows_keyed(staged, live, "角色A,角色B")
    assert merged.startswith("---\n")
    assert "敌对" in merged  # staged-priority row update preserved


def test_frontmatter_scaffold_still_classifies_as_shell() -> None:
    """#44 routing invariant: frontmatter + header-only content must stay a
    SHELL (creation form remains sanctioned on first write).
    """
    shell = ensure_truth_frontmatter("x.md", "| 章节 | 位置 |\n|---|---|\n")
    assert base_is_shell(shell) is True


def test_bare_row_repair_with_frontmatter_lands_header_after_block() -> None:
    """Repair form: frontmatter present, header missing, rows exist — the
    bootstrap header must land AFTER the block (frontmatter stays line 1).
    """
    damaged = (
        "---\ntype: truth\ncategory: state\nstatus: filled\n---\n\n| 1 | 0 | 0 |\n| 2 | 0 | 0 |\n"
    )
    out = ensure_table_header("resonance_anchors.md", damaged)
    assert out.startswith("---\n")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert lines[0] == "---"
    assert lines[5] == "| chapter | high_conf_anchors | correct |"
    assert any(ln.startswith("| 1 | 0 | 0 |") for ln in lines)
