"""shenbi-facts CLI——facts 查询面入口（spec #80 §1.1 T3）。

``shenbi-facts query --project <dir> --dim props|counters|identity [--chapter N]``
stdout=JSON（emit_json）；维缺席/空种子 → exit 1 + stderr WARN。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shenbi.cli_utils import echo, emit_json
from shenbi.facts.enums import FactsDim
from shenbi.facts.query import current_state
from shenbi.facts.store import load_facts
from shenbi.logging import get_logger

log = get_logger(__name__)

_FACTS_DIM_VALUES = tuple(dim.value for dim in FactsDim)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shenbi-facts", description="facts 查询面")
    sub = parser.add_subparsers(dest="command", required=True)
    query = sub.add_parser("query", help="现态紧凑查询（--as-of 历史态=P2）")
    query.add_argument("--project", required=True, help="novel project dir")
    query.add_argument("--dim", required=True, choices=_FACTS_DIM_VALUES, help="dimension")
    query.add_argument(
        "--chapter",
        type=int,
        default=None,
        help="relevance scoping (P1: full return; subset filtering lands in P2)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    project_dir = Path(args.project)
    dim = FactsDim(args.dim)
    file = load_facts(project_dir, dim)
    if file is None or file.is_empty:
        log.warning("facts_dim_absent_or_empty", dim=dim.value, project=str(project_dir))
        echo(
            f"WARN: facts dim '{dim.value}' absent or empty in {project_dir}"
            " — gate surface degrades to WARN (spec #80 F15/F16/F17 law)",
            err=True,
        )
        return 1
    emit_json(
        {
            "dim": dim.value,
            "facts": current_state(file, dim, chapter=args.chapter),
        }
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
