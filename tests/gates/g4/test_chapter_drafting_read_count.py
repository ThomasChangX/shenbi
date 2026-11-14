"""Spec #89 T1 AC1: the per-chapter plan file is read exactly once (memo base)."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4 import chapter_drafting as cd


@pytest.mark.unit
def test_plan_read_exactly_once_per_chapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = tmp_path / "proj"
    (proj / "chapters").mkdir(parents=True)
    (proj / "plans").mkdir(parents=True)
    (proj / "chapters" / "chapter-1.md").write_text(
        "## PRE_WRITE_CHECK\n- 目标\n\n正文一段。他说好了。\n\n## POST_WRITE_SELF_CHECK\n- 自检\n",
        encoding="utf-8",
    )
    plan = proj / "plans" / "chapter-1-plan.md"
    plan.write_text("- 本章目标：过闸\n- 章尾钩型：悬念\n", encoding="utf-8")

    reads = {"n": 0}
    real = Path.read_text
    target = str(plan)

    def counting(self: Path, *a: object, **k: object) -> str:
        if str(self) == target:
            reads["n"] += 1
        return real(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting)  # type: ignore[attr-defined]
    cd.g4_chapter_drafting([str(proj / "chapters" / "chapter-1.md")], project_dir=str(proj))
    assert reads["n"] == 1
