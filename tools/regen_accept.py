"""spec #79 regen-accept: per-criterion acceptance aggregator for the regen run.

Read-only verdict layer over already-persisted artifacts (report_longitudinal
precedent, tri-state exit 0 pass / 1 fail / 2 data error — fail-closed).
Criteria map (novel-market-overhaul 总设计 §4 + spec #79 §2):

  1    cross-chapter invariants — manifest gate key
       ``gates.chapter_loop.{ch}.pipeline-scene-split.G4.xc`` latest-wins PASS
  2a   chapter word band — floor via manifest check ids ``G4.word_count`` /
       ``G4.ln.word_count``; ceiling recomputed offline against genre-config
       ``chapter_word.max`` (``chapter_word_min_max`` single source)
  2b   drafting gate — remaining ``G4.cd.*`` check ids zero FAIL
  2c   emotional high proxy — memo ``emotion_tone`` cold-run streak <= 3 OR
       golden slot 燃 (deterministic positive/negative proxy; prose-level
       detection stays with the run project)
  3    volume planning nodes + 灰烬◆ slot deadline (lint_volume_nodes)
  4    voice/meme density (lint_voice_meme chapter + volume modes)
  5    real-chapter blind recognition — quote lines argmax-attributed from
       card catchphrases >= 4/5 per sampled protagonist
  6    release split on a temp copy (scene-atomic packing verified by the
       producer itself; aggregator asserts output exists + marker hygiene)
  7    ``just check`` — manual row (SKIP with the command to run)
  8    G3.4 independent scoring — RUN-PROJECT-ONLY (rubric delivered in-repo)

Zero LLM, zero dispatch, zero src/shenbi mutation. G4 manifest values appear
in BOTH dict (single run) and list (multi-run append) forms — records are
normalized to a list then reduced latest-by-timestamp before any scan.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shenbi.gates.shared import chapter_word_min_max, word_count_md
from shenbi.text.cjk import find_quote_spans
from shenbi.text.voice_lexicon import catchphrases_from_card

#: 判据 2c cold set — same family as #78 escalation_action's 3-cold trigger:
#: a cold streak longer than 3 means the emotional band has collapsed.
_COLD_TONES = {"悲", "惧", "平"}
_MAX_COLD_STREAK = 3

#: 判据 5 threshold — blind recognition per sampled protagonist.
_BLIND_MIN_RATIO = 4 / 5
_MIN_SAMPLED_ROLES = 5
_FAIL_DETAIL_CAP = 8
_FM_PARTS_MIN = 3

_EMOTION_RE = re.compile(r"emotion_tone\s*[:：]\s*[（(]?([^）)\s，,。]+)")
_GOLDEN_RE = re.compile(r"金句位\s*[:：]\s*(静|燃)｜")

_SCENE_SPLIT_SKILL = "pipeline-scene-split"
_XC_GATE_KEY = "G4.xc"
_FLOOR_IDS = ("G4.word_count", "G4.ln.word_count")
_CD_PREFIX = "G4.cd."


@dataclass
class Verdict:
    """Criterion row: status PASS/FAIL/SKIP + human-readable detail."""

    criterion: str
    status: str  # PASS | FAIL | SKIP | RUN-PROJECT-ONLY
    detail: str = ""

    def render(self) -> str:
        """Render one aligned criterion row."""
        return f"[{self.status:^16}] 判据 {self.criterion} {self.detail}".rstrip()


def _norm_records(manifest: dict[str, Any]) -> dict[tuple[int, str, str], dict[str, Any]]:
    """Normalize G4 values (dict single-run / list multi-run) latest-by-timestamp."""
    out: dict[tuple[int, str, str], dict[str, Any]] = {}
    for ch, skills in manifest.get("gates", {}).get("chapter_loop", {}).items():
        for skill, gate_keys in skills.items():
            for gk, val in gate_keys.items():
                for rec in val if isinstance(val, list) else [val]:
                    # manifest may carry bare strings (legacy markers) — only
                    # dict records carry a status; skip the rest (a skipped
                    # key then surfaces as 缺席 in the criterion, not a crash)
                    if not isinstance(rec, dict):
                        continue
                    # F8-era salvaged markers double-serialized `result` as a
                    # JSON string — re-parse so latest-wins comparison works.
                    if isinstance(rec.get("result"), str):
                        try:
                            rec["result"] = json.loads(rec["result"])
                        except ValueError:
                            rec["result"] = {}
                    key = (int(ch), skill, gk)
                    if key not in out or str(rec.get("timestamp", "")) >= str(
                        out[key].get("timestamp", "")
                    ):
                        out[key] = rec
    return out


def _failed_checks(rec: dict[str, Any], id_filter: Any) -> list[str]:
    """FAIL check ids under record.result.checks matching id_filter."""
    result = rec.get("result", {})
    return [
        c["id"] for c in result.get("checks", []) if c.get("s") == "FAIL" and id_filter(c["id"])
    ]


def _load_memo(plan_path: Path) -> str:
    return plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""


def check_xc(records: dict, through: int) -> Verdict:
    """判据 1: cross-chapter invariants (G4.xc gate key, latest-wins)."""
    rows = {ch for ch, skill, gk in records if skill == _SCENE_SPLIT_SKILL and gk == _XC_GATE_KEY}
    missing = [str(n) for n in range(1, through + 1) if n not in rows]
    fails = [
        f"ch{ch}"
        for ch, skill, gk in sorted(records)
        if skill == _SCENE_SPLIT_SKILL
        and gk == _XC_GATE_KEY
        and ch <= through
        and records[(ch, skill, gk)].get("result", {}).get("status") != "PASS"
    ]
    if missing:
        return Verdict("1", "FAIL", f"G4.xc 记录缺席章: {','.join(missing)}")
    if fails:
        return Verdict("1", "FAIL", f"G4.xc FAIL 章: {','.join(fails)}")
    return Verdict("1", "PASS", f"G4.xc 1-{through} 全 PASS（latest-wins）")


def check_word_band(project_dir: Path, records: dict, through: int) -> list[Verdict]:
    """判据 2a: floor (manifest ids) + ceiling (offline recompute vs config)."""
    floor_fails: list[str] = []
    for ch, _skill, _gk in sorted(records):
        if ch > through:
            continue
        rec = records[(ch, _skill, _gk)]
        for cid in _failed_checks(rec, lambda i: i in _FLOOR_IDS):
            floor_fails.append(f"ch{ch}:{cid}")
    v_floor = (
        Verdict("2a-floor", "PASS", "G4.word_count/G4.ln.word_count 零 FAIL")
        if not floor_fails
        else Verdict("2a-floor", "FAIL", "; ".join(floor_fails))
    )

    _, ceiling = chapter_word_min_max(project_dir)
    if ceiling is None:
        skip = Verdict(
            "2a-ceiling", "SKIP", "genre-config chapter_word.max 缺席（配置整体缺席才允许跳过）"
        )
        return [v_floor, skip]
    breaches = []
    for n in range(1, through + 1):
        chapter = project_dir / "chapters" / f"chapter-{n}.md"
        if not chapter.is_file():
            breaches.append(f"ch{n}:missing")
            continue
        if word_count_md(str(chapter)) > ceiling:
            breaches.append(f"ch{n}:{word_count_md(str(chapter))}>{ceiling}")
    v_ceil = (
        Verdict("2a-ceiling", "PASS", f"全部 ≤ chapter_word.max={ceiling}（离线复算）")
        if not breaches
        else Verdict("2a-ceiling", "FAIL", "; ".join(breaches))
    )
    return [v_floor, v_ceil]


def check_cd(project_dir: Path, records: dict, through: int) -> Verdict:
    """判据 2b: drafting-gate G4.cd.* ids zero FAIL (latest-wins)."""
    fails = []
    for ch, _skill, _gk in sorted(records):
        if ch > through:
            continue
        rec = records[(ch, _skill, _gk)]
        for cid in _failed_checks(rec, lambda i: i.startswith(_CD_PREFIX)):
            fails.append(f"ch{ch}:{cid}")
    if not fails:
        return Verdict("2b", "PASS", "G4.cd.* 零 FAIL（latest-wins）")
    head = "; ".join(fails[:_FAIL_DETAIL_CAP])
    more = "…" if len(fails) > _FAIL_DETAIL_CAP else ""
    return Verdict("2b", "FAIL", head + more)


def check_emotion_proxy(project_dir: Path, through: int) -> Verdict:
    """判据 2c: cold-streak proxy over memo emotion_tone + golden-slot 燃."""
    # spec #82 T1 (r3/r6): 10-chapter sliding window + shared cold predicate
    # (wordlist-external tones count as cold — the third escape hatch,
    # ch5/12/15 实证); absent memos within the window are skipped (volume-one
    # replay compatibility) instead of failing the whole check.
    from shenbi.text.recall_weight import cold_chapter  # noqa: PLC0415

    window = 10
    lo = max(1, through - window + 1)
    tones: list[tuple[int, str, bool]] = []
    for n in range(lo, through + 1):
        memo = _load_memo(project_dir / "plans" / f"chapter-{n}-plan.md")
        if not memo:
            continue  # 滑窗内缺席跳过（历史回放兼容——门面已拦，验收面不重复硬失败）
        m = _EMOTION_RE.search(memo)
        if not m:
            continue
        golden = _GOLDEN_RE.search(memo)
        hot = bool(golden and golden.group(1) == "燃")
        tones.append((n, m.group(1), hot))
    worst = 0
    streak = 0
    for _n, tone, hot in tones:
        if cold_chapter(tone, hot):
            streak += 1
            worst = max(worst, streak)
        else:
            streak = 0
    warm = sum(1 for _n, t, h in tones if not cold_chapter(t, h))
    if worst > _MAX_COLD_STREAK:
        detail = (
            f"近{window}章连续冷章最长 {worst} > {_MAX_COLD_STREAK}"
            f"（冷=词表外或 悲/惧/平 且金句位非燃——spec #82 共享谓词）"
        )
        return Verdict("2c", "FAIL", detail)
    return Verdict(
        "2c",
        "PASS",
        f"近{window}章最长冷连续 {worst} ≤ {_MAX_COLD_STREAK}；暖章 {warm}/{len(tones)}",
    )


def _run_tool(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, *args], capture_output=True, text=True, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def check_volume_nodes(project_dir: Path, volume: int) -> Verdict:
    """判据 3: planning nodes + slot deadlines (含 灰烬◆ ≤12)."""
    code, out = _run_tool(["tools/lint_volume_nodes.py", str(project_dir), "--volume", str(volume)])
    return (
        Verdict("3", "PASS", "lint_volume_nodes findings=0（含 灰烬◆ 首现≤12）")
        if code == 0
        else Verdict("3", "FAIL", out)
    )


def check_voice_meme(project_dir: Path, volume: int, through: int) -> Verdict:
    """判据 4: voice density chapter + volume modes."""
    fails = []
    modes = (
        ("chapter", ["--chapter", str(through)]),
        ("volume", ["--volume", str(volume)]),
    )
    for mode, extra in modes:
        code, out = _run_tool(["tools/lint_voice_meme.py", mode, str(project_dir), *extra])
        if code != 0:
            fails.append(f"{mode}: {out}")
    return (
        Verdict("4", "PASS", "lint_voice_meme chapter+volume 双模式绿")
        if not fails
        else Verdict("4", "FAIL", "; ".join(fails))
    )


@dataclass
class _Card:
    """Role card face: display name + catchphrase markers."""

    name: str
    markers: list[str]


def _card_name(text: str, fallback: str) -> str:
    """Frontmatter ``name`` first (authoritative), card heading second."""
    if text.lstrip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= _FM_PARTS_MIN:
            try:
                import yaml  # noqa: PLC0415 — lazy stdlib-adjacent dep, card face only

                fm = yaml.safe_load(parts[1])
                name = fm.get("name") if isinstance(fm, dict) else None
                if isinstance(name, str) and name.strip():
                    return name.strip()
            except Exception:  # noqa: BLE001 — heading fallback below
                pass
    m = re.search(r"^#+\s*(\S{2,4})", text, flags=re.M)
    return m.group(1) if m else fallback


def _load_cards(project_dir: Path) -> list[_Card]:
    cards: list[_Card] = []
    cdir = project_dir / "characters"
    if not cdir.is_dir():
        return cards
    for card in sorted(cdir.rglob("*.md")):
        if card.stem == "relationships":  # 关系表非角色卡
            continue
        text = card.read_text(encoding="utf-8")
        markers = catchphrases_from_card(text)
        if markers:
            cards.append(_Card(_card_name(text, card.stem), markers))
    return cards


def check_blind_recognition(project_dir: Path, through: int) -> Verdict:
    """判据 5: real-chapter blind recognition (catchphrase argmax per quote)."""
    cards = _load_cards(project_dir)
    if len(cards) < _MIN_SAMPLED_ROLES:
        return Verdict(
            "5", "FAIL", f"带卡面标记的角色卡仅 {len(cards)} 张（<{_MIN_SAMPLED_ROLES}）"
        )
    correct: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    for n in range(1, through + 1):
        chapter = project_dir / "chapters" / f"chapter-{n}.md"
        if not chapter.is_file():
            continue
        for para in chapter.read_text(encoding="utf-8").split("\n\n"):
            quotes = find_quote_spans(para)
            if not quotes:
                continue
            named = [c for c in cards if c.name in para]
            if len(named) != 1:  # 零命中或双名歧义段不归属（D4 粗粒度口径收窄）
                continue
            owner = named[0]
            # 盲认口径 = 引号内台词（叙述层的「那罕记账」动词不是说话人的声纹；
            # 段级计数把叙述噪声算进归属，连主角自测都 2/50——量谁在说，
            # 就只数谁说出口的那部分）
            spoken = "".join(para[a:b] for a, b in quotes)
            best, hits = None, 0
            for card in cards:
                cnt = sum(spoken.count(m) for m in card.markers)
                if cnt > hits:
                    best, hits = card, cnt
            total[owner.name] += 1
            # 零标记段无法盲认（best=None）——计错而非计对
            if best is not None and best.name == owner.name:
                correct[owner.name] += 1
    sampled = {k: v for k, v in total.items() if v > 0}
    if len(sampled) < _MIN_SAMPLED_ROLES:
        return Verdict(
            "5", "FAIL", f"有对白样本的角色仅 {len(sampled)} 个（<{_MIN_SAMPLED_ROLES}）"
        )
    ratios = {k: correct[k] / total[k] for k in sampled}
    weak = {k: f"{correct[k]}/{total[k]}" for k, r in ratios.items() if r < _BLIND_MIN_RATIO}
    detail = " ".join(f"{k}={correct[k]}/{total[k]}" for k in sorted(sampled))
    if weak:
        return Verdict("5", "FAIL", f"低于 4/5: {weak}｜{detail}")
    return Verdict("5", "PASS", f"五角色全 ≥4/5｜{detail}")


def check_release_split(project_dir: Path, through: int) -> Verdict:
    """判据 6: producer run on a temp copy (scene-atomic + marker hygiene)."""
    with tempfile.TemporaryDirectory(prefix="regen-accept-split-") as td:
        tmp = Path(td)
        for face in ("chapters", "pipeline-manifest.json", "genre-config.json", "novel.json"):
            src = project_dir / face
            if not src.exists():
                return Verdict("6", "FAIL", f"切分输入面缺席: {face}")
            dest = tmp / face
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from release_split import run_split  # noqa: PLC0415 — tools/ sibling

        try:
            run_split(
                tmp,
                platform=None,
                title_pattern=None,
                renumber_published=False,
                through=through,
            )
        except Exception as exc:  # noqa: BLE001 — producer failure IS the criterion result
            return Verdict("6", "FAIL", f"release_split: {exc}")
        published = list((tmp / "publish").rglob("*.md"))
        if not published:
            return Verdict("6", "FAIL", "publish/ 无产物")
        leaked = [f.name for f in published if "<!--SCENE-->" in f.read_text(encoding="utf-8")]
        if leaked:
            return Verdict("6", "FAIL", f"SCENE 标记泄漏进发布文本: {leaked}")
        return Verdict("6", "PASS", f"release_split 临时目录 {len(published)} 更、标记卫生合格")


def run_accept(project_dir: Path, through: int, volume: int = 1) -> int:
    """Aggregate all criteria; print rows; return 0 pass / 1 fail / 2 data error."""
    manifest_path = project_dir / "pipeline-manifest.json"
    chapters_dir = project_dir / "chapters"
    chapters = list(chapters_dir.glob("chapter-*.md")) if chapters_dir.is_dir() else []
    if not manifest_path.is_file() or not chapters:
        print(
            f"regen-accept: data error — manifest={'ok' if manifest_path.is_file() else 'MISSING'} "
            f"chapters={len(chapters)}（隔离后空基线或未起步：无可评数据）"
        )
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = _norm_records(manifest)
    if not records:
        print("regen-accept: data error — manifest 无 chapter_loop G4 记录")
        return 2

    verdicts = [
        check_xc(records, through),
        *check_word_band(project_dir, records, through),
        check_cd(project_dir, records, through),
        check_emotion_proxy(project_dir, through),
        check_volume_nodes(project_dir, volume),
        check_voice_meme(project_dir, volume, through),
        check_blind_recognition(project_dir, through),
        check_release_split(project_dir, through),
        Verdict("7", "SKIP", "just check 手动行——运行 `just check` 后人工确认"),
        Verdict(
            "8",
            "RUN-PROJECT-ONLY",
            "G3.4 独立评分（rubric: docs/regen-vol1-scoring-rubric.md）",
        ),
    ]
    for v in verdicts:
        print(v.render())
    if any(v.status == "FAIL" for v in verdicts):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: regen-accept <dir> --through N [--volume V]."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--through", type=int, required=True, help="evaluate chapters 1..N")
    parser.add_argument("--volume", type=int, default=1)
    args = parser.parse_args(argv)
    return run_accept(args.project_dir, args.through, args.volume)


if __name__ == "__main__":
    sys.exit(main())
