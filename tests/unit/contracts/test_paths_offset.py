"""Relative-offset placeholder semantics (spec #58 C20 T2.5 enabler, F811).

`chapter-{N-3}` resolves to a near-chapter path: no-ctx route uses the
chapter argument as base; ctx route uses the ctx family value (F207
semantics — None/str-sentinel raises instead of silently falling back);
genesis (chapter None) raises so resolve_or_skip_ctx filters it out.
"""

import pytest

from shenbi.contracts.paths import (
    PathContext,
    UnresolvedPathError,
    resolve_chapter_path,
    resolve_contract_path,
    resolve_or_skip_ctx,
)


def test_offset_no_ctx_chapter_base():
    assert resolve_chapter_path("chapters/chapter-{N-3}.md", 5) == "chapters/chapter-2.md"
    assert resolve_chapter_path("chapters/chapter-{N-1}.md", 1) == "chapters/chapter-0.md"


def test_offset_ctx_family_base():
    ctx = PathContext(chapter=99, volume=3)
    assert resolve_contract_path("chapters/chapter-{N-3}.md", 99, ctx) == "chapters/chapter-96.md"


def test_offset_ctx_family_value_missing_raises():
    # 路径须家族前有 / 或 -（_FAMILY_N_OFFSET lookbehind），字符串起始形态不匹配
    with pytest.raises(UnresolvedPathError):
        resolve_contract_path("truth/volume-{N-1}/x.md", 5, PathContext(chapter=5))


def test_offset_genesis_skipped_via_resolve_or_skip():
    assert resolve_or_skip_ctx("chapters/chapter-{N-3}.md", None, None) is None
    with pytest.raises(UnresolvedPathError):
        resolve_chapter_path("chapters/chapter-{N-3}.md", None)


def test_offset_no_interference_with_legacy_forms():
    assert resolve_chapter_path("chapters/chapter-N.md", 5) == "chapters/chapter-5.md"
    assert resolve_chapter_path("import/canon/01_SECTION.md", 5) == "import/canon/01_SECTION.md"
    assert resolve_chapter_path("audits/AC-007.md", 5) == "audits/AC-007.md"
