"""Shared audit context cache: pre-extracts chapter and project-level data
so multiple audit LLM calls for the same chapter reuse the same I/O.

Build a :class:`SharedAuditContext` once per chapter and pass it to each
auditor rather than letting every auditor re-read the same files.
"""

from dataclasses import dataclass
from pathlib import Path

from shenbi.logging import get_logger

log = get_logger(__name__)


@dataclass
class SharedAuditContext:
    """Pre-extracted context shared across all audit calls for a single chapter."""

    chapter_text: str = ""
    chapter_summary: str = ""
    world_rules: str = ""
    character_list: str = ""
    style_profile: str = ""
    volume_context: str = ""
    pending_hooks: str = ""

    @property
    def estimated_tokens(self) -> int:
        total = sum(
            len(v)
            for v in [
                self.chapter_text,
                self.chapter_summary,
                self.world_rules,
                self.character_list,
                self.style_profile,
                self.volume_context,
                self.pending_hooks,
            ]
        )
        return total // 3  # rough token estimate


def build_shared_audit_context(project_dir: Path, chapter: int) -> SharedAuditContext:
    """Build shared context once per chapter, reused across all audit LLM calls."""
    ctx = SharedAuditContext()

    chapter_file = project_dir / "chapters" / f"chapter-{chapter:03d}.md"
    if chapter_file.exists():
        ctx.chapter_text = chapter_file.read_text(encoding="utf-8")

    world_rules_file = project_dir / "truth" / "world_rules.md"
    if world_rules_file.exists():
        raw = world_rules_file.read_text(encoding="utf-8")
        ctx.world_rules = _summarize_if_large(raw, max_chars=5000)

    characters_file = project_dir / "truth" / "character_matrix.md"
    if characters_file.exists():
        raw = characters_file.read_text(encoding="utf-8")
        ctx.character_list = _summarize_if_large(raw, max_chars=3000)

    style_file = project_dir / "style" / "style_profile.md"
    if style_file.exists():
        ctx.style_profile = style_file.read_text(encoding="utf-8")[:2000]

    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if hooks_file.exists():
        ctx.pending_hooks = hooks_file.read_text(encoding="utf-8")[:3000]

    volume_map_file = project_dir / "truth" / "volume_map.md"
    if volume_map_file.exists():
        raw = volume_map_file.read_text(encoding="utf-8")
        ctx.volume_context = _extract_volume_chapter(raw, chapter)

    log.info(
        "shared_audit_context_built",
        chapter=chapter,
        estimated_tokens=ctx.estimated_tokens,
    )
    return ctx


def _summarize_if_large(text: str, max_chars: int = 5000) -> str:
    """Truncate text if it exceeds max_chars, adding summary indicator."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[... truncated from {len(text)} chars]"


def _extract_volume_chapter(volume_map_text: str, chapter: int) -> str:
    """Extract current chapter node from volume_map."""
    lines = volume_map_text.split("\n")
    in_section = False
    result = []
    for line in lines:
        if f"第{chapter}章" in line or f"Chapter {chapter}" in line:
            in_section = True
        elif in_section and (line.startswith("##") or line.startswith("# ")):
            break
        if in_section:
            result.append(line)
    return "\n".join(result[:50]) if result else ""
