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
from shenbi.pipeline.truth_io import HOOKS_VOLATILE_FIELDS, hooks_stable_fields_hint

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
#: rendered from the shared HOOKS_VOLATILE_FIELDS contract (truth_io) so
#: the gate exemption and the prompt-side ban list can never drift apart
#: again (phase3 esc#1: they had). Everything else in a hook block is base
#: mass and must survive settles verbatim.
_HOOKS_VOLATILE_RE = re.compile(
    r"^- (?:" + "|".join(re.escape(f) for f in HOOKS_VOLATILE_FIELDS) + r")\s*[:：]"
)

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


#: Initialized shells carry ``（待填充…）`` placeholder prose inside section
#: spans; the contract's first-fill (full-table escape) legitimately consumes
#: them via section replacement. #18-8b (probe24): not base mass.
_PLACEHOLDER_LINE_RE = re.compile(r"^（待填充")


def _dropped_content_lines(
    live_text: str, staged_text: str, samples: int = 3, hooks: bool = False
) -> list[str]:
    """Live content lines that do not survive (in order) in the staged file.

    Order-preserving subsequence check: a settle increment may append and
    upsert, but live prose/headings/bullets must appear in the staged file
    in their original order. Reordering is a format replacement.

    Per-line pointer semantics (probe18 adjudication #005): the old
    shared-iterator ``any()`` consumed the staged stream past the first
    miss, cascading every subsequent live line into the count — 2 real
    losses reported as 153, with sample lines that were present in staging.
    A miss now records exactly that line; the pointer stays put.

    hooks=True compares per ``### MHxx`` section (phase3 esc#1): generic
    same-value stable lines (``- plant_chapter: 2``) are indistinguishable
    across sections, and the flat order-preserving scan let a rewritten
    line match a LATER hook's same-value line, jumping the pointer a
    section ahead — 6 real violations inflated to 65 reported, with
    samples the model had never touched (un-actionable feedback, three
    burned attempts). Section scoping restores line identity.
    """
    if hooks:
        return _dropped_hook_section_lines(live_text, staged_text, samples)
    return _format_drops(
        _seq_drops(
            [l for l in _content_stream(live_text) if not _PLACEHOLDER_LINE_RE.match(l.strip())],
            _content_stream(staged_text),
        ),
        samples,
    )


def _seq_drops(live_stream: list[str], staged_stream: list[str]) -> list[str]:
    """Order-preserving scan with non-consuming miss (probe18 #005)."""
    missing: list[str] = []
    i = 0
    for line in live_stream:
        j = i
        while j < len(staged_stream) and staged_stream[j] != line:
            j += 1
        if j < len(staged_stream):
            i = j + 1  # consume the match
        else:
            missing.append(line)  # probe pointer stays at i for the next line
    return missing


def _split_hook_sections(stream: list[str]) -> dict[str, list[str]]:
    """Partition a hooks content stream keyed by ``###`` section heading.

    Lines before the first ``###`` (frontmatter-stripped headings, prose)
    form the ``""`` preamble section. Duplicate headings keep their lines
    merged — only content preservation matters here, not uniqueness.
    """
    sections: dict[str, list[str]] = {"": []}
    key = ""
    for line in stream:
        if line.lstrip().startswith("### "):
            key = line.strip()
            sections.setdefault(key, [])
            continue
        sections[key].append(line)
    return sections


def _dropped_hook_section_lines(live_text: str, staged_text: str, samples: int) -> list[str]:
    """Section-scoped dropped-line report for pending_hooks (phase3 esc#1)."""
    live_secs = _split_hook_sections(_hooks_content_stream(live_text))
    staged_secs = _split_hook_sections(_hooks_content_stream(staged_text))
    missing: list[str] = []
    for key, live_lines in live_secs.items():
        if not live_lines and not key:
            continue
        staged_lines = staged_secs.get(key)
        if staged_lines is None:
            missing.extend(live_lines)  # the whole hook block vanished
            continue
        missing.extend(
            [
                l
                for l in _seq_drops(live_lines, staged_lines)
                if not _PLACEHOLDER_LINE_RE.match(l.strip())
            ]
        )
    return _format_drops(missing, samples)


def _format_drops(missing: list[str], samples: int) -> list[str]:
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


def _current_settle_chapter(pf: Path) -> int | None:
    """Chapter the staged settle owns, from the sibling decisions sidecar.

    probe31 ch2 escalation: the audit-routed re-settle's keyed-upsert
    ATOMICALLY REPLACES the current chapter's own increment block; without
    chapter-awareness the matrix guard flagged the replaced bullets as
    content_dropped and every re-settle that touched its own block died —
    a deterministic deadlock, not model noise (2 byte-identical attempts).
    Unparseable/absent sidecar = no exemption (conservative).
    """
    sidecar = pf.parent / "state-settling-decisions.json"
    if not sidecar.exists():
        return None
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    chapter = payload.get("chapter") if isinstance(payload, dict) else None
    return chapter if isinstance(chapter, int) and chapter > 0 else None


def _strip_increment_section(live_text: str, chapter: int) -> str:
    """Drop the current chapter's own ``## 第N章状态增量`` span from the
    live text — that block is the merge-owned upsert unit, not base mass.
    Prior chapters' blocks stay (over-exemption guard is positional: only
    the span between this chapter's heading and the next ``##`` heading).
    """
    heading_re = re.compile(rf"^##\s*第{chapter}章状态增量\s*$")
    out: list[str] = []
    inside = False
    for line in live_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            inside = bool(heading_re.match(stripped))
            continue
        if inside:
            continue
        out.append(line)
    return "\n".join(out)


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
    # The current chapter's own increment block is the keyed-upsert unit a
    # re-settle owns (probe31 ch2); compare base mass only.
    _chapter = _current_settle_chapter(pf)
    if _chapter is not None:
        live_text = _strip_increment_section(live_text, _chapter)
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


#: Registry rows are keyed by their hook id wherever it starts the first
#: cell — the genesis live form ``| MH01（钩子名） | … |`` (id + name in one
#: cell, no hyphen) as well as legacy ``| MH-001 | … |`` (probe15 batch #10:
#: the hyphen-only family made this guard silently inert for live-form
#: tables). The lookahead requires a cell terminator so prose like
#: ``MH02编年`` never keys.
_HOOK_ROW_KEY_RE = re.compile(r"^\|\s*((?:MH|H|CP)-?\d{1,4})(?=[\s（(｜|]|$)")

_SEPARATOR_ROW_RE = re.compile(r"^[\s:\-|]+$")
_LIFECYCLE_HEADER_RE = re.compile(r"生命周期|状态")

#: Batch #27 (probe32 ch2): the foreshadowing-track's legal state chain
#: (skills/shenbi-foreshadowing-lifecycle SKILL.md — sole driver of hook
#: lifecycle state). Disjoint from the type vocabulary (ITEM/CHARACTER/
#: EVENT/INFORMATION/RULE/…) and the escalation-curve vocabulary
#: (RISING/STAIRCASE/…), so a column whose every hook-row value lands in
#: this set is unambiguously the lifecycle column.
_LIFECYCLE_VOCAB = {"PLANTED", "RELEVANT", "TRIGGERED", "RESOLVED"}


def _canon_hook_id(raw: str) -> str:
    """``MH-001`` ≡ ``MH01`` — mirrors truth_io.canon_hook_id (imported at
    call sites to keep the gates↔pipeline import direction cycle-free).
    """
    from shenbi.pipeline.truth_io import canon_hook_id

    return canon_hook_id(raw)


def _row_stable_cells(row: str, exempt: int | None = None) -> tuple[str, ...]:
    """All table cells except the LAST (status) column — and except *exempt*,
    the header-named lifecycle column — whitespace-normalized.
    """
    cells = [c.strip() for c in row.split("|")[1:-1]]
    if exempt is not None and 0 <= exempt < len(cells):
        cells = cells[:exempt] + cells[exempt + 1 :]
    return tuple(cells[:-1])


def _live_lifecycle_columns(live_text: str) -> dict[int, int]:
    """Map each live data-row line index → its table's lifecycle column.

    probe15's genesis 总览 table carries the lifecycle in column 2 of 8
    (``| MH01(名) | PLANTED | … |``); the last-cell-only exemption would
    flag every legitimate lifecycle bump (foreshadowing-track re-emits the
    changed row, lifecycle cell updated) as a stable-column rewrite. The
    column is located by the table header cell naming 当前生命周期/状态 —
    the same header key the truth-index parser keys on. Header detection
    does NOT require a separator row: the genesis template emits header
    directly above data rows.
    """
    lines = live_text.split("\n")
    out: dict[int, int] = {}
    exempt: int | None = None
    seen_header: int | None = None
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.split("|")[1:-1]]
        header_idx = next(
            (
                j
                for j, cell in enumerate(cells)
                if _LIFECYCLE_HEADER_RE.search(cell) and len(cell) <= 8
            ),
            None,
        )
        if header_idx is not None:
            exempt = header_idx
            seen_header = header_idx
            continue
        if exempt is None and seen_header is not None and _HOOK_ROW_KEY_RE.match(s):
            # #25-1 (probe25): the lifecycle appends new hook rows AFTER the
            # ### detail sections — a headerless continuation of the pool's
            # single registry table. Any hook-keyed row belongs to that table
            # and inherits its lifecycle column.
            exempt = seen_header
        if exempt is not None:
            out[i] = exempt
    if not out:
        # Batch #27 (probe32 ch2 4-attempt settle deadlock): a genesis live
        # registry can be entirely HEADERLESS (shell base, no bootstrap —
        # pending_hooks had no _TABLE_HEADER_BOOTSTRAP entry), leaving every
        # hook row without an exemption and framing the lifecycle writer's
        # legal PLANTED→RELEVANT bump as a settle-side stable rewrite.
        # Fallback: locate the lifecycle column by value vocabulary — the
        # column whose every hook-row cell is a known lifecycle state.
        hook_rows = [
            [c.strip() for c in line.strip().split("|")[1:-1]]
            for line in lines
            if _HOOK_ROW_KEY_RE.match(line.strip())
        ]
        if hook_rows:
            width = min(len(cells) for cells in hook_rows)
            for j in range(width):
                if all(cells[j].upper() in _LIFECYCLE_VOCAB for cells in hook_rows):
                    out.update(
                        {
                            i: j
                            for i, line in enumerate(lines)
                            if _HOOK_ROW_KEY_RE.match(line.strip())
                        }
                    )
                    break
    return out


def _dropped_hook_rows(live_text: str, staged_text: str) -> list[str]:
    """Keyed hook rows (H-*/MH-*/CP-*, any id form) whose STABLE planning
    columns were rewritten or which vanished outright.

    Probe2 ch1/ch2: the H-001/H-005 seed rows had 埋设位置/计划回收
    replaced with per-chapter reinforcement notes while the status column
    stayed plausible — the whole-row table exemption made this G4-invisible
    twice. Same-key rows may legitimately change ONLY the status column
    (plus the header-named lifecycle column); per-chapter reinforcements
    belong in the detail blocks.
    """
    staged_rows: dict[str, str] = {}
    for line in staged_text.split("\n"):
        m = _HOOK_ROW_KEY_RE.match(line.strip())
        if m:
            staged_rows.setdefault(_canon_hook_id(m.group(1)), line.strip())
    live_lines = live_text.split("\n")
    exempt_cols = _live_lifecycle_columns(live_text)
    issues: list[str] = []
    for i, line in enumerate(live_lines):
        s = line.strip()
        m = _HOOK_ROW_KEY_RE.match(s)
        if not m:
            continue
        key = _canon_hook_id(m.group(1))
        staged_row = staged_rows.get(key)
        if staged_row is None:
            issues.append(
                f"hook_row_dropped:{m.group(1)} "
                "(the registry row vanished — keep registry rows untouched "
                "except the final status cell)"
            )
        elif _row_stable_cells(s, exempt_cols.get(i)) != _row_stable_cells(
            staged_row, exempt_cols.get(i)
        ):
            issues.append(
                f"hook_row_stable_columns_rewritten:{m.group(1)} "
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
        f"the hook's stable lines: {hooks_stable_fields_hint()})"
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

    Detection policy (probe27 #019 root-cause fix): the bare agent name is
    a common Chinese word (缺口=deficit, 安静=quiet, 冷=cold, etc.) that
    appears freely in narrative prose. A parameter agent is only flagged
    when introduced with the explicit ``_param:`` tag prefix in the
    character_matrix content. The bare-token match alone is too noisy.

    Phrase-level match: a parameter agent occurrence is ``_param:<agent>``
    anywhere in the per-chapter state sections (outside 角色定义). Bare
    occurrences are tolerated as common Chinese vocabulary.

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

    state_sections = body
    if def_section:
        state_sections = body.replace(def_section, "")

    for agent in agents:
        # Phrase-level match: only flag if the agent is introduced with the
        # explicit `_param:` tag prefix. Bare occurrences of these words
        # are tolerated as common Chinese vocabulary (缺口=deficit, 冷=cold,
        # 安静=quiet, 光=light).
        agent_escaped = re.escape(agent)
        param_re = re.compile(rf"_param\s*[:：]\s*{agent_escaped}")
        if param_re.search(state_sections):
            issues.append(f"G4.ss.parameter_agent_in_character_matrix: {agent}")

    return issues


def _check_selections_coverage(fps: list[str], rd: str | None) -> list[str]:
    """#52 (probe21 adjudication #008): every staged truth target this settle
    emitted must be DECLARED in the decisions sidecar's selections — the
    rejected re-settlement declared 1/7 while touching seven files, hiding
    the ledger key-collapse from the review surface.

    Scope (probe22 adjudication #005): the obligation set is the skill's OWN
    contract targets, NOT every file under staging/truth —
    foreshadowing-lifecycle stages bridge_tracker.md into the same shared
    directory and the settle G4 file list globs it; demanding the settle
    sidecar declare a file its contract does not own is a false positive
    (declaring it would be the false report) and the retry loop becomes
    mathematically unsatisfiable — three deterministic escalation deaths in
    probe22 ch1. Cross-skill trespass stays owned by write-audit.

    The composite partition routes the sidecar to g4_decisions, so the
    sibling is located by convention: staging/truth/state-settling-decisions
    .json next to the staged truth targets. Parse/schema failures of the
    sidecar stay owned by g4_decisions.
    """
    staged = [fp.replace("\\", "/") for fp in fps if "staging/truth" in fp.replace("\\", "/")]
    if not staged:
        return []
    from shenbi.contracts import ContractError, load_contract

    try:
        own_targets = set(load_contract("shenbi-state-settling")["write_semantics"])
    except (ContractError, KeyError):
        own_targets = set()  # contract unavailable → keep the full staged-set obligation
    sidecar = resolve_input_path(staged[0], rd).parent / "state-settling-decisions.json"
    if not sidecar.exists():
        return []
    from shenbi.gates.shared import parse_decisions_payload

    try:
        _sc_text = sidecar.read_text(encoding="utf-8")
    except (OSError, ValueError):
        # audit-T8 round5 M-1（#52 期旧根清偿）：不可读/损坏 sidecar 按缺席
        # 处理——composite 层不再炸穿 _guarded_g4
        return []
    data, failures = parse_decisions_payload(_sc_text, str(sidecar), "G4.ss")
    if failures or not isinstance(data, dict):
        return []
    declared = {
        str(s.get("target", "")).replace("\\", "/").removeprefix("staging/")
        for s in data.get("selections") or []
        if isinstance(s, dict)
    }
    missing = sorted(
        {
            fp.removeprefix("staging/")
            for fp in staged
            if fp.endswith(".md")
            and (not own_targets or fp.removeprefix("staging/") in own_targets)
        }
        - declared
    )
    return [
        f"G4.ss.selections_uncovered:{m}"
        "（sidecar selections 未申报该实际产出目标——补齐全部触达目标的申报）"
        for m in missing
    ]


def g4_state_settling_check(
    project_dir: Path, sidecar_path: Path | None
) -> tuple[list[str], list[str]]:
    """Spec #80 T8 G4.ss — settle dual-write read-side checks (PURE reader).

    Returns ``(fail_issues, warn_notes)`` — audit-T8 C1/I3/M7/M8 shape.
    Registry lookups prefer the sidecar's staged sibling (this chapter's new
    rows live in staging/), falling back to committed truth/.

    ① sidecar lacks facts_ops while prop_registry shows a this-chapter row
      change -> compat-period WARN (not FAIL)
    ② ss.prop_row_match: the op chain's FINAL simulated owner per touched
      prop vs the markdown registry row owner (facts canonical — divergence
      FAIL; per-op ev.to would mis-fire on hop 1 of a legitimate same-chapter
      two-hop — audit-T8 round2 #1c)
    ③ ss.identity_row_match: POST-simulation facts alias set (this chapter's
      identity ops applied first — round2 I-3) <-> name_registry 别名/旌名
      rows, bidirectional, union of staged + committed rows, independent of
      identity_ops presence
    ④ ss.facts_ops: F16s simulate — chained dry-run each props/identity op
      against current facts; rejection-form ops FAIL (and require a sidecar
      rationale, P2.5); cross-commit fingerprint replays are skipped (same
      keys + multiset rule as the write side — audit-T8 round2 #1)
    Corrupt/unreadable facts files surface as structured ss.* issues, never
    raw exceptions (round2 M-1).
    """
    issues: list[str] = []
    warns: list[str] = []
    facts_dir = Path(project_dir) / "truth" / "facts"
    props_file = facts_dir / "props.json"
    identity_file = facts_dir / "identity.json"
    has_props = props_file.is_file()
    has_identity = identity_file.is_file()
    if sidecar_path is None or not sidecar_path.is_file():
        return issues, warns
    import json as _json
    from collections import Counter as _Counter
    from typing import Any as _Any

    try:
        doc = _json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError, UnicodeDecodeError):
        return issues, warns
    if not isinstance(doc, dict):
        # audit-T8 round3 I-3(c)：顶层非对象裸 AttributeError 会炸穿
        # _guarded_g4（只捕 ValueError），且抢占 g4_decisions 对同文件的
        # 精确 schema 报告——结构化 issue 让路
        return ["ss.facts_ops:非法形态——sidecar 顶层必须是 JSON 对象"], warns
    facts_ops = doc.get("facts_ops") or {}
    if not isinstance(facts_ops, dict):
        return ["ss.facts_ops:非法形态——facts_ops 必须是对象"], warns

    from pydantic import ValidationError

    from shenbi.exceptions import FactsOpRejectedError
    from shenbi.facts.enums import FactsDim
    from shenbi.facts.schemas import FactsFile, IdentityEvent, PropTransferEvent
    from shenbi.facts.store import (
        IDENTITY_REPLAY_KEYS,
        PROP_REPLAY_KEYS,
        apply_identity_op,
        apply_prop_op,
        replay_skip,
    )

    _staged_reg = sidecar_path.parent / "prop_registry.md"
    _staged_name_reg = sidecar_path.parent / "name_registry.md"
    chapter = doc.get("chapter")
    rationale = facts_ops.get("rationale")

    # ②+④ props op↔row reconciliation（链式模拟，audit-T8 M7 + round2 #1）。
    # 维文件缺席 ⇒ 不模拟（兼容期选择，audit-T8 round3 M-2：pipeline-init
    # 播种三维后可达性低；写侧 commit 时仍拒收非法 op）
    prop_ops = facts_ops.get("props") or []
    if has_props and prop_ops:
        try:
            current = FactsFile.model_validate_json(props_file.read_text(encoding="utf-8"))
            if current.dim is not FactsDim.PROPS:
                # audit-T8 round5 I-1：自洽错维文件过 schema 验（模型只验
                # 内部一致性），在访问器 props() 裸抛——槽位断言折算结构化
                raise ValueError(f"维度错位 dim={current.dim.value}（槽位期望 props）")
        except (OSError, ValueError) as _exc:
            # audit-T8 round2 M-1 + round4 I-1：裸上抛会被 CLI 折算成「文件
            # 路径参数非法」的误导报因；ValueError 宽捕同时覆盖
            # ValidationError 与 UnicodeDecodeError（非法 UTF-8）——结构化
            # FAIL 并指明修复对象
            issues.append(
                "ss.facts_ops:truth/facts/props.json 损坏/不可读/维度错位"
                f"（{_exc}）——G4 无法模拟，先修复 facts 文件本体"
            )
        else:
            touched: set[str] = set()
            seen: _Counter[tuple[_Any, ...]] = _Counter()
            for raw in prop_ops:
                try:
                    ev = PropTransferEvent.model_validate(raw)
                except ValidationError as exc:
                    issues.append(
                        f"ss.facts_ops:props op 结构非法（{exc.error_count()} 处）"
                        "——修正 sidecar 的 op 形态"
                    )
                    continue
                entry = ev.model_dump(by_alias=True)
                fp = tuple(entry.get(k) for k in PROP_REPLAY_KEYS)
                k = seen[fp]
                seen[fp] += 1
                if replay_skip(current.ops_log, entry, PROP_REPLAY_KEYS, k):
                    continue  # 跨提交指纹重放（写侧同键跳过）——不模拟不判非法
                try:
                    current = apply_prop_op(current, ev)
                except FactsOpRejectedError as exc:
                    # ④ rejection-form op: FAIL + P2.5 rationale requirement
                    issues.append(
                        f"ss.facts_ops:非法 op（{exc.reason}）——该形态必须携带非空 rationale（P2.5）"
                    )
                    if not rationale:
                        issues.append(
                            "ss.facts_ops:rationale 缺失（P2.5：非法形态 op 必须携带非空 rationale）"
                        )
                    continue
                touched.add(ev.prop)
            # ② row reconciliation vs the FINAL simulated owner（round2 #1c：
            # 逐 op 用 ev.to 会在合法二跳的第一跳误报——行持真终态时反被
            # 要求改写成错误的中间态）
            for prop in sorted(touched):
                _fact = current.props().get(prop)
                _final = _fact.owner if _fact is not None else ""
                _row_owner = _registry_row_owner(project_dir, prop, lookup=_staged_reg)
                if _row_owner is not None and _row_owner != _final:
                    issues.append(
                        f"ss.prop_row_match:「{prop}」op 链终态 owner「{_final or '（空）'}」"
                        f"≠ registry 行 owner「{_row_owner}」"
                        "——facts 为 canonical，修正 registry 行（修复者: settling）"
                    )
    elif not prop_ops and isinstance(chapter, int):
        # ① compat period: registry shows a this-chapter row change while the
        # sidecar declares no ops — WARN, not FAIL (audit-T8 I3)
        _reg = (
            _staged_reg
            if _staged_reg.is_file()
            else Path(project_dir) / "truth" / "prop_registry.md"
        )
        try:
            _reg_text = _reg.read_text(encoding="utf-8") if _reg.is_file() else ""
        except (OSError, ValueError):
            # audit-T8 round4 M-1：损坏/不可读 registry 不炸门——按无行变更处理
            _reg_text = ""
        if _reg_text and re.search(rf"第\s*{chapter}\s*章", _reg_text):
            warns.append(
                f"ss.facts_ops:旧 settle 兼容期——sidecar 无 facts_ops 而 prop_registry "
                f"含第{chapter}章行变更；双写未断言（sidecar 补 facts_ops 后本 WARN 消失）"
            )

    # ③ identity reconciliation — bidirectional, ungated from identity_ops
    # (audit-T8 M8); runs whenever identity facts exist (facts canonical).
    # identity.json 缺席 ⇒ 不对账（同 round3 M-2 兼容期选择）。
    # audit-T8 round2 I-3：先模拟本章 identity op 再对账——settle 声明新别名
    # 且 staging 已带新行是双写契约本身的合法形态（op 到 commit 才落地），
    # 对 committed 前态对账会把合法 settle 判成 FAIL。
    if has_identity:
        try:
            facts_id = FactsFile.model_validate_json(identity_file.read_text(encoding="utf-8"))
            if facts_id.dim is not FactsDim.IDENTITY:
                # audit-T8 round5 I-1：同 props 面——identity.json 装了别维
                # 内容时 identity() 访问器裸抛（含无 op 的 :838 路径）
                raise ValueError(f"维度错位 dim={facts_id.dim.value}（槽位期望 identity）")
        except (OSError, ValueError) as _exc:
            # round4 I-1 + round5 I-1：ValueError 宽捕覆盖 UnicodeDecodeError
            # 与槽位错位——结构化 issue
            issues.append(
                "ss.identity_row_match:truth/facts/identity.json 损坏/不可读/维度错位"
                f"（{_exc}）——先修复 facts 文件本体"
            )
        else:
            _id_seen: _Counter[tuple[_Any, ...]] = _Counter()
            for raw in facts_ops.get("identity") or []:
                try:
                    iev = IdentityEvent.model_validate(raw)
                except ValidationError as exc:
                    issues.append(
                        f"ss.facts_ops:identity op 结构非法（{exc.error_count()} 处）"
                        "——修正 sidecar 的 op 形态"
                    )
                    continue
                _entry = {
                    "op": iev.op.value,
                    "new_name": iev.new_name,
                    "alias": iev.alias,
                    "from_ch": iev.from_ch,
                }
                _fp = tuple(_entry.get(k) for k in IDENTITY_REPLAY_KEYS)
                _k = _id_seen[_fp]
                _id_seen[_fp] += 1
                if replay_skip(facts_id.ops_log, _entry, IDENTITY_REPLAY_KEYS, _k):
                    continue  # 跨提交指纹重放（写侧同键跳过）
                try:
                    facts_id = apply_identity_op(
                        facts_id,
                        iev.op.value,
                        new_name=iev.new_name,
                        alias=iev.alias,
                        from_ch=iev.from_ch,
                    )
                except FactsOpRejectedError as exc:
                    issues.append(
                        f"ss.facts_ops:非法 op（{exc.reason}）——该形态必须携带非空 rationale（P2.5）"
                    )
                    if not rationale:
                        issues.append(
                            "ss.facts_ops:rationale 缺失（P2.5：非法形态 op 必须携带非空 rationale）"
                        )
                    continue
            fact = facts_id.identity()
            if fact is not None:
                _rows = _name_registry_alias_rows(project_dir, lookup=_staged_name_reg)
                # 旌名行值=narration_name 是合法 registry 形态（旌名=册官给名即
                # 当前叙事名；运行侧首触 2026-10-29 ch23 settle 重派实弹）——
                # 前向允许集须并集 narration_name，否则 committed 旌名行把每个
                # settle sidecar 判成恒 FAIL
                _allowed = set(fact.aliases) | {fact.narration_name}
                for extra in _rows - _allowed:
                    issues.append(
                        f"ss.identity_row_match:name_registry 别名行「{extra}」"
                        "不在 facts 别名集——facts 为 canonical，重生成该行"
                        "（修复者: settling）"
                    )
                for missing in set(fact.aliases) - _rows:
                    issues.append(
                        f"ss.identity_row_match:facts 别名「{missing}」"
                        "无 name_registry 别名/旌名行——补行（修复者: settling）"
                    )
    return issues, warns


def _registry_row_owner(project_dir: Path, prop: str, *, lookup: Path | None = None) -> str | None:
    """prop_registry.md 行 owner（**全键精确匹配**，audit-T8 round3 I-1）。

    lookup 优先（staging 姊妹副本——本章新行只在 staging），缺席回退
    committed truth/prop_registry.md。`实体·副本` 是独立实体键、有独立行
    ——子串/stem 宽松匹配会把副本行当母行（顺序决定结果；母行缺席时静默
    替换成副本 owner，行对账基准被污染且重试数学不可满足）。行缺席返回
    None（不对账），是诚实信号而非覆盖缺口。
    """
    import re as _re

    candidates = [lookup] if lookup is not None else []
    candidates.append(Path(project_dir) / "truth" / "prop_registry.md")
    for path in candidates:
        if not path.is_file():
            continue
        try:
            _text = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            # audit-T8 round4 M-1：损坏/不可读的候选文件按缺席处理（诚实
            # None 信号不变）
            continue
        for line in _text.splitlines():
            m = _re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
            if not m:
                continue
            if m.group(1) == prop:
                return m.group(2)
    return None


def _name_registry_alias_rows(project_dir: Path, *, lookup: Path | None = None) -> set[str]:
    """name_registry 别名/旌名行的名集合（登记名 prose 备注出范围）。

    **并集**（audit-T8 round2 I-3）：staged 增量行 ∪ committed 旧行——
    staged 文件粒度优先（有行即早退）会把「旧行只在 committed」的过渡窗
    误判成 facts 别名无行。旧行被事实层淘汰时 facts 别名集同刻收窄
    （identity 维只增不删，无此形态）。
    """
    import re as _re

    candidates = [lookup] if lookup is not None else []
    candidates.append(Path(project_dir) / "truth" / "name_registry.md")
    out: set[str] = set()
    for path in candidates:
        if not path.is_file():
            continue
        try:
            _text = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            # audit-T8 round4 M-1：损坏/不可读的候选文件按缺席处理
            continue
        for line in _text.splitlines():
            m = _re.match(r"^\|\s*(别名|旌名)\s*\|\s*([^|]+?)\s*\|", line)
            if m:
                out.add(m.group(2))
    return out


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
            # 直呼路径（sidecar 显式出现在 fps——单元测试/裸 CLI）。生产
            # 复合分区从不把 sidecar 送进本槽（audit-T8 round2 C-2）——
            # 生产门经函数尾部的姊妹约定定位块进入同一检查。
            if project_dir:
                _issues, _warns = g4_state_settling_check(Path(project_dir), pf)
                mf.extend(_issues)
                c.extend(
                    {
                        "id": "G4.ss.facts_ops",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": w,
                    }
                    for w in _warns
                )

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

        # #75 registry tables: shape checks only — the invariant math lives
        # in G4.xc (gates/g4/cross_chapter.py), which derives anchors/owners
        # from prose as the primary source and uses these tables as the
        # cross-check layer. Calibrated to BOTH artifact shapes the gate
        # receives: the seeded whole file AND the rows-only append_dedup
        # increment the dispatch discipline mandates (final-review fix —
        # header-only checks WARNed on every legitimate increment).
        if "name_registry" in str(fp):
            if not re.search(r"\|\s*(?:登记名|代词白名单|禁用名)\s*\|", content):
                c.append(
                    {
                        "id": "G4.ss.name_registry",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no 称谓 row — name_registry rows are | 类别 | 名 | 备注 | (登记名/代词白名单/禁用名)",
                    }
                )
            else:
                c.append({"id": "G4.ss.name_registry", "file": fp, "s": GateStatus.PASS})

        if "timeline.md" in str(fp):
            if not re.search(r"\|\s*第\s*\d+\s*章\s*\|", content):
                c.append(
                    {
                        "id": "G4.ss.timeline",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no 第N章 row — timeline increments are | 第 N 章 | <末锚> | ... | rows keyed by 章",
                    }
                )
            else:
                c.append({"id": "G4.ss.timeline", "file": fp, "s": GateStatus.PASS})

        if "prop_registry" in str(fp):
            _rows = [
                ln
                for ln in content.split("\n")
                if ln.strip().startswith("|")
                and not re.match(r"^\|(\s*:?-{3,}:?\s*\|)+$", ln.strip())
            ]
            if not _rows:
                c.append(
                    {
                        "id": "G4.ss.prop_registry",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": "no entity row — prop_registry rows are | 实体名 | 当前owner | 经手事件 |",
                    }
                )
            else:
                c.append({"id": "G4.ss.prop_registry", "file": fp, "s": GateStatus.PASS})

    if not fps:
        c.append({"id": "G4.ss", "s": GateStatus.SKIP, "r": "no files"})

    # spec #80 T8（audit-T8 round2 C-2）：复合分区把 sidecar 路由给 g4_decisions
    # （schema/P2.5 归属见 _check_selections_coverage docstring）——直接在 fps
    # 里等 sidecar 是死路。按 #52 同款姊妹约定定位生产门真实可见的
    # staging/truth/state-settling-decisions.json，ss.* 四检查由此接入。
    # round3 I-2：produced_at 现实核查（模型伪造过 4 次）随同接入——
    # g4_decisions 只验 schema（str），不验时间真实性。
    if project_dir and not any("state-settling-decisions" in str(fp) for fp in fps or []):
        for fp in fps or []:
            if "staging/truth" not in fp.replace("\\", "/"):
                continue
            _sidecar = resolve_input_path(fp, rd).parent / "state-settling-decisions.json"
            if _sidecar.is_file():
                try:
                    _sc_text = _sidecar.read_text(encoding="utf-8")
                except (OSError, ValueError):
                    # audit-T8 round4 M-2：is_file→read 窗口竞态/损坏按缺席处理
                    _sc_text = ""
                if _sc_text:
                    mf.extend(_check_produced_at(_sc_text, str(_sidecar)))
                _issues, _warns = g4_state_settling_check(Path(project_dir), _sidecar)
                mf.extend(_issues)
                c.extend(
                    {
                        "id": "G4.ss.facts_ops",
                        "file": str(_sidecar),
                        "s": GateStatus.WARN,
                        "r": w,
                    }
                    for w in _warns
                )
            break

    mf.extend(_check_selections_coverage(fps, rd))

    if mf:
        return fail("G4-state-settling", c, "scoring", mf)
    return passed("G4-state-settling", c)
