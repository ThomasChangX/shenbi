"""G4 checker for shenbi-volume-outlining."""

from __future__ import annotations
from shenbi.status import GateStatus
from typing import Any
import re
from pathlib import Path

from shenbi.gates.shared import (
    PROJECT,
    fail,
    passed,
)
from shenbi.paths import RoundPaths


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
    if rd is None and project_dir is None:
        raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
    rp = RoundPaths(  # spec #48 C34: explicit roots, no silent fallthrough
        round_dir=Path(str(rd or project_dir)),
        project_dir=Path(str(project_dir or rd)),
        repo_root=Path(repo_root or PROJECT),
    )

    vm = rp.read("outline/volume_map.md")
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
            last_match = vol_sections[-1]
            last_vol = last_match.group()
            # Vol1 probe escalation #2: bare ids (`G4.vo.krs:0`) misled the
            # retrying model into refining the wrong volumes — carry the last
            # volume's identity so re-dispatch feedback is actionable.
            vol_head = last_vol.splitlines()[0].lstrip("# ").strip()
            vol_head = vol_head.split("（")[0].strip() or "last_volume"

            # Objective (binary yes/no)
            has_obj = bool(re.search(r"\*\*Objective\*\*[：:]\s*\S", last_vol))
            if not has_obj:
                mf.append(f"G4.vo.objective[{vol_head}]")
            else:
                c.append({"id": "G4.vo.objective", "s": GateStatus.PASS})

            # 3-5 KRs
            krs = re.findall(r"#### KR\d+", last_vol)
            if len(krs) < 3 or len(krs) > 5:
                mf.append(f"G4.vo.krs[{vol_head}]:{len(krs)}")
            else:
                c.append({"id": "G4.vo.krs", "s": GateStatus.PASS, "count": len(krs)})

            # 张力曲线
            if "张力曲线" not in last_vol:
                mf.append(f"G4.vo.tension_curve[{vol_head}]: 缺「### 卷内张力曲线」段")
            else:
                c.append({"id": "G4.vo.tension_curve", "s": GateStatus.PASS})

            # >= 1 cross-volume bridge hook
            has_bridge = bool(re.search(r"跨卷|桥接|bridge", last_vol, re.IGNORECASE))
            if not has_bridge:
                mf.append(f"G4.vo.bridge[{vol_head}]")
            else:
                c.append({"id": "G4.vo.bridge", "s": GateStatus.PASS})

            # P2-6 (2026-10-23): each volume region should carry a
            # 金句与梗位 line (quote slots / running gags / volume-end
            # Easter egg). WARN-level so pre-existing volumes stay green;
            # the SKILL checklist owns the instruction.
            if re.search(r"金句|梗位|彩蛋", last_vol):
                c.append({"id": "G4.vo.quote_line", "s": GateStatus.PASS})
                # spec #76: 梗位清单语法契约——段存在而 0「」跨度才 FAIL
                # （行/段整体缺席维持上方 P2-6 WARN——卷二+ 过渡态政策）。
                for _line in last_vol.split("\n"):
                    if "梗位复用" not in _line:
                        continue
                    _seg = _line.split("梗位复用", 1)[1].lstrip("：:")
                    _seg = re.split(r"[｜|]", _seg, maxsplit=1)[0]
                    if not re.search(r"「[^」]+」", _seg):
                        mf.append(
                            "G4.vo.meme_grammar:梗位复用段存在但 0「」跨度"
                            "（梗位项须引号短语——精确串计数口径）"
                        )
            else:
                c.append(
                    {
                        "id": "G4.vo.quote_line",
                        "s": GateStatus.WARN,
                        "r": "volume region lacks 金句/梗位/彩蛋 line (P2-6)",
                    }
                )

    if mf:
        return fail("G4-volume-outlining", c, "scoring", mf)
    return passed("G4-volume-outlining", c)
