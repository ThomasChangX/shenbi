"""G0.skill_contract: validate all skill contracts + descriptions (spec §3.1).

Checks, for every skills/*/SKILL.md:
  - description <= 500 chars (AGENTS.md)
  - description is trigger-only (no behavioral "This skill does X" text)
  - writes: and updates: paths are disjoint (write=create vs update=modify)
  - every writes/updates entry declares a write mode (mode sub-field)
Issues are returned as "G0.sc.<check>:<skill>:<detail>" strings; empty == pass.
Skills whose frontmatter fails to parse are skipped (their own checks surface
those errors).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DESCRIPTION_MAX_CHARS = 500

# Imperative/behavioral openers that indicate the description describes what
# the skill DOES rather than when to USE it. Deterministic, not a full NLP
# heuristic — keeps the check cheap and the failures explainable.
_BEHAVIORAL_MARKERS = [
    # English
    "this skill",
    "this module",
    "generates ",
    "writes ",
    "creates ",
    "validates ",
    "checks ",
    "analyzes ",
    "computes ",
    "extracts ",
    # Chinese
    "该技能",
    "该模块",
    "生成",
    "写入",
    "创建",
    "验证",
    "检查",
    "分析",
    "计算",
    "提取",
    "产出",
    "输出",
    "读取",
    "审计",
]


def _desc_has_behavioral_text(desc: str) -> bool:
    """True if the description reads as behavioral ('does X') not trigger ('use when Y')."""
    lowered = desc.lstrip().lower()
    return any(lowered.startswith(m) for m in _BEHAVIORAL_MARKERS)


def _parse_frontmatter(skill_md: Path) -> dict[str, Any] | None:
    """Parse SKILL.md frontmatter YAML. Returns None (skip) on any error."""
    try:
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return None
        parts = text.split("---", 2)
        if len(parts) < 3:
            return None
        data = yaml.safe_load(parts[1]) or {}
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def _normalize_paths(entries: list[Any]) -> list[tuple[str, dict[str, Any]]]:
    """Normalize writes/updates entries to [(path, meta_dict)].

    Accepts plain strings ("path") or dicts ({"file": "path", "mode": ...}).
    """
    out: list[tuple[str, dict[str, Any]]] = []
    for e in entries or []:
        if isinstance(e, str):
            out.append((e, {}))
        elif isinstance(e, dict) and "file" in e:
            meta = {k: v for k, v in e.items() if k != "file"}
            out.append((str(e["file"]), meta))
    return out


def check_skill_contracts(skills_dir: Path | None = None) -> list[str]:
    """Validate all skill SKILL.md files. Returns issue strings (empty == pass).

    Args:
        skills_dir: directory containing skill subdirs. Defaults to the
            project skills/ dir (shenbi.gates.shared.SKILLS).
    """
    if skills_dir is None:
        from shenbi.gates.shared import SKILLS

        skills_dir = SKILLS

    issues: list[str] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_md.parent.name
        fm = _parse_frontmatter(skill_md)
        if fm is None:
            continue  # malformed frontmatter surfaces in its own checks

        desc = str(fm.get("description", ""))
        if len(desc) > DESCRIPTION_MAX_CHARS:
            issues.append(f"G0.sc.desc_too_long:{skill_name}:{len(desc)}")
        if desc and _desc_has_behavioral_text(desc):
            issues.append(f"G0.sc.desc_has_behavior:{skill_name}")

        contract = fm.get("contract")
        if not isinstance(contract, dict):
            continue  # missing contract surfaces in its own checks

        writes = _normalize_paths(contract.get("writes", []))
        updates = _normalize_paths(contract.get("updates", []))

        # writes / updates disjoint
        write_paths = {p for p, _ in writes}
        update_paths = {p for p, _ in updates}
        overlap = write_paths & update_paths
        if overlap:
            issues.append(f"G0.sc.write_update_overlap:{skill_name}:{sorted(overlap)}")

        # every write/update entry must declare a mode (semantics)
        for path, meta in writes + updates:
            if "mode" not in meta:
                issues.append(f"G0.sc.missing_write_semantics:{skill_name}:{path}")

    return issues
