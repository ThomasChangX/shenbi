# tests/unit/contracts/test_paths.py
import pytest

from shenbi.contracts.paths import (
    UnresolvedPathError,
    extract_chapter,
    resolve_chapter_path,
    resolve_or_skip,
    resolve_volume_path,
)


class TestResolveChapterPath:
    def test_nnn_zero_pads(self):
        assert resolve_chapter_path("snapshots/chapter-NNN/", 5) == "snapshots/chapter-005/"

    def test_n_bounded_at_separator(self):
        assert resolve_chapter_path("chapters/chapter-N.md", 5) == "chapters/chapter-5.md"

    def test_n_not_corrupted_mid_token_uppercase(self):
        # C2 fix: uppercase N mid-token must NOT be replaced
        assert resolve_chapter_path("import/canon/01_SECTION.md", 5) == "import/canon/01_SECTION.md"
        assert resolve_chapter_path("NPC-list.md", 5) == "NPC-list.md"

    def test_lowercase_n_unaffected(self):
        # str.replace("N") is case-sensitive; lowercase n never corrupted
        assert resolve_chapter_path("truth/resonance_trend.md", 5) == "truth/resonance_trend.md"

    def test_none_with_placeholder_raises(self):
        with pytest.raises(UnresolvedPathError):
            resolve_chapter_path("chapters/chapter-N.md", None)

    def test_none_without_placeholder_passes(self):
        assert resolve_chapter_path("truth/current_state.md", None) == "truth/current_state.md"


class TestResolveVolumePath:
    def test_volume_no_zero_pad(self):
        assert resolve_volume_path("audits/volume-N-payoff.md", 3) == "audits/volume-3-payoff.md"

    def test_volume_none_raises(self):
        with pytest.raises(UnresolvedPathError):
            resolve_volume_path("audits/volume-N-payoff.md", None)


class TestExtractChapter:
    def test_word_boundary(self):
        assert extract_chapter("Execute skill for chapter 5 now") == 5

    def test_subchapter_not_matched(self):
        # unified to word-boundary: subchapter does not match
        assert extract_chapter("subchapter 5") is None

    def test_case_insensitive(self):
        assert extract_chapter("CHAPTER 12") == 12


class TestResolveOrSkip:
    def test_genesis_skips_placeholder(self):
        assert resolve_or_skip("chapters/chapter-N.md", None) is None

    def test_chapter_resolves(self):
        assert resolve_or_skip("chapters/chapter-N.md", 5) == "chapters/chapter-5.md"
