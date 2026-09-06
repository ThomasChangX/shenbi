import re

from shenbi.pipeline.dispatch_helper import (
    _FILE_PRIORITY_WEIGHTS,
    _INPUT_MAX_CHARS_PER_FILE,
    _INPUT_MAX_CHARS_TOTAL,
    TruncateRecord,
    _budgeted_truncate,
)


def test_budgeted_truncate_preserves_high_priority():
    texts = {
        "chapter-current.md": "A" * 30000,  # HIGH priority
        "world_rules.md": "B" * 10000,  # HIGH priority
        "style_profile.md": "C" * 5000,  # MEDIUM priority
        "archive_notes.md": "D" * 20000,  # LOW priority
    }
    budget = 20000  # chars

    result, records = _budgeted_truncate(texts, budget)
    total = sum(len(v) for v in result.values())

    # High priority files should be less truncated
    assert len(result.get("chapter-current.md", "")) > 5000
    # Total should be within budget (marker slack tolerated)
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

    result, _records = _budgeted_truncate(texts, budget)

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


# --- C29 spec #43 R1: truncation marker protocol (F361/F330) ---


def test_marker_survives_per_file_cap():
    """F361: marker appended after the per-file cap slice so it can never be clipped."""
    huge = "A" * 60000  # allocation > 32000 的超长文件
    texts, records = _budgeted_truncate({"chapter-N.md": huge}, _INPUT_MAX_CHARS_TOTAL)
    out = texts["chapter-N.md"]
    assert out.endswith("chars]")  # 标记在末尾存活
    assert "[TRUNCATED " in out
    m = re.search(r"\[TRUNCATED (\d+)/(\d+) chars\]", out)
    assert m and int(m.group(1)) == _INPUT_MAX_CHARS_PER_FILE and int(m.group(2)) == 60000
    assert len(records) == 1 and records[0].original_len == 60000
    assert records[0].kept_len == _INPUT_MAX_CHARS_PER_FILE


def test_budget_surplus_redistributed():
    """F330: surplus from short files is redistributed to truncated files, capped at per-file ceiling."""
    texts_in = {
        "chapter-N.md": "X" * 40000,  # HIGH，配额 16667 会被截
        "archive-notes.md": "Y" * 1000,  # LOW，配额 3333 只用 1000 → 余量 2333
    }
    out, records = _budgeted_truncate(texts_in, 20000)
    kept = records[0].kept_len
    # 纯按权重分配 = 16667；回补后必须超过它（16667 + 2333 ≈ 19000）
    assert kept > 17000
    # 回补不得越过 cap（标记长度余量 ~30 chars）
    assert len(out["chapter-N.md"]) <= _INPUT_MAX_CHARS_PER_FILE + 64


def test_no_truncation_no_records():
    texts_in = {"a.md": "short"}
    out, records = _budgeted_truncate(texts_in, 10000)
    assert records == []
    assert out == {"a.md": "short"}


def test_records_metadata_shape():
    """Meta carries original_len/kept_len/offset (spec R1)."""
    _texts, records = _budgeted_truncate({"chapter-N.md": "Z" * 50000}, 10000)
    rec = records[0]
    assert isinstance(rec, TruncateRecord)
    assert rec.file == "chapter-N.md"
    assert rec.original_len == 50000
    assert rec.offset == 0
    assert 0 < rec.kept_len < 50000


def test_budgeted_truncate_itself_is_pure_no_warn():
    """C29 R1: the helper is pure — the input_truncated WARN fires at the dispatch
    call boundary, not inside _budgeted_truncate (structlog capture proves it).
    """
    from structlog.testing import capture_logs

    texts_in = {"chapter-N.md": "X" * 40000, "archive-notes.md": "Y" * 1000}
    with capture_logs() as logs:
        _out, records = _budgeted_truncate(texts_in, 20000)
    warns = [e for e in logs if e.get("log_level") == "warning" and e["event"] == "input_truncated"]
    # helper itself is pure: the WARN fires at the dispatch call boundary;
    # assert the contract here via _cap_single (under-budget path)
    assert len(warns) == 0


def test_cap_single_marks_and_warns():
    """C29 R1 (F361 under-budget path): per-file cap via _cap_single discloses."""
    from structlog.testing import capture_logs

    from shenbi.pipeline.dispatch_helper import _cap_single

    long_text = "Q" * 50000
    with capture_logs() as logs:
        out = _cap_single(long_text, "big.md")
    assert out.endswith(f"[TRUNCATED {_INPUT_MAX_CHARS_PER_FILE}/50000 chars]")
    warns = [e for e in logs if e.get("log_level") == "warning" and e["event"] == "input_truncated"]
    assert len(warns) == 1 and warns[0]["file"] == "big.md"
