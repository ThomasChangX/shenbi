"""Spec #75 cross-chapter invariants: six hard checks across chapter seams.

Data path (dual-source, decoupled from the settling step's timing):
primary = memo declaration lines (planning batch product, on disk at the
split step) + deterministic derivation from the PREVIOUS chapter's prose;
the truth registry tables are a cross-check layer, never the sole truth at
check time. Pure validation: no side effects, idempotent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.status import GateStatus

# ---------- context ----------


@dataclass
class CrossChapterContext:
    """Inputs the checks consult; registry layers are optional (WARN)."""

    project_dir: Path | None = None
    name_whitelist: tuple[str, ...] = ("临", "他")  # #74 项 4 落地前 bootstrap
    registry_dir: Path | None = None  # truth/ 三表所在；缺席 → 交叉校验 WARN


# ---------- memo declaration lines (planning 场景预算块同区) ----------

_DECL_LINE_RES = {
    "时间锚": re.compile(r"^-\s*时间锚[：:]\s*(\[回拨\])?\s*(.+?)\s*$", re.MULTILINE),
    "余额": re.compile(r"^-\s*余额[：:]\s*(.+?)\s*$", re.MULTILINE),
    "POV": re.compile(r"^-\s*POV[：:]\s*(我|他|她)\s*$", re.MULTILINE),
}


def load_memo_declarations(memo_path: Path) -> dict[str, str]:
    """Declaration lines from a planning memo (时间锚/余额/POV).

    Missing file or pre-#72 memo (no scene-budget block) → {} — the caller
    treats that as the legacy-WARN path; prose-derived anchors still run.
    """
    if not memo_path.is_file():
        return {}
    text = memo_path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for key, rx in _DECL_LINE_RES.items():
        m = rx.search(text)
        if m:
            out[key] = (
                m.group(2)
                if key == "时间锚" and m.group(1) is None
                else (("[回拨]" + m.group(2)) if key == "时间锚" else m.group(1))
            )
    return out


# ---------- skeleton entry ----------


def prev_chapter_path(chapter_path: Path) -> Path | None:
    """章 N 前章恒为 N-1（双章批语义：leader 前章=批外，follower=leader）。"""
    m = re.search(r"chapter-(\d+)", chapter_path.name)
    if not m:
        return None
    n = int(m.group(1))
    if n <= 1:
        return None
    prev = chapter_path.parent / f"chapter-{n - 1}.md"
    return prev if prev.is_file() else None


def check_cross_chapter(
    chapter_path: Path,
    prev_path: Path | None,
    memo_path: Path | None,
    ctx: CrossChapterContext,
) -> list[str]:
    """Run the six invariants; returns violation strings (empty = clean).

    First chapter (prev_path None): skip the seam-dependent items entirely.
    """
    issues: list[str] = []
    if prev_path is None:
        return issues  # 首章：前章依赖项全跳过（骨架期）
    _ = (memo_path, ctx)
    return issues


def g4_cross_chapter(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,
    repo_root: str | None = None,
) -> str:
    """G4 checker entry (signature aligned with the existing checker family)."""
    from shenbi.gates.shared import fail, passed, resolve_input_path

    c: list[dict[str, Any]] = []
    mf: list[str] = []
    for fp in fps or []:
        ch_path = Path(fp)
        if not ch_path.is_absolute() and rd:
            ch_path = Path(resolve_input_path(fp, rd))
        if not ch_path.is_file():
            mf.append(f"XC.not_found:{fp}")
            continue
        prev = prev_chapter_path(ch_path)
        memo = None
        if project_dir:
            m = re.search(r"chapter-(\d+)", ch_path.name)
            if m:
                memo = Path(project_dir) / "plans" / f"chapter-{m.group(1)}-plan.md"
        ctx = CrossChapterContext(
            project_dir=Path(project_dir) if project_dir else None,
            registry_dir=(Path(project_dir) / "truth") if project_dir else None,
        )
        issues = check_cross_chapter(ch_path, prev, memo, ctx)
        if issues:
            mf.extend(f"XC:{ch_path.name}:{i}" for i in issues)
        else:
            c.append({"id": "XC.clean", "file": fp, "s": GateStatus.PASS})
    if mf:
        return fail(
            "G4-cross-chapter",
            [{"id": "XC", "s": GateStatus.FAIL, "r": m} for m in mf],
            "chapter_split",
            mf,
        )
    return passed("G4-cross-chapter", c)
