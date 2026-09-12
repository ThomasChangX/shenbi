"""G4 checker for shenbi-foreshadowing-lifecycle (spec #59 T3 wiring).

Merged successor of the retired plant/track checkers: hook metadata
completeness, depends_on, ops ceiling, and SMOKESCREEN exit notes (plant
heritage) plus pending_hooks change and chapter-ref checks (track heritage).
The recall-phase vocabulary (DORMANT/ACTIVE/ABANDONED — SKILL.md :50/:59/:150
and lifecycle-states.md) is accepted alongside the canonical six HookState
words (derived from the enum; plan review r5/r6 ruling).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from shenbi.contracts.schemas.hooks import HookState
from shenbi.gates.shared import PROJECT, fail, passed, resolve_input_path
from shenbi.paths import RoundPaths
from shenbi.status import GateStatus

# Canonical six from the enum + the designed recall-phase vocabulary.
_STATES_RE = re.compile(
    r"\b(" + "|".join(sorted(s.value for s in HookState)) + r"|DORMANT|ACTIVE|ABANDONED)\b"
)
_CHANGES_RE = re.compile(r"状态.*→|操作")
_CHAPTER_RE = re.compile(r"第\d+章")
_SMOKESCREEN_EXIT_RE = re.compile(r"若|如果|除非|unless|if\b|condition", re.IGNORECASE)
_OPS = ("plant", "reinforce", "trigger", "resolve")


def _parse_hooks(content: str) -> list[Any] | None:
    """Hooks payload from a ``## hooks`` body section or frontmatter, else None."""
    hooks_match = re.search(r"## hooks\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if hooks_match:
        try:
            loaded: Any = yaml.safe_load(hooks_match.group(1))
        except yaml.YAMLError:
            loaded = None
        if isinstance(loaded, list):
            return list(loaded) or None  # empty payload -> free-form checks
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        try:
            fm: Any = yaml.safe_load(fm_match.group(1))
        except yaml.YAMLError:
            fm = None
        if isinstance(fm, dict) and isinstance(fm.get("hooks"), list):
            return list(fm["hooks"]) or None  # empty payload -> free-form checks
    return None


def g4_foreshadowing_lifecycle(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Lifecycle: hook metadata completeness + ops ceiling + SMOKESCREEN notes +
    pending_hooks changes with chapter refs (canonical + recall states).
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    if rd is None and project_dir is None:
        raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
    rp = RoundPaths(  # spec #48 C34: explicit roots, no silent fallthrough
        round_dir=Path(str(rd or project_dir)),
        project_dir=Path(str(project_dir or rd)),
        repo_root=Path(repo_root or PROJECT),
    )

    # — per-output-file checks (plant heritage) —
    total_ops = 0
    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.fl.not_found:{fp}")
            continue
        try:
            content = pf.read_text(encoding="utf-8")
        except OSError as exc:
            mf.append(f"G4.fl.read_error:{fp}:{exc}")
            continue
        hooks = _parse_hooks(content)
        if hooks is None:
            # Free-form output (e.g. audit report): state presence suffices.
            if _STATES_RE.search(content):
                c.append({"id": "G4.fl.states", "s": GateStatus.PASS, "file": fp})
            else:
                mf.append(f"G4.fl.no_hook_states:{fp}")
            continue
        for h in hooks:
            if not isinstance(h, dict):
                mf.append(f"G4.fl.hook_not_dict:{fp}")
                continue
            hid = str(h.get("id", "?"))
            for field in ("subtlety", "cultivation_interval"):
                if field not in h:
                    mf.append(f"G4.fl.{hid}.missing_{field}")
            if h.get("depends_on") is None:
                mf.append(f"G4.fl.{hid}.depends_on_null")
            if h.get("type") == "SMOKESCREEN":
                notes = str(h.get("notes", ""))
                if len(notes) < 50 or not _SMOKESCREEN_EXIT_RE.search(notes):
                    mf.append(f"G4.fl.{hid}.smokescreen_no_exit")
        total_ops += sum(1 for h in hooks if isinstance(h, dict) and h.get("operation") in _OPS)
    if fps:
        if total_ops > 24:
            mf.append(f"G4.fl.ops:{total_ops}>24")
        else:
            c.append({"id": "G4.fl.ops", "s": GateStatus.PASS, "count": total_ops})

    # — project-face checks (track heritage) —
    ph = rp.read("truth/pending_hooks.md")
    if not ph.exists():
        mf.append("G4.fl.not_found_pending_hooks")
    else:
        content = ph.read_text(encoding="utf-8")
        if _STATES_RE.search(content) or _CHANGES_RE.search(content):
            c.append({"id": "G4.fl.changes", "s": GateStatus.PASS})
        else:
            mf.append("G4.fl.no_changes")
        refs = _CHAPTER_RE.findall(content)
        if not refs:
            mf.append("G4.fl.chapter_refs")
        else:
            c.append({"id": "G4.fl.chapter_refs", "s": GateStatus.PASS, "refs": len(refs)})

    if not fps:
        c.append({"id": "G4.fl", "s": GateStatus.SKIP, "r": "no files"})

    if mf:
        return fail("G4-foreshadowing-lifecycle", c, "scoring", mf)
    return passed("G4-foreshadowing-lifecycle", c)
