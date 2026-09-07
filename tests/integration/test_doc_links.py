"""Verify internal markdown links resolve (pure Python, no npm deps).

C17 T2 (spec #55, F001/F732): the former markdown-link-check subprocess
implementation required an npm tool that is never installed in CI, so the
371 parametrized cases were permanently skipped and internal link rot had
no defense. This rewrite checks internal relative links in-process and runs
on every PR as part of the ordinary pytest suite.

External http(s) links are out of scope (they were already ignored by the
old mlc-config.json); checking them would gate PRs on third-party uptime.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
# Markdown link targets: [text](target) — image syntax ![alt](src) matches too.
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _strip_code(text: str) -> str:
    """Remove fenced blocks and inline code spans from markdown text.

    docs/specs/plans are full of link *examples* inside backticks that are
    not real links; without stripping, those mass-fail as false positives.
    """
    without_fences = re.sub(
        r"^ {0,3}(?:```|~~~).*?(?:^ {0,3}(?:```|~~~)|\Z)",
        "",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return _CODE_SPAN_RE.sub("", without_fences)


def check_internal_links(doc: Path, repo_root: Path = REPO_ROOT) -> list[str]:
    """Return descriptions of broken internal links in ``doc`` (empty = OK).

    A link is checked when its target is relative (not http(s)/mailto/#) and
    resolves against the document's own directory. ``#anchor`` suffixes are
    stripped before the file-existence check.
    """
    text = _strip_code(doc.read_text(encoding="utf-8"))
    broken: list[str] = []
    for target in _LINK_RE.findall(text):
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            continue  # absolute URI scheme (http, mailto, ...) or pure anchor
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue  # same-file anchor
        path_part = path_part.rstrip("/")  # directory links may carry trailing slash
        if not (doc.parent / path_part).exists():
            broken.append(f"{doc.name}: [{target}]")
    return broken


def _markdown_docs() -> list[str]:
    """Markdown files that are documentation (link-checked).

    Scoped to docs/ and repo-root *.md. Test fixtures (tests/fixtures/) and
    archived round output (tests/rounds/archived/) are test data with
    intentionally illustrative content — not documentation — so they are
    excluded from link-checking.
    """
    docs = [p for p in (REPO_ROOT / "docs").rglob("*.md")]
    root = [p for p in REPO_ROOT.glob("*.md")]
    return sorted(str(p.relative_to(REPO_ROOT)) for p in docs + root)


@pytest.mark.parametrize("doc", _markdown_docs())
def test_internal_links_resolve(doc: str) -> None:
    broken = check_internal_links(REPO_ROOT / doc)
    assert not broken, f"Broken internal links in {doc}:\n" + "\n".join(broken)


class TestCheckInternalLinks:
    """Unit tests for the parser (synthetic tmp_path inputs — G0.9 does not
    apply: these are unit-test inputs, not tests/fixtures/ artifacts).
    """

    def test_code_fence_and_span_ignored(self, tmp_path: Path) -> None:
        d = tmp_path / "sub.md"
        d.write_text(
            "```\n[example](nonexistent-a.md)\n```\n"
            "`[inline](nonexistent-b.md)`\n"
            "[real](exists.md)\n",
            encoding="utf-8",
        )
        (tmp_path / "exists.md").write_text("x", encoding="utf-8")
        assert check_internal_links(d, repo_root=tmp_path) == []

    def test_relative_and_anchor_links(self, tmp_path: Path) -> None:
        d = tmp_path / "page.md"
        (tmp_path / "target.md").write_text("x", encoding="utf-8")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "t.md").write_text("x", encoding="utf-8")
        d.write_text(
            "[a](target.md#section) [b](sub/t.md) [c](#top) "
            "[d](mailto:x@y.z) [e](https://example.com)\n",
            encoding="utf-8",
        )
        assert check_internal_links(d, repo_root=tmp_path) == []

    def test_broken_link_reported(self, tmp_path: Path) -> None:
        d = tmp_path / "page.md"
        d.write_text("[gone](missing.md)\n", encoding="utf-8")
        assert check_internal_links(d, repo_root=tmp_path) == ["page.md: [missing.md]"]

    def test_directory_link_with_trailing_slash(self, tmp_path: Path) -> None:
        d = tmp_path / "page.md"
        (tmp_path / "dir").mkdir()
        d.write_text("[dir](dir/)\n", encoding="utf-8")
        assert check_internal_links(d, repo_root=tmp_path) == []
