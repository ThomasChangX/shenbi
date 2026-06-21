"""Unit tests for shenbi.update_progress.

Business rules under test:
- Single-writer progress.json state
- Skill "genuinely done" = all 3 test types done/skip
- Queue consistency: remaining_* queues match not-done skills per type
- completed_skill_names must equal genuinely_done set
- CLI: init/mark-done/validate/rebuild-queues routing
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi import update_progress
from shenbi.update_progress import (
    cmd_init,
    cmd_mark_done,
    cmd_rebuild_queues,
    cmd_validate,
    load,
    main,
    save,
    validate_internal,
)

pytestmark = pytest.mark.unit

# --- Fixtures -------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_skills(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Replace ALL_SKILLS with a fixed 3-skill set so tests are deterministic
    regardless of which real skills exist in skills/.
    """
    fake_skills = ["shenbi-alpha", "shenbi-beta", "shenbi-gamma"]
    monkeypatch.setattr(update_progress, "ALL_SKILLS", fake_skills)


@pytest.fixture
def round_dir(tmp_path: Path) -> Path:
    rd = tmp_path / "round-001"
    rd.mkdir()
    return rd


@pytest.fixture
def initialized_round(round_dir: Path) -> Path:
    """Round dir with progress.json initialized."""
    cmd_init(str(round_dir), "T1")
    return round_dir


# --- TestLoad ------------------------------------------------------------


class TestLoad:
    def test_loads_existing_progress_json(self, initialized_round: Path) -> None:
        data = load(str(initialized_round))
        assert data["tier"] == "T1"
        assert "skills" in data

    def test_exits_when_progress_json_missing(
        self, round_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            load(str(round_dir))
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert "progress.json not found" in emitted["error"]

    def test_returns_dict_with_required_keys(self, initialized_round: Path) -> None:
        data = load(str(initialized_round))
        for key in (
            "completed_skill_names",
            "skills",
            "remaining_generative",
            "remaining_bug_hunt",
            "remaining_clean",
        ):
            assert key in data


# --- TestSave ------------------------------------------------------------


class TestSave:
    def test_writes_progress_json_with_indent(self, round_dir: Path) -> None:
        save(str(round_dir), {"tier": "T1", "skills": {}})
        text = (round_dir / "progress.json").read_text(encoding="utf-8")
        # indent=2 produces newlines + 2-space indent
        assert "\n" in text
        assert "  " in text

    def test_overwrites_existing_progress(self, round_dir: Path) -> None:
        save(str(round_dir), {"v": 1})
        save(str(round_dir), {"v": 2})
        data = json.loads((round_dir / "progress.json").read_text(encoding="utf-8"))
        assert data == {"v": 2}


# --- TestValidateInternal -----------------------------------------------


class TestValidateInternal:
    def _progress_all_done(self) -> dict[str, Any]:
        """A perfectly consistent progress: all 3 skills fully done,
        all queues empty, completed lists all 3.
        """
        skills = {
            sn: {
                "generative": {"status": "done", "score": 90},
                "bug-hunt": {"status": "done", "score": 85},
                "clean": {"status": "done", "score": 95},
            }
            for sn in ["shenbi-alpha", "shenbi-beta", "shenbi-gamma"]
        }
        return {
            "completed_skill_names": ["shenbi-alpha", "shenbi-beta", "shenbi-gamma"],
            "skills": skills,
            "remaining_generative": [],
            "remaining_bug_hunt": [],
            "remaining_clean": [],
        }

    def test_returns_no_issues_for_consistent_progress(self) -> None:
        progress = self._progress_all_done()
        issues, _, _ = validate_internal(progress)
        assert issues == []

    def test_detects_extra_in_completed_not_genuinely_done(self) -> None:
        progress: dict[str, Any] = self._progress_all_done()
        progress["completed_skill_names"].append("shenbi-ghost")
        issues, _, _ = validate_internal(progress)
        assert any("shenbi-ghost" in i for i in issues)

    def test_detects_genuinely_done_missing_from_completed(self) -> None:
        progress: dict[str, Any] = self._progress_all_done()
        progress["completed_skill_names"].remove("shenbi-alpha")
        issues, _, _ = validate_internal(progress)
        assert any("shenbi-alpha" in i for i in issues)

    def test_detects_skill_done_but_listed_in_remaining_queue(self) -> None:
        """When a skill is genuinely done but still in a remaining queue,
        validate flags it as 'in queues but already done'. This requires
        another skill to be pending — validate's queue checks only fire
        when expected_pending is non-empty.
        """
        # alpha fully done; gamma pending (no entries)
        progress = self._progress_all_done()
        # Wipe gamma from skills to make it pending
        del progress["skills"]["shenbi-gamma"]
        progress["completed_skill_names"] = ["shenbi-alpha", "shenbi-beta"]
        # alpha (done) appears in remaining_generative alongside gamma (pending)
        progress["remaining_generative"] = ["shenbi-alpha", "shenbi-gamma"]
        progress["remaining_bug_hunt"] = ["shenbi-gamma"]
        progress["remaining_clean"] = ["shenbi-gamma"]
        issues, _, _ = validate_internal(progress)
        assert any("shenbi-alpha" in i and "already done" in i for i in issues)

    def test_detects_pending_skill_missing_from_all_queues(self) -> None:
        """A pending skill must appear in at least one queue."""
        progress = self._progress_all_done()
        # alpha clean is pending -> alpha should be in remaining_clean
        progress["skills"]["shenbi-alpha"]["clean"] = {"status": "pending"}
        progress["completed_skill_names"] = ["shenbi-beta", "shenbi-gamma"]
        # All queues empty (alpha should be in remaining_clean but isn't)
        progress["remaining_generative"] = []
        progress["remaining_bug_hunt"] = []
        progress["remaining_clean"] = []
        issues, _, _ = validate_internal(progress)
        # Expect a queue-emptiness warning since expected_pending is non-empty
        assert any("queues" in i for i in issues)

    def test_partly_done_counted_correctly(self) -> None:
        progress = self._progress_all_done()
        # alpha only has 2/3 done
        del progress["skills"]["shenbi-alpha"]["clean"]
        progress["completed_skill_names"] = ["shenbi-beta", "shenbi-gamma"]
        progress["remaining_clean"] = ["shenbi-alpha"]
        _, _, partly_done = validate_internal(progress)
        assert "shenbi-alpha" in partly_done
        assert partly_done["shenbi-alpha"] == 2

    def test_skill_with_skip_counts_as_done(self) -> None:
        """--note SKIP marks a test_type as 'skip' which still counts as
        completed for the purposes of being 'genuinely done'.
        """
        progress = self._progress_all_done()
        progress["skills"]["shenbi-alpha"]["clean"] = {
            "status": "skip",
            "note": "carry-forward",
        }
        _, genuinely_done, _ = validate_internal(progress)
        assert "shenbi-alpha" in genuinely_done

    def test_handles_missing_skills_dict_gracefully(self) -> None:
        progress: dict[str, Any] = {
            "completed_skill_names": [],
            "remaining_generative": [],
            "remaining_bug_hunt": [],
            "remaining_clean": [],
        }
        # No 'skills' key — should not crash
        issues, _, _ = validate_internal(progress)
        assert isinstance(issues, list)


# --- TestCmdInit ---------------------------------------------------------


class TestCmdInit:
    def test_creates_progress_json_with_tier(
        self, round_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cmd_init(str(round_dir), "T2")
        data = json.loads((round_dir / "progress.json").read_text(encoding="utf-8"))
        assert data["tier"] == "T2"

    def test_creates_subdirectories(self, round_dir: Path) -> None:
        cmd_init(str(round_dir), "T1")
        for sub in [
            "t1-reports",
            "t2-reports",
            "t3-reports",
            "skill-output",
            "skill-traces",
            "gate-markers",
            "phase-state",
        ]:
            assert (round_dir / sub).is_dir(), f"Missing subdir: {sub}"

    def test_initial_remaining_generative_lists_all_skills(self, round_dir: Path) -> None:
        cmd_init(str(round_dir), "T1")
        data = json.loads((round_dir / "progress.json").read_text(encoding="utf-8"))
        assert data["remaining_generative"] == ["shenbi-alpha", "shenbi-beta", "shenbi-gamma"]

    def test_initial_other_queues_empty(self, round_dir: Path) -> None:
        cmd_init(str(round_dir), "T1")
        data = json.loads((round_dir / "progress.json").read_text(encoding="utf-8"))
        assert data["remaining_bug_hunt"] == []
        assert data["remaining_clean"] == []

    def test_refuses_when_progress_already_exists(
        self, initialized_round: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_init(str(initialized_round), "T1")
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "error"

    def test_uses_custom_expected_chapters(self, round_dir: Path) -> None:
        cmd_init(str(round_dir), "T1", expected_chapters=42)
        data = json.loads((round_dir / "progress.json").read_text(encoding="utf-8"))
        assert data["expected_chapters"] == 42

    def test_default_expected_chapters_is_67(self, round_dir: Path) -> None:
        """G0.3 will recalculate based on outline; 67 is a placeholder default."""
        cmd_init(str(round_dir), "T1")
        data = json.loads((round_dir / "progress.json").read_text(encoding="utf-8"))
        assert data["expected_chapters"] == 67

    def test_emits_total_skills_count(
        self, round_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cmd_init(str(round_dir), "T1")
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["total_skills"] == 3


# --- TestCmdMarkDone -----------------------------------------------------


class TestCmdMarkDone:
    def test_marks_skill_done_for_generative(self, initialized_round: Path) -> None:
        cmd_mark_done(str(initialized_round), "shenbi-alpha", "generative", 90.0)
        data = load(str(initialized_round))
        assert data["skills"]["shenbi-alpha"]["generative"]["status"] == "done"
        assert data["skills"]["shenbi-alpha"]["generative"]["score"] == 90.0

    def test_marks_skill_skip_with_note(self, initialized_round: Path) -> None:
        """--note SKIP carries forward a previous cycle's result instead of
        re-running the test.
        """
        cmd_mark_done(
            str(initialized_round), "shenbi-alpha", "generative", 0.0, note="carry-forward"
        )
        data = load(str(initialized_round))
        entry = data["skills"]["shenbi-alpha"]["generative"]
        assert entry["status"] == "skip"
        assert entry["note"] == "carry-forward"

    def test_increments_subagent_completion_count(self, initialized_round: Path) -> None:
        cmd_mark_done(str(initialized_round), "shenbi-alpha", "generative", 90.0)
        cmd_mark_done(str(initialized_round), "shenbi-beta", "generative", 80.0)
        data = load(str(initialized_round))
        assert data["subagent_completion_count"] == 2

    def test_skill_not_in_completed_until_all_three_done(self, initialized_round: Path) -> None:
        cmd_mark_done(str(initialized_round), "shenbi-alpha", "generative", 90.0)
        data = load(str(initialized_round))
        assert "shenbi-alpha" not in data["completed_skill_names"]

    def test_skill_added_to_completed_when_all_three_done(self, initialized_round: Path) -> None:
        for tt in ("generative", "bug-hunt", "clean"):
            cmd_mark_done(str(initialized_round), "shenbi-alpha", tt, 90.0)
        data = load(str(initialized_round))
        assert "shenbi-alpha" in data["completed_skill_names"]

    def test_removes_skill_from_remaining_queue_for_test_type(
        self, initialized_round: Path
    ) -> None:
        cmd_mark_done(str(initialized_round), "shenbi-alpha", "generative", 90.0)
        data = load(str(initialized_round))
        assert "shenbi-alpha" not in data["remaining_generative"]
        # Other queues still have alpha
        assert "shenbi-alpha" in data["remaining_bug_hunt"]
        assert "shenbi-alpha" in data["remaining_clean"]

    def test_emits_ok_with_remaining_count(
        self,
        initialized_round: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cmd_mark_done(str(initialized_round), "shenbi-alpha", "generative", 90.0)
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "ok"
        assert emitted["remaining_gen"] == 2  # 3 - 1

    def test_score_stored_as_float(self, initialized_round: Path) -> None:
        cmd_mark_done(str(initialized_round), "shenbi-alpha", "generative", 90)
        data = load(str(initialized_round))
        assert isinstance(data["skills"]["shenbi-alpha"]["generative"]["score"], float)


# --- TestCmdValidate -----------------------------------------------------


class TestCmdValidate:
    def test_emits_ok_when_no_issues(
        self,
        initialized_round: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            cmd_validate(str(initialized_round))
        assert exc.value.code == 0
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "ok"

    def test_emits_fail_with_issues(
        self,
        initialized_round: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Corrupt: completed lists a skill not actually done
        data = load(str(initialized_round))
        data["completed_skill_names"] = ["shenbi-ghost"]
        save(str(initialized_round), data)
        with pytest.raises(SystemExit) as exc:
            cmd_validate(str(initialized_round))
        assert exc.value.code == 1
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["status"] == "fail"
        assert "issues" in emitted

    def test_includes_genuinely_done_count(
        self,
        initialized_round: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Mark one skill fully done
        for tt in ("generative", "bug-hunt", "clean"):
            cmd_mark_done(str(initialized_round), "shenbi-alpha", tt, 90.0)
        # Flush earlier mark-done emissions before capturing validate output
        capsys.readouterr()
        with pytest.raises(SystemExit):
            cmd_validate(str(initialized_round))
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["genuinely_done"] == 1

    def test_includes_remaining_queue_lengths(
        self,
        initialized_round: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Flush init's emission before capturing
        capsys.readouterr()
        with pytest.raises(SystemExit):
            cmd_validate(str(initialized_round))
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["remaining_gen"] == 3
        assert emitted["remaining_bug"] == 0
        assert emitted["remaining_clean"] == 0


# --- TestCmdRebuildQueues ------------------------------------------------


class TestCmdRebuildQueues:
    def test_recomputes_pending_generative(self, initialized_round: Path) -> None:
        cmd_mark_done(str(initialized_round), "shenbi-alpha", "generative", 90.0)
        # Corrupt the queue manually
        data = load(str(initialized_round))
        data["remaining_generative"] = ["shenbi-alpha", "shenbi-beta", "shenbi-gamma"]
        save(str(initialized_round), data)
        cmd_rebuild_queues(str(initialized_round))
        data = load(str(initialized_round))
        assert "shenbi-alpha" not in data["remaining_generative"]
        assert "shenbi-beta" in data["remaining_generative"]

    def test_recomputes_completed_skill_names(self, initialized_round: Path) -> None:
        for tt in ("generative", "bug-hunt", "clean"):
            cmd_mark_done(str(initialized_round), "shenbi-alpha", tt, 90.0)
        # Wipe completed list
        data = load(str(initialized_round))
        data["completed_skill_names"] = []
        save(str(initialized_round), data)
        cmd_rebuild_queues(str(initialized_round))
        data = load(str(initialized_round))
        assert "shenbi-alpha" in data["completed_skill_names"]

    def test_handles_empty_skills_dict(self, initialized_round: Path) -> None:
        # No skills marked done — all 3 should remain pending
        cmd_rebuild_queues(str(initialized_round))
        data = load(str(initialized_round))
        assert len(data["remaining_generative"]) == 3
        assert data["completed_skill_names"] == []

    def test_emits_rebuild_summary(
        self,
        initialized_round: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cmd_rebuild_queues(str(initialized_round))
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["action"] == "rebuild-queues"
        assert emitted["remaining_gen"] == 3


# --- TestMainCli ---------------------------------------------------------


class TestMainCli:
    def test_exits_when_no_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.argv", ["update-progress"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_routes_init(self, monkeypatch: pytest.MonkeyPatch, round_dir: Path) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["update-progress", "init", str(round_dir), "T1"],
        )
        main()
        assert (round_dir / "progress.json").exists()

    def test_routes_init_with_expected_chapters_flag(
        self, monkeypatch: pytest.MonkeyPatch, round_dir: Path
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            [
                "update-progress",
                "init",
                str(round_dir),
                "T1",
                "--expected-chapters",
                "50",
            ],
        )
        main()
        data = json.loads((round_dir / "progress.json").read_text(encoding="utf-8"))
        assert data["expected_chapters"] == 50

    def test_routes_mark_done(
        self,
        monkeypatch: pytest.MonkeyPatch,
        initialized_round: Path,
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            [
                "update-progress",
                "mark-done",
                str(initialized_round),
                "shenbi-alpha",
                "generative",
                "90",
            ],
        )
        main()
        data = load(str(initialized_round))
        assert data["skills"]["shenbi-alpha"]["generative"]["status"] == "done"

    def test_routes_validate(
        self,
        monkeypatch: pytest.MonkeyPatch,
        initialized_round: Path,
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["update-progress", "validate", str(initialized_round)],
        )
        with pytest.raises(SystemExit):
            main()

    def test_routes_rebuild_queues(
        self,
        monkeypatch: pytest.MonkeyPatch,
        initialized_round: Path,
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["update-progress", "rebuild-queues", str(initialized_round)],
        )
        main()

    def test_routes_unknown_command_to_error(
        self, monkeypatch: pytest.MonkeyPatch, round_dir: Path
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            ["update-progress", "bogus", str(round_dir)],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_mark_done_with_note_flag(
        self,
        monkeypatch: pytest.MonkeyPatch,
        initialized_round: Path,
    ) -> None:
        monkeypatch.setattr(
            "sys.argv",
            [
                "update-progress",
                "mark-done",
                str(initialized_round),
                "shenbi-alpha",
                "generative",
                "0",
                "--note",
                "carry-forward",
            ],
        )
        main()
        data = load(str(initialized_round))
        assert data["skills"]["shenbi-alpha"]["generative"]["status"] == "skip"
