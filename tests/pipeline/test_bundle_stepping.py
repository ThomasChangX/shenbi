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
from shenbi.pipeline.state import PipelinePhase, PipelineState, ReviewDecision


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


@pytest.mark.integration
def test_two_chapter_bundle_loop_drive(tmp_path: Path) -> None:
    """Bundle-level full loop drive: after leader ch1 completes the whole
    step sequence, follower ch2 must NOT re-dispatch planning/drafting
    (cursor jumps by bundle size).
    """
    import shenbi.pipeline.chapter_loop as cl
    from shenbi.pipeline.dispatch_helper import DispatchResult

    _project(tmp_path, ["## 第1卷 星火（第 1-4 章）"])
    state = PipelineState.default(str(tmp_path))
    state.phase = PipelinePhase.CHAPTER_LOOP
    state.chapter_loop.current_chapter = 1

    dispatched: list[tuple[str, str]] = []
    g4_files_seen: list[str] = []

    def _fake_dispatch(skill, project_dir, prompt, **kw):
        dispatched.append((skill, prompt))
        if skill == "shenbi-chapter-planning":
            # 双备忘 + decisions 落 staging（存在性检查面）
            for n in (1, 2):
                d = tmp_path / "staging" / "plans"
                d.mkdir(parents=True, exist_ok=True)
                (d / f"chapter-{n}-plan.md").write_text(
                    f"# 第{n}章备忘\n\n## 1. 当前任务\n- x\n", encoding="utf-8"
                )
                (d / f"chapter-{n}-plan-decisions.json").write_text("{}", encoding="utf-8")
        if skill == "shenbi-foreshadowing-lifecycle":
            d = tmp_path / "staging" / "truth"
            d.mkdir(parents=True, exist_ok=True)
            (d / "pending_hooks.md").write_text("# hooks\n", encoding="utf-8")
        if skill == "shenbi-chapter-drafting":
            _w(Path(project_dir), 1)
            # 双章簇：补第二章（复用 _w 的单章形态再拼一段 CH:2）
            bundle = tmp_path / "staging" / "chapter-1-bundle.md"
            ch2 = "\n".join(
                [
                    "===CH:2===",
                    "## PRE_WRITE_CHECK",
                    "",
                    "- x",
                    "",
                    "# 第2章",
                    "# 章题2",
                    "",
                    "<!--SCENE-->",
                    "灯" * 1900,
                    "二章钩一？",
                    "<!--SCENE-->",
                    "灯" * 1900,
                    "二章钩二？",
                    "",
                    "## POST_WRITE_SELF_CHECK",
                    "",
                    "- y",
                    "",
                ]
            )
            bundle.write_text(bundle.read_text(encoding="utf-8") + "\n" + ch2, encoding="utf-8")
            side = tmp_path / "staging" / "chapters" / "chapter-2-decisions.json"
            side.write_text("{}", encoding="utf-8")
        return DispatchResult(True, 0, "{}", "")

    with pytest.MonkeyPatch.context() as mp:
        import time as _time

        mp.setattr(_time, "sleep", lambda *_a: None)  # retry backoff 免睡
        mp.setattr(cl, "dispatch_skill", _fake_dispatch)
        mp.setattr(
            cl,
            "run_gate_g4",
            lambda skill, files, pd, chapter=None, phase=None: (
                g4_files_seen.extend(files),
                {"status": "PASS", "checks": [], "must_fix": []},
            )[1],
        )
        mp.setattr(cl, "run_gate_g3", lambda *a, **kw: {"status": "PASS"})
        mp.setattr(
            "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
            lambda tasks, on_task_complete=None: [DispatchResult(True, 0, "{}", "") for _ in tasks],
        )
        mp.setattr(
            "shenbi.pipeline.parallel_dispatch.consolidate_review_results",
            lambda *a, **kw: "No BLOCKING issues.",
        )
        mp.setattr(cl, "_any_audit_has_findings", lambda *a, **kw: False)
        mp.setattr(cl, "_check_volume_map_alignment", lambda *a, **kw: None)
        mp.setattr(cl, "_run_post_draft_extract", lambda *a, **kw: None)
        mp.setattr(cl, "_run_g4_checks", lambda state, n: [])
        mp.setattr(cl, "_run_context_assembly", lambda *a, **kw: None)
        mp.setattr(
            cl,
            "run_audit_layer",
            lambda *a, **kw: type(
                "R", (), {"blocking_found": False, "issues": [], "audit_reports": []}
            )(),
        )
        mp.setattr(cl, "_parse_and_persist_resonance", lambda *a, **kw: None)
        mp.setattr(cl, "_route_revision_after_resonance", lambda *a, **kw: None)
        mp.setattr(cl, "write_audit_aggregate", lambda *a, **kw: None)
        mp.setattr(
            "shenbi.pipeline.revision_router.dispatch_escalation",
            lambda *a, **kw: None,
        )

        # 驱动 leader 章 1 到 chapter 完成（_advance/--auto 语义下 checkpoint 不阻塞）
        guard = 0
        while state.chapter_loop.current_chapter == 1 and guard < 200:
            before = (state.chapter_loop.current_chapter, state.chapter_loop.step_index)
            cl.run_chapter_step(state, tmp_path)
            if before == (state.chapter_loop.current_chapter, state.chapter_loop.step_index):
                # 卡在 checkpoint：按 approve 清掉继续（auto 模式等价）
                if state.pending_checkpoint:
                    from shenbi.pipeline.machine import clear_checkpoint as _cc

                    _cc(state, ReviewDecision.APPROVE)
                else:
                    break
            guard += 1

    # 游标按束跳章：章 1 完成 → current_chapter == 3
    assert state.chapter_loop.current_chapter == 3, state.chapter_loop.current_chapter
    # planning/drafting 各恰一次（无 follower 重复派发）
    planning = [d for d in dispatched if d[0] == "shenbi-chapter-planning"]
    drafting = [d for d in dispatched if d[0] == "shenbi-chapter-drafting"]
    assert len(planning) == 1, planning
    assert len(drafting) == 1, drafting
    assert "chapters 1,2" in drafting[0][1]
    # 两章产物都在
    for n in (1, 2):
        assert (tmp_path / "chapters" / f"chapter-{n}.md").is_file()
