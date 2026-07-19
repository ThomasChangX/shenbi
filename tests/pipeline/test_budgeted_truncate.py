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


def test_high_priority_retains_more_than_low_priority():
    """When over budget, a high-priority file retains more chars than a low-priority
    file of equal original size (Task 6 Step 1 wiring verification).
    """
    equal_size = 25000
    texts = {
        "chapter-N.md": "X" * equal_size,  # HIGH priority (weight 1.0)
        "archive-notes.md": "Y" * equal_size,  # LOW priority (weight 0.2)
    }
    budget = 20000  # chars — forces truncation

    result = _budgeted_truncate(texts, budget)

    chapter_chars = len(result.get("chapter-N.md", ""))
    archive_chars = len(result.get("archive-notes.md", ""))

    # High-priority chapter should retain more characters than low-priority archive
    assert chapter_chars > archive_chars, (
        f"Expected high-priority chapter ({chapter_chars} chars) "
        f"to retain more than low-priority archive ({archive_chars} chars)"
    )
    # Additionally, chapter should keep a substantial portion
    assert chapter_chars > budget * 0.5, (
        f"High-priority file only got {chapter_chars} chars out of {budget} budget"
    )
