#!/usr/bin/env python3
"""Keep uv.lock in step with hook revs in .pre-commit-config.yaml (spec #97).

``pre-commit autoupdate`` rewrites only ``.pre-commit-config.yaml``, while the
lint and type faces run the lockfile's copies of the same tools. A hook bump
therefore leaves the two split until someone aligns them by hand (ruff 0.17.6:
bot PR #385, manual follow-up #388). This reads the hook revs, compares them
with the locked versions and runs ``uv lock --upgrade-package`` for every hook
that moved. Exit 1 when a moved hook cannot be pinned: that needs a person,
and it must not pass silently.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Hook repository -> the PyPI distribution uv.lock pins for the same tool.
LOCKED_HOOKS = {
    "https://github.com/astral-sh/ruff-pre-commit": "ruff",
    "https://github.com/pre-commit/mirrors-mypy": "mypy",
    "https://github.com/adrienverge/yamllint": "yamllint",
    "https://github.com/shellcheck-py/shellcheck-py": "shellcheck-py",
}
# The version part of a rev: drops the leading "v" and a packaging suffix
# such as the "-1" of shellcheck-py's v0.11.0.1-1.
_REV = r"v?(\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?)"


def hook_revs(config: str) -> dict[str, str]:
    """Map the distribution of each mapped hook to its rev in a config text."""
    revs = {}
    for repo, dist in LOCKED_HOOKS.items():
        match = re.search(r"repo:\s*" + re.escape(repo) + r"\s*\n\s*rev:\s*" + _REV, config)
        if match:
            revs[dist] = match.group(1)
    return revs


def locked_versions(lock: str) -> dict[str, str]:
    """Map each mapped distribution to its version in a uv.lock text."""
    versions = {}
    for dist in LOCKED_HOOKS.values():
        match = re.search(
            r'^name = "' + re.escape(dist) + r'"\nversion = "([^"]+)"', lock, re.MULTILINE
        )
        if match:
            versions[dist] = match.group(1)
    return versions


def mismatches(config: str, lock: str) -> list[tuple[str, str]]:
    """(distribution, hook version) for every mapped hook not at the locked version."""
    versions = locked_versions(lock)
    return [
        (dist, rev) for dist, rev in sorted(hook_revs(config).items()) if versions.get(dist) != rev
    ]


def main() -> int:
    """Pin uv.lock to every hook rev that moved; report the ones that could not be."""
    moved = mismatches(
        (REPO / ".pre-commit-config.yaml").read_text("utf-8"),
        (REPO / "uv.lock").read_text("utf-8"),
    )
    if not moved:
        print("uv.lock already matches every mapped hook rev")
        return 0
    for dist, version in moved:
        pin = f"{dist}=={version}"
        result = subprocess.run(["uv", "lock", "--upgrade-package", pin], cwd=REPO, check=False)
        if result.returncode != 0:
            print(f"hook rev {dist} {version} has no match on PyPI; align uv.lock by hand")
            return 1
        print(f"uv.lock: {dist} -> {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
