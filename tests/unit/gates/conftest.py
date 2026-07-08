"""Fixture factory for gate tests.

Returns (project_dir, round_dir) tuple. project_dir holds project-level
state (chapters/, novel.json, genre-config.json, truth/, config/, outline/).
round_dir holds round-level state (progress.json, summary.json, t1-reports/,
gate-markers/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def make_project(tmp_path: Path):
    """Factory: build project_dir + round_dir for gate testing."""

    def _make(
        *,
        chapters: list[str] | None = None,
        novel_json: dict[str, Any] | None = None,
        genre_config: dict[str, Any] | None = None,
        pending_hooks: str | None = None,
        style_profile: str | None = None,
        volume_map: str | None = None,
        progress: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        t1_reports: dict[str, dict[str, Any]] | None = None,
        gate_markers: list[dict[str, Any]] | None = None,
        seed_file: str | None = None,
    ) -> tuple[Path, Path]:
        project_dir = tmp_path / "project"
        round_dir = tmp_path / "round"
        project_dir.mkdir()
        round_dir.mkdir()

        if seed_file:
            (project_dir / "seed.md").write_text(seed_file, encoding="utf-8")
        if chapters:
            ch_dir = project_dir / "chapters"
            ch_dir.mkdir()
            for i, content in enumerate(chapters, 1):
                (ch_dir / f"chapter-{i:03d}.md").write_text(content, encoding="utf-8")
        if novel_json is not None:
            (project_dir / "novel.json").write_text(
                json.dumps(novel_json, ensure_ascii=False), encoding="utf-8"
            )
        if genre_config is not None:
            (project_dir / "genre-config.json").write_text(
                json.dumps(genre_config, ensure_ascii=False), encoding="utf-8"
            )
        if pending_hooks is not None:
            truth = project_dir / "truth"
            truth.mkdir(exist_ok=True)
            (truth / "pending_hooks.md").write_text(pending_hooks, encoding="utf-8")
        if style_profile is not None:
            style = project_dir / "style"
            style.mkdir(exist_ok=True)
            (style / "style_profile.md").write_text(style_profile, encoding="utf-8")
        if volume_map is not None:
            outline = project_dir / "outline"
            outline.mkdir(exist_ok=True)
            (outline / "volume_map.md").write_text(volume_map, encoding="utf-8")

        if progress is not None:
            (round_dir / "progress.json").write_text(
                json.dumps(progress, ensure_ascii=False), encoding="utf-8"
            )
        if summary is not None:
            (round_dir / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False), encoding="utf-8"
            )
        if t1_reports:
            reports_dir = round_dir / "t1-reports"
            reports_dir.mkdir()
            for skill_name, report_data in t1_reports.items():
                (reports_dir / f"{skill_name}-generative-scores.json").write_text(
                    json.dumps(report_data, ensure_ascii=False), encoding="utf-8"
                )
        if gate_markers:
            marker_dir = round_dir / "gate-markers"
            marker_dir.mkdir()
            for i, marker in enumerate(gate_markers):
                (marker_dir / f"marker-{i}.json").write_text(
                    json.dumps(marker, ensure_ascii=False), encoding="utf-8"
                )

        return project_dir, round_dir

    return _make
