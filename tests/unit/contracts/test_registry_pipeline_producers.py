# tests/unit/contracts/test_registry_pipeline_producers.py
"""Pipeline-producer registration (Task 17 / D20).

The ``producer`` field on ``RegistryConcept`` lets the closure check (Task 18)
distinguish skill-produced / pipeline-produced / external-seed / shared files, so
pipeline-written files are not falsely reported as orphan reads. This test pins
the phase-0 inventory: pipeline-only files carry ``producer: pipeline`` (or
``shared`` when a skill also writes them), external seeds carry ``external``,
and the D20 snapshot vocabulary is finalized (spec #57 T4): the skill-domain
directory layout ``snapshots/chapter-NNN/`` is covered by glob, the
crash_recovery emergency flatfile ``snapshots/chapter-N-emergency.md`` is a
registered concept, and ``snapshots/manifest.json`` is a drift marker.
"""

from __future__ import annotations

from shenbi.contracts.loader import load_registry

# Pipeline-only files the pipeline writes directly (no skill producer).
# Each must resolve to a concept whose producer is pipeline (or shared when a
# skill co-writes the same path).
PIPELINE_PRODUCED = {
    "context/chapter-N-context.md",
    "snapshots/manifest.json",
    "truth-index.json",
    "pipeline-state.json",
    "audits/chapter-N-review-summary.md",
}

# External seeds: author/seed-supplied read-only inputs (no skill producer).
EXTERNAL_SEEDS = {
    "era-reference.md",
    "import/source/*.txt",
    "source_canon/*",
    "benchmarks/anchors/",
}

# Shared: both a skill and the pipeline write the same path.
SHARED = {
    "novel.json",
    "genre-config.json",
}

# D20 snapshot vocabulary — finalized spec #57 T4:
# - skill domain: snapshots/chapter-NNN/ (snapshot-manage writes, sequel-writing
#   reads) — covered by glob `snapshots/chapter-*/*`, no concept entry needed.
# - emergency domain: snapshots/chapter-N-emergency.md (crash_recovery
#   _snapshot_chapter_files, label always "emergency") — registered concept.
D20_EMERGENCY_FLATFILE = "snapshots/chapter-N-emergency.md"
D20_SKILL_DIR_WRITE = "snapshots/chapter-NNN/*"


def _concept(reg, name: str):
    return next((c for c in reg.concepts if c.name == name), None)


def test_registry_loads() -> None:
    # The registry must still load via the Task 6 model after producer fields land.
    reg = load_registry()
    assert len(reg.concepts) > 0


def test_pipeline_files_marked_pipeline_producer() -> None:
    reg = load_registry()
    for name in PIPELINE_PRODUCED:
        concept = _concept(reg, name)
        assert concept is not None, f"{name} not in registry"
        assert concept.producer in {"pipeline", "shared"}, f"{name} producer={concept.producer}"


def test_external_seeds_marked_external_producer() -> None:
    reg = load_registry()
    for name in EXTERNAL_SEEDS:
        concept = _concept(reg, name)
        assert concept is not None, f"{name} not in registry"
        assert concept.producer == "external", f"{name} producer={concept.producer}"


def test_shared_files_marked_shared_producer() -> None:
    reg = load_registry()
    for name in SHARED:
        concept = _concept(reg, name)
        assert concept is not None, f"{name} not in registry"
        assert concept.producer == "shared", f"{name} producer={concept.producer}"


def test_d20_emergency_flatfile_registered() -> None:
    # D20: crash_recovery emergency snapshot must be a registered concept
    # (the only src/ snapshot writer after spec #26 path 3).
    reg = load_registry()
    concept = _concept(reg, D20_EMERGENCY_FLATFILE)
    assert concept is not None, f"{D20_EMERGENCY_FLATFILE} not registered (D20)"
    assert concept.kind == "snapshot"
    assert concept.producer == "pipeline"


def test_d20_skill_dir_no_concept_entry_needed() -> None:
    # D20 (spec #57 T4): the skill-domain directory layout snapshots/chapter-NNN/
    # is legitimate (snapshot-manage writes, sequel-writing reads) and is
    # covered by the glob `snapshots/chapter-*/*`; it intentionally has no
    # per-file concept entry.
    reg = load_registry()
    assert _concept(reg, D20_SKILL_DIR_WRITE) is None
    assert _concept(reg, "snapshots/manifest.json") is not None
    assert any(
        getattr(g, "pattern", g) == "snapshots/chapter-*/*" for g in getattr(reg, "globs", [])
    ), "skill-domain glob missing"


def test_default_producer_is_skill_for_truth_concepts() -> None:
    # Sanity: most truth concepts remain skill-produced (default), so the new
    # field does not accidentally flip the majority to a non-default producer.
    # The only non-skill truth concepts are the pipeline-managed index/store
    # (truth-index.json, truth-embeddings.db).
    reg = load_registry()
    truth = [c for c in reg.concepts if c.kind == "truth"]
    assert truth, "expected truth concepts"
    non_skill = [c for c in truth if c.producer != "skill"]
    assert {c.name for c in non_skill} == {
        "truth-index.json",
        "truth-embeddings.db",
        "truth/chapter_patterns.md",
        "truth/resonance_anchors.md",
    }, f"unexpected non-skill truth producers: {sorted(c.name for c in non_skill)}"
