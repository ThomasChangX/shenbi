"""record_scorer_evidence: G3.4 scorer-evidence persistence.

Canary escalation #5 (2026-09-28): the API dispatch path had no writer for
progress.json:current_scorer_agent, so requires_independent_agent steps
failed G3.4 fail-closed deterministically. These tests pin the repair's
contract: evidence lands, G3.4 passes, existing keys survive (F630), and
the file is never a scorer-only shell (F1309).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.gates.g3_independence import scoring_independence_status
from shenbi.pipeline.dispatch_helper import record_scorer_evidence


@pytest.mark.unit
def test_writes_evidence_and_passes_g3_independence(tmp_path: Path) -> None:
    """Scorer route + generator routes land; G3.4 evaluates PASS."""
    record_scorer_evidence(
        tmp_path,
        scorer_route="genesis-dispatch:shenbi-foundation-review",
        generator_routes={
            "shenbi-worldbuilding": "genesis-dispatch:shenbi-worldbuilding",
            "shenbi-chapter-drafting": "genesis-dispatch:shenbi-chapter-drafting",
        },
        extra_progress={"phase": "genesis", "genesis_current_step": 17},
    )
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert progress["current_scorer_agent"] == "genesis-dispatch:shenbi-foundation-review"
    status, reason = scoring_independence_status(progress, "shenbi-foundation-review")
    assert status == "PASS", reason


@pytest.mark.unit
def test_merges_existing_progress_keys(tmp_path: Path) -> None:
    """Pre-existing chapter-phase keys survive a genesis-phase update (F630)."""
    (tmp_path / "progress.json").write_text(
        json.dumps({"chapter": 5, "chapters_done": [1, 2, 3, 4]}), encoding="utf-8"
    )
    record_scorer_evidence(
        tmp_path,
        scorer_route="genesis-dispatch:shenbi-foundation-review",
        generator_routes={"shenbi-worldbuilding": "genesis-dispatch:shenbi-worldbuilding"},
        extra_progress={"phase": "genesis"},
    )
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert progress["chapter"] == 5
    assert progress["chapters_done"] == [1, 2, 3, 4]
    assert progress["current_scorer_agent"] == "genesis-dispatch:shenbi-foundation-review"


@pytest.mark.unit
def test_extra_progress_prevents_scorer_only_shell(tmp_path: Path) -> None:
    """With real progress fields the file is not a scorer-only shell (F1309)."""
    # F1313 isolation: the contract check also flags a missing ledger once
    # progress.json exists; seed one non-empty row so only F1309 is asserted.
    (tmp_path / "cost").mkdir()
    (tmp_path / "cost" / "token-ledger.jsonl").write_text('{"total_tokens": 1}\n', encoding="utf-8")
    record_scorer_evidence(
        tmp_path,
        scorer_route="genesis-dispatch:shenbi-foundation-review",
        generator_routes={},
        extra_progress={"phase": "genesis", "genesis_current_step": 17},
    )
    from shenbi.pipeline.product_contracts import check_product_contracts

    assert check_product_contracts(tmp_path) == []


@pytest.mark.unit
def test_unreadable_progress_recovers_with_warning(tmp_path: Path) -> None:
    """Corrupt prior progress.json is replaced, not propagated (logged WARN)."""
    (tmp_path / "progress.json").write_text("{broken", encoding="utf-8")
    record_scorer_evidence(
        tmp_path,
        scorer_route="genesis-dispatch:shenbi-foundation-review",
        generator_routes={},
        extra_progress={"phase": "genesis"},
    )
    progress = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert progress["current_scorer_agent"] == "genesis-dispatch:shenbi-foundation-review"


@pytest.mark.unit
def test_audit_classification_is_directory_scoped() -> None:
    """Plans are not audits: chapter-NN-<dim> NAME shape must not trigger
    audit-verdict checks outside audits/ (canary escalation #9).
    """
    from shenbi.pipeline.dispatch_helper import _is_audit_file

    assert _is_audit_file("audits/chapter-8-foreshadowing.md") is True
    assert _is_audit_file("staging/audits/chapter-51-anti-ai.md") is True
    assert _is_audit_file("audits/chapter-8.aggregate.md") is False
    assert _is_audit_file("plans/chapter-1-plan.md") is False
    assert _is_audit_file("staging/plans/chapter-1-plan.md") is False
    assert _is_audit_file("staging/plans/chapter-1-plan-decisions.json") is False
    assert _is_audit_file("chapters/chapter-1.md") is False
