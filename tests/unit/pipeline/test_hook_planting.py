"""Tests for deterministic hook planting."""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.hook_planting import (
    _extract_section_7,
    _parse_hook_entries,
    plant_hooks_from_plan,
)


class TestSection7Extraction:
    def test_extracts_section_7_from_plan(self):
        plan = """## 6. 章尾改变\nSome content.\n\n## 7. 本章 hook 账\n\n| hook-005 | test | plant |\n\n## 8. 禁忌\nProhibited."""
        result = _extract_section_7(plan)
        assert "hook-005" in result
        assert "## 8." not in result

    def test_returns_empty_when_section_7_missing(self):
        plan = "## 1. 当前任务\nSome content.\n## 2. 读者此刻在等什么"
        result = _extract_section_7(plan)
        assert result == ""

    def test_extracts_to_end_when_no_section_8(self):
        plan = "## 6. 章尾改变\n\n## 7. 本章 hook 账\n\n| hook-001 | desc | plant |\n\nLast line."
        result = _extract_section_7(plan)
        assert "hook-001" in result
        assert "Last line" in result


class TestHookEntryParsing:
    def test_parses_table_format(self):
        section7 = "| hook-005 | 矿井的心跳声 | plant | GENUINE | CHARACTER |"
        entries = _parse_hook_entries(section7)
        assert len(entries) == 1
        assert entries[0]["hook_id"] == "hook-005"
        assert entries[0]["description"] == "矿井的心跳声"
        assert entries[0]["operation"] == "plant"
        assert entries[0]["type"] == "GENUINE"
        assert entries[0]["category"] == "CHARACTER"

    def test_skips_non_plant_entries(self):
        section7 = "| hook-005 | test | advance |\n| hook-006 | test2 | plant |"
        entries = _parse_hook_entries(section7)
        assert len(entries) == 1
        assert entries[0]["hook_id"] == "hook-006"

    def test_treats_open_as_plant(self):
        """Real plans use 'open' to mean plant — treat as equivalent."""
        section7 = "| H-NEW-01 | 矿难波及面 | open | GENUINE | THEMATIC |"
        entries = _parse_hook_entries(section7)
        assert len(entries) == 1
        assert entries[0]["hook_id"] == "H-NEW-01"
        assert entries[0]["operation"] == "plant"

    def test_parses_partial_columns(self):
        """Fewer columns should still work — missing ones get defaults."""
        section7 = "| hook-007 | brief desc | plant |"
        entries = _parse_hook_entries(section7)
        assert len(entries) == 1
        assert entries[0]["hook_id"] == "hook-007"
        assert entries[0]["type"] is None

    def test_skips_header_row(self):
        section7 = (
            "| ID | 描述 | 操作 | 类型 | 维度 |\n"
            "|------|------|------|------|------|\n"
            "| hook-010 | test desc | plant | GENUINE | CHARACTER |"
        )
        entries = _parse_hook_entries(section7)
        assert len(entries) == 1
        assert entries[0]["hook_id"] == "hook-010"

    def test_skips_empty_lines(self):
        section7 = "\n\n| hook-011 | desc | plant |\n\n\n"
        entries = _parse_hook_entries(section7)
        assert len(entries) == 1


class TestPlantHooksFromPlan:
    def test_plants_and_appends_to_pending_hooks(self, tmp_path: Path):
        (tmp_path / "plans").mkdir()
        (tmp_path / "truth").mkdir()

        (tmp_path / "plans" / "chapter-5-plan.md").write_text(
            """## 7. 本章 hook 账

| hook-005 | 矿井深处的心跳声 | plant | GENUINE | CHARACTER |
""",
            encoding="utf-8",
        )

        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )

        count = plant_hooks_from_plan(tmp_path, chapter=5)
        assert count == 1

        updated = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert "hook-005" in updated
        assert "state: PLANTED" in updated

    def test_returns_zero_when_plan_missing(self, tmp_path: Path):
        (tmp_path / "truth").mkdir()
        count = plant_hooks_from_plan(tmp_path, chapter=99)
        assert count == 0

    def test_returns_zero_when_no_plant_entries(self, tmp_path: Path):
        (tmp_path / "plans").mkdir()
        (tmp_path / "truth").mkdir()

        (tmp_path / "plans" / "chapter-5-plan.md").write_text(
            """## 7. 本章 hook 账

| hook-005 | test | advance |
| hook-006 | test2 | defer |
""",
            encoding="utf-8",
        )

        (tmp_path / "truth" / "pending_hooks.md").write_text(
            "---\nhooks: []\n---\n", encoding="utf-8"
        )

        count = plant_hooks_from_plan(tmp_path, chapter=5)
        assert count == 0

    def test_appends_to_existing_hooks(self, tmp_path: Path):
        (tmp_path / "plans").mkdir()
        (tmp_path / "truth").mkdir()

        (tmp_path / "plans" / "chapter-6-plan.md").write_text(
            """## 7. 本章 hook 账

| hook-010 | new hook desc | plant | GENUINE | CHARACTER |
""",
            encoding="utf-8",
        )

        existing_yaml = """---
hooks:
  - id: hook-001
    content: Existing hook
    state: PLANTED
    operation: plant
    type: GENUINE
    dimension: THEMATIC
    subtlety: 0.5
    plant_chapter: 1
    cultivation_interval: 3
    last_reinforced: 1
    max_distance: 150
    escalation_curve: RISING
    depends_on: []
    core_hook: true
    promoted: false
---
"""
        (tmp_path / "truth" / "pending_hooks.md").write_text(existing_yaml, encoding="utf-8")

        count = plant_hooks_from_plan(tmp_path, chapter=6)
        assert count == 1

        updated = (tmp_path / "truth" / "pending_hooks.md").read_text(encoding="utf-8")
        assert "hook-001" in updated  # existing hook preserved
        assert "hook-010" in updated  # new hook added

    def test_creates_pending_hooks_if_missing(self, tmp_path: Path):
        (tmp_path / "plans").mkdir()
        (tmp_path / "truth").mkdir()

        (tmp_path / "plans" / "chapter-3-plan.md").write_text(
            """## 7. 本章 hook 账

| hook-003 | a new hook | plant | GENUINE | CHARACTER |
""",
            encoding="utf-8",
        )

        # No pending_hooks.md exists yet
        count = plant_hooks_from_plan(tmp_path, chapter=3)
        assert count == 1

        hooks_file = tmp_path / "truth" / "pending_hooks.md"
        assert hooks_file.exists()
        updated = hooks_file.read_text(encoding="utf-8")
        assert "hook-003" in updated
        assert "state: PLANTED" in updated

    def test_skips_duplicate_hook_ids(self, tmp_path: Path):
        (tmp_path / "plans").mkdir()
        (tmp_path / "truth").mkdir()

        (tmp_path / "plans" / "chapter-5-plan.md").write_text(
            """## 7. 本章 hook 账

| hook-005 | already planted | plant | GENUINE | CHARACTER |
""",
            encoding="utf-8",
        )

        existing_yaml = """---
hooks:
  - id: hook-005
    content: Already planted hook
    state: PLANTED
    operation: plant
    type: GENUINE
    dimension: CHARACTER
    subtlety: 0.6
    plant_chapter: 4
    cultivation_interval: 5
    last_reinforced: 4
    max_distance: 20
    escalation_curve: RISING
    depends_on: []
    core_hook: false
    promoted: false
---
"""
        (tmp_path / "truth" / "pending_hooks.md").write_text(existing_yaml, encoding="utf-8")

        count = plant_hooks_from_plan(tmp_path, chapter=5)
        assert count == 0  # duplicate, should be skipped
