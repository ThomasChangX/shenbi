from pathlib import Path

BRIDGE_TRACKER_HEADER = (
    "| Bridge ID | Content | Expected Activation Ch | Actual Activation Ch | Status |"
)


def test_bridge_tracker_template_has_correct_structure():
    """The bridge tracker template file must contain the expected table header."""
    template_path = (
        Path(__file__).resolve().parents[3] / "_templates" / "truth" / "bridge_tracker.md"
    )
    assert template_path.exists(), "bridge_tracker.md template must exist (F712: stale skip)"
    content = template_path.read_text(encoding="utf-8")
    assert BRIDGE_TRACKER_HEADER in content
    assert "PENDING" in content
    assert "ACTIVATED" in content or "| Status |" in content


def test_bridge_tracker_template_is_valid_markdown_table():
    template_path = (
        Path(__file__).resolve().parents[3] / "_templates" / "truth" / "bridge_tracker.md"
    )
    assert template_path.exists(), "bridge_tracker.md template must exist (F712: stale skip)"
    content = template_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    # Must have at least a header row and separator row
    pipe_lines = [l for l in lines if "|" in l]
    assert len(pipe_lines) >= 2
