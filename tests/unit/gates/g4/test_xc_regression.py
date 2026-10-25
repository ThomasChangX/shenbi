"""Spec #75 acceptance regression: the five real wounds of the old vol-1 run.

The fixture corpus (tests/fixtures/cross-chapter-regression/) is the old
nine-chapter vol-1 run where every one of the five wounds looked
chapter-locally fine — the exact blind spot this gate exists to close.
Each wound must surface as a FAIL issue naming it; a clean adjacent pair
must produce none; the checks must be pure (double-run identical, no file
side effects) and degrade loudly-but-safely when the registry layer is
absent (WARN, not silence).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from shenbi.gates.g4.cross_chapter import check_cross_chapter, g4_cross_chapter

FIX = Path(__file__).resolve().parents[4] / "tests/fixtures/cross-chapter-regression"


def _wounds(chapter: int) -> list[str]:
    """Issues for fixture chapter N vs N-1 (fixture root as project dir)."""
    from shenbi.gates.g4.cross_chapter import CrossChapterContext

    cur = FIX / "chapters" / f"chapter-{chapter}.md"
    prev = FIX / "chapters" / f"chapter-{chapter - 1}.md" if chapter > 1 else None
    memo = FIX / "plans" / f"chapter-{chapter}-plan.md"
    return check_cross_chapter(
        cur,
        prev,
        memo if memo.is_file() else None,
        CrossChapterContext(project_dir=FIX, registry_dir=FIX / "truth"),
    )


@pytest.mark.unit
def test_wound1_ch2_pov_break() -> None:
    """ch1 我-narration vs ch2 他-narration with no POV change declaration."""
    wounds = _wounds(2)
    assert any("POV 人称断裂" in w for w in wounds), wounds


@pytest.mark.unit
def test_wound2_protagonist_called_deng() -> None:
    """ch4-5 narrate the protagonist as 灯 — outside the name whitelist."""
    wounds = _wounds(5)
    assert any("称谓违例" in w and "灯" in w for w in wounds), wounds


@pytest.mark.unit
def test_wound3_timeline_rollback_ch2() -> None:
    """ch1 ends on 初十, ch2 opens on 初七/初八 — anchor rollback, no marker."""
    wounds = _wounds(2)
    assert any("时间锚回拨" in w for w in wounds), wounds


@pytest.mark.unit
def test_wound4_prop_chain_break(tmp_path: Path) -> None:
    """The red-paper bundle changes hands with no 经手 declaration.

    The old pre-#75 run kept no prop registry — the chain 小满→萤→老妇→
    井台女 was unrecoverable. Here the registry layer is a constructed
    structural input (G0.9: no real #75-era skill output exists for a file
    this spec introduces) recording the ch1 end-state; the ch2 mention
    then has no hand-off declaration to legitimate it.
    """
    from shenbi.gates.g4.cross_chapter import CrossChapterContext

    truth = tmp_path / "truth"
    truth.mkdir()
    (truth / "prop_registry.md").write_text(
        "| 实体 | owner | 事件 |\n|---|---|---|\n| 红纸包 | 小满→我(ch1) | ch1 收下 |\n",
        encoding="utf-8",
    )
    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()
    (ch_dir / "chapter-1.md").write_text(
        "---\nprovenance: real-output\n---\n\n他收下红纸包。", encoding="utf-8"
    )
    # round-2 rule: only TRANSFER contexts demand the memo 物象 line; the
    # wound's constructed form is a hand-off with no declaration.
    (ch_dir / "chapter-2.md").write_text(
        "---\nprovenance: real-output\n---\n\n他把红纸包递给了老妇。",
        encoding="utf-8",
    )
    memo = tmp_path / "plans" / "chapter-2-plan.md"
    memo.parent.mkdir()
    memo.write_text(
        "### 场景预算与收束钩\n- 时间锚: 腊月初十\n- 余额: 十文\n- POV: 他\n",
        encoding="utf-8",
    )
    issues = check_cross_chapter(
        ch_dir / "chapter-2.md",
        ch_dir / "chapter-1.md",
        memo,
        CrossChapterContext(project_dir=tmp_path, registry_dir=truth),
    )
    assert any("红纸包" in w and "无经手声明" in w for w in issues), issues


@pytest.mark.unit
def test_wound5_xiaoman_card_conflict() -> None:
    """xiao-man's card pronoun/organization conflicts with the prose."""
    wounds = _wounds(1)
    assert any("卡" in w and ("代词" in w or "机构" in w) for w in wounds), wounds


@pytest.mark.unit
def test_clean_adjacent_pair_zero_false_positive(tmp_path: Path) -> None:
    """True negative: a constructed clean adjacent pair yields no issues."""
    from shenbi.gates.g4.cross_chapter import CrossChapterContext

    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()
    filler = "他" * 4 + "数了一遍。" * 30
    (ch_dir / "chapter-1.md").write_text(
        "---\nprovenance: real-output\n---\n\n他推门。腊月初一。" + filler,
        encoding="utf-8",
    )
    (ch_dir / "chapter-2.md").write_text(
        "---\nprovenance: real-output\n---\n\n他出门。腊月初二。" + filler,
        encoding="utf-8",
    )
    issues = check_cross_chapter(
        ch_dir / "chapter-2.md",
        ch_dir / "chapter-1.md",
        None,
        CrossChapterContext(project_dir=tmp_path, registry_dir=tmp_path / "truth"),
    )
    assert issues == [], issues


@pytest.mark.unit
def test_registry_absence_warn_not_fail(tmp_path: Path) -> None:
    """WARN state: registry tables absent → XC.registry WARN, gate still PASS."""
    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()
    filler = "他" * 4 + "数了一遍。" * 30
    (ch_dir / "chapter-1.md").write_text(
        "---\nprovenance: real-output\n---\n\n他推门。腊月初一。" + filler, encoding="utf-8"
    )
    (ch_dir / "chapter-2.md").write_text(
        "---\nprovenance: real-output\n---\n\n他出门。腊月初二。" + filler, encoding="utf-8"
    )
    result = json.loads(
        g4_cross_chapter([str(ch_dir / "chapter-2.md")], rd=str(ch_dir), project_dir=str(tmp_path))
    )
    warns = [c for c in result["checks"] if c["id"] == "XC.registry" and c["s"] == "WARN"]
    assert len(warns) == 3, result["checks"]
    assert result["status"] == "PASS"


@pytest.mark.unit
def test_pure_idempotent_no_side_effects(tmp_path: Path) -> None:
    """Idempotence + purity: double run → identical output, files untouched."""
    import hashlib

    from shenbi.gates.g4.cross_chapter import CrossChapterContext

    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()
    filler = "他" * 4 + "数了一遍。" * 30
    (ch_dir / "chapter-1.md").write_text(
        "---\nprovenance: real-output\n---\n\n他推门。腊月初一。" + filler, encoding="utf-8"
    )
    (ch_dir / "chapter-2.md").write_text(
        "---\nprovenance: real-output\n---\n\n他出门。腊月初三。" + filler, encoding="utf-8"
    )
    ctx = CrossChapterContext(project_dir=tmp_path, registry_dir=tmp_path / "truth")

    def _snapshot(root: Path) -> dict[str, str]:
        return {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    before = _snapshot(tmp_path)
    run1 = check_cross_chapter(ch_dir / "chapter-2.md", ch_dir / "chapter-1.md", None, ctx)
    run2 = check_cross_chapter(ch_dir / "chapter-2.md", ch_dir / "chapter-1.md", None, ctx)
    assert run1 == run2
    assert _snapshot(tmp_path) == before, "gate must not mutate any input file"


# ---------- final-review fix batch: false-positive pins + new coverage ----------


@pytest.mark.unit
@pytest.mark.parametrize("n", [6, 8, 9, 10])
def test_clean_chapters_zero_naming_hits(n: int) -> None:
    """Final-review C1 pin: non-wound chapters must produce NO 称谓违例.

    The pre-fix gate fired on 灯芯/灯花/点灯 compounds and side-character
    actions (小满/萤) — 5 spurious FAILs on 4 clean chapters.
    """
    wounds = _wounds(n)
    assert not any("称谓违例" in w or "禁用名" in w for w in wounds), wounds


@pytest.mark.unit
def test_wound2b_ch7_reserved_name_hijack() -> None:
    """Final-review Missing pin: ch7 井台女 carries the heroine's reserved
    name — dialogue vocative + 她-co-ref paragraphs must trip the hijack.
    """
    wounds = _wounds(7)
    assert any("禁用名" in w and "灯" in w for w in wounds), wounds


@pytest.mark.unit
@pytest.mark.parametrize(
    ("probe", "want"),
    [
        ("腊月二十九", (12, 29)),
        ("腊月二十一", (12, 21)),
        ("腊月三十", (12, 30)),
        ("12月7日", (12, 7)),
        ("过了二十九天", None),
        ("二十两银子", None),
    ],
)
def test_twenty_and_arabic_day_forms(probe: str, want: tuple[int, int] | None) -> None:
    """Final-review C4 pin: every 二十X form previously parsed as day 2."""
    from shenbi.gates.g4.cross_chapter import normalize_anchor

    assert normalize_anchor(probe, None) == want


@pytest.mark.unit
def test_year_wrap_not_rollback() -> None:
    """腊月末 → 正月 is FORWARD (year wrap), never a rollback flag."""
    issues = _wounds(8)  # ch7 ends 腊月, ch8 opens 正月初一 — clean seam
    assert not any("时间锚回拨" in w for w in issues), issues


@pytest.mark.unit
def test_mixed_pov_declarable() -> None:
    """A declared 混称 chapter must not be an undeclarable POV dead end."""
    from shenbi.gates.g4.cross_chapter import CrossChapterContext, check_cross_chapter

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        filler = "他数了一遍。" * 40
        (d / "chapter-1.md").write_text("他推门。" + filler, encoding="utf-8")
        mixed = "他数了一遍。" * 20 + "我看着他，他又看我。我又看他。" * 12
        (d / "chapter-2.md").write_text(mixed, encoding="utf-8")
        memo = d / "chapter-2-plan.md"
        memo.write_text(
            "### 场景预算与收束钩\n- 时间锚: 腊月初十\n- 余额: 十文\n- POV: 混称\n",
            encoding="utf-8",
        )
        issues = check_cross_chapter(
            d / "chapter-2.md",
            d / "chapter-1.md",
            memo,
            CrossChapterContext(project_dir=d),
        )
        assert not any("POV" in i for i in issues), issues


@pytest.mark.unit
def test_event_reconciliation_mismatch_flagged() -> None:
    """A 1-文 event declaration cannot exempt a 180-文 jump."""
    from shenbi.gates.g4.cross_chapter import CrossChapterContext, check_cross_chapter

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text("他推门。" + "他数了一遍。" * 40, encoding="utf-8")
        (d / "chapter-2.md").write_text("他出门。" + "他数了一遍。" * 40, encoding="utf-8")
        memo = d / "chapter-2-plan.md"
        memo.write_text(
            "### 场景预算与收束钩\n"
            "- 时间锚: 腊月初十\n"
            "- 余额: 一百九十文\n"
            "- POV: 他\n"
            "- 事件: 支出|一文|买饼\n",
            encoding="utf-8",
        )
        (d / "plans").mkdir()
        prev_memo = d / "plans" / "chapter-1-plan.md"
        prev_memo.write_text(
            "### 场景预算与收束钩\n- 时间锚: 腊月初九\n- 余额: 十文\n- POV: 他\n",
            encoding="utf-8",
        )
        issues = check_cross_chapter(
            d / "chapter-2.md",
            d / "chapter-1.md",
            memo,
            CrossChapterContext(project_dir=d),
        )
        assert any("对账不符" in i for i in issues), issues


@pytest.mark.unit
def test_prev_gap_warns() -> None:
    """Chapter numbering gap → XC.prev_missing WARN, seam checks skipped."""
    import json as _json

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-3.md").write_text(
            "---\nprovenance: real-output\n---\n\n他推门。腊月初十。" + "他数了一遍。" * 40,
            encoding="utf-8",
        )
        result = _json.loads(g4_cross_chapter([str(d / "chapter-3.md")], rd=str(d), project_dir=td))
        warns = [c for c in result["checks"] if c["id"] == "XC.prev_missing" and c["s"] == "WARN"]
        assert warns, result["checks"]


@pytest.mark.unit
def test_relative_anchor_warns() -> None:
    """Month names with no parseable absolute anchor → visible WARN."""
    import json as _json

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "chapter-1.md").write_text(
            "---\nprovenance: real-output\n---\n\n他推门。入了腊月，天冷得快。"
            + "他数了一遍。" * 40,
            encoding="utf-8",
        )
        result = _json.loads(g4_cross_chapter([str(d / "chapter-1.md")], rd=str(d), project_dir=td))
        warns = [
            c for c in result["checks"] if c["id"] == "XC.relative_anchor" and c["s"] == "WARN"
        ]
        assert warns, result["checks"]
