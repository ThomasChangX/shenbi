"""G4 checker for shenbi-length-normalizing."""

from __future__ import annotations
from shenbi.status import GateStatus
from typing import Any

from shenbi.gates.shared import (
    CHAPTER_WORD_CEILING,
    chapter_word_floor,
    chapter_word_min_max,
    fail,
    passed,
    resolve_input_path,
    total_chars_md_text,
)


def g4_length_normalizing(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Length normalizing: per-chapter bounds from genre-config chapter_word
    (probe3 P1 unification — the drafting gate already floors on the same
    config's default; a 1700-default genre cannot demand 3000 from the
    normalizer while accepting 1700 from the drafter). Fallbacks keep the
    legacy 3000/10000 constants when the config is absent. Input is the
    merge_prose merged chapter (spec #95 维护批 audit-T13 F4).
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    floor = chapter_word_floor(project_dir)
    _mn, mx = chapter_word_min_max(project_dir)
    ceiling = mx if mx else CHAPTER_WORD_CEILING

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.ln.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")
        # spec #72 口径统一: total_chars (band contract), not CJK-only count
        wc = total_chars_md_text(content)

        # spec #95 维护批（audit-T13 F4）：updates mode=merge_prose——staged 件=
        # applier 合并后的整章，旧「## 归一化报告 在章内」检查退役（报告移出章
        # 文件，进场景段会被吸收为正文）；字数带即结果判定：带内=无需归一化亦过，
        # 带外=below_floor/above_ceiling（顺带修复旧口径把报告文本计入字数的虚高）。
        if wc < floor:
            mf.append(f"G4.ln.below_floor:{fp}:{wc}<{floor}")
        elif wc > ceiling:
            mf.append(f"G4.ln.above_ceiling:{fp}:{wc}>{ceiling}")
        else:
            c.append({"id": "G4.ln.word_count", "file": fp, "s": GateStatus.PASS, "wc": wc})

    if not fps:
        c.append({"id": "G4.ln", "s": GateStatus.SKIP, "r": "no files"})

    if mf:
        return fail("G4-length-normalizing", c, "scoring", mf)
    return passed("G4-length-normalizing", c)
