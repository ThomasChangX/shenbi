"""Dead-code enforcement allowlist lint (C37 R3, spec #51).

The dead-code gate is basedpyright's ``reportUnusedFunction`` (strict mode,
already part of ``just check``). ``# pyright: ignore[reportUnusedFunction]``
suppressions in ``src/shenbi/`` are the allowlist; each must carry a
justification comment naming a real caller (pyright false positives on
function-local private imports) or a triage defer row.

This lint freezes the allowlist: adding a new suppression (or removing the
justification) fails CI. Shrink the list when a caller is wired for real —
never grow it without a c37-triage row or equivalent justification.

Quarterly review (per spec R3): re-verify each entry still has its caller.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "shenbi"

# (file, function_name) — the frozen allowlist. Every entry documents why
# pyright cannot see the caller.
ALLOWLIST: set[tuple[str, str]] = {
    ("pipeline/chapter_loop.py", "_clamp_resume_cursor"),  # cli.py:cmd_resume local import
    ("pipeline/chapter_loop.py", "_auto_rebuild_progress_if_stale"),  # cmd_resume
    ("pipeline/chapter_loop.py", "_cleanup_residual_staging"),  # cli.py:195 local import
    ("pipeline/chapter_loop.py", "_has_pending_staging_step"),  # cli.py:195 local import
    ("pipeline/state.py", "_merge_step_result"),  # chapter_loop.py local import
    ("pipeline/crash_recovery.py", "_check_emergency_flag"),  # chapter_loop.py wrapper call
}

SUPPRESSION_RE = re.compile(r"^\s*(?:async\s+)?def\s+(_?\w+)\(")

JUSTIFICATION_MIN_LEN = 20  # " -- called from ..." style comments


def main() -> int:
    """Run the frozen-allowlist check (see module docstring)."""
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for py in sorted(SRC.rglob("*.py")):
        rel = py.relative_to(SRC).as_posix()
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            m = SUPPRESSION_RE.search(line)
            if not m or "reportUnusedFunction" not in line:
                continue
            fn = m.group(1)
            seen.add((rel, fn))
            # Justification = text AFTER the ignore directive (PR #179 review:
            # counting the directive itself made the length check vacuous).
            parts = line.split("reportUnusedFunction]", 1)
            justification = parts[1].strip(" #:-") if len(parts) > 1 else ""
            if len(justification) < JUSTIFICATION_MIN_LEN:
                problems.append(
                    f"{rel}:{lineno}: {fn} suppression lacks justification after the directive"
                )
    for extra in sorted(seen - ALLOWLIST):
        problems.append(
            f"{extra[0]}: NEW reportUnusedFunction suppression on {extra[1]} — "
            "wire the caller for real, delete the function, or justify + update "
            "the frozen allowlist in tools/lint_dead_code_allowlist.py"
        )
    for missing in sorted(ALLOWLIST - seen):
        problems.append(
            f"{missing[0]}: allowlisted {missing[1]} no longer suppresses — "
            "shrink ALLOWLIST in tools/lint_dead_code_allowlist.py"
        )
    if problems:
        for p in problems:
            print(f"dead-code-allowlist: {p}", file=sys.stderr)
        return 1
    print(f"dead-code-allowlist: {len(ALLOWLIST)} justified suppressions, frozen set OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
