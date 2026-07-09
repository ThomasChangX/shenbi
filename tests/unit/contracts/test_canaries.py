# tests/unit/contracts/test_canaries.py
"""The 7 canary regression tests (spec §8.2) — the sentinels.

This file is the single discoverable index for all 7 sentinels. The first six
canaries live next to the code they guard (better locality) and are *referenced*
here rather than re-imported — re-importing test objects causes pytest to collect
and run them twice (once at their canonical path, once here), which is wasteful
and obscures the real ownership. Run each sentinel at its canonical path, or run
this file to exercise sentinel 7 (the cross-layer seam) which is implemented here
because it spans multiple modules (g2, g4, the contract schema).

Each canary pins a previously-fixed bug so it cannot silently regress.

Sentinel index
--------------
1. ORPHAN_READ injection ........ tests/unit/tools/test_lint_contract_graph.py::test_detects_injected_orphan
2. N-corruption (SECTION/NPC) ... tests/unit/contracts/test_paths.py::TestResolveChapterPath::test_n_not_corrupted_mid_token_uppercase
                                   tests/unit/test_dispatcher_executor.py::test_section_path_not_corrupted
3. three-root .bak .............. tests/unit/test_round_paths.py::test_backup_same_root_as_write
4. field-match + fullwidth ...... tests/unit/contracts/test_fields.py::TestMatchField (match_field suite, incl. test_fullwidth_space_folded)
5. D16 G6.10 dead-path .......... tests/unit/gates/test_g6.py::test_g610_not_skipped_when_style_profile_exists
6. D19 G3.1 silent-skip ......... tests/unit/gates/test_g3.py::test_g31_does_not_silently_query_missing_key
7. Cross-layer seam ............. implemented below (this file)

A one-line verification that all six external sentinels still exist at their
documented paths is performed in ``TestSentinelIndex`` so this index cannot drift
out of sync with reality.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Sentinel 7 — the cross-layer seam canary
# ---------------------------------------------------------------------------
#
# §3 three-layer-stack claim: G2 (write gate), G4 (scoring gate), and the
# contract layer all validate ``decisions.json`` against ONE shared schema,
# ``DecisionsDoc`` (src/shenbi/contracts/schemas/decisions.py). Before the
# contract refactor, each gate hand-rolled its own checks, so a schema change
# could be applied in one place and forgotten in the others — the layers would
# silently disagree.
#
# This canary proves the layers genuinely share the single model by two
# independent means:
#
#   (a) STATIC — identity: the ``DecisionsDoc`` names imported by the g2 and g4
#       modules ARE the canonical class object (``is``), not copies or
#       re-declarations. If anyone reintroduces a local schema duplicate, this
#       identity assertion fails.
#   (b) DYNAMIC — shared mutation: we wrap ``DecisionsDoc.model_validate`` so a
#       previously-VALID doc is now REJECTED, then run that same doc through both
#       g2's decisions branch and g4's decisions validator. Because both call
#       ``DecisionsDoc.model_validate`` (they do not re-parse or short-circuit),
#       BOTH verdicts flip PASS → FAIL in lockstep. A gate that held a stale
#       private copy of the schema would keep returning PASS and break the lock.
#
# The lint layer (tools/lint_contracts.py, tools/lint_contract_graph.py) does
# NOT consume DecisionsDoc, so the cross-layer claim reduces to g2 + g4; this is
# documented rather than asserted.
from shenbi.contracts.schemas import decisions as decisions_schema
from shenbi.contracts.schemas.decisions import DecisionsDoc
from shenbi.gates import g2 as g2_module
from shenbi.gates.g2 import gate_G2
from shenbi.gates.g4 import decisions_validator as g4_decisions_module
from shenbi.gates.g4.decisions_validator import g4_decisions

_VALID_DECISIONS: dict[str, object] = {
    "$schema": "shenbi-decisions-v1",
    "skill": "shenbi-context-composing",
    "chapter": 5,
    "selections": [],
    "produced_at": "2026-07-08T00:00:00Z",
}


def _decisions_file(tmp_path: Path) -> Path:
    fp = tmp_path / "chapter-5-context-decisions.json"
    fp.write_text(json.dumps(_VALID_DECISIONS), encoding="utf-8")
    return fp


def _validation_error(loc: tuple[str, ...], msg: str) -> Exception:
    """Build a pydantic v2 ValidationError mirroring a model_validator fault.

    Both gate adapters (``decisions_err_to_g2_failures`` and
    ``pydantic_err_to_gate_failures``) iterate ``err.errors()``, so the
    constructed error must produce at least one error entry.
    """
    from pydantic import ValidationError

    return ValidationError.from_exception_data(
        "ValueError",
        [
            {
                "type": "value_error",
                "loc": loc,
                "input": None,
                "ctx": {"error": ValueError(msg)},
            }
        ],
    )


@pytest.mark.unit
class TestCrossLayerSeam:
    """Sentinel 7: g2 + g4 validate decisions.json through ONE shared DecisionsDoc."""

    def test_g2_and_g4_share_the_canonical_decisionsdoc(self) -> None:
        """Static identity: both gates' ``DecisionsDoc`` is the same object.

        Guards against a regression where a gate re-declares or copies the
        schema locally, which would let the layers drift out of sync.
        Access is via module attributes (not ``from ... import``) both because
        that is precisely the binding under test and to keep basedpyright's
        ``reportPrivateImportUsage`` quiet.
        """
        canonical = DecisionsDoc
        # Suppress reportPrivateImportUsage: verifying that each gate binds the
        # canonical (privately-imported) DecisionsDoc is the entire purpose of
        # this test — a non-identical binding would mean a duplicated schema.
        g2_doc = g2_module.DecisionsDoc  # pyright: ignore[reportPrivateImportUsage]
        g4_doc = g4_decisions_module.DecisionsDoc  # pyright: ignore[reportPrivateImportUsage]
        assert g2_doc is canonical, "g2 must bind the canonical DecisionsDoc"
        assert g4_doc is canonical, "g4 must bind the canonical DecisionsDoc"
        # Belt-and-braces: the canonical module and the schema module agree too.
        assert decisions_schema.DecisionsDoc is canonical

    def test_valid_doc_passes_both_gates(self, tmp_path: Path) -> None:
        """Baseline: the shared model accepts the canonical doc in both layers."""
        fp = _decisions_file(tmp_path)
        assert json.loads(g4_decisions([str(fp)]))["status"] == "PASS"
        assert json.loads(gate_G2([str(fp)], file_type="decisions"))["status"] == "PASS"

    def test_schema_mutation_flips_both_gates_in_lockstep(self, tmp_path: Path) -> None:
        """Dynamic proof: changing DecisionsDoc changes g2 AND g4 identically.

        We tighten ``model_validate`` to reject a doc the canonical schema
        accepts, then assert BOTH gates flip PASS → FAIL on the *same* input.
        This is only possible because each gate delegates to the shared model —
        a gate with a private schema copy would keep returning PASS.
        """
        fp = _decisions_file(tmp_path)

        # Pre-condition: both PASS under the real schema.
        assert json.loads(g4_decisions([str(fp)]))["status"] == "PASS"
        assert json.loads(gate_G2([str(fp)], file_type="decisions"))["status"] == "PASS"

        original_validate = DecisionsDoc.model_validate

        def rejecting_validate(data: object) -> DecisionsDoc:
            raise _validation_error(
                ("skill",),
                "sentinel-7: shared-schema mutation rejects this doc",
            )

        try:
            DecisionsDoc.model_validate = rejecting_validate  # type: ignore[method-assign]
            g4_status = json.loads(g4_decisions([str(fp)]))["status"]
            g2_status = json.loads(gate_G2([str(fp)], file_type="decisions"))["status"]
        finally:
            DecisionsDoc.model_validate = original_validate  # type: ignore[method-assign]

        # The lockstep flip is the whole point: both must move together.
        assert g4_status == "FAIL", (
            "g4 did not react to a DecisionsDoc change — it is NOT using the shared schema"
        )
        assert g2_status == "FAIL", (
            "g2 did not react to a DecisionsDoc change — it is NOT using the shared schema"
        )

    def test_consistent_failure_on_same_bad_input(self, tmp_path: Path) -> None:
        """A genuinely-invalid doc (bad chapter type) fails both gates.

        Complements the mutation test: this verifies the layers agree on a real
        schema violation, not only on an injected one.
        """
        bad = dict(_VALID_DECISIONS)
        bad["chapter"] = "not-an-int"  # DecisionsDoc.chapter is int
        fp = tmp_path / "chapter-5-context-decisions.json"
        fp.write_text(json.dumps(bad), encoding="utf-8")

        g4 = json.loads(g4_decisions([str(fp)]))
        g2 = json.loads(gate_G2([str(fp)], file_type="decisions"))

        assert g4["status"] == "FAIL"
        assert g2["status"] == "FAIL"
        # Both must surface a must_fix entry naming the offending field.
        assert g4["must_fix"], "g4 reported no fault for a bad chapter type"
        assert g2["must_fix"], "g2 reported no fault for a bad chapter type"


# ---------------------------------------------------------------------------
# Sentinel index integrity check
# ---------------------------------------------------------------------------

# (module_path, attribute) for each of the six externally-defined sentinels.
# If a sentinel is ever moved or renamed, this test fails loudly at runtime,
# keeping the module-docstring index honest.
_EXTERNAL_SENTINELS: tuple[tuple[str, str], ...] = (
    # 1. ORPHAN_READ injection
    ("tests.unit.tools.test_lint_contract_graph", "test_detects_injected_orphan"),
    # 2a. N-corruption — contract layer
    ("tests.unit.contracts.test_paths", "TestResolveChapterPath"),
    # 2b. N-corruption — dispatcher layer
    ("tests.unit.test_dispatcher_executor", "test_section_path_not_corrupted"),
    # 3. three-root .bak same-root
    ("tests.unit.test_round_paths", "test_backup_same_root_as_write"),
    # 4. field-match + fullwidth
    ("tests.unit.contracts.test_fields", "TestMatchField"),
    # 5. D16 G6.10 dead-path
    ("tests.unit.gates.test_g6", "test_g610_not_skipped_when_style_profile_exists"),
    # 6. D19 G3.1 silent-skip
    ("tests.unit.gates.test_g3", "test_g31_does_not_silently_query_missing_key"),
)


@pytest.mark.unit
def test_sentinel_index_references_real_tests() -> None:
    """Every sentinel documented above must resolve to a real test object.

    A rename or move without updating this index (or the module docstring) is a
    regression: the canary would silently stop guarding its bug.
    """
    missing: list[str] = []
    for module_path, attr in _EXTERNAL_SENTINELS:
        try:
            module = importlib.import_module(module_path)
            if not hasattr(module, attr):
                missing.append(f"{module_path}.{attr} (attribute missing)")
        except ImportError as exc:
            missing.append(f"{module_path} ({exc})")
    assert not missing, (
        "sentinel index is stale — the following references no longer resolve:\n  "
        + "\n  ".join(missing)
    )
