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
