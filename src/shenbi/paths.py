# src/shenbi/paths.py
"""RoundPaths: the single path-resolution authority for one dispatch/run.
Encapsulates three roots (round_dir / project_dir / repo_root) and eliminates
bare-string path joins and silent CWD fallbacks.
"""

from __future__ import annotations

# REPO_ROOT binds BEFORE the contracts import below: gates.shared (imported
# transitively via shenbi.contracts -> ... -> g4.generic -> gates.shared)
# imports REPO_ROOT from this module, so it must exist on the partially
# initialized module when that import cycle re-enters paths (spec #92 T2b).
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
"""Single source for the repository root (spec #92 T2b).

Replaces the four same-value definitions (gates.shared.PROJECT,
dispatch_helper._PROJECT_ROOT, plugins.generate.REPO_ROOT, codex local) and
the per-file parents[N] derivations. sync_contracts imports PROJECT from
gates.shared and stays a consumer, not a definer.
"""

from dataclasses import dataclass
from enum import StrEnum

from structlog import get_logger

log = get_logger(__name__)


def _resolve(rel: str, chapter: int | None) -> str:
    """Lazy resolve: importing contracts.paths at module top creates a cycle
    (paths -> contracts -> registry -> gates.shared -> paths); the method-local
    import runs after all modules are initialized (spec #92 T2b).
    """
    from shenbi.contracts.paths import resolve_chapter_path

    return resolve_chapter_path(rel, chapter)


class Layout(StrEnum):
    """Output layout families (spec #48 C34/F413). Single probe authority."""

    SKILL_OUTPUT = "skill-output"
    NOVEL_OUTPUT = "novel-output"
    PROJECT_OUTPUT = "project-output"
    NONE = "none"


_LAYOUT_ROOT_NAMES = {Layout.NOVEL_OUTPUT.value, Layout.SKILL_OUTPUT.value}


def detect_layout(project_dir: Path) -> Layout:
    """Detect the output layout family for ``project_dir`` (pure, no I/O side effects).

    Project-dir level keying with upward parent walk:
    - dir contains novel.json -> PROJECT_OUTPUT
    - dir contains genre-config.json and parent.name is
      "novel-output"/"skill-output" -> that layout
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

    @classmethod
    def require_roots(
        cls,
        rd: str | None,
        project_dir: str | None,
        repo_root: str | Path,
    ) -> RoundPaths:
        """Collapse the 11-checker preamble (spec #89 T3, spec #48 C34).

        Raises the pinned ValueError when both roots are None (message kept
        byte-identical — test_g4_signatures pins it); mutual defaults
        otherwise: each missing root mirrors the provided one.
        """
        if rd is None and project_dir is None:
            raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
        return cls(
            round_dir=Path(str(rd or project_dir)),
            project_dir=Path(str(project_dir or rd)),
            repo_root=Path(repo_root),
        )

    def read(self, rel: str, chapter: int | None = None, *, strict: bool = False) -> Path:
        resolved = _resolve(rel, chapter)
        rd = self.round_dir / resolved
        if rd.exists():
            return rd.resolve()
        # spec #48 C34: rd-miss fallback to project_dir is explicit and
        # logged — no silent fallthrough.
        if strict:
            # API affordance (spec #48 C34 T2): no production caller yet —
            # fix-and-keep-dormant, consumers opt in when they need no-fallback
            raise FileNotFoundError(f"round_dir miss and strict=True: {rd}")
        log.debug("round_paths_read_fallback", rel=rel)
        return (self.project_dir / resolved).resolve()

    def write(self, rel: str, chapter: int | None = None) -> Path:
        resolved = _resolve(rel, chapter)
        return (self.round_dir / resolved).resolve()

    def repo(self, rel: str) -> Path:
        return (self.repo_root / rel).resolve()

    def backup(self, rel: str, chapter: int | None = None) -> Path:
        w = self.write(rel, chapter)
        return w.with_name(w.name + ".bak")
