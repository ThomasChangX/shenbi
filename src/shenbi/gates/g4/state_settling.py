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


def _content_stream(text: str) -> list[str]:
    """Content-bearing lines: every non-empty line except the frontmatter
    block, table rows (``|`` — upsertable by key), and ``>`` annotation
    lines (volatile counts/notes). These three are the only legitimate
    mutation surfaces of a settle increment; everything else is base mass.
    """
    out: list[str] = []
    in_fm = False
    first = True
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if first:
            first = False
            if s == "---":
                in_fm = True
                continue
        if in_fm:
            if s == "---":
                in_fm = False
            continue
        if s.startswith("|") or s.startswith(">"):
            continue
        out.append(s)
    return out


#: pending_hooks per-hook bullets that legitimately mutate every chapter —
#: lifecycle transitions, evidence citations, and notes. Everything else in a
#: hook block (headings, type/埋设/trigger_condition/resolve_condition/
#: subtlety/depends_on) is base mass and must survive settles verbatim.
_HOOKS_VOLATILE_RE = re.compile(r"^- (?:lifecycle_state|证据|notes|last_reinforced)\s*[:：]")

#: The MH detail blocks combine stable and volatile fields on one line
#: (``- type: … ｜ dimension: … ｜ lifecycle_state: …``); a legitimate
#: lifecycle transition mutates that line. Normalize the volatile VALUE to a
#: sentinel so the stable parts stay comparable while transitions pass.
_HOOKS_LIFECYCLE_VALUE_RE = re.compile(r"lifecycle_state\s*[:：][^｜]*")


def _hooks_content_stream(text: str) -> list[str]:
    """Content stream for pending_hooks with volatile-field exemption."""
    out: list[str] = []
    for line in _content_stream(text):
        s = line.strip()
        if _HOOKS_VOLATILE_RE.match(s):
            continue
        out.append(_HOOKS_LIFECYCLE_VALUE_RE.sub("lifecycle_state:~", line))
    return out


def _dropped_content_lines(
    live_text: str, staged_text: str, samples: int = 3, hooks: bool = False
) -> list[str]:
    """Live content lines that do not survive (in order) in the staged file.

    Order-preserving subsequence check: a settle increment may append and
    upsert, but live prose/headings/bullets must appear in the staged file
    in their original order. Reordering is a format replacement.
    """
    stream_fn = _hooks_content_stream if hooks else _content_stream
    live_stream = stream_fn(live_text)
    staged_iter = iter(stream_fn(staged_text))
    missing: list[str] = []
    for line in live_stream:
        if any(s == line for s in staged_iter):
            continue
        missing.append(line)
    total = len(missing)
    if not total:
        return []
    shown = [m[:24] + ("…" if len(m) > 24 else "") for m in missing[:samples]]
    return [f"content_dropped:{total}行 e.g. {shown}"]


def _check_escape_corruption(pf: Path, live_text: str, staged_text: str) -> list[str]:
    """Flag ``>`` annotation lines HTML-escaped to ``&gt;`` in the staged copy.

    Probe2 ch2 settle: seven matrix base annotations arrived as ``&gt; …`` —
    the content survives but the blockquote semantics are destroyed, and the
    escaped form evades the ``>``-exempt content stream. Escaping is never a
    legitimate settle mutation: flag whenever the staged copy introduces
    ``&gt;`` sequences absent from the live base.
    """
    if "&gt;" in staged_text and "&gt;" not in live_text:
        count = staged_text.count("&gt;")
        return [
            f"G4.ss.escape_corruption:{pf}: {count} 处 「>」被转义为「&gt;」"
            "（注解行格式损毁——以 live 原样保全）"
        ]
    return []


def _check_matrix_structure(pf: Path) -> list[str]:
    """Content-preservation guard for a STAGED character_matrix.

    Fixcheck probe (2026-09-29): seven consecutive settle rewrites failed
    as template regenerations — line collapse, format replacement,
    same-size replacement, heading-preserving content swap — and each
    structural tightening was bypassed by the next variant. Root cause:
    the settle contract did not declare ``truth/character_matrix.md`` as a
    read, so the writer never saw the base it was told to preserve (fixed
    at the contract; this check is the mechanical enforcement of the
    adjudicated acceptance standard). Apart from frontmatter, table rows
    and ``>`` annotations, every live content line must survive in order.
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
            "(template regeneration — rebuild as live increment)"
        )
    issues.extend(
        f"G4.ss.matrix_structure:{pf}:{detail} "
        "(format replacement — re-emit ONLY this chapter's increment: the "
        "new/changed keyed rows plus this chapter's increment section; do "
        "NOT reproduce or re-emit other sections of the live file)"
        for detail in _dropped_content_lines(live_text, staged_text)
    )
    issues.extend(_check_escape_corruption(pf, live_text, staged_text))
    return issues


_HOOK_ROW_KEY_RE = re.compile(r"^\|\s*(H-\d{3}|MH-\d{3})\s*\|")


def _row_stable_cells(row: str) -> tuple[str, ...]:
    """All table cells except the LAST (status) column, whitespace-normalized."""
    cells = [c.strip() for c in row.split("|")[1:-1]]
    return tuple(cells[:-1])


def _dropped_hook_rows(live_text: str, staged_text: str) -> list[str]:
    """Keyed hook rows (H-*/MH-*) whose STABLE planning columns were
    rewritten or which vanished outright.

    Probe2 ch1/ch2: the H-001/H-005 seed rows had 埋设位置/计划回收
    replaced with per-chapter reinforcement notes while the status column
    stayed plausible — the whole-row table exemption made this G4-invisible
    twice. Same-key rows may legitimately change ONLY the final status
    column; per-chapter reinforcements belong in the detail blocks.
    """
    staged_rows: dict[str, str] = {}
    for line in staged_text.split("\n"):
        m = _HOOK_ROW_KEY_RE.match(line.strip())
        if m:
            staged_rows.setdefault(m.group(1), line.strip())
    issues: list[str] = []
    for line in live_text.split("\n"):
        s = line.strip()
        m = _HOOK_ROW_KEY_RE.match(s)
        if not m:
            continue
        key = m.group(1)
        staged_row = staged_rows.get(key)
        if staged_row is None:
            issues.append(
                f"hook_row_dropped:{key} "
                "(the registry row vanished — keep registry rows untouched "
                "except the final status cell)"
            )
        elif _row_stable_cells(s) != _row_stable_cells(staged_row):
            issues.append(
                f"hook_row_stable_columns_rewritten:{key} "
                "(registry rows are not chapter increments — a state-settling "
                "output must OMIT them entirely (the status column belongs "
                "to foreshadowing-track); a lifecycle writer updating the "
                "status must re-emit every stable cell VERBATIM from the "
                "live row, changing ONLY the final status cell. Either way, "
                "per-chapter reinforcement data belongs in the hook "
                "section's colon bullets, never in registry columns)"
            )
    return issues


def _check_hooks_structure(pf: Path) -> list[str]:
    """Content-preservation guard for a STAGED pending_hooks.

    Probe2 ch1/ch2 settles (2026-10-01): the settle writer damaged
    truth/pending_hooks.md twice — seed-row column overwrites (table rows,
    still the documented same-key blind spot), dropped MH detail lines
    (type/埋设/trigger/resolve/depends_on), and overwritten per-chapter
    increment sections — while G4 passed both times because the guard only
    ran on character_matrix. Same enforcement as the matrix guard, with the
    hooks file's legitimately volatile bullets (lifecycle_state/证据/notes)
    exempted alongside the three generic mutation surfaces.
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
            f"G4.ss.hooks_structure:{pf}:line_collapse:"
            f"staged={len(staged_lines)}<live*0.9={int(len(live_lines) * 0.9)} "
            "(base mass lost — rebuild as live increment)"
        )
    issues.extend(
        f"G4.ss.hooks_structure:{pf}:{detail} "
        "(hook base lines dropped — re-emit ONLY the affected hook's section "
        "as named-field colon bullets (e.g. `- last_reinforced: N`); the "
        "program merges them into the live block in place — never re-emit "
        "the hook's stable lines: type/plant_ch/trigger_condition/"
        "resolve_condition/subtlety/depends_on)"
        for detail in _dropped_content_lines(live_text, staged_text, hooks=True)
    )
    # Hook-row findings carry their own row-scoped remediation text.
    issues.extend(
        f"G4.ss.hooks_structure:{pf}:{detail}"
        for detail in _dropped_hook_rows(live_text, staged_text)
    )
    issues.extend(_check_escape_corruption(pf, live_text, staged_text))
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
            # Structural preservation vs the live sibling (probe2 ch1/ch2:
            # the settle writer damaged pending_hooks twice under a
            # token-only check — see _check_hooks_structure).
            mf.extend(_check_hooks_structure(pf))

    if not fps:
        c.append({"id": "G4.ss", "s": GateStatus.SKIP, "r": "no files"})

    if mf:
        return fail("G4-state-settling", c, "scoring", mf)
    return passed("G4-state-settling", c)
