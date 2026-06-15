"""CLI entry point for gate validation.

P-1.D creates this module as the future entry point. Currently forwards to
the existing validate-gate.py by subprocess (the hyphenated filename prevents
direct import). Full modularization deferred to P-1.E.
"""

import subprocess
import sys
from pathlib import Path

VG_PATH = Path(__file__).resolve().parents[3] / "tests" / "validate-gate.py"


def main() -> int:
    """Forward to existing validate-gate.py CLI."""
    result = subprocess.run(
        [sys.executable, str(VG_PATH), *sys.argv[1:]],
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
