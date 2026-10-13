"""Parse seed files (format: outline-example.md) into structured project data.

Spec: docs/superpowers/specs/archive/2026-07-01-novel-pipeline-design.md Section 4.

The seed is a bilingual (EN/ZH) Markdown outline. Section headings map to
output targets per spec 4.1:

  Basic Info      / 基本信息    -> novel.json fields (genre, era, ...)
  Protagonist     / 主角设定    -> genesis context
  World Rules     / 世界观设定  -> genesis context
  Forces          / 势力/组织   -> genesis context
  Core Conflict   / 核心冲突    -> genesis context (3 layers)
  Plot Lines      / 情节线      -> genesis context
  Chapter Outline / 章节大纲    -> genesis context
  Three-Act       / 三幕结构    -> genesis context
  Narrative       / 叙事技巧    -> genre-config

total_chapters is intentionally NOT set here -- volume-outlining (genesis
step 6) computes it (spec 4.2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)


@dataclass
class SeedData:
    """Parsed seed file data.

    novel_json      -- fields written to novel.json
    genre_config    -- fields written to genre-config.json
    genesis_context -- raw section text keyed for skill dispatch prompts
    """

    novel_json: dict[str, object] = field(default_factory=dict)
    genre_config: dict[str, object] = field(default_factory=dict)
    genesis_context: dict[str, str] = field(default_factory=dict)


def _extract_section(text: str, section_name: str) -> str:
    """Extract body under a heading until the next heading of same/higher level.

    section_name is a pipe-separated list of accepted heading texts
    (e.g. "Basic Info|基本信息"); each alternative is escaped individually
    so the pipe acts as a regex alternation.

    Subsections (a deeper heading level than the match) are kept inside the
    returned text -- only a heading of the same or shallower level ends it.
    """
    alternatives = "|".join(re.escape(a) for a in section_name.split("|"))
    # Capture the heading depth so ### subsections stay inside a ## section.
    pattern = rf"^(#{{1,3}})\s+(?:{alternatives})\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return ""
    level = len(match.group(1))
    start = match.end()
    for heading in re.finditer(r"^(#{1,3})\s", text[start:], re.MULTILINE):
        if len(heading.group(1)) <= level:
            return text[start : start + heading.start()].strip()
    return text[start:].strip()


def _parse_list_items(section_text: str) -> list[str]:
    """Parse markdown list items (lines starting with - or *)."""
    items: list[str] = []
    for line in section_text.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            items.append(line[2:].strip())
    return items


def _split_key_value(item: str) -> tuple[str, str] | None:
    """Split a key-value list item into (key, value).

    Handles both ASCII and fullwidth-Chinese colon separators, partitioning
    on whichever appears earliest so a colon embedded in a value does not
    hijack the split (see test_chinese_key_value_with_ascii_colon_in_value).
    Returns None when no colon is present.
    """
    pos = min(
        (item.find(sep) for sep in (":", "：") if sep in item),
        default=-1,
    )
    if pos == -1:
        return None
    return item[:pos].strip(), item[pos + 1 :].strip()


#: Sections every structurally-valid seed must carry (non-empty), with the
#: bilingual heading alternatives from the section map above. Missing or
#: empty sections produce empty genesis context — the run then silently
#: degrades instead of failing (the AI-tool-edited-outline risk this guards).
REQUIRED_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Basic Info", "Basic Info|基本信息"),
    ("Protagonist", "Protagonist|主角设定|主角"),
    ("World Rules", "World Rules|世界观设定|世界规则|World Setting"),
    ("Forces", "Forces|势力/组织|势力|组织|Factions"),
    ("Core Conflict", "Core Conflict|核心冲突"),
    ("Plot Lines", "Plot Lines|情节线"),
    ("Chapter Outline", "Chapter Outline|章节大纲"),
    ("Three-Act Structure", "Three-Act Structure|三幕结构"),
    ("Narrative Techniques", "Narrative Techniques|叙事技巧"),
)


def validate_seed(seed_path: Path | str) -> list[str]:
    """Structural validation for seed files. Returns ALL problems found.

    Guards against AI-tool edits that silently restructure the outline:
    every required section present and non-empty, an H1 title, and at
    least one parseable ``- key: value`` item under Basic Info. An empty
    return means structurally sound (semantic quality is out of scope).
    """
    seed_path = Path(seed_path)
    if not seed_path.exists():
        return [f"seed file not found: {seed_path}"]
    text = seed_path.read_text(encoding="utf-8")

    errors: list[str] = []
    if not re.search(r"^#\s+\S", text, re.MULTILINE):
        errors.append("缺少一级标题（# 书名）——novel.json title 的唯一来源")

    for label, alternatives in REQUIRED_SECTIONS:
        body = _extract_section(text, alternatives)
        if not body.strip():
            errors.append(f"必需节缺失或为空：{label}（可接受标题：{alternatives}）")

    basic = _extract_section(text, "Basic Info|基本信息")
    if basic.strip() and not any(
        _split_key_value(item) is not None for item in _parse_list_items(basic)
    ):
        errors.append("Basic Info 无任何可解析的 `- key: value` 列表项")

    conflict = _extract_section(text, "Core Conflict|核心冲突")
    if conflict.strip():
        keys = [(_split_key_value(i) or ("", ""))[0] for i in _parse_list_items(conflict)]
        if not any("surface" in k.lower() or "表层" in k for k in keys):
            errors.append("Core Conflict 缺表层冲突（surface_conflict/表层）")
        if not any("personal" in k.lower() or "个人" in k for k in keys):
            errors.append("Core Conflict 缺个人冲突（personal_conflict/个人）")
        if not any("deep" in k.lower() or "深层" in k for k in keys):
            errors.append("Core Conflict 缺深层冲突（deep_conflict/深层）")

    return errors


def parse_seed(seed_path: Path | str) -> SeedData:
    """Parse a seed file into SeedData. Raises FileNotFoundError if missing."""
    seed_path = Path(seed_path)
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_path}")

    text = seed_path.read_text(encoding="utf-8")

    # -- Basic Info -> novel.json -------------------------------------------
    basic = _extract_section(text, "Basic Info|基本信息")
    novel_json: dict[str, object] = {}
    dropped_basic: list[str] = []

    # -- H1 -> novel.json title ---------------------------------------------
    # probe10/11: init never wrote a title, so G4.novel.missing_title only
    # ever passed via worldbuilding's (guarded-away) LLM overwrite of the
    # framework file — with a model-invented title. The work title is the
    # seed's first H1, main segment before a subtitle colon.
    h1 = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if h1:
        novel_json["title"] = re.split(r"[：:]", h1.group(1), maxsplit=1)[0].strip()

    for item in _parse_list_items(basic):
        kv = _split_key_value(item)
        if kv is None:
            continue
        key, value = kv
        key_norm = key.lower().replace(" ", "_")

        if key_norm in ("genre", "类型", "题材"):
            novel_json["genre"] = [g.strip() for g in re.split(r"[,，]", value)]
        elif key_norm in ("era", "时代背景", "时代"):
            novel_json["era"] = value
        elif key_norm in ("core_concept", "核心概念"):
            novel_json["core_concept"] = value
        elif key_norm in (
            "target_total_chapters",
            "目标章节数",
            "目标总章数",
            "总章数",
        ):
            # T3: authoritative chapter-count override. When present,
            # volume-outlining uses this instead of deriving
            # ceil(target_word_count / chapter_word.default).
            nums = re.findall(r"\d+", value)
            if nums:
                novel_json["target_total_chapters"] = int(nums[0])
        elif key_norm in ("target_word_count", "目标字数"):
            nums = re.findall(r"\d+", value)
            if nums:
                novel_json["target_word_count"] = int(nums[0])
        elif key_norm in ("ending_direction", "故事结局方向", "结局"):
            novel_json["ending_direction"] = value
        else:
            dropped_basic.append(key)
    if dropped_basic:
        # spec #69 T3: surface silently-dropped seed keys once per section.
        log.warning("seed_key_dropped", section="Basic Info|基本信息", keys=dropped_basic)

    # total_chapters (volume_map frontmatter) is NOT set here -- volume-outlining
    # (genesis step 6) computes it. See spec section 4.2. The optional
    # ``target_total_chapters`` parsed above is an authoritative override for
    # that derivation, not the volume_map field itself.
    novel_json["golden_opening_chapters"] = 3
    novel_json["language"] = "zh"

    # -- Narrative Techniques -> genre-config -------------------------------
    narrative = _extract_section(text, "Narrative Techniques|叙事技巧")
    genre_config: dict[str, object] = {}
    dropped_narrative: list[str] = []
    for item in _parse_list_items(narrative):
        kv = _split_key_value(item)
        if kv is None:
            continue
        key, value = kv
        key_norm = key.lower().replace(" ", "_").replace("/", "_")

        if ("show" in key_norm and "tell" in key_norm) or ("展示" in key and "讲述" in key):
            genre_config["show_tell_ratio"] = value
        elif "theme" in key_norm or "主题" in key:
            genre_config["deep_themes"] = value
        else:
            dropped_narrative.append(key)
    if dropped_narrative:
        # spec #69 T3: surface silently-dropped seed keys once per section.
        log.warning(
            "seed_key_dropped", section="Narrative Techniques|叙事技巧", keys=dropped_narrative
        )

    # -- Section raw text -> genesis context --------------------------------
    genesis_context: dict[str, str] = {
        "protagonist": _extract_section(text, "Protagonist|主角设定|主角"),
        "supporting": _extract_section(text, "Supporting Cast|配角设定|配角"),
        "world_rules": _extract_section(text, "World Rules|世界观设定|世界规则|World Setting"),
        "forces": _extract_section(text, "Forces|势力/组织|势力|组织|Factions"),
        "surface_conflict": "",
        "personal_conflict": "",
        "deep_conflict": "",
        "plot_lines": _extract_section(text, "Plot Lines|情节线"),
        "chapter_outline": _extract_section(text, "Chapter Outline|章节大纲"),
        "three_act": _extract_section(text, "Three-Act Structure|三幕结构"),
    }

    # -- Core Conflict: three layers ----------------------------------------
    conflict = _extract_section(text, "Core Conflict|核心冲突")
    for item in _parse_list_items(conflict):
        kv = _split_key_value(item)
        if kv is None:
            continue
        key, value = kv
        if "surface" in key.lower() or "表层" in key:
            genesis_context["surface_conflict"] = value
        elif "personal" in key.lower() or "个人" in key:
            genesis_context["personal_conflict"] = value
        elif "deep" in key.lower() or "深层" in key:
            genesis_context["deep_conflict"] = value

    log.debug(
        "seed_parsed",
        seed_path=str(seed_path),
        genre=novel_json.get("genre"),
        context_keys=list(genesis_context),
    )
    return SeedData(
        novel_json=novel_json,
        genre_config=genre_config,
        genesis_context=genesis_context,
    )
