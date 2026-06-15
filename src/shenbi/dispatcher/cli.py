"""CLI entry point for dispatcher.

PR-20 (P-1.E): Python translation of tests/dispatch-subagent.sh main().
"""

import sys
from pathlib import Path

from shenbi.dispatcher.executor import dispatch
from shenbi.logging import configure_logging


def main():
    """Forward to dispatcher executor."""
    configure_logging()
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <skill_name> <test_type> <round_dir> [prompt]")
        return 1
    skill = sys.argv[1]
    test_type = sys.argv[2]
    round_dir = Path(sys.argv[3])
    prompt = sys.argv[4] if len(sys.argv) > 4 else ""
    return dispatch(skill, test_type, round_dir, prompt)


if __name__ == "__main__":
    sys.exit(main())
