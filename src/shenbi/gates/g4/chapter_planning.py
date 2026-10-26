"""G4 checker for shenbi-chapter-planning."""

from __future__ import annotations
from pathlib import Path
from shenbi.status import GateStatus
from typing import Any
import re

from shenbi.logging import get_logger
from shenbi.gates.g4.cross_chapter import load_memo_declarations
from shenbi.gates.shared import (
    SCENE_INDEPENDENT_BAND,
    SCENE_PAIRED_BAND,
    chapter_word_min_max,
    fail,
    jload,
    pack_scenes,
    parse_scene_declarations,
    passed,
    resolve_input_path,
    split_scenes,
)

log = get_logger(__name__)


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

    # ── spec #72 G4.cp.scene_budget — 场景预算两型域/组合/可打包性预检 ──
    # planning 时点拦截不可打包的预算序列。打包窗口 = 前章全场景（实际值）+
    # 本备忘声明 + 邻章备忘声明（bundle 双备忘 staging 时点均在盘——R2 接缝
    # 联合）；尾组开埠（allow_open_tail）配下 bundle 首场景。
    _fanqie_band = (1800, 2800)
    if project_dir:
        try:
            _gc = jload(str(Path(project_dir) / "genre-config.json"))
            _fq = _gc.get("chapter_word", {}).get("fanqie_update", {})
            if isinstance(_fq, dict) and _fq.get("min") and _fq.get("max"):
                _fanqie_band = (int(_fq["min"]), int(_fq["max"]))
        except (OSError, ValueError):
            log.warning("cp_scene_budget_fanqie_band_fallback", band=_fanqie_band)
    _mn_cfg, _mx_cfg = chapter_word_min_max(project_dir)
    chapter_band = (_mn_cfg or 2800, _mx_cfg or 4000)

    def _memo_decl_sizes(plan_path: Path) -> list[int]:
        """Sibling memo's declared sizes (packing-window input)."""
        if not plan_path.is_file():
            return []
        return [
            size
            for (_num, size, _kind, _hook) in parse_scene_declarations(
                plan_path.read_text(encoding="utf-8")
            )
        ]

    for fp in fps or []:
        resolved = resolve_input_path(fp, rd)
        p_ = Path(resolved)
        if not p_.is_file():
            continue
        decls = parse_scene_declarations(p_.read_text(encoding="utf-8"))
        if not decls:
            continue  # 旧式备忘（无场景块）——存量兼容
        n_match = re.search(r"chapter-(\d+)", p_.name)
        chapter_no = int(n_match.group(1)) if n_match else None
        issues: list[str] = []
        if not 2 <= len(decls) <= 3:
            issues.append(f"场景数 {len(decls)} 不在 2-3")
        for idx, (_num, size, kind, _hook) in enumerate(decls, 1):
            lo_i, hi_i = SCENE_INDEPENDENT_BAND
            lo_p, hi_p = SCENE_PAIRED_BAND
            in_ind = lo_i <= size <= hi_i
            in_pair = lo_p <= size <= hi_p
            if kind == "独立型" and not in_ind:
                issues.append(f"场景{idx} 声明独立型但 {size} 不落 [1800,2000]")
            if kind == "配对型" and not in_pair:
                issues.append(f"场景{idx} 声明配对型但 {size} 不落 [900,1400]")
            if not (in_ind or in_pair):
                issues.append(f"场景{idx}={size} 落灰域 [1400,1800)")
        sizes = [d[1] for d in decls]
        total = sum(sizes)
        indep_count = sum(1 for d in decls if d[2] == "独立型")
        if len(decls) == 2 and indep_count != 2:
            issues.append("2 场景章须两独立型（和 [3600,4000]）")
        if len(decls) == 3 and indep_count not in (0, 1):
            issues.append("3 场景章须三配对型或一独两配")
        if not chapter_band[0] <= total <= chapter_band[1]:
            issues.append(f"章和 {total} 不在 [{chapter_band[0]},{chapter_band[1]}]")
        # 打包窗口：前章全场景（实际）+ 本声明 + 邻章备忘声明（R2 接缝联合）
        seq: list[int] = []
        if chapter_no is not None and project_dir:
            prev = Path(project_dir) / "chapters" / f"chapter-{chapter_no - 1}.md"
            if prev.is_file():
                seq.extend(s for s, _ll in split_scenes(prev.read_text(encoding="utf-8")))
        seq.extend(sizes)
        if chapter_no is not None:
            for cand in (
                p_.parent / f"chapter-{chapter_no + 1}-plan.md",
                Path(project_dir or ".")
                / "staging"
                / "plans"
                / f"chapter-{chapter_no + 1}-plan.md",
                Path(project_dir or ".") / "plans" / f"chapter-{chapter_no + 1}-plan.md",
            ):
                sib = _memo_decl_sizes(cand)
                if sib:
                    seq.extend(sib)
                    break
        if pack_scenes(seq, _fanqie_band, allow_open_tail=True) is None:
            issues.append(f"贪心不可打包（序列 {seq}，更带 {_fanqie_band}）——请调整场景预算组合")
        if issues:
            mf.append(f"G4.cp.scene_budget:{fp}:" + ";".join(issues))
        else:
            c.append({"id": "G4.cp.scene_budget", "file": fp, "s": GateStatus.PASS})

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if not pf.exists():
            mf.append(f"G4.cp.not_found:{fp}")
            continue

        content = pf.read_text(encoding="utf-8")

        # ── spec #76/#78 G4.cp.plan_format — 版本令牌分立 ──
        # 缺席 = v1 默认（不 FAIL）；在场值 ∉ {v1,v2,v3} = FAIL；
        # v2/v3 ⇒ 声口要求行存在；v3 ⇒ 张力拍分级行 + payoff 轴量行。
        _pf_m = re.search(r"^plan_format[：:]\s*(\S+)\s*$", content, re.MULTILINE)
        if _pf_m:
            _pf_val = _pf_m.group(1)
            if _pf_val not in ("v1", "v2", "v3"):
                mf.append(
                    f"G4.cp.plan_format:{fp}:invalid_token:{_pf_val} (合法值 v1/v2/v3；缺席 = v1 默认)"
                )
            elif _pf_val in ("v2", "v3"):
                if not re.search(r"^声口要求[：:].+$", content, re.MULTILINE):
                    mf.append(
                        f"G4.cp.voice_line:{fp}:{_pf_val}_requires_声口要求行 "
                        "(protagonist 口癖/句式要点——planning 从 protagonist.md voice_profile 生成)"
                    )
                else:
                    c.append({"id": "G4.cp.voice_line", "file": fp, "s": GateStatus.PASS})
            if _pf_val == "v3":
                # spec #78 v3 义务：张力拍分级行 + payoff 轴量行
                if not re.search(r"章尾张力拍[：:]\s*\[?(微|章|大)", content):
                    mf.append(
                        f"G4.cp.tension_tier:{fp}:v3_requires_张力拍分级行 "
                        "（[微|章|大]+形态——分级声明制）"
                    )
                _payoff_m = re.search(r"\*\*payoff 拍\*\*[：:]\s*(.+)", content)
                if _payoff_m and not re.search(
                    r"轴[（(]?(债|名声|名字数|进度)", _payoff_m.group(1)
                ):
                    mf.append(
                        f"G4.cp.payoff_axis:{fp}:v3_requires_轴量声明 "
                        "（类型｜轴(债/名声/名字数/进度)｜量——四轴登记为兑现唯一口径）"
                    )

        # ── spec #75 G4.cp.declarations — 三声明行（时间锚/余额/POV）──
        # SKILL 承诺「新格式备忘缺任一行 = G4.cp FAIL」；旧格式（无场景预算
        # 块）= WARN 豁免（legacy 备忘只免声明行交叉核对，散文派生检查照跑）。
        _has_budget_block = re.search(r"#{2,4}\s*场景预算", content) is not None
        if _has_budget_block:
            _decls = load_memo_declarations(pf)
            _missing = [k for k in ("时间锚", "余额", "POV") if k not in _decls]
            if _missing:
                mf.append(
                    f"G4.cp.declarations:{fp}:missing_{'+'.join(_missing)} "
                    "(#75 三声明行——机器消费字段，缺行使跨章不变量门降级)"
                )
            else:
                c.append({"id": "G4.cp.declarations", "file": fp, "s": GateStatus.PASS})
        else:
            c.append(
                {
                    "id": "G4.cp.declarations",
                    "file": fp,
                    "s": GateStatus.WARN,
                    "r": "legacy memo (no scene-budget block) — declaration cross-check exempt, prose-derived checks still run",
                }
            )

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
        # line (§2). The window mirrors golden-3's hardcode (fixed 30).
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
