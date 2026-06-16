"""G6: round integrity gate.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19).
"""

from shenbi.logging import get_logger

log = get_logger(__name__)


import json
import re
from pathlib import Path
from typing import Any

from shenbi.gates.g6_checks import check_continuity, check_pacing, check_style_consistency
from shenbi.gates.shared import (
    CHAPTER_WORD_FLOOR,
    FIXTURES,
    PROJECT,
    TESTS,
    fail,
    jload,
    passed,
)


def gate_G6(
    pipeline_name: str | None = None, round_dir: str | None = None, project_dir: str | None = None
) -> str:
    """G6: T3 Pipeline check."""
    c, mf = [], []
    deps = jload(TESTS / "tiers" / "deps.json")
    pipe_data = deps.get("t3-pipelines", {}).get(pipeline_name, {})
    min_ratio = pipe_data.get("min_chapter_ratio", 0.5)
    pd = Path(project_dir) if project_dir else PROJECT

    # G6.1: chapter count >= ceil(expected * min_ratio)
    nj = pd / "novel.json"
    target_words = jload(str(nj)).get("target_words", 100000) if nj.exists() else 100000
    gc = pd / "genre-config.json"
    default_w = (
        jload(str(gc)).get("chapter_word", {}).get("default", CHAPTER_WORD_FLOOR)
        if gc.exists()
        else CHAPTER_WORD_FLOOR
    )
    expected = -(-target_words // default_w)
    min_chapters = int(-(-(expected * min_ratio) // 1))
    chapters = []
    nums: list[int] = []
    ch_dir = pd / "chapters"
    if ch_dir.exists():
        chapters = sorted(ch_dir.glob("chapter-*.md"))
        if len(chapters) < min_chapters:
            mf.append(f"G6.1:{len(chapters)}<{min_chapters}(ceil({expected}*{min_ratio}))")
        else:
            c.append({"id": "G6.1", "s": "PASS", "chapters": len(chapters)})
        # G6.2: no gaps
        for ch in chapters:
            m = re.search(r"chapter-(\d+)", ch.name)
            if m:
                nums.append(int(m.group(1)))
        if nums and sorted(nums) != list(range(min(nums), max(nums) + 1)):
            mf.append("G6.2:chapter_gaps")
        else:
            c.append({"id": "G6.2", "s": "PASS"})
        # G6.3: each chapter passes G4 chapter-drafting
        for ch in chapters:
            try:
                from shenbi.gates.g4 import gate_G4

                g4r = json.loads(gate_G4("shenbi-chapter-drafting", "generative", [str(ch)]))
                if g4r.get("status") == "FAIL":
                    mf.append(f"G6.3:{ch.name}")
            except Exception as e:
                mf.append(f"G6.3:{ch.name}:exception={e}")
        if not any(x.startswith("G6.3:") for x in mf):
            c.append({"id": "G6.3", "s": "PASS"})
    else:
        mf.append("G6.1:no_chapters_dir")

    # G6.4 + G6.5: continuity and pacing checks (extracted to g6_checks.py)
    g64_checks, g64_mf = check_continuity(chapters)
    c.extend(g64_checks)
    mf.extend(g64_mf)

    g65_checks, g65_mf = check_pacing(chapters)
    c.extend(g65_checks)
    mf.extend(g65_mf)

    # G6.7: foreshadowing lifecycle (pending_hooks.md)
    hooks_path = pd / "truth" / "pending_hooks.md"
    if hooks_path.exists():
        hook_text = hooks_path.read_text()
        # Parse YAML-like hook entries (after "## hooks" section)
        hooks_section = hook_text.split("## hooks")[-1] if "## hooks" in hook_text else hook_text
        # Extract hook blocks using regex
        hook_blocks = re.split(r"\n- id:", hooks_section)
        hook_blocks = ["id:" + b for b in hook_blocks if b.strip()]
        total_hooks = len(hook_blocks)
        unresolved = 0
        exceeded = []
        planted_chapters = []
        for block in hook_blocks:
            hid_m = re.search(r"id:\s*(\S+)", block)
            state_m = re.search(r"state:\s*(\S+)", block)
            maxd_m = re.search(r"max_distance:\s*(\d+)", block)
            plant_m = re.search(r"plant_chapter:\s*(\d+)", block)
            hid = hid_m.group(1) if hid_m else "??"
            state = state_m.group(1) if state_m else "??"
            if state != "RESOLVED" and state != "resolved":
                unresolved += 1
            if maxd_m and plant_m:
                maxd = int(maxd_m.group(1))
                planted = int(plant_m.group(1))
                max_ch = max(nums) if nums else planted
                if max_ch - planted > maxd:
                    exceeded.append(f"{hid}:planted={planted}:max_ch={max_ch}:maxd={maxd}")
            if plant_m:
                planted_chapters.append(int(plant_m.group(1)))
        if exceeded:
            mf.extend([f"G6.7:max_distance_exceeded:{x}" for x in exceeded])
        # Hook density
        density: float | None = None
        if chapters:
            density = total_hooks / max(len(chapters), 1)
            if density > 3:
                mf.append(f"G6.7:high_hook_density:{density:.1f}/chapter")
            elif density < 0.3:
                mf.append(f"G6.7:low_hook_density:{density:.1f}/chapter")
        # Unresolved at end
        if unresolved > 0:
            c.append(
                {
                    "id": "G6.7",
                    "s": "PASS",
                    "total_hooks": total_hooks,
                    "unresolved": unresolved,
                    "exceeded": len(exceeded),
                    "density": round(density, 2) if density is not None else None,
                }
            )
        else:
            c.append({"id": "G6.7", "s": "PASS", "total_hooks": total_hooks, "all_resolved": True})
    else:
        c.append(
            {"id": "G6.7", "s": "SKIP", "r": "need truth/pending_hooks.md for foreshadowing check"}
        )

    # G6.8: character voice consistency (voice_profile + catchphrase check)
    char_dir6 = pd / "characters"
    if char_dir6.exists() and chapters:
        char_voice: dict[str, dict[str, Any]] = {}  # name -> voice_data
        for cf in char_dir6.rglob("*.md"):
            try:
                ct = cf.read_text()
                nm_m = re.search(r"^name:\s*(\S+)", ct, re.MULTILINE)
                if not nm_m:
                    continue
                cname = nm_m.group(1)
                has_vp = "voice_profile:" in ct
                cps = []
                if has_vp:
                    # Extract catchphrases
                    cp_section = ct[ct.index("voice_profile:") :] if "voice_profile:" in ct else ""
                    cps = re.findall(r'"([^"]{2,30})"', cp_section)
                char_voice[cname] = {
                    "has_voice_profile": has_vp,
                    "catchphrases": cps,
                    "file": cf.name,
                }
            except Exception:
                pass
        # Ghost detection: character appears in chapters but no voice_profile
        for ch in chapters[:15]:  # sample up to 15 chapters
            ct = ch.read_text()[:5000]
            for cname, vdata in char_voice.items():
                if not vdata["has_voice_profile"] and cname in ct and len(cname) >= 2:
                    mf.append(f"G6.8:ghost_voice:{cname}:in_{ch.name}:no_voice_profile")
        # Catchphrase matching
        for cname, vdata in char_voice.items():
            if vdata["catchphrases"] and vdata["has_voice_profile"]:
                found_any = False
                for cp in vdata["catchphrases"][:3]:  # check top 3 catchphrases
                    for ch in chapters[:15]:
                        if cp in ch.read_text()[:5000]:
                            found_any = True
                            break
                    if found_any:
                        break
                if not found_any:
                    c.append(
                        {
                            "id": "G6.8",
                            "s": "WARN",
                            "r": f"{cname}:catchphrases_not_found_in_chapters",
                        }
                    )
        c.append(
            {
                "id": "G6.8",
                "s": "PASS",
                "chars_with_voice": sum(1 for v in char_voice.values() if v["has_voice_profile"]),
                "chars_total": len(char_voice),
            }
        )
    else:
        c.append({"id": "G6.8", "s": "SKIP", "r": "need characters/ and chapters/ for voice check"})

    # G6.9: world rule compliance — scan numerical constraints and check chapters
    rules_path = pd / "world" / "rules.md"
    if rules_path.exists() and chapters:
        rules_text = rules_path.read_text()
        # Extract numerical constraints: "不超过N人", "至少N个", "≥N", "≤N", "N天内", "N章内"
        constraints: list[dict[str, Any]] = []
        num_const_pat = re.compile(
            r"(?:不超过|不超|最多|至多|至少|不少于|≥|≤|\>|\<|等于)\s*(\d+)\s*(?:个|种|人|章|次|处|条|名|位|倍|%|万|千|百|天|日|小时|分钟|年|月)?",
            re.MULTILINE,
        )
        for m in num_const_pat.finditer(rules_text):
            val = int(m.group(1))
            # get surrounding context for keyword
            ctx_start = max(0, m.start() - 40)
            ctx = rules_text[ctx_start : m.end() + 40].replace("\n", " ")
            # Determine constraint type from full match text
            op_full = m.group(0)
            is_upper_bound = any(x in op_full for x in ["不超过", "不超", "最多", "至多", "≤"])
            is_lower_bound = any(x in op_full for x in ["至少", "不少于", "≥"])
            constraints.append(
                {"val": val, "ctx": ctx[:80], "upper": is_upper_bound, "lower": is_lower_bound}
            )
        # Scan chapters for violations of simple numerical constraints
        # Pre-read chapter contents for performance (avoid re-reading per constraint)
        ch_contents = []
        for ch in chapters:
            try:
                ch_contents.append((ch.name, ch.read_text()[:3000]))
            except Exception:
                ch_contents.append((ch.name, ""))
        for const in constraints[:10]:  # limit to 10 constraints for performance
            val = const["val"]
            ctx = const["ctx"]
            if "人" in ctx or "个" in ctx:
                # Look for related scenes in chapters with higher counts
                key_words = (
                    re.findall(r"[一-鿿]{2,}", ctx.split(str(val))[0]) if str(val) in ctx else []
                )
                for kw in key_words[:3]:
                    for ch_name, ct in ch_contents:
                        # Find numeric patterns near the keyword
                        for nm in re.finditer(
                            rf"{re.escape(kw)}\D{{0,20}}(\d+)\s*(?:人|个|名)", ct
                        ):
                            found_val = int(nm.group(1))
                            if const["upper"] and found_val > val:
                                mf.append(f"G6.9:limit_exceeded:{kw}:{found_val}>{val}:{ch_name}")
                            elif const["lower"] and found_val < val:
                                mf.append(f"G6.9:below_minimum:{kw}:{found_val}<{val}:{ch_name}")
        c.append({"id": "G6.9", "s": "PASS", "constraints_extracted": len(constraints)})
    else:
        c.append(
            {
                "id": "G6.9",
                "s": "SKIP",
                "r": "need world/rules.md and chapters/ for world rule compliance",
            }
        )

    # G6.10: style consistency (extracted to g6_checks.py)
    style_path = pd / "config" / "style_profile.md"
    g610_checks, g610_mf = check_style_consistency(style_path, chapters)
    c.extend(g610_checks)
    mf.extend(g610_mf)

    # G6.11: volume boundary adherence — read volume_map.md, verify chapter coverage
    vm_path = pd / "outline" / "volume_map.md"
    if vm_path.exists():
        vm_text = vm_path.read_text()
        # Extract volume-chapter mappings: "第一卷", "第X卷", "Volume N", chapter ranges
        volumes: list[dict[str, Any]] = []
        vol_pat = re.compile(r"(?:第\s*(\d+|[一二三四五六七八九十百千]+)\s*卷|Volume\s+(\d+))")
        _ch_range_pat = re.compile(
            r"(?:第\s*(\d+)\s*[章節].*?(?:第\s*(\d+)\s*[章節]|(\d+)\s*[章節]))"
        )
        # Simpler: find "第X章" to "第Y章" or "Chapter X-Y" patterns
        range_pat = re.compile(r"(?:chapters?|第)\s*(\d+)\s*[-—\-到至]\s*(\d+)")
        for m in vol_pat.finditer(vm_text):
            vnum = m.group(1) or m.group(2)
            # Find the nearest chapter range after this volume header
            rem = vm_text[m.end() : m.end() + 300]
            rm = range_pat.search(rem)
            if rm:
                start_ch = int(rm.group(1))
                end_ch = int(rm.group(2))
                volumes.append({"vol": vnum, "start": start_ch, "end": end_ch})
        # Deduplicate volumes by name (keep first occurrence)
        seen_vols = set()
        deduped: list[dict[str, Any]] = []
        for vol in volumes:
            if vol["vol"] not in seen_vols:
                seen_vols.add(vol["vol"])
                deduped.append(vol)
        volumes = deduped
        if volumes and chapters:
            # Verify chapters exist for each volume
            for vol in volumes:
                vol_start = int(vol["start"])
                vol_end = int(vol["end"])
                ch_in_vol = [
                    ch
                    for ch in chapters
                    if (cn_m := re.search(r"chapter-(\d+)", ch.name))
                    and vol_start <= int(cn_m.group(1)) <= vol_end
                ]
                if not ch_in_vol:
                    mf.append(f"G6.11:no_chapters:vol{vol['vol']}:range={vol_start}-{vol_end}")
                # Check volume-ending hook: last chapter should have >=1 tangible hook (except final volume)
                is_final = vol == volumes[-1]
                if not is_final and ch_in_vol:

                    def _ch_num(c: Path) -> int:
                        m = re.search(r"chapter-(\d+)", c.name)
                        return int(m.group(1)) if m else 0

                    last_ch = sorted(ch_in_vol, key=_ch_num)[-1]
                    last_ct = last_ch.read_text()
                    hook_markers = ["伏笔", "暗示", "悬念", "未解", "待续", "将", "预告", "铺垫"]
                    if not any(h in last_ct[-1000:] for h in hook_markers):
                        mf.append(f"G6.11:no_ending_hook:vol{vol['vol']}:ch={last_ch.name}")
            c.append(
                {
                    "id": "G6.11",
                    "s": "PASS",
                    "volumes": len(volumes),
                    "chapters_total": len(chapters),
                }
            )
        elif volumes:
            c.append(
                {
                    "id": "G6.11",
                    "s": "PASS",
                    "volumes": len(volumes),
                    "note": "no chapters/ to verify",
                }
            )
        else:
            c.append({"id": "G6.11", "s": "SKIP", "r": "no volume ranges found in volume_map.md"})
    else:
        c.append(
            {
                "id": "G6.11",
                "s": "SKIP",
                "r": "need outline/volume_map.md for volume boundary check",
            }
        )

    # G6.6: ghost character detection
    cm_path = pd / "truth" / "character_matrix.md"
    if cm_path.exists() and chapters:
        dead_chars = set()
        for line in cm_path.read_text().split("\n"):
            m = re.match(r"\|\s*(\S+?)\s*\|.*死亡", line)
            if m:
                dead_chars.add(m.group(1))
        ghosts_found = []
        for ch in chapters:
            content = ch.read_text()
            for dc in dead_chars:
                if dc in content:
                    ghosts_found.append(f"{dc}:{ch.name}")
        if ghosts_found:
            mf.extend([f"G6.6:{g}" for g in ghosts_found])
        else:
            c.append({"id": "G6.6", "s": "PASS"})
    else:
        c.append(
            {
                "id": "G6.6",
                "s": "SKIP",
                "r": "need character_matrix.md and chapters/ for ghost check",
            }
        )

    # G6.12: sensitive word scan (standalone token detection to avoid substring false positives)
    sw_path = FIXTURES / "sensitive_words.txt"
    if sw_path.exists() and chapters:
        sensitive = [
            l.strip()
            for l in sw_path.read_text().split("\n")
            if l.strip() and not l.startswith("#")
        ]
        sw_found = []
        for ch in chapters:
            content = ch.read_text()
            for word in sensitive:
                # Only flag as standalone token (surrounded by whitespace/punctuation),
                # not as substring of other words
                if re.search(rf"(?:^|[^\w]){re.escape(word)}(?:$|[^\w])", content):
                    sw_found.append(f"{word}:{ch.name}")
        if sw_found:
            mf.extend([f"G6.12:{s}" for s in sw_found])
        else:
            c.append({"id": "G6.12", "s": "PASS"})
    else:
        c.append(
            {"id": "G6.12", "s": "SKIP", "note": "sensitive_words.txt missing — round INCOMPLETE"}
        )

    if mf:
        return fail("G6", c, "scoring", mf)
    return passed("G6", c)
