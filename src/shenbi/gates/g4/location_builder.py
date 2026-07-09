"""G4 checker for shenbi-location-builder."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

from shenbi.gates.shared import (
    PROJECT,
    fail,
    passed,
)
from shenbi.paths import RoundPaths


def g4_location_builder(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Location builder: each location has layout (>=200 chars), atmosphere (>=150 chars),
    functional events.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    if rd is None and project_dir is None:
        raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
    rp = RoundPaths(
        round_dir=Path(str(rd or project_dir)),
        project_dir=Path(str(project_dir or rd)),
        repo_root=Path(repo_root or PROJECT),
    )

    loc_path = rp.read("world/locations.md")
    if not loc_path.exists():
        mf.append("G4.locations.not_found")
    else:
        content = loc_path.read_text(encoding="utf-8")
        locations = re.findall(r"## 地点[：:]", content)
        if not locations:
            mf.append("G4.lb.no_locations")
        else:
            valid = 0
            for match in re.finditer(r"## 地点[：:].*?\n(?=## 地点|\Z)", content, re.DOTALL):
                loc_text = match.group()
                layout_match = re.search(
                    r"###\s*(?:\d+\.?\s*)?(?:布局描述|空间布局)\n(.*?)(?=###|\Z)",
                    loc_text,
                    re.DOTALL,
                )
                layout_len = len(layout_match.group(1).strip()) if layout_match else 0
                atmo_match = re.search(
                    r"###\s*(?:\d+\.?\s*)?(?:氛围锚点|感官锚点)\n(.*?)(?=###|\Z)",
                    loc_text,
                    re.DOTALL,
                )
                atmo_len = len(atmo_match.group(1).strip()) if atmo_match else 0
                has_events = bool(re.search(r"### 功能事件", loc_text))
                if layout_len >= 200 and atmo_len >= 150 and has_events:
                    valid += 1
            min_required = max(3, round(len(locations) * 0.5))
            if valid < min_required:
                mf.append(f"G4.lb.complete:{valid}/{len(locations)}_need_{min_required}")
            else:
                c.append(
                    {"id": "G4.lb", "s": "PASS", "locations": len(locations), "complete": valid}
                )

    if mf:
        return fail("G4-location-builder", c, "scoring", mf)
    return passed("G4-location-builder", c)
