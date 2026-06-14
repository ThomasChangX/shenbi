"""CLI entry point for gate validation.

P-1.D creates this module as the future entry point.
Currently forwards to the existing validate-gate.py main().
"""

import sys


def main() -> int:
    """Forward to existing validate-gate.py CLI."""
    from tests import validate_gate

    result = validate_gate.main(); return int(result) if result else 0


if __name__ == "__main__":
    sys.exit(main())
