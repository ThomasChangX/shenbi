"""G4 checker for shenbi-state-settling."""

from __future__ import annotations
from shenbi.status import GateStatus
from typing import Any
from datetime import UTC, datetime, timedelta
from pathlib import Path
import json
import re

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_input_path,
)

# Known parameter-agent identifiers that must NOT appear in character_matrix
_PARAMETER_AGENT_NAMES = {"冷", "光", "安静", "缺口", "在场于", "参数", "槽位"}


def _live_sibling(pf: Path) -> Path | None:
    """The committed (non-staging) sibling of a staged truth file, or None."""
    if "staging" not in pf.parts:
        return None
    live = Path(*[p for p in pf.parts if p != "staging"])
    return live if live.exists() else None


def _h2_headings(text: str) -> set[str]:
    """Section titles (H2, leading #'s and numbering stripped for compare)."""
    out: set[str] = set()
    for line in text.split("\n"):
        m = re.match(r"^##\s+(.*)$", line.strip())
        if m:
            title = re.sub(r"^[一二三四五六七八九十\d]+[、.．]\s*", "", m.group(1).strip())
            if title:
                out.add(title)
    return out


def _check_matrix_structure(pf: Path) -> list[str]:
    """Structural-preservation guard for a STAGED character_matrix (probe
    session 2026-09-29: 12 template regenerations collapsed the live 100+
    line matrix — R1-R28 信息边界 and all Re-sync history deleted — while
    the gate PASSed vacuously). An increment must keep the live body mass,
    the 信息边界 section, and every Re-sync heading.

    Fixcheck ch1/ch2 (2026-09-29): line count alone cannot catch a
    same-size-or-bigger FORMAT REPLACEMENT — the settle writer restructured
    the matrix into a self-invented schema three times (121/140-line files
    passing the 0.9x line check while dropping every live section). A
    staged increment must therefore preserve the live H2 section set
    verbatim; new appended sections are allowed, live sections are not.
    """
    live = _live_sibling(pf)
    if live is None:
        return []
    issues: list[str] = []
    staged_text = pf.read_text(encoding="utf-8")
    live_text = live.read_text(encoding="utf-8")
    staged_lines = [l for l in staged_text.split("\n") if l.strip()]
    live_lines = [l for l in live_text.split("\n") if l.strip()]
    if live_lines and len(staged_lines) < len(live_lines) * 0.9:
        issues.append(
            f"G4.ss.matrix_structure:{pf}:line_collapse:"
            f"staged={len(staged_lines)}<live*0.9={int(len(live_lines) * 0.9)} "
            f"(template regeneration — rebuild as live increment)"
        )
    if "## 信息边界" in live_text and "## 信息边界" not in staged_text:
        issues.append(f"G4.ss.matrix_structure:{pf}:boundary_dropped")
    live_resync = len(re.findall(r"## .*Re-sync", live_text))
    staged_resync = len(re.findall(r"## .*Re-sync", staged_text))
    if staged_resync < live_resync:
        issues.append(
            f"G4.ss.matrix_structure:{pf}:resync_history_dropped:"
            f"staged={staged_resync}<live={live_resync}"
        )
    dropped = _h2_headings(live_text) - _h2_headings(staged_text)
    if dropped:
        issues.append(
            f"G4.ss.matrix_structure:{pf}:sections_dropped:"
            f"{sorted(dropped)} (format replacement — keep every live section, "
            f"append new ones)"
        )
    return issues


def _check_produced_at(content: str, fp: str) -> list[str]:
    """produced_at reality check (probe: fabricated four times — 12:00:00Z
    placeholders, mismatched first-dispatch times, a future-dated value).
    """
    start = content.find("{")
    if start < 0:
        return []
    try:
        data = json.loads(content[start:])
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []
    produced = data.get("produced_at")
    if not isinstance(produced, str) or not produced:
        return []
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", produced)
    if not m:
        return [f"G4.ss.produced_at:{fp}:unparseable:{produced}"]
    if m.group(5) == "00" and m.group(6) == "00":
        return [f"G4.ss.produced_at:{fp}:placeholder:{produced}"]
    try:
        ts = datetime.fromisoformat(produced.replace("Z", "+00:00"))
    except ValueError:
        return [f"G4.ss.produced_at:{fp}:unparseable:{produced}"]
    if ts > datetime.now(UTC) + timedelta(minutes=5):
        return [f"G4.ss.produced_at:{fp}:future:{produced}"]
    return []


def _validate_character_matrix(
    content: str,
    known_parameter_agents: set[str] | None = None,
) -> list[str]:
    """Validate that character_matrix.md does not contain parameter agents.

    Parameter agents (冷, 光, 安静, etc.) must be written to
    ``particle_ledger.md``, not to ``character_matrix.md``.

    Returns:
        List of issue strings (empty if valid).
    """
    agents = known_parameter_agents or _PARAMETER_AGENT_NAMES
    issues: list[str] = []

    # Only check the content after the frontmatter, excluding the 角色定义 section
    body = content
    if "---" in content:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]

    # Find the 角色定义 section boundaries
    def_section = ""
    if "## 角色定义" in body:
        def_parts = body.split("## 角色定义", 1)
        if len(def_parts) > 1:
            def_section = def_parts[1].split("\n## ", 1)[0]

    for agent in agents:
        # Token-level match: a parameter agent is a standalone NAME (its own
        # cell/word), not a substring of ordinary vocabulary — "冷" as an
        # agent must not fire on descriptors like "冷静" (canary ch1: 老头's
        # personality column tripped the bare-substring blacklist).
        agent_re = re.compile(rf"(?<![\u4e00-\u9fff]){re.escape(agent)}(?![\u4e00-\u9fff])")
        if agent_re.search(body):
            # Check if agent appears in per-chapter state sections (not 角色定义)
            state_sections = body
            if def_section:
                state_sections = body.replace(def_section, "")
            if agent_re.search(state_sections):
                issues.append(f"G4.ss.parameter_agent_in_character_matrix: {agent}")

    return issues


def g4_state_settling(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """State settling: current_state has position, char_matrix has characters, summaries appended, emotional arcs."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.ss.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        if "current_state" in str(fp):
            # Accept: ## 位置, ### 位置变化, 当前位置, 场景位置, etc.
            if not re.search(r"#{1,4}\s*(位置|当前位置|场景位置|地点)", content):
                c.append(
                    {
                        "id": "G4.ss.position",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no position/location heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.position", "file": fp, "s": GateStatus.PASS})

        if "character_matrix" in str(fp):
            # Accept: ## 已登场角色, ## 角色, ## 出场角色, ## 登场人物, ## 人物, etc.
            if not re.search(r"#{1,4}\s*(已登场角色|出场角色|登场人物|角色|人物)", content):
                c.append(
                    {
                        "id": "G4.ss.characters",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no character heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.characters", "file": fp, "s": GateStatus.PASS})

            # G4.ss.parameter_agent_in_character_matrix: prevent parameter agent
            # names from leaking into character_matrix instead of particle_ledger
            matrix_issues = _validate_character_matrix(content)
            if matrix_issues:
                mf.extend(matrix_issues)

            # Structural preservation vs the live sibling (probe session
            # 2026-09-29: template regeneration was invisible to the gate).
            mf.extend(_check_matrix_structure(pf))

        if "state-settling-decisions" in str(fp):
            mf.extend(_check_produced_at(content, fp))

        if "chapter_summaries" in str(fp):
            if not re.search(r"#{1,4}\s*第\d+章", content):
                c.append(
                    {
                        "id": "G4.ss.summaries",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no chapter summary heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.summaries", "file": fp, "s": GateStatus.PASS})

        if "emotional_arcs" in str(fp):
            if not re.search(r"#{1,4}\s*第\d+章", content):
                c.append(
                    {
                        "id": "G4.ss.arcs",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no emotional arc chapter heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.arcs", "file": fp, "s": GateStatus.PASS})

        if "particle_ledger" in str(fp):
            # Accept: 粒子账本, 粒子记录, particle ledger, 账本, etc.
            if not re.search(
                r"(粒子账本|粒子记录|particle.*ledger|账本|资源)", content, re.IGNORECASE
            ):
                c.append(
                    {
                        "id": "G4.ss.particle_ledger",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no particle ledger heading found",
                    }
                )
            else:
                c.append({"id": "G4.ss.particle_ledger", "file": fp, "s": GateStatus.PASS})

        if "pending_hooks" in str(fp):
            if "state" not in content:
                mf.append(f"G4.ss.no_hook_state:{fp}")
            else:
                c.append({"id": "G4.ss.pending_hooks", "file": fp, "s": GateStatus.PASS})

    if not fps:
        c.append({"id": "G4.ss", "s": GateStatus.SKIP, "r": "no files"})

    if mf:
        return fail("G4-state-settling", c, "scoring", mf)
    return passed("G4-state-settling", c)
