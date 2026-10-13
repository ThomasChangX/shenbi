"""Output-envelope & increment contracts (probe14 batch #9, 2026-10-02).

probe14 died twice on one family: the shared decisions-sidecar boilerplate
(「该文件必须是纯 JSON…禁止任何前后缀文字」) literally contradicts the
dispatcher-injected ### FILE envelope — state-settling collapsed a 39864-token
settle into a 1264-char bare sidecar (8 declared paths quarantined), and
genesis step 12 drifted into an unparseable {"files":[...]} envelope. Same
batch pins the goal-word-count line (probe13+probe14 both needed adjudication
M1 to add it) and the settle increment envelope skeleton.
"""

from __future__ import annotations

from pathlib import Path

_SKILLS = Path(__file__).parents[3] / "skills"


def _body(skill: str) -> str:
    return (_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


def test_sidecar_boilerplate_scoped_to_block_interior() -> None:
    """The boilerplate must no longer forbid text outside the JSON — the
    ### FILE marker line and sibling file blocks are required (probe14 #13).
    """
    for skill in (
        "shenbi-state-settling",
        "shenbi-chapter-drafting",
        "shenbi-chapter-planning",
    ):
        body = _body(skill)
        assert "禁止 markdown 标题、围栏代码块或任何前后缀文字" not in body, skill
        assert "### FILE 块内容必须是纯 JSON" in body, skill


def test_state_settling_pins_file_envelope_skeleton() -> None:
    """The output-format section must SHOW the ### FILE envelope with the
    increment forms — prose rules alone lost to the boilerplate conflict
    (probe14 #14).
    """
    body = _body("shenbi-state-settling")
    assert "### FILE: truth/current_state.md" in body
    assert "### FILE: truth/state-settling-decisions.json" in body
    assert "last_reinforced: 1" in body  # pending_hooks increment example
    assert "### MH09" in body


def test_chapter_planning_pins_goal_word_count_line() -> None:
    """probe13 M1 AND probe14 M1 both had to add the 目标字数 line by
    adjudication — the template must demand it (P2-R①, two-probe recurrence).
    """
    body = _body("shenbi-chapter-planning")
    assert "**目标字数**" in body
    assert "chapter_word.default" in body


def test_chapter_planning_phase1_placeholder_is_conditional() -> None:
    """The Phase-1 placeholder branch must forbid emitting 占位声明 when the
    hook pool is populated (probe14 M2: 14 hooks in pool, model still copied
    the placeholder note — a false self-attestation).
    """
    body = _body("shenbi-chapter-planning")
    assert "严禁输出「尚未实现/占位声明」类字样" in body


def test_thread_map_template_has_frontmatter() -> None:
    """thread_map shipped header-less twice (probe13/14 O2 recurrence) —
    the template pins frontmatter like volume_map/rhythm_principles.
    """
    body = _body("shenbi-plot-thread-weaver")
    assert "---\ntotal_chapters: X\nupdated_at: YYYY-MM-DD\n---" in body


def test_book_spine_reads_pending_hooks_pool() -> None:
    """MH numbering must inherit from the foreshadowing pool — two
    independent numbering systems broke the per-chapter tracker contract
    (probe14 genesis M1: 11 shared ids, all pointing at different hooks).
    """
    body = _body("shenbi-book-spine-init")
    assert "- truth/pending_hooks.md" in body
    assert "逐钩继承" in body


def test_foreshadowing_resolve_binds_report_to_audits_file() -> None:
    """phase3 esc#3 (ch23, first-ever volume boundary): the output template
    taught an H2-led report as the content of truth/pending_hooks.md — the
    only writable target, whose ingestion guard bans exactly that scaffold.
    No ≤5-chapter probe ever reached the boundary, so the contradiction
    survived every probe. The template must bind the report to an audits
    file and teach the hooks increment form for the truth target.
    """
    body = _body("shenbi-foreshadowing-resolve")
    assert "audits/volume-N-foreshadowing.md" in body
    # the truth target is taught as increments, not as the report file
    assert "### FILE: truth/pending_hooks.md" in body
    assert "### MHxx" in body


def test_hook_keyed_writers_teach_increment_form() -> None:
    """Generalized esc#3 scan: every skill with an append_dedup hook_id
    target must teach the ``### MHxx`` increment form in its output
    template — a template that never shows the sanctioned form loses to
    its own boilerplate (esc#1/esc#2/esc#3, three members of one family).
    """
    import re

    for skill_md in sorted(_SKILLS.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        if not re.search(r"mode:\s*append_dedup\s*\n\s*key:\s*hook_id", text):
            continue
        assert re.search(r"### MH(xx|\d+)", text), skill_md.parent.name
