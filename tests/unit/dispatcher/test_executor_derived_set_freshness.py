"""Spec #93 T4 — derived truth/decisions sets follow the registry stat key.

Editing truth-files.yaml mid-process must refresh the derived sets on the
next call (loader contract: (mtime_ns, size) keyed cache), not stay frozen
for the process lifetime.
"""

from __future__ import annotations

from pathlib import Path

import shenbi.contracts.loader as loader_mod
from shenbi.contracts import OutputKind  # defined in contracts/loader.py:42
import shenbi.dispatcher.executor as ex


def _write_registry(path: Path, truth_kind: str) -> None:
    # Real schema: concepts is a list of {name, kind} (docs/framework/truth-files.yaml)
    path.write_text(
        f"concepts:\n  - {{name: truth/current_state.md, kind: {truth_kind}}}\n",
        encoding="utf-8",
    )


def test_derived_set_refreshes_on_registry_edit(tmp_path: Path, monkeypatch) -> None:
    reg = tmp_path / "truth-files.yaml"
    _write_registry(reg, "truth")
    monkeypatch.setattr(loader_mod, "REGISTRY_PATH", reg)
    monkeypatch.setattr(
        ex,
        "load_contract",
        lambda skill: {
            "kind": OutputKind.ARTIFACT,
            "writes": {"truth/current_state.md"},
            "updates": set(),
        },
    )
    assert ex.derive_file_type("test-skill-writes") == "truth"
    # Same process, registry edited: kind truth -> decisions (size changes -> stat key changes)
    _write_registry(reg, "decisions")
    assert ex.derive_file_type("test-skill-writes") == "decisions"
