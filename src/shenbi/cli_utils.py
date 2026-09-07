"""CLI output utilities for emitting machine-readable data to stdout.

Separate from shenbi.logging (which is for stderr diagnostics):
- logging.* → stderr, human or JSON-format logs
- cli_utils.emit_json → stdout, parsed by downstream tools (shells, other CLIs)
- cli_utils.echo → stdout (or stderr with err=True), human-facing text
"""

import json
import sys
from typing import Any


def emit_json(data: Any) -> None:
    """Emit JSON to stdout for downstream parsing.

    Used by gate/scoring CLIs that produce JSON output consumed by shell
    pipelines or other tools. Distinct from structlog logging which goes
    to stderr.
    """
    try:
        sys.stdout.write(json.dumps(data, ensure_ascii=False))
        sys.stdout.write("\n")
        sys.stdout.flush()
    except BrokenPipeError:
        # Downstream consumer (head/pipe) closed early — not an error worth a traceback (F160).
        raise SystemExit(0) from None


def echo(msg: str, *, err: bool = False) -> None:
    """Write a human-facing message to stdout (or stderr with err=True).

    Mirrors emit_json's durability semantics: flush, and a closed pipe
    (e.g. piped into head) exits cleanly rather than tracebacking.
    """
    stream = sys.stderr if err else sys.stdout
    try:
        stream.write(msg + "\n")
        stream.flush()
    except BrokenPipeError:
        raise SystemExit(0) from None
