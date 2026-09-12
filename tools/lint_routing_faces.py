#!/usr/bin/env python3
"""Routing-face reconciliation: DEPRECATED skills must not be routed anywhere (spec #59 T3.11).

Faces (structural, not text-grep): deps.json string values, using-shenbi
SKILL.md full text (dead-name ban + routed-name disk existence), GENESIS_STEPS,
TRIGGER_STEPS, GENRE_ACTIVATION_MATRIX, CHAPTER_STEPS, BOUNDARY_TRIGGERS.
Exit 1 on any violation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from shenbi.pipeline.audit_layer import BOUNDARY_TRIGGERS, GENRE_ACTIVATION_MATRIX  # noqa: E402
from shenbi.pipeline.chapter_loop import CHAPTER_STEPS  # noqa: E402
from shenbi.pipeline.genesis import GENESIS_STEPS  # noqa: E402
from shenbi.pipeline.triggers import TRIGGER_STEPS  # noqa: E402
from shenbi.skill_utils.deprecated import deprecated_skill_names  # noqa: E402


def _walk_strings(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [s for it in node for s in _walk_strings(it)]
    if isinstance(node, dict):
        return [s for v in node.values() for s in _walk_strings(v)]
    return []


def lint_routing_faces(repo: Path, skills_dir: Path) -> list[str]:
    """Reconcile all seven routing faces against DEPRECATED and ghost names."""
    errs: list[str] = []
    dead = deprecated_skill_names(skills_dir)

    # 1) deps.json — any string value naming a DEPRECATED skill
    if dead:
        deps_path = repo / "tests" / "tiers" / "deps.json"
        if deps_path.exists():
            deps = json.loads(deps_path.read_text(encoding="utf-8"))
            hits = sorted(set(_walk_strings(deps)) & dead)
            if hits:
                errs.append(f"deps.json routes DEPRECATED skills: {hits}")

    # 2) using-shenbi SKILL.md — full text (table rows + default column + Phase
    #    list). Both directions (spec T3.11(b)): dead-name ban AND routed-name
    #    disk existence (ghost typo detection). The lookbehind excludes filename
    #    fragments like `2026-06-08-shenbi-design.md` (hyphen-preceded).
    table_path = skills_dir / "using-shenbi" / "SKILL.md"
    if table_path.exists():
        text = table_path.read_text(encoding="utf-8")
        row_hits = sorted(d for d in dead if d in text)
        if row_hits:
            errs.append(f"using-shenbi routes DEPRECATED skills: {row_hits}")
        live_dirs = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
        ghosts = sorted(set(re.findall(r"(?<![\w-])shenbi-[a-z0-9-]+", text)) - live_dirs)
        if ghosts:
            errs.append(f"using-shenbi routes skills without a skills/ dir: {ghosts}")

    # 3) code faces (structural imports — STEP_NAME_MIGRATIONS whitelist-safe);
    #    only meaningful when DEPRECATED skills exist to ban
    if dead:
        faces: dict[str, list[str]] = {
            "GENESIS_STEPS": [s.skill for s in GENESIS_STEPS],
            "TRIGGER_STEPS": [s.skill for s in TRIGGER_STEPS],
            "GENRE_ACTIVATION_MATRIX": list(GENRE_ACTIVATION_MATRIX.values()),
            "CHAPTER_STEPS": [s.skill for s in CHAPTER_STEPS],
            "BOUNDARY_TRIGGERS": list(BOUNDARY_TRIGGERS),
        }
        for face, members in faces.items():
            hit = sorted(set(members) & dead)
            if hit:
                errs.append(f"{face} routes DEPRECATED skills: {hit}")
    return errs


def main() -> int:
    """CLI entry: lint the real repo, exit 1 on any violation."""
    repo = _REPO_ROOT
    errs = lint_routing_faces(repo, repo / "skills")
    if errs:
        for e in errs:
            print(f"lint_routing_faces: FAIL {e}")
        return 1
    print("lint_routing_faces: OK (0 violations across 7 faces)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
