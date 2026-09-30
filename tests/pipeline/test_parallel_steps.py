"""Test parallel execution of foreshadowing-lifecycle and state-settling.

Uses the single-writer (actor-model) pattern: workers return dict results,
the main thread merges. No _state_lock.
"""

import inspect
from unittest.mock import MagicMock, patch

from shenbi.pipeline.chapter_loop import run_parallel_post_draft_steps
from shenbi.pipeline.state import PipelineState


class TestParallelPostDraft:
    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_post_draft_steps_sequential_in_order(self, mock_dispatch):
        """Post-draft steps run SEQUENTIALLY, lifecycle before settling.

        9be872df (canary escalation #16) replaced parallel execution: both
        steps ``append_dedup``-update ``truth/pending_hooks.md`` through
        staging whose merge base is the LIVE file — in parallel the two
        staging writers race last-writer-wins and lock contention could kill
        a worker before its dispatch. This replaces the F745 barrier test,
        which asserted true overlap and can never pass against the
        sequential design (first barrier waiter times out alone).
        """
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 3

        lifecycle_result, settling_result = run_parallel_post_draft_steps(state)

        assert lifecycle_result.success and settling_result.success
        skills_called = [c.args[0] for c in mock_dispatch.call_args_list]
        assert skills_called == [
            "shenbi-foreshadowing-lifecycle",
            "shenbi-state-settling",
        ], "settling must run AFTER lifecycle so its staging merge base "
        "includes lifecycle's landed pending_hooks increment"

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_lifecycle_failure_isolated_from_settling(self, mock_dispatch):
        """Lifecycle failure is logged but does not block state-settling."""

        def side_effect(skill, project_dir, prompt, **kwargs):
            result = MagicMock()
            if skill == "shenbi-foreshadowing-lifecycle":
                result.success = False
                result.result = {}
                result.stdout = ""
                result.stderr = "mock lifecycle failure"
                result.returncode = 1
            else:
                result.success = True
                result.result = {}
            return result

        mock_dispatch.side_effect = side_effect
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 3

        # Should not raise; lifecycle failure is logged but does not
        # block state-settling from succeeding.
        run_parallel_post_draft_steps(state)

        # Both were dispatched
        assert mock_dispatch.call_count == 2

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_state_settling_failure_handled(self, mock_dispatch):
        """State-settling failure is reported in results (caller handles escalation)."""

        def side_effect(skill, project_dir, prompt, **kwargs):
            result = MagicMock()
            if skill == "shenbi-state-settling":
                result.success = False
                result.result = {}
                result.stdout = ""
                result.stderr = "mock settling failure"
                result.returncode = 1
            else:
                result.success = True
                result.result = {}
            return result

        mock_dispatch.side_effect = side_effect
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 3

        lifecycle_result, settling_result = run_parallel_post_draft_steps(state)
        assert lifecycle_result.success
        assert not settling_result.success

    def test_state_merged_on_main_thread_single_writer(self):
        """Workers return dict results; the main thread merges to PipelineState.

        No _state_lock should exist -- this is the actor-model pattern.
        """
        from shenbi.pipeline import state as state_mod

        src = inspect.getsource(state_mod)
        # The single-writer pattern forbids a module-level _state_lock
        assert "_state_lock" not in src, (
            "Use single-writer (actor-model), NOT _state_lock (Spec 6 §3.4)"
        )
        # F745 behavioral complement: state mutations happen only on the
        # calling (main) thread — the workers' results are merged after
        # future.result() returns (chapter_loop.py "merge on the main thread
        # ONLY"). The textual grep above cannot see call-site discipline;
        # this pins the observable contract: after run_parallel_post_draft_steps
        # returns, both steps' results are merged into the state.
        import threading as _threading

        from shenbi.pipeline.state import _merge_step_result

        merge_thread_ids: list[int] = []
        real_merge = _merge_step_result

        def tracking_merge(*a, **k):
            merge_thread_ids.append(_threading.get_ident())
            return real_merge(*a, **k)

        with patch("shenbi.pipeline.state._merge_step_result", tracking_merge):
            state = PipelineState.default("/tmp/test-project")
            state.chapter_loop.current_chapter = 4
            run_parallel_post_draft_steps(state)
        main_id = _threading.get_ident()
        assert merge_thread_ids and all(tid == main_id for tid in merge_thread_ids), (
            "state merges must happen on the calling thread only (single-writer)"
        )


class TestConsolidateAttribution:
    """Canary 聚合器漏并 + probe vacuous zero-findings: the consolidator
    scanned only result.stdout — the actual review artifacts are the
    audits/chapter-N-*.md FILES, whose stdout is usually empty, so BLOCKING
    findings in the files never reached the summary; results were anonymous
    ('Review #3'); cascade-skipped audits were undisclosed.
    """

    def test_consolidate_reads_audit_files_and_names_skills(self, tmp_path):
        from shenbi.pipeline.parallel_dispatch import consolidate_review_results

        (tmp_path / "audits").mkdir()
        # a review whose stdout is EMPTY but whose audit FILE carries BLOCKING
        (tmp_path / "audits" / "chapter-5-pacing.md").write_text(
            "# Pacing review\n\n**严重度**: BLOCKING\n\n第 5 章节奏崩溃。\n",
            encoding="utf-8",
        )

        from unittest.mock import MagicMock

        r = MagicMock()
        r.success = True
        r.stdout = ""

        summary = consolidate_review_results(
            [r],
            5,
            skills=["shenbi-review-pacing"],
            project_dir=tmp_path,
            cascade_skipped=["shenbi-review-group-craft"],
        )
        assert "shenbi-review-pacing" in summary, "issues must be attributable to a skill"
        assert "BLOCKING" in summary and "节奏崩溃" in summary, (
            "audit-file findings must reach the summary even with empty stdout"
        )
        assert "cascade-skipped" in summary, "skipped audits must be disclosed"

    def test_consolidate_stdout_still_scanned(self):
        from unittest.mock import MagicMock

        from shenbi.pipeline.parallel_dispatch import consolidate_review_results

        r = MagicMock()
        r.success = True
        r.stdout = "BLOCKING continuity break at L40"

        summary = consolidate_review_results([r], 5, skills=["shenbi-review-continuity"])
        assert "continuity break" in summary
        assert "shenbi-review-continuity" in summary


def test_parallel_worker_exception_persists_stack(tmp_path, monkeypatch):
    """Canary #16 + probe recurrence '派发前死亡无栈迹': a worker exception
    was logged as error=str(exc) with NO stack — the death was undiagnosable
    from the project dir. The stack must be persisted to diagnostics/.
    """
    from shenbi.pipeline.parallel_dispatch import ReviewTask, dispatch_reviews_parallel

    def boom(client, model, messages, **kwargs):
        raise RuntimeError("pre-dispatch lock contention death")

    # route through the API path so _call_llm_streaming_with_retry is used
    monkeypatch.setattr("shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry", boom)
    monkeypatch.setattr("shenbi.pipeline.dispatch_helper._dispatch_via_api", boom)
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")

    task = ReviewTask(
        skill="shenbi-review-pacing",
        project_dir=tmp_path,
        prompt="x",
        output_path="audits/chapter-1-pacing.md",
    )
    # force retries to 1 for speed
    import shenbi.pipeline.parallel_dispatch as pd

    monkeypatch.setattr(pd, "MAX_RETRIES", 0)
    results = dispatch_reviews_parallel([task])
    dumps = list((tmp_path / "diagnostics").glob("worker-death-*.md"))
    assert dumps, "worker death must persist a stack dump"
    content = dumps[0].read_text(encoding="utf-8")
    assert "Traceback" in content or "runtime" in content.lower()
    assert results and not results[0].success


class TestParallelRetryFeedbackWire:
    """Fixcheck escalation ch1 (2026-09-29): the parallel post-draft path ran
    blind retries — its G4 failure site stored no retry_feedback and its
    prompt builder injected none, so state-settling restructured
    character_matrix 3x (matrix_structure line_collapse) and escalated.
    """

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_retry_prompt_carries_g4_corrective_feedback(self, mock_dispatch):
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.retry_feedback["ch1-shenbi-state-settling"] = (
            "G4.ss.matrix_structure:character_matrix.md:line_collapse:staged=22<live*0.9=73"
        )

        run_parallel_post_draft_steps(state)

        settling_call = mock_dispatch.call_args_list[1]
        settling_prompt = settling_call.args[2]
        assert "CORRECTIVE FEEDBACK" in settling_prompt
        assert "matrix_structure" in settling_prompt
        # the lifecycle prompt must NOT carry the settling feedback
        lifecycle_prompt = mock_dispatch.call_args_list[0].args[2]
        assert "matrix_structure" not in lifecycle_prompt

    @patch("shenbi.pipeline.chapter_loop.dispatch_skill")
    def test_modify_feedback_injected_and_consumed_once(self, mock_dispatch):
        state = PipelineState.default("/tmp/test-project")
        state.chapter_loop.current_chapter = 1
        state.chapter_loop.modify_feedback = "改用送灯回铺收尾"

        run_parallel_post_draft_steps(state)

        prompts = [c.args[2] for c in mock_dispatch.call_args_list]
        assert sum("Human review feedback" in p for p in prompts) == 1
        assert state.chapter_loop.modify_feedback is None


class TestSeverityVocabularySensing:
    """Fixcheck ch1 (2026-09-29): audit skills emitted the template's
    ``- [ERROR]`` labels while every sensor matched only BLOCKING/CRITICAL —
    the summary reported a false zero and revision routing never fired.
    Sensors must see both the enums vocabulary and the legacy [ERROR] form,
    and skill templates must not reintroduce the drifted labels.
    """

    def test_consolidate_senses_bracket_and_error_labels(self, tmp_path):
        from unittest.mock import MagicMock

        from shenbi.pipeline.parallel_dispatch import consolidate_review_results

        (tmp_path / "audits").mkdir()
        (tmp_path / "audits" / "chapter-3-continuity.md").write_text(
            "# Continuity\n\n### 建议修复\n"
            "- [BLOCKING] L155 算术矛盾：改价码。\n"
            "- [ERROR] L200 地点分叉：以正文为准。\n",
            encoding="utf-8",
        )
        r = MagicMock()
        r.success = True
        r.stdout = ""
        summary = consolidate_review_results(
            [r], 3, skills=["shenbi-review-continuity"], project_dir=tmp_path
        )
        assert "shenbi-review-continuity" in summary
        assert "算术矛盾" in summary, "[BLOCKING] bracket form must be sensed"
        assert "地点分叉" in summary, "legacy [ERROR] label must be sensed"

    def test_cascade_marker_re_senses_bracket_and_error(self):
        from shenbi.pipeline.chapter_loop import _BLOCKING_MARKER_RE

        assert _BLOCKING_MARKER_RE.search("- [BLOCKING] L10 问题：修\n")
        assert _BLOCKING_MARKER_RE.search("- [ERROR] L20 问题：修\n")
        assert _BLOCKING_MARKER_RE.search("- [CRITICAL] L30 问题：修\n")
        assert not _BLOCKING_MARKER_RE.search("- [MINOR] L40 建议：润色\n")

    def test_review_skill_templates_use_enums_vocabulary(self):
        """Regression guard: no review skill template may emit [ERROR] /
        [WARNING] labels — the sensing chain matches the enums vocabulary
        (BLOCKING/CRITICAL/MINOR) plus the legacy [ERROR] alias only.
        """
        import re
        from pathlib import Path

        root = Path(__file__).resolve().parents[2] / "skills"
        drifted = []
        for skill_md in sorted(root.glob("shenbi-review-*/SKILL.md")):
            for lineno, line in enumerate(skill_md.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"-\s*\[(?:ERROR|WARNING)\]", line):
                    drifted.append(f"{skill_md.relative_to(root)}:{lineno}")
        assert not drifted, f"drifted severity labels in templates: {drifted}"


def test_wave_failed_group_not_marked_done_and_real_paths_recorded(tmp_path, monkeypatch):
    """Fixcheck ch2 zero-coverage silence: the character audit group's
    dispatch failed (length truncation, 3 retries exhausted), yet the wave
    completion marked its step done (resume never re-dispatches) and
    audit_reports pointed at the phantom audits/chapter-2-group-character.md.
    A failed audit must stay un-done for crash-resume replay, and the
    recorded paths must be the skill's real contract writes.
    """
    from types import SimpleNamespace
    from unittest.mock import patch

    import pytest  # noqa: F401  (marker below)

    from shenbi.pipeline import chapter_loop as cl
    from shenbi.pipeline.state import PipelineState

    (tmp_path / "audits").mkdir()
    (tmp_path / "genre-config.json").write_text("{}", encoding="utf-8")

    GROUP = "shenbi-review-group-character"

    class _R:
        def __init__(self, ok: bool) -> None:
            self.success = ok
            self.returncode = 0 if ok else -1
            self.stdout = ""
            self.stderr = "length_truncation: output still exceeds raised cap"

    def _results_for(tasks):
        return [_R(t.skill != GROUP) for t in tasks]

    state = PipelineState()
    state.project_dir = str(tmp_path)
    state.chapter_loop.current_chapter = 2
    idx = cl._FIRST_AUDIT_IDX
    state.chapter_loop.step_index = idx

    with (
        patch(
            "shenbi.pipeline.audit_context_cache.build_shared_audit_context",
            return_value=SimpleNamespace(
                estimated_tokens=0,
                raw_files={},
                world_rules="",
                character_list="",
                style_profile="",
                pending_hooks="",
            ),
        ),
        patch("shenbi.pipeline.audit_layer.get_active_genre_audits", return_value=[]),
        patch(
            "shenbi.pipeline.parallel_dispatch.dispatch_reviews_parallel",
            side_effect=lambda tasks, on_task_complete=None: _results_for(tasks),
        ),
        patch.object(
            cl, "_dispatch_serial_reviews", side_effect=lambda tasks, pd: _results_for(tasks)
        ),
        patch.object(cl, "_parse_and_persist_resonance"),
        patch.object(cl, "_route_revision_after_resonance"),
    ):
        cl.run_chapter_step(state, tmp_path)

    cs = state.chapter_loop.chapter_states.get("2")
    assert cs is not None
    # 1. the failed group is NOT marked done (crash-resume can replay it)
    assert GROUP not in cs.steps_done, cs.steps_done
    # successful audit skills still are
    assert "shenbi-review-group-factual" in cs.steps_done
    # 2. audit_reports carries the four real contract writes, not the phantom
    reports = cs.audit_results.get("audit_reports", [])
    assert "audits/chapter-2-group-character.md" not in reports, reports
    assert "audits/chapter-2-character.md" in reports, reports
    assert "audits/chapter-2-pov.md" in reports, reports
    # 3. per-skill failure disclosed as before
    assert cs.audit_results.get("group-character", {}).get("passed") is False
