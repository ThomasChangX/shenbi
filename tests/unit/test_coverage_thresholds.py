"""Enforce coverage thresholds post-test."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

COVERAGE_XML = Path("tests/coverage/coverage.xml")
LINE_THRESHOLD = 90
BRANCH_THRESHOLD = 80


@pytest.mark.last
def test_branch_coverage_meets_threshold() -> None:
    """Branch coverage must be >= 80%."""
    if not COVERAGE_XML.exists():
        pytest.fail(
            "coverage.xml not found; ensure pytest runs with "
            "'--cov-report=xml:tests/coverage/coverage.xml' and "
            "test_coverage_thresholds runs AFTER all other tests"
        )

    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()

    total_valid = 0
    total_covered = 0
    for cls in root.findall(".//class"):
        for counter in cls.findall("counter"):
            if counter.get("type") == "BRANCH":
                total_valid += int(counter.get("valid", "0"))
                total_covered += int(counter.get("covered", "0"))

    if total_valid == 0:
        pytest.skip("No branches in coverage data")

    pct = (total_covered / total_valid) * 100
    assert pct >= BRANCH_THRESHOLD, (
        f"Branch coverage {pct:.1f}% below {BRANCH_THRESHOLD}%. "
        f"Covered {total_covered}/{total_valid} branches."
    )
