"""Verify documentation accuracy.

Scans markdown files for code-span references to file paths (e.g.,
`tests/validate-gate.py`) and verifies those files exist. Catches the
most common doc drift: stale path references.

Not a substitute for semantic review — only catches missing-file drift.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

DOCS_TO_CHECK = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "command-to-give.md",
    "goal-prompt.md",
    "docs/index.md",
]

ALLOWED_MISSING: set[str] = {
    "deps.json",
    "plans/chapter-N-plan.md",
}

CODESPAN_PATTERN = re.compile(r"`([.\w][\w./-]*\.\w+)`")


def extract_paths_from_doc(doc_path: Path) -> list[Path]:
    """Extract code-span file path references from a markdown doc."""
    if not doc_path.exists():
        return []
    text = doc_path.read_text(encoding="utf-8")
    paths = []
    for match in CODESPAN_PATTERN.finditer(text):
        candidate = match.group(1)
        if "/" in candidate or candidate.endswith(
            (
                ".py",
                ".md",
                ".yaml",
                ".yml",
                ".toml",
                ".json",
                ".sh",
            )
        ):
            paths.append(REPO_ROOT / candidate)
    return paths


@pytest.mark.parametrize("doc_relative", DOCS_TO_CHECK)
def test_doc_references_existing_files(doc_relative: str) -> None:
    """Each code-span file reference in docs must point to an existing file."""
    doc_path = REPO_ROOT / doc_relative
    if not doc_path.exists():
        pytest.skip(f"{doc_relative} not present (may be added by later PR)")

    missing = []
    for referenced in extract_paths_from_doc(doc_path):
        rel = referenced.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWED_MISSING:
            continue
        if not referenced.exists():
            missing.append(f"{doc_relative}: references `{rel}` which does not exist")

    assert not missing, "Documentation references missing files:\n" + "\n".join(missing)


def test_chapter_file_format_doc_exists():
    doc_path = Path(__file__).resolve().parents[2] / "docs" / "framework" / "chapter-file-format.md"
    assert doc_path.exists(), f"Expected {doc_path} to exist"


def test_chapter_file_format_documents_meta_blocks():
    doc_path = Path(__file__).resolve().parents[2] / "docs" / "framework" / "chapter-file-format.md"
    if not doc_path.exists():
        pytest.skip("File not yet created")
    content = doc_path.read_text(encoding="utf-8")
    assert "META" in content
    assert "<!--META-BEGIN-->" in content or "META-BEGIN" in content


def test_chapter_file_format_documents_stripping_method():
    doc_path = Path(__file__).resolve().parents[2] / "docs" / "framework" / "chapter-file-format.md"
    if not doc_path.exists():
        pytest.skip("File not yet created")
    content = doc_path.read_text(encoding="utf-8")
    assert "strip" in content.lower() or "shared.py" in content


def test_chapter_file_format_states_meta_not_prose():
    doc_path = Path(__file__).resolve().parents[2] / "docs" / "framework" / "chapter-file-format.md"
    if not doc_path.exists():
        pytest.skip("File not yet created")
    content = doc_path.read_text(encoding="utf-8")
    assert "not part of" in content.lower() or "not prose" in content.lower()
