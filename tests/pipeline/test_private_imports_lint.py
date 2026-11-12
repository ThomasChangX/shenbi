"""Spec #87 T5: private-import baseline lint — subset invariant."""

import pytest


@pytest.mark.unit
def test_baseline_subset_assertion() -> None:
    """Current tests' shenbi.pipeline private imports must be a subset of
    the version-controlled baseline (increment = zero).
    """
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "tools/lint_private_imports.py", "--check"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.unit
def test_baseline_exists_and_sorted() -> None:
    from pathlib import Path

    baseline = Path("tests/private_imports_baseline.txt")
    assert baseline.is_file()
    lines = [
        ln
        for ln in baseline.read_text(encoding="utf-8").splitlines()
        if ln and not ln.startswith("#")
    ]
    assert lines == sorted(lines)
