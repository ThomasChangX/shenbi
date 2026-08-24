"""R4 (F620): DriftEscalationError must escape the step call site; other
exceptions stay non-blocking. Tested via the extracted helper
``_run_linguistic_drift_check`` (the production call-site handler).
"""

import shutil
from pathlib import Path

import pytest

FIXTURE_CHAPTERS = Path("tests/fixtures/multi-chapter-example")


def _make_project(tmp_path: Path, ch4_text: str) -> Path:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    for ch in (1, 2, 3):
        shutil.copy(FIXTURE_CHAPTERS / f"chapter-{ch}.md", chapters / f"chapter-{ch}.md")
    (chapters / "chapter-4.md").write_text(ch4_text, encoding="utf-8")
    return tmp_path


DEGRADED = "冷在场于第七层深度。冷值7.3，在场度0.89。系统阈值参数格式串。" * 30


def test_escalation_propagates_out_of_check(tmp_path):
    from shenbi.pipeline.chapter_loop import DriftEscalationError, _check_linguistic_drift

    project = _make_project(tmp_path, DEGRADED)
    # 直接断言底层可达（stm>100‰ → ESCALATE → raise）
    with pytest.raises(DriftEscalationError):
        _check_linguistic_drift(project, 4)


def test_call_site_helper_rethrows_escalation(tmp_path, monkeypatch):
    """R4 核心: 调用点 helper 不得把 DriftEscalationError 降级为 warning."""
    from shenbi.pipeline import chapter_loop
    from shenbi.pipeline.chapter_loop import DriftEscalationError

    def fake_check(project_dir, chapter):
        raise DriftEscalationError("escalated")

    monkeypatch.setattr(chapter_loop, "_check_linguistic_drift", fake_check)
    with pytest.raises(DriftEscalationError):
        chapter_loop._run_linguistic_drift_check(tmp_path, 4)


def test_call_site_helper_swallows_other_exceptions(tmp_path, monkeypatch):
    from shenbi.pipeline import chapter_loop

    def fake_check(project_dir, chapter):
        raise RuntimeError("transient")

    monkeypatch.setattr(chapter_loop, "_check_linguistic_drift", fake_check)
    # 不外抛即通过（helper 内部 log.warning 降级）
    chapter_loop._run_linguistic_drift_check(tmp_path, 4)


def test_escalation_converted_to_checkpoint(monkeypatch, tmp_path):
    """R4 (audit I-1): DriftEscalationError 在 orchestrator 转为持久化
    ESCALATION checkpoint(镜像 RetryExhaustedError), 而非崩溃循环。
    """
    from typing import Any, ClassVar

    from shenbi.pipeline import cli
    from shenbi.pipeline.chapter_loop import DriftEscalationError
    from shenbi.pipeline.state import CheckpointType, PipelinePhase

    class _CL:
        current_chapter = 4
        step_index = 0

    class _State:  # type: ignore[no-any-unimported]
        phase = PipelinePhase.GENESIS
        chapter_loop = _CL()
        pending_re_dispatches: ClassVar[list[Any]] = []

    captured: dict[str, Any] = {}

    def fake_set_checkpoint(state, cp_type, chapter=None, context=None):
        captured["type"] = cp_type
        captured["chapter"] = chapter
        captured["context"] = context

    def raising_genesis(state, project_dir):
        raise DriftEscalationError("Chapter 4: system term density 233.0 per mille.")

    monkeypatch.setattr(cli, "set_checkpoint", fake_set_checkpoint)
    monkeypatch.setattr("shenbi.pipeline.genesis.run_genesis_step", raising_genesis)
    monkeypatch.setattr(cli, "save_state", lambda *a, **k: None)

    st = _State()
    cli._orchestrate_to_checkpoint(st, tmp_path)  # pyright: ignore[reportArgumentType]

    assert captured["type"] is CheckpointType.ESCALATION
    assert "drift ESCALATE" in captured["context"]
