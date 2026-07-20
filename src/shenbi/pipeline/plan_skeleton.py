"""Deterministic plan skeleton generator.

Derives ~55% of chapter plan content from volume_map.md, reducing LLM token
consumption and ensuring blueprint alignment. The LLM's role shifts from
"generator" to "polisher + creative filler" for sections 1,4,6,7 while
retaining full creative control over section 5 (Key Decisions).

Sections derived from volume_map:
  - 1. Current Task: fully (node role + description)
  - 4. Transition Role: fully (node role)
  - 6. End-of-Chapter Change: basic (current + next chapter node)
  - 7. Hook Ledger: bridges within activation window

Sections with partial derivation:
  - 2. Reader Expectations: tension curve hints
  - 3. Fulfill/Defer Decisions: cross-volume bridges
  - 8. Don't Do: volume boundary constraints

Section fully LLM-generated:
  - 5. Key Decisions
"""

from __future__ import annotations

import re
from pathlib import Path

# Volume boundaries are parsed at runtime via triggers.py:read_volume_boundaries()
# -- NEVER hard-coded. See _resolve_volume_at_runtime().

from shenbi.pipeline.context_assemble import _BRIDGE_ACTIVATION_WINDOW  # pyright: ignore[reportPrivateUsage]

_SKELETON_TEMPLATE = """# Chapter {chapter} Plan Skeleton

> **以下为参考骨架，可根据创作需要调整。** (The following is a reference
> skeleton; adjust as needed for creative purposes.)
> Pre-filled sections are EDITABLE CONTEXT derived from volume_map.md, not
> locked output. You may modify, override, or deviate from any pre-filled
> content. Section 5 (Key Decisions) is entirely yours to create.

## 1. Current Task
{section_1}

## 2. Reader Expectations
{section_2}

## 3. Fulfill/Defer Decisions
{section_3}

## 4. Transition Role
{section_4}

## 5. Key Decisions
{section_5}

## 6. End-of-Chapter Change
{section_6}

## 7. Hook Ledger
{section_7}

## 8. Don't Do
{section_8}
"""


def generate_plan_skeleton(project_dir: Path, chapter: int) -> str:
    """Generate a deterministic plan skeleton from volume_map.md.

    Returns a markdown string with sections 1,4,6,7 pre-filled where
    possible and the remaining sections containing [LLM] placeholders
    with guidance for completion.
    """
    vm_path = project_dir / "outline" / "volume_map.md"
    if not vm_path.exists():
        return _empty_skeleton(chapter)

    volume_map_text = vm_path.read_text(encoding="utf-8")

    # Resolve current volume at runtime via triggers.py (NEVER hard-code)
    resolved = _resolve_volume_at_runtime(project_dir, chapter)
    if resolved is None:
        current_volume, next_chapter = "Unknown", chapter + 1
    else:
        current_volume, _ch_start, ch_end = resolved
        next_chapter = min(chapter + 1, ch_end)
    chapter_node = _extract_chapter_node(volume_map_text, chapter)
    next_node = _extract_chapter_node(volume_map_text, next_chapter)
    pending_bridges = _extract_pending_bridges(volume_map_text, chapter)

    # Section 1: Current Task (fully derivable)
    if chapter_node:
        section_1 = (
            f"**Role:** {chapter_node['role']}\n"
            f"**Content:** {chapter_node['content']}\n"
            f"**Volume:** {current_volume}"
        )
    else:
        section_1 = f"[LLM] Determine current task for Ch{chapter}. Volume: {current_volume}"

    # Section 2: Reader Expectations (partial)
    section_2 = (
        f"[LLM] Define 3-5 reader expectations for this chapter. "
        f"Consider: what promises does the previous chapter make? "
        f"What tension level is appropriate for a '{chapter_node['role'] if chapter_node else 'unknown'}' chapter?"
    )

    # Section 3: Fulfill/Defer Decisions (partial)
    if pending_bridges:
        bridge_list = "\n".join(f"  - {b}" for b in pending_bridges)
        section_3 = (
            f"[LLM] Decide which hooks to fulfill or defer this chapter.\n"
            f"Pending cross-volume bridges:\n{bridge_list}\n"
            f"Also consider intra-chapter hooks from previous chapter."
        )
    else:
        section_3 = "[LLM] Decide which hooks to fulfill or defer this chapter."

    # Section 4: Transition Role (fully derivable)
    if chapter_node:
        section_4 = (
            f"**Node Role:** {chapter_node['role']}\n"
            f"**From volume_map:** This chapter serves as a '{chapter_node['role']}' node "
            f"within {current_volume}."
        )
    else:
        section_4 = f"[LLM] Define the transition role for Ch{chapter}."

    # Section 5: Key Decisions (full LLM)
    section_5 = (
        "[LLM] List 3-5 key creative decisions for this chapter. "
        "This is fully LLM-generated; the skeleton provides no constraints here. "
        "Consider: character choices, plot pivots, revelation timing."
    )

    # Section 6: End-of-Chapter Change (basic)
    if chapter_node and next_node:
        section_6 = (
            f"**Current chapter role:** {chapter_node['role']}\n"
            f"**Next chapter (Ch{next_chapter}) role:** {next_node['role']}\n"
            f"**Next chapter content hint:** {next_node['content']}\n\n"
            f"[LLM] Refine: what specific changes should occur by end of this chapter "
            f"to set up Ch{next_chapter}?"
        )
    elif chapter_node:
        section_6 = (
            f"**Current chapter role:** {chapter_node['role']}\n\n"
            f"[LLM] Define the end-of-chapter change that propels into the next chapter."
        )
    else:
        section_6 = "[LLM] Define the end-of-chapter change."

    # Section 7: Hook Ledger (partially derivable)
    if pending_bridges:
        bridge_list = "\n".join(f"  - {b}" for b in pending_bridges)
        section_7 = (
            f"[LLM] Track all hooks and their fulfillment status.\n"
            f"Cross-volume bridges approaching activation:\n{bridge_list}\n\n"
            f"[LLM] Add intra-chapter hooks planted/fulfilled this chapter."
        )
    else:
        section_7 = "[LLM] Track all hooks planted and fulfilled this chapter. Include hook IDs."

    # Section 8: Don't Do (partial)
    if chapter_node:
        role = chapter_node["role"]
        if role == "opening":
            section_8 = (
                "[LLM] Avoid: rushing exposition, introducing too many characters. "
                "This is an opening chapter - focus on hooking the reader."
            )
        elif role == "closing":
            section_8 = (
                "[LLM] Avoid: introducing new plot threads, unresolved cliffhangers "
                "that won't pay off soon. This is a closing chapter - deliver resolution."
            )
        else:
            section_8 = (
                "[LLM] List 3-5 things to avoid in this chapter. Consider volume boundaries."
            )
    else:
        section_8 = "[LLM] List 3-5 things to avoid in this chapter."

    return _SKELETON_TEMPLATE.format(
        chapter=chapter,
        section_1=section_1,
        section_2=section_2,
        section_3=section_3,
        section_4=section_4,
        section_5=section_5,
        section_6=section_6,
        section_7=section_7,
        section_8=section_8,
    )


# _resolve_volume_at_runtime imported from context_assemble (canonical definition)
from shenbi.pipeline.context_assemble import _resolve_volume_at_runtime  # pyright: ignore[reportPrivateUsage]


def _extract_chapter_node(volume_map_text: str, chapter: int) -> dict[str, str] | None:
    """Extract {role, content} for a chapter from the volume_map table."""
    pattern = re.compile(rf"\|\s*{chapter}\s*\|([^|]+)\|([^|]+)\|")
    m = pattern.search(volume_map_text)
    if m:
        return {"role": m.group(1).strip(), "content": m.group(2).strip()}
    return None


def _extract_pending_bridges(volume_map_text: str, chapter: int) -> list[str]:
    """Return list of bridge descriptions near activation for this chapter."""
    bridge_section = volume_map_text.split("## Cross-Volume Bridges")
    if len(bridge_section) < 2:
        return []

    pattern = re.compile(r"\|\s*(V\d+-B\d+)\s*\|([^|]+)\|\s*(\d+)\s*\|")
    bridges: list[str] = []
    for m in pattern.finditer(bridge_section[1]):
        bridge_id = m.group(1)
        content = m.group(2).strip()
        activation_ch = int(m.group(3))
        if chapter >= activation_ch - _BRIDGE_ACTIVATION_WINDOW:
            bridges.append(f"{bridge_id}: {content} (activates Ch {activation_ch})")
    return bridges


def _empty_skeleton(chapter: int) -> str:
    """Return skeleton with all [LLM] placeholders when volume_map is missing."""
    return _SKELETON_TEMPLATE.format(
        chapter=chapter,
        section_1=f"[LLM] Determine current task for Ch{chapter}.",
        section_2="[LLM] Define reader expectations.",
        section_3="[LLM] Decide which hooks to fulfill or defer.",
        section_4="[LLM] Define transition role.",
        section_5="[LLM] List key creative decisions.",
        section_6="[LLM] Define end-of-chapter change.",
        section_7="[LLM] Track hooks planted and fulfilled.",
        section_8="[LLM] List things to avoid.",
    )
