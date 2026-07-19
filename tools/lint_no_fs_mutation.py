#!/usr/bin/env python3
"""Purity lint: forbid FS-mutation primitives in src/shenbi/ except allowlisted files.

Usage: python tools/lint_no_fs_mutation.py <root_dir>
exit 0 = pass; exit 1 = violations found.

Allowlist rationale:
  - safe_write.py: the atomic-write entry point (temp + os.replace + fsync).
  - trace/writer.py: TraceWriter does true append-only writes (.open("a") +
    per-line fsync). safe_write is temp+replace (full-file), incompatible.
  - cost/ledger.py: TokenLedger does append-only writes (.open("a") +
    per-line write). safe_write is temp+replace (full-file), incompatible.

Transitional allowlist: files not yet migrated to safe_write. Each entry is
verified by a test to contain actual violations (no dead entries). This list
MUST shrink as files migrate.

NOT detected (known limitations):
  - `from os import replace; replace(...)` (import-aliased calls; requires
    import tracking, out of scope for AST lint).
  - Dynamic open modes (non-constant mode arg; conservative skip).
  - os.open (low-level fd-based; only used in allowlisted safe_write).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# --- Allowlist ---

PERMANENT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "safe_write.py",
        "trace/writer.py",
        "cost/ledger.py",
    }
)

TRANSITIONAL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "skill_utils/drift_detection/compute_drift.py",
        "trace/compaction.py",
        "audit/record.py",
        "pipeline/checkpoint.py",
        "pipeline/chapter_loop.py",
    }
)

ALLOWED_FILES: frozenset[str] = PERMANENT_ALLOWLIST | TRANSITIONAL_ALLOWLIST

# --- Detection constants ---

_OS_MUTATIONS = frozenset(
    {
        "replace",
        "rename",
        "unlink",
        "remove",
        "rmdir",
        "removedirs",
    }
)

_SHUTIL_MUTATIONS = frozenset(
    {
        "copy",
        "copy2",
        "copyfile",
        "move",
        "rmtree",
        "copytree",
    }
)

_PATH_WRITE_METHODS = frozenset({"write_text", "write_bytes", "unlink"})

_WRITE_CHARS = frozenset("wax")


def _is_write_mode(mode_arg: ast.expr | None) -> bool:
    """True if a mode arg is a string constant containing w/a/x."""
    if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
        return bool(_WRITE_CHARS & set(mode_arg.value))
    return False


def _extract_mode(call: ast.Call, is_method: bool) -> ast.expr | None:
    """Extract the mode argument from an open() call.

    Path.open(mode): mode is args[0].
    builtin open(file, mode): mode is args[1].
    Keyword 'mode=' checked for both.
    """
    for kw in call.keywords:
        if kw.arg == "mode":
            return kw.value
    idx = 0 if is_method else 1
    if len(call.args) > idx:
        return call.args[idx]
    return None


def _find_violations(tree: ast.Module, filepath: Path) -> list[str]:
    """Walk AST, return violation messages for FS-mutation primitives."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func

        if isinstance(func, ast.Attribute):
            attr = func.attr

            # .write_text() / .write_bytes() / .unlink()
            if attr in _PATH_WRITE_METHODS:
                violations.append(f"{filepath}:{node.lineno}: forbidden FS-mutation: .{attr}()")
                continue

            # .open(mode) with write/append mode
            if attr == "open":
                if _is_write_mode(_extract_mode(node, is_method=True)):
                    violations.append(
                        f"{filepath}:{node.lineno}: forbidden FS-mutation: "
                        f".open() in write/append mode"
                    )
                continue

            # os.<mutation> or shutil.<mutation>
            if isinstance(func.value, ast.Name):
                mod = func.value.id
                if mod == "os" and attr in _OS_MUTATIONS:
                    violations.append(
                        f"{filepath}:{node.lineno}: forbidden FS-mutation: os.{attr}()"
                    )
                elif mod == "shutil" and attr in _SHUTIL_MUTATIONS:
                    violations.append(
                        f"{filepath}:{node.lineno}: forbidden FS-mutation: shutil.{attr}()"
                    )

        # builtin open(file, mode)
        elif isinstance(func, ast.Name) and func.id == "open":
            if _is_write_mode(_extract_mode(node, is_method=False)):
                violations.append(
                    f"{filepath}:{node.lineno}: forbidden FS-mutation: open() in write/append mode"
                )

    return violations


def lint_dir(root: Path) -> list[str]:
    """Lint all .py under root, skipping allowlisted files.

    File identity is the posix relative path from root (e.g. 'gates/shared.py').
    """
    all_violations: list[str] = []
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root).as_posix()
        if rel in ALLOWED_FILES:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        all_violations.extend(_find_violations(tree, py))
    return all_violations


EXPECTED_ARGS = 2


def main() -> int:
    """Print violations and exit non-zero if any were found."""
    if len(sys.argv) != EXPECTED_ARGS:
        print("usage: lint_no_fs_mutation.py <path>", file=sys.stderr)
        return 2
    vs = lint_dir(Path(sys.argv[1]))
    for v in vs:
        print(v, file=sys.stderr)
    return 1 if vs else 0


if __name__ == "__main__":
    sys.exit(main())
