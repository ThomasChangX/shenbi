"""Product-contract checks for pipeline output artifacts (z11 SDD #20 R3).

Pure, read-only, idempotent: returns a list of violation descriptions.
Wired into chapter completion (chapter_loop._complete_chapter) FAIL-CLOSED;
the fix bodies for F640/F302 live in specs #27/#36 — this module only detects.
"""

import json
from pathlib import Path

from structlog import get_logger

log = get_logger(__name__)

_SCORER_SHELL_KEYS = {"current_scorer_agent", "scoring_history"}


def check_product_contracts(project_dir: Path) -> list[str]:
    """Detect product-contract violations (z11 F1309/F1313).

    - progress.json that carries only scorer fields = scorer-only shell (F1309)
    - missing/empty cost/token-ledger.jsonl (F1313); only checked once the
      project actually writes progress.json (bookkeeping started).
    """
    violations: list[str] = []
    progress = project_dir / "progress.json"
    if progress.exists():
        try:
            data = json.loads(progress.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            violations.append("progress.json: invalid JSON")
        else:
            if isinstance(data, dict) and set(data.keys()) <= _SCORER_SHELL_KEYS:
                violations.append("progress.json: scorer-only shell, no progress fields (F1309)")
        ledger = project_dir / "cost" / "token-ledger.jsonl"
        if not ledger.exists() or not ledger.read_text(encoding="utf-8").strip():
            violations.append("cost/token-ledger.jsonl missing or empty (F1313)")
    if violations:
        log.warning(
            "product_contract_violations", project_dir=str(project_dir), violations=violations
        )
    return violations
