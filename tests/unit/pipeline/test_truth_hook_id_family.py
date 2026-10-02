r"""Hook-id family alignment across genesis/live and machinery forms (probe15 P1).

probe15 ch1 settle (2026-10-02, cross-probe breaker 3/3): the genesis-pinned
template writes hooks as ``MH02(钩子名)`` (no hyphen, id + name in one
heading/cell), while every machinery regex accepted only ``MH-\d{3}``. The
field-level in-place merge therefore NEVER activated: the splitter grouped
``## 详情`` + all hook sections into one blob unit, ``_hook_section_bullet_merge``
returned None, and the scaffold headings fell to ``_replace_section`` — whose
H1 span-to-EOF replacement destroyed the live base (242<317 lines, 204 base
lines dropped, 3x G4.ss rejects, escalation).

These tests pin the single hook-id family: live form ``MH02(名)``, gate
example form ``MH-001|名``, and legacy ``### MH-001 · 名`` all canonicalize to
the same hook, while chapter-local hooks (``CH1-L1``) stay non-family.
"""

from __future__ import annotations

import pytest

from shenbi.pipeline.truth_io import canon_hook_id, is_hook_heading, upsert_markdown_row

#: probe15 live shape — genesis template form, id and name in one heading.
_LIVE_PROBE15 = """## 详情

### MH02（星火残梦与那句听不清的话）

- hook_id: MH02
- type: INFORMATION / dimension: SYMBOLIC
- lifecycle_state: PLANTED
- plant_ch: 1
- trigger_condition: 残梦复现（第9/40章）
- resolve_condition: 那句话被听清（第98章）
- subtlety: 0.6
- depends_on: [MH13]
- last_reinforced: 0
- notes: 创世登记

### MH09（穹障与赤锈谷的总体衰减）

- hook_id: MH09
- type: RULE
- last_reinforced: 0
"""


class TestCanonHookId:
    def test_family_forms_canonicalize_together(self):
        assert canon_hook_id("MH02") == canon_hook_id("MH-002") == canon_hook_id("mh2")

    def test_prefix_families_distinct(self):
        assert canon_hook_id("MH01") != canon_hook_id("H01")
        assert canon_hook_id("CP-003") == canon_hook_id("CP3")

    def test_non_family_passthrough(self):
        assert canon_hook_id("CH1-L1") == "CH1-L1"


class TestIsHookHeading:
    def test_accepts_live_form(self):
        assert is_hook_heading("### MH02（星火残梦与那句听不清的话）")

    def test_accepts_gate_example_and_legacy_forms(self):
        assert is_hook_heading("### MH-001｜粗纸小册子")
        assert is_hook_heading("### MH-001 · 账簿涂改空白")

    def test_rejects_local_and_prose_headings(self):
        assert not is_hook_heading("### CH1-L1（原主留下的半张活计签）")
        # no word boundary between digits and CJK identifier text
        assert not is_hook_heading("### MH02编年核对")
        assert not is_hook_heading("### 钩子详情")


class TestLiveFormFieldMerge:
    def test_live_form_increment_patches_in_place(self):
        """probe15 exact shape: increment heading copies the live form; the
        colon bullet must patch the live block, stable lines untouched.
        """
        increment = "### MH02（星火残梦与那句听不清的话）\n- last_reinforced: 第 1 章"
        merged = upsert_markdown_row(_LIVE_PROBE15, increment, "hook_id")

        assert merged.count("### MH02") == 1
        mh02 = merged.split("### MH02", 1)[1].split("### MH09", 1)[0]
        assert "- last_reinforced: 第 1 章" in mh02
        for stable in (
            "- hook_id: MH02",
            "- plant_ch: 1",
            "- trigger_condition: 残梦复现（第9/40章）",
            "- resolve_condition: 那句话被听清（第98章）",
            "- depends_on: [MH13]",
        ):
            assert stable in mh02, f"stable line dropped: {stable}"
        assert "### MH09" in merged

    def test_hyphenated_increment_matches_unhyphenated_live_block(self):
        """Cross-form canon: a gate-example-form heading must land in the
        live-form block instead of appending a duplicate section.
        """
        increment = "### MH-002 · 星火残梦\n- last_reinforced: 第 3 章"
        merged = upsert_markdown_row(_LIVE_PROBE15, increment, "hook_id")

        assert merged.count("MH-002 · 星火残梦") == 0, "duplicate section appended"
        assert merged.count("### MH02") == 1
        assert "- last_reinforced: 第 3 章" in merged

    def test_local_hook_section_appends_whole(self):
        """A chapter-local hook (CH n-L n) is not family — its new block
        appends (probe15 CH1-L1 registration).
        """
        increment = (
            "### CH1-L1（原主留下的半张活计签）\n- hook_id: CH1-L1\n- lifecycle_state: PLANTED"
        )
        merged = upsert_markdown_row(_LIVE_PROBE15, increment, "hook_id")

        assert "### CH1-L1（原主留下的半张活计签）" in merged
        assert merged.count("### MH02") == 1


@pytest.mark.unit
def test_live_form_registry_row_upsert_replaces_by_canon_key():
    """Table branch: a live-form registry row is keyed by its id cell."""
    live = (
        "## 总览\n"
        "| Hook ID（钩子名） | 当前生命周期 | 种植章 |\n"
        "|---|---|---|\n"
        "| MH02（星火残梦与那句听不清的话） | PLANTED | 1 |\n"
    )
    bump = "| MH02（星火残梦与那句听不清的话） | RELEVANT | 1 |"
    merged = upsert_markdown_row(live, bump, "hook_id")
    assert "RELEVANT" in merged
    assert merged.count("| MH02") == 1


class TestBoldFieldAddressing:
    """probe18 adjudication #005 (#35): genesis improvised a bold field
    grammar (``- **notes**: …``) while the merge's name capture kept the
    stars — a bold increment name-matched a differently-styled live line
    and whole-line-replaced it. Addressing must normalize emphasis markers;
    the REPLACED line keeps the increment's own form (content strictness
    unchanged, G4 still gates it).
    """

    def test_bold_increment_addresses_plain_live_field(self):
        base = (
            "## 详情\n\n### MH01（标题）\n\n- type: ITEM\n"
            "- notes: 第 0 章 创世登记；历史甲\n- last_reinforced: 0\n"
        )
        increment = "### MH01（标题）\n- **last_reinforced**: 第 1 章"
        merged = upsert_markdown_row(base, increment, "hook_id")
        assert "- **last_reinforced**: 第 1 章" in merged
        assert "- last_reinforced: 0" not in merged
        assert merged.count("last_reinforced") == 1, "no duplicate field artifact"

    def test_plain_increment_addresses_bold_live_field(self):
        base = "## 详情\n\n### MH01（标题）\n\n- **type**: ITEM\n- **last_reinforced**: 0\n"
        increment = "### MH01（标题）\n- last_reinforced: 第 2 章"
        merged = upsert_markdown_row(base, increment, "hook_id")
        assert "- last_reinforced: 第 2 章" in merged
        assert merged.count("last_reinforced") == 1
