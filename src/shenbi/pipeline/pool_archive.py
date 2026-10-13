"""GO② rolling archival for the pending_hooks evidence pool.

Compatibility surface: the generic implementation lives in
:mod:`shenbi.pipeline.ledger_archive` (B 批参数化 — one archival engine,
both evidence ledgers). This module keeps the historical ``archive_pool``
entry point and the pool-only CLI so the driver protocol's
``just pool-archive`` contract is unchanged; the boundary chain's single
both-ledgers command is ``just ledger-archive``.

Usage::

    python -m shenbi.pipeline.pool_archive <project_dir> --resolved-through 94
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shenbi.pipeline import ledger_archive
from shenbi.pipeline.ledger_archive import POOL_SPEC, archive_ledger


def archive_pool(project_dir: Path, resolved_through: int) -> list[str]:
    """Back-compat entry point: delegate to the generic ledger archival."""
    return archive_ledger(project_dir, resolved_through, ledger_archive.POOL_SPEC)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "Pool archive").splitlines()[0])
    parser.add_argument("project_dir", type=str, help="novel project directory")
    parser.add_argument(
        "--resolved-through",
        type=int,
        required=True,
        help="archive hooks whose resolve_chapter is at/below this (keep-window applied by caller)",
    )
    args = parser.parse_args(argv)
    archived = archive_ledger(Path(args.project_dir), args.resolved_through, POOL_SPEC)
    sys.stdout.write(f"archived {len(archived)}: {', '.join(archived) or '-'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
