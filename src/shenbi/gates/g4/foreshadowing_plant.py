"""G4 checker for shenbi-foreshadowing-plant."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

import yaml

from shenbi.gates.shared import (
    fail,
    passed,
)


def g4_foreshadowing_plant(fps: list[str], rd: str | None = None) -> str:
    """Foreshadowing plant: hook metadata completeness, depends_on not null, ops <= 8, SMOKESCREEN check."""
    c: list[dict[str, Any]] = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.fp.not_found:{fp}")
            continue

        # Read hooks from ## hooks body section (not frontmatter — hook arrays
        # can be large and frontmatter is harder to edit manually)
        try:
            content = pf.read_text(encoding="utf-8")
        except Exception:
            mf.append(f"G4.fp.read_error:{fp}")
            continue
        hooks: list[dict[str, Any]] = []
        hooks_match = re.search(r"## hooks\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if hooks_match:
            try:
                loaded: Any = yaml.safe_load(hooks_match.group(1))
                hooks = loaded if isinstance(loaded, list) else []
            except Exception:
                pass

        if not hooks:
            mf.append(f"G4.fp.no_hooks:{fp}")
            continue

        for h in hooks:
            hid = h.get("id", "?")
            required = [
                "type",
                "dimension",
                "subtlety",
                "cultivation_interval",
                "max_distance",
                "escalation_curve",
            ]
            for f in required:
                if f not in h:
                    mf.append(f"G4.fp.{hid}.missing_{f}")

            if h.get("depends_on") is None:
                mf.append(f"G4.fp.{hid}.depends_on_null")

            if h.get("type") == "SMOKESCREEN":
                notes = h.get("notes", "")
                if len(notes) < 50 or not re.search(r"如果|若|when|if|则|then", notes):
                    mf.append(f"G4.fp.{hid}.smokescreen_no_exit")

        # plant+reinforce+trigger+resolve ops <= 8
        total_ops = sum(
            1 for h in hooks if h.get("operation") in ("plant", "reinforce", "trigger", "resolve")
        )
        if total_ops > 8:
            mf.append(f"G4.fp.ops:{total_ops}>8")
        else:
            c.append({"id": "G4.fp.ops", "file": fp, "s": "PASS", "count": total_ops})

    if not fps:
        c.append({"id": "G4.fp", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-foreshadowing-plant", c, "scoring", mf)
    return passed("G4-foreshadowing-plant", c)
