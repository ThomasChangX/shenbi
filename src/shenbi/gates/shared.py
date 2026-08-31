"""Shared helpers for gate validation.

Gate validation logic (originally extracted from tests/validate-gate.py in PR-19). All gate modules
import these helpers to keep behavior identical to the legacy monolith.
"""

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write
from shenbi.status import GateResult, GateStatus

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
CHAPTER_HEADER_RE = re.compile(r"^#\s+Chapter\s+\d+:", re.MULTILINE)
CHAPTER_NUM_RE = re.compile(r"chapter-(\d+)")


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


def word_count_md(fp: str | Path) -> int:
    """Count Chinese characters in Markdown body (excluding frontmatter,
    code blocks, and meta sections).
    """
    c = Path(fp).read_text(encoding="utf-8")
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
    return len(re.findall(r"[一-鿿]", c))


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


def fail(gid: str, checks: list[dict[str, Any]], blocked: str, must_fix: list[str]) -> str:
    """Return FAIL JSON string."""
    result: GateResult = {
        "gate": gid,
        "status": GateStatus.FAIL,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
        "blocked_action": blocked,
        "must_fix": must_fix,
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


def passed(gid: str, checks: list[dict[str, Any]]) -> str:
    """Return PASS JSON string."""
    result: GateResult = {
        "gate": gid,
        "status": GateStatus.PASS,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


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
    "shenbi-chapter-drafting",
    "shenbi-chapter-planning",
    "shenbi-character-design",
    "shenbi-context-composing",
    "shenbi-faction-builder",
    "shenbi-foreshadowing-plant",
    "shenbi-foreshadowing-track",
    "shenbi-genre-config",
    "shenbi-length-normalizing",
    "shenbi-location-builder",
    "shenbi-pacing-design",
    "shenbi-plot-thread-weaver",
    "shenbi-power-system",
    "shenbi-relationship-map",
    "shenbi-review-arc-payoff",
    "shenbi-review-resonance",
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
