"""T104 (spec #30 T6): G2/G4 decisions collision regression suite.

16 real production samples (copied from the novel-output tree, G0.9) covering
the observed failure modes: valid, concatenated multi-JSON, prose-prefixed
JSON, missing required fields, extra fields, P2.5 rationale violations, and
other schema violations — plus case16, a valid object with trailing junk
(recovery-then-PASS, the exact historical G2-passes/G4-fails divergence).

Invariants per case: (1) G2 and G4 render the SAME verdict, and (2) the
verdict matches the expected status from the case's failure-mode class —
guards against both gates regressing together.
"""

import json
from pathlib import Path

import pytest

from shenbi.gates.g2 import gate_G2
from shenbi.gates.g4.decisions_validator import g4_decisions

CORPUS = sorted((Path(__file__).parent / "fixtures" / "decisions" / "corpus").glob("*.json"))


def _verdicts(fp: Path) -> tuple[str, str]:
    g2 = json.loads(gate_G2([str(fp)], "decisions"))["status"]
    g4 = json.loads(g4_decisions([str(fp)]))["status"]
    return g2, g4


def _expected(fp: Path) -> str:
    return "PASS" if fp.stem.split("-", 2)[1].startswith("ok") else "FAIL"


@pytest.mark.parametrize("fp", CORPUS, ids=lambda fp: fp.name)
def test_g2_g4_verdicts_agree_and_match_class(fp: Path, tmp_path: Path):
    named = tmp_path / "chapter-9-decisions.json"
    named.write_text(fp.read_text(encoding="utf-8"), encoding="utf-8")
    g2, g4 = _verdicts(named)
    exp = _expected(fp)
    assert g2 == g4 == exp, f"{fp.name}: G2={g2} G4={g4} expected={exp}"


def test_corpus_has_16_cases():
    assert len(CORPUS) == 16
