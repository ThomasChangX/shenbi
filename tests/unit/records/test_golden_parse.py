from __future__ import annotations

import json

from shenbi.gates.shared import PROJECT
from shenbi.records.parser import parse_records

FIXTURE = PROJECT / "tests" / "fixtures" / "truth-pending_hooks.md"
BASELINE = PROJECT / "tests" / "baselines" / "pending_hooks.parse.json"


def test_parse_matches_golden_baseline() -> None:
    """Golden-parse：parse(fixture) 必须等于提交基线。parser 漂移 → fail。"""
    recs = parse_records(FIXTURE.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert recs == baseline
