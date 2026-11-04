"""Spec #95 T3③: settle-exclusive total char budget at the assembly exit.

72k chars (≈60k tokens @0.80) with disclosed truncation + WARN above budget;
hard floor 40k raises (cannot carry the incremental contract); the in-function
assertion pins budget-path + disclosure co-occurrence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import shenbi.pipeline.dispatch_helper as dh
from tests.unit.pipeline.test_read_extractors_slicing import _settle_project


def _inflate(project: Path, rel: str, filler_lines: int) -> None:
    f = project / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    pad = "\n".join(f"| 第 {n} 章 | {'x' * 80} | 填充行 n{n} |" for n in range(filler_lines))
    f.write_text(f.read_text(encoding="utf-8") + "\n" + pad + "\n", encoding="utf-8")


def test_over_budget_truncates_with_disclosure_and_warn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _settle_project(tmp_path)
    # 推高总量 >72k：三份 full-read 面各顶 32k per-file 帽（audits/正文/matrix
    # fulltext 回退——cast 不命中），组装 ~100k 触发总预算路径
    (project / "audits" / "chapter-57-foreshadowing.md").write_text(
        "触及 MH02。" + "填充" * 20000, encoding="utf-8"
    )
    (project / "chapters" / "chapter-57.md").write_text(
        "# 第57章\n\n" + "正文填充。" * 12000, encoding="utf-8"
    )
    (project / "truth" / "character_matrix.md").write_text(
        (project / "truth" / "character_matrix.md").read_text(encoding="utf-8")
        + "\n"
        + "\n".join(f"| 路人{n} | 路人{n + 1} | 擦肩 | 无 | 第 {n} 章 |" for n in range(3000)),
        encoding="utf-8",
    )
    warned: list[str] = []
    monkeypatch.setattr(dh.log, "warning", lambda event, **kw: warned.append(event))
    _, user_prompt, _, _, _ = dh._build_skill_prompt(
        "shenbi-state-settling", project, "settle ch57", chapter=57
    )
    assert len(user_prompt) <= 72_000 + 400, len(user_prompt)
    assert "【截断告知】" in user_prompt  # 披露块必然出现
    assert "settle_budget_degraded" in warned


def test_floor_raises_when_windowing_eats_real_corpus(tmp_path: Path) -> None:
    """Raw reads >= floor while assembly collapses (windowing failure) -> raise.

    Five chapter-keyed tables at ~54k raw each (recent_increments keeps
    last 3 rows), small hooks/matrix windows: raw_total >40k but assembly <40k.
    """
    project = _settle_project(tmp_path)
    big_rows = "\n".join(f"| 第 {n} 章 | {'y' * 80} | {'z' * 40} |" for n in range(1, 600))
    for name, header in (
        ("current_state.md", "| 章节 | 位置 | 时间锚 |"),
        ("particle_ledger.md", "| 章节 | 变动项 | 收支 |"),
        ("emotional_arcs.md", "| 章节 | 角色 | 本章情感弧线 |"),
        ("subplot_board.md", "| 章节 | 支线 | 起始章 |"),
        (
            "chapter_summaries.md",
            "| 章节 | 一句话事件 | 出场角色 | 推进的支线 | 新增／回收伏笔 | 结尾钩子 |",
        ),
    ):
        ncols = header.count("|") - 1
        row = "| 第 1 章 | " + " | ".join("d" * 20 for _ in range(ncols - 1)) + " |"
        (project / "truth" / name).write_text(
            f"---\ntype: truth\n---\n\n# {name}\n\n{header}\n|{'---|' * ncols}\n{big_rows}\n{row}\n",
            encoding="utf-8",
        )
    with pytest.raises(ValueError, match="hard floor"):
        dh._build_skill_prompt("shenbi-state-settling", project, "settle ch57", chapter=57)


def test_normal_project_within_budget_no_disclosure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _settle_project(tmp_path)
    warned: list[str] = []
    monkeypatch.setattr(dh.log, "warning", lambda event, **kw: warned.append(event))
    _, user_prompt, _, _, _ = dh._build_skill_prompt(
        "shenbi-state-settling", project, "settle ch57", chapter=57
    )
    assert "【截断告知】" not in user_prompt
    assert "settle_budget_degraded" not in [w for w in warned if w == "settle_budget_degraded"]
