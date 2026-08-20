"""Tests for contract-driven write semantics in _write_parsed_outputs (spec §3.3)."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.dispatch_helper import _write_parsed_outputs


class TestCreateOrOverwrite:
    def test_default_mode_overwrites(self, tmp_path: Path):
        """create_or_overwrite (and undeclared) -> safe_write, current behavior."""
        # NOTE: _parse_file_outputs expects the real marker format
        # "### FILE: <path>" (see dispatch_helper._parse_file_outputs).
        out = _write_parsed_outputs(
            response="### FILE: chapters/c-1.md\nnew body\n",
            output_paths=["chapters/c-1.md"],
            project_dir=tmp_path,
            skill="shenbi-chapter-drafting",
        )
        assert "chapters/c-1.md" in out
        assert "new body" in (tmp_path / "chapters" / "c-1.md").read_text()


class TestAppendDedupRoutedThroughTruthUpsert:
    """The generic dispatch write path ROUTES contract-declared append_dedup
    truth targets through the truth_io keyed upsert (C3 T2, F360/F828).

    The skill's output for such a target is the INCREMENT; the program merges
    it by the contract ``key:`` — the existing content survives instead of
    being overwritten by the increment (the old whole-file behavior collapsed
    cumulative truth files to the latest chapter's data). Full acceptance
    coverage (history preserved, double-chapter writes, hook_id keys, staging
    merge, fail-loud) lives in test_dispatch_append_dedup_wiring.py; this test
    pins the routing switch itself.
    """

    def test_append_dedup_truth_file_merged_not_overwritten(self, tmp_path: Path):
        """A truth/ path declared mode: append_dedup keeps prior content and
        appends/merges the increment (upsert, not whole-file replace).
        """
        truth = tmp_path / "truth" / "current_state.md"
        truth.parent.mkdir(parents=True)
        truth.write_text("# Current State\n\n- chapter: ch0\n", encoding="utf-8")

        out = _write_parsed_outputs(
            response="### FILE: truth/current_state.md\n| 第 2 章 | 林烽进入内门 |\n",
            output_paths=["truth/current_state.md"],
            project_dir=tmp_path,
            skill="shenbi-state-settling",
        )
        assert "truth/current_state.md" in out
        result = truth.read_text(encoding="utf-8")
        # Prior content survives the increment write (was: whole-file replace).
        assert "# Current State" in result
        assert "- chapter: ch0" in result
        # The increment landed.
        assert "| 第 2 章 | 林烽进入内门 |" in result


class TestNoOpSkipWrite:
    def test_skip_write_paths_not_written(self, tmp_path: Path):
        """A path in skip_paths is not written even if content is present."""
        out = _write_parsed_outputs(
            response="### FILE: chapters/c-1.md\nbody\n",
            output_paths=["chapters/c-1.md"],
            project_dir=tmp_path,
            skill="shenbi-chapter-revision",
            skip_paths={"chapters/c-1.md"},
        )
        assert out == []
        assert not (tmp_path / "chapters" / "c-1.md").exists()
