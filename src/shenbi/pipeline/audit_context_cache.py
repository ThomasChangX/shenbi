"""Shared audit context cache: pre-extracts chapter and project-level data
so multiple audit LLM calls for the same chapter reuse the same I/O.

Build a :class:`SharedAuditContext` once per chapter and pass it to each
auditor rather than letting every auditor re-read the same files.
"""

from dataclasses import dataclass, field
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
    # C28 R1 read-suppression source: FULL original bytes keyed by
    # project-relative POSIX path (same form as dispatch_helper._input_key).
    # The summarized fields above are truncated values and MUST NOT back
    # suppression (byte-equality gate).
    raw_files: dict[str, str] = field(default_factory=dict)

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


def _rel(path: Path, project_dir: Path) -> str:
    """Project-relative POSIX key — must match dispatch_helper._input_key."""
    try:
        return path.relative_to(project_dir).as_posix()
    except ValueError:
        return str(path)


def build_shared_audit_context(project_dir: Path, chapter: int) -> SharedAuditContext:
    """Build shared context once per chapter, reused across all audit LLM calls.

    C28 R1 (F312/T1614): the three builder paths were dead keys —
    ``chapter-{chapter:03d}.md`` zero-padding (production writers are
    unpadded), ``truth/world_rules.md`` (canonical is ``world/rules.md``),
    ``truth/volume_map.md`` (canonical is ``outline/volume_map.md``) — so the
    shared context was always empty and the audit wave re-read the chapter
    file 9x per chapter. ``raw_files`` holds the full original bytes for the
    read-suppression table.
    """
    ctx = SharedAuditContext()

    chapter_file = project_dir / "chapters" / f"chapter-{chapter}.md"
    if chapter_file.exists():
        ctx.chapter_text = chapter_file.read_text(encoding="utf-8")
        ctx.raw_files[_rel(chapter_file, project_dir)] = ctx.chapter_text

    world_rules_file = project_dir / "world" / "rules.md"
    if world_rules_file.exists():
        raw = world_rules_file.read_text(encoding="utf-8")
        ctx.world_rules = _summarize_if_large(raw, max_chars=5000)
        ctx.raw_files[_rel(world_rules_file, project_dir)] = raw

    characters_file = project_dir / "truth" / "character_matrix.md"
    if characters_file.exists():
        raw = characters_file.read_text(encoding="utf-8")
        ctx.character_list = _summarize_if_large(raw, max_chars=3000)
        ctx.raw_files[_rel(characters_file, project_dir)] = raw

    style_file = project_dir / "style" / "style_profile.md"
    if style_file.exists():
        raw = style_file.read_text(encoding="utf-8")
        ctx.style_profile = raw[:2000]
        ctx.raw_files[_rel(style_file, project_dir)] = raw

    hooks_file = project_dir / "truth" / "pending_hooks.md"
    if hooks_file.exists():
        raw = hooks_file.read_text(encoding="utf-8")
        ctx.pending_hooks = raw[:3000]
        ctx.raw_files[_rel(hooks_file, project_dir)] = raw

    # volume_context has zero consumers in the audit wave (C28 spec R2 drop)
    # — path fixed for hygiene, extraction retained, not in raw_files.
    volume_map_file = project_dir / "outline" / "volume_map.md"
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
