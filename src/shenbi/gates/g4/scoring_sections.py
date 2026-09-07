"""G4 checker for the score-family skills (arc / stratum / volume).

C37 F427: the three former copy-paste checkers (score_arc.py /
score_stratum.py / score_volume.py) are unified into one parameterized
checker. Behavior is unchanged — each registration point passes its skill
id, gate name, message-code prefix, and required sections.
"""

from __future__ import annotations

import re
from typing import Any

from shenbi.gates.shared import fail, passed, resolve_input_path
from shenbi.status import GateStatus

# (skill id, gate name, code prefix) — the three former checkers differed
# ONLY in these strings plus identical Route C / Route A(锚点) requirements.
_SCORE_FAMILY: list[tuple[str, str, str]] = [
    ("shenbi-score-arc", "G4-score-arc", "G4.arc"),
    ("shenbi-score-stratum", "G4-score-stratum", "G4.str"),
    ("shenbi-score-volume", "G4-score-volume", "G4.vol"),
]


def g4_scoring_sections(
    fps: list[str],
    gate_name: str,
    code_prefix: str,
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Validate score-family output has Route C + Route A sections."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"{code_prefix}.not_found:{fp}")
            continue
        content = pf.read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", "", content)
        if "RouteC" not in normalized:
            mf.append(f"{code_prefix}.no_route_c:must have Route C section")
        if "RouteA" not in normalized and "锚点" not in content:
            mf.append(f"{code_prefix}.no_route_a:must have Route A anchor section")
    if not fps:
        c.append({"id": code_prefix, "s": GateStatus.SKIP, "r": "no files"})
    if mf:
        return fail(gate_name, c, "scoring", mf)
    return passed(gate_name, c)


def register_score_checkers(table: dict[str, Any]) -> None:
    """Register one parameterized checker per score-family skill."""
    for skill_id, gate_name, code_prefix in _SCORE_FAMILY:
        table[skill_id] = (
            lambda fps, rd=None, project_dir=None, repo_root=None, _gate=gate_name, _code=code_prefix: (
                g4_scoring_sections(fps, _gate, _code, rd, project_dir, repo_root)
            )
        )
