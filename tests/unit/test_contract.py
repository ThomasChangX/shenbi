"""contract.load_contract: one loader, schema-validated, registry-resolved."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.contracts import ContractError, OutputKind, load_contract

# A minimal registry the test paths resolve against. Tests monkeypatch
# shenbi.contracts.legacy.REGISTRY_PATH to this tmp file, so they are fully isolated
# from the real docs/framework/truth-files.yaml (authored in Task 5).
_TEST_REGISTRY = (
    "concepts:\n"
    "  - {name: plans/chapter-N-plan.md, kind: plan}\n"
    "  - {name: chapters/chapter-N.md, kind: chapter}\n"
    "patterns:\n"
    "  - {parametric: plans/chapter-N-plan.md, glob: plans/chapter-*-plan.md}\n"
    "  - {parametric: chapters/chapter-N.md, glob: chapters/chapter-*.md}\n"
    "globs: []\n"
)


def _setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, body: str) -> None:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    reg = tmp_path / "registry.yaml"
    reg.write_text(_TEST_REGISTRY, encoding="utf-8")
    monkeypatch.setattr("shenbi.contracts.legacy.SKILLS", tmp_path)
    monkeypatch.setattr("shenbi.contracts.legacy.REGISTRY_PATH", reg)


@pytest.mark.unit
def test_valid_artifact_contract_loads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-x",
        "---\n"
        "name: shenbi-x\ndescription: Use when x\n"
        "contract:\n  kind: artifact\n  reads:\n    - plans/chapter-N-plan.md\n"
        "  writes:\n    - chapters/chapter-N.md\n  updates: []\n"
        "---\n\n# Body\n",
    )
    c = load_contract("shenbi-x")
    assert c["kind"] is OutputKind.ARTIFACT
    assert c["writes"] == ["chapters/chapter-N.md"]


@pytest.mark.unit
def test_prose_writes_report_only_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Layer C root cause: 'report only' is not a list -> ContractError."""
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-bad",
        "---\nname: shenbi-bad\ndescription: Use when bad\n"
        "contract:\n  kind: report\n  reads: []\n  writes: report only\n  updates: []\n"
        "---\n\n# Body\n",
    )
    with pytest.raises(ContractError):
        load_contract("shenbi-bad")


@pytest.mark.unit
def test_invalid_kind_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-bad",
        "---\nname: shenbi-bad\ndescription: x\n"
        "contract:\n  kind: wat\n  reads: []\n  writes: []\n  updates: []\n"
        "---\n\n# Body\n",
    )
    with pytest.raises(ContractError):
        load_contract("shenbi-bad")


@pytest.mark.unit
def test_non_list_reads_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-bad",
        "---\nname: shenbi-bad\ndescription: x\n"
        "contract:\n  kind: artifact\n  reads: chapters/chapter-N.md\n  writes: []\n  updates: []\n"
        "---\n\n# Body\n",
    )
    with pytest.raises(ContractError):
        load_contract("shenbi-bad")


@pytest.mark.unit
def test_unregistered_path_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _setup(
        monkeypatch,
        tmp_path,
        "shenbi-bad",
        "---\nname: shenbi-bad\ndescription: x\n"
        "contract:\n  kind: artifact\n  reads:\n    - totally/made/up.md\n"
        "  writes: []\n  updates: []\n---\n\n# Body\n",
    )
    with pytest.raises(ContractError):
        load_contract("shenbi-bad")


@pytest.mark.unit
def test_missing_skill_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reg = tmp_path / "registry.yaml"
    reg.write_text(_TEST_REGISTRY, encoding="utf-8")
    monkeypatch.setattr("shenbi.contracts.legacy.SKILLS", tmp_path)
    monkeypatch.setattr("shenbi.contracts.legacy.REGISTRY_PATH", reg)
    with pytest.raises(ContractError):
        load_contract("shenbi-nope")


def test_load_registry_still_returns_truth_files_vocab() -> None:
    """Transition period: load_registry still contains truth-files.yaml concepts.

    v2 C2: iterate reg['concepts'] names, not top-level keys.
    Task 10: load_registry now returns a TruthFilesRegistry model; concepts are
    accessed as model attributes (``reg.concepts`` / ``c.name``).
    """
    from shenbi.contracts import load_registry
    from shenbi.contracts.schemas.registry import TruthFilesRegistry

    reg = load_registry()
    assert isinstance(reg, TruthFilesRegistry)
    concepts = reg.concepts
    assert any("pending_hooks" in c.name for c in concepts)


def test_contracts_registry_coexists_with_contract_py() -> None:
    """Two-source coexistence: contract.py (unmigrated) + contracts.REGISTRY (migrated)."""
    from shenbi.contracts import REGISTRY

    assert "shenbi-foreshadowing-resolve" in REGISTRY
    from shenbi.contracts import load_contract

    c = load_contract("shenbi-worldbuilding")  # unmigrated, uses TypedDict
    assert c is not None


@pytest.mark.unit
class TestDecisionsRegistryPaths:
    """Integration-style: resolve decisions.json paths against the REAL registry.

    Unlike the _setup()-based tests above, these hit the authored
    docs/framework/truth-files.yaml so that a missing registration fails here
    (the authoring decision point that prevents silent synonym creation).
    """

    def test_context_decisions_json_resolves(self) -> None:
        from shenbi.contracts.legacy import load_registry, resolves

        registry = load_registry()
        assert resolves("context/chapter-N-context-decisions.json", registry)

    def test_chapter_decisions_json_resolves(self) -> None:
        from shenbi.contracts.legacy import load_registry, resolves

        registry = load_registry()
        assert resolves("chapters/chapter-N-decisions.json", registry)

    def test_decisions_kind_in_registry(self) -> None:
        from shenbi.contracts.registry import bootstrap_registry

        reg = bootstrap_registry()
        assert reg.get("context/chapter-N-context-decisions.json") == "decisions"
        assert reg.get("chapters/chapter-N-decisions.json") == "decisions"
