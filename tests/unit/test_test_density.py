"""Enforce test density floor per README Threshold Justification.

Metric: test_function_count / framework_loc
Target: >= 0.10 (1 test function per 10 LOC of framework code).

Cluster 04 (Plan 4 PR-28~32) will deliver the test volume to meet this
floor. Until then, the assertion is marked xfail(strict=True) so the
canonical value is encoded without putting main red. Plan 4 must remove
the xfail decorator in the same PR that delivers the 600th test.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_DIR = REPO_ROOT / "src" / "shenbi"
TEST_DIRS = [REPO_ROOT / "tests" / sub for sub in ("unit", "integration", "property", "benchmark")]


def count_framework_loc() -> int:
    """Count non-blank, non-comment Python LOC in src/shenbi/."""
    total = 0
    for py_file in FRAMEWORK_DIR.rglob("*.py"):
        for line in py_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                total += 1
    return total


def count_test_functions() -> int:
    """Count `def test_*` (and `async def test_*`) functions across all test directories."""
    total = 0
    for test_dir in TEST_DIRS:
        if not test_dir.exists():
            continue
        for py_file in test_dir.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                    total += 1
    return total


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Plan 4 PR-28~32 must deliver ~600 tests to meet 0.10 density floor. "
        "Remove this xfail in the same Plan 4 PR that crosses the threshold; "
        "strict=True means an unexpected XPASS will also fail."
    ),
)
def test_density_meets_minimum() -> None:
    """Test density must be >= 0.10 (1 test per 10 framework LOC)."""
    framework_loc = count_framework_loc()
    test_count = count_test_functions()
    density = test_count / framework_loc if framework_loc else 0
    assert density >= 0.10, (
        f"Test density {density:.4f} below 0.10 floor "
        f"({test_count} tests / {framework_loc} framework LOC). "
        f"Add ~{int(0.10 * framework_loc - test_count)} more tests."
    )

