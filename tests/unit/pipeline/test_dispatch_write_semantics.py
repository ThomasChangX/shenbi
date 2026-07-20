"""Tests for contract-driven write semantics in _write_parsed_outputs (spec §3.3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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


class TestAppendDedupNotRoutedInDispatch:
    """The generic dispatch write path does NOT route append_dedup to
    write_truth_file. Truth-file append semantics are enforced at the caller
    (state-settling skill calls write_truth_file explicitly with a real key),
    NOT by fabricating a key from prose in the generic write path.

    Here a declared mode: append_dedup truth-file path is still written as a
    WHOLE FILE via safe_write — the contract declares the mode for G0.16, but
    the dispatch path does not interpret it as an upsert.
    """

    def test_append_dedup_truth_file_is_written_whole_not_upserted(self, tmp_path: Path):
        """A truth/ path declared mode: append_dedup is written as a whole file
        by _write_parsed_outputs (safe_write), NOT routed to write_truth_file.
        Upsert is the caller's (state-settling skill's) responsibility.
        """
        truth = tmp_path / "truth" / "current_state.md"
        truth.parent.mkdir(parents=True)
        truth.write_text("# Current State\n\n- chapter: ch0\n", encoding="utf-8")

        with patch("shenbi.pipeline.dispatch_helper.write_truth_file") as mock_wtf:
            mock_wtf.return_value = None
            out = _write_parsed_outputs(
                response="### FILE: truth/current_state.md\nrow\n",
                output_paths=["truth/current_state.md"],
                project_dir=tmp_path,
                skill="shenbi-state-settling",
            )
            # write_truth_file must NOT be invoked from the dispatch path.
            mock_wtf.assert_not_called()
            # The file is written whole instead.
            assert "truth/current_state.md" in out
            assert (tmp_path / "truth" / "current_state.md").read_text() == "row"


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
