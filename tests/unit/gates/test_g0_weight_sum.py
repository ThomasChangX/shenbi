"""G0.5 — rubric weight-sum checker (C17 T5 / T1109, spec #55).

G0.5 was permanently UNIMPLEMENTED with a hardcoded placeholder; a 2026-06
baseline even recorded a fake PASS through it. These tests pin the real
behavior: every rubric weight table must sum to exactly 100%.
"""

from pathlib import Path

import pytest

from shenbi.status import GateStatus


def _make_rubric(tmp_path: Path, weights: list[str]) -> Path:
    rows = "\n".join(f"| {i} | dim{i} | {w} | |" for i, w in enumerate(weights, 1))
    p = tmp_path / "rubric.md"
    p.write_text(
        f"# R\n\n## Dimensions\n\n| # | Dimension | Weight | Standard |\n|---|---|---|---|\n{rows}\n",
        encoding="utf-8",
    )
    return p


class TestRubricWeightSum:
    def test_sums_weight_column(self, tmp_path: Path) -> None:
        from shenbi.gates.g0 import _rubric_weight_sum

        rubric = _make_rubric(tmp_path, ["10%", "5%", "50%", "20%", "15%"])
        assert _rubric_weight_sum(rubric) == 100

    def test_fractional_weights_supported(self, tmp_path: Path) -> None:
        from shenbi.gates.g0 import _rubric_weight_sum

        rubric = _make_rubric(tmp_path, ["33.5%", "66.5%"])
        assert _rubric_weight_sum(rubric) == 100

    def test_no_weight_table_returns_none(self, tmp_path: Path) -> None:
        from shenbi.gates.g0 import _rubric_weight_sum

        p = tmp_path / "no-table.md"
        p.write_text("# Plain prose, no weight table\n", encoding="utf-8")
        assert _rubric_weight_sum(p) is None


class TestG05Check:
    def test_real_rubrics_all_pass(self) -> None:
        from shenbi.gates.g0 import _g05_weight_check

        # Full adjudication: all real rubrics run every time (measured
        # milliseconds for ~80 files of table regex — see progress.md).
        result = _g05_weight_check()
        assert result["s"] is GateStatus.PASS, result

    def test_mismatched_rubric_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from shenbi.gates import g0

        tiers = tmp_path / "tiers" / "t1-skill"
        tiers.mkdir(parents=True)
        _make_rubric(tiers, ["50%", "40%"])  # sums to 90, not 100
        monkeypatch.setattr(g0, "TESTS", tmp_path)

        result = g0._g05_weight_check()
        assert result["s"] is GateStatus.FAIL
        assert "90" in str(result.get("r", ""))
