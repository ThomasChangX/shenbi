"""Spec #78 recall registry + weight checks (declarative, offline).

recall_window defaults 8 (market_params.recall_window ∈[3,20]); high-weight
entries use ceil(window/2) floored at the authored touch-chain gap. WARN rows
``- [recall] chN name gap`` / ``- [emotion-band] chN tone`` land in
truth/audit_drift (structurally excluded from count_drift_alerts).
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from shenbi.cli_utils import echo
from shenbi.gates.shared import strip_narrative_body
from shenbi.text.cjk import find_quote_spans

_DEATH_PATTERNS = re.compile(r"(萤死|而死|战死|病故|身死|殁)")
_CURRENT_DEATH = re.compile(r"已故|已消散")
_COLD_TONES = ("悲", "惧", "平")
_TONE_WORDLIST = frozenset({"悲", "喜", "怒", "惧", "平"})  # spec #82 cold predicate branch ①


@dataclass
class RecallEntry:
    """One dead character under the recall obligation."""

    name: str
    death_chapter: int
    weight: str = "中"
    aliases: tuple[str, ...] = field(default_factory=tuple)
    last_touch: int | None = None


def load_recall_registry(path: Path) -> list[RecallEntry]:
    """Parse truth/recall_registry.md rows: | 死者名 | 死亡章 | 权重 | 化名 | 末触章 |."""
    if not path.is_file():
        return []
    out: list[RecallEntry] = []
    for ln in path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"\|\s*([^|]+)\|\s*(\d+)\s*\|\s*(高|中)\s*\|\s*([^|]*)\|\s*([^|]*)\|", ln)
        if not m or m.group(1).strip() in ("死者名", "---") or set(m.group(1).strip()) <= {"-"}:
            continue
        last = m.group(5).strip()
        out.append(
            RecallEntry(
                name=m.group(1).strip(),
                death_chapter=int(m.group(2)),
                weight=m.group(3),
                aliases=tuple(
                    a.strip() for a in m.group(4).split("、") if a.strip() and a.strip() != "—"
                ),
                last_touch=int(last) if last.isdigit() else None,
            )
        )
    return out


def _card_death_chapter(card_text: str, volume_map: Path | None) -> int | None:
    """Death chapter from volume_map node-table cells (萤死/而死 族取证)."""
    if volume_map is None or not volume_map.is_file():
        return None
    for m in re.finditer(
        r"\|\s*第(\d+)章\s*\|[^|]*\|([^|]*)\|", volume_map.read_text(encoding="utf-8")
    ):
        if _DEATH_PATTERNS.search(m.group(2)):
            return int(m.group(1))
    return None


def seed_recall_registry(project_dir: Path) -> Path:
    """Cards + volume_map → truth/recall_registry.md (idempotent skip-if-exists)."""
    target = project_dir / "truth" / "recall_registry.md"
    if target.exists():
        echo("recall_registry 已存在——跳过", err=True)
        return target
    vm = project_dir / "outline" / "volume_map.md"
    rows: list[str] = [
        "# 死者回触登记（recall_registry）",
        "",
        "| 死者名 | 死亡章 | 权重 | 化名 | 末触章 |",
        "|---|---|---|---|---|",
    ]
    for area in ("major", "minor"):
        for card in sorted((project_dir / "characters" / area).glob("*.md")):
            text = card.read_text(encoding="utf-8")
            alive_marker = re.search(r"current_state[：:]\s*([^\n(（]*)", text)
            dead = bool(_CURRENT_DEATH.search(text)) or (
                alive_marker and any(k in alive_marker.group(1) for k in ("已故", "已消散"))
            )
            death_ch = _card_death_chapter(text, vm)
            # 化身卡（active）但卷内有死亡节点（萤死类）→ 死者行按化身名入表
            alias_death = False
            aliases_m0 = re.search(r"aliases_note[：:]\s*([^\n]+)", text)
            if not dead and death_ch is not None and aliases_m0:
                vm_text = vm.read_text(encoding="utf-8") if vm.is_file() else ""
                alias_death = "萤死" in vm_text or _DEATH_PATTERNS.search(vm_text) is not None
            if not dead and not alias_death and death_ch is None:
                continue
            nm = re.search(r"^name[：:]\s*(\S+)", text, re.MULTILINE)
            name = nm.group(1) if nm else card.stem
            weight = "高" if re.search(r"情感主轴|情感投资|挚友|至交|师承", text) else "中"
            aliases_m = re.search(r"aliases_note[：:]\s*([^\n]+)", text)
            alias_names: list[str] = []
            if aliases_m:
                note = aliases_m.group(1)
                # 裸名提取：学徒X/之女X/女童X 形态 + 顿号分隔的短名（≤3 字）
                alias_names = re.findall(r"(?:学徒|之女|女童|之子)([\u4e00-\u9fa5]{1,2})", note)
                alias_names += [
                    a.strip()
                    for a in re.split(r"[、，,；;]", note.split("；")[0])
                    if 0 < len(a.strip()) <= 3 and not re.search(r"卷|为|学徒|之女|女童|身份", a)
                ]
            aliases = "、".join(dict.fromkeys(alias_names)) or "—"
            if death_ch is None:
                death_ch = 0  # dead per marker but chapter unresolvable — row parked at 0 for manual_override
            rows.append(f"| {name} | {death_ch} | {weight} | {aliases} | — |")
    target.parent.mkdir(parents=True, exist_ok=True)
    from shenbi.safe_write import safe_write

    safe_write(target, ("\n".join(rows) + "\n").encode("utf-8"))
    return target


def _lexicons(project_dir: Path, extra: tuple[str, ...] = ()) -> list[str]:
    """物象（prop_registry 优雅降级）+ catchphrases + 登记名/化名 词串集。"""
    words = list(extra)
    prop = project_dir / "truth" / "prop_registry.md"
    if prop.is_file():
        for ln in prop.read_text(encoding="utf-8").split("\n"):
            m = re.match(r"\|\s*([^|\s][^|]*?)\s*\|", ln)
            if m and not set(m.group(1)) <= {"-", "实"} and "实体" not in m.group(1):
                words.append(m.group(1))
    for card in (project_dir / "characters").rglob("*.md"):
        from shenbi.text.voice_lexicon import catchphrases_from_card

        words.extend(catchphrases_from_card(card.read_text(encoding="utf-8")))
    nreg = project_dir / "truth" / "name_registry.md"
    if nreg.is_file():
        words.extend(
            re.findall(
                r"\|\s*(?:登记名|代词白名单|禁用名)\s*\|\s*([^|]+)\|",
                nreg.read_text(encoding="utf-8"),
            )
        )
    return [w for w in words if w]


def detect_recall(body: str, entry: RecallEntry, lexicons: list[str]) -> bool:
    """低成本回触：物象/小调（catchphrase 词串）/台词（名或化名在对白域）。"""
    stripped = strip_narrative_body(body)
    names = (entry.name, *entry.aliases)
    if any(n in stripped for n in names):
        return True
    if any(w in stripped for w in lexicons):
        return True
    return any(any(n in stripped[_s:_e] for n in names) for _s, _e in find_quote_spans(stripped))


def recall_warnings(
    project_dir: Path,
    chapter: int,
    *,
    recall_window: int = 8,
    extra_lexicons: tuple[str, ...] = (),
) -> list[str]:
    """`- [recall] chN 名 超窗n章` rows at one chapter (gap > window)."""
    entries = load_recall_registry(project_dir / "truth" / "recall_registry.md")
    lexicons = _lexicons(project_dir, extra_lexicons)
    rows: list[str] = []
    for e in entries:
        if e.death_chapter == 0:
            continue
        last = e.last_touch or e.death_chapter
        window = recall_window
        if e.weight == "高":
            window = max(math.ceil(recall_window / 2), 1)
        gap = chapter - last
        if gap > window:
            touched = False
            for n in range(last + 1, chapter + 1):
                f = project_dir / "chapters" / f"chapter-{n}.md"
                if f.is_file() and detect_recall(f.read_text(encoding="utf-8"), e, lexicons):
                    touched = True
                    break
            if not touched:
                rows.append(f"[recall] ch{chapter} {e.name} 超窗{gap}章（窗{window}）")
    return rows


def _tone_of(project_dir: Path, chapter: int) -> str | None:
    memo = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    if not memo.is_file():
        return None
    m = re.search(
        r"^emotion_tone[：:]\s*(悲|喜|怒|惧|平)", memo.read_text(encoding="utf-8"), re.MULTILINE
    )
    return m.group(1) if m else None


def cold_chapter(tone: str | None, golden_hot: bool) -> bool:
    """Shared cold predicate (spec #82 T1) — ordered branches, single source.

    ① tone outside the five-value wordlist → cold (wordlist-external takes
       priority over the golden exception — the third escape hatch);
    ② tone in {悲,惧,平} AND not golden-hot → cold (2c golden exception);
    ③ otherwise warm. Consumed by the G4.cp sequence gate, regen-accept 2c
    and the T0 snapshot write-validation.
    """
    if tone is None or tone not in _TONE_WORDLIST:
        return True
    return tone in _COLD_TONES and not golden_hot


def cold_run(project_dir: Path, chapter: int, *, lookback: int = 5) -> int:
    """Adjacent cold-chapter run ending at *chapter* (tone ∈ 悲/惧/平)."""
    run = 0
    for n in range(chapter, chapter - lookback, -1):
        if _tone_of(project_dir, n) in _COLD_TONES:
            run += 1
        else:
            break
    return run


def emotion_band_warnings(project_dir: Path, chapter: int) -> list[str]:
    tone = _tone_of(project_dir, chapter)
    if tone in _COLD_TONES:
        return [f"[emotion-band] ch{chapter} 冷章（{tone}；连续{cold_run(project_dir, chapter)}）"]
    return []


def escalation_action(project_dir: Path, chapter: int) -> str | None:
    """3 连冷 → 注入下一个未消费 转折/收官 节点；5 连 → CHECKPOINT；卷末降级 WARN."""
    run = cold_run(project_dir, chapter)
    if run >= 5:
        return "CHECKPOINT"
    if run >= 3:
        vm = project_dir / "outline" / "volume_map.md"
        if not vm.is_file():
            return None
        text = vm.read_text(encoding="utf-8")
        for m in re.finditer(r"\|\s*第(\d+)章\s*\|\s*(转折|收官)\s*\|([^|]*)\|", text):
            if int(m.group(1)) > chapter:
                return f"escalation 节点提前取用：第{m.group(1)}章（{m.group(2)}）{m.group(3).strip()[:30]}"
        return None  # 卷末无后续节点 → 降级 WARN（不跨卷）
    return None


def main(argv: list[str] | None = None) -> int:
    """CLI: seed / lint one chapter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["seed", "lint"])
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--chapter", type=int)
    args = parser.parse_args(argv)
    if args.mode == "seed":
        echo(f"seeded: {seed_recall_registry(args.project_dir)}")
        return 0
    rows = recall_warnings(args.project_dir, args.chapter or 1) + emotion_band_warnings(
        args.project_dir, args.chapter or 1
    )
    for r in rows:
        echo(f"- {r}")
    echo(f"recall-weight: ch{args.chapter} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
