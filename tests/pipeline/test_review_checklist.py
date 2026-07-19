import json
import tempfile
from pathlib import Path

from shenbi.pipeline.review_checklist import (
    generate_chapter_delta,
    get_checklist,
)


def test_get_checklist_merges_template_and_delta():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        context_dir = project_dir / "context"
        context_dir.mkdir(parents=True)

        template = {
            "ai_blacklist": ["avoid_word_1"],
            "voice_constraints": "third_person",
            "pov_mode": "limited",
            "world_rules_brief": "rules summary",
            "sensitivity_flags": 0,
        }
        (context_dir / "review-checklist-template.json").write_text(
            json.dumps(template, ensure_ascii=False), encoding="utf-8"
        )

        delta = {
            "chapter": 5,
            "transition_budget": 3,
            "ending_constraints": "cliffhanger",
            "hook_deliverables": ["MH-001-advance"],
        }
        (context_dir / "review-checklist-chapter-005.json").write_text(
            json.dumps(delta, ensure_ascii=False), encoding="utf-8"
        )

        merged = get_checklist(project_dir, 5)
        assert merged["ai_blacklist"] == ["avoid_word_1"]
        assert merged["chapter"] == 5
        assert merged["hook_deliverables"] == ["MH-001-advance"]


def test_generate_chapter_delta_extracts_hooks():
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        plans_dir = project_dir / "plans"
        plans_dir.mkdir(parents=True)
        plan = """## 7. Hook Ledger
| MH-001 | advance | 推到50% |
| MH-003 | plant | 新线索 |
"""
        (plans_dir / "chapter-005-plan.md").write_text(plan, encoding="utf-8")

        delta = generate_chapter_delta(project_dir, 5)
        assert "hook_deliverables" in delta
        assert len(delta["hook_deliverables"]) >= 1
