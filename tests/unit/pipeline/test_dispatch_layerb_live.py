"""Dispatch-loop Layer B behavior tests (spec #65 §3.0).

Unlike tests/unit/pipeline/test_field_filtering.py (pure-function tests),
these exercise the REAL _build_skill_prompt read loop end-to-end: the
loader-normalized reads + read_fields sidecar must actually filter content
before it reaches user_prompt. G0.9: inputs are assembled from real
fixture products (real fixture file contents; trivial declared-header
seeding only).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.contracts import fields as fields_mod
from shenbi.pipeline import dispatch_helper as dh
from shenbi.pipeline.dispatch_helper import _build_skill_prompt

pytestmark = pytest.mark.unit


@pytest.fixture()
def warn_spy(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Spy WARN events on both emitting module loggers (repo structlog
    writes via PrintLoggerFactory — stdlib handlers see nothing; this is
    the tests/unit/contracts/test_fields.py:71-83 pattern applied to both
    emitters: fields module -> field_filter_missing_fields; dispatch_helper
    -> extractor_failed_fulltext).
    """
    events: dict[str, list[str]] = {"fields": [], "dispatch": []}

    def _spy(bucket: list[str], orig):
        def inner(event: str, **kw: object) -> None:
            bucket.append(event)
            orig(event, **kw)

        return inner

    monkeypatch.setattr(fields_mod.log, "warning", _spy(events["fields"], fields_mod.log.warning))
    monkeypatch.setattr(dh.log, "warning", _spy(events["dispatch"], dh.log.warning))
    return events


@pytest.fixture()
def project_tree(tmp_path: Path) -> Path:
    """Minimal shenbi-chapter-planning read set, real fixture content."""
    (tmp_path / "truth").mkdir()
    (tmp_path / "outline").mkdir()
    # truth/chapter_summaries.md: chapter-planning declares fields [已完成章节]
    (tmp_path / "truth" / "chapter_summaries.md").write_text(
        "## 已完成章节\n\n第1章：占位。\n\n## OTHER_STUFF\n\nXYZZY_LEAK_MARKER 不该进 prompt。\n",
        encoding="utf-8",
    )
    # outline/volume_map.md from the G0.11 production mirror
    (tmp_path / "outline" / "volume_map.md").write_text(
        Path("tests/fixtures/volume-map-xinghuo.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # truth/current_state.md: shenbi-native seeded lineage (declared fields all present)
    (tmp_path / "truth" / "current_state.md").write_text(
        "## 系统演化阶段\n\n中期。\n\n## 参数当前位置\n\n第3卷。\n\n## 进行中的情节线\n\n主线。\n",
        encoding="utf-8",
    )
    (tmp_path / "outline" / "story_frame.md").write_text("frame", encoding="utf-8")
    (tmp_path / "truth" / "current_focus.md").write_text("focus", encoding="utf-8")
    (tmp_path / "truth" / "author_intent.md").write_text("intent", encoding="utf-8")
    (tmp_path / "truth" / "pending_hooks.md").write_text(
        "## 活跃伏笔\n\nA。\n\n## 伏笔统计\n\n2 条。\n", encoding="utf-8"
    )
    (tmp_path / "novel.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_declared_fields_filter_in_dispatch_loop(project_tree: Path) -> None:
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # Declared section survives
    assert "已完成章节" in user_prompt
    # Undeclared section of the same file must NOT reach the prompt
    assert "XYZZY_LEAK_MARKER" not in user_prompt


def test_escape_hatch_warns_and_fulltext_on_missing_field(
    project_tree: Path, warn_spy: dict[str, list[str]]
) -> None:
    # Sabotage: remove a declared field's header -> escape hatch must fire
    (project_tree / "truth" / "pending_hooks.md").write_text(
        "## 别的节\n\n无声明节。\n", encoding="utf-8"
    )
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    assert "field_filter_missing_fields" in warn_spy["fields"]
    # Full-text fallback: undeclared section present
    assert "别的节" in user_prompt


def test_string_reads_unfiltered(project_tree: Path) -> None:
    _, user_prompt, _ = _build_skill_prompt(
        "shenbi-chapter-planning", project_tree, "plan ch26", chapter=26
    )
    # outline/story_frame.md is a string read -> full content present
    assert "frame" in user_prompt
