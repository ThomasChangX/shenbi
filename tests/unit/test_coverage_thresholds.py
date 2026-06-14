"""Enforce coverage thresholds post-test.

This test runs LAST (@pytest.mark.last). It reads coverage.xml produced by
the main test run (which must NOT pass --no-cov). In CI, the main run is
`pytest -n auto -m "not last"` and this test runs separately with --no-cov
to avoid overwriting coverage.xml.

Single-invocation guard: if --no-cov was NOT passed (i.e., cov plugin is
still active), skip — coverage.xml would be stale or missing because
pytest-cov writes reports at session teardown, after this test runs.

Cobertura XML format: branch counts are attributes on the root <coverage>
element (branches-valid, branches-covered).
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

COVERAGE_XML = Path(__file__).resolve().parent.parent / "coverage" / "coverage.xml"

# P-1.B: staged ramp-up. Current branch coverage is ~1% (most framework code
# is legacy untyped modules with ignore_errors overrides in mypy/basedpyright).
# As P-1.E refactors these modules and adds tests, raise this threshold.
# Target trajectory: 30% after P-1.E, 60% after P-2, 80% after P-3.
BRANCH_THRESHOLD_PCT = 0.5


@pytest.mark.last
def test_branch_coverage_meets_threshold(request: pytest.FixtureRequest) -> None:
    """Branch coverage across the framework must meet the staged threshold."""
    if not request.config.getoption("--no-cov", default=False):
        pytest.skip(
            "coverage threshold only enforced in the --no-cov second invocation; "
            "run: pytest -m 'last' --no-cov"
        )

    if not COVERAGE_XML.exists():
        pytest.fail(
            f"coverage.xml not found at {COVERAGE_XML}; ensure the main pytest run "
            "produces it and this test runs with --no-cov to avoid overwriting"
        )

    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()

    branches_valid = int(root.get("branches-valid", "0"))
    branches_covered = int(root.get("branches-covered", "0"))

    if branches_valid == 0:
        pytest.fail("coverage.xml has no branch data; ensure pytest runs with --cov-branch")

    pct = (branches_covered / branches_valid) * 100
    assert pct >= BRANCH_THRESHOLD_PCT, (
        f"Branch coverage {pct:.2f}% below {BRANCH_THRESHOLD_PCT}%. "
        f"Covered {branches_covered}/{branches_valid} branches."
    )
