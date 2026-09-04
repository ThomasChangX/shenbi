"""C28 read-suppression test file (T2 template short-circuit + T4 R1 tests).

T2 part: _init_truth_templates must skip the 74-skill contract scan
(~655ms) when every template file already exists (T1606).
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

import shenbi.pipeline.dispatch_helper as dh
from shenbi.pipeline.audit_context_cache import build_shared_audit_context
from shenbi.pipeline.dispatch_helper import _build_skill_prompt


def test_init_truth_templates_shortcircuits_when_all_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    truth = tmp_path / "truth"
    truth.mkdir()
    for fn in dh._TRUTH_FILE_TITLES:
        (truth / fn).write_text("---\nupdate_mode: replace\n---\n", encoding="utf-8")

    calls = {"n": 0}

    def counting_collect() -> dict[str, list[str]]:
        calls["n"] += 1
        return {}

    monkeypatch.setattr(dh, "_collect_declared_truth_fields", counting_collect)
    dh._init_truth_templates(tmp_path)
    assert calls["n"] == 0


def test_init_truth_templates_scans_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At least one template missing -> the scan runs and the missing file is created."""
    truth = tmp_path / "truth"
    truth.mkdir()
    names = list(dh._TRUTH_FILE_TITLES)
    for fn in names[:-1]:
        (truth / fn).write_text("---\nupdate_mode: replace\n---\n", encoding="utf-8")

    calls = {"n": 0}

    def counting_collect() -> dict[str, list[str]]:
        calls["n"] += 1
        return {}

    monkeypatch.setattr(dh, "_collect_declared_truth_fields", counting_collect)
    dh._init_truth_templates(tmp_path)
    assert calls["n"] == 1
    assert (truth / names[-1]).exists()


# ---------------------------------------------------------------------------
# T4 (C28 R1): raw-files read suppression — 4-site F312 path fix + 9->1 reads
# ---------------------------------------------------------------------------

_FIX = Path(__file__).resolve().parents[2] / "fixtures"

AUDIT_SKILLS = [
    "shenbi-review-group-factual",
    "shenbi-review-group-character",
    "shenbi-review-group-craft",
    "shenbi-review-group-plan",
    "shenbi-review-resonance",
    "shenbi-review-sensitivity",
]


def _assemble_project(tmp_path: Path) -> Path:
    """Real-output fixture project (G0.9): copies of real products, never hand-written."""
    for sub in ("chapters", "truth", "world", "style", "context"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    for src in sorted((_FIX / "multi-chapter-example").glob("chapter-*.md")):
        shutil.copy(src, tmp_path / "chapters" / src.name)
    shutil.copy(
        _FIX / "snapshots" / "chapter-025" / "truth" / "character_matrix.md",
        tmp_path / "truth" / "character_matrix.md",
    )
    shutil.copy(
        _FIX / "snapshots" / "chapter-025" / "truth" / "pending_hooks.md",
        tmp_path / "truth" / "pending_hooks.md",
    )
    shutil.copy(_FIX / "world-rules-example.md", tmp_path / "world" / "rules.md")
    shutil.copy(_FIX / "style-profile-example.md", tmp_path / "style" / "style_profile.md")
    return tmp_path


_RAW_FILES_EXPECTED = [
    "chapters/chapter-3.md",
    "world/rules.md",
    "truth/character_matrix.md",
    "style/style_profile.md",
    "truth/pending_hooks.md",
]


def test_raw_files_hold_full_content(tmp_path: Path) -> None:
    project = _assemble_project(tmp_path)
    ctx = build_shared_audit_context(project, 3)
    for rel in _RAW_FILES_EXPECTED:
        assert ctx.raw_files[rel] == (project / rel).read_text(encoding="utf-8"), rel


def test_world_rules_key_present(tmp_path: Path) -> None:
    project = _assemble_project(tmp_path)
    ctx = build_shared_audit_context(project, 3)
    assert "world/rules.md" in ctx.raw_files  # was truth/world_rules.md dead path
    assert "truth/world_rules.md" not in ctx.raw_files


def test_chapter_read_count_is_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _assemble_project(tmp_path)
    chapter_file = project / "chapters" / "chapter-3.md"
    counter = {"n": 0}
    real_read = Path.read_text

    def counting_read(self: Path, *a: object, **k: object) -> str:
        if self == chapter_file:
            counter["n"] += 1
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting_read)
    ctx = build_shared_audit_context(project, 3)  # the ONE legitimate read
    for skill in AUDIT_SKILLS:
        _build_skill_prompt(
            skill=skill, project_dir=project, prompt="审计本章", chapter=3, shared_context=ctx
        )
    assert counter["n"] == 1  # was 9: 6 contract reads + 3 checklist cold-path reads


def test_byte_equality_suppression_switch(tmp_path: Path) -> None:
    project = _assemble_project(tmp_path)
    ctx_on = build_shared_audit_context(project, 3)
    prompts_on = [
        _build_skill_prompt(
            skill=s, project_dir=project, prompt="审计本章", chapter=3, shared_context=ctx_on
        )
        for s in AUDIT_SKILLS
    ]
    ctx_off = replace(ctx_on, raw_files={})  # suppression OFF (path fixes stay)
    prompts_off = [
        _build_skill_prompt(
            skill=s, project_dir=project, prompt="审计本章", chapter=3, shared_context=ctx_off
        )
        for s in AUDIT_SKILLS
    ]
    assert prompts_on == prompts_off
