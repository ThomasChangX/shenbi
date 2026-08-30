"""spec #31 T5: G3 must fail closed without fabricating progress.json (F794 guard)."""

from __future__ import annotations

import pytest

from shenbi.pipeline.dispatch_helper import run_gate_g3


@pytest.mark.unit
def test_g3_fail_closed_no_progress_fabrication(tmp_path):
    rd = tmp_path / "round"
    rd.mkdir()
    result = run_gate_g3("sk", rd)  # (skill, round_dir, chapter=None, phase=None) -> dict
    assert result["status"] == "FAIL"
    assert not (rd / "progress.json").exists()  # 不得自造
