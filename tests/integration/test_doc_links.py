"""Verify internal markdown links resolve.

Complements test_docs_accuracy.py (code-span file paths) by checking the
markdown [text](link) links that test_docs_accuracy does not cover.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MLC_CONFIG = REPO_ROOT / "tests" / "fixtures" / "mlc-config.json"


@pytest.fixture(scope="session")
def _require_mlc() -> None:
    if shutil.which("markdown-link-check") is None:
        pytest.skip("markdown-link-check not installed (npm i -g markdown-link-check)")


def _markdown_docs() -> list[str]:
    return sorted(
        str(p.relative_to(REPO_ROOT))
        for p in REPO_ROOT.rglob("*.md")
        if ".venv" not in p.parts and "site/" not in p.parts
    )


@pytest.mark.parametrize("doc", _markdown_docs())
def test_internal_links_resolve(doc: str, _require_mlc: None) -> None:
    result = subprocess.run(
        ["markdown-link-check", "--config", str(MLC_CONFIG), "--quiet", doc],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Broken links in {doc}:\n{result.stdout}"
