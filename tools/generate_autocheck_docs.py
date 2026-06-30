#!/usr/bin/env python3
"""Generate 'auto-checkable' doc sections from contract models (spec P6).

Reads Pydantic contract models from contracts/skills/ and renders a markdown
block into each skill's SKILL.md. The block is delimited by sentinels
(AUTO-CHECK-START / AUTO-CHECK-END); regeneration replaces the block wholesale.
CI runs this + git diff to reject manual edits.

Usage: python tools/generate_autocheck_docs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"

BANNER = "<!-- AUTO-CHECK-START -->"
ENDER = "<!-- AUTO-CHECK-END -->"

_SKIP_CONSTS = frozenset({"AGGREGATION_FORMULA", "BANNER", "ENDER"})


def _get_module_constants(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Extract uppercase module-level constants (int/float/dict)."""
    mod = sys.modules.get(model_cls.__module__)
    if mod is None:
        return {}
    out: dict[str, Any] = {}
    for name in dir(mod):
        if name.startswith("_") or name in _SKIP_CONSTS:
            continue
        if not (name.isupper() or name.endswith(("_THRESHOLDS", "_WEIGHT"))):
            continue
        val = getattr(mod, name, None)
        if isinstance(val, (int, float, dict)):
            out[name] = val
    return out


def _type_str(t: Any) -> str:
    if t is None:
        return "auto"
    name = getattr(t, "__name__", None)
    if isinstance(name, str):
        return name
    return str(t)


def _computed_fields_table(model_cls: type[BaseModel]) -> str:
    lines = ["| name | type |", "|------|------|"]
    for name, info in model_cls.model_computed_fields.items():
        rt = getattr(info, "return_type", None)
        lines.append(f"| {name} | {_type_str(rt)} |")
    return "\n".join(lines)


def _validator_names(model_cls: type[BaseModel]) -> list[str]:
    decorators = getattr(model_cls, "__pydantic_decorators__", None)
    if decorators is None:
        return []
    return sorted(decorators.model_validators.keys())


def render_autocheck(model_cls: type[BaseModel]) -> str:
    """Render the auto-checkable markdown block for a contract model."""
    lines = [BANNER, "", "## auto-check (generated -- do not edit)", ""]

    consts = _get_module_constants(model_cls)
    if consts:
        lines.append("### constants")
        lines.append("")
        lines.append("| name | value |")
        lines.append("|------|-------|")
        for name, val in sorted(consts.items()):
            lines.append(f"| {name} | {val} |")
        lines.append("")

    mod = sys.modules.get(model_cls.__module__)
    if mod is not None:
        formula = getattr(mod, "AGGREGATION_FORMULA", None)
        if formula:
            lines.append("### formula")
            lines.append("")
            lines.append("```")
            lines.append(str(formula))
            lines.append("```")
            lines.append("")

    if model_cls.model_computed_fields:
        lines.append("### computed fields")
        lines.append("")
        lines.append(_computed_fields_table(model_cls))
        lines.append("")

    vals = _validator_names(model_cls)
    if vals:
        lines.append("### invariants")
        lines.append("")
        for v in vals:
            desc = v.lstrip("_").replace("_", " ")
            lines.append(f"- {desc}")
        lines.append("")

    lines.append(ENDER)
    return "\n".join(lines) + "\n"


_PATTERN = re.compile(re.escape(BANNER) + r".*?" + re.escape(ENDER) + r"\n?", re.DOTALL)
_FRONTMATTER_RE = re.compile(r"^(---\n.*?\n---\n)(.*)$", re.DOTALL)


def inject_block(skill_md: Path, block: str) -> bool:
    """Replace the auto-check block in a SKILL.md. Return True if changed."""
    text = skill_md.read_text(encoding="utf-8")
    if _PATTERN.search(text):
        new_text = _PATTERN.sub(block, text, count=1)
    else:
        m = _FRONTMATTER_RE.match(text)
        new_text = m.group(1) + block + "\n" + m.group(2) if m else block + "\n" + text
    if new_text != text:
        skill_md.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> int:
    """Render auto-check blocks for every registered skill's SKILL.md."""
    sys.path.insert(0, str(SRC))
    from shenbi.contracts.registry import REGISTRY  # noqa: PLC0415
    from shenbi.gates.shared import SKILLS  # noqa: PLC0415

    changed: list[str] = []
    for skill_name, model_cls in sorted(REGISTRY.items()):
        skill_md = SKILLS / skill_name / "SKILL.md"
        if not skill_md.exists():
            continue
        block = render_autocheck(model_cls)
        if inject_block(skill_md, block):
            changed.append(str(skill_md))
    if changed:
        for c in changed:
            print(f"updated: {c}")
    else:
        print("all up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
