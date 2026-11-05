"""G4 checker for shenbi-style-polishing."""

from __future__ import annotations
from shenbi.status import GateStatus
from typing import Any
from pathlib import Path

from shenbi.gates.shared import (
    bak_path,
    fail,
    passed,
    resolve_input_path,
    word_count_md,
)


def g4_style_polishing(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Style polishing: word count change ratio check vs pre-polish .bak.

    spec #95 维护批（audit-T13 F4）：updates mode=merge_prose——staged 件=
    applier 合并后的整章，旧「## 润色说明 在章内」存在性检查随报告移出章文件
    而退役（报告进场景段会被 applier 吸收为正文污染）；±15% 字数比（vs .bak
    同伴）即章内可检不变量。
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.sp.not_found:{fp}")
            continue

        # Word count change ratio within [0.85, 1.15]
        # Check the .bak sibling (pre-polish version) at the same resolved
        # root as the polished content (pf = base/fp), not a bare fp.
        bak = Path(bak_path(pf))
        if bak.exists():
            wc_before = word_count_md(bak)
            wc_after = word_count_md(pf)
            if wc_before > 0:
                ratio = wc_after / wc_before
                if ratio < 0.85 or ratio > 1.15:
                    mf.append(f"G4.sp.word_ratio:{fp}:{ratio:.2f}")
                else:
                    c.append(
                        {
                            "id": "G4.sp.word_ratio",
                            "file": fp,
                            "s": GateStatus.PASS,
                            "before": wc_before,
                            "after": wc_after,
                        }
                    )

    if not fps:
        c.append({"id": "G4.sp", "s": GateStatus.SKIP, "r": "no files"})

    if mf:
        return fail("G4-style-polishing", c, "scoring", mf)
    return passed("G4-style-polishing", c)
