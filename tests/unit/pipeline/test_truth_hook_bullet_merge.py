"""Hook-section bullet-level merge (probe3 P0/P1 root-cause fix).

probe3 ch1 settle attempt1: the only staging merge primitive for a headed
section was whole-section replacement, so updating one volatile field
(``- last_reinforced: 1``) forced the LLM to re-emit the ENTIRE ``### MH-NNN``
block verbatim — it abbreviated, 189 base lines were dropped, the G4 hooks
guard (correctly) rejected, and the guard's whole-file remediation text then
pushed attempt2 into a full 18.6K reproduction pinned at 49152 completion
tokens.

These tests lock the code-side merge that removes the LLM from stable-line
preservation: a colon-bullet increment under a hook heading patches fields
IN PLACE; stable lines are never re-emitted, hence never dropped.

Row-side: registry-row enrichment stays ALLOWED (probe escalation #14's
adjudicated semantics, pinned by test_upsert_shape_mismatch_row_keeps_existing).
A width-growing hook row is guard-rejected downstream (hook_row_stable_
columns_rewritten) and retried with the row-scoped remediation text — the
guard decides, the merge does not pre-empt it.
"""

from __future__ import annotations

import pytest

from shenbi.pipeline.truth_io import upsert_markdown_row

_LIVE_HOOKS = """## 钩子详情
### MH-001 · 账簿上「丙七」旁被涂改过的空白

- type: GENUINE | dimension: ITEM | core_hook: true
- plant_ch: 1（废矿道分拣芒晶残渣）
- trigger_condition: 西陆顾问团启动补齐核查
- resolve_condition: 陈述把名字从公开名录撤下
- subtlety: 0.5 | cultivation_interval: 12 | max_distance: 90
- last_reinforced: 0
- depends_on: []
- notes: 除名制度与真名危机的双重接口

### MH-002 · 祝岐从未示人的预言收支账

- type: GENUINE | dimension: ITEM | core_hook: true
- last_reinforced: 0
"""


@pytest.mark.unit
def test_hook_field_update_replaces_in_place_and_preserves_stable_lines():
    """A one-field colon-bullet increment patches the field; every stable
    line (type/plant_ch/trigger/resolve/depends_on) survives untouched.
    """
    increment = "### MH-001 · 账簿上「丙七」旁被涂改过的空白\n- last_reinforced: 1"
    merged = upsert_markdown_row(_LIVE_HOOKS, increment, "hook_id")

    assert merged.count("### MH-001") == 1
    mh1 = merged.split("### MH-001", 1)[1].split("### MH-002", 1)[0]
    assert "- last_reinforced: 1" in mh1
    assert "- last_reinforced: 0" not in mh1
    for stable in (
        "- type: GENUINE | dimension: ITEM | core_hook: true",
        "- plant_ch: 1（废矿道分拣芒晶残渣）",
        "- trigger_condition: 西陆顾问团启动补齐核查",
        "- resolve_condition: 陈述把名字从公开名录撤下",
        "- depends_on: []",
    ):
        assert stable in mh1, f"stable line dropped: {stable}"
    assert "### MH-002" in merged, "sibling section untouched"


@pytest.mark.unit
def test_hook_new_field_inserted_into_existing_section():
    """A field absent from the live block (e.g. track's first 证据) is
    inserted INSIDE the section, not appended at file tail.
    """
    increment = (
        "### MH-002 · 祝岐从未示人的预言收支账\n"
        "- lifecycle_state: RELEVANT\n"
        "- 证据: chapter-3.md L45 > 「账目从未示人」"
    )
    merged = upsert_markdown_row(_LIVE_HOOKS, increment, "hook_id")

    assert "- lifecycle_state: RELEVANT" in merged
    assert "- 证据: chapter-3.md L45 > 「账目从未示人」" in merged
    mh2 = merged.split("### MH-002", 1)[1]
    assert "- 证据:" in mh2, "new field must land inside MH-002's section"


@pytest.mark.unit
def test_hook_heading_paraphrase_still_matches_by_id():
    """The model may paraphrase the hook title after the id; the section is
    located by (level, hook-id) so the update lands in the live block
    instead of appending a duplicate section.
    """
    increment = "### MH-001 · 矿区账簿涂改空白\n- last_reinforced: 2"
    merged = upsert_markdown_row(_LIVE_HOOKS, increment, "hook_id")

    assert merged.count("### MH-001") == 1, "paraphrased heading must not duplicate the section"
    assert "- last_reinforced: 2" in merged
    assert "- plant_ch: 1（废矿道分拣芒晶残渣）" in merged


@pytest.mark.unit
def test_unknown_hook_section_appends_whole():
    """A genuinely new hook (plant) appends its whole section — legacy
    append semantics preserved.
    """
    increment = "### CP-001 · 记工房的旧墨账\n- lifecycle_state: PLANTED"
    merged = upsert_markdown_row(_LIVE_HOOKS, increment, "hook_id")

    assert "### CP-001 · 记工房的旧墨账" in merged
    assert "- lifecycle_state: PLANTED" in merged


@pytest.mark.unit
def test_hook_section_with_non_colon_lines_keeps_replace_semantics():
    """Discriminator: bullet-merge applies ONLY to all-colon-bullet bodies.
    Free-form content in the unit expresses a section REWRITE — the legacy
    replace semantics (and its locked test) must hold.
    """
    existing = "## 伏笔详情\n### MH-001｜静海回响\n- lifecycle_state: PLANTED\n- 旧证据\n"
    updated = "### MH-001｜静海回响\n- lifecycle_state: RELEVANT\n- 新证据（第 9 章）"
    merged = upsert_markdown_row(existing, updated, "hook_id")

    assert merged.count("### MH-001") == 1
    assert "旧证据" not in merged, "mixed-content unit replaces, old body must not linger"
    assert "新证据（第 9 章）" in merged


@pytest.mark.unit
def test_hook_registry_row_same_shape_status_update_replaces():
    """The one legal row mutation — final status cell — replaces in place."""
    live = "## 主钩总览\n| MH-001 | 空白 | GENUINE | ITEM | 1 | 第4卷 | true | PLANTED |\n"
    bumped = "| MH-001 | 空白 | GENUINE | ITEM | 1 | 第4卷 | true | REINFORCED |"
    merged = upsert_markdown_row(live, bumped, "hook_id")

    assert bumped in merged
    assert "PLANTED |" not in merged
