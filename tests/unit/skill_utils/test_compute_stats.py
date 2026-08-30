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


# ---------------------------------------------------------------------------
# Branch coverage (PR-56 coverage fill)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_main_outputs_json_to_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() with a readable chapter file emits full stats JSON to stdout.

    Covers the main() body (compute_stats.py:369-389) excluding the --output
    branch.
    """
    import io
    import json
    import sys

    from shenbi.skill_utils.style_learning.compute_stats import main

    ch = tmp_path / "ch1.md"
    ch.write_text("这是一段测试正文内容。第二句话在这里。\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["compute_stats.py", str(ch)])
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    main()
    data = json.loads(out.getvalue())
    assert data["sample"]["file_count"] == 1
    assert "sentence_length" in data


@pytest.mark.unit
def test_main_writes_to_output_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() with --output writes stats to the named file and logs to stdout.

    Covers compute_stats.py:385-387 (the output_path branch).
    """
    import io
    import json
    import sys

    from shenbi.skill_utils.style_learning.compute_stats import main

    ch = tmp_path / "ch1.md"
    ch.write_text("测试正文内容。第二句。\n", encoding="utf-8")
    out_file = tmp_path / "stats.json"
    monkeypatch.setattr(sys, "argv", ["compute_stats.py", str(ch), "--output", str(out_file)])
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    main()
    assert out_file.exists()
    assert "Stats written to" in out.getvalue()
    assert "sentence_length" in json.loads(out_file.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_main_exits_when_no_readable_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """main() with a path to no readable files exits with an error.

    Covers compute_stats.py:376-382 (empty-paths / no-readable-files branches).
    """
    import io
    import sys

    from shenbi.skill_utils.style_learning.compute_stats import main

    missing = tmp_path / "nonexistent.md"
    monkeypatch.setattr(sys, "argv", ["compute_stats.py", str(missing)])
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    with pytest.raises(SystemExit):
        main()
    assert "no readable files" in err.getvalue()


@pytest.mark.unit
def test_compute_ttr_sliding_window_for_long_text() -> None:
    """Text with >1000 content chars triggers the sliding-window TTR loop.

    Covers compute_stats.py:177-185 (the window iteration + non-empty
    window_ttrs branch). Short texts skip the loop entirely.
    """
    text = "各种不同的文字内容用于测试滑窗。" * 80  # >1000 content chars
    ttr = compute_ttr(text)
    assert ttr["total_chars"] > 1000
    # sliding stats come from actual windows, not the global fallback
    assert isinstance(ttr["sliding_ttr_mean"], float)


@pytest.mark.unit
def test_compute_sentence_stats_populates_all_histogram_bins() -> None:
    """Sentences spanning each length range populate every histogram bin.

    Covers compute_stats.py:119-130 (the 11-20/21-30/31-50/51-80/81+ branches).
    """
    sentences = [("", n) for n in (5, 15, 25, 40, 65, 90)]
    stats = compute_sentence_stats(sentences)
    hist = stats["histogram"]
    assert hist == {
        "1-10": 1,
        "11-20": 1,
        "21-30": 1,
        "31-50": 1,
        "51-80": 1,
        "81+": 1,
    }


@pytest.mark.unit
def test_detect_rhetoric_counts_repetition() -> None:
    """A phrase repeated 3+ times within 100 chars -> 反复 count > 0.

    Covers compute_stats.py:271-276 (the repetition-detection inner branch).
    """
    result = detect_rhetoric("主角笑了主角笑了主角笑了。")
    assert result["反复"] >= 1


@pytest.mark.unit
def test_segment_sentences_emits_trailing_sentence_without_terminator() -> None:
    """Text not ending in a terminator still yields a final trailing sentence.

    Covers compute_stats.py:69-73 (the post-loop `if current:` branch).
    """
    sents = segment_sentences("第一句。没有句号结尾")
    assert len(sents) == 2
    assert sents[1][0] == "没有句号结尾"


# --- spec #14 T1: segmentation & rhetoric fixes (F628/F668/F633/F656/F652/F663) ---


@pytest.mark.unit
def test_segment_sentences_splits_on_semicolon() -> None:
    r"""F628: fullwidth ; belongs to SENT_ENDS, so it must terminate sentences too."""
    sents = segment_sentences("前半句；后半句。")
    assert len(sents) == 2
    assert sents[0][0] == "前半句；"


@pytest.mark.unit
def test_segment_sentences_no_split_inside_cjk_quotes() -> None:
    """F668: sentence-final punctuation inside “” stays in one sentence."""
    sents = segment_sentences("“……。”他说。")
    assert len(sents) == 2
    assert sents[0][0] == "“……。”"


@pytest.mark.unit
def test_segment_sentences_no_split_inside_corner_quotes_across_semicolon() -> None:
    """F668+F628: fullwidth ; inside 「」 does not split."""
    sents = segment_sentences("他说「甲；乙；丙」然后离开。")
    assert len(sents) == 1


@pytest.mark.unit
def test_segment_sentences_unbalanced_quote_escapes_at_newline() -> None:
    r"""F668: unterminated quote must not swallow the rest — \n splits unconditionally."""
    sents = segment_sentences("“未闭合的引号内容。继续。\n第二段第一句。")
    assert len(sents) == 2
    assert sents[1][0] == "第二段第一句。"


@pytest.mark.unit
def test_segment_sentences_ascii_quote_toggle() -> None:
    """F668: ASCII " toggles quote state; 。 inside the pair does not split."""
    sents = segment_sentences('"内文。"他说。')
    assert len(sents) == 2
    assert sents[0][0] == '"内文。"'


@pytest.mark.unit
def test_detect_rhetoric_long_unequal_sentences_not_parallel() -> None:
    """F656: [:20] truncation made any 3 long sentences "parallel"; full lengths must not."""
    long_a = "这是一段相当长的句子" * 5 + "甲。"  # >20 chars, unequal tails
    long_b = "这是一段相当长的句子" * 4 + "乙乙乙。"
    long_c = "这是一段相当长的句子" * 6 + "丙丙。"
    result = detect_rhetoric(long_a + long_b + long_c)
    assert result["排比"] == 0


@pytest.mark.unit
def test_detect_rhetoric_equal_length_sentences_parallel() -> None:
    result = detect_rhetoric("他慢慢地走向前去。她静静地坐在那里。它轻轻地叫了一声。")
    assert result["排比"] == 1


@pytest.mark.unit
def test_detect_rhetoric_repetition_deduped_across_ngram_lengths() -> None:
    """F652: one repeated phrase must count once, not once per n-gram length."""
    text = "风吹过山岗。" + "月光洒满大地然后" * 3 + "。"
    result = detect_rhetoric(text)
    assert result["反复"] == 1


@pytest.mark.unit
def test_detect_rhetoric_repetition_independent_phrases_counted_separately() -> None:
    """F652: two disjoint repeated phrases (start vs end) count as 2."""
    text = (
        "主角笑了" * 3 + "之间隔着一大段互不重复的过渡文字甲乙丙丁戊己庚辛壬癸。" + "夜色渐深" * 3
    )
    result = detect_rhetoric(text)
    assert result["反复"] == 2


@pytest.mark.unit
def test_compute_ttr_empty_returns_full_key_set() -> None:
    """F663: early-exit branch must include content_ttr and total_chars."""
    ttr = compute_ttr("")
    assert ttr["global_ttr"] == 0
    assert ttr["content_ttr"] == 0
    assert ttr["total_chars"] == 0
    assert ttr["sliding_ttr_mean"] == 0
    assert ttr["sliding_ttr_std"] == 0


@pytest.mark.unit
def test_segment_sentences_nested_quote_inner_close_does_not_split() -> None:
    """F668: only the outermost closing quote after sentence-final punct splits."""
    sents = segment_sentences("「外层『内层。』外层继续。」他说。")
    assert len(sents) == 2
    assert sents[0][0] == "「外层『内层。』外层继续。」"
