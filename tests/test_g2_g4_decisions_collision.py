"""T104 (spec #30 T6): G2/G4 decisions collision regression suite.

15 real production samples (copied from the novel-output tree, G0.9) covering
the observed failure modes: valid, concatenated multi-JSON, prose-prefixed
JSON, missing required fields, extra fields, P2.5 rationale violations, and
other schema violations. The invariant: the same file must render the SAME
verdict (PASS/FAIL) in gate_G2(file_type="decisions") and g4_decisions —
the 15-case divergence class from the audit (raw_decode truncation recovery
in G2 vs strict json.loads in G4) must stay fixed.
"""

import json
from pathlib import Path

import pytest

from shenbi.gates.g2 import gate_G2
from shenbi.gates.g4.decisions_validator import g4_decisions

CORPUS = sorted((Path(__file__).parent / "fixtures" / "decisions" / "corpus").glob("*.json"))


def _g2(fp: Path) -> str:
    return json.loads(gate_G2([str(fp)], "decisions"))["status"]


def _g4(fp: Path) -> str:
    # g4_decisions only processes *-decisions.json paths; copy under proper name
    return json.loads(g4_decisions([str(fp)]))["status"]


@pytest.mark.parametrize("fp", CORPUS, ids=lambda fp: fp.name)
def test_g2_g4_verdicts_agree(fp: Path, tmp_path: Path):
    named = tmp_path / "chapter-9-decisions.json"
    named.write_text(fp.read_text(encoding="utf-8"), encoding="utf-8")
    assert _g2(named) == _g4(named), (
        f"verdict divergence on {fp.name}: G2={_g2(named)} G4={_g4(named)}"
    )


def test_corpus_has_15_cases():
    assert len(CORPUS) == 15
