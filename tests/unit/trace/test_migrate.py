from __future__ import annotations

import json
from pathlib import Path

from shenbi.trace.migrate import migrate_from_progress


def test_migrate_from_existing_progress(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text(
        json.dumps(
            {"round": "001", "tier": "T1", "completed_skill_names": ["shenbi-a"]},
        ),
        encoding="utf-8",
    )
    e = migrate_from_progress(rd)
    assert e.action == "LEGACY_MIGRATION"
    assert "progress_sha256" in e.payload
    snapshot = e.payload["progress_snapshot"]
    assert isinstance(snapshot, dict)
    assert "completed_skill_names" in snapshot


def test_migrate_idempotent(tmp_path: Path) -> None:
    rd = tmp_path / "round"
    rd.mkdir()
    (rd / "progress.json").write_text("{}", encoding="utf-8")
    migrate_from_progress(rd)
    from shenbi.trace.replay import replay

    before = len(replay(rd))
    migrate_from_progress(rd)
    after = len(replay(rd))
    assert before == after
