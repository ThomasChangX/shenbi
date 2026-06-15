"""CLI output utilities for emitting machine-readable data to stdout.

Separate from shenbi.logging (which is for stderr diagnostics):
- logging.* → stderr, human or JSON-format logs
- cli_utils.emit_json → stdout, parsed by downstream tools (shells, other CLIs)
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
    sys.stdout.write(json.dumps(data, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()
