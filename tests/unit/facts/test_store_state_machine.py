"""T1: facts op 状态机——纯内存合法性校验（spec #80 §1.1）。

G0.9 注：facts 态种子为测试内构造的结构性输入（spec §3 钉死的豁免面）。
"""

from __future__ import annotations

import pytest

from shenbi.exceptions import FactsOpRejectedError
from shenbi.facts.schemas import FactsFile, PropTransferEvent
from shenbi.facts.store import (
    apply_counter_op,
    apply_identity_op,
    apply_prop_op,
)


def props_file() -> FactsFile:
    return FactsFile.model_validate(
        {
            "$schema": "shenbi-facts-v1",
            "dim": "props",
            "facts": {
                "火纹骨哨": {"entity": "火纹骨哨", "owner": "那罕", "events": ["ch3 老驼所授"]},
            },
            "ops_log": [],
        }
    )


def counters_file() -> FactsFile:
    return FactsFile.model_validate(
        {
            "$schema": "shenbi-facts-v1",
            "dim": "counters",
            "facts": {"鉴录名数": {"name": "鉴录名数", "value": 3, "history": ["ch8 添第三名"]}},
            "ops_log": [],
        }
    )


def identity_file() -> FactsFile:
    return FactsFile.model_validate(
        {
            "$schema": "shenbi-facts-v1",
            "dim": "identity",
            "facts": {
                "主角": {
                    "narration_name": "那罕",
                    "from_ch": 3,
                    "aliases": ["林烽"],
                }
            },
            "ops_log": [],
        }
    )


# ── props 状态机 ──────────────────────────────────────────────


def test_transfer_from_current_owner_passes():
    ev = PropTransferEvent.model_validate(
        {
            "op": "transfer",
            "prop": "火纹骨哨",
            "from": "那罕",
            "to": "帖木哥",
            "evidence": "chapter-20.md L218",
            "chapter": 20,
        }
    )
    out = apply_prop_op(props_file(), ev)
    assert out.props()["火纹骨哨"].owner == "帖木哥"
    assert len(out.ops_log) == 1


def test_transfer_from_wrong_owner_rejected():
    ev = PropTransferEvent.model_validate(
        {
            "op": "transfer",
            "prop": "火纹骨哨",
            "from": "老驼",
            "to": "帖木哥",
            "evidence": "chapter-20.md L218",
            "chapter": 20,
        }
    )
    with pytest.raises(FactsOpRejectedError):
        apply_prop_op(props_file(), ev)


def test_acquire_without_source_rejected():
    # ch20 伤口形态：帖木哥「我揣了二十年」——无来源的二次获得
    ev = PropTransferEvent.model_validate(
        {
            "op": "acquire",
            "prop": "火纹骨哨",
            "from": "",
            "to": "帖木哥",
            "evidence": "chapter-20.md L218",
            "chapter": 20,
        }
    )
    with pytest.raises(FactsOpRejectedError):
        apply_prop_op(props_file(), ev)


def test_acquire_unknown_entity_is_first_sighting():
    ev = PropTransferEvent.model_validate(
        {
            "op": "acquire",
            "prop": "半块墨",
            "from": "",
            "to": "林烽",
            "evidence": "chapter-1.md L10",
            "chapter": 1,
        }
    )
    out = apply_prop_op(props_file(), ev)
    assert out.props()["半块墨"].owner == "林烽"


def test_copy_entity_is_a_new_key_not_reacquisition():
    # 实体副本语义（spec rev1）：同母题新实体=独立键初见——修复后 ch20 双哨并存全绿
    ev = PropTransferEvent.model_validate(
        {
            "op": "acquire",
            "prop": "火纹骨哨·帖木哥支",
            "from": "",
            "to": "那罕",
            "evidence": "chapter-20.md L218",
            "chapter": 20,
        }
    )
    out = apply_prop_op(props_file(), ev)
    assert out.props()["火纹骨哨"].owner == "那罕"  # 老键不动
    assert out.props()["火纹骨哨·帖木哥支"].owner == "那罕"


def test_lose_by_non_owner_rejected():
    ev = PropTransferEvent.model_validate(
        {
            "op": "lose",
            "prop": "火纹骨哨",
            "from": "帖木哥",
            "to": "",
            "evidence": "chapter-21.md L1",
            "chapter": 21,
        }
    )
    with pytest.raises(FactsOpRejectedError):
        apply_prop_op(props_file(), ev)


# ── counters 单调律 ───────────────────────────────────────────


def test_counter_increment_monotonic():
    out = apply_counter_op(counters_file(), "鉴录名数", "increment", delta=1, chapter=9)
    assert out.counters()["鉴录名数"].value == 4


def test_counter_nonpositive_delta_rejected():
    with pytest.raises(FactsOpRejectedError):
        apply_counter_op(counters_file(), "鉴录名数", "increment", delta=0, chapter=9)
    with pytest.raises(FactsOpRejectedError):
        apply_counter_op(counters_file(), "鉴录名数", "increment", delta=-1, chapter=9)


def test_counter_set_only_legal_at_seed_chapter():
    out = apply_counter_op(counters_file(), "鉴录名数", "set", delta=3, chapter=0)
    assert out.counters()["鉴录名数"].value == 3
    with pytest.raises(FactsOpRejectedError):
        apply_counter_op(counters_file(), "鉴录名数", "set", delta=5, chapter=9)


# ── identity 改名路径 ─────────────────────────────────────────


def test_identity_rename_updates_narration_name():
    out = apply_identity_op(identity_file(), "rename", new_name="临", alias=None, from_ch=25)
    renamed = out.identity()
    assert renamed is not None
    assert renamed.narration_name == "临"
    assert renamed.from_ch == 25


def test_identity_set_alias_appends():
    out = apply_identity_op(identity_file(), "set_alias", new_name=None, alias="萤", from_ch=0)
    aliased = out.identity()
    assert aliased is not None
    assert "萤" in aliased.aliases


# ── audit-T1 M5 补：hold 分支 / lose 成功 / rename 边界 / 校验面 / 不可变性 ──


def test_hold_first_sighting_registers():
    out = apply_prop_op(
        props_file(),
        PropTransferEvent.model_validate(
            {"op": "hold", "prop": "盐包", "from": "", "to": "林烽", "chapter": 2}
        ),
    )
    assert out.props()["盐包"].owner == "林烽"


def test_hold_matching_owner_records_no_change():
    out = apply_prop_op(
        props_file(),
        PropTransferEvent.model_validate(
            {"op": "hold", "prop": "火纹骨哨", "from": "", "to": "那罕", "chapter": 5}
        ),
    )
    assert out.props()["火纹骨哨"].owner == "那罕"
    assert len(out.props()["火纹骨哨"].events) == 2  # 追加持有不变行


def test_hold_wrong_owner_rejected():
    with pytest.raises(FactsOpRejectedError):
        apply_prop_op(
            props_file(),
            PropTransferEvent.model_validate(
                {"op": "hold", "prop": "火纹骨哨", "from": "", "to": "帖木哥", "chapter": 5}
            ),
        )


def test_lose_by_owner_succeeds_and_clears_owner():
    out = apply_prop_op(
        props_file(),
        PropTransferEvent.model_validate(
            {"op": "lose", "prop": "火纹骨哨", "from": "那罕", "to": "", "chapter": 21}
        ),
    )
    assert out.props()["火纹骨哨"].owner == ""
    assert any("lost" in e for e in out.props()["火纹骨哨"].events)


def test_transfer_empty_from_on_owned_entity_rejected():
    # audit-T1 I4：空 from_ 的在场实体 = 无来源获得（与 acquire 同罪）
    with pytest.raises(FactsOpRejectedError):
        apply_prop_op(
            props_file(),
            PropTransferEvent.model_validate(
                {"op": "transfer", "prop": "火纹骨哨", "from": "", "to": "帖木哥", "chapter": 20}
            ),
        )


def test_identity_rename_requires_from_ch_bound():
    with pytest.raises(FactsOpRejectedError):
        apply_identity_op(identity_file(), "rename", new_name="临", alias=None, from_ch=0)
    with pytest.raises(FactsOpRejectedError):
        apply_identity_op(identity_file(), "rename", new_name="", alias=None, from_ch=25)


def test_dim_mismatch_rejected_by_validator():
    import pytest as _pytest

    with _pytest.raises(ValueError):
        FactsFile.model_validate(
            {
                "$schema": "shenbi-facts-v1",
                "dim": "props",
                "facts": {"x": {"name": "x", "value": 1, "history": []}},
            }
        )


def test_wrong_schema_literal_rejected():
    import pytest as _pytest

    with _pytest.raises(ValueError):
        FactsFile.model_validate({"$schema": "shenbi-facts-v2", "dim": "props", "facts": {}})


def test_is_empty_and_typed_accessors():
    empty = FactsFile.model_validate({"$schema": "shenbi-facts-v1", "dim": "identity", "facts": {}})
    assert empty.is_empty is True
    pf = props_file()
    assert set(pf.props()) == {"火纹骨哨"}
    with pytest.raises(ValueError):
        pf.counters()  # dim mismatch accessor


def test_apply_is_immutable_on_input():
    original = props_file()
    snapshot = original.model_copy(deep=True)
    ev = PropTransferEvent.model_validate(
        {"op": "transfer", "prop": "火纹骨哨", "from": "那罕", "to": "帖木哥", "chapter": 20}
    )
    apply_prop_op(original, ev)
    assert original == snapshot  # 输入未被改写
