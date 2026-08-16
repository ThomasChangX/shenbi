"""T6 integration guard: a two-chapter loop cannot lose settled chapters (C3).

Audit F1104/F1105 shape: the dispatch write path used to write contract
``append_dedup`` targets as WHOLE FILES, so every chapter's state-settling
dispatch collapsed the cumulative truth files (chapter summaries, trend rows)
to that chapter's increment — chapter 1's row vanished the moment chapter 2
settled. Task 2/5 routed these writes through the truth_io keyed upsert
(``_route_append_dedup_write``). These tests are the REGRESSION GUARD for that
fix: a simulated two-chapter loop must leave one row per completed chapter in
``truth/chapter_summaries.md`` and ``truth/resonance_trend.md``, and the row
count must grow MONOTONICALLY (chapter 1's row survives chapter 2's write).

Integration scope — the ONLY stubbed boundary is the LLM itself
(``_call_llm_streaming_with_retry`` returns canned per-chapter increments).
Everything downstream runs REAL: contract loading (``load_contract``), prompt
building (``_build_skill_prompt`` — output paths come from the live frontmatter
contract), response parsing, ``_write_parsed_outputs``,
``_route_append_dedup_write``, the staging merge against the live file,
``commit_staging``, and the truth_io keyed upsert. Stubbing the write path
would defeat the guard's purpose.

Guard validity (verified while developing, see task-6-report.md): against the
pre-routing BASE commit 7de2360 these tests FAIL — chapter 2's whole-file
staging commit leaves 1 row instead of 2 (F1104/F1105 recurrence caught);
short-circuiting ``_route_append_dedup_write`` to the legacy whole-file write
on current HEAD fails all four loop tests the same way.

Fixture policy (G0.9): the "loop continues from real prior state" test seeds
live truth files from REAL skill outputs under ``tests/fixtures/``.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from shenbi.contracts import load_contract
from shenbi.pipeline.chapter_loop import _build_resonance_trend_row
from shenbi.pipeline.checkpoint import commit_staging
from shenbi.pipeline.dispatch_helper import DispatchResult, _dispatch_via_api

FIXTURES = Path("tests/fixtures")

#: state-settling's full staging surface, MECHANICALLY DERIVED from the live
#: frontmatter contract (writes + updates, declaration order preserved). The
#: production STATE_SETTLE checkpoint commit actually globs whatever is staged
#: under ``staging/truth/*.md`` (pipeline/cli.py), so the contract is the only
#: non-hand-maintained source for the full declared surface.
_SETTLING_CONTRACT = load_contract("shenbi-state-settling")
_SETTLING_TARGETS = [*_SETTLING_CONTRACT["writes"], *_SETTLING_CONTRACT["updates"]]

#: Real ch1 truth outputs (G0.9) used to seed the "continuing loop" scenario.
_PRIOR_STATE_FIXTURES = {
    "truth/chapter_summaries.md": "truth-chapter_summaries.md",
    "truth/current_state.md": "truth-current_state.md",
    "truth/particle_ledger.md": "truth-particle_ledger.md",
    "truth/emotional_arcs.md": "truth-emotional_arcs.md",
    "truth/pending_hooks.md": "truth-pending_hooks.md",
}

_SEPARATOR_ROW_RE = re.compile(r"^\|(\s*:?-{3,}:?\s*\|)+$")


def _data_rows(path: Path) -> list[str]:
    """Markdown TABLE data rows in *path* (``|``-delimited, separators excluded)."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").split("\n")
        if line.strip().startswith("|") and not _SEPARATOR_ROW_RE.match(line.strip())
    ]


class _FakeLLM:
    """Canned LLM at the streaming-call seam: pops one response per dispatch.

    The responses are the per-chapter INCREMENTS the skills are contractually
    supposed to emit (append_dedup targets get only the new chapter's rows) —
    exactly what a well-behaved LLM returns under the Task-2 output contract.
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def __call__(
        self, client: object, model: str, messages: list[dict[str, str]], **kwargs: object
    ):
        self.calls += 1
        return (self._responses.pop(0), None, None, "stop")


def _settle_response(chapter: int) -> str:
    """state-settling's staged output for one chapter: whole-file write for the
    ``create_or_overwrite`` target, one increment row per append_dedup target
    (row formats per the skill's documented Row format rule).
    """
    return (
        f"### FILE: staging/truth/character_matrix.md\n"
        f"# 角色矩阵\n\n第 {chapter} 章出场：林烽\n\n"
        f"### FILE: staging/truth/current_state.md\n"
        f"| 第 {chapter} 章 | 位置{chapter}；状态增量{chapter} |\n"
        f"### FILE: staging/truth/particle_ledger.md\n"
        f"| 第 {chapter} 章 | 银盾 -{chapter} |\n"
        f"### FILE: staging/truth/emotional_arcs.md\n"
        f"| 第 {chapter} 章 | 情绪弧增量{chapter} |\n"
        f"### FILE: staging/truth/subplot_board.md\n"
        f"| 第 {chapter} 章 | 线索{chapter} 推进 |\n"
        f"### FILE: staging/truth/pending_hooks.md\n"
        f"| hook-ch{chapter}-001 | GENUINE | STRUCTURAL | 0.6 | RISING | {chapter} | plant | PLANTED |\n"
        f"### FILE: staging/truth/chapter_summaries.md\n"
        f"| 第 {chapter} 章 | 第{chapter}章摘要：穿越负债开局后的推进{chapter} |\n"
    )


def _resonance_response(chapter: int, overall: int) -> str:
    """review-resonance's output for one chapter.

    M1 NOTE (T5 review, key-format drift): resonance_trend has TWO writers —
    this skill (LLM increment) and chapter_loop's programmatic
    post-review persistence (``_build_resonance_trend_row``), both keyed by
    the first cell. The skill's SKILL.md example shows a bare-``N`` first
    cell while the programmatic writer uses ``Ch{N}``; mixing the two formats
    would produce TWO rows for the same chapter (distinct keys — the exact M1
    drift T3 will收口). This guard pins the SINGLE ``Ch{N}`` format — the one
    the authoritative post-review writer uses — and asserts one row per
    chapter under that consistent key format.
    """
    return (
        f"### FILE: audits/chapter-{chapter}-resonance.md\n"
        f"# 第 {chapter} 章共鸣评分\n\n**Resonance Score**: {overall}\n"
        f"### FILE: truth/audit_drift.md\n"
        f"- [文笔质感] 第 {chapter} 章短板观测{chapter} → 下章 PRE_WRITE_CHECK 防范建议\n"
        f"### FILE: truth/resonance_trend.md\n"
        f"{_build_resonance_trend_row(chapter, overall)}\n"
    )


def _install_fake_llm(monkeypatch: pytest.MonkeyPatch, responses: list[str]) -> _FakeLLM:
    fake = _FakeLLM(responses)
    monkeypatch.setattr("shenbi.pipeline.dispatch_helper._call_llm_streaming_with_retry", fake)
    monkeypatch.setenv("SHENBI_LLM_API_KEY", "test-key")
    return fake


def _settle_chapter(monkeypatch: pytest.MonkeyPatch, project: Path, chapter: int) -> None:
    """One loop iteration's state-settling leg: staged dispatch + commit."""
    result = _dispatch_via_api(
        "shenbi-state-settling",
        project,
        f"settle truth files after drafting chapter {chapter}",
        uses_staging=True,
    )
    assert isinstance(result, DispatchResult)
    assert result.success, f"state-settling dispatch failed for chapter {chapter}: {result.stderr}"
    commit_staging(project, _SETTLING_TARGETS)


def _resonance_chapter(
    monkeypatch: pytest.MonkeyPatch, project: Path, chapter: int, overall: int
) -> None:
    """One loop iteration's review leg: resonance dispatch + the programmatic
    post-review trend-row persistence (the second resonance_trend writer).
    """
    result = _dispatch_via_api(
        "shenbi-review-resonance",
        project,
        f"score chapter {chapter} for emotional landing and reader reward",
    )
    assert isinstance(result, DispatchResult)
    assert result.success, (
        f"review-resonance dispatch failed for chapter {chapter}: {result.stderr}"
    )

    from shenbi.pipeline.truth_io import write_truth_file

    write_truth_file(
        project,
        "resonance_trend.md",
        _build_resonance_trend_row(chapter, overall),
        mode="upsert_markdown_row",
        key_field="chapter",
    )


class TestTwoChapterLoopFromFreshProject:
    """Fresh (genesis-just-finished) project: chapters 1 and 2 run the
    settle→commit→review loop. Every cumulative truth file must carry exactly
    one row per completed chapter, and rows must NEVER disappear.
    """

    def test_row_count_equals_completed_chapters_and_grows_monotonically(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_fake_llm(
            monkeypatch,
            [
                _settle_response(1),
                _resonance_response(1, 82),
                _settle_response(2),
                _resonance_response(2, 87),
            ],
        )

        _settle_chapter(monkeypatch, tmp_project, 1)
        _resonance_chapter(monkeypatch, tmp_project, 1, 82)

        summaries = tmp_project / "truth" / "chapter_summaries.md"
        trend = tmp_project / "truth" / "resonance_trend.md"
        assert summaries.exists() and trend.exists()

        # After chapter 1: exactly one row per file.
        rows_after_ch1 = _data_rows(summaries)
        trend_after_ch1 = _data_rows(trend)
        assert len(rows_after_ch1) == 1, f"expected 1 summary row, got {rows_after_ch1}"
        assert len(trend_after_ch1) == 1, f"expected 1 trend row, got {trend_after_ch1}"

        _settle_chapter(monkeypatch, tmp_project, 2)
        _resonance_chapter(monkeypatch, tmp_project, 2, 87)

        # After chapter 2: exactly two rows per file — chapter 1's rows are
        # STILL THERE (monotonic growth; the old whole-file write collapsed
        # both files to chapter 2's increment — the F1104/F1105 recurrence).
        rows_after_ch2 = _data_rows(summaries)
        trend_after_ch2 = _data_rows(trend)
        assert len(rows_after_ch2) == 2, f"expected 2 summary rows, got {rows_after_ch2}"
        assert len(trend_after_ch2) == 2, f"expected 2 trend rows, got {trend_after_ch2}"
        assert rows_after_ch1[0] in rows_after_ch2, "chapter 1 summary row lost on chapter 2 write"
        assert trend_after_ch1[0] in trend_after_ch2, "chapter 1 trend row lost on chapter 2 write"

        assert any("第 1 章" in r for r in rows_after_ch2)
        assert any("第 2 章" in r for r in rows_after_ch2)
        # Keyed rows, one per chapter key (crash-retry safe).
        assert sum(1 for r in rows_after_ch2 if r.startswith("| 第 1 章 |")) == 1
        assert sum(1 for r in rows_after_ch2 if r.startswith("| 第 2 章 |")) == 1

        # audit_drift increments accumulate too (block-style appends merged by
        # drift-guidance later): chapter 1's increment survives chapter 2's.
        drift = (tmp_project / "truth" / "audit_drift.md").read_text(encoding="utf-8")
        assert "短板观测1" in drift and "短板观测2" in drift

    def test_resonance_trend_one_row_per_chapter_despite_two_writers(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The M1 invariant from the write-path side: the skill increment and
        the programmatic post-review writer share the ``Ch{N}`` key, so a
        chapter gets exactly ONE row even though two writers touch the file
        per loop iteration. (Key-format drift between the two writers is the
        M1 risk — pinned here under a single consistent format.)
        """
        _install_fake_llm(
            monkeypatch,
            [
                _settle_response(1),
                _resonance_response(1, 82),
                _settle_response(2),
                _resonance_response(2, 87),
            ],
        )
        for chapter, score in ((1, 82), (2, 87)):
            _settle_chapter(monkeypatch, tmp_project, chapter)
            _resonance_chapter(monkeypatch, tmp_project, chapter, score)

        trend_rows = _data_rows(tmp_project / "truth" / "resonance_trend.md")
        assert len(trend_rows) == 2
        assert sum(1 for r in trend_rows if r.startswith("| Ch1 |")) == 1
        assert sum(1 for r in trend_rows if r.startswith("| Ch2 |")) == 1

    def test_all_row_keyed_settling_targets_accumulate(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The same guard extended to the remaining row-keyed append_dedup
        targets state-settling owns (chapter_summaries is already covered by
        the loop test above; character_matrix is create_or_overwrite and thus
        not row-keyed): chapter 1's increment survives chapter 2's
        settle+commit in all five row-keyed truth files (pending_hooks keyed
        by hook id).
        """
        _install_fake_llm(monkeypatch, [_settle_response(1), _settle_response(2)])
        _settle_chapter(monkeypatch, tmp_project, 1)
        _settle_chapter(monkeypatch, tmp_project, 2)

        for rel in (
            "truth/current_state.md",
            "truth/particle_ledger.md",
            "truth/emotional_arcs.md",
            "truth/subplot_board.md",
        ):
            rows = _data_rows(tmp_project / rel)
            assert len(rows) == 2, f"{rel}: expected one row per completed chapter, got {rows}"
            assert any("第 1 章" in r for r in rows), f"{rel}: chapter 1 row lost"

        hooks = (tmp_project / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert "hook-ch1-001" in hooks, "chapter 1 hook row lost on chapter 2 write"
        assert "hook-ch2-001" in hooks


class TestLoopContinuesFromRealPriorState:
    """The loop resumes on a project whose truth files are REAL chapter-1
    skill outputs (G0.9 fixtures): chapter 2's settle+commit must MERGE into
    them, never replace them.
    """

    def test_chapter2_merges_into_real_chapter1_truth(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seeded: dict[str, str] = {}
        for rel, fixture in _PRIOR_STATE_FIXTURES.items():
            src = FIXTURES / fixture
            if not src.exists():
                pytest.skip(f"fixture not available: {src}")
            dst = tmp_project / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            seeded[rel] = dst.read_text(encoding="utf-8")

        _install_fake_llm(monkeypatch, [_settle_response(2), _resonance_response(2, 87)])
        _settle_chapter(monkeypatch, tmp_project, 2)
        _resonance_chapter(monkeypatch, tmp_project, 2, 87)

        # Every real prior-state file is preserved under the chapter 2 write —
        # a whole-file staging commit would have replaced them with the bare
        # chapter 2 increment (F1104 data loss on real data).
        for rel, pre in seeded.items():
            post = (tmp_project / rel).read_text(encoding="utf-8")
            assert pre.strip() in post, f"{rel}: real chapter-1 content lost on chapter 2 write"

        summaries = (tmp_project / "truth" / "chapter_summaries.md").read_text(encoding="utf-8")
        assert "第1章：毕业即失业与穿越即负债" in summaries
        assert "| 第 2 章 |" in summaries
        assert "穿越负债开局后的推进2" in summaries

        trend_rows = _data_rows(tmp_project / "truth" / "resonance_trend.md")
        assert len(trend_rows) == 1  # fresh file, chapter 2 only in this scenario
        assert trend_rows[0].startswith("| Ch2 |")
