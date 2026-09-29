"""Bespoke error-path tests for g4_chapter_drafting.

The parametrized harness in test_all_skills_parametrized.py covers the COMMON
contract (empty input, missing file, gate field, etc.). This file covers the
checker-SPECIFIC business rules: content overlap, visual scene, chapter-end
hook, PRE/POST check blocks, transition-word density, and fatigue words.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_drafting import check_hook_fulfillment, g4_chapter_drafting


def _run(fps: list[str], rd: str | None = None) -> dict[str, Any]:
    return json.loads(g4_chapter_drafting(fps, rd))


def _must_fix(result: dict[str, Any]) -> list[str]:
    return result.get("must_fix", [])


# CJK paragraphs long enough (>=50 chars) to be fingerprinted for overlap.
_FP_PARA_A = "他沿着小路慢慢走着看着远方心中想着未来的种种可能不知道该如何是好。" * 2
_FP_PARA_B = "她站在窗前静静望着天空回想着过去发生的种种事情感到十分无奈。" * 2


@pytest.mark.unit
def test_fails_when_content_overlap_above_40_percent(tmp_path: Path) -> None:
    """Two near-identical chapters (>40% shared paragraphs) -> FAIL.

    The overlap check only runs when a round_dir is supplied and a sibling
    chapter exists under project-output/chapters.
    """
    rd = tmp_path / "round"
    chapters = rd / "project-output" / "chapters"
    chapters.mkdir(parents=True)
    body = f"{_FP_PARA_A}\n\n{_FP_PARA_B}\n"
    ch1 = chapters / "chapter-001.md"
    ch2 = chapters / "chapter-002.md"
    ch1.write_text(body, encoding="utf-8")
    ch2.write_text(body, encoding="utf-8")

    result = _run([str(ch1)], str(rd))
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.cd.content_overlap" in m for m in mf)


@pytest.mark.unit
def test_fails_when_no_visual_scene(tmp_path: Path) -> None:
    """No paragraph with >=200 CJK chars of visual narrative -> FAIL."""
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n抽象的叙述内容。\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.cd.no_visual_scene" in m for m in mf)


@pytest.mark.unit
def test_fails_when_no_chapter_end_hook(tmp_path: Path) -> None:
    """Last paragraph (>=30 CJK) with no question/tension marker -> FAIL."""
    ch = tmp_path / "chapter-001.md"
    plain_end = "他回到了家中休息吃饭睡觉度过了一个平淡无奇的夜晚时光然后入睡。"
    ch.write_text(f"# 章节\n\n{plain_end}\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.cd.no_hook" in m for m in mf)


@pytest.mark.unit
def test_fails_when_pre_write_check_missing(tmp_path: Path) -> None:
    """Missing ## PRE_WRITE_CHECK block -> must_fix.

    pins current behavior: the plan labeled this WARN, but the checker appends
    G4.pre_check to must_fix, which makes the whole gate FAIL.
    """
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n他回到了家中。\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.pre_check" in m for m in mf)


@pytest.mark.unit
def test_fails_when_post_write_check_missing(tmp_path: Path) -> None:
    """PRE_WRITE_CHECK present but POST_WRITE_SELF_CHECK absent -> must_fix.

    pins current behavior: treated as FAIL (must_fix), not WARN.
    """
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n## PRE_WRITE_CHECK\n内容。\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.post_check" in m for m in mf)


@pytest.mark.unit
def test_fails_when_transition_density_too_high(tmp_path: Path) -> None:
    """Transition-word count exceeds the 1-per-3000-words budget -> FAIL."""
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n" + "此时终于于是" * 3 + "\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.transition" in m for m in mf)


@pytest.mark.unit
def test_fails_when_fatigue_words_exceeded(tmp_path: Path) -> None:
    """More than 8 fatigue-word hits -> FAIL (threshold relaxed from 3).

    Uses fatigue words that are NOT transition words (猛地/瞬间/一股/恐怖) so
    the failure is attributable to the fatigue check, not transition density.
    """
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n" + "猛地瞬间一股恐怖" * 3 + "\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert result["status"] == "FAIL"
    assert any("G4.fatigue" in m for m in mf)


# ── Task 6: Protagonist Presence ───────────────────────────────────────────


def test_protagonist_presence_check_detects_absence():
    """G4.cd.protagonist_presence fails when protagonist appears < 3 times."""
    from shenbi.gates.g4.chapter_drafting import _check_protagonist_presence

    text = "参数知道深度在第X层——光在场于第三日"  # No protagonist names
    protagonist_names = ["林烽", "他"]

    issues = _check_protagonist_presence(text, protagonist_names, threshold=3)
    assert len(issues) > 0
    assert "protagonist_absent" in issues[0]


def test_protagonist_presence_check_passes_with_sufficient_mentions():
    """G4 check passes when protagonist appears >= threshold."""
    from shenbi.gates.g4.chapter_drafting import _check_protagonist_presence

    text = "林烽握紧拳头。他看着前方。林烽知道这一战不可避免。他深吸一口气。"
    protagonist_names = ["林烽", "他"]

    issues = _check_protagonist_presence(text, protagonist_names, threshold=3)
    assert len(issues) == 0


# ── Task 11: META Stripping Warning ─────────────────────────────────────────


def test_chapter_drafting_skill_has_meta_warning_block():
    """The chapter-drafting SKILL.md must have a prominent META stripping warning."""
    skill_path = (
        Path(__file__).resolve().parents[4] / "skills" / "shenbi-chapter-drafting" / "SKILL.md"
    )
    content = skill_path.read_text(encoding="utf-8")
    assert "WARNING" in content or "IMPORTANT" in content
    assert "META" in content
    assert "strip" in content.lower() or "not prose" in content.lower()


# --- Spec #35 (F443): no project-specific protagonist fallback -------------
def test_no_protagonist_data_returns_empty(tmp_path: Path) -> None:
    from shenbi.gates.g4.chapter_drafting import _load_protagonist_names

    assert _load_protagonist_names(str(tmp_path)) == []


def test_no_hardcoded_fallback_names() -> None:
    import inspect

    from shenbi.gates.g4 import chapter_drafting

    assert "林烽" not in inspect.getsource(chapter_drafting)


def test_absent_protagonist_data_skips_check(tmp_path: Path) -> None:
    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    # no characters/ dir at all → empty names → SKIP record, not FAIL
    fp = tmp_path / "chapter-1.md"
    fp.write_text("正文\n", encoding="utf-8")
    r = json.loads(g4_chapter_drafting([str(fp)], project_dir=str(tmp_path)))
    skip_checks = [c for c in r.get("checks", []) if c.get("id") == "G4.cd.protagonist_presence"]
    assert any(c.get("s") == "SKIP" for c in skip_checks)


@pytest.mark.c13_regression
def test_hook_ids_outside_ledger_section_ignored(tmp_path) -> None:
    """F749: hook IDs appearing only outside the Hook Ledger section are not
    requirements (docstring says Section 7 — implementation now matches).
    """
    plan = tmp_path / "plan.md"
    plan.write_text(
        """# 章节计划

## Section 3 场景备注

曾参考 hook MH-999 的历史记录。

## Section 7 Hook Ledger

- 无本章需兑现钩子
""",
        encoding="utf-8",
    )
    chapter = tmp_path / "chapter-001.md"
    chapter.write_text("正文没有出现任何钩子编号。\n", encoding="utf-8")
    issues = check_hook_fulfillment(plan, chapter)
    assert issues == []


@pytest.mark.c13_regression
def test_hook_ids_inside_ledger_section_enforced(tmp_path) -> None:
    """F749 positive control: ledger-declared hooks are still enforced."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        """# 章节计划

## Section 7 Hook Ledger

- MH-003 必须兑现
""",
        encoding="utf-8",
    )
    chapter = tmp_path / "chapter-001.md"
    chapter.write_text("正文没有出现任何钩子编号。\n", encoding="utf-8")
    issues = check_hook_fulfillment(plan, chapter)
    assert any("MH-003" in i for i in issues)


# ---------------------------------------------------------------------------
# Windowed visual-scene measure (canary escalation #13): web-novel prose
# uses 50-100 CJK paragraphs — a single-paragraph >=100 measure never fires
# on the style the SKILL itself teaches.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_visual_scene_window_two_short_paragraphs_pass(tmp_path: Path) -> None:
    """Two consecutive short visual paragraphs (99 + 40 CJK) satisfy the
    windowed measure — the exact canary shape (99-CJK rift description
    one char short of the legacy single-paragraph threshold).
    """
    p1 = "不是光。" + "他看见那道白从地面切进空气里。" * 8  # ~99 CJK, vn=True
    p2 = "他往后退了半步，伸手去抓门框，指尖碰到的是湿的木头。" * 1  # vn=True
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{p1}\n\n{p2}\n", encoding="utf-8")

    result = _run([str(ch)])

    assert result["status"] != "FAIL" or not any("no_visual_scene" in m for m in _must_fix(result))


@pytest.mark.unit
def test_visual_scene_pure_introspection_still_fails(tmp_path: Path) -> None:
    """Long introspective paragraphs without visual verbs or dialogue still
    fail — the window does not hollow out the check.
    """
    p1 = "他想起许多关于过去的细节。" * 10  # >=100 CJK, no vn, no di
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{p1}\n", encoding="utf-8")

    result = _run([str(ch)])
    mf = _must_fix(result)

    assert any("G4.cd.no_visual_scene" in m for m in mf)


# ---------------------------------------------------------------------------
# Probe escalation #4 (novel-xinghuo-probe, 2026-09-28): three 口径 defects —
# transition count included the framework's own PRE_WRITE_CHECK checklist,
# the word floor was CJK-only against a memo layer that plans in total chars,
# and the end-hook window saw only the final (stylistic beat) paragraph.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_transition_words_in_meta_sections_not_counted(tmp_path: Path) -> None:
    """PRE/POST check blocks enumerate transition words themselves — counting
    raw content made the gate count its own checklist (probe ch1: 8 raw,
    2 real). The count must run on the stripped narrative body.
    """
    body = "他沿着矿道走了很久没有说话也没有停下来的意思只是继续往前走去。" * 20
    meta = (
        "## PRE_WRITE_CHECK\n"
        "- 转折词预算: 此时/突然/终于/于是/然 各计一次\n\n"
        "## POST_WRITE_SELF_CHECK\n"
        "- 转折词密度: 0（此时 突然 终于 于是 然 虽然然而当然自然忽然）\n"
    )
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n\n{meta}", encoding="utf-8")

    result = _run([str(ch)])

    assert not any("G4.transition" in m for m in _must_fix(result))


@pytest.mark.unit
def test_word_floor_passes_on_total_chars_when_cjk_short(tmp_path: Path) -> None:
    """A plan-compliant chapter (~2860 CJK + punctuation ≈ 3400 total) must
    pass the 3000 floor on the total 口径 — CJK-only demanded ≈3565 total and
    no plan-compliant chapter could ever pass (production ch36/37/39/41).
    """
    # ~2940 CJK + 420 full-width punctuation = ~3360 total
    body = "他沿着矿道往前走，看了看手里的名册，又放回怀里。" * 140
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n\n## PRE_WRITE_CHECK\n- 预算\n", encoding="utf-8")

    result = _run([str(ch)])

    assert not any("G4.word_count" in m for m in _must_fix(result))


@pytest.mark.unit
def test_word_floor_still_fails_genuinely_short_chapter(tmp_path: Path) -> None:
    """The total 口径 must not hollow out the floor: a chapter far below 3000
    total chars still fails.
    """
    ch = tmp_path / "chapter-001.md"
    ch.write_text("# 章节\n\n他回到了家中。\n", encoding="utf-8")

    result = _run([str(ch)])

    assert any("G4.word_count" in m for m in _must_fix(result))


@pytest.mark.unit
def test_end_hook_window_catches_tension_in_closing_beat(tmp_path: Path) -> None:
    """Stylistic web-novel closure: tension lands a few paragraphs before the
    final image paragraph (probe ch1: explicit 不知 at -5, clean image at -1).
    The window of 5 must accept it.
    """
    tension = "他不知道那个数是从哪儿冒出来的，说不清，像有人替他把一本账翻到了底。" * 2
    beats = "\n\n".join(["他张了张嘴。", '"二十四。"他说。', "灯花爆了一下。", "他吹灭了灯。"])
    closing = "黑暗里，那串木牌在腰间轻轻响了一声，又一声，没了动静。"
    body = "他沿着矿道往前走，看了看手里的名册，又放回怀里。" * 30
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n\n{tension}\n\n{beats}\n\n{closing}\n", encoding="utf-8")

    result = _run([str(ch)])

    assert not any("G4.cd.no_hook" in m for m in _must_fix(result))


@pytest.mark.unit
def test_end_hook_window_still_fails_flat_ending(tmp_path: Path) -> None:
    """Non-vacuous control: five closing paragraphs with no question or
    tension marker in any of them still fail the windowed hook check.
    """
    body = "他沿着矿道往前走，看了看手里的名册，又放回怀里。" * 140
    flat = "\n\n".join(
        [
            "他回到了家中坐下来，安安静静地吃了一碗温热的饭食，洗净了手上的尘土。",
            "他躺到草席上面，闭上了眼睛，听着屋顶上面细碎的风声过了一阵。",
            "第二日清晨的钟声敲响之前，他睡得很沉，一个梦也没有做成。",
            "他醒来之后收拾好衣物，跟着众人一道走到矿道入口处排队。",
            "这一天平淡无奇地过去了，同之前的许多个日子一模一样。",
        ]
    )
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n\n{flat}\n", encoding="utf-8")

    result = _run([str(ch)])

    assert any("G4.cd.no_hook" in m for m in _must_fix(result))


@pytest.mark.unit
def test_word_floor_reads_genre_config_chapter_word_default(tmp_path: Path) -> None:
    """Probe escalation #9: the floor must come from genre-config
    chapter_word.default — the same number G0.3/G6 use for chapter-count
    math. A 1500-default plan (134 chapters from 200k) structurally cannot
    satisfy the hardcoded 3000 constant: every memo-faithful chapter failed.
    """
    gc = tmp_path / "genre-config.json"
    gc.write_text('{"chapter_word": {"default": 1500}}', encoding="utf-8")
    body = "他沿着矿道往前走，看了看手里的名册，又放回怀里。" * 80  # ~1920 total
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n\n## PRE_WRITE_CHECK\n- 预算\n", encoding="utf-8")

    result = _run([str(ch)], str(tmp_path))

    assert not any("G4.word_count" in m for m in _must_fix(result))


@pytest.mark.unit
def test_word_floor_config_value_is_enforced(tmp_path: Path) -> None:
    """The config floor is a real floor: a chapter below the configured
    default still fails (non-vacuous control for the config read).
    """
    gc = tmp_path / "genre-config.json"
    gc.write_text('{"chapter_word": {"default": 2900}}', encoding="utf-8")
    body = "他沿着矿道往前走，看了看手里的名册，又放回怀里。" * 80  # ~1920 total < 2900
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n\n## PRE_WRITE_CHECK\n- 预算\n", encoding="utf-8")

    result = _run([str(ch)], str(tmp_path))

    assert any("G4.word_count" in m for m in _must_fix(result))


@pytest.mark.unit
def test_visual_scene_micro_paragraph_style_passes(tmp_path: Path) -> None:
    """Probe escalation #37: extreme micro-paragraph prose (~13 CJK/para)
    never reaches 100 CJK inside a 3-paragraph window — the visual-scene
    check structurally could not fire on that style. Windows up to 8 keep
    the mass requirement and scale the density requirement.
    """
    p = "他沿着矿道慢慢走到门边看了很久。"  # 15 CJK, vn=True
    body = "\n\n".join([p] * 12)  # ~180 CJK, ~15/para micro style
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n", encoding="utf-8")

    result = _run([str(ch)])

    assert not any("no_visual_scene" in m for m in _must_fix(result))


@pytest.mark.unit
def test_end_hook_concealment_tension_counts(tmp_path: Path) -> None:
    """Probe escalation #38: concealment closures ("他没说……") are unresolved
    tension — the regex family lacked the 没说/瞒/藏 markers and the stylistic
    ending (no question marks anywhere) structurally failed the hook check.
    """
    tension = "他没说自己先读到了那个数，也没说那一格他认得，压在盐引底下写得很小。" * 2
    beats = "\n\n".join(
        ["「没怎么。」", "火盆里的炭褪了一层红。", "他抬头看了一眼铜盘。", "袖口的炭条往里按了按。"]
    )
    closing = "那一格，占了。"
    body = "他沿着矿道往前走，看了看手里的名册，又放回怀里。" * 30
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n\n{tension}\n\n{beats}\n\n{closing}\n", encoding="utf-8")

    result = _run([str(ch)])

    assert not any("G4.cd.no_hook" in m for m in _must_fix(result))


@pytest.mark.unit
def test_hook_ledger_markup_not_prose(tmp_path: Path) -> None:
    """Probe escalation #39: <!--HOOK-BEGIN--> ledger blocks are machine
    markup — left in the prose paragraph list, the markup line became the
    "last paragraph" and short-circuited the end-hook window.
    """
    para = "他沿着矿道往前走，看了看手里的名册，又放回怀里。"
    body = "\n\n".join([para] * 20)  # micro-normal mix, none with tension
    beats = "\n\n".join(["「多少。」", "林渡没答。", "他抬手把指针拨回一格。"])
    ledger = "<!--HOOK-BEGIN-->\nhook_id: MH-005\n章尾钩子: 机器标记\n<!--HOOK-END-->"
    ch = tmp_path / "chapter-001.md"
    ch.write_text(f"# 章节\n\n{body}\n\n{beats}\n\n{ledger}\n", encoding="utf-8")

    result = _run([str(ch)])

    assert not any("G4.cd.no_hook" in m for m in _must_fix(result))
