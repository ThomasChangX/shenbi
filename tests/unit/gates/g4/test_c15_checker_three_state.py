"""Three-state (PASS/FAIL/SKIP) behavioral tests for zero-coverage G4 checkers.

F417/F765 (spec #53 C15). Inputs are real-product fixtures per G0.9
(arc-example.md carries generated_by: shenbi-memory-distill); missing-file
and no-file cases exercise the checker's own path handling.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from shenbi.gates.g4.book_spine_init import g4_book_spine_init
from shenbi.gates.g4.memory_distill import g4_memory_distill

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def _status(out: str) -> str:
    return json.loads(out)["status"]


class TestMemoryDistillChecker:
    def test_pass_on_real_artifact(self, tmp_path: Path) -> None:
        fp = tmp_path / "arc.md"
        shutil.copy(FIXTURES / "arc-example.md", fp)
        out = g4_memory_distill([str(fp)])
        assert _status(out) == "PASS"

    def test_fail_missing_section_on_arc_named_file(self, tmp_path: Path) -> None:
        fp = tmp_path / "arcs.md"  # arc in filename → 事件链/伏笔/角色状态 required
        fp.write_text("第3章 只有摘要，没有必需章节。\n", encoding="utf-8")
        out = g4_memory_distill([str(fp)])
        assert _status(out) == "FAIL"
        missing = [mf for mf in ("事件链", "伏笔", "角色状态") if f"missing_section:{mf}" in out]
        assert missing == ["事件链", "伏笔", "角色状态"]

    def test_fail_no_chapter_ref(self, tmp_path: Path) -> None:
        fp = tmp_path / "summary.md"
        fp.write_text("事件链 x 伏笔 y 角色状态 z\n", encoding="utf-8")
        out = g4_memory_distill([str(fp)])
        assert _status(out) == "FAIL"
        assert "no_chapter_ref" in out

    def test_fail_not_found(self, tmp_path: Path) -> None:
        # absolute path: resolve_input_path fails closed on relative paths without rd
        out = g4_memory_distill([str(tmp_path / "nonexistent-arc.md")])
        assert _status(out) == "FAIL"
        assert "not_found" in out

    def test_skip_when_no_files(self) -> None:
        # repo-wide g4 convention: empty file list → PASS with a SKIP check entry
        out = g4_memory_distill([])
        parsed = json.loads(out)
        assert parsed["status"] == "PASS"
        assert any(ch.get("s") == "SKIP" and ch.get("r") == "no files" for ch in parsed["checks"])


class TestBookSpineInitChecker:
    def test_pass_on_real_artifact(self, tmp_path: Path) -> None:
        fp = tmp_path / "book_spine.md"
        shutil.copy(FIXTURES / "book-spine-example.md", fp)
        out = g4_book_spine_init([str(fp)])
        assert _status(out) == "PASS"

    def test_fail_missing_required_fields(self, tmp_path: Path) -> None:
        fp = tmp_path / "book_spine.md"
        fp.write_text("# 空壳\n核心冲突 x\nthemes y\n主角弧 z\n主线钩子 w\n", encoding="utf-8")
        out = g4_book_spine_init([str(fp)])
        assert _status(out) == "FAIL"
        assert "missing_field:updated:" in out
        assert "missing_field:total_chapters:" in out
        assert "missing_field:status:" in out

    def test_fail_missing_sections(self, tmp_path: Path) -> None:
        fp = tmp_path / "book_spine.md"
        fp.write_text(
            "---\nupdated: 2026-01-01\ntotal_chapters: 100\nstatus: active\n---\n只有 frontmatter\n",
            encoding="utf-8",
        )
        out = g4_book_spine_init([str(fp)])
        assert _status(out) == "FAIL"
        for section in ("核心冲突", "themes", "主角弧", "主线钩子"):
            assert f"missing_section:{section}" in out

    def test_fail_not_found(self, tmp_path: Path) -> None:
        out = g4_book_spine_init([str(tmp_path / "nowhere" / "book_spine.md")])
        assert _status(out) == "FAIL"
        assert "not_found" in out

    def test_skip_when_no_files(self) -> None:
        # repo-wide g4 convention: empty file list → PASS with a SKIP check entry
        out = g4_book_spine_init([])
        parsed = json.loads(out)
        assert parsed["status"] == "PASS"
        assert any(ch.get("s") == "SKIP" and ch.get("r") == "no files" for ch in parsed["checks"])
