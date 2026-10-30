"""spec #82 T4 (Task 7): hook-type rotation gate + ending diversity sentinel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

GENRE = {
    "version": "1",
    "approval": {"decision": "approved"},
    "auditDimensions": {f"d{i}": True for i in range(5)},
    "chapterTypes": {f"t{i}": True for i in range(6)},
    "customRules": [],
    "fatigueWords": {"禁用": []},
    "pacing": {},
    "updated": "",
    "market_params": {
        "payoff_density": {"window": 3, "min": 1},
        "hook_grading": {"max_consecutive_micro": 2},
        "hook_rotation": {"shadow": False},
    },
}

CH = "# 第{n}章\n<!--SCENE-->\n他把账翻到那一页，又翻了回来。灯芯挑了一下。\n<!--SCENE-->\n数完三遍，门开了一半。\n"
MEMO_V4 = "plan_format: v4\n章尾钩型: {hook_type}\n"


def _mk(
    tmp_path: Path,
    *,
    ch: int,
    hook_type: str = "悬念钩",
    prev_hooks: dict[int, str] | None = None,
    genre: dict[str, Any] | None = None,
) -> Path:
    (tmp_path / "plans").mkdir(exist_ok=True)
    (tmp_path / "chapters").mkdir(exist_ok=True)
    (tmp_path / "chapters" / f"chapter-{ch}.md").write_text(CH.format(n=ch), encoding="utf-8")
    (tmp_path / "plans" / f"chapter-{ch}-plan.md").write_text(
        MEMO_V4.format(hook_type=hook_type), encoding="utf-8"
    )
    (tmp_path / "genre-config.json").write_text(
        json.dumps(genre or GENRE, ensure_ascii=False), encoding="utf-8"
    )
    if prev_hooks:
        state = {
            "project_dir": str(tmp_path),
            "chapter_loop": {
                "current_chapter": ch,
                "chapter_states": {
                    str(n): {"declared": {"章尾钩型": t}, "status": "complete"}
                    for n, t in prev_hooks.items()
                },
            },
        }
        (tmp_path / "pipeline-state.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
    return tmp_path


def _mf(tmp_path: Path, ch: int) -> list[str]:
    out = g4_chapter_drafting(
        [str(tmp_path / "chapters" / f"chapter-{ch}.md")],
        rd=str(tmp_path),
        project_dir=str(tmp_path),
    )
    return json.loads(out).get("must_fix", [])


@pytest.mark.unit
def test_consecutive_same_type_fails(tmp_path: Path) -> None:
    _mk(tmp_path, ch=38, hook_type="账目钩", prev_hooks={37: "账目钩"})
    assert any("hook_type_rotation" in m for m in _mf(tmp_path, 38))


@pytest.mark.unit
def test_different_type_passes(tmp_path: Path) -> None:
    _mk(tmp_path, ch=38, hook_type="悬念钩", prev_hooks={37: "账目钩"})
    assert not any("hook_type_rotation" in m for m in _mf(tmp_path, 38))


@pytest.mark.unit
def test_first_chapter_exempt(tmp_path: Path) -> None:
    _mk(tmp_path, ch=1)  # no history at all
    assert not any("hook_type_rotation" in m for m in _mf(tmp_path, 1))


@pytest.mark.unit
def test_absent_prev_type_skips(tmp_path: Path) -> None:
    # prev chapter declared before v4 (no 章尾钩型 key) → absent, skip
    _mk(tmp_path, ch=38, prev_hooks={37: "账目钩"})
    (tmp_path / "pipeline-state.json").write_text(
        json.dumps(
            {
                "project_dir": str(tmp_path),
                "chapter_loop": {
                    "current_chapter": 38,
                    "chapter_states": {"37": {"declared": {"emotion_tone": "悲"}}},
                },
            }
        ),
        encoding="utf-8",
    )
    assert not any("hook_type_rotation" in m for m in _mf(tmp_path, 38))


@pytest.mark.unit
def test_ending_diversity_warn_ledger_form(tmp_path: Path) -> None:
    """账目形态 first: 末段 ≥2 数字串的数钱收尾连续 3 章 → WARN (checks, not must_fix)."""
    ledger_ch = "# 第38章\n<!--SCENE-->\n他把账翻开。工钱 87 文，还剩 103 文。他把两笔都记下。\n"
    (tmp_path / "plans").mkdir()
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-38.md").write_text(ledger_ch, encoding="utf-8")
    (tmp_path / "plans" / "chapter-38-plan.md").write_text(
        MEMO_V4.format(hook_type="账目钩"), encoding="utf-8"
    )
    (tmp_path / "genre-config.json").write_text(
        json.dumps(GENRE, ensure_ascii=False), encoding="utf-8"
    )
    state = {
        "project_dir": str(tmp_path),
        "chapter_loop": {
            "current_chapter": 38,
            "chapter_states": {
                str(n): {"declared": {"章尾钩型": "账目钩"}, "status": "complete"} for n in (36, 37)
            },
        },
    }
    (tmp_path / "pipeline-state.json").write_text(json.dumps(state), encoding="utf-8")
    out = g4_chapter_drafting(
        [str(tmp_path / "chapters" / "chapter-38.md")], rd=str(tmp_path), project_dir=str(tmp_path)
    )
    result = json.loads(out)
    # the ledger-closer pattern fired the ending-diversity WARN row (checks)
    assert any(
        "ending_diversity" in str(chk.get("id", "")) for chk in result.get("checks", [])
    ) or any("ending_diversity" in m for m in result["must_fix"])


FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec82"


@pytest.mark.unit
def test_ending_archetype_ignores_meta_tail() -> None:
    """PR #263 Copilot: real chapters end with a META POST self-check whose
    digit-heavy tail made the raw-window classifier call every chapter
    账目形态 (diversity sentinel deaf + garbage ending_history). The closing
    window must be prose-based (strip_narrative_body), proven on real fixtures.
    """
    from shenbi.gates.g4.chapter_drafting import _ending_archetype_of

    for name in ("chapter-1", "chapter-6"):
        raw = (FIX / "chapters" / f"{name}.md").read_text(encoding="utf-8")
        assert _ending_archetype_of(raw) is None, name  # prose tail ≠ 账目形态


@pytest.mark.unit
def test_ending_archetype_ledger_prose_survives_meta_tail() -> None:
    """Discriminating pair: 账目形态 must fire on PROSE ledger digits even when
    a META block follows, and must not fire on prose digits + META-only digits.
    """
    from shenbi.gates.g4.chapter_drafting import _ending_archetype_of

    ledger = "他把账翻开。工钱 87 文，还剩 103 文。他把两笔都记下。\n"
    meta_tail = "<!--META-BEGIN-->\n- [ ] 正文字数: 3625 字，场景 2 个\n<!--META-END-->\n"
    assert _ending_archetype_of(ledger + meta_tail) == "账目形态"  # prose digits fire
    assert _ending_archetype_of("他望着河面出神，很久没说话。\n" + meta_tail) is None
