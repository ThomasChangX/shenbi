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
