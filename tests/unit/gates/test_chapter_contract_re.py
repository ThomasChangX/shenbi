"""z11 R1a: chapter-contract regex single source (SDD #20, F1301/F1302)."""

from shenbi.gates.shared import CHAPTER_HEADER_RE, META_BLOCK_RE


def test_chapter_header_re_matches_contract_form() -> None:
    assert CHAPTER_HEADER_RE.match("# Chapter 1:")
    assert CHAPTER_HEADER_RE.match("# Chapter 56: 星火")
    assert not CHAPTER_HEADER_RE.match("## Chapter 1")  # h2 不算
    assert not CHAPTER_HEADER_RE.match("Chapter 1")  # 无 # 前缀


def test_meta_block_re_is_single_source() -> None:
    assert META_BLOCK_RE.search("正文\n<!--META-BEGIN-->\nfoo\n<!--META-END-->\n尾")
    # g2 的 _META_RE 是 shared 的别名（单源，z11 F1301）——同对象即同 pattern
    from shenbi.gates.shared import META_BLOCK_RE as AGAIN

    assert AGAIN is META_BLOCK_RE
