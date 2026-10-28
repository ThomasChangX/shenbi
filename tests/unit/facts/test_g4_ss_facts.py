"""T8b: G4.ss 读侧——op↔row 一致性 + identity 对账 + F16s simulate（纯读者）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shenbi.gates.g4.state_settling import g4_state_settling_check


def _seed(tmp_path: Path, props: dict[str, Any], identity: dict[str, Any] | None = None) -> None:
    d = tmp_path / "truth" / "facts"
    d.mkdir(parents=True, exist_ok=True)
    (d / "props.json").write_text(
        json.dumps(
            {"$schema": "shenbi-facts-v1", "dim": "props", "facts": props, "ops_log": []},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if identity is not None:
        (d / "identity.json").write_text(
            json.dumps(
                {
                    "$schema": "shenbi-facts-v1",
                    "dim": "identity",
                    "facts": {"主角": identity},
                    "ops_log": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


def _sidecar(tmp_path: Path, facts_ops: dict[str, Any]) -> Path:
    p = tmp_path / "chapters" / "chapter-20-decisions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 20,
                "produced_at": "2026-10-28T00:00:00Z",
                "facts_ops": facts_ops,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def test_prop_row_match_fails_on_divergence(tmp_path: Path):
    # G4.ss 在 settle 时点跑（facts 尚未应用 op）：op 合法（from=那罕=现态），
    # registry 行 owner 仍写那罕（Markdown 面未跟上 op.to=帖木哥）⇒ 分叉 FAIL
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    registry = tmp_path / "truth" / "prop_registry.md"
    registry.parent.mkdir(exist_ok=True)
    registry.write_text(
        "---\ntype: truth\n---\n\n| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n"
        "| 火纹骨哨 | 那罕 | ch20 交付 |\n",
        encoding="utf-8",
    )
    sidecar = _sidecar(
        tmp_path,
        {
            "props": [
                {
                    "op": "transfer",
                    "prop": "火纹骨哨",
                    "from": "那罕",
                    "to": "帖木哥",
                    "evidence": "L218",
                    "chapter": 20,
                }
            ]
        },
    )
    issues = g4_state_settling_check(tmp_path, sidecar)
    assert any("ss.prop_row_match:" in i for i in issues)


def test_f16s_simulate_rejects_illegal_op(tmp_path: Path):
    # F16s 纯读者：op 对现 facts 干跑（owner=那罕，transfer from=老驼 ⇒ 拒收形态）
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    sidecar = _sidecar(
        tmp_path,
        {
            "props": [
                {
                    "op": "transfer",
                    "prop": "火纹骨哨",
                    "from": "老驼",
                    "to": "帖木哥",
                    "evidence": "L218",
                    "chapter": 20,
                }
            ]
        },
    )
    issues = g4_state_settling_check(tmp_path, sidecar)
    assert any("ss.facts_ops:" in i for i in issues)


def test_identity_reconciliation_fails_on_alias_mismatch(tmp_path: Path):
    # facts 别名集与 name_registry 别名行分叉 ⇒ ss.identity_row_match FAIL
    _seed(
        tmp_path,
        {},
        identity={"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]},
    )
    name_registry = tmp_path / "truth" / "name_registry.md"
    name_registry.write_text(
        "---\ntype: truth\n---\n\n| 类别 | 名 | 备注 |\n|---|---|---|\n"
        "| 别名 | 林烽 | 星象局用名 |\n| 别名 | 萤 | 不在 facts 别名集 |\n",
        encoding="utf-8",
    )
    sidecar = _sidecar(
        tmp_path,
        {"props": [], "identity": [{"op": "set_alias", "alias": "林烽"}]},
    )
    issues = g4_state_settling_check(tmp_path, sidecar)
    assert any("ss.identity_row_match:" in i for i in issues)


def test_no_oracles_no_hard_fail(tmp_path: Path):
    # 无 facts/无 registry/无 sidecar：G4.ss 不硬 FAIL（兼容期）
    issues = g4_state_settling_check(tmp_path, None)
    assert isinstance(issues, list)
