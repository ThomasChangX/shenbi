"""Tests for revision decisions fallback generation.

The fallback must conform to DecisionsDoc (extra="forbid"): $schema, skill,
chapter, selections, adjustments, produced_at. It must NOT use route/changes/
rationale keys.
"""

import json
import tempfile
from pathlib import Path

from shenbi.pipeline.chapter_loop import (
    _ensure_revision_decisions_exists,
    _is_revision_routed,
)


def test_fallback_generates_decisionsdoc_compliant_file_when_missing():
    """Missing revision-decisions.json -> fallback writes a DecisionsDoc file."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters_dir = project_dir / "chapters"
        chapters_dir.mkdir(parents=True)

        _ensure_revision_decisions_exists(project_dir, chapter=5)

        rev_path = chapters_dir / "chapter-5-revision-decisions.json"
        assert rev_path.exists()
        data = json.loads(rev_path.read_text())
        # DecisionsDoc required fields
        assert data["$schema"] == "shenbi-decisions-v1"
        assert data["skill"] == "shenbi-chapter-revision"
        assert data["chapter"] == 5
        assert data["adjustments"] == []
        assert "produced_at" in data
        # The skip decision is documented in selections, not a `route` key
        assert isinstance(data["selections"], list)
        assert any(
            "no_revision" in str(s.get("target", "")).lower()
            for s in data["selections"]
            if isinstance(s, dict)
        )
        # Must NOT contain forbidden keys
        assert "route" not in data
        assert "changes" not in data
        assert "rationale" not in data


def test_fallback_does_not_overwrite_existing():
    """If revision decisions already exist, fallback does nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        chapters_dir = project_dir / "chapters"
        chapters_dir.mkdir(parents=True)

        existing = {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-chapter-revision",
            "chapter": 5,
            "selections": [],
            "adjustments": [
                {
                    "issue_id": "x",
                    "severity": "high",
                    "handling": "explicit_callout",
                    "rationale": "Fix the dialogue pacing in scene.",
                }
            ],
            "produced_at": "2026-07-19T00:00:00+00:00",
        }
        rev_path = chapters_dir / "chapter-5-revision-decisions.json"
        rev_path.write_text(json.dumps(existing))

        _ensure_revision_decisions_exists(project_dir, chapter=5)

        data = json.loads(rev_path.read_text())
        # Not overwritten — still has the non-empty adjustments
        assert len(data["adjustments"]) == 1


def test_fallback_only_creates_when_revision_was_routed():
    """Fallback only creates when revision routing was recorded in state."""
    assert _is_revision_routed("no_revision") is True
    assert _is_revision_routed("spot_fix") is True
    assert _is_revision_routed(None) is False
