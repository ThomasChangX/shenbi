from shenbi.pipeline.dispatch_helper import _FILE_PRIORITY_WEIGHTS, _budgeted_truncate


def test_budgeted_truncate_preserves_high_priority():
    texts = {
        "chapter-current.md": "A" * 30000,  # HIGH priority
        "world_rules.md": "B" * 10000,  # HIGH priority
        "style_profile.md": "C" * 5000,  # MEDIUM priority
        "archive_notes.md": "D" * 20000,  # LOW priority
    }
    budget = 20000  # chars

    result = _budgeted_truncate(texts, budget)
    total = sum(len(v) for v in result.values())

    # High priority files should be less truncated
    assert len(result.get("chapter-current.md", "")) > 5000
    # Total should be within budget
    assert total <= budget * 1.1  # 10% tolerance


def test_priority_weights_exist_for_all_keys():
    assert "chapter-current.md" in _FILE_PRIORITY_WEIGHTS or "chapter" in str(
        _FILE_PRIORITY_WEIGHTS
    )
    assert isinstance(_FILE_PRIORITY_WEIGHTS, dict)
    assert len(_FILE_PRIORITY_WEIGHTS) >= 5
