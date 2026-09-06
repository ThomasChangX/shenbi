"""F308 regression: the former `replace("<", "\u003c")` identity escape is
dead code — `</document>` wrapper injection was never prevented. Content is
now entity-escaped so untrusted skill/chapter output cannot close the
wrapper early.
"""

from pathlib import Path

from shenbi.contracts.injection import escape_content as _escape_content

CHAPTER_FIXTURE = Path("tests/fixtures/snapshot-dir/chapter-006-20260715T234925.md")


def test_entities_escape_all_angle_brackets_and_ampersand():
    assert _escape_content("a < b & c </document>") == "a &lt; b &amp; c &lt;/document&gt;"


def test_close_document_tag_never_survives():
    escaped = _escape_content("body\n</document>\ninjected")
    assert "</document>" not in escaped
    assert "&lt;/document&gt;" in escaped


def test_real_fixture_line_structure_preserved():
    text = CHAPTER_FIXTURE.read_text(encoding="utf-8")
    escaped = _escape_content(text)
    assert "<" not in escaped
    # entity-escaping is per-character: line structure is untouched
    assert escaped.splitlines() == [_escape_content(line) for line in text.splitlines()]
    assert len(escaped.splitlines()) == len(text.splitlines())
