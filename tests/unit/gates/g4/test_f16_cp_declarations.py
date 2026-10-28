"""T4: F16 G4.cp——memo 物象声明解析 + 对 facts 现态合法性（spec #80 §4 F16）。

G0.9: memo 文本与 facts 种子为测试内构造的结构性输入（spec §3 豁免面）。
"""

from __future__ import annotations

import json
from pathlib import Path

from shenbi.gates.g4.chapter_planning import (
    g4_chapter_planning,
    parse_prop_declarations,
)


def test_parse_declaration_line():
    memo = "- 火纹骨哨@transfer: 帖木哥→那罕\n- 红纸包@hold: 那罕"
    decls = parse_prop_declarations(memo)
    assert decls[0] == ("火纹骨哨", "transfer", "帖木哥", "那罕")
    assert decls[1] == ("红纸包", "hold", "那罕", "那罕")  # hold 单值形态 from_=to


def test_parse_ignores_prose_motif_line():
    memo = "**母题物象**: 火纹骨哨（本章变奏：骨哨在怀里响了一下）"
    assert parse_prop_declarations(memo) == []


def _seed_props(tmp_path: Path, owner: str = "那罕") -> None:
    facts_dir = tmp_path / "truth" / "facts"
    facts_dir.mkdir(parents=True, exist_ok=True)
    (facts_dir / "props.json").write_text(
        json.dumps(
            {
                "$schema": "shenbi-facts-v1",
                "dim": "props",
                "facts": {
                    "火纹骨哨": {"entity": "火纹骨哨", "owner": owner, "events": []},
                },
                "ops_log": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _memo_file(tmp_path: Path, text: str) -> Path:
    plans = tmp_path / "plans"
    plans.mkdir(exist_ok=True)
    p = plans / "chapter-20-plan.md"
    p.write_text(text, encoding="utf-8")
    return p


_LEGACY_MEMO = """---
plan_format: v3
---

# 第二十章备忘

**母题物象**: 火纹骨哨（本章变奏：帖木哥交出钥匙时骨哨响了一下，没吹）
"""


def test_declared_transfer_from_wrong_owner_fails(tmp_path: Path):
    _seed_props(tmp_path, owner="那罕")
    memo = _memo_file(tmp_path, _LEGACY_MEMO + "\n- 火纹骨哨@transfer: 老驼→帖木哥\n")
    out = g4_chapter_planning([str(memo)], project_dir=str(tmp_path))
    assert "cp.prop_decl:" in out


def test_declared_transfer_from_owner_passes(tmp_path: Path):
    _seed_props(tmp_path, owner="那罕")
    memo = _memo_file(tmp_path, _LEGACY_MEMO + "\n- 火纹骨哨@transfer: 那罕→帖木哥\n")
    out = g4_chapter_planning([str(memo)], project_dir=str(tmp_path))
    assert "cp.prop_decl:" not in out


def test_copy_key_first_sighting_is_legal(tmp_path: Path):
    # 实体副本语义：帖木哥支=独立键初见——修复后 ch20 双哨并存全绿的 cp 侧
    _seed_props(tmp_path, owner="那罕")
    memo = _memo_file(
        tmp_path,
        _LEGACY_MEMO + "\n- 火纹骨哨·帖木哥支@acquire: 那罕（ch20 灯座交付）\n",
    )
    out = g4_chapter_planning([str(memo)], project_dir=str(tmp_path))
    assert "cp.prop_decl:" not in out


def test_legacy_memo_warns_not_silent(tmp_path: Path):
    # 13/24 静默死法禁令：无声明行备忘必须 WARN 可见
    _seed_props(tmp_path)
    memo = _memo_file(tmp_path, _LEGACY_MEMO)
    out = g4_chapter_planning([str(memo)], project_dir=str(tmp_path))
    assert "legacy_memo" in out  # WARN 文本可见


def test_facts_absent_warns(tmp_path: Path):
    # 无 facts 项目：skip + WARN 可见（不硬 FAIL）
    memo = _memo_file(tmp_path, _LEGACY_MEMO + "\n- 火纹骨哨@transfer: 那罕→帖木哥\n")
    out = g4_chapter_planning([str(memo)], project_dir=str(tmp_path))
    assert "no_facts" in out
