"""Shared helpers for gate validation.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19). All gate modules
import these helpers to keep behavior identical to the legacy monolith.
"""

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write
from shenbi.status import GateResult, GateStatus
from shenbi.text.cjk import find_quote_spans

log = get_logger(__name__)


import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

PROJECT = Path(__file__).resolve().parents[3]
SKILLS = PROJECT / "skills"
TESTS = PROJECT / "tests"
FIXTURES = TESTS / "fixtures"
CHAPTER_WORD_FLOOR = 3000
CHAPTER_WORD_CEILING = 10000

#: Chapter-file contract anchors. SINGLE SOURCE for both the write-path
#: normalizer (pipeline.dispatch_helper) and the gate-side check (gates.g2)
#: — a second copy of either regex anywhere is a contract drift (z11 F1301).
META_BLOCK_RE = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)

#: Scene-boundary marker contract (spec #72). SINGLE SOURCE for all four
#: consumers — splitter / G4 scene count / revision marker-diff / release_split
#: v2 boundary detection. Durable in final chapter files (rendering-invisible
#: standalone comment line); stripped from every counting surface below.
SCENE_MARKER = "<!--SCENE-->"


def is_scene_marker_line(line: str) -> bool:
    """Standalone SCENE marker predicate: exact match after strip()."""
    return line.strip() == SCENE_MARKER


def strip_scene_markers(text: str) -> str:
    """Remove standalone SCENE marker lines (blank line left in place)."""
    return "\n".join(ln for ln in text.split("\n") if not is_scene_marker_line(ln))


#: Scene-size domains (spec #72 two-type rule): 独立型 [1800, 2000] packs alone
#: as one 更; 配对型 [900, 1400] packs in adjacent pairs; [1400, 1800) is the
#: banned gray zone. Single source for planner/splitter/G4/v2.
SCENE_INDEPENDENT_BAND = (1800, 2000)
SCENE_PAIRED_BAND = (900, 1400)

#: Memo scene-budget declaration line (planning SKILL contract):
#: ``- 场景1: 1900字｜独立型｜收束钩：<hook text>``
_SCENE_DECL_RE = re.compile(
    r"^-\s*场景(\d+):\s*(\d+)字｜(独立型|配对型)｜收束钩：(.+?)\s*$",
    re.MULTILINE,
)


def parse_scene_declarations(memo_text: str) -> list[tuple[int, int, str, str]]:
    """Declared scene budgets from a planning memo (pure text parse).

    Returns ``[(场景序号, 字数, 型别, 钩原文), ...]``; empty when the memo
    carries no scene-budget block (pre-#72 memos).
    """
    return [
        (int(m.group(1)), int(m.group(2)), m.group(3), m.group(4))
        for m in _SCENE_DECL_RE.finditer(memo_text)
    ]


def split_scenes(text: str) -> list[tuple[int, str]]:
    """Marker-delimited scenes of ONE chapter file: [(size, last_line), ...].

    Scene k spans (marker_k, next marker | first trailing meta H2); pure
    text split — the G4 scene checks and revision revalidation consume this
    without needing the bundle machinery.
    """
    lines = text.split("\n")
    marker_idx = [i for i, ln in enumerate(lines) if is_scene_marker_line(ln)]
    if not marker_idx:
        return []
    # F4 (regen v3): the trailing self-check block is META-wrapped — the
    # <!--META-BEGIN--> marker line precedes its H2, so the boundary must
    # catch either form or the marker itself becomes the last scene's 末行.
    trailing_meta = next(
        (
            i
            for i, ln in enumerate(lines)
            if (ln.startswith("## ") or ln.startswith("<!--META")) and i > marker_idx[-1]
        ),
        len(lines),
    )
    out: list[tuple[int, str]] = []
    for k, start in enumerate(marker_idx):
        end = marker_idx[k + 1] if k + 1 < len(marker_idx) else trailing_meta
        seg = [ln for ln in lines[start + 1 : end] if ln.strip()]
        if not seg:
            continue
        size = sum(len(re.sub(r"\s", "", ln)) for ln in seg)
        out.append((size, seg[-1].strip()))
    return out


def scene_hook_mismatches(
    decls: list[tuple[int, int, str, str]], scenes: list[tuple[int, str]]
) -> list[str]:
    """Declared-vs-actual scene-hook mismatches (spec #72 single predicate).

    ``decls`` from :func:`parse_scene_declarations`; ``scenes`` from
    :func:`split_scenes`. Predicate: the declared hook text (whitespace-
    stripped) must be a substring of the scene's final non-empty line.
    Consumed by BOTH the G4.cd gate and the post-revision revalidation —
    one predicate, no drift.
    """
    import re as _re

    issues: list[str] = []
    for k, (_num, _size, _kind, hook) in enumerate(decls):
        want = _re.sub(r"\s", "", hook)
        if k < len(scenes):
            got = _re.sub(r"\s", "", scenes[k][1])
            if want not in got:
                issues.append(
                    f"场景{k + 1} 钩未落款: 声明「{hook[:20]}」vs 末行「{scenes[k][1][:20]}」"
                )
        else:
            issues.append(f"场景{k + 1} 声明多于实际场景数 {len(scenes)}")
    return issues


def pack_scenes(
    sizes: list[int],
    update_band: tuple[int, int],
    *,
    allow_open_tail: bool = False,
) -> list[list[int]] | None:
    """Greedy scene-run packing for 番茄 更 (spec 施工面 6; pure math).

    Deterministic single source — the SAME function backs the G4.cp precheck
    and release_split v2, so precheck-pass guarantees v2-pass on the same
    input. Returns the grouping, or ``None`` when greedy-unpackageable
    (CONSERVATIVE: a greedy-failing sequence may admit a non-greedy partition,
    e.g. [1800, 900, 900] fails here though [[1800], [900, 900]] is valid —
    such bundles take a planning re-dispatch; pinned by test).

    ``allow_open_tail=True`` (planning-time precheck): the FINAL run may be
    under-weight — a bundle's trailing 配对型 scene legitimately pairs with
    the NEXT bundle's first scene, so the precheck window ends open. v2's
    terminal packing keeps the default (every 更 complete within the packed
    window).
    """
    lo, hi = update_band
    groups: list[list[int]] = []
    current: list[int] = []
    for size in sizes:
        if size > hi:
            return None  # single scene can never fit
        if current and sum(current) + size > hi:
            if sum(current) < lo:
                return None  # closing under-weight with no room to extend
            groups.append(current)
            current = []
        current.append(size)
    if current:
        if sum(current) < lo and not allow_open_tail:
            return None
        groups.append(current)
    return groups


CHAPTER_HEADER_RE = re.compile(r"^#\s+Chapter\s+\d+:", re.MULTILINE)
CHAPTER_NUM_RE = re.compile(r"chapter-(\d+)")

# spec #71: simile closed set — substring counting on the non-dialogue domain.
SIMILE_MARKERS: tuple[str, ...] = ("像", "仿佛", "宛如", "宛若", "恰似", "如同", "似的")


def optional_read_hit(path_str: str, patterns: "list[str] | tuple[str, ...]") -> str | None:
    """Return the first OPTIONAL_READS-style pattern matching *path_str*.

    Patterns carry both bare names ("anchors.md") and slash forms
    ("style/anchors.md"); consumers pass either relative or absolute paths
    (glob expansion yields absolute). A basename-only fnmatch never hits
    slash forms, and a plain fnmatch never hits absolute paths against
    relative patterns — hence basename + full-string + suffix matching
    (audit-T4 M-1, spec #71).
    """
    from fnmatch import fnmatch

    basename = path_str.rsplit("/", 1)[-1]
    for pat in patterns:
        if fnmatch(basename, pat) or fnmatch(path_str, pat) or path_str.endswith("/" + pat):
            return pat
    return None


def bak_path(fp: str | Path) -> str:
    """Return the ``.bak`` sibling path for ``fp``.

    Single construction site for the truth-diff backup filename so the G1
    writer, the G2.11 reader, and the G4 style-polishing word-ratio reader
    all agree on the same root (``str(fp) + ".bak"``). Keeping this in one
    place prevents the three call sites from drifting apart.
    """
    return str(fp) + ".bak"


def jload(p: str | Path) -> dict[str, Any]:
    """Load a JSON file as a dict.

    All call sites in shenbi.gates treat the result as a dict (`.get`,
    indexing by str key). JSON files that aren't objects are treated as
    malformed and raise ValueError — failing loud beats silent AttributeError
    downstream.
    """
    data = json.loads(Path(p).read_text(encoding="utf-8"))
    if not isinstance(data, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise ValueError(f"{p}: expected JSON object, got {type(data).__name__}")
    return data


def resolve_input_path(fp: str | Path, rd: str | None = None) -> Path:
    """Resolve a caller-supplied file path (an entry of ``fps``) for G4 checkers.

    Absolute paths are returned unchanged. Relative paths are joined to the
    round_dir ``rd``; if ``rd`` is None a ``ValueError`` is raised rather than
    silently falling back to the current working directory. This replaces the
    ``base = Path(rd) if rd else Path.cwd()`` inline anti-pattern in the generic
    + inline checkers.
    """
    p = Path(fp)
    if p.is_absolute():
        return p
    if not rd:
        raise ValueError(
            f"round_dir required to resolve relative path {fp!r}; "
            "silent CWD fallback removed (Task 15b)"
        )
    return Path(rd) / fp


def yload(p: str | Path) -> dict[str, Any]:
    """Load YAML frontmatter or full YAML from a file as a dict."""
    if yaml is None:
        raise RuntimeError("PyYAML is not installed. Run: pip install pyyaml")
    with open(p, encoding="utf-8") as f:
        content = f.read()
    # Strip leading blank lines that may appear before YAML frontmatter
    # (worldbuilding skill outputs sometimes have \n before ---)
    cleaned = content.lstrip("\n\r\t ")
    if cleaned.startswith("---"):
        parts = cleaned.split("---", 3)
        data = yaml.safe_load(parts[1]) or {} if len(parts) > 1 else {}
    else:
        try:
            data = yaml.safe_load(cleaned) or {}
        except (yaml.YAMLError, TypeError, ValueError):
            data = {}
    if not isinstance(data, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise ValueError(f"{p}: expected YAML mapping, got {type(data).__name__}")
    return data


def chapter_word_floor(project_dir: str | Path | None) -> int:
    """Per-chapter hard floor = genre-config ``chapter_word.min`` (spec #72
    口径统一: the band's lower edge; ``default`` stays math-only for G0.3 /
    volume-budget / G6 chapter-count derivations). Fallback chain
    min → default → :data:`CHAPTER_WORD_FLOOR` — a config without ``min``
    keeps the pre-#72 default floor instead of dropping to the constant.
    """
    if not project_dir:
        return CHAPTER_WORD_FLOOR
    gc_path = Path(project_dir) / "genre-config.json"
    try:
        data = jload(str(gc_path))
    except (json.JSONDecodeError, OSError, ValueError):
        return CHAPTER_WORD_FLOOR
    cw = data.get("chapter_word", {})
    if not isinstance(cw, dict):
        return CHAPTER_WORD_FLOOR
    for key in ("min", "default"):
        value = cw.get(key)
        try:
            if value and int(value) > 0:
                return int(value)
        except (TypeError, ValueError):
            continue
    return CHAPTER_WORD_FLOOR


def chapter_word_min_max(project_dir: str | Path | None) -> tuple[int | None, int | None]:
    """Per-chapter (min, max) bounds from genre-config ``chapter_word``.

    Same single source as :func:`chapter_word_floor` (probe3 P1: the
    chapter-loop WARN bounds and the length-normalizing ceiling ran on their
    own hardcoded 4000/15000 and 3000/10000 regimes while the drafting gate
    already floored on the config). ``(None, None)`` when absent — callers
    keep their legacy constants so no-config behavior is unchanged.
    """
    if not project_dir:
        return (None, None)
    gc_path = Path(project_dir) / "genre-config.json"
    try:
        data = jload(str(gc_path))
    except (json.JSONDecodeError, OSError, ValueError):
        return (None, None)
    cw = data.get("chapter_word", {})
    if not isinstance(cw, dict):
        return (None, None)

    def _int_or_none(v: object) -> int | None:
        try:
            return int(v) if isinstance(v, (int, float, str)) and v else None
        except (TypeError, ValueError):
            return None

    return (_int_or_none(cw.get("min")), _int_or_none(cw.get("max")))


def word_count_md(fp: str | Path) -> int:
    """Count Chinese characters in Markdown body (excluding frontmatter,
    code blocks, and meta sections).
    """
    return word_count_md_text(Path(fp).read_text(encoding="utf-8"))


def strip_narrative_body(content: str) -> str:
    """Strip YAML frontmatter, code blocks, and non-narrative meta sections.

    Single construction site for the "chapter body" 口径 (probe escalation
    #4, 2026-09-28): ``word_count_md``, the G4 transition-word count, and the
    chapter word floor must all measure the SAME body — a transition count on
    raw content counted the framework-mandated PRE_WRITE_CHECK checklist
    itself (6 of 8 hits on the probe's chapter 1).
    """
    c = content
    # Strip YAML frontmatter
    c = re.sub(r"^---\n.*?\n---\n", "", c, flags=re.DOTALL)
    # Strip code blocks
    c = re.sub(r"```.*?```", "", c, flags=re.DOTALL)
    # Strip meta sections that are not narrative
    # Boundary: next H2, H1, HTML comment, or end of file
    _META_BOUNDARY = r"(?=## |# |<!--META|\Z)"
    for tag in [
        r"## PRE_WRITE_CHECK.*?" + _META_BOUNDARY,
        r"## POST_WRITE_SELF_CHECK.*?" + _META_BOUNDARY,
        r"## 润色说明.*?" + _META_BOUNDARY,
        r"## 改写报告.*?" + _META_BOUNDARY,
        r"## 归一化报告.*?" + _META_BOUNDARY,
    ]:
        c = re.sub(tag, "", c, flags=re.DOTALL)
    # Also strip HTML comment wrappers (<!--META-BEGIN-->...<!--META-END-->)
    c = META_BLOCK_RE.sub("", c)
    # Strip standalone SCENE marker lines (spec #72): durable in chapter files
    # for consumers that read boundaries, but never part of the narrative count.
    return strip_scene_markers(c)


QUOTE_PAIR = {"”": "“", "’": "‘", "」": "「", "』": "『"}
# 迁自 skill_utils/style_learning/compute_stats.py（spec #71 单信源化：
# G4.cd 与 compute_stats 同源切分；compute_stats re-export 保 API 兼容）。


def segment_sentences(text: str) -> list[tuple[str, int]]:
    r"""Segment Chinese text into sentences. Returns list of (sentence_text, char_count).

    F628: ； terminates sentences (unified with SENT_ENDS).
    F668: sentence-final punctuation inside open quotes does not split;
    \n splits unconditionally (escape hatch for unterminated quotes).
    """
    sentences: list[tuple[str, int]] = []
    current: list[str] = []
    quote_stack: list[str] = []
    ascii_quote_open = False

    def flush() -> None:
        sent = "".join(current).strip()
        if sent:
            char_count = len(sent.replace("\n", "").replace(" ", ""))
            if char_count > 0:
                sentences.append((sent, char_count))
        current.clear()

    for ch in text:
        current.append(ch)
        quote_closed = False
        if ch in QUOTE_PAIR.values():
            quote_stack.append(ch)
        elif ch in QUOTE_PAIR:
            if quote_stack and quote_stack[-1] == QUOTE_PAIR[ch]:
                quote_stack.pop()
                quote_closed = True
        elif ch == '"':
            if ascii_quote_open:
                quote_closed = True
            ascii_quote_open = not ascii_quote_open
        in_quote = bool(quote_stack) or ascii_quote_open
        if ch == "\n" or (ch in "。！？；" and not in_quote):
            if ch == "\n":
                # reset quote state so an unterminated quote on one line cannot
                # suppress splitting on later lines (Copilot review, PR #100)
                quote_stack.clear()
                ascii_quote_open = False
            flush()
        elif (
            quote_closed
            and not quote_stack
            and not ascii_quote_open
            and len(current) >= 2
            and current[-2] in "。！？；"
        ):
            # F668: sentence-final punct right before the OUTERMOST closing quote
            # ends the sentence (nested inner closes do not split the outer one)
            flush()
    if current:
        flush()
    return sentences


def _non_dialogue_text(content: str) -> str:
    """PRE/POST 裸 H2 节 + META 包裹剥除后，再剥引号内文字的正文（spec #71 §4.2）。"""
    body = strip_narrative_body(content)
    pieces: list[str] = []
    last = 0
    for start, end in find_quote_spans(body):
        pieces.append(body[last:start])
        last = end
    pieces.append(body[last:])
    return "".join(pieces)


def count_similes(content: str) -> dict[str, Any]:
    """比喻闭集子串计数于非对白域（spec #71 §4.2）。

    分子分母同域：计数与非对白字数都取自 _non_dialogue_text——
    含对白的 total_chars_md_text 分母会把 35-55% 对白占比的测值
    系统性下移约半，带界 [2,4] 与模板写作者语义错位。
    """
    nd = _non_dialogue_text(content)
    non_dialogue_chars = len(nd.replace("\n", "").replace(" ", ""))
    count = sum(nd.count(marker) for marker in SIMILE_MARKERS)
    per_1000 = round(count * 1000 / non_dialogue_chars, 1) if non_dialogue_chars else 0.0
    return {"count": count, "non_dialogue_chars": non_dialogue_chars, "per_1000": per_1000}


def word_count_md_text(content: str) -> int:
    """Content-based variant of :func:`word_count_md` (C28 R1: callers that
    already hold the chapter bytes — e.g. the shared audit context — must not
    re-read the file just to count).
    """
    return len(re.findall(r"[一-鿿]", strip_narrative_body(content)))


def total_chars_md_text(content: str) -> int:
    """Non-whitespace character count of the narrative body (all scripts and
    punctuation, meta stripped).

    The chapter word FLOOR runs on this 口径 (probe escalation #4): the memo
    layer plans chapter length in TOTAL characters (~3400), so a CJK-only
    floor of 3000 demanded ≈3565 total chars — plan-compliant chapters
    structurally could not pass (production fixture: ch36/37/39/41 all
    27xx-CJK fails while plan-compliant).
    """
    return len(re.sub(r"\s", "", strip_narrative_body(content)))


def parse_decisions_payload(
    content: str, file: str, prefix: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Single decisions-JSON parse policy shared by G2 and G4 (spec #30 T3/T6).

    Order: concatenated-multi-object detection first (strict loads would raise
    "Extra data" before the check could run), then strict ``json.loads``,
    then raw_decode first-object recovery with a warning. Recovery is a
    diagnostic path — the recovered object is returned for schema validation
    and can still FAIL; this helper never silently passes a file.

    Returns ``(data, failures)``: exactly one is non-empty/None-free. IDs use
    *prefix* (``G2.dec`` / ``G4.dec``) with the shared numeric suffixes
    ``.4`` (concatenation) and ``.1`` (invalid JSON / non-object).
    """
    if content.count('"$schema"') > 1:
        return None, [
            {
                "id": f"{prefix}.4",
                "file": file,
                "s": GateStatus.FAIL,
                "r": f"multiple JSON objects concatenated ({content.count(chr(34) + '$schema' + chr(34))} schemas found)",
            }
        ]
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        try:
            clean, end_pos = json.JSONDecoder().raw_decode(content)
        except json.JSONDecodeError:
            # Leading-prefix recovery (canary escalation #10): models wrap
            # pure-JSON sidecars with a markdown title/fence header —
            # `# Chapter 1:` then valid JSON. Re-decode from the first `{`.
            # Bounded: the recovered object still faces full schema + P2.5
            # validation by the caller, and the recovery is logged.
            brace = content.find("{")
            if brace > 0 and "\n" in content[:brace]:
                try:
                    clean, end_pos = json.JSONDecoder().raw_decode(content[brace:])
                except json.JSONDecodeError:
                    return None, [
                        {
                            "id": f"{prefix}.1",
                            "file": file,
                            "s": GateStatus.FAIL,
                            "r": "invalid JSON",
                        }
                    ]
                log.warning(
                    "decisions_json_leading_prefix_recovered",
                    file=file,
                    skipped_prefix=content[:brace][:80],
                )
                if not isinstance(clean, dict):
                    return None, [
                        {
                            "id": f"{prefix}.1",
                            "file": file,
                            "s": GateStatus.FAIL,
                            "r": f"recovered non-object JSON: {type(clean).__name__}",
                        }
                    ]
                return clean, []
            return None, [
                {"id": f"{prefix}.1", "file": file, "s": GateStatus.FAIL, "r": "invalid JSON"}
            ]
        if not isinstance(clean, dict):
            return None, [
                {
                    "id": f"{prefix}.1",
                    "file": file,
                    "s": GateStatus.FAIL,
                    "r": f"recovered non-object JSON: {type(clean).__name__}",
                }
            ]
        remaining = content[end_pos:].strip()
        if remaining:
            log.warning(
                "decisions_multi_json_truncated",
                file=file,
                original_len=len(content),
                recovered_len=end_pos,
                remaining_preview=remaining[:200],
            )
        else:
            log.info(
                "decisions_json_trailing_ws_recovered",
                file=file,
                original_len=len(content),
                cleaned_len=end_pos,
            )
        return clean, []
    if not isinstance(data, dict):
        return None, [
            {
                "id": f"{prefix}.1",
                "file": file,
                "s": GateStatus.FAIL,
                "r": f"expected JSON object, got {type(data).__name__}",
            }
        ]
    return data, []


def fail(
    gid: str,
    checks: list[dict[str, Any]],
    blocked: str,
    must_fix: list[str],
    extra: dict[str, Any] | None = None,
) -> str:
    """Return FAIL JSON string."""
    result: GateResult = {
        "gate": gid,
        "status": GateStatus.FAIL,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
        "blocked_action": blocked,
        "must_fix": must_fix,
    }
    merged = dict(result)
    if extra:
        merged.update(extra)
    return json.dumps(merged, indent=2, ensure_ascii=False)


def clip_with_disclosure(text: str, limit: int) -> tuple[str, bool]:
    """Clip ``text`` to ``limit`` chars, disclosing that a sample was read.

    C29 R2 (F459): every gate-side text-prefix clip goes through this helper
    so checks can attach ``input_sampled`` to their result dicts. Pure.
    """
    if len(text) <= limit:
        return text, False
    return text[:limit], True


def sampled_checks_summary(checks: list[dict[str, Any]]) -> str | None:
    """Aggregate ``input_sampled`` flags into a top-level disclosure line.

    Returns e.g. ``"2/7 checks ran on sampled input"`` or None when no check
    sampled. C29 R2: consumed by gate_G5/gate_G6 result assembly (persisted via
    write_gate_marker and surfaced by G7.13 re-runs).
    """
    executed = [chk for chk in checks if chk.get("s") is not GateStatus.SKIP]
    sampled = sum(1 for chk in executed if chk.get("input_sampled"))
    if not sampled:
        return None
    return f"{sampled}/{len(executed)} checks ran on sampled input"


def passed(gid: str, checks: list[dict[str, Any]], extra: dict[str, Any] | None = None) -> str:
    """Return PASS JSON string."""
    result: GateResult = {
        "gate": gid,
        "status": GateStatus.PASS,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }
    merged = dict(result)
    if extra:
        merged.update(extra)
    return json.dumps(merged, indent=2, ensure_ascii=False)


def parse_report_stem(stem: str, known_skills: "tuple[str, ...] | list[str]") -> str | None:
    """Parse a t1-reports filename stem into its skill name (single parser).

    Strips the production ``-scores`` / ``-scores-subagent`` (and the
    dual-scorer ``-scores-subagent-2``, spec #31 T2b) suffixes
    (dispatcher/modes/codex.py) and matches the longest known skill prefix.
    Returns None for stems matching no known skill (hallucination signal).
    """
    for suffix in ("-scores-subagent-2", "-scores-subagent", "-scores"):
        stem = stem.removesuffix(suffix)
    for skill in sorted(known_skills, key=len, reverse=True):
        if stem == skill or stem.startswith(skill + "-"):
            return skill
    return None


def find_report(
    reports_dir: str | Path, skill_name: str, test_type: str | None = None
) -> Path | None:
    """Find a report file with flexible naming convention.

    Tries: <skill>-<test_type>-scores-subagent.json (F464), then
    <skill>-<test_type>-scores.json, <skill>-<test_type>.json, <skill>.json.
    """
    rd = Path(reports_dir)
    if test_type:
        # F401/F464: production naming appends -subagent (independent subagent
        # scoring, dispatcher/modes/codex.py) — accept it alongside -scores.
        for suffix in ("-scores-subagent", "-scores", ""):
            path = rd / f"{skill_name}-{test_type}{suffix}.json"
            if path.exists():
                return path
    path = rd / f"{skill_name}.json"
    if path.exists():
        return path
    return None


def normalize_file_paths(
    file_paths: str | list[str] | tuple[str, ...] | None,
) -> list[str]:
    """Accept list or comma-separated string, return list of Path strings."""
    if file_paths is None:
        return []
    if isinstance(file_paths, str):
        return [p.strip() for p in file_paths.split(",") if p.strip()]
    # list or tuple — exhaustive after str and None checks above
    return [str(p) for p in file_paths]


def marker_filename(gate: str, target: str, test_type: str) -> str:
    """Single source for gate-marker filenames (spec #27 T2).

    Both the writer (write_gate_marker) and the reader
    (scoring.check_gate_markers) must derive the name from here.
    """
    return f"{gate}-{target}-{test_type}.json"


def write_gate_marker(
    gate: str,
    target: str,
    test_type: str,
    result_str: str,
    round_dir: str | None,
    file_paths: list[str] | None = None,
) -> None:
    """Write a gate marker file if result is PASS and round_dir is provided."""
    if not round_dir:
        return
    try:
        result = json.loads(result_str)
        if result.get("status") != "PASS":
            return
        rd = Path(round_dir)
        marker_dir = rd / "gate-markers"
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker = {
            **result,
            "files_checked": [str(p) for p in (file_paths or [])],
        }
        marker_file = marker_dir / marker_filename(gate, target, test_type)
        safe_write(marker_file, json.dumps(marker, indent=2, ensure_ascii=False))
    except (json.JSONDecodeError, OSError):
        pass  # best-effort marker write; non-PASS or unreadable result → skip marker


def unimplemented(gate_name: str, note: str = "") -> str:
    """Return UNIMPLEMENTED JSON string for stub gates."""
    return json.dumps(
        {
            "gate": gate_name,
            "status": GateStatus.UNIMPLEMENTED,
            "note": note or f"{gate_name} not yet implemented — stub",
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": [],
        },
        indent=2,
        ensure_ascii=False,
    )


def read_genre_config(project_dir: str | Path) -> dict[str, Any]:
    """Read genre-config.json from a project directory to get
    fatigue_words, chapter_word, etc.
    """
    gc_path = Path(project_dir) / "genre-config.json"
    if gc_path.exists():
        try:
            data: dict[str, Any] = jload(str(gc_path))
            return data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


# Pre-compute the known skill names from the skills/ directory
ALL_SKILLS = (
    sorted(d.name for d in SKILLS.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    if SKILLS.exists()
    else []
)

# F432: the t1-skill scaffold roster (tests/tiers/t1-skill/<skill>/) is the
# coverage universe for G7.1b reverse coverage — skills without a T1 scaffold
# (group-*/lifecycle) can never appear in a round summary and must not FAIL it.
T1_SCAFFOLD_SKILLS: tuple[str, ...] = tuple(
    sorted(
        d.name
        for d in (TESTS / "tiers" / "t1-skill").iterdir()
        if d.is_dir() and d.name != "_template"
    )
    if (TESTS / "tiers" / "t1-skill").exists()
    else []
)

# Skills that have dedicated (non-generic) G4 generative checkers
G4_CHECKER_SKILLS = {
    "shenbi-anti-detect",
    "shenbi-book-spine-init",
    "shenbi-chapter-drafting",
    "shenbi-chapter-planning",
    "shenbi-chapter-revision",
    "shenbi-character-design",
    "shenbi-context-composing",
    "shenbi-escalation-review",
    "shenbi-faction-builder",
    "shenbi-foreshadowing-lifecycle",
    "shenbi-genre-config",
    "shenbi-length-normalizing",
    "shenbi-location-builder",
    "shenbi-market-radar",
    "shenbi-memory-distill",
    "shenbi-pacing-design",
    "shenbi-plot-thread-weaver",
    "shenbi-power-system",
    "shenbi-relationship-map",
    "shenbi-review-arc-payoff",
    "shenbi-review-resonance",
    "shenbi-score-arc",
    "shenbi-score-stratum",
    "shenbi-score-volume",
    "shenbi-short-drafting",
    "shenbi-state-settling",
    "shenbi-story-architecture",
    "shenbi-style-polishing",
    "shenbi-volume-outlining",
    "shenbi-worldbuilding",
}

# Default lists (used when genre-config.json doesn't provide them)
FATIGUE_BASE = [
    "突然",
    "猛地",
    "瞬间",
    "一股",
    "恐怖",
    "死死",
    "眼中闪过",
    "嘴角",
    "冷冷",
    "淡淡",
    "微微一笑",
    "心中一动",
    "暗道",
    "不由得",
    "显然",
    "似乎",
    "仿佛",
    "如同",
    "无比",
    "极致",
    "难以形容",
    "不可思议",
    "前所未有",
    "令人发指",
    "震惊",
    "愣住",
    "呆住",
]
META_NARRATIVE = [
    "让人感悟",
    "引人深思",
    "由此可见",
    "综上所述",
    "值得注意的是",
    "不禁感慨",
    "不由得想到",
]
TRANSITION_SPECIFIC = ["不过", "此时", "突然", "终于", "于是"]


def count_transition_words(content: str) -> int:
    """Count transition word occurrences.  '然' is handled specially to
    avoid double-counting with compounds like 然而/虽然/当然/自然/忽然
    and to avoid double-counting with 突然 (which IS a transition word).
    """
    tc = content.count("然")
    # Subtract compounds where 然 is NOT a standalone transition word
    tc -= content.count("虽然")
    tc -= content.count("然而")
    tc -= content.count("当然")
    tc -= content.count("自然")
    tc -= content.count("忽然")
    # Subtract 突然 to avoid double-counting (it will be added back below)
    tc -= content.count("突然")
    # Add specific multi-char transition words
    for w in TRANSITION_SPECIFIC:
        tc += content.count(w)
    # spec #83 T1 前置：补语潜在形（V+不过+来/去）非转折用法——ch17:79「算不过来的账」
    # 实弹误计 1 次；不修则 cd.post_transition_cross 反向误伤无过错正文
    tc -= content.count("不过来")
    tc -= content.count("不过去")
    return max(tc, 0)


def load_chapter_exemptions() -> dict[str, set[int]]:
    """Read-only load of z11 chapter META exemptions (SDD #20 R1b, F1302).

    Returns {project: {chapter}}; a missing or malformed file yields {} so the
    G2.13 check fails closed on real violations instead of crashing.
    """
    path = PROJECT / "docs" / "framework" / "z11-chapter-exemptions.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, set[int]] = {}
    for e in data.get("exemptions", []):
        try:
            out.setdefault(str(e.get("project", "")), set()).add(int(e.get("chapter", -1)))
        except (TypeError, ValueError):
            continue
    return out


# Spec #80 T4: shared transfer-verb vocabulary — single table consumed by
# BOTH the F16 G4.cd co-occurrence scan AND the #75 XC invariant-4 fallback
# (plan R2-I5: two hand-maintained lists drift; the wound forms 抽出/揣着
# were invisible to the old closed set).
TRANSFER_VERBS: frozenset[str] = frozenset(
    {
        "递给",
        "塞给",
        "交给",
        "送给",
        "还给",
        "还了",
        "给了",
        "留给",
        "转手",
        "递了",
        "送了",
        "交到",
        "递到",
        "递还",
        "抽出",
        "揣着",
        "揣进",
        "取出",
    }
)
