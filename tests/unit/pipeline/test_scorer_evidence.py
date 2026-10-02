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


@pytest.mark.unit
def test_parameter_agent_match_is_token_level() -> None:
    """Descriptors containing a blacklisted char (冷静) don't trip the
    parameter-agent check; a standalone agent name does (canary ch1).
    """
    from shenbi.gates.g4.state_settling import _validate_character_matrix

    body_ok = "---\nfm\n---\n\n| 老头 | 登记人 | 存活 | 冷静、讳莫如深 | 起点 |\n"
    assert _validate_character_matrix(body_ok) == []
    body_agent = "---\nfm\n---\n\n| 冷 | 参数代理 | 活跃 | 无 | 第1章 |\n"
    assert _validate_character_matrix(body_agent) != []


@pytest.mark.unit
def test_json_manifest_envelope_recovery() -> None:
    """A {"files":[...]} manifest envelope (model deviation from the taught
    ### FILE: form) parses instead of failing with zero files (canary
    closure round, 2026-09-28). Validated against the real forensic dump.
    """
    from shenbi.pipeline.dispatch_helper import _parse_structured_output

    raw = '```json\n{"files":[{"path":"world/factions.md","content":"# F"}]}\n```'
    out = _parse_structured_output(raw)
    assert [f.path for f in out.files] == ["world/factions.md"]
    assert out.files[0].content == "# F"
    # taught envelope still wins when present
    out2 = _parse_structured_output("### FILE: a.md\nhello\n")
    assert [f.path for f in out2.files] == ["a.md"]
    # garbage stays empty (no false recovery)
    assert _parse_structured_output("no files here").files == []


@pytest.mark.unit
def test_json_manifest_envelope_recovers_control_chars() -> None:
    """probe14 genesis step 12 (2026-10-02): the model shipped a 39KB
    {"files":[...]} envelope whose content strings carry RAW newlines/
    control chars — RFC-illegal, so strict json.loads AND raw_decode both
    died with "Invalid control character" and 3 dispatches quarantined with
    zero files while the full artifact sat in quarantine. strict=False
    (literal control chars accepted inside strings) recovers it verbatim.
    Fixture = the real quarantine dump (G0.9).
    """
    from pathlib import Path

    from shenbi.pipeline.dispatch_helper import _parse_structured_output

    fixture = (
        Path(__file__).parents[2] / "fixtures" / "relationship-map-json-envelope-probe14.md"
    ).read_text(encoding="utf-8")
    # strip the quarantine wrapper's own header line
    raw = fixture[fixture.find("{") :]
    out = _parse_structured_output(raw)
    assert [f.path for f in out.files] == [
        "characters/relationships.md",
        "truth/character_matrix.md",
    ]
    assert "关系图谱" in out.files[0].content


@pytest.mark.unit
def test_json_manifest_envelope_recovers_with_trailing_junk() -> None:
    """Trailing text after the envelope must not block strict=False recovery
    (raw_decode takes the first complete object).
    """
    from shenbi.pipeline.dispatch_helper import _parse_structured_output

    raw = '{"files":[{"path":"a.md","content":"line1\nline2"}]}\n以上输出完成。'
    out = _parse_structured_output(raw)
    assert [f.path for f in out.files] == ["a.md"]
    assert out.files[0].content == "line1\nline2"
