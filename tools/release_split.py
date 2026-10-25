"""spec #72 release-split v2: declarative scene-atomic publish packing.

qidian tier: 1 chapter = 1 更 (direct, title from the 2nd H1).
fanqie tier: durable ``<!--SCENE-->`` markers are the packing atoms —
``pack_scenes`` (single source, gates.shared) groups adjacent scenes into
更 of the configured ``chapter_word.fanqie_update`` band, boundaries land
ONLY on scene edges, every 更 closes on its final scene's hook line, and
marker lines never reach the published text. Settled window comes from
pipeline-manifest per-chapter gate records (latest-per-key PASS + the
``pipeline-scene-split`` key). v1 heuristics (SCENE_TRANSITION_WORDS /
tension cuts / TIERS) retired (spec #72 施工面 6).
Reads only ``chapters/chapter-N.md`` + ``pipeline-manifest.json`` +
``genre-config.json``; writes only ``publish/<platform>/``. No LLM, no
pipeline faces. 口径 reused from shenbi.gates.shared.
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

from shenbi.gates.shared import (
    is_scene_marker_line,
    pack_scenes,
    strip_narrative_body,
    strip_scene_markers,
    total_chars_md_text,
)

SCHEMA_ID = "shenbi-releases-v2"

#: Platforms (v2): qidian = native 1:1; fanqie = scene-atomic packing.
PLATFORMS = ("fanqie", "qidian")
_DEFAULT_PLATFORM = "fanqie"
#: Manifest key whose per-chapter presence settles a chapter (spec 施工面 6).
_SPLIT_STEP_SKILL = "pipeline-scene-split"

_MIN_H1_LINES = 2
_ORDINAL_MAX = 99
_SCENE_HOOK_PREVIEW = 24

CHAPTER_FILE_RE = re.compile(r"^chapter-(\d+)\.md$")
_PARA_SPLIT_RE = re.compile(r"\n\s*\n")
_TITLE_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")


class ReleaseSplitError(RuntimeError):
    """Structural input / freeze / ledger-lifecycle error (exit 1)."""


def nonws(s: str) -> int:
    """Non-whitespace char count — the spec's unified metric."""
    return len(re.sub(r"\s", "", s))


@dataclass(frozen=True)
class SceneText:
    """One marker-delimited scene (durable in the chapter file)."""

    index: int
    size: int  # non-ws chars, marker excluded
    text: str  # marker-stripped prose paragraphs
    last_line: str  # the declared hook lands here


@dataclass(frozen=True)
class ChapterInput:
    """Parsed chapter: stripped narrative + title + scenes + 口径 counts."""

    path: Path
    number: int
    title: str
    gate_chars: int
    h1_nonws: int
    paragraphs: tuple[str, ...]
    scenes: tuple[SceneText, ...]


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
    # strip each piece: a chapter file ending in a single trailing "\n" rides
    # that newline on the last paragraph and would double the file-final "\n"
    # (spec §4 byte composition: exactly one trailing newline per release file)
    paras = tuple(p.strip() for p in _PARA_SPLIT_RE.split(body) if nonws(p) > 0)
    if not paras:
        raise ReleaseSplitError(f"剥离后无正文段: {path.name}")
    # spec #72: durable markers delimit the packing atoms. Marker lines are
    # excluded from every published text (strip_scene_markers).
    markered = raw.splitlines()
    # R5-M1: single-source marker predicate (the 4th consumer).
    marker_idx = [i for i, ln in enumerate(markered) if is_scene_marker_line(ln)]
    trailing_meta = next(
        (
            i
            for i, ln in enumerate(markered)
            if ln.startswith("## ") and (not marker_idx or i > marker_idx[-1])
        ),
        len(markered),
    )
    scenes: list[SceneText] = []
    for k, s in enumerate(marker_idx):
        e = marker_idx[k + 1] if k + 1 < len(marker_idx) else trailing_meta
        seg = strip_scene_markers("\n".join(markered[s + 1 : e])).strip()
        if not seg:
            continue
        seg_paras = [q for q in (x.strip() for x in _PARA_SPLIT_RE.split(seg)) if q]
        last_line = next(ln.strip() for ln in reversed(seg.splitlines()) if ln.strip())
        scenes.append(
            SceneText(
                index=k,
                size=nonws(seg),
                text=build_release_text(seg_paras),
                last_line=last_line,
            )
        )
    return ChapterInput(
        path=path,
        number=int(m.group(1)),
        title=title,
        gate_chars=total_chars_md_text(raw),
        h1_nonws=sum(nonws(h) for h in h1_lines),
        paragraphs=paras,
        scenes=tuple(scenes),
    )


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


def nonws_head_tail(text: str) -> tuple[str, str]:
    """First/last ≤12 non-ws chars of the slice, single-line."""
    flat = re.sub(r"\s", "", text)
    return flat[:12], flat[-12:]


def fanqie_update_band(project_dir: Path) -> tuple[int, int]:
    """更带 from genre-config ``chapter_word.fanqie_update`` (hard requirement)."""
    gc = project_dir / "genre-config.json"
    if not gc.is_file():
        raise ReleaseSplitError(
            "v2 起发布切分硬依赖 genre-config.json（chapter_word.fanqie_update 更带）——缺配置"
        )
    try:
        data = json.loads(gc.read_text(encoding="utf-8"))
        fq = data.get("chapter_word", {}).get("fanqie_update", {})
        lo, hi = int(fq["min"]), int(fq["max"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        raise ReleaseSplitError(
            f"chapter_word.fanqie_update 更带缺失/畸形（v2 硬依赖）: {e}"
        ) from e
    if not 0 < lo <= hi:
        raise ReleaseSplitError(f"fanqie_update 带非法: [{lo},{hi}]")
    return lo, hi


def default_platform(project_dir: Path) -> str:
    """Default platform: primary_platform key, else the v1 default fanqie."""
    gc = project_dir / "genre-config.json"
    if gc.is_file():
        try:
            v = json.loads(gc.read_text(encoding="utf-8")).get("primary_platform")
            if v in PLATFORMS:
                return str(v)
        except json.JSONDecodeError:
            pass
    return _DEFAULT_PLATFORM


def settled_chapters(project_dir: Path) -> set[int]:
    """Settled chapters (spec 施工面 6).

    manifest ``gates.chapter_loop`` phase; latest record per key is PASS
    and the chapter carries a pipeline-scene-split G4 key.
    """
    mf = project_dir / "pipeline-manifest.json"
    if not mf.is_file():
        return set()
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    settled: set[int] = set()
    for ch_key, skills in (data.get("gates", {}).get("chapter_loop", {}) or {}).items():
        try:
            n = int(ch_key)
        except ValueError:
            continue
        has_split_key = False
        ok = True
        for skill, gates in (skills or {}).items():
            if skill == _SPLIT_STEP_SKILL:
                has_split_key = any("G4" in str(g) for g in (gates or {}))
            for _gate, rec in (gates or {}).items():
                latest = rec[-1] if isinstance(rec, list) else rec
                status = (latest or {}).get("result", {}).get("status")
                if status is not None and status != "PASS":
                    ok = False
        if ok and has_split_key:
            settled.add(n)
    return settled


def split_chapter_qidian(ch: ChapterInput, title_pattern: str | None) -> dict[str, Any]:
    """Qidian tier: 1 chapter = 1 update (direct title, markers stripped)."""
    text = build_release_text(list(ch.paragraphs))  # 已经 strip（标记/元数据剥除）
    chars = nonws(text)
    releases = [
        {
            "seq": 0,
            "file": "",
            "chars": chars,
            "range": [0, chars],
            "cut_quality": "direct-1v1",
            "head": nonws_head_tail(text)[0],
            "tail": nonws_head_tail(text)[1],
            "title": render_title(title_pattern, ch.title, None),
            "content_hash": content_hash_of(text),
            "published": False,
            "_text": text,
        }
    ]
    return {
        "chapter": ch.number,
        "gate_chars": ch.gate_chars,
        "stripped_chars": ch.gate_chars - chars,
        "flags": ["direct-1v1"],
        "releases": releases,
    }


def split_chapters_fanqie(
    chapters: list[ChapterInput], band: tuple[int, int], title_pattern: str | None
) -> list[dict[str, Any]]:
    """Fanqie tier: cross-chapter scene-stream greedy packing (one group per 更)."""
    atoms: list[tuple[ChapterInput, SceneText]] = [(ch, sc) for ch in chapters for sc in ch.scenes]
    if not atoms:
        raise ReleaseSplitError("已收束章内零场景标记（fanqie 档以场景为原子）")
    sizes = [sc.size for _ch, sc in atoms]
    groups = pack_scenes(sizes, band)
    if groups is None:
        offending = ", ".join(f"{s}" for s in sizes[:12])
        raise ReleaseSplitError(
            f"场景序列贪心不可打包（更带 [{band[0]},{band[1]}]）——offending 场景字数: {offending}"
        )
    entries: dict[int, dict[str, Any]] = {}
    i = 0
    for group in groups:
        members = atoms[i : i + len(group)]
        i += len(group)
        text = "".join(sc.text for _ch, sc in members)
        first_ch = members[0][0]
        ch_releases = entries.setdefault(
            first_ch.number,
            {
                "chapter": first_ch.number,
                "gate_chars": first_ch.gate_chars,
                "stripped_chars": 0,
                "flags": [],
                "releases": [],
            },
        )
        ch_releases["releases"].append(
            {
                "seq": 0,
                "file": "",
                "chars": sum(sc.size for _c, sc in members),
                "range": [0, 0],
                "cut_quality": "scene-hook",
                "head": nonws_head_tail(text)[0],
                "tail": members[-1][1].last_line[:_SCENE_HOOK_PREVIEW],
                "title": "",  # 序数在更数确定后渲染（见下）
                "content_hash": content_hash_of(text),
                "published": False,
                "cross_chapter": len({c.number for c, _s in members}) > 1,
                "_text": text,
            }
        )
    # 序数/标题：每章更数确定后渲染
    for entry in entries.values():
        m = len(entry["releases"])
        # 找回该章的 ChapterInput 以取章题
        ch = next(c for c in chapters if c.number == entry["chapter"])
        for k, rel in enumerate(entry["releases"]):
            ordinal = None if m == 1 else chinese_ordinal(k + 1)
            rel["title"] = render_title(title_pattern, ch.title, ordinal)
            if rel["cross_chapter"]:
                entry["flags"].append("cross-chapter-group")
            rel.pop("_ch_title", None)
    return [entries[c.number] for c in chapters if c.number in entries]


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
                for q in ("direct-1v1", "scene-hook")
            },
            "cross_chapter_groups": sum(1 for r in totals_rels if r.get("cross_chapter")),
        },
    }
    (platform_dir / "releases.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return ledger


def run_split(
    project_dir: Path,
    platform: str | None,
    title_pattern: str | None,
    renumber_published: bool,
    through: int | None = None,
) -> int:
    """One idempotent split pass over the project's SETTLED chapters (exit 0/1)."""
    plat = platform or default_platform(project_dir)
    settled = settled_chapters(project_dir)
    if through is not None:
        settled = {n for n in settled if n <= through}  # 收窄不豁免
    # F3: filter by FILENAME chapter number BEFORE parsing — an unsettled
    # (possibly mid-flight / malformed) chapter must not abort the run.
    wanted = [
        f
        for f in select_chapter_files(project_dir / "chapters")
        if int(CHAPTER_FILE_RE.match(f.name).group(1)) in settled
    ]
    chapters = [parse_chapter(f) for f in wanted]
    if not chapters:
        raise ReleaseSplitError(
            "已收束章集合为空（manifest 逐章闸记录无全 PASS + scene-split 键的章）"
        )

    if plat == "qidian":
        entries = [split_chapter_qidian(ch, title_pattern) for ch in chapters]
    else:
        band = fanqie_update_band(project_dir)
        entries = split_chapters_fanqie(chapters, band, title_pattern)

    platform_dir = project_dir / "publish" / plat
    (platform_dir / "releases").mkdir(parents=True, exist_ok=True)
    old = load_ledger(platform_dir, plat)

    by_number = {e["chapter"]: e for e in entries}
    seq = 0
    for e in entries:
        for r in e["releases"]:
            seq += 1
            r["seq"] = seq
            r["file"] = f"release-{seq:04d}.md"

    if old is not None:
        _validate_freeze(old, by_number, renumber_published)

    ledger = _write_products(entries, platform_dir, plat)
    t2 = ledger["totals"]
    print(
        f"release-split[{plat}]: chapters={len(entries)} "
        f"releases={t2['releases']} chars={t2['chars']} "
        f"min={t2['min_chars']} max={t2['max_chars']} "
        f"quality={t2['cut_quality']} cross={t2.get('cross_chapter_groups', 0)}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: argparse usage errors exit 2; ReleaseSplitError exits 1."""
    parser = argparse.ArgumentParser(
        prog="release-split",
        description="发布切分层：已收束章节 → 平台档位发布更（spec #70，纯确定性）",
    )
    parser.add_argument("project_dir", type=Path, help="项目目录（含 chapters/）")
    parser.add_argument(
        "--platform",
        choices=sorted(PLATFORMS),
        default=None,
        help="缺省读 genre-config.primary_platform（无键回退 fanqie）",
    )
    parser.add_argument(
        "--through",
        type=int,
        default=None,
        help="打包域上限章号（收窄不豁免：取 1..N 内仍满足已收束谓词的章）",
    )
    parser.add_argument(
        "--title-pattern", default=None, help="更题模式（占位符 {章题}/{中文序数}）"
    )
    parser.add_argument("--renumber-published", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run_split(
            args.project_dir,
            args.platform,
            args.title_pattern,
            args.renumber_published,
            args.through,
        )
    except ReleaseSplitError as e:
        print(f"release-split: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
