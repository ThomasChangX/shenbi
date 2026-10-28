"""T8a: decisions facts_ops schema + 写侧 fail-fast 应用（spec #80 §1.1/§6 P1）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shenbi.exceptions import FactsOpRejectedError
from shenbi.facts.settle_ops import apply_sidecar_ops


def _sidecar(tmp_path: Path, facts_ops: dict[str, Any] | None) -> Path:
    doc: dict[str, Any] = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-state-settling",
        "chapter": 20,
        "produced_at": "2026-10-28T00:00:00Z",
    }
    if facts_ops is not None:
        doc["facts_ops"] = facts_ops
    p = tmp_path / "chapters" / "chapter-20-decisions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _seed_props(tmp_path: Path) -> None:
    d = tmp_path / "truth" / "facts"
    d.mkdir(parents=True, exist_ok=True)
    (d / "props.json").write_text(
        json.dumps(
            {
                "$schema": "shenbi-facts-v1",
                "dim": "props",
                "facts": {"火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": []}},
                "ops_log": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_decisions_doc_accepts_facts_ops_key():
    from shenbi.contracts.schemas.decisions import DecisionsDoc

    doc = DecisionsDoc.model_validate(
        {
            "$schema": "shenbi-decisions-v1",
            "skill": "shenbi-state-settling",
            "chapter": 20,
            "produced_at": "2026-10-28T00:00:00Z",
            "facts_ops": {"props": []},
        }
    )
    assert doc.facts_ops is not None


def test_apply_legal_transfer_updates_facts(tmp_path: Path):
    _seed_props(tmp_path)
    sidecar = _sidecar(
        tmp_path,
        {
            "props": [
                {
                    "op": "transfer",
                    "prop": "火纹骨哨",
                    "from": "那罕",
                    "to": "帖木哥",
                    "evidence": "chapter-20.md L218",
                    "chapter": 20,
                }
            ]
        },
    )
    apply_sidecar_ops(tmp_path, sidecar)
    from shenbi.facts.enums import FactsDim
    from shenbi.facts.store import load_facts

    out = load_facts(tmp_path, FactsDim.PROPS)
    assert out is not None and out.props()["火纹骨哨"].owner == "帖木哥"


def test_rejection_writes_nothing(tmp_path: Path):
    # fail-fast：拒收 op ⇒ 不写任何文件（Markdown upsert 前的语义等价面）
    _seed_props(tmp_path)
    target = tmp_path / "truth" / "facts" / "props.json"
    before = target.read_text(encoding="utf-8")
    sidecar = _sidecar(
        tmp_path,
        {
            "props": [
                {
                    "op": "acquire",
                    "prop": "火纹骨哨",
                    "from": "",
                    "to": "帖木哥",
                    "evidence": "chapter-20.md L218",
                    "chapter": 20,
                }
            ]
        },
    )
    with pytest.raises(FactsOpRejectedError):
        apply_sidecar_ops(tmp_path, sidecar)
    assert target.read_text(encoding="utf-8") == before


def test_sidecar_without_facts_ops_is_noop(tmp_path: Path):
    # 旧 settle 兼容期：无 facts_ops 键 ⇒ 不动 facts
    _seed_props(tmp_path)
    sidecar = _sidecar(tmp_path, None)
    apply_sidecar_ops(tmp_path, sidecar)  # no raise, no change


def _stage_sidecar(tmp_path: Path, facts_ops: dict[str, Any] | None) -> None:
    """Staged copy at the contract-declared path (SKILL.md writes) —
    the surface apply_settle_facts_ops consumes via staged_decisions_targets.
    """
    from shenbi.pipeline.checkpoint import STAGING_DIR

    p = tmp_path / STAGING_DIR / "truth" / "state-settling-decisions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, Any] = {
        "$schema": "shenbi-decisions-v1",
        "skill": "shenbi-state-settling",
        "chapter": 20,
        "produced_at": "2026-10-28T00:00:00Z",
    }
    if facts_ops is not None:
        doc["facts_ops"] = facts_ops
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def test_apply_settle_facts_ops_rejection_routes_feedback(tmp_path: Path):
    # commit 站点共享 helper：拒收 ⇒ 指向性 retry_feedback + 返回消息，
    # facts 零变更（staging 保留由调用方路径保证）
    from shenbi.facts.enums import FactsDim
    from shenbi.facts.store import load_facts
    from shenbi.pipeline.chapter_loop import apply_settle_facts_ops
    from shenbi.pipeline.state import PipelineState

    _seed_props(tmp_path)
    before = load_facts(tmp_path, FactsDim.PROPS)
    _stage_sidecar(
        tmp_path,
        {
            "props": [
                {
                    "op": "acquire",
                    "prop": "火纹骨哨",
                    "from": "",
                    "to": "帖木哥",
                    "evidence": "chapter-20.md L218",
                    "chapter": 20,
                }
            ]
        },
    )
    state = PipelineState(project_dir=str(tmp_path))
    msg = apply_settle_facts_ops(state, tmp_path, "shenbi-state-settling", 20)
    assert msg is not None and "火纹骨哨" in msg
    key = "ch20-shenbi-state-settling"
    assert key in state.chapter_loop.retry_feedback
    assert msg in state.chapter_loop.retry_feedback[key]
    assert load_facts(tmp_path, FactsDim.PROPS) == before


def test_apply_settle_facts_ops_noop_without_staged_sidecar(tmp_path: Path):
    # 无 staged sidecar（契约目标不在 staging）⇒ None，无 feedback 副作用
    from shenbi.pipeline.chapter_loop import apply_settle_facts_ops
    from shenbi.pipeline.state import PipelineState

    state = PipelineState(project_dir=str(tmp_path))
    assert apply_settle_facts_ops(state, tmp_path, "shenbi-state-settling", 20) is None
    assert not state.chapter_loop.retry_feedback


def _seed_counters(tmp_path: Path) -> None:
    d = tmp_path / "truth" / "facts"
    d.mkdir(parents=True, exist_ok=True)
    (d / "counters.json").write_text(
        json.dumps(
            {
                "$schema": "shenbi-facts-v1",
                "dim": "counters",
                "facts": {"名字数": {"name": "名字数", "value": 5, "history": []}},
                "ops_log": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_two_phase_zero_write_across_dims(tmp_path: Path):
    # audit-T8 C2：合法 props + 非法 counters ⇒ 拒收时 props.json 也不写
    _seed_props(tmp_path)
    _seed_counters(tmp_path)
    props_before = (tmp_path / "truth" / "facts" / "props.json").read_text(encoding="utf-8")
    counters_before = (tmp_path / "truth" / "facts" / "counters.json").read_text(encoding="utf-8")
    sidecar = _sidecar(
        tmp_path,
        {
            "props": [
                {
                    "op": "transfer",
                    "prop": "火纹骨哨",
                    "from": "那罕",
                    "to": "帖木哥",
                    "evidence": "chapter-20.md L218",
                    "chapter": 20,
                }
            ],
            "counters": [
                # set 非种子期（chapter=20）⇒ 拒收
                {"op": "set", "name": "名字数", "delta": 9, "chapter": 20}
            ],
        },
    )
    with pytest.raises(FactsOpRejectedError):
        apply_sidecar_ops(tmp_path, sidecar)
    assert (tmp_path / "truth" / "facts" / "props.json").read_text(encoding="utf-8") == props_before
    assert (tmp_path / "truth" / "facts" / "counters.json").read_text(
        encoding="utf-8"
    ) == counters_before


def test_multi_sidecar_rejection_zero_write(tmp_path: Path):
    # audit-T8 C2 跨 sidecar：第一个合法、第二个非法 ⇒ 单次调用零写入
    _seed_props(tmp_path)
    before = (tmp_path / "truth" / "facts" / "props.json").read_text(encoding="utf-8")
    legal = _sidecar(
        tmp_path,
        {
            "props": [
                {
                    "op": "transfer",
                    "prop": "火纹骨哨",
                    "from": "那罕",
                    "to": "帖木哥",
                    "evidence": "chapter-20.md L218",
                    "chapter": 20,
                }
            ]
        },
    )
    second = tmp_path / "chapters" / "chapter-20-2nd-decisions.json"
    second.write_text(
        json.dumps(
            {
                "$schema": "shenbi-decisions-v1",
                "skill": "shenbi-state-settling",
                "chapter": 20,
                "produced_at": "2026-10-28T00:00:00Z",
                "facts_ops": {
                    "props": [
                        {
                            "op": "acquire",
                            "prop": "火纹骨哨",
                            "to": "老驼",
                            "evidence": "L1",
                            "chapter": 20,
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(FactsOpRejectedError):
        apply_sidecar_ops(tmp_path, legal, second)
    assert (tmp_path / "truth" / "facts" / "props.json").read_text(encoding="utf-8") == before


def test_malformed_op_wrapped_as_rejection(tmp_path: Path):
    # audit-T8 I5：闭集外自造键（ValidationError）折算为 FactsOpRejectedError
    _seed_props(tmp_path)
    sidecar = _sidecar(
        tmp_path,
        {"props": [{"op": "transfer", "prop": "火纹骨哨", "自造键": 1}]},
    )
    with pytest.raises(FactsOpRejectedError, match="结构非法"):
        apply_sidecar_ops(tmp_path, sidecar)


def test_list_valued_facts_ops_rejected(tmp_path: Path):
    # audit-T8 I5：facts_ops 非对象形态 ⇒ 折算拒收（非裸 AttributeError）
    _seed_props(tmp_path)
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
    with pytest.raises(FactsOpRejectedError, match="必须是对象"):
        apply_sidecar_ops(tmp_path, p)


def test_replayed_counter_increment_not_double_counted(tmp_path: Path):
    # audit-T8 I6：at-least-once 重放——同章同计数器同 op 已在 ops_log ⇒ 跳过
    _seed_counters(tmp_path)
    cf = tmp_path / "truth" / "facts" / "counters.json"
    doc = json.loads(cf.read_text(encoding="utf-8"))
    doc["ops_log"] = [
        {"dim": "counters", "name": "名字数", "op": "increment", "delta": 1, "chapter": 20}
    ]
    cf.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    sidecar = _sidecar(
        tmp_path,
        {"counters": [{"op": "increment", "name": "名字数", "delta": 1, "chapter": 20}]},
    )
    apply_sidecar_ops(tmp_path, sidecar)
    from shenbi.facts.enums import FactsDim
    from shenbi.facts.store import load_facts

    out = load_facts(tmp_path, FactsDim.COUNTERS)
    assert out is not None and out.counters()["名字数"].value == 5  # 不双计


def test_commit_site_applies_before_write_loop(tmp_path: Path):
    # audit-T8 M12（站点 3）：拒收 ⇒ _commit_staging_for_checkpoint 上抛，
    # 写循环未执行（truth/prop_registry.md 不落），staging 保留
    from shenbi.pipeline.checkpoint import STAGING_DIR

    _seed_props(tmp_path)
    staged = tmp_path / STAGING_DIR / "truth"
    staged.mkdir(parents=True)
    (staged / "prop_registry.md").write_text(
        "| 实体名 | 当前owner |\n|---|---|\n", encoding="utf-8"
    )
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
                            "op": "acquire",
                            "prop": "火纹骨哨",
                            "to": "老驼",
                            "evidence": "L1",
                            "chapter": 20,
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    from shenbi.pipeline.cli import _commit_staging_for_checkpoint
    from shenbi.pipeline.state import CheckpointData, CheckpointType

    cp = CheckpointData(type=CheckpointType.STATE_SETTLE, chapter=20)
    with pytest.raises(FactsOpRejectedError):
        _commit_staging_for_checkpoint(tmp_path, cp)
    assert (tmp_path / "truth" / "prop_registry.md").exists() is False  # 写循环未跑
    assert (staged / "state-settling-decisions.json").is_file()  # staging 保留


def test_same_chapter_two_hop_transfer_reaches_final_owner(tmp_path: Path):
    # audit-T8 round2 #1 核心：同章两跳 A→B、B→C 各自生效——粗键
    # (prop,op,chapter) 会把第二跳错当重放吞掉（终态滞留 B）
    from shenbi.facts.enums import FactsDim
    from shenbi.facts.store import load_facts

    _seed_props(tmp_path)
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
    apply_sidecar_ops(tmp_path, sidecar)
    out = load_facts(tmp_path, FactsDim.PROPS)
    assert out is not None
    assert out.props()["火纹骨哨"].owner == "帖木哥"
    assert len(out.ops_log) == 2
    # 整批重放（at-least-once 窗口）：两跳各自指纹命中 ⇒ 全跳过，不四计
    apply_sidecar_ops(tmp_path, sidecar)
    replayed = load_facts(tmp_path, FactsDim.PROPS)
    assert replayed is not None
    assert replayed.props()["火纹骨哨"].owner == "帖木哥"
    assert len(replayed.ops_log) == 2


def test_same_delta_double_increment_counts_both(tmp_path: Path):
    # audit-T8 round2 #1 附带：同章同 delta 双 increment 是两条合法事件——
    # delta 入指纹后布尔判定仍会吞第二条，多重集计数才计满
    from shenbi.facts.enums import FactsDim
    from shenbi.facts.store import load_facts

    _seed_counters(tmp_path)
    sidecar = _sidecar(
        tmp_path,
        {
            "counters": [
                {"op": "increment", "name": "名字数", "delta": 1, "chapter": 20},
                {"op": "increment", "name": "名字数", "delta": 1, "chapter": 20},
            ]
        },
    )
    apply_sidecar_ops(tmp_path, sidecar)
    out = load_facts(tmp_path, FactsDim.COUNTERS)
    assert out is not None and out.counters()["名字数"].value == 7
    # 整批重放：两条指纹各已记 1 ⇒ 都跳过
    apply_sidecar_ops(tmp_path, sidecar)
    replayed = load_facts(tmp_path, FactsDim.COUNTERS)
    assert replayed is not None and replayed.counters()["名字数"].value == 7


def test_mixed_delta_same_chapter_both_counted(tmp_path: Path):
    # +1 与 +3 同章——不同指纹天然各自生效
    from shenbi.facts.enums import FactsDim
    from shenbi.facts.store import load_facts

    _seed_counters(tmp_path)
    sidecar = _sidecar(
        tmp_path,
        {
            "counters": [
                {"op": "increment", "name": "名字数", "delta": 1, "chapter": 20},
                {"op": "increment", "name": "名字数", "delta": 3, "chapter": 20},
            ]
        },
    )
    apply_sidecar_ops(tmp_path, sidecar)
    out = load_facts(tmp_path, FactsDim.COUNTERS)
    assert out is not None and out.counters()["名字数"].value == 9


def test_partial_replay_applies_new_same_fingerprint_op(tmp_path: Path):
    # 多重集精度：log 已记 1 条 (名字数,increment,+1,ch20)、批内 2 条同指纹
    # ⇒ 第 1 条跳（重放）、第 2 条应用（新增）——布尔判定会把新 op 一起吞掉
    from shenbi.facts.enums import FactsDim
    from shenbi.facts.store import load_facts

    _seed_counters(tmp_path)
    cf = tmp_path / "truth" / "facts" / "counters.json"
    doc = json.loads(cf.read_text(encoding="utf-8"))
    doc["ops_log"] = [
        {"dim": "counters", "name": "名字数", "op": "increment", "delta": 1, "chapter": 20}
    ]
    cf.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    sidecar = _sidecar(
        tmp_path,
        {
            "counters": [
                {"op": "increment", "name": "名字数", "delta": 1, "chapter": 20},
                {"op": "increment", "name": "名字数", "delta": 1, "chapter": 20},
            ]
        },
    )
    apply_sidecar_ops(tmp_path, sidecar)
    out = load_facts(tmp_path, FactsDim.COUNTERS)
    assert out is not None and out.counters()["名字数"].value == 6


def test_double_acquire_same_chapter_rejected_not_swallowed(tmp_path: Path):
    # audit-T8 round2 #1 附带：同章双 acquire（to 不同）旧键被静默吞成合法，
    # 现须按状态机拒收（在场实体二次获得）
    _seed_props(tmp_path)
    before = (tmp_path / "truth" / "facts" / "props.json").read_text(encoding="utf-8")
    sidecar = _sidecar(
        tmp_path,
        {
            "props": [
                {"op": "acquire", "prop": "新火种", "to": "老驼", "evidence": "L1", "chapter": 20},
                {
                    "op": "acquire",
                    "prop": "新火种",
                    "to": "帖木哥",
                    "evidence": "L2",
                    "chapter": 20,
                },
            ]
        },
    )
    with pytest.raises(FactsOpRejectedError, match="新火种"):
        apply_sidecar_ops(tmp_path, sidecar)
    assert (tmp_path / "truth" / "facts" / "props.json").read_text(encoding="utf-8") == before


def test_corrupt_existing_facts_file_wrapped_as_rejection(tmp_path: Path):
    # audit-T8 round2 I-2：既有 props.json 损坏 ⇒ 折算拒收（三处 commit 站点
    # 的路由协议不收裸 ValidationError）
    d = tmp_path / "truth" / "facts"
    d.mkdir(parents=True)
    (d / "props.json").write_text("NOT-JSON", encoding="utf-8")
    sidecar = _sidecar(
        tmp_path,
        {"props": [{"op": "hold", "prop": "火纹骨哨", "to": "那罕", "chapter": 20}]},
    )
    with pytest.raises(FactsOpRejectedError, match="损坏/不可读"):
        apply_sidecar_ops(tmp_path, sidecar)
    assert (d / "props.json").read_text(encoding="utf-8") == "NOT-JSON"


def test_dim_swapped_facts_file_rejected(tmp_path: Path):
    # audit-T8 round5 I-1 写侧孪生：自洽错维文件（props.json 装 identity 维
    # 内容）过 schema 验、在 appliers 的维度访问器裸抛 ValueError 绕过
    # commit 路由——槽位断言折算拒收（阶段 1 零写入）
    d = tmp_path / "truth" / "facts"
    d.mkdir(parents=True)
    payload = {
        "$schema": "shenbi-facts-v1",
        "dim": "identity",
        "facts": {"主角": {"narration_name": "那罕", "from_ch": 3, "aliases": []}},
        "ops_log": [],
    }
    (d / "props.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    sidecar = _sidecar(
        tmp_path,
        {
            "props": [
                {
                    "op": "transfer",
                    "prop": "火纹骨哨",
                    "from": "那罕",
                    "to": "帖木哥",
                    "chapter": 20,
                }
            ]
        },
    )
    with pytest.raises(FactsOpRejectedError, match="维度错位"):
        apply_sidecar_ops(tmp_path, sidecar)
    assert json.loads((d / "props.json").read_text(encoding="utf-8")) == payload


def test_invalid_utf8_facts_file_wrapped_as_rejection(tmp_path: Path):
    # audit-T8 round3 I-3(b)：非法 UTF-8 字节（UnicodeDecodeError 是
    # ValueError 子类、非 ValidationError）也须折算拒收
    d = tmp_path / "truth" / "facts"
    d.mkdir(parents=True)
    (d / "props.json").write_bytes(b"\xff\xfe\x00bad")
    sidecar = _sidecar(
        tmp_path,
        {"props": [{"op": "hold", "prop": "火纹骨哨", "to": "那罕", "chapter": 20}]},
    )
    with pytest.raises(FactsOpRejectedError, match="损坏/不可读"):
        apply_sidecar_ops(tmp_path, sidecar)
    assert (d / "props.json").read_bytes() == b"\xff\xfe\x00bad"


def test_sidecar_top_level_non_dict_rejected(tmp_path: Path):
    # audit-T8 round3 I-3(a)：整文件顶层非对象（list）⇒ 折算拒收而非裸
    # AttributeError（G4.dec 常规先挡，此处纵深防御）
    _seed_props(tmp_path)
    p = tmp_path / "chapters" / "chapter-20-decisions.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('["not", "an", "object"]', encoding="utf-8")
    with pytest.raises(FactsOpRejectedError, match="顶层必须是 JSON 对象"):
        apply_sidecar_ops(tmp_path, p)
