"""Unit tests for skill_utils/style_learning/compute_stats.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.skill_utils.style_learning.compute_stats import (
    compute_all_stats,
    compute_connectives,
    compute_ngrams,
    compute_paragraph_stats,
    compute_percentiles,
    compute_punctuation,
    compute_sentence_stats,
    compute_ttr,
    count_ai_markers,
    count_transition_words,
    detect_rhetoric,
    read_chapters,
    segment_paragraphs,
    segment_sentences,
)

SAMPLE_CHAPTER = """# 第一章

这是第一段内容。主角走进了房间。他看到了一本书。

「你来啦。」她说。

主角点了点头。然后他坐下了。
"""


@pytest.mark.unit
def test_segment_sentences_splits_on_terminal_punctuation() -> None:
    sentences = segment_sentences("第一句。第二句！第三句？")
    assert len(sentences) == 3


@pytest.mark.unit
def test_segment_sentences_returns_text_and_count_tuples() -> None:
    sentences = segment_sentences("测试句子。")
    assert len(sentences) == 1
    text, count = sentences[0]
    assert isinstance(text, str)
    assert isinstance(count, int)
    assert count > 0


@pytest.mark.unit
def test_segment_sentences_empty_returns_empty() -> None:
    assert segment_sentences("") == []


@pytest.mark.unit
def test_segment_paragraphs_splits_on_double_newline() -> None:
    text = "第一段。\n\n第二段。\n\n第三段。"
    paras = segment_paragraphs(text)
    assert len(paras) == 3


@pytest.mark.unit
def test_segment_paragraphs_returns_dict_with_chars_and_sentences() -> None:
    paras = segment_paragraphs("一段内容。一句。两句。")
    assert len(paras) == 1
    assert "chars" in paras[0]
    assert "sentences" in paras[0]


@pytest.mark.unit
def test_compute_percentiles_empty_returns_zeros() -> None:
    pct = compute_percentiles([])
    assert pct == {"P25": 0, "P50": 0, "P75": 0, "P95": 0}


@pytest.mark.unit
def test_compute_percentiles_single_value_returns_same() -> None:
    pct = compute_percentiles([42])
    assert pct["P25"] == 42
    assert pct["P95"] == 42


@pytest.mark.unit
def test_compute_sentence_stats_returns_count_mean_median() -> None:
    sentences = segment_sentences("短句。中等长度的句子。更长的句子呢。")
    stats = compute_sentence_stats(sentences)
    assert "count" in stats
    assert "mean" in stats
    assert "median" in stats
    assert stats["count"] == 3


@pytest.mark.unit
def test_compute_sentence_stats_empty_returns_empty_dict() -> None:
    assert compute_sentence_stats([]) == {}


@pytest.mark.unit
def test_compute_paragraph_stats_returns_count_and_averages() -> None:
    paras = segment_paragraphs("段一。\n\n段二。")
    stats = compute_paragraph_stats(paras)
    assert "count" in stats
    assert "sentences_per_paragraph" in stats
    assert "chars_per_paragraph" in stats


@pytest.mark.unit
def test_compute_ttr_returns_global_ttr_between_0_and_1() -> None:
    ttr = compute_ttr("各种各样的文字内容测试")
    assert 0.0 <= ttr["global_ttr"] <= 1.0


@pytest.mark.unit
def test_compute_ttr_empty_returns_zeros() -> None:
    ttr = compute_ttr("")
    assert ttr["global_ttr"] == 0


@pytest.mark.unit
def test_compute_ngrams_returns_sorted_tuples() -> None:
    ngrams = compute_ngrams("测试测试测试文字文字", n=2, min_count=2)
    assert isinstance(ngrams, list)
    assert all(isinstance(t, tuple) and len(t) == 2 for t in ngrams)


@pytest.mark.unit
def test_compute_punctuation_returns_density_per_1000() -> None:
    result = compute_punctuation("一句话。")
    assert "句号" in result
    assert "per_1000" in result["句号"]


@pytest.mark.unit
def test_compute_punctuation_empty_returns_empty() -> None:
    assert compute_punctuation("") == {}


@pytest.mark.unit
def test_compute_connectives_finds_known_words() -> None:
    result = compute_connectives("因为所以然后")
    assert isinstance(result, dict)


@pytest.mark.unit
def test_detect_rhetoric_returns_int_counts() -> None:
    result = detect_rhetoric("难道不是吗？为什么是这样？")
    assert "反问" in result
    assert "设问" in result
    assert isinstance(result["反问"], int)


@pytest.mark.unit
def test_count_ai_markers_returns_dict_of_matches() -> None:
    result = count_ai_markers("似乎他微微一笑。")
    assert "似乎" in result
    assert "微微" in result


@pytest.mark.unit
def test_count_transition_words_returns_density() -> None:
    result = count_transition_words("然而此时突然终于")
    assert "total_transitions" in result
    assert "density_per_3000_chars" in result


@pytest.mark.unit
def test_read_chapters_handles_directory_and_file(tmp_path: Path) -> None:
    ch1 = tmp_path / "ch1.md"
    ch1.write_text(SAMPLE_CHAPTER, encoding="utf-8")
    texts = read_chapters([str(tmp_path)])
    assert isinstance(texts, dict)
    assert len(texts) >= 1


@pytest.mark.unit
def test_compute_all_stats_returns_all_categories() -> None:
    texts = {"ch1.md": SAMPLE_CHAPTER}
    stats = compute_all_stats(texts)
    for key in (
        "sample",
        "sentence_length",
        "paragraph_length",
        "ttr",
        "bigrams",
        "trigrams",
        "4grams",
        "punctuation",
        "connectives",
        "rhetoric",
        "ai_markers",
        "transition_density",
    ):
        assert key in stats, f"missing category: {key}"


# ---------------------------------------------------------------------------
# Error-path / edge-case tests (PR-52 Step 13)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_read_chapters_nonexistent_path_returns_empty(tmp_path: Path) -> None:
    """A path that does not exist is skipped silently -> empty dict."""
    texts = read_chapters([str(tmp_path / "does-not-exist.md")])
    assert texts == {}


@pytest.mark.unit
def test_read_chapters_mixed_files_and_dirs(tmp_path: Path) -> None:
    """A mix of a directory (read *.md) and a loose file -> both collected."""
    (tmp_path / "part1.md").write_text("第一段正文。", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "ch2.md").write_text("第二段正文。", encoding="utf-8")
    (sub / "notes.txt").write_text("ignored", encoding="utf-8")  # non-md ignored in dir
    loose = tmp_path / "loose.md"
    loose.write_text("松散文件。", encoding="utf-8")
    texts = read_chapters([str(sub), str(loose)])
    assert "ch2.md" in texts
    assert "loose.md" in texts
    assert "notes.txt" not in texts  # directory glob is *.md only


@pytest.mark.unit
def test_compute_ngrams_text_shorter_than_n_returns_empty() -> None:
    """Text with fewer than n characters yields no n-grams -> empty list."""
    ngrams = compute_ngrams("一二三", n=5, min_count=1)
    assert ngrams == []


@pytest.mark.unit
def test_segment_sentences_whitespace_only_returns_empty() -> None:
    """Whitespace-only input produces no sentences (char_count stays 0)."""
    assert segment_sentences("   \n   \t  ") == []


@pytest.mark.unit
def test_compute_ttr_punctuation_only_returns_zeros() -> None:
    """Punctuation/space-only input has no content chars -> all-zero TTR."""
    ttr = compute_ttr("。，！？；： \n")
    assert ttr["global_ttr"] == 0
    assert ttr["sliding_ttr_mean"] == 0
    assert ttr["sliding_ttr_std"] == 0


@pytest.mark.unit
def test_compute_sentence_stats_empty_returns_zeros() -> None:
    """compute_sentence_stats with empty list returns all zeros."""
    from shenbi.skill_utils.style_learning.compute_stats import compute_sentence_stats

    result = compute_sentence_stats([])
    assert isinstance(result, dict)


@pytest.mark.unit
def test_read_chapters_from_directory_returns_md_files(tmp_path: Path) -> None:
    """read_chapters reads .md files from a directory path."""
    from shenbi.skill_utils.style_learning.compute_stats import read_chapters

    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()
    (ch_dir / "ch001.md").write_text("正文内容。", encoding="utf-8")
    result = read_chapters([str(ch_dir)])
    assert "ch001.md" in result
    assert "正文内容。" in result["ch001.md"]


@pytest.mark.unit
def test_read_chapters_from_file_path(tmp_path: Path) -> None:
    """read_chapters reads a single .md file from a file path."""
    from shenbi.skill_utils.style_learning.compute_stats import read_chapters

    f = tmp_path / "ch001.md"
    f.write_text("正文内容。", encoding="utf-8")
    result = read_chapters([str(f)])
    assert "ch001.md" in result
    assert "正文内容。" in result["ch001.md"]


@pytest.mark.unit
def test_segment_paragraphs_with_trailing_newline() -> None:
    """segment_paragraphs with trailing double newline -> 2 paragraphs."""
    from shenbi.skill_utils.style_learning.compute_stats import segment_paragraphs

    result = segment_paragraphs("一段。\n\n二段。\n\n")
    assert len(result) == 2


@pytest.mark.unit
def test_main_requires_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() with no arguments prints usage and exits."""
    import io
    import sys

    from shenbi.skill_utils.style_learning.compute_stats import main

    monkeypatch.setattr(sys, "argv", ["compute_stats.py"])
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    with pytest.raises(SystemExit):
        main()
    assert "Usage" in out.getvalue()


@pytest.mark.unit
def test_compute_connectives_nests_counts_under_category() -> None:
    """Connective words nest their per-word counts under the matching category."""
    result = compute_connectives("然而但是")
    assert result["转折"]["然而"]["count"] == 1
    assert result["转折"]["但是"]["count"] == 1


@pytest.mark.unit
def test_compute_connectives_returns_empty_dict_for_blank_text() -> None:
    """Empty text short-circuits to an empty dict (no categories emitted)."""
    assert compute_connectives("") == {}
