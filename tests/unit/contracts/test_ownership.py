from __future__ import annotations

from shenbi.contracts.ownership import (
    FileChange,
    check_write_ownership,
    get_ownership,
)


def test_genre_config_has_nine_write_keys() -> None:
    own = get_ownership("shenbi-genre-config", "genre-config.json")
    assert own is not None
    assert own.level == "field"
    assert own.write_keys == {
        "approval",
        "auditDimensions",
        "chapterTypes",
        "customRules",
        "fatigueWords",
        "pacing",
        "tropeInventory",
        "updated",
        "version",
    }


def test_genre_field_level_allows_declared_key() -> None:
    ch = FileChange(relpath="genre-config.json", status="modified", changed_top_keys=("version",))
    assert check_write_ownership("shenbi-genre-config", ch) == []


def test_genre_field_level_rejects_undeclared_key() -> None:
    ch = FileChange(relpath="genre-config.json", status="modified", changed_top_keys=("title",))
    v = check_write_ownership("shenbi-genre-config", ch)
    assert any("title" in i for i in v)


def test_state_settling_record_field_rejects_new_record() -> None:
    """The surviving record_field row rejects creation — contrast to the
    row-less lifecycle fallthrough above (spec #59 T3).
    """
    ch = FileChange(
        relpath="truth/pending_hooks.md",
        status="modified",
        new_record_ids=("hook-new",),
    )
    v = check_write_ownership("shenbi-state-settling", ch)
    assert any("新增" in i for i in v)


def test_lifecycle_has_no_ownership_row_falls_to_file_level() -> None:
    """Spec #59 T3 (plan r2 I1): lifecycle creates AND updates records every
    chapter, which no single FileOwnership level expresses — no row means the
    file-level declared-writes check in write_audit governs (ownership.py:110).
    """
    from shenbi.contracts.ownership import get_ownership

    assert get_ownership("shenbi-foreshadowing-lifecycle", "truth/pending_hooks.md") is None
    ch = FileChange(
        relpath="truth/pending_hooks.md",
        status="modified",
        modified_record_keys=(("hook-ch1-001", frozenset({"state"})),),
        new_record_ids=("hook-new",),
    )
    assert check_write_ownership("shenbi-foreshadowing-lifecycle", ch) == []


def test_no_ownership_entry_returns_empty() -> None:
    """无 OWNERSHIP 条目 → 由 write_audit 做 file-level 声明写入检查。"""
    ch = FileChange(relpath="chapters/chapter-5.md", status="added")
    assert check_write_ownership("shenbi-chapter-drafting", ch) == []
