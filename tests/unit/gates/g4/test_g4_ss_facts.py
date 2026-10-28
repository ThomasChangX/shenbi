"""T8b: G4.ss 读侧——op↔row 一致性 + identity 对账 + F16s simulate（纯读者）。

audit-T8 清偿后的契约：返回 (fail_issues, warn_notes)；①兼容期 WARN 已实现
（I3）；④链式模拟（M7）；③双向且不以 identity_ops 为门（M8）；幂等重放与
写侧同键跳过（I6）。
"""

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


def _sidecar(tmp_path: Path, facts_ops: dict[str, Any] | None, chapter: int = 20) -> Path:
    p = tmp_path / "chapters" / "chapter-20-decisions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, Any] = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-state-settling",
        "chapter": chapter,
        "produced_at": "2026-10-28T00:00:00Z",
    }
    if facts_ops is not None:
        doc["facts_ops"] = facts_ops
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
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
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert any("ss.prop_row_match:" in i for i in issues)


def test_staged_sibling_registry_preferred(tmp_path: Path):
    # 本章新行只在 staging 姊妹副本——committed 缺行时以 staging 行对账
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    sidecar_dir = tmp_path / "staging" / "truth"
    sidecar_dir.mkdir(parents=True)
    (sidecar_dir / "prop_registry.md").write_text(
        "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n| 火纹骨哨 | 那罕 | 旧 |\n",
        encoding="utf-8",
    )
    doc = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-state-settling",
        "chapter": 20,
        "produced_at": "2026-10-28T00:00:00Z",
        "facts_ops": {
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
    }
    sidecar = sidecar_dir / "state-settling-decisions.json"
    sidecar.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert any("ss.prop_row_match:" in i for i in issues)


def test_f16s_simulate_rejects_illegal_op(tmp_path: Path):
    # F16s 纯读者：op 对现 facts 干跑（owner=那罕，transfer from=老驼 ⇒ 拒收形态）；
    # 无 rationale ⇒ P2.5 缺失双 issue
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
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert sum("ss.facts_ops:非法 op" in i for i in issues) == 1
    assert any("rationale 缺失" in i for i in issues)


def test_chained_two_hop_transfer_is_legal(tmp_path: Path):
    # M7 + round2 #1/#1c：同 sidecar 两跳 A→B、B→C 链式模拟——第二跳对第一跳
    # 后状态合法；registry 行持**真终态** C 时不得误报（旧逐 op ev.to 对账 +
    # 粗重放键吞第二跳会把正确行判成分叉，要求改写成错误中间态）
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    registry = tmp_path / "truth" / "prop_registry.md"
    registry.parent.mkdir(exist_ok=True)
    registry.write_text(
        "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n| 火纹骨哨 | 帖木哥 | ch20 两跳经手 |\n",
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
                    "to": "老驼",
                    "evidence": "L10",
                    "chapter": 20,
                },
                {
                    "op": "transfer",
                    "prop": "火纹骨哨",
                    "from": "老驼",
                    "to": "帖木哥",
                    "evidence": "L20",
                    "chapter": 20,
                },
            ]
        },
    )
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert not [i for i in issues if "ss.facts_ops:" in i or "ss.prop_row_match:" in i]


def test_two_hop_row_with_hop1_owner_diverges(tmp_path: Path):
    # 行持中间态 owner（老驼）≠ op 链终态（帖木哥）⇒ 仍 FAIL——重构后
    # 对账按终态，逃逸面没有变大
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    registry = tmp_path / "truth" / "prop_registry.md"
    registry.parent.mkdir(exist_ok=True)
    registry.write_text(
        "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n| 火纹骨哨 | 老驼 | ch20 |\n",
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
                    "to": "老驼",
                    "evidence": "L10",
                    "chapter": 20,
                },
                {
                    "op": "transfer",
                    "prop": "火纹骨哨",
                    "from": "老驼",
                    "to": "帖木哥",
                    "evidence": "L20",
                    "chapter": 20,
                },
            ]
        },
    )
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert any("ss.prop_row_match:" in i and "帖木哥" in i for i in issues)


def test_replayed_op_skipped_in_simulate(tmp_path: Path):
    # I6 一致性：ops_log 已含同全指纹 op ⇒ 模拟侧同键跳过，
    # 不再判「from 不匹配」假红（at-least-once 重放窗口的复检场景）
    _seed(
        tmp_path,
        {
            "火纹骨哨": {
                "entity": "火纹骨哨",
                "owner": "帖木哥",
                "events": [],
            }
        },
    )
    props_file = tmp_path / "truth" / "facts" / "props.json"
    doc = json.loads(props_file.read_text(encoding="utf-8"))
    doc["ops_log"] = [
        {
            "op": "transfer",
            "prop": "火纹骨哨",
            "from": "那罕",
            "to": "帖木哥",
            "evidence": "L218",
            "chapter": 20,
        }
    ]
    props_file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
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
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert not [i for i in issues if "ss.facts_ops:" in i]


def test_structurally_invalid_prop_op_fails(tmp_path: Path):
    # I5 读侧镜像：op 条目带闭集外自造键 ⇒ 结构非法 issue（而非裸 ValidationError）
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    sidecar = _sidecar(
        tmp_path,
        {"props": [{"op": "transfer", "prop": "火纹骨哨", "自造键": 1}]},
    )
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert any("ss.facts_ops:props op 结构非法" in i for i in issues)


def test_compat_warn_when_registry_changed_without_ops(tmp_path: Path):
    # ① 兼容期 WARN：sidecar 无 facts_ops 而 registry 含第20章行变更
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    registry = tmp_path / "truth" / "prop_registry.md"
    registry.parent.mkdir(exist_ok=True)
    registry.write_text(
        "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n| 火纹骨哨 | 那罕 | 第 20 章交付 |\n",
        encoding="utf-8",
    )
    sidecar = _sidecar(tmp_path, None)
    issues, warns = g4_state_settling_check(tmp_path, sidecar)
    assert not issues
    assert any("兼容期" in w and "facts_ops" in w for w in warns)


def test_no_ops_no_registry_change_no_warn(tmp_path: Path):
    # ① 反向：registry 无本章行变更 ⇒ 无 WARN（旧章行不触发）
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    registry = tmp_path / "truth" / "prop_registry.md"
    registry.parent.mkdir(exist_ok=True)
    registry.write_text(
        "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n| 火纹骨哨 | 那罕 | 第 19 章交付 |\n",
        encoding="utf-8",
    )
    sidecar = _sidecar(tmp_path, None)
    issues, warns = g4_state_settling_check(tmp_path, sidecar)
    assert not issues and not warns


def test_identity_reconciliation_bidirectional(tmp_path: Path):
    # M8：双向 + 不以 identity_ops 为门——sidecar 无 identity ops 仍对账；
    # 双向 = registry 行不在 facts（萤）+ facts 别名无行（晨）双 FAIL
    _seed(
        tmp_path,
        {},
        identity={"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽", "晨"]},
    )
    name_registry = tmp_path / "truth" / "name_registry.md"
    name_registry.write_text(
        "---\ntype: truth\n---\n\n| 类别 | 名 | 备注 |\n|---|---|---|\n"
        "| 别名 | 林烽 | 星象局用名 |\n| 别名 | 萤 | 不在 facts 别名集 |\n",
        encoding="utf-8",
    )
    sidecar = _sidecar(tmp_path, {"props": []})
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    joined = "\n".join(issues)
    assert "「萤」" in joined and "「晨」" in joined


def test_malformed_facts_ops_object_fails(tmp_path: Path):
    # facts_ops 非对象（list）⇒ 结构非法 issue
    _seed(tmp_path, {})
    p = tmp_path / "chapters" / "chapter-20-decisions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 20,
                "produced_at": "2026-10-28T00:00:00Z",
                "facts_ops": ["not", "an", "object"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    issues, _warns = g4_state_settling_check(tmp_path, p)
    assert any("必须是对象" in i for i in issues)


def test_no_oracles_no_hard_fail(tmp_path: Path):
    # 无 facts/无 registry/无 sidecar：G4.ss 不硬 FAIL（兼容期）
    issues, warns = g4_state_settling_check(tmp_path, None)
    assert isinstance(issues, list) and isinstance(warns, list)
    assert not issues and not warns


def test_identity_simulate_before_reconcile_no_false_fail(tmp_path: Path):
    # round2 I-3：settle 声明 set_alias「萤」且 staging 行已带「萤」是双写契约
    # 的合法形态（op 到 commit 才落地）——对 committed 前态对账会假红
    _seed(tmp_path, {}, identity={"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]})
    sidecar_dir = tmp_path / "staging" / "truth"
    sidecar_dir.mkdir(parents=True)
    (sidecar_dir / "name_registry.md").write_text(
        "| 类别 | 名 | 备注 |\n|---|---|---|\n| 别名 | 林烽 | 星象局用名 |\n| 别名 | 萤 | ch20 新 |\n",
        encoding="utf-8",
    )
    sidecar = sidecar_dir / "state-settling-decisions.json"
    sidecar.write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 20,
                "produced_at": "2026-10-28T00:00:00Z",
                "facts_ops": {"identity": [{"op": "set_alias", "alias": "萤", "from_ch": 20}]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert not issues


def test_identity_union_rows_staged_plus_committed(tmp_path: Path):
    # round2 I-3：staged 只有新行「萤」、旧行「林烽」只在 committed——
    # 文件粒度早退会把旧别名判成无行假红；并集后全绿
    _seed(
        tmp_path, {}, identity={"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽", "萤"]}
    )
    committed = tmp_path / "truth" / "name_registry.md"
    committed.write_text(
        "| 类别 | 名 | 备注 |\n|---|---|---|\n| 别名 | 林烽 | 星象局用名 |\n",
        encoding="utf-8",
    )
    sidecar_dir = tmp_path / "staging" / "truth"
    sidecar_dir.mkdir(parents=True)
    (sidecar_dir / "name_registry.md").write_text(
        "| 类别 | 名 | 备注 |\n|---|---|---|\n| 别名 | 萤 | ch20 新 |\n",
        encoding="utf-8",
    )
    sidecar = sidecar_dir / "state-settling-decisions.json"
    sidecar.write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 20,
                "produced_at": "2026-10-28T00:00:00Z",
                "facts_ops": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert not issues


def test_corrupt_props_json_structured_issue(tmp_path: Path):
    # round2 M-1：既有 props.json 损坏 ⇒ 结构化 issue 指明修复对象，
    # 不裸抛（CLI 否则折算成「文件路径参数非法」误导报因）
    d = tmp_path / "truth" / "facts"
    d.mkdir(parents=True)
    (d / "props.json").write_text("NOT-JSON", encoding="utf-8")
    sidecar = _sidecar(
        tmp_path,
        {"props": [{"op": "hold", "prop": "火纹骨哨", "to": "那罕", "chapter": 20}]},
    )
    issues, _warns = g4_state_settling_check(tmp_path, sidecar)
    assert any("props.json 损坏/不可读" in i for i in issues)


def test_production_composite_path_fires_ss_checks(tmp_path: Path):
    # round2 C-2：生产入口 = build_checkers 复合分区——sidecar 被路由给
    # g4_decisions，existing 槽只见 staged md 目标。ss.* 必须经姊妹约定
    # 定位块在真实复合路径上点火（此前接线是死代码）
    import importlib

    generic = importlib.import_module("shenbi.gates.g4.generic")
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    staged = tmp_path / "staging" / "truth"
    staged.mkdir(parents=True)
    (staged / "current_state.md").write_text("## 当前位置\n东行\n", encoding="utf-8")
    (staged / "state-settling-decisions.json").write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 20,
                "produced_at": "2026-10-28T00:00:00Z",
                "facts_ops": {
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
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    checkers = generic.build_checkers()
    fn = checkers["shenbi-state-settling"]
    result = fn([str(staged / "current_state.md")], None, str(tmp_path), None)
    import json as _json

    payload = _json.loads(result)
    assert any("ss.facts_ops:非法 op" in m for m in payload["must_fix"])


def test_production_composite_path_flags_placeholder_produced_at(tmp_path: Path):
    # audit-T8 round3 I-2：produced_at 现实核查（模型伪造过 4 次）此前只在
    # 裸 fps 路径跑——生产复合路径必须随姊妹约定块点火
    import importlib

    generic = importlib.import_module("shenbi.gates.g4.generic")
    _seed(tmp_path, {})
    staged = tmp_path / "staging" / "truth"
    staged.mkdir(parents=True)
    (staged / "current_state.md").write_text("## 当前位置\n东行\n", encoding="utf-8")

    def _run(produced_at: str) -> list[str]:
        (staged / "state-settling-decisions.json").write_text(
            json.dumps(
                {
                    "$schema": "shenbi-decisions-v1",
                    "skill": "shenbi-state-settling",
                    "chapter": 20,
                    "produced_at": produced_at,
                    "facts_ops": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        fn = generic.build_checkers()["shenbi-state-settling"]
        import json as _json

        return _json.loads(fn([str(staged / "current_state.md")], None, str(tmp_path), None)).get(
            "must_fix", []
        )

    assert any("produced_at" in m and "placeholder" in m for m in _run("2026-10-28T00:00:00Z"))
    # 非占位真值：取 1 小时前、钉非零分秒（避开 future 分支的时钟敏感）
    from datetime import UTC, datetime, timedelta

    real = datetime.now(UTC).replace(minute=23, second=45) - timedelta(hours=1)
    assert not any("produced_at" in m for m in _run(real.strftime("%Y-%m-%dT%H:%M:%SZ")))


def test_registry_copy_key_rows_not_substituted(tmp_path: Path):
    # audit-T8 round3 I-1：`实体·副本` 是独立实体键——子串匹配会把副本行
    # 当母行（顺序决定结果/母行缺席时静默替换 owner）。全键精确匹配后：
    # 副本行在前不干扰母行对账；仅副本行 ⇒ 母行缺席不对账（None 诚实信号）
    _seed(tmp_path, {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}})
    op = {
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
    }
    # 副本行在前 + 母行持真终态 ⇒ 精确命中母行，无 issue
    registry = tmp_path / "truth" / "prop_registry.md"
    registry.parent.mkdir(exist_ok=True)
    registry.write_text(
        "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n"
        "| 火纹骨哨·副本 | 老驼 | ch18 |\n| 火纹骨哨 | 帖木哥 | ch20 |\n",
        encoding="utf-8",
    )
    issues, _warns = g4_state_settling_check(tmp_path, _sidecar(tmp_path, op))
    assert not [i for i in issues if "ss.prop_row_match" in i]
    # 仅副本行 ⇒ 母行缺席：不对账、不替换（旧行为会拿老驼当母行 owner）
    registry.write_text(
        "| 实体名 | 当前owner | 经手事件 |\n|---|---|---|\n| 火纹骨哨·副本 | 老驼 | ch18 |\n",
        encoding="utf-8",
    )
    issues, _warns = g4_state_settling_check(tmp_path, _sidecar(tmp_path, op))
    assert not [i for i in issues if "ss.prop_row_match" in i]
    assert not [i for i in issues if "老驼" in i]


def test_sidecar_top_level_non_dict_structured_issue(tmp_path: Path):
    # audit-T8 round3 I-3(c)：读侧顶层非对象 ⇒ 结构化 issue（裸
    # AttributeError 会炸穿 _guarded_g4 并抢占 g4_decisions 的精确报告）
    _seed(tmp_path, {})
    p = tmp_path / "chapters" / "chapter-20-decisions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('["not", "an", "object"]', encoding="utf-8")
    issues, _warns = g4_state_settling_check(tmp_path, p)
    assert any("顶层必须是 JSON 对象" in i for i in issues)
