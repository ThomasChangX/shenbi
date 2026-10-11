"""C 批: volume budget guardrails — 卷界锚规则、骨架序言派生、再预算检视.

The 千万字 route appends volumes at boundaries; three deterministic
disciplines keep that growth honest (GO① pattern — no LLM writer
discipline load-bearing): new volumes anchor at live max boundary + 1, the
frontmatter/preamble skeleton derives from the volume sections, and the
boundary chain's budget check surfaces re-budget entries, per-volume drift
beyond ±3, consecutive overshoot, and 保量 shortfalls (G0.3 口径).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shenbi.exceptions import IncrementShapeError
from shenbi.pipeline.dispatch_helper import _write_parsed_outputs
from shenbi.pipeline.volume_budget import (
    apply_budget_writeback,
    budget_verdict,
    check_new_volume_anchor,
    main,
    parse_volume_spans,
    sync_volume_skeleton,
)

_VOLUME_MAP = """---
total_chapters: 47
generated_at: "2026-10-06T13:51:59Z"
---

# 分卷地图

> **章数预算**：略。
> **卷界**：23 / 24 = 47；最大章界为第 47 章。

---

## 第一卷：哑脉藏火（第 1-23 章）

**Objective**: 卷一目标。

## 第二卷：入港（第 24-47 章）

**Objective**: 卷二目标。
"""


def test_anchor_rule_accepts_contiguous_new_volume() -> None:
    assert (
        check_new_volume_anchor(
            _VOLUME_MAP, "## 第三卷：潮汛（第 48-71 章）\n\n**Objective**: 三。\n"
        )
        is None
    )


def test_anchor_rule_rejects_wrong_start() -> None:
    err = check_new_volume_anchor(
        _VOLUME_MAP, "## 第三卷：潮汛（第 40-71 章）\n\n**Objective**: 三。\n"
    )
    assert err is not None and "第 48 章起卷" in err and "第 47 章" in err


def test_anchor_rule_rejects_unreadable_span() -> None:
    err = check_new_volume_anchor(_VOLUME_MAP, "## 第三卷：潮汛\n\n**Objective**: 三。\n")
    assert err is not None and "机器可读章界" in err


def test_anchor_rule_leaves_replaced_volumes_unconstrained() -> None:
    """Retitling/refining an EXISTING volume is drift-guardrail territory,
    not the merge's — any span form passes the anchor check.
    """
    assert (
        check_new_volume_anchor(
            _VOLUME_MAP, "## 第二卷：新港（第 24-50 章）\n\n**Objective**: 改。\n"
        )
        is None
    )


def test_skeleton_derivation_rewrites_total_and_boundary_line() -> None:
    out = sync_volume_skeleton(_VOLUME_MAP.replace("（第 24-47 章）", "（第 24-40 章）"))
    assert "total_chapters: 40" in out
    assert "> **卷界**：23 / 17 = 40；最大章界为第 40 章。" in out
    assert "generated_at" in out, "other frontmatter untouched"


def test_skeleton_derivation_never_invents_missing_lines() -> None:
    bare = "# 分卷地图\n\n## 第一卷：哑脉藏火（第 1-23 章）\n"
    assert sync_volume_skeleton(bare) == bare


def test_skeleton_derivation_noop_without_spans() -> None:
    assert (
        sync_volume_skeleton("---\ntotal_chapters: 5\n---\n\n# 无卷\n")
        == "---\ntotal_chapters: 5\n---\n\n# 无卷\n"
    )


def _budget_project(tmp_path: Path) -> Path:
    (tmp_path / "outline").mkdir(parents=True)
    (tmp_path / "truth").mkdir(parents=True)
    (tmp_path / "chapters").mkdir(parents=True)
    (tmp_path / "outline" / "volume_map.md").write_text(_VOLUME_MAP, encoding="utf-8")
    (tmp_path / "novel.json").write_text(
        json.dumps({"target_word_count": 79900, "total_chapters": 47}), encoding="utf-8"
    )
    # 79900 / 2200 = 36.3 → implied 37 ≠ planned 47 → re-budget pending
    (tmp_path / "genre-config.json").write_text(
        json.dumps({"chapter_word": {"default": 2200}}), encoding="utf-8"
    )
    return tmp_path


def test_budget_verdict_full_matrix(tmp_path: Path) -> None:
    project = _budget_project(tmp_path)
    # actual: 卷一 consumed 1-27 (drift +4 → overrun), 卷二 pending
    (project / "truth" / "volume_summaries.md").write_text(
        "---\ntype: truth\n---\n\n# 卷级摘要\n\n## 第1卷: 哑脉 (第1-27章)\n\n摘要。\n",
        encoding="utf-8",
    )
    # written through ch51 (spillover past 卷二's planned end 47 by 4 > 3)
    for n in range(1, 52):
        (project / "chapters" / f"chapter-{n}.md").write_text("字" * 2500, encoding="utf-8")
    (project / "chapters" / "chapter-30.md").write_text(
        "字" * 1500, encoding="utf-8"
    )  # under floor

    v = budget_verdict(project)

    assert v.re_budget_pending is True
    assert v.implied_total == 37 and v.planned_total == 47
    assert v.drifts.get("第一卷") == 4
    checks = " ".join(v.findings)
    assert "re_budget_pending" in checks
    assert "volume_overrun" in checks and "超 4 章" in checks
    assert "volume_spillover" in checks and "第 51 章" in checks
    assert "word_floor" in checks and "1 章低于" in checks


def test_budget_verdict_within_tolerance_is_ok(tmp_path: Path) -> None:
    project = _budget_project(tmp_path)
    (project / "novel.json").write_text(
        json.dumps({"target_word_count": 103400, "total_chapters": 47}), encoding="utf-8"
    )  # 103400/2200 = 47 → implied == planned, no re-budget
    (project / "truth" / "volume_summaries.md").write_text(
        "---\ntype: truth\n---\n\n# 卷级摘要\n\n## 第1卷: 哑脉 (第1-25章)\n\n摘要。\n",
        encoding="utf-8",
    )  # drift +2 ≤ 3 tolerated
    for n in range(1, 26):
        (project / "chapters" / f"chapter-{n}.md").write_text("字" * 2500, encoding="utf-8")

    v = budget_verdict(project)

    assert v.ok, v.findings
    assert v.drifts == {"第一卷": 2}


def test_consecutive_overshoot_escalates(tmp_path: Path) -> None:
    project = _budget_project(tmp_path)
    (project / "novel.json").write_text(
        json.dumps({"target_word_count": 103400, "total_chapters": 47}), encoding="utf-8"
    )
    (project / "truth" / "volume_summaries.md").write_text(
        "---\ntype: truth\n---\n\n# 卷级摘要\n\n"
        "## 第1卷: 哑脉 (第1-28章)\n\n摘要。\n\n## 第2卷: 入港 (第29-58章)\n\n摘要。\n",
        encoding="utf-8",
    )  # 卷一 +6, 卷二 +7 (29-58 = 30 vs 24) → two consecutive overruns
    for n in range(1, 59):
        (project / "chapters" / f"chapter-{n}.md").write_text("字" * 2500, encoding="utf-8")

    checks = " ".join(budget_verdict(project).findings)
    assert "consecutive_overshoot" in checks


def test_apply_writeback_updates_total_and_skeleton(tmp_path: Path) -> None:
    project = _budget_project(tmp_path)
    vm = project / "outline" / "volume_map.md"
    vm.write_text(
        _VOLUME_MAP + "\n## 第三卷：潮汛（第 48-71 章）\n\n**Objective**: 三。\n", encoding="utf-8"
    )

    total = apply_budget_writeback(project)

    assert total == 71
    assert json.loads((project / "novel.json").read_text(encoding="utf-8"))["total_chapters"] == 71
    text = vm.read_text(encoding="utf-8")
    assert "total_chapters: 71" in text
    assert "> **卷界**：23 / 24 / 24 = 71；最大章界为第 71 章。" in text


def test_dispatch_rejects_misanchored_new_volume(tmp_path: Path) -> None:
    (tmp_path / "outline").mkdir(parents=True)
    (tmp_path / "outline" / "volume_map.md").write_text(_VOLUME_MAP, encoding="utf-8")
    before = (tmp_path / "outline" / "volume_map.md").read_text(encoding="utf-8")
    with pytest.raises(IncrementShapeError, match="卷界锚规则"):
        _write_parsed_outputs(
            response="### FILE: outline/volume_map.md\n## 第三卷：潮汛（第 45-71 章）\n\n**Objective**: 三。\n",
            output_paths=["outline/volume_map.md"],
            project_dir=tmp_path,
            skill="shenbi-volume-outlining",
        )
    assert (tmp_path / "outline" / "volume_map.md").read_text(encoding="utf-8") == before


def test_dispatch_derives_skeleton_on_new_volume(tmp_path: Path) -> None:
    (tmp_path / "outline").mkdir(parents=True)
    (tmp_path / "outline" / "volume_map.md").write_text(_VOLUME_MAP, encoding="utf-8")
    _write_parsed_outputs(
        response="### FILE: outline/volume_map.md\n## 第三卷：潮汛（第 48-71 章）\n\n**Objective**: 三。\n",
        output_paths=["outline/volume_map.md"],
        project_dir=tmp_path,
        skill="shenbi-volume-outlining",
    )
    text = (tmp_path / "outline" / "volume_map.md").read_text(encoding="utf-8")
    assert "## 第三卷：潮汛（第 48-71 章）" in text
    assert "total_chapters: 71" in text, "frontmatter derived from landed sections"
    assert "> **卷界**：23 / 24 / 24 = 71；最大章界为第 71 章。" in text


def test_cli_reports_verdict(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = _budget_project(tmp_path)
    rc = main([str(project)])
    out = capsys.readouterr().out
    assert rc == 1, "re-budget pending → non-zero for the boundary chain"
    assert "re_budget_pending=true" in out
    assert "verdict=NEEDS_ATTENTION" in out


def test_replay_skeleton_derivation_on_live_volume_map() -> None:
    """Idempotence on the REAL 118-chapter map: totals already consistent →
    byte-identical output (production shapes beat synthetic fixtures).
    """
    live = (
        Path(__file__).resolve().parents[3] / "novel-xinghuo-phase3" / "outline" / "volume_map.md"
    )
    if not live.exists():
        pytest.skip("live phase3 project not present")
    text = live.read_text(encoding="utf-8")
    assert parse_volume_spans(text), "live map carries paren spans"
    assert sync_volume_skeleton(text) == text
