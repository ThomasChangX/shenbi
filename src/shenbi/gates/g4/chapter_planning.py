"""G4 checker for shenbi-chapter-planning."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

from shenbi.gates.shared import (
    fail,
    passed,
)


def g4_chapter_planning(fps: list[str], rd: str | None = None) -> str:
    """Chapter planning: 8 numbered sections (## 1. to ## 8.), golden-3 rules,
    section 4 has 关键抉择, section 5 has hook operation names.
    """
    c: list[dict[str, Any]] = []
    mf = []

    for fp in fps or []:
        pf = Path(fp)
        if not pf.exists():
            mf.append(f"G4.cp.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        # 8 numbered sections (## N. / ## N、 / ## N： / ## N)
        sections_found = []
        for i in range(1, 9):
            if re.search(rf"## {i}[\.、：:\s]", content):
                sections_found.append(i)
        if len(sections_found) < 8:
            missing = [i for i in range(1, 9) if i not in sections_found]
            mf.append(f"G4.cp.sections:{len(sections_found)}/8_missing_{missing}")
        else:
            c.append({"id": "G4.cp.sections", "file": fp, "s": "PASS"})

        # Golden-3 rules based on chapter number N (hardcoded default=3;
        # projects can configure golden_opening_chapters in novel.json)
        ch_num = re.search(r"-(\d+)-plan", str(fp))
        n = int(ch_num.group(1)) if ch_num else 0
        golden = {1: "三面墙", 2: "验证主角特殊性|对手", 3: "小高潮"}
        if n in golden:
            # golden[n] may contain | for alternative matches
            alternatives = golden[n].split("|")
            if not any(alt in content for alt in alternatives):
                mf.append(f"G4.cp.golden_{n}:missing_{golden[n]}")
            else:
                c.append({"id": f"G4.cp.golden_{n}", "file": fp, "s": "PASS"})
        else:
            c.append(
                {
                    "id": "G4.cp.golden",
                    "file": fp,
                    "s": "SKIP",
                    "r": f"N={n}, golden-3 only for N=1,2,3",
                }
            )

        # Section 5: 关键抉择 (per SKILL.md, section 5 is key decision)
        s5_match = re.search(r"## 5\..*?\n(?=## 6\.|\Z)", content, re.DOTALL)
        s5_text = s5_match.group() if s5_match else ""
        if "关键抉择" not in s5_text:
            mf.append(f"G4.cp.s5_choice:{fp}")
        else:
            c.append({"id": "G4.cp.s5_choice", "file": fp, "s": "PASS"})

        # Section 7: hook operation names (per SKILL.md, section 7 is 本章 hook 账)
        s7_match = re.search(r"## 7\..*?\n(?=## 8\.|\Z)", content, re.DOTALL)
        s7_text = s7_match.group() if s7_match else ""
        hook_ops = ["open", "advance", "resolve", "defer"]
        found_ops = [op for op in hook_ops if op in s7_text.lower()]
        if not found_ops:
            mf.append(f"G4.cp.s7_hook_ops:{fp}")
        else:
            c.append({"id": "G4.cp.s7_hook_ops", "file": fp, "s": "PASS", "ops": found_ops})

    if not fps:
        c.append({"id": "G4.cp", "s": "SKIP", "r": "no files"})

    if mf:
        return fail("G4-chapter-planning", c, "scoring", mf)
    return passed("G4-chapter-planning", c)
