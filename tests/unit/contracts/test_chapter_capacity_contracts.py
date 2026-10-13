"""Chapter-phase capacity & registration contracts (probe9 P1/P2-R, 2026-10-02).

probe9 ch1 drafting failed G4.word_count 3x (1595 < 2000) WITH the enriched
feedback in retry state — the escalation reads table rendered correctly
(fix #4c) and the per-attempt record carried 口径+扩写方向, yet the model
never approached the floor. probe7 died the same death (1767, 3x, generic
feedback). The generation-side root cause: chapter-drafting's SKILL carries
NO length contract at all — its only length-adjacent line is the transition-
word budget. The model knows "约2000字" (it computed 转折词预算 from 2000)
but has no caliber definition, no scene-level budgeting, and no
self-measurement obligation, so it writes ~1600 "feels-like" characters.

Same batch: the genesis 总览表 in truth/pending_hooks.md parses to ZERO
hooks in EVERY run ever (probe7/9 genesis outputs AND the real production
fixture all yield 0 from read_pending_hooks — the header-keyed parser only
matches per-chapter tables that cannot exist at genesis), so Route A's hook
index has always been empty at genesis, silently.
"""

from __future__ import annotations

from pathlib import Path

_SKILLS = Path(__file__).parents[3] / "skills"


def _body(skill: str) -> str:
    return (_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 5a — chapter-drafting length contract (capacity family, 2nd recurrence)
# ---------------------------------------------------------------------------


def test_chapter_drafting_pins_length_caliber() -> None:
    body = _body("shenbi-chapter-drafting")
    assert "chapter_word.default" in body
    # The G4 caliber must be pinned so the model can self-measure the same
    # number the gate will read.
    assert "去空白" in body and "剥" in body and "META" in body


def test_chapter_drafting_pins_self_count_line() -> None:
    body = _body("shenbi-chapter-drafting")
    # POST_WRITE_SELF_CHECK template must demand a self-measured count line
    # (probe9 wrote "约2000字" budgets while shipping 1595 actual chars).
    assert "正文字数" in body


def test_chapter_drafting_pins_scene_budgeting() -> None:
    body = _body("shenbi-chapter-drafting")
    assert "场景" in body and "预算" in body


def test_chapter_drafting_pins_per_paragraph_counting() -> None:
    """probe13 (3rd recurrence, human-ruled fix 2026-10-02): the batch-#5
    single-number self-count line ran ~15% high (claimed 1950, actual 1686)
    — a gestalt estimate, not a count. The POST template must demand
    per-paragraph tallies that sum to the total.
    """
    body = _body("shenbi-chapter-drafting")
    assert "逐段" in body
    assert "合计" in body
    assert "禁止整段估数" in body


# ---------------------------------------------------------------------------
# 5d — genesis 总览表 parseable registration (truth-index always-empty hooks)
# ---------------------------------------------------------------------------


def test_foreshadowing_genesis_table_header_is_parser_keyed() -> None:
    """The genesis 总览 template must carry a header the production parser
    keys on (当前生命周期) — every prior genesis output was headerless and
    its own column invention, so Route A indexed zero hooks.
    """
    body = _body("shenbi-foreshadowing-lifecycle")
    assert "当前生命周期" in body
    assert "MH01（" in body  # content rides the parenthetical, per parser


def test_pinned_genesis_table_shape_parses() -> None:
    """The SKILL-pinned genesis table shape must actually yield index rows
    through read_pending_hooks (state + content at minimum).
    """
    import re
    import tempfile

    from shenbi.pipeline.truth_readers import read_pending_hooks

    body = _body("shenbi-foreshadowing-lifecycle")
    m = re.search(
        r"\| Hook ID[^\n]*当前生命周期[^\n]*\|\n\|[-| ]+\|\n((?:\| MH\d+[^\n]+\|\n?)+)", body
    )
    assert m, "genesis template must contain the pinned header + separator + rows"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "truth").mkdir()
        (root / "truth" / "pending_hooks.md").write_text(
            "---\nlast_chapter: 0\n---\n\n# 伏笔池\n\n## 总览\n" + m.group(0),
            encoding="utf-8",
        )
        hooks = read_pending_hooks(root)
        assert hooks, "pinned genesis shape must parse to hook records"
        first = hooks[0]
        assert first["state"] == "PLANTED"
        assert first.get("content"), "hook name must ride the parenthetical"
