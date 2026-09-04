"""C28 read-suppression test file (T2 template short-circuit + T4 R1 tests).

T2 part: _init_truth_templates must skip the 74-skill contract scan
(~655ms) when every template file already exists (T1606).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import shenbi.pipeline.dispatch_helper as dh


def test_init_truth_templates_shortcircuits_when_all_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    truth = tmp_path / "truth"
    truth.mkdir()
    for fn in dh._TRUTH_FILE_TITLES:
        (truth / fn).write_text("---\nupdate_mode: replace\n---\n", encoding="utf-8")

    calls = {"n": 0}

    def counting_collect() -> dict[str, list[str]]:
        calls["n"] += 1
        return {}

    monkeypatch.setattr(dh, "_collect_declared_truth_fields", counting_collect)
    dh._init_truth_templates(tmp_path)
    assert calls["n"] == 0


def test_init_truth_templates_scans_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At least one template missing -> the scan runs and the missing file is created."""
    truth = tmp_path / "truth"
    truth.mkdir()
    names = list(dh._TRUTH_FILE_TITLES)
    for fn in names[:-1]:
        (truth / fn).write_text("---\nupdate_mode: replace\n---\n", encoding="utf-8")

    calls = {"n": 0}

    def counting_collect() -> dict[str, list[str]]:
        calls["n"] += 1
        return {}

    monkeypatch.setattr(dh, "_collect_declared_truth_fields", counting_collect)
    dh._init_truth_templates(tmp_path)
    assert calls["n"] == 1
    assert (truth / names[-1]).exists()
