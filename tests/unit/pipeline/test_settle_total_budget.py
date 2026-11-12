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
    _, user_prompt, _, _, _ = dh.build_skill_prompt(
        "shenbi-state-settling", project, "settle ch57", chapter=57
    )
    assert len(user_prompt) <= 72_000 + 400, len(user_prompt)
    # audit-T9 I2: 下界——体量必须保住（容差=单个可弃面粒度 ~31k）
    assert len(user_prompt) >= 72_000 - 33_000, len(user_prompt)
    # 披露必然在场：整面省略行（面降级）或顶部【截断告知】（平尾）
    assert ("【截断告知】" in user_prompt) or ("【预算省略】" in user_prompt)
    assert "settle_budget_degraded" in warned


def test_priority_face_drop_before_tail_cut(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """audit-T9 I1: face-priority degradation precedes the flat tail cut.

    audits face ~31k (per-file cap) + huge matrix fulltext fallback ~32k
    + huge chapter body ~32k -> assembly ~100k. The audits block must be
    dropped whole (disclosure line present); the tail cut is only the belt.
    """
    project = _settle_project(tmp_path)
    (project / "audits" / "chapter-57-foreshadowing.md").write_text(
        "触及 MH02。" + "甲" * 31000, encoding="utf-8"
    )
    (project / "chapters" / "chapter-57.md").write_text(
        "# 第57章\n\n" + "正文填充。" * 6000, encoding="utf-8"
    )
    (project / "truth" / "character_matrix.md").write_text(
        (project / "truth" / "character_matrix.md").read_text(encoding="utf-8")
        + "\n"
        + "\n".join(f"| 路人{n} | 路人{n + 1} | 擦肩 | 无 | 第 {n} 章 |" for n in range(3000)),
        encoding="utf-8",
    )
    warned: list[str] = []
    monkeypatch.setattr(dh.log, "warning", lambda event, **kw: warned.append(event))
    _, user_prompt, _, _, _ = dh.build_skill_prompt(
        "shenbi-state-settling", project, "settle ch57", chapter=57
    )
    assert len(user_prompt) <= 72_000 + 400
    assert "【预算省略】" in user_prompt and "chapter-57-foreshadowing" in user_prompt
    assert "settle_budget_degraded" in warned


def test_floor_only_inside_enforcement_path(tmp_path: Path) -> None:
    """audit-T9 C2: healthy windowed small assemblies must NOT raise.

    Five chapter-keyed tables at ~54k raw each (recent_increments keeps the
    last 3 rows): raw_total >40k while assembly <40k — the old floor
    misfire shape; it must now return normally (floor lives inside the
    enforcement branch only).
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
    _, user_prompt, _, _, _ = dh.build_skill_prompt(
        "shenbi-state-settling", project, "settle ch57", chapter=57
    )
    assert len(user_prompt) < 40_000  # the healthy-windowed premise shape
    # not raising is the pass condition


def test_normal_project_within_budget_no_disclosure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _settle_project(tmp_path)
    warned: list[str] = []
    monkeypatch.setattr(dh.log, "warning", lambda event, **kw: warned.append(event))
    _, user_prompt, _, _, _ = dh.build_skill_prompt(
        "shenbi-state-settling", project, "settle ch57", chapter=57
    )
    assert "【截断告知】" not in user_prompt
    assert "settle_budget_degraded" not in [w for w in warned if w == "settle_budget_degraded"]


def test_same_tier_multi_face_drop_content_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """audit-T9 r2 N1: same-tier multi-face drops must actually remove content.

    The stale-offset shape kept the 2nd "dropped" face ~99.5% alive while
    silently deleting pending_hooks head content — length-conserving, so
    only content assertions can catch it.
    """
    project = _settle_project(tmp_path)
    (project / "audits" / "chapter-57-foreshadowing.md").write_text(
        "触及 MH02。" + "甲" * 16000, encoding="utf-8"
    )
    # 同层第二面：settle 契约还读 audits/chapter-56-foreshadowing? 无——用
    # registries 同层三面替代同层多弃形态（tier 2: prop/name/recall）
    (project / "truth" / "prop_registry.md").write_text("道具甲" * 9000, encoding="utf-8")
    (project / "truth" / "name_registry.md").write_text("人名乙" * 9000, encoding="utf-8")
    (project / "truth" / "recall_registry.md").write_text("回触丙" * 9000, encoding="utf-8")
    (project / "chapters" / "chapter-57.md").write_text(
        "# 第57章\n\n" + "正文填充。" * 6000, encoding="utf-8"
    )
    warned: list[tuple[str, dict[str, object]]] = []

    def _spy(event: str, **kw: object) -> None:
        warned.append((event, dict(kw)))

    with monkeypatch.context() as mp:
        mp.setattr(dh.log, "warning", _spy)
        _, user_prompt, _, _, _ = dh.build_skill_prompt(
            "shenbi-state-settling", project, "settle ch57", chapter=57
        )
    budget_events = [kw for ev, kw in warned if ev == "settle_budget_degraded"]
    assert budget_events, "enforcement must fire"
    dropped = list(budget_events[0]["dropped_faces"])  # type: ignore[arg-type]
    # N1 不变量：台账声称已弃的面，其内容必须真的消失（内容级——非长度守恒陷阱）
    assert len(dropped) >= 3, dropped  # 同层多弃形态成立（audits+至少两面 registry）
    assert "audits/chapter-57-foreshadowing.md" in dropped
    assert "道具甲道具甲" not in user_prompt
    assert "人名乙人名乙" not in user_prompt
    if "truth/recall_registry.md" in dropped:
        assert "回触丙回触丙" not in user_prompt
    # 省略披露行数与台账一致
    assert user_prompt.count("【预算省略】") == len(dropped)
    # 受保护面无伤：伏笔池（pending_hooks 恒保）内容完整在场
    assert "伏笔池" in user_prompt and "MH02（灵誓）" in user_prompt
    # 顶部汇总在场（纯面降级路径，r2 N2）
    assert "【截断告知】" in user_prompt
