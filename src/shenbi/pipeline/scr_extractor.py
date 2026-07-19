"""Deterministic Structured Chapter Representation (SCR) extraction.

Extracts structured facts from chapter prose once per chapter.
Cached to disk at context/chapter-N-scr.json.
All downstream LLM calls consume SCR fields instead of raw chapter text.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shenbi.safe_write import safe_write


@dataclass
class StructuredChapterRepresentation:
    chapter: int
    extracted_at: str

    # Facts-Only fields (deterministic, high precision)
    character_locations: list[dict[str, Any]] = field(default_factory=list)
    dialogue_segments: list[dict[str, Any]] = field(default_factory=list)
    event_timeline: list[dict[str, Any]] = field(default_factory=list)
    emotional_markers: list[dict[str, Any]] = field(default_factory=list)
    hook_appearances: list[dict[str, Any]] = field(default_factory=list)
    world_refs: list[dict[str, Any]] = field(default_factory=list)
    pov_shifts: list[dict[str, Any]] = field(default_factory=list)
    decision_points: list[dict[str, Any]] = field(default_factory=list)
    paragraph_stats: dict[str, Any] = field(default_factory=dict)
    sensitive_hits: list[dict[str, Any]] = field(default_factory=list)
    fatigue_word_hits: list[dict[str, Any]] = field(default_factory=list)
    transition_markers: list[dict[str, Any]] = field(default_factory=list)

    # Smart-Excerpting fields (original text preserved)
    opening_paragraph: str = ""
    closing_paragraph: str = ""
    implicit_info_passages: list[str] = field(default_factory=list)

    # Metadata
    total_chinese_chars: int = 0
    extraction_confidence: float = 0.0


# --- META stripping ---
_META_RE = re.compile(r"<!--META-BEGIN-->.*?<!--META-END-->", re.DOTALL)


def extract_prose(text: str) -> str:
    """Strip META blocks and title line from chapter text."""
    text = _META_RE.sub("", text)
    # Remove H1 title line
    text = re.sub(r"^#\s+.+?\n", "", text, count=1)
    return text.strip()


# --- Character name extraction ---
_SPEAKER_RE = re.compile(r"(.+?)(?:说|道|问|答|喊|叫|低语|轻声|沉声|冷冷|缓缓|慢慢)")


def _extract_character_locations(prose: str) -> list[dict[str, Any]]:
    """Extract character appearances from dialogue attributions and narration."""
    results = []
    seen = set()
    _BAD_END = set("的了吗呢啊吧呀着在以和与或之地得就到从被把对向自而则且但所者也为及")

    # Pattern 1: dialogue with speech-verb attribution (e.g., "..."王铁说)
    for match in re.finditer(r'["""](.+?)["»"]\s*(.+?)(?:说|道|问|答)', prose):
        speaker_text = match.group(2).strip()
        speaker_match = re.search(r"[\u4e00-\u9fff]{2,3}", speaker_text)
        if speaker_match:
            name = speaker_match.group()
            if name[-1] in _BAD_END:
                name = name[:-1]
            if len(name) >= 2 and name not in seen:
                seen.add(name)
                pos = match.start()
                line_num = prose[:pos].count("\n") + 1
                results.append(
                    {
                        "name": name,
                        "location": "dialogue_attribution",
                        "evidence": match.group(0)[:50],
                        "line_range": [line_num, line_num + 1],
                    }
                )

    # Pattern 2: dialogue immediately followed by a name (e.g., "..."王铁的声音)
    for match in re.finditer(r'["""](.+?)["»"]\s*([\u4e00-\u9fff]{2,3})', prose):
        name = match.group(2)
        if name[-1] in _BAD_END:
            name = name[:-1]
        if len(name) >= 2 and name not in seen:
            seen.add(name)
            pos = match.start()
            line_num = prose[:pos].count("\n") + 1
            results.append(
                {
                    "name": name,
                    "location": "dialogue_attribution",
                    "evidence": match.group(0)[:50],
                    "line_range": [line_num, line_num + 1],
                }
            )

    # Pattern 3: find character names in narration (sentence/paragraph starts)
    for match in re.finditer(r"(?:^|\n|。|！|？)\s*([\u4e00-\u9fff]{2,3})", prose, re.MULTILINE):
        name = match.group(1)
        if name[-1] in _BAD_END:
            name = name[:-1]
        if len(name) >= 2 and name not in seen:
            seen.add(name)
            pos = match.start()
            line_num = prose[:pos].count("\n") + 1
            results.append(
                {
                    "name": name,
                    "location": "narration",
                    "evidence": prose[max(0, pos - 5) : pos + len(name) + 10],
                    "line_range": [line_num, line_num + 1],
                }
            )

    return results


def _extract_dialogue_segments(prose: str) -> list[dict[str, Any]]:
    """Extract dialogue segments with speaker attribution."""
    results = []
    for match in re.finditer(r'(?:["""])(.+?)(?:["»"])', prose):
        text = match.group(1)
        pos = match.start()
        line_num = prose[:pos].count("\n") + 1

        # Try to find speaker from preceding context
        before = prose[max(0, pos - 30) : pos]
        speaker_match = _SPEAKER_RE.search(before)
        if speaker_match:
            speaker = speaker_match.group(1).strip()[-3:]
        else:
            # Check after dialogue for a name (e.g., "..."王铁的声音)
            after_start = match.end()
            after = prose[after_start : after_start + 20]
            name_match = re.search(r"([\u4e00-\u9fff]{2})", after)
            speaker = name_match.group(1) if name_match else "unknown"

        results.append(
            {
                "speaker": speaker,
                "text": text[:100],
                "line_range": [line_num, line_num + 1],
                "tags": [],
            }
        )

    return results


def _extract_event_timeline(prose: str) -> list[dict[str, Any]]:
    """Extract event-like sentences from narrative text."""
    results = []
    # Split into sentences roughly
    sentences = re.split(r"[。！？\n]", prose)
    line_num = 1
    for _i, sent in enumerate(sentences):
        sent = sent.strip()
        if not sent or len(sent) < 4:
            continue
        # Heuristic: events often contain specific verbs
        if re.search(r"(走|来|去|到|拿|放|看|听|说|做|打|杀|买|卖|数|算)", sent):
            results.append(
                {
                    "description": sent[:80],
                    "line_range": [line_num, line_num + 1],
                    "characters_involved": [],
                }
            )
    return results


def _extract_emotional_markers(prose: str) -> list[dict[str, Any]]:
    """Extract emotional state indicators."""
    emotion_words = [
        "怒",
        "悲",
        "喜",
        "惧",
        "忧",
        "惊",
        "静",
        "冷",
        "热",
        "颤",
        "抖",
        "微笑",
        "哭泣",
    ]
    results = []
    for word in emotion_words:
        for match in re.finditer(re.escape(word), prose):
            pos = match.start()
            # line_num used only for evidence context
            line_num = prose[:pos].count("\n") + 1
            ctx_start = max(0, pos - 10)
            ctx_end = min(len(prose), pos + 10)
            results.append(
                {
                    "character": "unknown",
                    "emotion": word,
                    "evidence": prose[ctx_start:ctx_end],
                    "confidence": 0.7,
                    "line_range": [line_num, line_num + 1],
                }
            )
    return results


def _extract_hook_appearances(prose: str) -> list[dict[str, Any]]:
    """Extract hook ID references from prose."""
    results = []
    for match in re.finditer(r"([A-Z]{2,4}-\d+)", prose):
        hook_id = match.group(1)
        pos = match.start()
        line_num = prose[:pos].count("\n") + 1
        ctx_start = max(0, pos - 30)
        ctx_end = min(len(prose), pos + 30)
        results.append(
            {
                "hook_id": hook_id,
                "line_range": [line_num, line_num + 1],
                "context": prose[ctx_start:ctx_end],
            }
        )
    return results


def _extract_world_references(prose: str) -> list[dict[str, Any]]:
    """Extract references to world elements (locations, items, systems)."""
    results = []
    # Common world element indicators
    patterns = [
        (r"(灵石|丹药|法器|阵法|功法)", "cultivation"),
        (r"(铜币|银币|金币|灵石)", "currency"),
        (r"(山|河|城|镇|村|谷|林|海|原)", "location"),
    ]
    for pat, category in patterns:
        for match in re.finditer(pat, prose):
            pos = match.start()
            line_num = prose[:pos].count("\n") + 1
            results.append(
                {
                    "element": match.group(1),
                    "category": category,
                    "line_range": [line_num, line_num + 1],
                }
            )
    return results


def _extract_pov_shifts(prose: str) -> list[dict[str, Any]]:
    """Detect point-of-view transitions using name pattern changes."""
    results = []
    # Simplified: detect when a new character name dominates a paragraph
    paragraphs = prose.split("\n\n")
    prev_dominant = None
    for i, para in enumerate(paragraphs):
        names = re.findall(r"[\u4e00-\u9fff]{2,3}", para)
        if not names:
            continue
        # Most frequent name in paragraph
        dominant = Counter(names).most_common(1)[0][0]
        if prev_dominant and dominant != prev_dominant:
            results.append(
                {
                    "from_pov": prev_dominant,
                    "to_pov": dominant,
                    "line_range": [i * 2, (i + 1) * 2],
                }
            )
        prev_dominant = dominant
    return results


def _extract_decision_points(prose: str) -> list[dict[str, Any]]:
    """Extract character decision moments."""
    results = []
    decision_indicators = ["决定", "选择", "下定", "毅然", "最终"]
    for indicator in decision_indicators:
        for match in re.finditer(re.escape(indicator), prose):
            pos = match.start()
            line_num = prose[:pos].count("\n") + 1
            results.append(
                {
                    "character": "unknown",
                    "decision": indicator,
                    "cause_chain": "",
                    "effect": "",
                    "line_range": [line_num, line_num + 1],
                }
            )
    return results


def _compute_paragraph_stats(prose: str) -> dict[str, Any]:
    """Compute paragraph-level statistics."""
    paragraphs = [p.strip() for p in prose.split("\n\n") if p.strip()]
    lengths = [len(p) for p in paragraphs]
    dialogue_count = sum(1 for p in paragraphs if '"' in p or '"' in p or '"' in p)

    return {
        "count": len(paragraphs),
        "lengths": lengths,
        "dialogue_density": dialogue_count / max(len(paragraphs), 1),
        "avg_length": sum(lengths) / max(len(lengths), 1),
    }


_SENSITIVE_WORDS = ["死", "杀", "血", "尸", "鬼", "魔", "妖", "毒", "咒"]


def _scan_sensitive_words(prose: str) -> list[dict[str, Any]]:
    """Scan for sensitive content words."""
    results = []
    for word in _SENSITIVE_WORDS:
        for match in re.finditer(re.escape(word), prose):
            pos = match.start()
            line_num = prose[:pos].count("\n") + 1
            ctx_start = max(0, pos - 15)
            ctx_end = min(len(prose), pos + 15)
            results.append(
                {
                    "word": word,
                    "line_range": [line_num, line_num + 1],
                    "surrounding_context": prose[ctx_start:ctx_end],
                }
            )
    return results


_FATIGUE_WORDS = ["骤然", "仿佛", "只见", "突然", "缓缓", "微微", "深深", "轻轻", "慢慢"]


def _scan_fatigue_words(prose: str) -> list[dict[str, Any]]:
    """Scan for AI fatigue indicator words."""
    results = []
    counts: dict[str, int] = {}
    for word in _FATIGUE_WORDS:
        for _match in re.finditer(re.escape(word), prose):
            counts[word] = counts.get(word, 0) + 1
    for word, count in counts.items():
        if count > 0:
            results.append(
                {
                    "word": word,
                    "count": count,
                    "line_ranges": [],
                }
            )
    return results


_TRANSITION_WORDS = ["接着", "然后", "之后", "随后", "此后", "不久", "过了"]


def _scan_transition_markers(prose: str) -> list[dict[str, Any]]:
    """Scan for temporal transition markers."""
    results = []
    for word in _TRANSITION_WORDS:
        for match in re.finditer(re.escape(word), prose):
            pos = match.start()
            line_num = prose[:pos].count("\n") + 1
            results.append(
                {
                    "marker": word,
                    "line_range": [line_num, line_num + 1],
                }
            )
    return results


def _extract_opening(prose: str) -> str:
    """Extract opening paragraph of chapter body."""
    paragraphs = [p.strip() for p in prose.split("\n\n") if p.strip()]
    return paragraphs[0] if paragraphs else ""


def _extract_closing(prose: str) -> str:
    """Extract closing paragraph of chapter body."""
    paragraphs = [p.strip() for p in prose.split("\n\n") if p.strip()]
    return paragraphs[-1] if paragraphs else ""


def _extract_implicit_passages(prose: str) -> list[str]:
    """Extract passages containing emotional/relational implicit content."""
    results = []
    indicators = ["感到", "觉得", "想起", "记得", "似乎", "好像", "也许", "或许"]
    paragraphs = prose.split("\n\n")
    for para in paragraphs:
        if any(ind in para for ind in indicators):
            if len(para) < 200:
                results.append(para.strip())
    return results[:3]  # Cap at 3 passages


def _compute_confidence(prose: str) -> float:
    """Estimate extraction confidence based on pattern coverage."""
    if not prose:
        return 0.0
    total_chars = len(prose)
    matched_chars = 0

    # Count characters covered by known patterns
    matched_chars += sum(len(m.group()) for m in re.finditer(r'["""].+?["»"]', prose))
    matched_chars += sum(len(m.group()) for m in re.finditer(r"[\u4e00-\u9fff]{2,4}", prose))

    return min(0.95, matched_chars / max(total_chars, 1))


def extract_scr(project_dir: Path, chapter: int) -> StructuredChapterRepresentation:
    """Once per chapter: deterministic structured extraction from chapter prose.

    Caches result to context/chapter-N-scr.json.
    """
    cache_path = project_dir / "context" / f"chapter-{chapter}-scr.json"

    # Return cached if available and fresh
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        return StructuredChapterRepresentation(**cached)

    chapter_path = project_dir / "chapters" / f"chapter-{chapter}.md"
    if not chapter_path.exists():
        raise FileNotFoundError(f"Chapter file not found: {chapter_path}")

    chapter_text = chapter_path.read_text(encoding="utf-8")
    prose = extract_prose(chapter_text)

    scr = StructuredChapterRepresentation(
        chapter=chapter,
        extracted_at=datetime.now(UTC).isoformat(),
        character_locations=_extract_character_locations(prose),
        dialogue_segments=_extract_dialogue_segments(prose),
        event_timeline=_extract_event_timeline(prose),
        emotional_markers=_extract_emotional_markers(prose),
        hook_appearances=_extract_hook_appearances(prose),
        world_refs=_extract_world_references(prose),
        pov_shifts=_extract_pov_shifts(prose),
        decision_points=_extract_decision_points(prose),
        paragraph_stats=_compute_paragraph_stats(prose),
        sensitive_hits=_scan_sensitive_words(prose),
        fatigue_word_hits=_scan_fatigue_words(prose),
        transition_markers=_scan_transition_markers(prose),
        opening_paragraph=_extract_opening(prose),
        closing_paragraph=_extract_closing(prose),
        implicit_info_passages=_extract_implicit_passages(prose),
        total_chinese_chars=sum(1 for c in prose if "\u4e00" <= c <= "\u9fff"),
        extraction_confidence=_compute_confidence(prose),
    )

    # Cache to disk
    safe_write(cache_path, json.dumps(asdict(scr), ensure_ascii=False, indent=2))
    return scr
