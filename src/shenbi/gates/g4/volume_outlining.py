"""G4 checker for shenbi-volume-outlining."""

from __future__ import annotations
from typing import Any
import re

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_g4_base,
)


def g4_volume_outlining(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Volume outlining: Objective (binary), 3-5 KRs, tension curve,
    >= 1 cross-volume bridge hook.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []
    pd = resolve_g4_base(rd)

    vm = pd / "outline" / "volume_map.md"
    if not vm.exists():
        mf.append("G4.vo.not_found")
    else:
        content = vm.read_text(encoding="utf-8")
        vol_sections = list(
            re.finditer(
                r"## 第[一二三四五六七八九十\d]+卷[：:].*?\n(?=## 第[一二三四五六七八九十\d]+卷|\Z)",
                content,
                re.DOTALL,
            )
        )
        if not vol_sections:
            mf.append("G4.vo.no_volumes")
        else:
            last_vol = vol_sections[-1].group()

            # Objective (binary yes/no)
            has_obj = bool(re.search(r"\*\*Objective\*\*[：:]\s*\S", last_vol))
            if not has_obj:
                mf.append("G4.vo.objective")
            else:
                c.append({"id": "G4.vo.objective", "s": "PASS"})

            # 3-5 KRs
            krs = re.findall(r"#### KR\d+", last_vol)
            if len(krs) < 3 or len(krs) > 5:
                mf.append(f"G4.vo.krs:{len(krs)}")
            else:
                c.append({"id": "G4.vo.krs", "s": "PASS", "count": len(krs)})

            # 张力曲线
            if "张力曲线" not in last_vol:
                mf.append("G4.vo.tension_curve")
            else:
                c.append({"id": "G4.vo.tension_curve", "s": "PASS"})

            # >= 1 cross-volume bridge hook
            has_bridge = bool(re.search(r"跨卷|桥接|bridge", last_vol, re.IGNORECASE))
            if not has_bridge:
                mf.append("G4.vo.bridge")
            else:
                c.append({"id": "G4.vo.bridge", "s": "PASS"})

    if mf:
        return fail("G4-volume-outlining", c, "scoring", mf)
    return passed("G4-volume-outlining", c)
