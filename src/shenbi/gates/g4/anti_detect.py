"""G4 checker for shenbi-anti-detect."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shenbi.gates.shared import (
    bak_path,
    fail,
    passed,
    resolve_input_path,
)
from shenbi.status import GateStatus

#: 章内场景分隔标记（与 pipeline/prose_patch 同一判据：独立行 ``<!--SCENE-->``）。
_SCENE_MARKER_RE = re.compile(r"^<!--SCENE-->$", re.MULTILINE)


def g4_anti_detect(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Anti-detect: merge_prose 合并章面的场景标记保全。

    spec #95 维护批（audit-T13 F4）：contract updates mode=merge_prose——staged
    件=applier 合并后的整章，旧「## 改写报告 在章内」存在性检查随报告移出章文件
    而退役（报告进场景段会被 applier 吸收为正文污染）。章内可检结构不变量=场景
    标记数与改写前基线（.bak 同伴）一致；改写报告结构/META 块/章界等结构断言归
    spec #96 T3 扩面。基线缺席（无 .bak 或基线本无场景标记）时优雅跳过。
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.ad.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        bak = Path(bak_path(pf))
        if bak.exists():
            base = bak.read_text(encoding="utf-8")
            n_base = len(_SCENE_MARKER_RE.findall(base))
            n_staged = len(_SCENE_MARKER_RE.findall(content))
            if n_base and n_staged != n_base:
                mf.append(f"G4.ad.scene_marker_loss:{fp}:{n_staged}!={n_base}")
                continue
            if n_base:
                c.append(
                    {
                        "id": "G4.ad.scene_markers",
                        "file": fp,
                        "s": GateStatus.PASS,
                        "markers": n_staged,
                    }
                )

    if not fps:
        c.append({"id": "G4.ad", "s": GateStatus.SKIP, "r": "no files"})

    if mf:
        return fail("G4-anti-detect", c, "scoring", mf)
    return passed("G4-anti-detect", c)
