"""C30 R3 assembly trigger gate + derived lifecycle index.

Spec #44 (T1602/F358): step-2 (chapter-planning) must not trigger context
assembly — the plan does not exist yet, so the old behavior wasted an
assembly pass and wrote a discarded minimal fallback per chapter.
"""

import re
from pathlib import Path
from typing import ClassVar

from shenbi.pipeline.chapter_loop import CHAPTER_STEPS, _run_context_assembly


def test_step2_does_not_call_assembly() -> None:
    step2 = CHAPTER_STEPS[1]
    assert step2.skill == "shenbi-chapter-planning"
    assert step2.calls_context_assembly is False


def test_step3_calls_assembly() -> None:
    step3 = CHAPTER_STEPS[2]
    assert step3.skill == "pipeline-context-prepare"
    assert step3.calls_context_assembly is True


def test_assembly_guard_skips_when_plan_missing(tmp_path: Path, monkeypatch) -> None:
    """Plan-missing guard: no assembly call, no fallback write (call count 0)."""
    calls: list[int] = []

    def _must_not_assemble(*args, **kwargs):  # pragma: no cover - guard must prevent
        raise AssertionError("assemble_context must not run without a plan")

    monkeypatch.setattr(
        "shenbi.pipeline.context_assemble.assemble_context",
        lambda *a, **k: calls.append(1) or _must_not_assemble(),
    )
    _run_context_assembly(tmp_path, 1)
    assert calls == []  # dispatch-count proxy: 0 assembly invocations
    assert not (tmp_path / "context" / "chapter-1-context.md").exists()


def test_assembly_runs_when_plan_exists(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "plans").mkdir()
    (tmp_path / "plans" / "chapter-1-plan.md").write_text("# plan\n", encoding="utf-8")

    class _Pkg:
        sections: ClassVar[list[str]] = []
        total_tokens: ClassVar[int] = 0

    monkeypatch.setattr("shenbi.pipeline.context_assemble.assemble_context", lambda *a, **k: _Pkg())
    monkeypatch.setattr(
        "shenbi.pipeline.context_assemble.write_context_file",
        lambda project_dir, chapter, pkg: project_dir / "context" / f"chapter-{chapter}-context.md",
    )
    # write_context_file is monkeypatched to return a path without creating
    # it — pre-create so the hard post-check passes.
    ctx = tmp_path / "context"
    ctx.mkdir()
    (ctx / "chapter-1-context.md").write_text("x", encoding="utf-8")
    _run_context_assembly(tmp_path, 1)  # must not raise


def test_foreshadowing_idx_derived_not_literal() -> None:
    src = Path("src/shenbi/pipeline/chapter_loop.py").read_text(encoding="utf-8")
    assert not re.search(r"_FORESHADOWING_LIFECYCLE_IDX\s*=\s*\d", src)
    # Derived value still points at the lifecycle step.
    from shenbi.pipeline.chapter_loop import (
        _FORESHADOWING_LIFECYCLE_IDX,  # pyright: ignore[reportPrivateUsage]
        CHAPTER_STEPS,
    )

    assert CHAPTER_STEPS[_FORESHADOWING_LIFECYCLE_IDX].skill == "shenbi-foreshadowing-lifecycle"


def test_new_chapter_starts_at_step1_volume_align() -> None:
    """F380 regression lock: a new chapter's first step is volume-align (step-1)."""
    assert CHAPTER_STEPS[0].skill == "pipeline-volume-align"
    assert CHAPTER_STEPS[0].step_num == 1
