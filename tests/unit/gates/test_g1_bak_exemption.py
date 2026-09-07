# spec #48 C34 (F412) adjudication Option B: G1.4 .bak write is a documented,
# idempotent exemption to the pure-checker rule (docs/framework/gates.md).

import json
from pathlib import Path

from shenbi.gates import g1


def test_g1_4_bak_idempotent(tmp_path):
    skill = "shenbi-foreshadowing-track"
    target = tmp_path / "state.md"
    target.write_text("k: v\n", encoding="utf-8")
    args = [str(target)]
    r1 = json.loads(g1.gate_G1(skill_name=skill, input_files=args, round_dir=str(tmp_path)))
    r2 = json.loads(g1.gate_G1(skill_name=skill, input_files=args, round_dir=str(tmp_path)))
    baks = list(tmp_path.rglob("*.bak"))
    assert baks, "first run creates the .bak"
    first_content = baks[0].read_bytes()
    # mutate the source between runs: a non-idempotent re-copy would pick up
    # the new bytes — the ".bak exists → skip" branch must keep the original.
    target.write_text("k: CHANGED\n", encoding="utf-8")
    r3 = json.loads(g1.gate_G1(skill_name=skill, input_files=args, round_dir=str(tmp_path)))
    assert baks[0].read_bytes() == first_content, "idempotent: .bak not rewritten"
    g14 = [c for r in (r1, r2, r3) for c in r.get("checks", []) if c.get("id") == "G1.4"]
    assert g14, "G1.4 check present"


def test_exemption_documented():
    # doc pin: exemption must stay written down (gates.md + AGENTS.md + g1 docstring).
    gates_md = (Path(__file__).resolve().parents[3] / "docs/framework/gates.md").read_text(
        encoding="utf-8"
    )
    assert "G1.4" in gates_md and ".bak" in gates_md and "豁免" in gates_md
    agents = (Path(__file__).resolve().parents[3] / "AGENTS.md").read_text(encoding="utf-8")
    assert "G1.4" in agents
    src = Path(g1.__file__).read_text(encoding="utf-8")
    assert "Option B" in src and "F412" in src
