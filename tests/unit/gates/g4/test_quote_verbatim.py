"""spec #82 T1 (Task 5): quote anchoring + proxy sliding window."""

from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.gates.g4.quote_verbatim import (
    extract_anchor_quotes,
    extract_meta_quotes,
    quote_in_chapter,
    strip_to_prose,
)

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec82"

CH1 = (FIX / "chapters" / "chapter-1.md").read_text(encoding="utf-8")
CH6 = (FIX / "chapters" / "chapter-6.md").read_text(encoding="utf-8")


@pytest.mark.unit
def test_strip_to_prose_removes_meta() -> None:
    prose = strip_to_prose(
        "<!--SCENE-->\n正文一句。\n<!--META-BEGIN-->\nPOST 引句\n<!--META-END-->\n<!--SCENE-->\n尾段。\n"
    )
    assert "POST" not in prose
    assert "正文一句。" in prose and "尾段。" in prose


@pytest.mark.unit
def test_ch6_quote_present_in_prose() -> None:
    # #83 evidence: ch6 POST claims「册子认得人」— the prose has it
    assert quote_in_chapter("册子认得人", CH6)


@pytest.mark.unit
def test_ch1_meta_only_quote_absent_from_prose() -> None:
    # #83 evidence: ch1 POST 引句 exists only inside the META block
    assert quote_in_chapter("却不知道明天城就破了", CH1) is False


@pytest.mark.unit
def test_extract_anchor_quotes_v4_form() -> None:
    memo = "章尾张力拍: 大｜『他数到第三遍，门被推开一半。』\n"
    assert extract_anchor_quotes(memo) == [("大", "他数到第三遍，门被推开一半。")]
    assert extract_anchor_quotes("plan_format: v3\n章尾张力拍: 章＋形态\n") == []


@pytest.mark.unit
def test_anchor_quote_verdict_e2e(tmp_path: Path) -> None:
    """v4 memo's anchored quote replayed against the real ch6 prose."""
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    d = tmp_path
    (d / "plans").mkdir()
    (d / "chapters").mkdir()
    (d / "plans" / "chapter-6-plan.md").write_text(
        "plan_format: v4\n章尾张力拍: 章｜『册子认得人』\n", encoding="utf-8"
    )
    (d / "chapters" / "chapter-6.md").write_text(CH6, encoding="utf-8")
    import json

    result = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-6.md")], rd=str(d), project_dir=str(d))
    )
    assert not any("quote_verbatim" in m for m in result["must_fix"])

    # flipped: anchored quote that the prose does not carry
    (d / "plans" / "chapter-6-plan.md").write_text(
        "plan_format: v4\n章尾张力拍: 章｜『不存在的引句断言』\n", encoding="utf-8"
    )
    result = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-6.md")], rd=str(d), project_dir=str(d))
    )
    assert any("quote_verbatim" in m for m in result["must_fix"])


@pytest.mark.unit
def test_v4_memo_missing_anchor_form_fails(tmp_path: Path) -> None:
    """audit-T5/I1: v4 memo without the 『』 anchor form → FAIL (template duty)."""
    import json

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    d = tmp_path
    (d / "plans").mkdir()
    (d / "chapters").mkdir()
    (d / "plans" / "chapter-6-plan.md").write_text(
        "plan_format: v4\n章尾张力拍: 章＋形态\n",
        encoding="utf-8",  # v4 duty escaped
    )
    (d / "chapters" / "chapter-6.md").write_text(CH6, encoding="utf-8")
    result = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-6.md")], rd=str(d), project_dir=str(d))
    )
    assert any("缺『』引句锚定形态" in m for m in result["must_fix"])


@pytest.mark.unit
def test_ch17_orphan_meta_end_stripped() -> None:
    """audit-T5/C2: orphan META-END / headered chapters strip correctly."""
    text = (
        "---\ntitle: 头部 frontmatter\n---\n"
        "<!--SCENE-->\n正文一句，册子认得人。\n"
        "<!--META-END-->\n## POST_WRITE_SELF_CHECK\n- 引句「不该在正文里被找到」\n"
    )
    assert quote_in_chapter("不该在正文里被找到", text) is False
    assert quote_in_chapter("册子认得人", text)


@pytest.mark.unit
def test_extract_meta_quotes_seam() -> None:
    """audit-T5/I2(a): #83 T1 extraction seam — meta quotes extracted, prose not."""
    text = (
        "<!--SCENE-->\n正文说「这句在正文里不算声明引句」。\\n"
        "<!--META-BEGIN-->\\nPOST 声明「这句是声明引句要在正文里」\\n<!--META-END-->\\n"
    ).replace("\\n", "\n")
    got = extract_meta_quotes(text)
    assert "这句是声明引句要在正文里" in got
    assert all(q != "这句在正文里" for q in got)


@pytest.mark.unit
def test_v3_memo_skips_anchor_gate(tmp_path: Path) -> None:
    """audit-T5/I1 re-audit: v3 memos (『』 form legally absent) never fire
    the quote_verbatim gate — the v[4-9] scope. Real vol1 ch6 is v3.
    """
    import json

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    d = tmp_path
    (d / "plans").mkdir()
    (d / "chapters").mkdir()
    (d / "plans" / "chapter-6-plan.md").write_text(
        "plan_format: v3\n章尾张力拍: 章＋形态\n", encoding="utf-8"
    )
    (d / "chapters" / "chapter-6.md").write_text(CH6, encoding="utf-8")
    result = json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-6.md")], rd=str(d), project_dir=str(d))
    )
    assert not any("quote_verbatim" in m for m in result["must_fix"])


@pytest.mark.unit
def test_curly_quote_extraction() -> None:
    """Stage-8/M6: curly-quote (“”) declarations are extracted too."""
    text = "<!--META-BEGIN-->\nPOST 声明“这句是弯引号声明要在正文里”\n<!--META-END-->\n<!--SCENE-->\n正文一句。\n"
    got = extract_meta_quotes(text)
    assert "这句是弯引号声明要在正文里" in got


# ── spec #83 T1: nested-aware extraction + paren tail-note position exclusion ──

FIX83 = Path(__file__).resolve().parents[3] / "fixtures" / "spec83"
CH1_83 = (FIX83 / "chapters" / "chapter-1.md").read_text(encoding="utf-8")
CH19_83 = (FIX83 / "chapters" / "chapter-19.md").read_text(encoding="utf-8")


@pytest.mark.unit
def test_spec83_nested_quote_extracted_from_meta() -> None:
    # ch1:231 外层「」内嵌「听不懂的账」——现行字符类排除嵌套括号，r4 实测零命中
    quotes = extract_meta_quotes(CH1_83, min_len=6)
    assert any("听不懂的账" in q and "城就破了" in q for q in quotes)


@pytest.mark.unit
def test_spec83_paren_span_quotes_excluded() -> None:
    # ch19 尾注形（（收束钩：「粥凉了，不算折耗。」…）等 3 条）——位置法：引句起点落在
    # 全角括号区间内即弃。测试内按 match 位置复算未排除面（不含括号内命中）应与提取器一致。
    from shenbi.gates.g4.quote_verbatim import (
        _META_BLOCK_RE,
        _META_SECTION_RE,
        _NESTED_QUOTE_RE,
        _PAREN_SPAN_RE,
        _QUOTE_RE,
    )

    quotes = extract_meta_quotes(CH19_83, min_len=6)
    assert "粥凉了，不算折耗。" not in quotes  # 尾注内引句被位置法弃置
    regions = [m.group(0) for m in _META_BLOCK_RE.finditer(CH19_83)]
    regions += [m.group(0) for m in _META_SECTION_RE.finditer(CH19_83)]
    raw_kept = 0
    paren_hits = 0
    for region in regions:
        spans = [m.span() for m in _PAREN_SPAN_RE.finditer(region)]
        for rx in (_NESTED_QUOTE_RE, _QUOTE_RE):
            for m in rx.finditer(region):
                if len(m.group(1)) < 6:
                    continue
                if any(ps <= m.start() < pe for ps, pe in spans):
                    paren_hits += 1
                else:
                    raw_kept += 1
    assert paren_hits >= 1  # ch19 语料确有括号内引句（排除面非空）
    assert raw_kept == len(quotes)  # 复算与提取器一致


@pytest.mark.unit
def test_spec82_anchor_extraction_unchanged() -> None:
    # #82 面回归（r5.3 注记）：extract_anchor_quotes 用独立『』行正则，不受 _QUOTE_RE 影响
    plan1 = (FIX83 / "plans" / "chapter-1-plan.md").read_text(encoding="utf-8")
    for _tier, q in extract_anchor_quotes(plan1):
        assert q and "「" not in q  # 『』锚面不含「」
    for n in (1, 2, 6, 13, 16, 17, 19, 23, 25, 26, 28, 30, 31, 33, 35):
        text = (FIX83 / "chapters" / f"chapter-{n}.md").read_text(encoding="utf-8")
        assert isinstance(extract_meta_quotes(text, min_len=1), list)  # 全包 15 章提取不崩


@pytest.mark.unit
def test_spec83_nested_span_dedup() -> None:
    # M16：『』嵌套在「」内（ch31 章尾形）——单层命中落在嵌套 span 内则弃（span 级去重）
    from shenbi.gates.g4.quote_verbatim import _NESTED_QUOTE_RE, _QUOTE_RE

    region = "「他写下『制度』『私放』『借』三个词」"
    nested = [m.span() for m in _NESTED_QUOTE_RE.finditer(region)]
    singles = [m for m in _QUOTE_RE.finditer(region)]
    assert nested and singles
    assert all(any(ns <= m.start() < ne for ns, ne in nested) for m in singles)
    # 『』片段全部落在嵌套 span 内——提取器须弃置（span 去重义务的行为前提）


@pytest.mark.unit
def test_spec83_min_len_one_and_golden_lines() -> None:
    # T2 消费面预演：min_len=1 时 1 字引句（ch6「查」形）入提取集（逃逸面已知注记）
    quotes = extract_meta_quotes(CH1_83, min_len=1)
    assert quotes  # 非空即提取面活着；逐字臂判定归 T2 门
