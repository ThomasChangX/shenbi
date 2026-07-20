from pathlib import Path

import pytest

from shenbi.pipeline.plan_skeleton import generate_plan_skeleton


@pytest.fixture
def project_with_volume_map(tmp_path: Path) -> Path:
    outline_dir = tmp_path / "outline"
    outline_dir.mkdir()
    volume_map = outline_dir / "volume_map.md"
    volume_map.write_text("""# Volume Map

## Volume 1: Awakening (Ch 1-15)
**Objective:** Introduce protagonist and establish cultivation world

### Chapter Nodes
| Ch | Role | Content |
|----|------|---------|
| 1 | opening | Lin Feng awakens in cave |
| 2 | progression | First encounter with elder |

## Cross-Volume Bridges
| Bridge ID | Content | Expected Activation Ch |
|-----------|---------|----------------------|
| V1-B1 | Brahmi inscription | 26 |
""")
    truth_dir = tmp_path / "truth"
    truth_dir.mkdir()
    (truth_dir / "book_spine.md").write_text("# Book Spine\nThree-act structure placeholder.")
    return tmp_path


def test_skeleton_has_eight_sections(project_with_volume_map: Path):
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=1)
    assert "## 1. Current Task" in skeleton
    assert "## 2. Reader Expectations" in skeleton
    assert "## 3. Fulfill/Defer Decisions" in skeleton
    assert "## 4. Transition Role" in skeleton
    assert "## 5. Key Decisions" in skeleton
    assert "## 6. End-of-Chapter Change" in skeleton
    assert "## 7. Hook Ledger" in skeleton
    assert "## 8. Don't Do" in skeleton


def test_skeleton_section_1_prefilled_from_volume_map(project_with_volume_map: Path):
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=1)
    assert "Lin Feng awakens in cave" in skeleton
    assert "opening" in skeleton.lower()


def test_skeleton_section_5_is_llm_generated_placeholder(project_with_volume_map: Path):
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=1)
    # Section 5 should be a placeholder for LLM, not pre-filled
    section_5_start = skeleton.index("## 5. Key Decisions")
    section_6_start = skeleton.index("## 6. End-of-Chapter Change")
    section_5 = skeleton[section_5_start:section_6_start]
    assert "[LLM]" in section_5 or "placeholder" in section_5.lower()


def test_skeleton_returns_empty_on_missing_volume_map(tmp_path: Path):
    skeleton = generate_plan_skeleton(tmp_path, chapter=1)
    # Should still produce the 8-section template but with all [LLM] placeholders
    assert "## 1. Current Task" in skeleton
    assert "[LLM]" in skeleton


def test_skeleton_section_7_includes_pending_bridges(project_with_volume_map: Path):
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=25)
    assert "V1-B1" in skeleton or "Brahmi" in skeleton


def test_skeleton_marks_prefilled_sections_as_editable_context(project_with_volume_map: Path):
    """Pre-filled sections MUST be marked EDITABLE CONTEXT, not locked output.

    The skeleton must include an explicit instruction (Chinese and/or English)
    telling the LLM it may modify, override, or deviate from pre-filled content.
    """
    skeleton = generate_plan_skeleton(project_with_volume_map, chapter=1)
    # Must include the editable-context instruction in Chinese or English
    assert (
        "以下为参考骨架" in skeleton
        or "EDITABLE CONTEXT" in skeleton
        or "adjust as needed" in skeleton.lower()
    )
