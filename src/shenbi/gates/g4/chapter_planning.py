"""G4 checker for shenbi-chapter-planning."""

from __future__ import annotations
from pathlib import Path
from shenbi.status import GateStatus
from typing import Any
import re

from shenbi.gates.shared import (
    fail,
    passed,
    resolve_input_path,
)


def g4_chapter_planning(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Chapter planning: 8 numbered sections (## 1. to ## 8.), golden-3 rules,
    section 4 has 关键抉择, section 5 has hook operation names.
    """
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    # #18-2 (probe23 adjudication #007): the ch3 memo invented MH11/MH12 —
    # book_spine caps at MH10, pending_hooks never registered them, two
    # human reject rounds with explicit delete instructions still shipped
    # MH11 in the approved memo. The machine gate owns hook authenticity:
    # MH-namespace IDs are genesis-owned (lifecycle assigns CP-NNN to new
    # plants), so every MH reference in §7 must exist in the spine or the
    # pool. Registry files absent (phase 1) → nothing to check against.
    registered_hooks: set[str] | None = None
    if project_dir:
        registry_parts: list[str] = []
        for rel in ("truth/book_spine.md", "truth/pending_hooks.md"):
            rf = Path(project_dir) / rel
            if rf.is_file():
                registry_parts.append(rf.read_text(encoding="utf-8"))
        # both registry files absent (phase 1) → nothing to check against
        if registry_parts:
            registered_hooks = set(re.findall(r"MH\d+", "\n".join(registry_parts)))

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
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
            c.append({"id": "G4.cp.sections", "file": fp, "s": GateStatus.PASS})

        # chapter_role token — drives review-resonance threshold calibration (spec §5.1)
        if re.search(r"chapter_role\s*[:：]\s*(高潮|兑现|推进|转折|过渡|铺垫)", content):
            c.append({"id": "G4.cp.chapter_role", "file": fp, "s": GateStatus.PASS})
        else:
            mf.append(f"G4.cp.missing_chapter_role:{fp}")

        # #27 (probe17 adjudications #003→#005): the '# Chapter N:' English
        # heading is contract-banned; the write-path injector kept re-adding
        # it after compliant model output (#28 scoped the injector), so the
        # gate now enforces the ban machine-side on the written artifact.
        _eng = re.search(r"^#\s*Chapter\s*\d+\s*:?", content, re.MULTILINE)
        if _eng:
            mf.append(
                f"G4.cp.english_heading:{fp}:「{_eng.group(0)}」"
                "（删除该英文标题行——文件必须以「# 第N章 章节备忘」中文标题行开头）"
            )
        else:
            c.append({"id": "G4.cp.english_heading", "file": fp, "s": GateStatus.PASS})

        # Golden-3 rules based on chapter number N — quality bonus, not hard gate.
        # Only fails if golden content is completely missing AND sections are also
        # incomplete. Warnings are more appropriate for automated pipelines.
        ch_num = re.search(r"-(\d+)-plan", str(fp))
        n = int(ch_num.group(1)) if ch_num else 0
        golden = {1: "三面墙", 2: "验证主角特殊性|对手", 3: "小高潮"}
        if n in golden:
            alternatives = golden[n].split("|")
            if not any(alt in content for alt in alternatives):
                # Don't fail — golden rules are aspirational quality targets
                c.append(
                    {
                        "id": f"G4.cp.golden_{n}",
                        "file": fp,
                        "s": GateStatus.WARN,
                        "r": f"golden rule '{golden[n]}' not found in chapter {n}",
                    }
                )
            else:
                c.append({"id": f"G4.cp.golden_{n}", "file": fp, "s": GateStatus.PASS})
        else:
            c.append(
                {
                    "id": "G4.cp.golden",
                    "file": fp,
                    "s": GateStatus.SKIP,
                    "r": f"N={n}, golden-3 only for N=1,2,3",
                }
            )

        # P1 craft-declaration fields (2026-10-23, 诡秘/炮火 commercial-rhythm
        # audit): §1 must declare emotion_tone (抑扬排程 — five-value
        # vocabulary aligned with rhythm_principles monotony detection) and
        # a payoff 拍 (爽点兑现声明; review-highpoint audits 蓄压-释放比 against
        # it); chapters inside the retention window must declare a 留存锚
        # line (§2). The window mirrors golden-3's hardcode; genre-config
        # pacing.retentionWindow is the doc-level default (30).
        if re.search(r"emotion_tone\s*[:：]\s*(悲|喜|怒|惧|平)", content):
            c.append({"id": "G4.cp.emotion_tone", "file": fp, "s": GateStatus.PASS})
        else:
            mf.append(f"G4.cp.missing_emotion_tone:{fp}")

        if re.search(r"\*{0,2}payoff\s*拍\*{0,2}\s*[:：]\s*\S", content):
            c.append({"id": "G4.cp.payoff_beat", "file": fp, "s": GateStatus.PASS})
        else:
            mf.append(f"G4.cp.missing_payoff_beat:{fp}")

        if 1 <= n <= 30:
            if re.search(r"\*{0,2}留存锚\*{0,2}\s*[:：]\s*\S", content):
                c.append({"id": "G4.cp.retention_anchor", "file": fp, "s": GateStatus.PASS})
            else:
                mf.append(f"G4.cp.missing_retention_anchor:{fp}")
        else:
            c.append(
                {
                    "id": "G4.cp.retention_anchor",
                    "file": fp,
                    "s": GateStatus.SKIP,
                    "r": f"N={n}, retention window is chapters 1-30",
                }
            )

        # Section 5: 关键抉择 — quality bonus, not hard gate
        s5_match = re.search(r"## 5\..*?\n(?=## 6\.|\Z)", content, re.DOTALL)
        s5_text = s5_match.group() if s5_match else ""
        if "关键抉择" not in s5_text:
            c.append(
                {
                    "id": "G4.cp.s5_choice",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "section 5 missing 关键抉择 keyword",
                }
            )
        else:
            c.append({"id": "G4.cp.s5_choice", "file": fp, "s": GateStatus.PASS})

        # Section 7: hook operation names (per SKILL.md, section 7 is 本章 hook 账)
        s7_match = re.search(r"## 7\..*?\n(?=## 8\.|\Z)", content, re.DOTALL)
        s7_text = s7_match.group() if s7_match else ""
        hook_ops = ["open", "advance", "resolve", "defer"]
        found_ops = [op for op in hook_ops if op in s7_text.lower()]
        if not found_ops:
            mf.append(f"G4.cp.s7_hook_ops:{fp}")
        else:
            c.append(
                {"id": "G4.cp.s7_hook_ops", "file": fp, "s": GateStatus.PASS, "ops": found_ops}
            )

        # #18-2: MH-namespace hook authenticity (registry read once above).
        if registered_hooks is None:
            c.append(
                {
                    "id": "G4.cp.hook_refs",
                    "file": fp,
                    "s": GateStatus.SKIP,
                    "r": "no book_spine/pending_hooks registry (phase 1)",
                }
            )
        else:
            refs = list(dict.fromkeys(re.findall(r"MH\d+", s7_text)))
            unknown = [r for r in refs if r not in registered_hooks]
            if unknown:
                mf.append(
                    f"G4.cp.hook_refs:{fp}:引用未注册钩子「{'、'.join(unknown)}」"
                    "（book_spine/pending_hooks 无此 MH 编号——新钩属 genesis/lifecycle "
                    "职权，memo 不得自造 MH 号；确需新钩请走 CP-NNN 或先注册再引用）"
                )
            else:
                c.append({"id": "G4.cp.hook_refs", "file": fp, "s": GateStatus.PASS})

        # Defer-silence rule (SKILL.md section 7 可自动检查规则; spec #9 R2):
        # rows with 操作=defer and 沉默章数 >= 4 require an 激活方案 or ABANDON
        # annotation in section 7. Only the EXACT-template column order
        # (ID | 操作 | 推进方式 | 沉默章数) is parsed; free-form tables
        # (e.g. Phase-1 placeholder prose) do not match and are not flagged.
        defer_silent = re.findall(r"\|\s*[^|]*\|\s*defer\s*\|[^|]*\|\s*(\d+)\s*\|", s7_text)
        if any(int(n) >= 4 for n in defer_silent) and not re.search(
            r"激活方案|ABANDON", s7_text, re.IGNORECASE
        ):
            mf.append(f"G4.cp.s7_defer_silence:{fp}")
        else:
            c.append({"id": "G4.cp.s7_defer_silence", "file": fp, "s": GateStatus.PASS})

    if not fps:
        c.append({"id": "G4.cp", "s": GateStatus.SKIP, "r": "no files"})

    if mf:
        return fail("G4-chapter-planning", c, "scoring", mf)
    return passed("G4-chapter-planning", c)
