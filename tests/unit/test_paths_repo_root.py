"""spec #92 T2b: REPO_ROOT single-source + parents[N] purge."""

import subprocess


def test_repo_root_points_at_repo() -> None:
    from shenbi.paths import REPO_ROOT

    assert (REPO_ROOT / "pyproject.toml").exists()
    assert (REPO_ROOT / "justfile").exists()


def test_no_parents_magic_in_src() -> None:
    """parents[2|3|4] outside paths.py is forbidden (spec T2 criterion)."""
    from shenbi.paths import REPO_ROOT

    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "grep",
            "-nE",
            r"parents\[[234]\]",
            "--",
            "src/shenbi/",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode in (0, 1), f"git grep failed: {result.stderr}"
    hits = [line for line in result.stdout.splitlines() if "src/shenbi/paths.py:" not in line]
    assert hits == [], f"parents[N] survivors: {hits}"
