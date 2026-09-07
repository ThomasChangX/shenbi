"""Branch coverage for dispatcher/cli.py main + executor failure/skip branches.

F216 (spec #53 C15): cli argv matrix (usage rc=1, F267 prompt join, rc
passthrough) and executor G1-fail / G2-fail / dispatch-failure / SHENBI_G1_SKIP_READS
filter branches. Seams are stubbed at module boundaries (run_g1/run_g2/detect_mode/
dispatch_internal); the logic under test is executor.dispatch itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import shenbi.dispatcher.cli as dcli
from shenbi.dispatcher import executor


@pytest.mark.unit
class TestCliMainArgvMatrix:
    def test_usage_returns_1_when_too_few_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["shenbi-dispatch", "only-two"])
        assert dcli.main() == 1

    def test_forwards_args_with_joined_prompt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: dict[tuple[str, str, Path, str], int] = {}

        def fake_dispatch(skill: str, test_type: str, round_dir: Path, prompt: str) -> int:
            calls[(skill, test_type, round_dir, prompt)] = 1
            return 0

        monkeypatch.setattr(
            sys,
            "argv",
            ["shenbi-dispatch", "skill", "generative", "/tmp/rd", "multi", "word", "prompt"],
        )
        monkeypatch.setattr(dcli, "dispatch", fake_dispatch)
        assert dcli.main() == 0
        # F267: multi-word prompt joined with spaces, not truncated
        args = next(iter(calls))
        assert "/tmp/rd" in str(args[2])
        assert args[3] == "multi word prompt"
        assert args[:2] == ("skill", "generative")

    def test_propagates_dispatch_rc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["shenbi-dispatch", "s", "t", "/tmp/rd", "p"])
        monkeypatch.setattr(dcli, "dispatch", lambda *a: 2)
        assert dcli.main() == 2


@pytest.mark.unit
class TestExecutorFailureBranches:
    def _stub_green_g1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(executor, "run_g1", lambda skill, files, rd: {"status": "PASS"})

    def test_g1_failure_returns_1(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(executor, "run_g1", lambda skill, files, rd: {"status": "FAIL"})
        rc = executor.dispatch("shenbi-worldbuilding", "generative", tmp_path, "test")
        assert rc == 1

    def test_g2_failure_returns_1(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self._stub_green_g1(monkeypatch)
        monkeypatch.setattr(executor, "detect_mode", lambda: "internal")
        monkeypatch.setattr(
            "shenbi.dispatcher.modes.internal.dispatch_internal", lambda *a, **kw: 0
        )
        monkeypatch.setattr(executor, "run_g2", lambda files, ft, rd: {"status": "FAIL"})
        # tmp_path has no pipeline-state.json → non-pipeline → G2 enforced
        rc = executor.dispatch("shenbi-worldbuilding", "generative", tmp_path, "test")
        assert rc == 1

    def test_dispatch_failure_rc_passthrough_skips_g2(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        self._stub_green_g1(monkeypatch)
        monkeypatch.setattr(executor, "detect_mode", lambda: "internal")
        monkeypatch.setattr(
            "shenbi.dispatcher.modes.internal.dispatch_internal", lambda *a, **kw: 3
        )
        g2_calls: list[list[str]] = []

        def fake_g2(files: list[str], ft: str, rd: Path) -> dict[str, str]:
            g2_calls.append(files)
            return {"status": "PASS"}

        monkeypatch.setattr(executor, "run_g2", fake_g2)
        rc = executor.dispatch("shenbi-worldbuilding", "generative", tmp_path, "test")
        # nonzero dispatch rc propagates; rc==0 short-circuit keeps G2 unrun
        assert rc == 3
        assert g2_calls == []

    def test_skip_reads_env_filters_nonexistent_optional_files(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """SHENBI_G1_SKIP_READS (executor copy): optional files that don't exist
        yet are dropped from the G1 input list before run_g1 sees it.
        """
        captured: dict[str, list[str]] = {}

        def fake_g1(skill: str, files: list[str], rd: Path) -> dict[str, str]:
            captured["files"] = files
            return {"status": "FAIL"}  # stop after G1; we only inspect the input list

        monkeypatch.setattr(executor, "run_g1", fake_g1)
        baseline: dict[str, list[str]] = {}
        monkeypatch.delenv("SHENBI_G1_SKIP_READS", raising=False)
        executor.dispatch("shenbi-worldbuilding", "generative", tmp_path, "test")
        baseline["files"] = captured["files"]
        assert baseline["files"], "fixture sanity: skill derives a non-empty read list"

        monkeypatch.setenv("SHENBI_G1_SKIP_READS", "*")
        executor.dispatch("shenbi-worldbuilding", "generative", tmp_path, "test")
        # '*' matches every filename; all derived reads are optional-not-yet-produced
        # (tmp_path is empty), so the filtered list must shrink (possibly to empty)
        assert len(captured["files"]) < len(baseline["files"])
