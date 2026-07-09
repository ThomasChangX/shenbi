# src/shenbi/paths.py
"""RoundPaths: the single path-resolution authority for one dispatch/run.
Encapsulates three roots (round_dir / project_dir / repo_root) and eliminates
bare-string path joins and silent CWD fallbacks.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from shenbi.contracts.paths import resolve_chapter_path


@dataclass(frozen=True)
class RoundPaths:
    round_dir: Path  # this round's workspace (outputs, markers, state)
    project_dir: Path  # the novel project root (novel.json, world/, chapters/, truth/)
    repo_root: Path  # repo root (SKILL.md, fixtures, rubric, validate-gate.py)

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
