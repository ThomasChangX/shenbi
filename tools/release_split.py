"""spec #70 release-split: deterministic publish-layer chapter splitting.

Reads only ``chapters/chapter-N.md``; writes only ``publish/<platform>/``.
No LLM, no pipeline faces. 口径 reused from shenbi.gates.shared.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.gates.shared import strip_narrative_body, total_chars_md_text

SCHEMA_ID = "shenbi-releases-v1"

# Closed scene-transition word list (spec §3.2) — the single source.
SCENE_TRANSITION_WORDS: frozenset[str] = frozenset(
    {
        "翌日",
        "次日",
        "清晨",
        "天亮",
        "黄昏",
        "入夜",
        "夜半",
        "午夜",
        "到了",
        "走进",
        "回到",
        "出门",
        "动身",
        "起程",
        "转场",
        "天明",
    }
)

_TENSION_END_CHARS = frozenset({"？", "！"})
_DIALOGUE_START_CHARS = frozenset({"“", "「", "『"})
_SHORT_OBJECT_SENTENCE_MAX = 40
_ORDINAL_MAX = 99
_HARD_FLOOR = 2000  # both tiers share this floor (spec §2)
_SIZE_SINGLE_GATE = 2 * _HARD_FLOOR  # gate < 4000 → size-single path first
_MIN_H1_LINES = 2
_MIN_SPLIT = 2  # splitting needs >= 2 更 and >= 2 paragraphs

CHAPTER_FILE_RE = re.compile(r"^chapter-(\d+)\.md$")
_PARA_SPLIT_RE = re.compile(r"\n\s*\n")
_TITLE_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")


class ReleaseSplitError(RuntimeError):
    """Structural input / freeze / ledger-lifecycle error (exit 1)."""


@dataclass(frozen=True)
class Tier:
    """Platform tier: hard floor / target / soft cap (spec §2)."""

    floor: int
    target: int
    soft: int


TIERS: dict[str, Tier] = {
    "fanqie": Tier(floor=2000, target=2200, soft=2400),
    "qidian": Tier(floor=2000, target=2700, soft=3000),
}


def nonws(s: str) -> int:
    """Non-whitespace char count — the spec's unified metric."""
    return len(re.sub(r"\s", "", s))


@dataclass(frozen=True)
class ChapterInput:
    """Parsed chapter: stripped narrative + title + 口径 counts."""

    path: Path
    number: int
    title: str
    gate_chars: int
    h1_nonws: int
    paragraphs: tuple[str, ...]


def select_chapter_files(chapters_dir: Path) -> list[Path]:
    """Numeric-ascending chapter files; rejects empty dir and duplicate numbers."""
    if not chapters_dir.is_dir():
        raise ReleaseSplitError(f"chapters/ 目录不存在: {chapters_dir}")
    picked: dict[int, Path] = {}
    for f in sorted(chapters_dir.iterdir()):
        m = CHAPTER_FILE_RE.match(f.name)
        if not (m and f.is_file()):
            continue
        num = int(m.group(1))
        if num in picked:
            raise ReleaseSplitError(
                f"同章号重复文件: chapter-{num}（{picked[num].name} 与 {f.name}）"
            )
        picked[num] = f
    if not picked:
        raise ReleaseSplitError(f"chapters/ 内零匹配章: {chapters_dir}")
    return [picked[n] for n in sorted(picked)]


def parse_chapter(path: Path) -> ChapterInput:
    """Strip (shared 口径) → extract ALL H1 lines → split paragraphs.

    Structural errors: empty file / no second H1 / no surviving paragraphs.
    """
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ReleaseSplitError(f"章文件为空: {path.name}")
    m = CHAPTER_FILE_RE.match(path.name)
    if m is None:  # pragma: no cover - callers go through select_chapter_files
        raise ReleaseSplitError(f"文件名不匹配: {path.name}")
    body = strip_narrative_body(raw)
    h1_lines = [ln for ln in body.splitlines() if ln.startswith("# ")]
    if len(h1_lines) < _MIN_H1_LINES:
        raise ReleaseSplitError(f"章文件无第二个 H1（章题提取失败）: {path.name}")
    title = h1_lines[1].lstrip("#").strip()
    for h in h1_lines:
        body = body.replace(h, "", 1)
    paras = tuple(p for p in _PARA_SPLIT_RE.split(body) if nonws(p) > 0)
    if not paras:
        raise ReleaseSplitError(f"剥离后无正文段: {path.name}")
    return ChapterInput(
        path=path,
        number=int(m.group(1)),
        title=title,
        gate_chars=total_chars_md_text(raw),
        h1_nonws=sum(nonws(h) for h in h1_lines),
        paragraphs=paras,
    )


@dataclass(frozen=True)
class CutSignals:
    """Closed-set scoring outcome for one candidate cut."""

    score: int
    tension: bool
    scene: bool
    waist: bool


def classify_pair(prev: str, next_para: str | None) -> CutSignals:
    """Score a cut between prev and next paragraphs (spec §3.2 closed rules).

    ``next_para=None`` is the end-of-chapter imaginary cut: tension
    predicates live, scene/waist predicates are dead.
    """
    pn = re.sub(r"\s", "", prev)
    score = 0
    tension = False
    if pn and pn[-1] in _TENSION_END_CHARS:
        score += 2
        tension = True
    if len(pn) <= _SHORT_OBJECT_SENTENCE_MAX:
        score += 2
        tension = True
    if pn and pn[0] in _DIALOGUE_START_CHARS:
        score += 2
        tension = True
    scene = False
    waist = False
    if next_para is not None:
        fn = re.sub(r"\s", "", next_para)
        if any(fn.startswith(w) for w in SCENE_TRANSITION_WORDS):
            score += 1
            scene = True
        if any(pn.startswith(w) for w in SCENE_TRANSITION_WORDS):
            score -= 2
            waist = True
    return CutSignals(score=score, tension=tension, scene=scene, waist=waist)


def tier_of(sig: CutSignals) -> str:
    """Quality tier by predicate firing (spec §3.4)."""
    if sig.tension:
        return "tension"
    if sig.scene:
        return "scene"
    if sig.waist:
        return "weak"
    return "plain"


_CN_DIGITS = "零一二三四五六七八九"


def chinese_ordinal(k: int) -> str:
    """1..99 → 一 … 九十九 (per-chapter release ordinal, spec §4)."""
    if not 1 <= k <= _ORDINAL_MAX:
        raise ValueError(f"中文序数仅支持 1-{_ORDINAL_MAX}: {k}")
    tens, ones = divmod(k, 10)
    parts: list[str] = []
    if tens >= 1:
        parts.append("十" if tens == 1 else _CN_DIGITS[tens] + "十")
    if ones >= 1:
        parts.append(_CN_DIGITS[ones])
    return "".join(parts)


def initial_n(gate_chars: int, tier: Tier) -> int:
    """§2: size-single first, then ceil(gate/soft) with single floor fallback."""
    if gate_chars < 2 * tier.floor:
        return 1
    n = -(-gate_chars // tier.soft)  # ceil
    if gate_chars / n < tier.floor:
        n -= 1
    return max(n, 1)


def _select_cut(
    paras: tuple[str, ...],
    prefix: list[int],
    prev_cut_pos: int,
    i: int,
    m: int,
    body: int,
    floor: int,
) -> int | None:
    """Select the boundary index for cut i; None when the feasible set is empty.

    Window∩feasible has candidates → max score (tie → earlier position);
    otherwise → feasible candidate nearest to target t_i = i*body/m
    (exact-rational cross-multiplication, tie → earlier).
    """
    lo = prev_cut_pos + floor
    hi = body - floor * (m - i)
    half = (15 * body) // (100 * m)
    ib = i * body
    in_win: list[tuple[int, int]] = []  # (boundary j, position)
    feasible: list[tuple[int, int]] = []
    for j in range(1, len(paras)):
        p = prefix[j]
        if lo <= p <= hi:
            feasible.append((j, p))
            # closed interval: p*m >= ib - half*m and p*m <= ib + half*m
            if p * m >= ib - half * m and p * m <= ib + half * m:
                in_win.append((j, p))
    if not feasible:
        return None
    if in_win:
        return max(
            in_win,
            key=lambda jp: (classify_pair(paras[jp[0] - 1], paras[jp[0]]).score, -jp[1]),
        )[0]
    return min(feasible, key=lambda jp: (abs(jp[1] * m - ib), jp[1]))[0]


def plan_releases(ch: ChapterInput, n: int, tier: Tier) -> tuple[list[tuple[int, int]], int]:
    """Constrained-window selection (spec §3.2) → paragraph-index groups + m."""
    paras = ch.paragraphs
    sizes = [nonws(p) for p in paras]
    body = sum(sizes)
    # prefix[j] = non-ws chars before boundary j (after paragraphs 0..j-1)
    prefix: list[int] = [0]
    for s in sizes:
        prefix.append(prefix[-1] + s)

    if n < _MIN_SPLIT or len(paras) < _MIN_SPLIT:
        return [(0, len(paras))], 1

    floor = tier.floor
    m = n
    while True:
        cuts: list[int] = []  # chosen boundary indices
        infeasible = False
        for i in range(1, m):
            j = _select_cut(paras, prefix, prefix[cuts[-1]] if cuts else 0, i, m, body, floor)
            if j is None:
                m -= 1
                if m < _MIN_SPLIT:
                    return [(0, len(paras))], 1
                infeasible = True
                break
            cuts.append(j)
        if not infeasible:
            groups: list[tuple[int, int]] = []
            start = 0
            for c in cuts:
                groups.append((start, c))
                start = c
            groups.append((start, len(paras)))
            return groups, m


def build_release_text(paras: tuple[str, ...] | list[str]) -> str:
    """Paragraphs joined with a blank line + exactly one trailing newline."""
    return "\n\n".join(paras) + "\n"


def content_hash_of(text: str) -> str:
    """sha256 of the release FILE bytes (UTF-8), first 16 hex chars."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def render_title(pattern: str | None, chapter_title: str, ordinal: str | None) -> str:
    """Default ``{章题}（{中文序数}）``; single 更 → bare title."""
    if pattern is None:
        return chapter_title if ordinal is None else f"{chapter_title}（{ordinal}）"

    def _sub(m: re.Match[str]) -> str:
        key = m.group(1)
        if key == "章题":
            return chapter_title
        if key == "中文序数":
            if ordinal is None:
                raise ReleaseSplitError("单更无 {中文序数}，标题模式不可含该占位符")
            return ordinal
        raise ReleaseSplitError(f"--title-pattern 含未知占位符: {{{key}}}")

    return _TITLE_PLACEHOLDER_RE.sub(_sub, pattern)


def chapter_flags(gate: int, body: int, m: int) -> list[str]:
    """§3.3 flags matrix — size rule owns all gate<4000 chapters first."""
    if gate < _SIZE_SINGLE_GATE:
        flags = ["single-release"]
        if body < _HARD_FLOOR:
            flags.append("floor-violation")
        return flags
    if m == 1:
        return ["forced-single"]
    return []


def nonws_head_tail(text: str) -> tuple[str, str]:
    """First/last ≤12 non-ws chars of the slice, single-line."""
    flat = re.sub(r"\s", "", text)
    return flat[:12], flat[-12:]


def split_chapter(ch: ChapterInput, tier: Tier, title_pattern: str | None) -> dict[str, Any]:
    """Per-chapter ledger entry (seq/file placeholders assigned in T5)."""
    n = initial_n(ch.gate_chars, tier)
    groups, m = plan_releases(ch, n, tier)
    body = sum(nonws(p) for p in ch.paragraphs)
    flags = chapter_flags(ch.gate_chars, body, m)
    offset = 0
    releases: list[dict[str, Any]] = []
    for k, (s, e) in enumerate(groups):
        text = build_release_text(ch.paragraphs[s:e])
        chars = nonws(text)
        ordinal = None if m == 1 else chinese_ordinal(k + 1)
        # cut_quality: 更 k = its terminating cut (cut k); 末更 = imaginary
        # end-cut (tension predicates live, scene/waist dead)
        if e < len(ch.paragraphs):
            sig = classify_pair(ch.paragraphs[e - 1], ch.paragraphs[e])
        else:
            sig = classify_pair(ch.paragraphs[e - 1], None)
        releases.append(
            {
                "seq": 0,  # assigned globally in T5
                "file": "",  # assigned globally in T5
                "chars": chars,
                "range": [offset, offset + chars],
                "cut_quality": tier_of(sig),
                "head": nonws_head_tail(text)[0],
                "tail": nonws_head_tail(text)[1],
                "title": render_title(title_pattern, ch.title, ordinal),
                "content_hash": content_hash_of(text),
                "published": False,
                "_paras": (s, e),
                "_text": text,
            }
        )
        offset += chars
    return {
        "chapter": ch.number,
        "gate_chars": ch.gate_chars,
        "stripped_chars": ch.gate_chars - sum(r["chars"] for r in releases),
        "flags": flags,
        "releases": releases,
    }


def load_ledger(platform_dir: Path, platform: str) -> dict[str, Any] | None:
    """Load + validate the existing platform ledger; None when absent."""
    path = platform_dir / "releases.json"
    if not path.exists():
        return None
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ReleaseSplitError(f"releases.json 畸形 JSON: {e}") from e
    if not isinstance(ledger, dict):
        raise ReleaseSplitError(f"releases.json 顶层非对象: {type(ledger).__name__}")
    if ledger.get("schema") != SCHEMA_ID:
        raise ReleaseSplitError(
            f"releases.json schema 不符: {ledger.get('schema')!r} != {SCHEMA_ID!r}"
        )
    if ledger.get("platform") != platform:
        raise ReleaseSplitError(
            f"releases.json platform 不符: {ledger.get('platform')!r} != {platform!r}"
        )
    return ledger


def _validate_freeze(
    old: dict[str, Any],
    by_number: dict[int, dict[str, Any]],
    renumber_published: bool,
) -> None:
    """Spec §4 freeze triple + vanished-chapter lifecycle; drift manifest under escape."""
    drifts: list[str] = []
    for cnum, oc in {c["chapter"]: c for c in old.get("chapters", [])}.items():
        pub = [r for r in oc.get("releases", []) if r.get("published")]
        if not pub:
            continue  # unfrozen: vanish → drop+renumber; present → re-cut freely
        if cnum not in by_number:
            raise ReleaseSplitError(f"在册章 chapter-{cnum} 已消失且含冻结条目（人工账本手术）")
        new_entry = by_number[cnum]
        # 对齐旧章完整更列表（非前缀 published 集：更1+更3 已发而更2 未发是合法形态）
        old_rels = oc.get("releases", [])
        for k, orl in enumerate(old_rels):
            if not orl.get("published"):
                continue
            if k >= len(new_entry["releases"]):
                raise ReleaseSplitError(f"chapter-{cnum} 重切后更数少于冻结更数")
            nr = new_entry["releases"][k]
            if nr["content_hash"] != orl["content_hash"]:
                raise ReleaseSplitError(
                    f"chapter-{cnum} 更 {k + 1} 内容哈希漂移于冻结条目（无逃生口，人工账本手术）"
                )
            if (nr["seq"], nr["file"]) != (orl["seq"], orl["file"]):
                drifts.append(
                    f"chapter-{cnum} 更 {k + 1}: "
                    f"seq {orl['seq']}\u2192{nr['seq']} file {orl['file']}\u2192{nr['file']}"
                )
            nr["published"] = True
    if drifts and not renumber_published:
        raise ReleaseSplitError(
            "冻结序号/路径漂移（--renumber-published 逃生口需人工确认平台侧同步改名）: "
            + "; ".join(drifts)
        )
    for line in drifts:
        print(f"renumber-published: {line}")


def _write_products(
    entries: list[dict[str, Any]], platform_dir: Path, platform: str
) -> dict[str, Any]:
    """Write releases/*.md + releases.json; orphan cleanup; return the ledger."""
    rel_dir = platform_dir / "releases"
    totals_rels = [r for e in entries for r in e["releases"]]
    for e in entries:
        for r in e["releases"]:
            (rel_dir / r["file"]).write_text(r["_text"], encoding="utf-8")
    referenced = {r["file"] for r in totals_rels}
    for f in rel_dir.glob("release-*.md"):  # 孤儿清理：仅本平台 releases/
        if f.name not in referenced:
            f.unlink()
    ledger: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "platform": platform,
        "generated_at": datetime.now(UTC).isoformat(),
        "chapters": [
            {
                "chapter": e["chapter"],
                "gate_chars": e["gate_chars"],
                "stripped_chars": e["stripped_chars"],
                "flags": e["flags"],
                "releases": [
                    {k: v for k, v in r.items() if not k.startswith("_")} for r in e["releases"]
                ],
            }
            for e in entries
        ],
        "totals": {
            "releases": len(totals_rels),
            "chars": sum(r["chars"] for r in totals_rels),
            "min_chars": min((r["chars"] for r in totals_rels), default=0),
            "max_chars": max((r["chars"] for r in totals_rels), default=0),
            "cut_quality": {
                q: sum(1 for r in totals_rels if r["cut_quality"] == q)
                for q in ("tension", "scene", "plain", "weak")
            },
            "flags": {
                f: sum(1 for e in entries if f in e["flags"])
                for f in ("single-release", "forced-single", "floor-violation")
            },
        },
    }
    (platform_dir / "releases.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return ledger


def run_split(
    project_dir: Path,
    platform: str,
    title_pattern: str | None,
    renumber_published: bool,
) -> int:
    """One idempotent split pass over the project's chapters (exit 0/1)."""
    tier = TIERS[platform]
    files = select_chapter_files(project_dir / "chapters")
    chapters = [parse_chapter(f) for f in files]

    platform_dir = project_dir / "publish" / platform
    (platform_dir / "releases").mkdir(parents=True, exist_ok=True)
    old = load_ledger(platform_dir, platform)

    entries = [split_chapter(ch, tier, title_pattern) for ch in chapters]
    by_number = {e["chapter"]: e for e in entries}
    seq = 0
    for e in entries:
        for r in e["releases"]:
            seq += 1
            r["seq"] = seq
            r["file"] = f"release-{seq:04d}.md"

    if old is not None:
        _validate_freeze(old, by_number, renumber_published)

    ledger = _write_products(entries, platform_dir, platform)
    t = ledger["totals"]
    print(
        f"release-split[{platform}]: chapters={len(entries)} "
        f"releases={t['releases']} chars={t['chars']} "
        f"min={t['min_chars']} max={t['max_chars']} "
        f"quality={t['cut_quality']} flags={t['flags']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: argparse usage errors exit 2; ReleaseSplitError exits 1."""
    parser = argparse.ArgumentParser(
        prog="release-split",
        description="发布切分层：已收束章节 → 平台档位发布更（spec #70，纯确定性）",
    )
    parser.add_argument("project_dir", type=Path, help="项目目录（含 chapters/）")
    parser.add_argument("--platform", choices=sorted(TIERS), default="fanqie")
    parser.add_argument(
        "--title-pattern", default=None, help="更题模式（占位符 {章题}/{中文序数}）"
    )
    parser.add_argument("--renumber-published", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run_split(
            args.project_dir, args.platform, args.title_pattern, args.renumber_published
        )
    except ReleaseSplitError as e:
        print(f"release-split: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
