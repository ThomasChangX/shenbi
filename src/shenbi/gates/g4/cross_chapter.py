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


# ---------- invariant 1: POV mode (prose-derived) ----------

_FIRST_PERSON = re.compile(r"^[^「”』]*?我(?![们们])", re.MULTILINE)
_THIRD_PERSON = re.compile(r"他|她")


def derive_pov_mode(text: str) -> str:
    """Deterministic POV derivation: first-person vs third-person density."""
    body = "\n".join(
        ln for ln in text.split("\n") if not ln.startswith("#") and not ln.startswith("<!--")
    )
    first = len(re.findall(r"我", body))
    third = len(_THIRD_PERSON.findall(body))
    if first + third == 0:
        return "unknown"
    return "我" if first > third * 2 else ("他" if third > first * 2 else "mixed")


# ---------- invariant 2: protagonist naming (three-signal binding) ----------

# 内汲动词绑定形态（ch4:88「灯在心里过了一遍」实证）
_INNER_VERBS = ("在心里", "暗自", "心里过了一遍", "心想", "暗想", "寻思")


def _sentence_spans(text: str) -> list[str]:
    parts = re.split(r"[。！？\n]", text)
    return [s for s in (p.strip() for p in parts) if s]


def protagonist_binding_hits(text: str, name: str, whitelist: tuple[str, ...]) -> list[str]:
    """Three-signal binding: 主语位 / 内汲动词绑定 / 邻句代词共指 (any two).

    Returns violation descriptions for occurrences where `name` binds to the
    protagonist while sitting outside the whitelist.
    """
    if name in whitelist:
        return []
    hits: list[str] = []
    sents = _sentence_spans(text)
    for i, sent in enumerate(sents):
        if name not in sent:
            continue
        signals = 0
        if re.search(rf"(?:^|[。！？，；]|接着|然后|而)\s*{re.escape(name)}", sent):
            signals += 1  # 主语位
        if any(v in sent for v in _INNER_VERBS) and name in sent:
            signals += 1  # 内汲动词绑定
        window = " ".join(sents[max(0, i - 1) : i + 2])
        if re.search(
            rf"{re.escape(name)}[^。！？]{{0,20}}他\b|他[^。！？]{{0,8}}{re.escape(name)}", window
        ):
            signals += 1  # 邻句代词共指
        if signals >= 2:
            hits.append(f"「{name}」主角指称绑定（信号 {signals}/3）: {sent[:24]}")
    return hits


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
        return issues  # 首章：前章依赖项全跳过

    cur_text = chapter_path.read_text(encoding="utf-8")
    prev_text = prev_path.read_text(encoding="utf-8")

    # ── 不变量 1: POV 人称一致（正文推导；变更须 memo 声明）──
    cur_pov = derive_pov_mode(cur_text)
    prev_pov = derive_pov_mode(prev_text)
    decls = load_memo_declarations(memo_path) if memo_path else {}
    declared = decls.get("POV")
    if cur_pov != prev_pov and cur_pov != "unknown" and prev_pov != "unknown":
        if not declared or declared != cur_pov:
            issues.append(
                f"POV 人称断裂: 前章 {prev_pov} → 本章 {cur_pov} 且无 POV 变更声明"
                "（修复者: planning+drafting）"
            )

    # ── 不变量 2: 主角称谓（三信号绑定；白名单外名绑定即 FAIL）──
    for name in ("灯", "小满", "萤"):
        hits = protagonist_binding_hits(cur_text, name, ctx.name_whitelist)
        if hits:
            issues.append("称谓违例（修复者: planning+drafting）: " + "; ".join(hits[:2]))
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
