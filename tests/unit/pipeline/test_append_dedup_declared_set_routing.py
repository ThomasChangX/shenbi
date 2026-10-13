"""T6 guard: EVERY declared append_dedup (skill, path) routes through upsert (C3).

The declared surface is MECHANICALLY EXTRACTED from the live
``skills/*/SKILL.md`` frontmatter via the production contract loader — no
hardcoded pair list. A skill newly declaring ``mode: append_dedup`` enters the
test surface automatically; a pair quietly disappearing is caught by the
explicit snapshot-count assertion below (updating that number is then a
conscious act, not a silent shrink).

Per pair, the behavioral pin of the Task-2/5 routing: dispatching an increment
for key A then an increment for key B must leave BOTH rows in the file — the
pre-fix whole-file write collapsed the file to B's increment (audit F1104/F1105
data loss). A re-dispatch of the same key replaces its row in place (exactly
one row per key). The write path under test is the real
``_write_parsed_outputs`` → ``_route_append_dedup_write`` → truth_io upsert
chain with the real contract loaded; only the LLM text is the test's own.

Guard validity (verified while developing, see task-6-report.md): against the
pre-routing BASE commit 7de2360 the parametrized guard FAILS (history collapses
to the last increment; BASE also carries drift-guidance's since-removed
append_dedup declaration, so the snapshot count reads 18 there), and
short-circuiting ``_route_append_dedup_write`` to the legacy whole-file write
on current HEAD fails all 17 parametrized cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.contracts import ContractError, load_contract
from shenbi.gates.shared import SKILLS as _SKILLS_DIR
from shenbi.pipeline.dispatch_helper import _write_parsed_outputs


def _declared_append_dedup_pairs() -> list[tuple[str, str, str]]:
    """(skill, contract_path, key) for every append_dedup declaration.

    Extracted mechanically from the frontmatter contracts through the same
    loader the dispatcher uses at runtime (``load_contract`` — the
    loader-uniqueness lint forbids any second frontmatter reader), so the test
    surface can never drift from what production actually routes on. Skills
    without a contract block (the two meta skills) are skipped; contract
    VALIDITY failures are owned by tools/lint_contracts.py in ``just check``.
    """
    pairs: list[tuple[str, str, str]] = []
    for skill_md in sorted(_SKILLS_DIR.glob("*/SKILL.md")):
        skill = skill_md.parent.name
        try:
            contract = load_contract(skill)
        except ContractError:
            continue
        for path, meta in contract["write_semantics"].items():
            if meta.get("mode") == "append_dedup":
                pairs.append((skill, path, str(meta.get("key") or "chapter")))
    return pairs


_PAIRS = _declared_append_dedup_pairs()


def test_declared_surface_snapshot_count() -> None:
    """Explicit snapshot of the declared surface: 24 (skill, path) pairs —
    17 as of the C3 T6 guard (10 skills; state-settling owns 6 targets) + 1
    from spec #58 C20 (foreshadowing-lifecycle bridge_tracker, F825) + 1
    from the probe2 settle capacity fix (state-settling character_matrix,
    composite key 角色A,角色B — the whole-file rewrite contract made settle
    output grow O(chapters) past the model output cap) + 2 from the A1
    千万字卷层批 (volume-outlining volume_map / plot-thread-weaver
    thread_map — whole-file rewrites pinned the output cap as the ledgers
    grew ~10KB/volume) + 3 from the A2 section-ledger 批 (location-builder
    locations / relationship-map relationships + character_matrix — the
    ~50-volume whole-file rewrite walls). This is the anti-silent-shrink
    tripwire — the parametrized guard below adapts to any future growth
    automatically, but a REMOVED declaration must surface here so it
    cannot pass unnoticed. Updating this number is the explicit action.
    """
    assert len(_PAIRS) == 24, (
        "declared append_dedup surface changed — if intentional, update the "
        f"snapshot (currently {len(_PAIRS)} pairs: {_PAIRS})"
    )


def test_every_declared_target_is_truth_routed() -> None:
    """Structural precondition: append_dedup routes under ``truth/`` or the
    A1 keyed-outline allowlist — any declaration outside BOTH would silently
    fall back to the legacy whole-file write (data loss with a declared
    dedup contract).
    """
    from shenbi.pipeline.dispatch_helper import _KEYED_OUTLINE_TARGETS

    for skill, path, _key in _PAIRS:
        assert path.startswith("truth/") or path in _KEYED_OUTLINE_TARGETS, (
            f"{skill} declares append_dedup with no merge route: {path} "
            "(unroutable — falls back to whole-file write)"
        )


@pytest.mark.parametrize(
    ("skill", "path", "key"),
    _PAIRS,
    ids=[f"{skill}:{path}" for skill, path, _key in _PAIRS],
)
def test_declared_increment_routes_through_keyed_upsert(
    skill: str, path: str, key: str, tmp_path: Path
) -> None:
    """Two increments (two chapter-like keys) then a re-dispatch of one key:
    the routed keyed upsert keeps history and dedups per key; the legacy
    whole-file write loses the first increment on the second dispatch.

    Row shape follows the DECLARED key arity (#50): composite-key targets
    (章节,变动项 / 章节,支线 / 角色A,角色B) carry a stable second key cell —
    a re-merge varies a payload cell, never a key cell (probe21's re-settle
    rows kept 变动项 constant across attempts).
    """
    if path == "outline/volume_map.md":
        # A1 form: keyed volume sections, located by 第N卷 token (retitles
        # replace in place — same invariants as the table-row pairs below).
        # C 批: headings carry the machine-readable paren span (卷界锚规则 —
        # new volumes must start at live max boundary + 1).
        first = "## 第一卷：t6-key-one（第 1-8 章）\n\n- first increment"
        second = "## 第二卷：t6-key-two（第 9-16 章）\n\n- second increment"
        revised = "## 第二卷：t6-key-two·修订（第 9-16 章）\n\n- revised increment"
    elif path == "outline/thread_map.md":
        first = "### T1: t6-key-one\n\n- first increment"
        second = "### T2: t6-key-two\n\n- second increment"
        revised = "### T2: t6-key-two 修订\n\n- revised increment"
    elif path == "world/locations.md":
        first = "## 地点：t6-key-one\n\n- first increment"
        second = "## 地点：t6-key-two\n\n- second increment"
        revised = "## 地点：t6-key-two\n\n- revised increment"
    elif path == "characters/relationships.md":
        first = "## 关系对：t6-key-one - t6-char-b\n\n**矩阵格**: first increment"
        second = "## 关系对：t6-key-two - t6-char-d\n\n**矩阵格**: second increment"
        revised = "## 关系对：t6-key-two - t6-char-d\n\n**矩阵格**: revised increment"
    elif "," in key:
        first = "| t6-key-one | t6-item-one | first increment |"
        second = "| t6-key-two | t6-item-two | second increment |"
        revised = "| t6-key-two | t6-item-two | revised increment |"
    else:
        first = "| t6-key-one | first increment |"
        second = "| t6-key-two | second increment |"
        revised = "| t6-key-two | revised increment |"
    for row in (first, second):
        written = _write_parsed_outputs(
            response=f"### FILE: {path}\n{row}\n",
            output_paths=[path],
            project_dir=tmp_path,
            skill=skill,
        )
        assert path in written

    text = (tmp_path / path).read_text(encoding="utf-8")
    assert "t6-key-one" in text, (
        f"{skill} → {path}: first increment lost on second write "
        "(whole-file collapse, F1104/F1105 shape)"
    )
    assert "t6-key-two" in text

    # Re-dispatching the SAME key replaces its row in place — crash-retry
    # safety — and never duplicates it or disturbs the other key's row.
    _write_parsed_outputs(
        response=f"### FILE: {path}\n{revised}\n",
        output_paths=[path],
        project_dir=tmp_path,
        skill=skill,
    )
    text = (tmp_path / path).read_text(encoding="utf-8")
    assert "t6-key-one" in text
    assert "revised increment" in text
    assert "second increment" not in text
    assert text.count("t6-key-two") == 1
