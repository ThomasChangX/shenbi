# spec #48 C34 (F628): compute_drift audit/trend writes anchor at
# project_dir/truth regardless of process CWD; --project-dir override;
# path form consistent with downstream readers (triggers.py AUDIT_DRIFT_PATH,
# chapter_loop route-C).

from pathlib import Path

from shenbi.skill_utils.drift_detection import compute_drift


def _write_inputs(pd: Path) -> None:
    truth = pd / "truth"
    truth.mkdir(parents=True)
    (truth / "resonance_trend.md").write_text(
        "| chapter | 情感落地 |\n|---|---|\n| 1 | 9.0 |\n| 2 | 8.0 |\n| 3 | 6.5 |\n| 4 | 4.0 |\n",
        encoding="utf-8",
    )


def test_write_audit_drift_anchors_project_dir(tmp_path, monkeypatch):
    pd = tmp_path / "pd"
    _write_inputs(pd)
    other = tmp_path / "other-cwd"
    other.mkdir()
    monkeypatch.chdir(other)
    import pytest

    with pytest.raises(SystemExit):
        compute_drift.main(
            [
                "--resonance",
                str(pd / "truth" / "resonance_trend.md"),
                "--write-audit-drift",
            ]
        )
    # main exits non-zero when drift findings exist — the write must still be
    # anchored under the project's truth/ dir.
    audit = pd / "truth" / "audit_drift.md"
    assert audit.exists(), "audit_drift.md must land in project truth/, not CWD"
    assert not (other / "truth").exists()


def test_project_dir_flag_overrides(tmp_path, monkeypatch):
    pd = tmp_path / "pd"
    _write_inputs(pd)
    other = tmp_path / "other-cwd"
    other.mkdir()
    monkeypatch.chdir(other)
    import pytest

    with pytest.raises(SystemExit):
        compute_drift.main(
            [
                "--resonance",
                str(pd / "truth" / "resonance_trend.md"),
                "--write-audit-drift",
                "--project-dir",
                str(pd),
            ]
        )
    assert (pd / "truth" / "audit_drift.md").exists()
