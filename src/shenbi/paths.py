# src/shenbi/paths.py
"""RoundPaths: the single path-resolution authority for one dispatch/run.
Encapsulates three roots (round_dir / project_dir / repo_root) and eliminates
bare-string path joins and silent CWD fallbacks.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shenbi.contracts.paths import resolve_chapter_path


class Layout(StrEnum):
    """Output layout families (spec #48 C34/F413). Single probe authority."""

    SKILL_OUTPUT = "skill-output"
    NOVEL_OUTPUT = "novel-output"
    PROJECT_OUTPUT = "project-output"
    NONE = "none"


_LAYOUT_ROOT_NAMES = {layout.value for layout in Layout if layout is not Layout.NONE}


def detect_layout(project_dir: Path) -> Layout:
    """Detect the output layout family for ``project_dir`` (pure, no I/O side effects).

    Project-dir level keying with upward parent walk:
    - dir contains novel.json -> PROJECT_OUTPUT
    - dir contains genre-config.json and parent.name is a layout root
      ("novel-output"/"skill-output") -> that layout
    - dir name itself is a layout root -> that layout (anchors root derivation;
      callers collecting *project roots* must additionally require a key file)
    - otherwise walk up one parent and retry; filesystem root -> NONE
    """
    d = Path(project_dir)
    while True:
        if (d / "novel.json").exists():
            return Layout.PROJECT_OUTPUT
        if (d / "genre-config.json").exists() and d.parent.name in _LAYOUT_ROOT_NAMES:
            return Layout(d.parent.name)
        if d.name in _LAYOUT_ROOT_NAMES:
            return Layout(d.name)
        if d.parent == d:
            return Layout.NONE
        d = d.parent


@dataclass(frozen=True)
class RoundPaths:
    round_dir: Path  # this round's workspace (outputs, markers, state)
    project_dir: Path  # the novel project root (novel.json, world/, chapters/, truth/)
    repo_root: Path  # repo root (SKILL.md, fixtures, rubric)

    def read(self, rel: str, chapter: int | None = None) -> Path:
        resolved = resolve_chapter_path(rel, chapter)
        rd = self.round_dir / resolved
        if rd.exists():
            return rd.resolve()
        return (self.project_dir / resolved).resolve()

    def write(self, rel: str, chapter: int | None = None) -> Path:
        resolved = resolve_chapter_path(rel, chapter)
        return (self.round_dir / resolved).resolve()

    def repo(self, rel: str) -> Path:
        return (self.repo_root / rel).resolve()

    def backup(self, rel: str, chapter: int | None = None) -> Path:
        w = self.write(rel, chapter)
        return w.with_name(w.name + ".bak")
