"""Unit tests for dispatcher/executor.py happy paths."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from shenbi.dispatcher.executor import (
    derive_file_type,
    derive_input_files,
    derive_output_files,
    detect_mode,
    generate_agent_id,
)


@pytest.mark.unit
def test_derive_file_type_returns_decisions_for_drafting() -> None:
    """Task 10: chapter-drafting now writes chapter-N-decisions.json -> 'decisions'."""
    assert derive_file_type("shenbi-chapter-drafting") == "decisions"


@pytest.mark.unit
def test_derive_file_type_returns_truth_for_state_settling() -> None:
    assert derive_file_type("shenbi-state-settling") == "truth"


@pytest.mark.unit
def test_derive_file_type_defaults_to_chapter_for_unknown() -> None:
    assert derive_file_type("shenbi-unknown-skill") == "chapter"


@pytest.mark.unit
def test_derive_file_type_returns_truth_for_foreshadowing_resolve() -> None:
    """New-I fix: resolve updates truth/pending_hooks.md -> 'truth' (not 'chapter').

    Old hardcoded truth_skills set (executor.py:39-43) missed resolve, so G2 ran
    chapter word-count validation on a truth-file edit. derive now joins contract
    OutputKind + truth-files.yaml concepts.
    """
    assert derive_file_type("shenbi-foreshadowing-resolve") == "truth"


@pytest.mark.unit
def test_derive_file_type_returns_report_for_report_kind_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REPORT OutputKind -> 'report'."""
    import shenbi.dispatcher.executor as exec_mod
    from shenbi.contracts import OutputKind

    monkeypatch.setattr(
        exec_mod,
        "load_contract",
        lambda s: {
            "kind": OutputKind.REPORT,
            "reads": [],
            "writes": ["audits/r.md"],
            "updates": [],
            "read_fields": {},
        },
    )
    assert derive_file_type("shenbi-review-arc-payoff") == "report"


@pytest.mark.unit
def test_derive_file_type_returns_chapter_for_ephemeral_skill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EPHEMERAL has no persisted output -> default 'chapter' (G2 skipped upstream)."""
    import shenbi.dispatcher.executor as exec_mod
    from shenbi.contracts import OutputKind

    monkeypatch.setattr(
        exec_mod,
        "load_contract",
        lambda s: {
            "kind": OutputKind.EPHEMERAL,
            "reads": [],
            "writes": [],
            "updates": [],
            "read_fields": {},
        },
    )
    assert derive_file_type("shenbi-ephemeral") == "chapter"


@pytest.mark.unit
def test_derive_files_delegate_to_contract_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    """derive_input_files/derive_output_files delegate to load_contract (no regex)."""
    monkeypatch.setattr(
        "shenbi.dispatcher.executor.load_contract",
        lambda s: {
            "kind": "artifact",
            "reads": ["plans/chapter-N-plan.md"],
            "writes": ["chapters/chapter-N.md"],
            "updates": ["truth/current_state.md"],
        },
    )
    assert derive_input_files("shenbi-x", chapter=1) == ["plans/chapter-1-plan.md"]
    # writes + updates both fold into output files
    assert derive_output_files("shenbi-x", chapter=1) == [
        "chapters/chapter-1.md",
        "truth/current_state.md",
    ]


@pytest.mark.unit
def test_derive_files_empty_when_skill_has_no_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    """A skill outside the contract system (meta skill) raises ContractError -> []."""
    from shenbi.contracts import ContractError

    def raise_contract_error(_skill: str) -> None:
        raise ContractError("no contract")

    monkeypatch.setattr("shenbi.dispatcher.executor.load_contract", raise_contract_error)
    assert derive_input_files("using-shenbi") == []
    assert derive_output_files("using-shenbi") == []


@pytest.mark.unit
def test_derive_files_read_real_migrated_skill_contract() -> None:
    """Post-migration, derive_* read the real frontmatter contract end-to-end."""
    # chapter=None filters N/NNN placeholders (genesis mode); pass chapter number
    # to resolve them for this test.
    assert derive_input_files("shenbi-chapter-drafting", chapter=1) == [
        "plans/chapter-1-plan.md",
        "context/chapter-1-context.md",
        "context/chapter-1-context-decisions.json",
        "style/style_profile.md",
        "genre-config.json",
        "truth/audit_drift.md",
    ]
    # shenbi-state-settling: writes a decisions sidecar + updates=7 truth files (all fold into outputs)
    assert derive_output_files("shenbi-state-settling") == [
        "truth/state-settling-decisions.json",
        "truth/current_state.md",
        "truth/particle_ledger.md",
        "truth/character_matrix.md",
        "truth/emotional_arcs.md",
        "truth/subplot_board.md",
        "truth/pending_hooks.md",
        "truth/chapter_summaries.md",
    ]


@pytest.mark.unit
def test_generate_agent_id_is_unique() -> None:
    round_dir = Path("/tmp/round-001")
    id1 = generate_agent_id(round_dir, "skill-x", "generative")
    id2 = generate_agent_id(round_dir, "skill-x", "generative")
    assert id1 != id2
    assert "skill-x" in id1
    assert "generative" in id1


@pytest.mark.unit
def test_generate_agent_id_contains_round_dir_name() -> None:
    round_dir = Path("/tmp/round-042")
    agent_id = generate_agent_id(round_dir, "skill-y", "discriminating")
    assert "round-042" in agent_id


@pytest.mark.unit
def test_detect_mode_returns_internal_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """detect_mode returns 'internal' when no IDE CLI is available.

    On developer machines with codex CLI installed, detect_mode() returns 'codex'.
    Mock shutil.which to simulate an environment without any IDE CLI.
    """
    monkeypatch.setattr(shutil, "which", lambda _x: None)
    assert detect_mode() == "internal"


@pytest.mark.unit
def test_detect_mode_returns_internal_with_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """detect_mode returns 'internal' even when CODEX_API_KEY is set."""
    monkeypatch.setenv("CODEX_API_KEY", "sk-test-key")
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    assert detect_mode() == "internal"


@pytest.mark.unit
def test_detect_mode_returns_internal_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """detect_mode returns 'internal' when neither codex nor env var is available."""
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    monkeypatch.delenv("CODEX_API_KEY", raising=False)
    from shenbi.dispatcher.executor import detect_mode as dm

    assert dm() == "internal"


@pytest.mark.unit
def test_run_g1_returns_parsed_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_g1 parses subprocess stdout JSON into a dict."""
    import subprocess

    def mock_run(*a, **kw):
        return type("R", (), {"stdout": '{"status": "PASS"}'})()

    monkeypatch.setattr(subprocess, "run", mock_run)
    from shenbi.dispatcher.executor import run_g1

    result = run_g1("skill-x", [], Path("/tmp"))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_run_g2_returns_parsed_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_g2 parses subprocess stdout JSON into a dict."""
    import subprocess

    def mock_run(*a, **kw):
        return type("R", (), {"stdout": '{"status": "PASS"}'})()

    monkeypatch.setattr(subprocess, "run", mock_run)
    from shenbi.dispatcher.executor import run_g2

    result = run_g2(["out.md"], "chapter", Path("/tmp"))
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_dispatch_returns_0_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch returns 0 when all gates pass and internal mode succeeds."""
    import subprocess
    from pathlib import Path

    def mock_run(*a, **kw):
        return type("R", (), {"stdout": '{"status": "PASS"}'})()

    monkeypatch.setattr(subprocess, "run", mock_run)

    import shenbi.dispatcher.executor as exec_mod
    from shenbi.dispatcher.executor import dispatch

    monkeypatch.setattr(exec_mod, "detect_mode", lambda: "internal")

    import shenbi.dispatcher.modes.internal as internal_mod

    monkeypatch.setattr(internal_mod, "dispatch_internal", lambda *a, **kw: 0)

    result = dispatch("shenbi-worldbuilding", "generative", Path("/tmp/round-001"), "test")
    assert result == 0


@pytest.mark.unit
def test_dispatch_routes_to_codex_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatch routes to codex-api mode when detect_mode returns 'codex-api'."""
    import subprocess
    from pathlib import Path

    import shenbi.dispatcher.executor as exec_mod
    import shenbi.dispatcher.modes.codex_api as codex_api_mod

    def mock_run(*a, **kw):
        return type("R", (), {"stdout": '{"status": "PASS"}'})()

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(exec_mod, "detect_mode", lambda: "codex-api")
    monkeypatch.setattr(codex_api_mod, "dispatch_codex_api", lambda *a, **kw: 0)

    from shenbi.dispatcher.executor import dispatch

    result = dispatch("shenbi-worldbuilding", "generative", Path("/tmp/round-001"), "test")
    assert result == 0


@pytest.mark.unit
def test_resolve_chapter_path_with_chapter() -> None:
    """_resolve_chapter_path resolves N/NNN with chapter number."""
    from shenbi.dispatcher.executor import _resolve_chapter_path

    assert _resolve_chapter_path("chapters/chapter-N.md", 5) == "chapters/chapter-5.md"
    assert _resolve_chapter_path("chapters/chapter-NNN.md", 5) == "chapters/chapter-005.md"
    assert _resolve_chapter_path("no-placeholder.md", 5) == "no-placeholder.md"


@pytest.mark.unit
def test_resolve_chapter_path_none_sentinel() -> None:
    """_resolve_chapter_path returns '' sentinel when chapter=None and N present."""
    from shenbi.dispatcher.executor import _resolve_chapter_path

    assert _resolve_chapter_path("chapters/chapter-N.md", None) == ""
    assert _resolve_chapter_path("chapters/chapter-NNN.md", None) == ""
    assert _resolve_chapter_path("no-placeholder.md", None) == "no-placeholder.md"


@pytest.mark.unit
def test_derive_input_files_with_chapter_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """derive_input_files resolves NNN placeholders when chapter is provided."""
    monkeypatch.setattr(
        "shenbi.dispatcher.executor.load_contract",
        lambda s: {
            "kind": "artifact",
            "reads": ["plans/chapter-NNN-plan.md", "style/style_profile.md"],
            "writes": [],
            "updates": [],
        },
    )
    result = derive_input_files("shenbi-x", chapter=3)
    assert "plans/chapter-003-plan.md" in result
    assert "style/style_profile.md" in result


@pytest.mark.unit
def test_derive_input_files_filter_empty_sentinels(monkeypatch: pytest.MonkeyPatch) -> None:
    """derive_input_files filters empty sentinels when chapter=None (genesis mode)."""
    monkeypatch.setattr(
        "shenbi.dispatcher.executor.load_contract",
        lambda s: {
            "kind": "artifact",
            "reads": ["plans/chapter-N-plan.md"],
            "writes": [],
            "updates": [],
        },
    )
    assert derive_input_files("shenbi-x", chapter=None) == []


@pytest.mark.unit
def test_derive_file_type_returns_decisions_for_context_composing_after_migration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After context-composing migrates to kind=artifact with decisions.json writes,
    derive_file_type returns 'decisions'.
    """
    from shenbi.contracts import OutputKind

    monkeypatch.setattr(
        "shenbi.dispatcher.executor.load_contract",
        lambda s: {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": ["context/chapter-N-context-decisions.json"],
            "updates": [],
            "read_fields": {},
        },
    )
    assert derive_file_type("shenbi-context-composing") == "decisions"


@pytest.mark.unit
def test_derive_file_type_returns_decisions_for_chapter_drafting_after_migration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """chapter-drafting writes both chapter-N.md AND chapter-N-decisions.json.
    When it writes a decisions file, derive_file_type returns 'decisions'.
    """
    from shenbi.contracts import OutputKind

    monkeypatch.setattr(
        "shenbi.dispatcher.executor.load_contract",
        lambda s: {
            "kind": OutputKind.ARTIFACT,
            "reads": [],
            "writes": ["chapters/chapter-N.md", "chapters/chapter-N-decisions.json"],
            "updates": [],
            "read_fields": {},
        },
    )
    assert derive_file_type("shenbi-chapter-drafting") == "decisions"
