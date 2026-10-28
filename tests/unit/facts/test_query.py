"""T3: 查询面——现态紧凑投影 + planning 视图 + CLI（spec §1.1）。"""

from __future__ import annotations

from pathlib import Path

from shenbi.facts.cli import main
from shenbi.facts.enums import FactsDim
from shenbi.facts.query import current_state, planning_view
from shenbi.facts.store import save_facts, seed_empty


def _counters_file():
    from shenbi.facts.schemas import FactsFile

    return FactsFile.model_validate(
        {
            "$schema": "shenbi-facts-v1",
            "dim": "counters",
            "facts": {"鉴录名数": {"name": "鉴录名数", "value": 3, "history": []}},
        }
    )


def _identity_file():
    from shenbi.facts.schemas import FactsFile

    return FactsFile.model_validate(
        {
            "$schema": "shenbi-facts-v1",
            "dim": "identity",
            "facts": {"主角": {"narration_name": "那罕", "from_ch": 3, "aliases": ["林烽"]}},
        }
    )


def test_current_state_props_compact(props_file):
    view = current_state(props_file, FactsDim.PROPS)
    assert view == {"火纹骨哨": {"owner": "那罕"}}  # 不含 events 历史


def test_current_state_counters():
    view = current_state(_counters_file(), FactsDim.COUNTERS)
    assert view == {"鉴录名数": {"value": 3}}


def test_current_state_identity_includes_from_ch():
    view = current_state(_identity_file(), FactsDim.IDENTITY)
    assert view["narration_name"] == "那罕"
    assert view["from_ch"] == 3
    assert view["aliases"] == ["林烽"]


def test_planning_view_bounded_text(tmp_path: Path, props_file):
    save_facts(tmp_path, props_file)
    text = planning_view(tmp_path, FactsDim.PROPS)
    assert "火纹骨哨" in text and "那罕" in text
    assert "ch3 老驼所授" not in text  # 历史 events 不进 planning 投影


def test_planning_view_identity_dim_no_keyerror(tmp_path: Path):
    # 全分支审查 I-3：header 表曾缺 identity 键——P2 消费方 context_assemble
    # 首调即 KeyError；回归钉
    save_facts(tmp_path, _identity_file())
    text = planning_view(tmp_path, FactsDim.IDENTITY)
    assert "那罕" in text and "林烽" in text and "自 ch3" in text


def test_planning_view_absent_returns_empty(tmp_path: Path):
    assert planning_view(tmp_path, FactsDim.PROPS) == ""


def test_cli_query_emits_json(tmp_path: Path, props_file, capsys):
    save_facts(tmp_path, props_file)
    rc = main(["query", "--project", str(tmp_path), "--dim", "props"])
    import json

    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["dim"] == "props"
    assert out["facts"]["火纹骨哨"]["owner"] == "那罕"


def test_cli_query_absent_dim_exits_one_with_stderr_warn(tmp_path: Path, capsys):
    seed_empty(tmp_path)
    rc = main(["query", "--project", str(tmp_path), "--dim", "props"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "WARN" in captured.err or "空" in captured.err or "empty" in captured.err
