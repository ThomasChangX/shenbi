from __future__ import annotations

from shenbi.contracts.ownership import (
    OWNERSHIP,
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


def test_plant_record_create_allows_new_record() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md",
        status="modified",
        new_record_ids=("hook-new",),
    )
    assert check_write_ownership("shenbi-foreshadowing-plant", ch) == []


def test_plant_rejects_modifying_existing_record() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md",
        status="modified",
        modified_record_keys=(("hook-ch1-001", frozenset({"state"})),),
    )
    v = check_write_ownership("shenbi-foreshadowing-plant", ch)
    assert any("hook-ch1-001" in i for i in v)


def test_track_record_field_allows_state_only() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md",
        status="modified",
        modified_record_keys=(("hook-ch1-001", frozenset({"state"})),),
    )
    assert check_write_ownership("shenbi-foreshadowing-track", ch) == []


def test_track_rejects_subtlety_change() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md",
        status="modified",
        modified_record_keys=(("hook-ch1-001", frozenset({"subtlety"})),),
    )
    v = check_write_ownership("shenbi-foreshadowing-track", ch)
    assert any("subtlety" in i for i in v)


def test_track_rejects_creating_new_record() -> None:
    ch = FileChange(
        relpath="truth/pending_hooks.md",
        status="modified",
        new_record_ids=("hook-new",),
    )
    v = check_write_ownership("shenbi-foreshadowing-track", ch)
    assert any("新增" in i for i in v)


def test_no_ownership_entry_returns_empty() -> None:
    """无 OWNERSHIP 条目 → 由 write_audit 做 file-level 声明写入检查。"""
    ch = FileChange(relpath="chapters/chapter-5.md", status="added")
    assert check_write_ownership("shenbi-chapter-drafting", ch) == []
