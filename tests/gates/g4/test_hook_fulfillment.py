"""Test G4.cd.hook_fulfillment plan-content cross-validation."""

from shenbi.gates.g4.chapter_drafting import check_hook_fulfillment


class TestHookFulfillment:
    def test_detects_missing_hooks(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("""
## 7. Hook Ledger

| MH-003 | advance | Progress the copper coin mystery |
| MH-007 | reference | Mention the amulet backstory |
""")
        chapter = tmp_path / "chapter.md"
        chapter.write_text(
            "This chapter mentions MH-007 briefly but does not advance the copper coin mystery."
        )
        issues = check_hook_fulfillment(plan, chapter)
        assert any("MH-003" in i for i in issues)
        assert not any("MH-007" in i for i in issues)

    def test_passes_when_all_hooks_fulfilled(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("## 7. Hook Ledger\n\n| MH-003 | advance | desc |\n")
        chapter = tmp_path / "chapter.md"
        chapter.write_text("MH-003 advancement in this scene.")
        issues = check_hook_fulfillment(plan, chapter)
        assert len(issues) == 0

    def test_no_hooks_in_plan_returns_empty(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("## 7. Hook Ledger\n\nNo hooks this chapter.\n")
        chapter = tmp_path / "chapter.md"
        chapter.write_text("Regular chapter body.")
        issues = check_hook_fulfillment(plan, chapter)
        assert len(issues) == 0

    def test_plan_missing_returns_empty(self, tmp_path):
        plan = tmp_path / "nonexistent.md"
        chapter = tmp_path / "chapter.md"
        chapter.write_text("Content.")
        issues = check_hook_fulfillment(plan, chapter)
        assert len(issues) == 0

    def test_handles_hook_ids_with_letters(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("| CP-012 | advance | Character progression hook |\n")
        chapter = tmp_path / "chapter.md"
        chapter.write_text("CP-012 is referenced here.")
        issues = check_hook_fulfillment(plan, chapter)
        assert len(issues) == 0
