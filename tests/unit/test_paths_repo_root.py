"""spec #92 T2b: REPO_ROOT single-source + parents[N] purge."""

import subprocess


def test_repo_root_points_at_repo() -> None:
    from shenbi.paths import REPO_ROOT

    assert (REPO_ROOT / "pyproject.toml").exists()
    assert (REPO_ROOT / "justfile").exists()


def test_no_parents_magic_in_src() -> None:
    """parents[2|3|4] outside paths.py is forbidden (spec T2 criterion)."""
    result = subprocess.run(
        ["git", "grep", "-nE", r"parents\[[234]\]", "--", "src/shenbi/"],
        capture_output=True,
        text=True,
    )
    hits = [line for line in result.stdout.splitlines() if "paths.py" not in line]
    assert hits == [], f"parents[N] survivors: {hits}"
