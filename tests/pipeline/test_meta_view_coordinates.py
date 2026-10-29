"""F-6 (probe22 adjudication #006 P2-2 / #009 P2-1): line-anchor offset family.

``_strip_meta_for_non_drafting`` removed the whole ``<!--META-->`` block
(probe22 chapter-2.md L3-L14, 12 lines) from the served view, so every
non-drafting skill — state-settling, the audit wave — counted line anchors
in a view SHORTER than the physical file: a constant +11/12 offset on every
``chapters/chapter-N.md Lxx`` citation, identical across settle AND audits
(they shared the same shifted view) and across chapters. The phrase quotes
were verbatim-real; only the coordinates were wrong, and the revision step
then received fix instructions pointing at the wrong spans.

Fix under test: the strip must be COORDINATE-PRESERVING — each removed
physical line is replaced 1:1 by an inert placeholder, so view line N ==
physical line N. No per-line gutter cost, no quote contamination, and the
±2 anchor tolerance stops leaking a structured block-size offset.
"""

from __future__ import annotations

from shenbi.pipeline.dispatch_helper import _build_skill_prompt, _strip_meta_for_non_drafting

#: probe22 chapters/chapter-2.md layout (verbatim structure): title, blank,
#: 12-line META block L3-L14, blank, prose from L16.
CHAPTER_WITH_META = "\n".join(
    [
        "# Chapter 2:",
        "",
        "<!--META-BEGIN-->",
        "## PRE_WRITE_CHECK",
        "",
        "- 本章核心任务: 抄写三份「自离」页",
        "- 要兑现的伏笔: MH08 种植",
        "<!--META-END-->",
        "",
        "# 自离",
        "",
        "钟伯来的时候，灰雨正敲着铁皮棚顶。",
        "",
        "「会写字的人，」钟伯说，「这矿上就你一个肯替我们写。」",
    ]
)
#: 1-based physical line number of the prose opening line.
PROSE_LINENO = CHAPTER_WITH_META.split("\n").index("# 自离") + 1


def test_meta_replacement_preserves_physical_line_coordinates():
    view = _strip_meta_for_non_drafting("shenbi-state-settling", CHAPTER_WITH_META)
    view_lines = view.split("\n")
    phys_lines = CHAPTER_WITH_META.split("\n")
    assert len(view_lines) == len(phys_lines), "coordinate-preserving strip must keep 1:1 lines"
    assert "PRE_WRITE_CHECK" not in view and "META-BEGIN" not in view
    begin_idx = phys_lines.index("<!--META-BEGIN-->")
    end_idx = phys_lines.index("<!--META-END-->")
    for n, (v, p) in enumerate(zip(view_lines, phys_lines, strict=True), 1):
        if begin_idx < n - 1 < end_idx or (begin_idx <= n - 1 <= end_idx):
            assert v == f"<!--META L{n}-->", (
                f"physical L{n} (block span) must be a placeholder, got {v!r}"
            )
        else:
            assert v == p, f"physical L{n} must be byte-identical in the view, got {v!r}"
    assert view_lines[PROSE_LINENO - 1] == "# 自离"


def test_drafting_and_revision_keep_raw_text():
    assert _strip_meta_for_non_drafting("shenbi-chapter-drafting", CHAPTER_WITH_META) == (
        CHAPTER_WITH_META
    )
    assert _strip_meta_for_non_drafting("shenbi-chapter-revision", CHAPTER_WITH_META) == (
        CHAPTER_WITH_META
    )


def test_served_read_view_keeps_prose_at_physical_line(tmp_path):
    """Integration: the injected chapter read in the assembled prompt carries
    the prose at its physical line position — an anchor cited from the view
    addresses the physical file without arithmetic.
    """
    (tmp_path / "chapters").mkdir(parents=True)
    (tmp_path / "chapters" / "chapter-2.md").write_text(CHAPTER_WITH_META, encoding="utf-8")
    for rel in (
        "truth/current_state.md",
        "truth/character_matrix.md",
        "truth/particle_ledger.md",
        "truth/emotional_arcs.md",
        "truth/subplot_board.md",
        "truth/pending_hooks.md",
        "truth/chapter_summaries.md",
        "audits/chapter-2-foreshadowing.md",
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# stub\n", encoding="utf-8")
    _, user_prompt, _, _, _ = _build_skill_prompt(
        skill="shenbi-state-settling",
        project_dir=tmp_path,
        prompt="settle chapter 2",
        chapter=2,
        uses_staging=True,
    )
    view_lines = user_prompt.split("\n")
    prose_idx = next(i for i, l in enumerate(view_lines) if l == "# 自离")
    # the view inside the prompt is offset by the injection header lines;
    # what matters: the SAME relative spacing — exactly one placeholder line
    # row between the title line and the prose line's META gap (12 → here 5).
    title_idx = next(i for i, l in enumerate(view_lines) if l == "# Chapter 2:")
    # untrusted-source blocks are HTML-escaped in the assembled prompt
    meta_gap = [
        l
        for l in view_lines[title_idx + 1 : prose_idx]
        if l.replace("&lt;", "<").replace("&gt;", ">").startswith("<!--META L")
    ]
    phys = CHAPTER_WITH_META.split("\n")
    block_size = phys.index("<!--META-END-->") - phys.index("<!--META-BEGIN-->") + 1
    assert len(meta_gap) == block_size, (
        f"served view must keep one placeholder row per removed physical line ({block_size}), "
        f"got {len(meta_gap)}"
    )
