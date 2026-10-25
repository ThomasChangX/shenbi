"""spec #72 T4: 2-chapter bundle stepping + pipeline-scene-split step (T2 层).

All inputs constructed in tmp_path (G0.9 structural exemption, spec §4);
run_gate_g4 is stubbed where the test target is the stepper wiring, not the
checkers (checkers carry their own T1/T6 suites).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.pipeline.chapter_loop import (
    CHAPTER_STEPS,
    PIPELINE_STEPS_VERSION,
    _run_scene_split_step,
    bundle_chapters,
)


def _w(project_dir: Path, n: int) -> None:
    staging = Path(project_dir) / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    parts = [
        f"===CH:{n}===",
        "## PRE_WRITE_CHECK",
        "",
        "- x",
        "",
        f"# 第{n}章",
        f"# 章题{n}",
        "",
        "<!--SCENE-->",
        "灯" * 1900,
        "钩一？",
        "<!--SCENE-->",
        "灯" * 1900,
        "钩二？",
        "",
        "## POST_WRITE_SELF_CHECK",
        "",
        "- y",
        "",
    ]
    (staging / f"chapter-{n}-bundle.md").write_text("\n".join(parts), encoding="utf-8")
    side = staging / "chapters" / f"chapter-{n}-decisions.json"
    side.parent.mkdir(parents=True, exist_ok=True)
    side.write_text("{}", encoding="utf-8")


def _project(tmp_path: Path, volume_spans: list[str] | None = None) -> Path:
    (tmp_path / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 3200, "min": 2800, "max": 4000}}),
        encoding="utf-8",
    )
    if volume_spans:
        vm = tmp_path / "outline"
        vm.mkdir(exist_ok=True)
        (vm / "volume_map.md").write_text("# Map\n\n" + "\n".join(volume_spans), encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_steps_version_3_and_16_skills() -> None:
    assert PIPELINE_STEPS_VERSION == 3
    skills = [s.skill for s in CHAPTER_STEPS]
    assert len(skills) == 16
    assert skills[4] == "pipeline-scene-split"
    assert skills.index("pipeline-scene-split") == skills.index("shenbi-chapter-drafting") + 1


@pytest.mark.unit
def test_drafting_step_no_md_output_path() -> None:
    drafting = next(s for s in CHAPTER_STEPS if s.skill == "shenbi-chapter-drafting")
    assert drafting.output_path == ""
    assert drafting.uses_staging is True


@pytest.mark.unit
def test_bundle_chapters_no_volume_map_singleton(tmp_path: Path) -> None:
    _project(tmp_path)  # no volume_map → singleton (conservative default)
    assert bundle_chapters(tmp_path, 1) == [1]


@pytest.mark.unit
def test_bundle_chapters_volume_end_singleton(tmp_path: Path) -> None:
    _project(tmp_path, ["## 第1卷 星火（第 1-4 章）", "## 第2卷 燎原（第 5-8 章）"])
    assert bundle_chapters(tmp_path, 3) == [3, 4]
    assert bundle_chapters(tmp_path, 4) == [4]  # 卷末奇数章单章簇
    assert bundle_chapters(tmp_path, 5) == [5, 6]


@pytest.mark.integration
def test_split_step_promotes_and_records_both(tmp_path: Path) -> None:
    _project(tmp_path, ["## 第1卷 星火（第 1-4 章）"])
    # 双章 bundle：章 1+2 各两独立场景
    staging = tmp_path / "staging"
    staging.mkdir(parents=True)

    def _ch(n: int) -> str:
        return "\n".join(
            [
                f"===CH:{n}===",
                "## PRE_WRITE_CHECK",
                "",
                "- x",
                "",
                f"# 第{n}章",
                f"# 章题{n}",
                "",
                "<!--SCENE-->",
                "灯" * 1900,
                f"第{n}章第一场景钩？",
                "<!--SCENE-->",
                "灯" * 1900,
                f"第{n}章第二场景钩？",
                "",
                "## POST_WRITE_SELF_CHECK",
                "",
                "- y",
                "",
            ]
        )

    (staging / "chapter-1-bundle.md").write_text(_ch(1) + "\n" + _ch(2), encoding="utf-8")
    for n in (1, 2):
        side = staging / "chapters" / f"chapter-{n}-decisions.json"
        side.parent.mkdir(parents=True, exist_ok=True)
        side.write_text("{}", encoding="utf-8")

    import shenbi.pipeline.chapter_loop as cl

    g4_calls: list[int] = []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            cl,
            "run_gate_g4",
            lambda skill, files, pd, chapter=None, phase=None: (
                g4_calls.append(int(chapter or 0)),
                {"status": "PASS", "checks": [], "must_fix": []},
            )[1],
        )
        issues = _run_scene_split_step(tmp_path, 1)
    assert issues == []
    for n in (1, 2):
        ch = tmp_path / "chapters" / f"chapter-{n}.md"
        assert ch.is_file()
        text = ch.read_text(encoding="utf-8")
        assert "===CH:" not in text  # CH 剥离
        assert text.count("<!--SCENE-->") == 2  # SCENE 保留
        # decisions 晋升
        assert (tmp_path / "chapters" / f"chapter-{n}-decisions.json").is_file()
    assert sorted(g4_calls) == [1, 2]  # manifest 闸记录按章分别落


@pytest.mark.integration
def test_split_step_missing_bundle_fails_closed(tmp_path: Path) -> None:
    _project(tmp_path)
    issues = _run_scene_split_step(tmp_path, 1)
    assert any("簇产物缺失" in i for i in issues)


@pytest.mark.integration
def test_split_step_gray_zone_violation(tmp_path: Path) -> None:
    _project(tmp_path)
    staging = tmp_path / "staging"
    staging.mkdir(parents=True)
    (staging / "chapter-1-bundle.md").write_text(
        "\n".join(
            [
                "===CH:1===",
                "## PRE_WRITE_CHECK",
                "",
                "- x",
                "",
                "# 第1章",
                "# 题",
                "",
                "<!--SCENE-->",
                "灯" * 1450,
                "钩一？",
                "<!--SCENE-->",
                "灯" * 1450,
                "钩二？",
                "",
                "## POST_WRITE_SELF_CHECK",
                "",
                "- y",
            ]
        ),
        encoding="utf-8",
    )
    issues = _run_scene_split_step(tmp_path, 1)
    assert any("灰域" in i for i in issues)


@pytest.mark.integration
def test_crash_replay_idempotent(tmp_path: Path) -> None:
    _project(tmp_path)
    _w(tmp_path, 1)
    import shenbi.pipeline.chapter_loop as cl

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            cl,
            "run_gate_g4",
            lambda *a, **kw: {"status": "PASS", "checks": [], "must_fix": []},
        )
        assert _run_scene_split_step(tmp_path, 1) == []
        first = (tmp_path / "chapters" / "chapter-1.md").read_bytes()
        assert _run_scene_split_step(tmp_path, 1) == []  # 重放
        second = (tmp_path / "chapters" / "chapter-1.md").read_bytes()
    assert first == second
