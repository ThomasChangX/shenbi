"""T2 wiring tests: dispatch routes ``append_dedup`` to truth_io upsert (C3).

Audit F360/F828: contract updates declared ``mode: append_dedup`` were written
as WHOLE FILES by ``_write_parsed_outputs`` — cumulative truth data (chapter
summaries, trend rows, hook rows) collapsed to the last chapter's increment on
every dispatch. These tests pin the routed behavior:

- a dispatched increment merges by key; historical rows survive;
- two chapters written in sequence leave both rows present;
- ``hook_id``-keyed rows dedup on the Hook ID column (normalized header);
- staging truth writes (state-settling) merge against the LIVE file as base
  and leave the live file untouched until the staging commit;
- a corrupt existing truth file fails loud (TruthFileParseError propagates)
  instead of being silently collapsed.

Fixture policy (G0.9): seeds copy REAL skill outputs from ``tests/fixtures/``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from shenbi.exceptions import TruthFileParseError
from shenbi.pipeline.dispatch_helper import _write_parsed_outputs

FIXTURES = Path("tests/fixtures")


def _seed_from_fixture(tmp_path: Path, rel_path: str, fixture_name: str) -> None:
    """Seed ``tmp_path/<rel_path>`` from a real fixture file (G0.9)."""
    src = FIXTURES / fixture_name
    if not src.exists():
        pytest.skip(f"fixture not available: {src}")
    dst = tmp_path / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


class TestChapterSummariesHistoryPreserved:
    """Acceptance: one chapter of state-settling writing chapter_summaries —
    the historical chapter content must still be there after the write.
    """

    def test_new_chapter_row_appended_history_preserved(self, tmp_path: Path):
        """Real chapter_summaries fixture (ch1 settled) + dispatched ch2 row:
        ch1 content survives, ch2 row appears (old path overwrote whole file).
        """
        _seed_from_fixture(tmp_path, "truth/chapter_summaries.md", "truth-chapter_summaries.md")

        out = _write_parsed_outputs(
            response=(
                "### FILE: truth/chapter_summaries.md\n"
                "| 第 2 章 | 林烽开始修炼灵能呼吸法，初次引导灵能流经经脉。 |\n"
            ),
            output_paths=["truth/chapter_summaries.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )

        assert "truth/chapter_summaries.md" in out
        result = (tmp_path / "truth" / "chapter_summaries.md").read_text(encoding="utf-8")
        # Historical chapter 1 content survives the chapter 2 write.
        assert "第1章：毕业即失业与穿越即负债" in result, "ch1 section deleted by ch2 write"
        assert "毕业即失业" in result
        # The new chapter 2 row landed.
        assert "| 第 2 章 |" in result
        assert "灵能呼吸法" in result

    def test_two_chapter_writes_both_rows_present(self, tmp_path: Path):
        """Acceptance (double-write): dispatching ch1 then ch2 rows leaves BOTH
        rows in chapter_summaries.
        """
        for chapter, summary in ((1, "穿越负债开局"), (2, "初次修炼突破")):
            out = _write_parsed_outputs(
                response=(
                    f"### FILE: truth/chapter_summaries.md\n| 第 {chapter} 章 | {summary} |\n"
                ),
                output_paths=["truth/chapter_summaries.md"],
                project_dir=tmp_path,
                skill="shenbi-state-settling",
            )
            assert "truth/chapter_summaries.md" in out

        result = (tmp_path / "truth" / "chapter_summaries.md").read_text(encoding="utf-8")
        assert "| 第 1 章 | 穿越负债开局 |" in result
        assert "| 第 2 章 | 初次修炼突破 |" in result

    def test_re_dispatch_same_chapter_replaces_not_duplicates(self, tmp_path: Path):
        """Re-running the same chapter (crash-retry) replaces its row in place
        — exactly one row per chapter key.
        """
        row = "| 第 2 章 | 初版摘要 |"
        _write_parsed_outputs(
            response=f"### FILE: truth/chapter_summaries.md\n{row}\n",
            output_paths=["truth/chapter_summaries.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )
        _write_parsed_outputs(
            response="### FILE: truth/chapter_summaries.md\n| 第 2 章 | 修订摘要 |\n",
            output_paths=["truth/chapter_summaries.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )

        result = (tmp_path / "truth" / "chapter_summaries.md").read_text(encoding="utf-8")
        assert result.count("| 第 2 章 |") == 1
        assert "修订摘要" in result
        assert "初版摘要" not in result


class TestResonanceTrendDoubleChapter:
    """Acceptance alternative: resonance_trend double-chapter write via the
    review-resonance contract (updates append_dedup, key: chapter).
    """

    def test_two_chapter_rows_both_present(self, tmp_path: Path):
        for chapter, score in ((1, 82), (2, 87)):
            _write_parsed_outputs(
                response=(
                    "### FILE: truth/resonance_trend.md\n"
                    f"| Ch{chapter} | - | - | - | - | - | {score} |\n"
                ),
                output_paths=["truth/resonance_trend.md"],
                project_dir=tmp_path,
                skill="shenbi-review-resonance",
            )

        result = (tmp_path / "truth" / "resonance_trend.md").read_text(encoding="utf-8")
        assert "| Ch1 | - | - | - | - | - | 82 |" in result
        assert "| Ch2 | - | - | - | - | - | 87 |" in result


class TestPendingHooksKeyedByHookId:
    """pending_hooks declares append_dedup key: hook_id — rows dedup on the
    Hook ID column of the real 活跃伏笔 table.
    """

    def test_new_hook_row_merges_without_dropping_existing_hooks(self, tmp_path: Path):
        _seed_from_fixture(tmp_path, "truth/pending_hooks.md", "truth-pending_hooks.md")

        _write_parsed_outputs(
            response=(
                "### FILE: truth/pending_hooks.md\n"
                "| hook-ch2-001 | GENUINE | STRUCTURAL | 0.60 | RISING | 2 | plant | PLANTED |\n"
            ),
            output_paths=["truth/pending_hooks.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )

        result = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        # All three existing hooks survive.
        for hook in ("hook-ch1-001", "hook-ch1-002", "hook-ch1-003"):
            assert hook in result, f"existing hook {hook} deleted by new-chapter write"
        # The new hook landed.
        assert "hook-ch2-001" in result

    def test_same_hook_id_replaced_exactly_once(self, tmp_path: Path):
        _seed_from_fixture(tmp_path, "truth/pending_hooks.md", "truth-pending_hooks.md")

        row = "| hook-ch1-001 | GENUINE | THEMATIC | 0.45 | RISING | 1 | reinforce | RELEVANT |"
        _write_parsed_outputs(
            response=f"### FILE: truth/pending_hooks.md\n{row}\n",
            output_paths=["truth/pending_hooks.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )

        result = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert result.count("hook-ch1-001") >= 1  # table row + hooks record section
        assert "RELEVANT" in result
        # The old PLANTED table row for this hook is replaced, not duplicated:
        # count pipe-delimited table rows mentioning the hook id.
        table_rows = [
            ln for ln in result.split("\n") if ln.startswith("|") and "hook-ch1-001" in ln
        ]
        assert len(table_rows) == 1
        assert "REINFORCE" in table_rows[0].upper()

    def test_multiple_new_hooks_one_dispatch_all_merge(self, tmp_path: Path):
        """A multi-row increment (two hooks planted in one chapter) merges row
        by row — the whole blob is not treated as one garbage-key row.
        """
        _seed_from_fixture(tmp_path, "truth/pending_hooks.md", "truth-pending_hooks.md")

        _write_parsed_outputs(
            response=(
                "### FILE: truth/pending_hooks.md\n"
                "| hook-ch2-001 | GENUINE | STRUCTURAL | 0.60 | RISING | 2 | plant | PLANTED |\n"
                "| hook-ch2-002 | FALSE | CHARACTER | 0.30 | FLAT | 2 | plant | PLANTED |\n"
            ),
            output_paths=["truth/pending_hooks.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )

        result = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert "hook-ch2-001" in result
        assert "hook-ch2-002" in result
        # Re-dispatch the same two rows: still one table row per hook (dedup).
        _write_parsed_outputs(
            response=(
                "### FILE: truth/pending_hooks.md\n"
                "| hook-ch2-001 | GENUINE | STRUCTURAL | 0.60 | RISING | 2 | plant | PLANTED |\n"
                "| hook-ch2-002 | FALSE | CHARACTER | 0.30 | FLAT | 2 | plant | PLANTED |\n"
            ),
            output_paths=["truth/pending_hooks.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )
        result = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert (
            len([ln for ln in result.split("\n") if ln.startswith("|") and "hook-ch2-001" in ln])
            == 1
        )


class TestStagingTruthMerge:
    """state-settling dispatches with uses_staging=True write to
    staging/truth/*.md; the staging commit later replaces the live file.
    The routed write must merge the increment against the LIVE file as base so
    the whole-file commit stays safe, while leaving the live file untouched
    until commit (review gating).
    """

    def test_staged_write_contains_live_base_plus_increment(self, tmp_path: Path):
        _seed_from_fixture(tmp_path, "truth/chapter_summaries.md", "truth-chapter_summaries.md")
        live_before = (tmp_path / "truth" / "chapter_summaries.md").read_text(encoding="utf-8")

        _write_parsed_outputs(
            response=("### FILE: staging/truth/chapter_summaries.md\n| 第 2 章 | 初次修炼突破 |\n"),
            output_paths=["staging/truth/chapter_summaries.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )

        staged = tmp_path / "staging" / "truth" / "chapter_summaries.md"
        assert staged.exists(), "staged truth file not written"
        staged_text = staged.read_text(encoding="utf-8")
        # The staged snapshot carries the live base (commit will not collapse it).
        assert "第1章：毕业即失业与穿越即负债" in staged_text
        assert "| 第 2 章 | 初次修炼突破 |" in staged_text
        # The live file is untouched until the staging commit (review gating).
        assert (tmp_path / "truth" / "chapter_summaries.md").read_text(
            encoding="utf-8"
        ) == live_before


class TestFailLoudOnCorruptTruthFile:
    """TruthFileParseError must propagate (fail-loud) rather than being
    swallowed — the dispatch layer converts it into a failed DispatchResult.
    """

    def test_parse_error_propagates_from_write_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        target = tmp_path / "truth" / "pending_hooks.md"
        target.parent.mkdir(parents=True)
        target.write_text("---\nhooks:\n  - id: [broken\n", encoding="utf-8")

        def _raise(*args: object, **kwargs: object) -> None:
            raise TruthFileParseError("truth file could not be parsed", path=str(target))

        monkeypatch.setattr("shenbi.pipeline.truth_io.write_truth_file", _raise)

        with pytest.raises(TruthFileParseError):
            _write_parsed_outputs(
                response=(
                    "### FILE: truth/pending_hooks.md\n"
                    "| hook-ch2-001 | GENUINE | STRUCTURAL | 0.6 | RISING | 2 | plant | PLANTED |\n"
                ),
                output_paths=["truth/pending_hooks.md"],
                project_dir=tmp_path,
                skill="shenbi-state-settling",
            )
        # Fail-loud leaves the corrupt file untouched for repair.
        assert "[broken" in target.read_text(encoding="utf-8")


class TestNonTruthAppendDedupFallback:
    """An append_dedup declaration on a non-truth path cannot route to
    truth_io — fall back to the legacy whole-file write (never crash).
    """

    def test_non_truth_path_falls_back_to_whole_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "shenbi.contracts.load_contract",
            lambda skill: {
                "kind": "artifact",
                "reads": [],
                "writes": [],
                "updates": [],
                "read_fields": {},
                "write_semantics": {"logs/append.md": {"mode": "append_dedup", "key": "chapter"}},
            },
        )
        out = _write_parsed_outputs(
            response="### FILE: logs/append.md\nrow-1\n",
            output_paths=["logs/append.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )
        # Unroutable declaration: falls back to whole-file write, still written.
        assert "logs/append.md" in out
        assert (tmp_path / "logs" / "append.md").read_text(encoding="utf-8") == "row-1"
