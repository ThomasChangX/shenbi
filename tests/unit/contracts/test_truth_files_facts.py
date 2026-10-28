"""spec #80 T9: facts store 三维注册对账 (truth-files.yaml + status-vocab)。"""

from __future__ import annotations

from pathlib import Path

import yaml

from tools.status_vocab_registry import parse_registry, resolve_symbol_values

_TRUTH_FILES = Path("docs/framework/truth-files.yaml")


def _truth_entries() -> dict[str, dict[str, str]]:
    doc = yaml.safe_load(_TRUTH_FILES.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, str]] = {}
    for row in doc.get("concepts") or []:
        if isinstance(row, dict) and "name" in row:
            rows[str(row["name"])] = {
                "kind": str(row.get("kind", "")),
                "producer": str(row.get("producer", "")),
            }
    return rows


def test_truth_files_registry_has_three_facts_dims() -> None:
    entries = _truth_entries()
    for dim in ("props", "counters", "identity"):
        row = entries.get(f"truth/facts/{dim}.json")
        assert row is not None, f"truth/facts/{dim}.json not registered in truth-files.yaml"
        assert row["kind"] == "truth"
        assert row["producer"] == "pipeline"


def test_status_vocab_has_four_facts_domains() -> None:
    rows = {r.domain: r for r in parse_registry()}
    assert rows["PropOp"].values == frozenset({"transfer", "acquire", "hold", "lose"})
    assert rows["CounterOp"].values == frozenset({"increment", "set"})
    assert rows["IdentityOp"].values == frozenset({"rename", "set_alias"})
    assert rows["FactsDim"].values == frozenset({"props", "counters", "identity"})
    # 值集与 StrEnum 成员全等（plan 审查 R1-M12：四枚举全注册）
    assert resolve_symbol_values("shenbi.facts.enums.PropOp") == rows["PropOp"].values
    assert resolve_symbol_values("shenbi.facts.enums.CounterOp") == rows["CounterOp"].values
    assert resolve_symbol_values("shenbi.facts.enums.IdentityOp") == rows["IdentityOp"].values
    assert resolve_symbol_values("shenbi.facts.enums.FactsDim") == rows["FactsDim"].values
