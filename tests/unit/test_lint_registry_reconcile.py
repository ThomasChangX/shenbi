"""lint_registry_reconcile R1/R5 faces (spec #60 T1). Temp-copy negative samples."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from tools.lint_registry_reconcile import lint_registry_reconcile

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[2]
_COPY_LIST = [
    "plugins/master.json",
    "tests/tiers/deps.json",
    "docs/skills/index.md",
    "docs/framework/truth-files.yaml",
    "AGENTS.md",
    "src/shenbi/gates/g5.py",
    "src/shenbi/gates/shared.py",
    "src/shenbi/gates/g4/generic.py",
    "src/shenbi/gates/g4/scoring_sections.py",
    "src/shenbi/contracts/registry.py",
    "src/shenbi/gates/cli.py",  # SHORT_MAP import face needs the module itself
    "src/shenbi/__init__.py",
    "src/shenbi/gates/__init__.py",  # regular-package precedence
]
_SCORE_EXEMPT = frozenset({"shenbi-score-arc", "shenbi-score-stratum", "shenbi-score-volume"})


@pytest.fixture()
def repo_copy(tmp_path: Path) -> Path:
    dst = tmp_path / "repo"
    for rel in _COPY_LIST:
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_SRC / rel, dst / rel)
    shutil.copytree(_SRC / "skills", dst / "skills")
    return dst


def test_clean_repo_zero_violations(repo_copy: Path) -> None:
    # NOTE: stays RED from Task 4 until Tasks 6-11 land (the copy carries the
    # born-red inventory). Finally green at Task 14. Do NOT data-fix inside a
    # lint test. score-* pipeline-internal exemption passed like the mounts.
    assert lint_registry_reconcile(repo_copy, allow_missing=_SCORE_EXEMPT) == []


def test_master_json_deprecated_route_fails(repo_copy: Path) -> None:
    p = repo_copy / "plugins" / "master.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    m["skills"].append("skills/shenbi-review-pov/SKILL.md")  # DEPRECATED
    p.write_text(json.dumps(m), encoding="utf-8")
    vios = lint_registry_reconcile(repo_copy)
    assert any("master.json: routes-DEPRECATED" in v and "shenbi-review-pov" in v for v in vios)


def test_master_json_delete_live_fails(repo_copy: Path) -> None:
    p = repo_copy / "plugins" / "master.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    m["skills"] = [e for e in m["skills"] if "shenbi-worldbuilding" not in e]
    p.write_text(json.dumps(m), encoding="utf-8")
    vios = lint_registry_reconcile(repo_copy)
    assert any("master.json: missing-live" in v and "shenbi-worldbuilding" in v for v in vios)


def test_short_map_deletion_fails(repo_copy: Path) -> None:
    p = repo_copy / "src" / "shenbi" / "gates" / "cli.py"
    orig = (_SRC / "src/shenbi/gates/cli.py").read_text(encoding="utf-8")
    p.write_text(
        re.sub(r'"chapter-drafting": "shenbi-chapter-drafting",\n', "", orig, count=1),
        encoding="utf-8",
    )
    vios = lint_registry_reconcile(repo_copy)
    assert any("SHORT_MAP: missing-checkers" in v and "shenbi-chapter-drafting" in v for v in vios)


def test_g5_glob_deletion_fails(repo_copy: Path) -> None:
    p = repo_copy / "src" / "shenbi" / "gates" / "g5.py"
    orig = (_SRC / "src/shenbi/gates/g5.py").read_text(encoding="utf-8")
    # shenbi-genre-config: a genesis prereq with a checker and a glob
    p.write_text(
        orig.replace('    "shenbi-genre-config": ["genre-config.json"],\n', "", 1),
        encoding="utf-8",
    )
    vios = lint_registry_reconcile(repo_copy)
    assert any(
        "G5_CHECKER_GLOBS: missing-checker-prereqs" in v and "shenbi-genre-config" in v
        for v in vios
    )


def test_g4_checker_skills_gap_fails(repo_copy: Path) -> None:
    p = repo_copy / "src" / "shenbi" / "gates" / "shared.py"
    orig = (_SRC / "src/shenbi/gates/shared.py").read_text(encoding="utf-8")
    p.write_text(orig.replace('    "shenbi-worldbuilding",\n', "", 1), encoding="utf-8")
    vios = lint_registry_reconcile(repo_copy)
    assert any("G4_CHECKER_SKILLS: !=checkers" in v and "shenbi-worldbuilding" in v for v in vios)


def test_index_md_row_deletion_fails(repo_copy: Path) -> None:
    p = repo_copy / "docs" / "skills" / "index.md"
    p.write_text(
        p.read_text(encoding="utf-8").replace("shenbi-worldbuilding", "shenbi-redacted"),
        encoding="utf-8",
    )
    vios = lint_registry_reconcile(repo_copy)
    assert any(
        "docs/skills/index.md: missing-live" in v and "shenbi-worldbuilding" in v for v in vios
    )


def test_trigger_table_exemption_roundtrip(repo_copy: Path) -> None:
    """allow_missing removes exactly the named skills from the trigger face."""
    vios = lint_registry_reconcile(repo_copy)  # no exemption
    unmentioned = next(v for v in vios if "using-shenbi: unmentioned" in v)
    assert "shenbi-score-arc" in unmentioned
    vios2 = lint_registry_reconcile(repo_copy, allow_missing=_SCORE_EXEMPT)
    face = [v for v in vios2 if "using-shenbi: unmentioned" in v]
    if face:  # other non-exempt gaps may remain pre-Task-9; score-* must not
        assert "shenbi-score-arc" not in face[0]


def test_r5_strict_containment_detected(repo_copy: Path) -> None:
    """The F432 carrier: a broad glob strictly containing a specialized one."""
    p = repo_copy / "src" / "shenbi" / "gates" / "g5.py"
    orig = (_SRC / "src/shenbi/gates/g5.py").read_text(encoding="utf-8")
    # state-settling (drafting, checker-having, truth/*.md) gains nothing here;
    # instead give chapter-drafting a glob strictly containing style-polishing's
    # equal one is exempt — craft the carrier: drafting phase has both
    # chapter-drafting and state-settling; make state-settling cover chapters too.
    mutated = orig.replace(
        '"shenbi-state-settling": ["truth/*.md"],',
        '"shenbi-state-settling": ["truth/*.md", "chapters/chapter-*.md"],',
        1,
    )
    assert mutated != orig
    p.write_text(mutated, encoding="utf-8")
    vios = lint_registry_reconcile(repo_copy)
    # chapters/*.md (chapter-drafting) strictly contains chapters/chapter-*.md
    # (mutated state-settling) within the drafting phase -> containment fires.
    assert any("strict-containment" in v for v in vios)
