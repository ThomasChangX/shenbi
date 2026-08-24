"""R1 (F602): establish_baseline wiring — baseline exists from chapter 4 on."""

import shutil
from pathlib import Path

FIXTURE_CHAPTERS = Path("tests/fixtures/multi-chapter-example")  # 真实章节产物 (G0.9)


def _make_project(tmp_path: Path) -> Path:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    for ch in (1, 2, 3, 4):
        shutil.copy(FIXTURE_CHAPTERS / f"chapter-{ch}.md", chapters / f"chapter-{ch}.md")
    return tmp_path


def test_baseline_lazily_established_from_ch4(tmp_path):
    from shenbi.pipeline.chapter_loop import _check_linguistic_drift

    project = _make_project(tmp_path)
    assert not (project / "style" / "linguistic_baseline.json").exists()

    result = _check_linguistic_drift(project, 4)

    baseline_file = project / "style" / "linguistic_baseline.json"
    assert baseline_file.exists()  # 验收：第 4 章起 baseline 文件存在
    assert result is not None  # 检查真实执行（非 no_linguistic_baseline 早退）


def test_baseline_not_established_before_ch4(tmp_path):
    from shenbi.pipeline.chapter_loop import _check_linguistic_drift

    project = _make_project(tmp_path)
    assert _check_linguistic_drift(project, 3) is None  # ch1-3 无 baseline 属预期
    assert not (project / "style" / "linguistic_baseline.json").exists()


def test_baseline_reused_not_rebuilt(tmp_path):
    from shenbi.pipeline.chapter_loop import _check_linguistic_drift

    chapters = tmp_path / "chapters"
    chapters.mkdir()
    for ch in (1, 2, 3, 4, 5):  # 含 ch5，否则 ch5 检查在文件存在性早退、断言空转
        shutil.copy(FIXTURE_CHAPTERS / f"chapter-{ch}.md", chapters / f"chapter-{ch}.md")
    _check_linguistic_drift(tmp_path, 4)
    baseline_file = tmp_path / "style" / "linguistic_baseline.json"
    first = baseline_file.read_text(encoding="utf-8")
    # 篡改章节后重跑：已存在的 baseline 不重建
    (tmp_path / "chapters" / "chapter-1.md").write_text("完全不同的文本", encoding="utf-8")
    _check_linguistic_drift(tmp_path, 5)
    assert baseline_file.read_text(encoding="utf-8") == first
