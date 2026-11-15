"""Spec #105 T1b: six-consumer swap is behavior-preserving (differential vs frozen baseline, #99 precedent)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CORPUS = REPO / "tests" / "fixtures" / "audits"
BASELINE = REPO / "tests" / "baselines" / "severity-swap" / "baseline.json"
PATTERNS_BASELINE = REPO / "tests" / "baselines" / "severity-swap" / "baseline.patterns.json"


def _current_outputs() -> dict[str, object]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = tmp.name
    try:
        subprocess.run(
            [
                sys.executable,
                str(REPO / "tools" / "gen_severity_diff_baseline.py"),
                str(CORPUS),
                out_path,
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO,
        )
        return json.loads(Path(out_path).read_text(encoding="utf-8"))
    finally:
        Path(out_path).unlink(missing_ok=True)


def test_five_sensors_match_frozen_baseline() -> None:
    frozen = json.loads(BASELINE.read_text(encoding="utf-8"))
    current = _current_outputs()
    assert current == frozen, (
        "换装后五传感输出与冻结基线逐项不一致（spec T1 差分判据失败）: "
        f"{[k for k in frozen if frozen[k] != current.get(k)]}"
    )


def test_longitudinal_section_header_now_includes_minor() -> None:
    # 行为变更单列（spec T1 判据(c)：longitudinal MINOR 修复=设计内行为变更，不入差分面）
    from shenbi.contracts.severity import SECTION_HEADER_RE

    assert SECTION_HEADER_RE.match("## MINOR Findings (2)")
    assert not SECTION_HEADER_RE.match("## Resonance 报告")


def test_production_patterns_match_frozen_baseline() -> None:
    """audit-S8 I-3: pattern-level freeze.

    The corpus has no zero-declaration/legend samples, so data-level equality
    alone cannot catch a builder change (verified by mutation). Pinning the
    exact production pattern text closes that gap.
    """
    from tools.gen_severity_diff_baseline import production_patterns

    frozen = json.loads(PATTERNS_BASELINE.read_text(encoding="utf-8"))
    current = production_patterns()
    for key, expected in frozen.items():
        assert current[key] == expected, f"production pattern drifted: {key}"
