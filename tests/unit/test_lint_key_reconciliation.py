"""Tests for tools/lint_key_reconciliation.py (spec #27 T7)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_orphan_read_key_warns_and_strict_fails(tmp_path, monkeypatch):
    import tools.lint_key_reconciliation as lk

    orphan = lk.ReadKey(
        "test/orphan",
        "src/shenbi/scoring.py: def main",  # real anchor
        "ghost-key",
        ["src/shenbi/does_not_exist.py: def nothing"],
    )
    monkeypatch.setattr(lk, "READ_KEY_REGISTRY", [orphan])
    assert lk.main([]) == 0  # WARN mode non-fatal
    assert lk.main(["--strict"]) == 1


@pytest.mark.unit
def test_healthy_read_key_passes_strict(monkeypatch):
    import tools.lint_key_reconciliation as lk

    healthy = lk.ReadKey(
        "test/healthy",
        "src/shenbi/scoring.py: def main",
        "final_score",
        ["src/shenbi/scoring.py: final_score"],
    )
    monkeypatch.setattr(lk, "READ_KEY_REGISTRY", [healthy])
    assert lk.main(["--strict"]) == 0


@pytest.mark.unit
def test_zero_writer_sources_flagged(monkeypatch):
    import tools.lint_key_reconciliation as lk

    no_writer = lk.ReadKey(
        "test/no-writer",
        "src/shenbi/scoring.py: def main",
        "some-key",
        [],
    )
    monkeypatch.setattr(lk, "READ_KEY_REGISTRY", [no_writer])
    assert lk.main(["--strict"]) == 1


@pytest.mark.unit
def test_real_registry_reconciled():
    """验收 3: the shipped registry runs clean in WARN mode (zero WARN)."""
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "tools/lint_key_reconciliation.py"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert proc.returncode == 0
    assert "WARN" not in proc.stdout
    assert "OK" in proc.stdout
