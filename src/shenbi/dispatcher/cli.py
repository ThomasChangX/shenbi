"""CLI entry point for dispatcher.

P-1.D creates this module as the future entry point.
Currently forwards to existing dispatch-subagent.sh shell script.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Forward to existing dispatch-subagent.sh."""
    script = Path(__file__).resolve().parents[3] / "tests" / "dispatch-subagent.sh"
    result = subprocess.run(["bash", str(script), *sys.argv[1:]])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
