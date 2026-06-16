"""Cross-chapter continuity and pacing checks for G6.

Extracted from g6.py to keep file length under 500 lines.
"""

import re
from pathlib import Path
from typing import Any


def check_continuity(chapters: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    """G6.4: cross-chapter continuity (timeline monotonicity, information state).

    Returns (checks, mf_entries).
    """
    if not chapters:
        return ([{"id": "G6.4", "s": "SKIP", "r": "need chapters/ for continuity check"}], [])

    violations: list[str] = []
    day_pat = re.compile(r"第\s*(\d+)\s*(?:天|日|夜)")
    date_pat = re.compile(r"(\d+)\s*月\s*(\d+)\s*[日号]")
    stage_pat = re.compile(r"(?:阶段|第)\s*(\d+)\s*(?:阶段|步|回合)")

    timeline: list[tuple[int, int, str]] = []
    for ch in chapters:
        cn_match = re.search(r"chapter-(\d+)", ch.name)
        if not cn_match:
            continue
        cn = int(cn_match.group(1))
        ct = ch.read_text()[:5000]
        for m in day_pat.finditer(ct):
            timeline.append((cn, int(m.group(1)), "day"))
        for m in date_pat.finditer(ct):
            timeline.append((cn, int(m.group(1)) * 100 + int(m.group(2)), "date"))
        for m in stage_pat.finditer(ct):
            timeline.append((cn, int(m.group(1)), "stage"))

    for i in range(1, len(timeline)):
        pc, pv, pt = timeline[i - 1]
        cc, cv, _ = timeline[i]
        if pt == timeline[i][2] and cv < pv and cc >= pc:
            violations.append(f"timeline_regression:ch{pc}->ch{cc}:{pv}->{cv}({pt})")

    intro_map: dict[str, int] = {}
    entity_pat = re.compile(r"(?:灵能\S+|位面\S+|金手指|革命|起义|矿场|据点)")
    know_pat = re.compile(r"(?:知道|明白|意识到|了解|学会|懂得|掌握|想起|回忆)")
    for ch in chapters:
        cn_match = re.search(r"chapter-(\d+)", ch.name)
        if not cn_match:
            continue
        cn = int(cn_match.group(1))
        ct = ch.read_text()[:3000]
        entities = set(m.group(0) for m in entity_pat.finditer(ct))
        for ent in entities:
            if ent not in intro_map:
                intro_map[ent] = cn
        for know_m in know_pat.finditer(ct):
            post_ctx = ct[know_m.end() : know_m.end() + 50]
            ref_entities = set(m.group(0) for m in entity_pat.finditer(post_ctx))
            for re_ent in ref_entities:
                if re_ent in intro_map and intro_map[re_ent] > cn:
                    violations.append(
                        f"future_knowledge:ch{cn}:knows_{re_ent}_intro_ch{intro_map[re_ent]}"
                    )

    mf = [f"G6.4:{v}" for v in violations[:10]]
    if violations:
        return ([], mf)
    return (
        [
            {
                "id": "G6.4",
                "s": "PASS",
                "chapters": len(chapters),
                "note": "timeline and info-state ok",
            }
        ],
        [],
    )


def check_pacing(chapters: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    """G6.5: pacing rhythm — classify chapters, check variety and tension curve.

    Returns (checks, mf_entries).
    """
    if not chapters:
        return ([{"id": "G6.5", "s": "SKIP", "r": "need chapters/ for pacing check"}], [])

    ch_types: list[dict[str, Any]] = []
    for ch in chapters:
        cn_match = re.search(r"chapter-(\d+)", ch.name)
        if not cn_match:
            continue
        cn = int(cn_match.group(1))
        ct = ch.read_text()
        body = ct
        for tag_pat in [
            r"^---\n.*?\n---\n",
            r"```.*?```",
            r"## PRE_WRITE_CHECK.*?(?=## |\Z)",
            r"## POST_WRITE_SELF_CHECK.*?(?=## |\Z)",
            r"## 润色说明.*?(?=## |\Z)",
            r"## 改写报告.*?(?=## |\Z)",
            r"## 归一化报告.*?(?=## |\Z)",
        ]:
            body = re.sub(tag_pat, "", body, flags=re.DOTALL)
        action_count = len(
            re.findall(r"(?:爆炸|战斗|攻击|闪避|格挡|冲锋|斩杀|灵力爆发|拳|剑|刀|枪)", body)
        )
        dialogue_chars = len(re.findall(r'[""][^""]*[""]', body)) + len(
            re.findall(r"「[^」]*」", body)
        )
        body_chars = len(re.findall(r"[一-鿿]", body))
        dialogue_pct = (dialogue_chars / body_chars * 100) if body_chars > 0 else 0
        inner_mono = len(re.findall(r"(?:心想|暗想|暗道|心说|默念|内心)", body))
        scene_breaks = len(re.findall(r"^---\s*$", body, re.MULTILINE))
        if action_count > 15 and dialogue_pct < 30:
            cht = "action"
        elif dialogue_pct > 35:
            cht = "dialogue"
        elif inner_mono > 8:
            cht = "introspection"
        elif scene_breaks >= 2:
            cht = "transition"
        else:
            cht = "narrative"
        ch_types.append({"ch": cn, "type": cht, "dialogue_pct": round(dialogue_pct, 1)})

    mf: list[str] = []
    consec = 1
    for i in range(1, len(ch_types)):
        if ch_types[i]["type"] == ch_types[i - 1]["type"]:
            consec += 1
            if consec >= 4:
                mf.append(
                    f"G6.5:4_consecutive_{ch_types[i]['type']}:ch{ch_types[i - 3]['ch']}-ch{ch_types[i]['ch']}"
                )
        else:
            consec = 1

    action_density = [
        (
            t["ch"],
            sum(
                1
                for x in ch_types[max(0, i - 2) : min(len(ch_types), i + 3)]
                if x["type"] == "action"
            ),
        )
        for i, t in enumerate(ch_types)
    ]
    peaks = [ch for ch, d in action_density if d >= 3]
    if len(ch_types) >= 8 and not peaks:
        mf.append("G6.5:no_action_peaks")

    return ([{"id": "G6.5", "s": "PASS", "ch_types": ch_types, "action_peaks": len(peaks)}], mf)


def check_style_consistency(
    style_path: Path, chapters: list[Path]
) -> tuple[list[dict[str, Any]], list[str]]:
    """G6.10: style consistency — read style_profile.md, sample chapters vs ranges.

    Returns (checks, mf_entries).
    """
    if not style_path.exists() or not chapters:
        return (
            [
                {
                    "id": "G6.10",
                    "s": "SKIP",
                    "r": "need config/style_profile.md and chapters/ for style check",
                }
            ],
            [],
        )

    style_text = style_path.read_text()
    ranges: dict[str, float] = {}
    sent_pat = re.search(
        r"(?:句长|句子长度).*?(\d+\.?\d*)\s*(?:[-\~—到至])\s*(\d+\.?\d*)", style_text
    )
    para_pat = re.search(r"(?:段长|段落).*?(\d+\.?\d*)\s*(?:[-\~—到至])\s*(\d+\.?\d*)", style_text)
    dia_pat = re.search(
        r"(?:对白占比|对话占比).*?(\d+\.?\d*)\s*%?\s*(?:[-\~—到至])\s*(\d+\.?\d*)\s*%?",
        style_text,
    )
    if sent_pat:
        ranges["sent_lo"] = float(sent_pat.group(1))
        ranges["sent_hi"] = float(sent_pat.group(2))
    if para_pat:
        ranges["para_lo"] = float(para_pat.group(1))
        ranges["para_hi"] = float(para_pat.group(2))
    if dia_pat:
        ranges["dia_lo"] = float(dia_pat.group(1))
        ranges["dia_hi"] = float(dia_pat.group(2))

    if not ranges:
        for line in style_text.split("\n"):
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 5 and cells[0].startswith("第"):
                try:
                    avg_sent = float(cells[-2]) if len(cells) >= 6 else None
                    avg_para = float(cells[-1]) if len(cells) >= 6 else None
                    if avg_sent and "sent_lo" not in ranges:
                        ranges["sent_lo"] = avg_sent * 0.6
                        ranges["sent_hi"] = avg_sent * 1.4
                    if avg_para and "para_lo" not in ranges:
                        ranges["para_lo"] = max(1, avg_para * 0.5)
                        ranges["para_hi"] = avg_para * 1.5
                except ValueError:
                    pass
                break

    if not ranges:
        return (
            [
                {
                    "id": "G6.10",
                    "s": "SKIP",
                    "r": "could not extract style ranges from style_profile.md",
                }
            ],
            [],
        )

    outliers: list[str] = []
    for ch in chapters[: min(10, len(chapters))]:
        ct = ch.read_text()
        body = ct
        body = re.sub(r"^---\n.*?\n---\n", "", body, flags=re.DOTALL)
        body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        for tag_rx in [
            r"## PRE_WRITE_CHECK.*?(?=## |\Z)",
            r"## POST_WRITE_SELF_CHECK.*?(?=## |\Z)",
            r"## 润色说明.*?(?=## |\Z)",
            r"## 改写报告.*?(?=## |\Z)",
            r"## 归一化报告.*?(?=## |\Z)",
        ]:
            body = re.sub(tag_rx, "", body, flags=re.DOTALL)
        sent_marks = len(re.findall(r"[。！？\.!\?]", body))
        paras = len(re.findall(r"\n\s*\n", body)) + 1
        ch_chars = len(re.findall(r"[一-鿿]", body))
        dia_chars = len(re.findall(r"「[^」]*」", body)) + len(re.findall(r'"[^"]*"', body))
        if paras > 0 and ch_chars > 0:
            avg_sent_ch = ch_chars / max(sent_marks, 1)
            avg_para_ch = ch_chars / max(paras, 1)
            dia_pct_ch = (dia_chars / ch_chars * 100) if ch_chars > 0 else 0
            if "sent_lo" in ranges and (
                avg_sent_ch < ranges["sent_lo"] or avg_sent_ch > ranges["sent_hi"]
            ):
                outliers.append(f"sentence:{ch.name}:avg={avg_sent_ch:.1f}")
            if "para_lo" in ranges and (
                avg_para_ch < ranges["para_lo"] or avg_para_ch > ranges["para_hi"]
            ):
                outliers.append(f"paragraph:{ch.name}:avg={avg_para_ch:.1f}")
            if "dia_lo" in ranges and (
                dia_pct_ch < ranges["dia_lo"] or dia_pct_ch > ranges["dia_hi"]
            ):
                outliers.append(f"dialogue:{ch.name}:pct={dia_pct_ch:.1f}%")

    if outliers:
        return ([], [f"G6.10:{o}" for o in outliers[:8]])
    return (
        [
            {
                "id": "G6.10",
                "s": "PASS",
                "ranges": ranges,
                "chapters_sampled": min(10, len(chapters)),
            }
        ],
        [],
    )
