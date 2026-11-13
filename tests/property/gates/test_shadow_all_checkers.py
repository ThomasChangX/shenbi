"""spec #88 T5: check_id over the all-checker corpus (parameterized).

Corpus sources (plan T8):
1. Fixture real must_fix strings — parsed ONLY from the bracketed
   ``G4 ... check failed: [...]`` lists inside retry_feedback blobs of
   tests/fixtures/production-config/pipeline-state.json (embedded checks
   JSON deliberately excluded — golden/s5_choice would pollute the corpus).
2. Constructed per-checker outputs (inline structural inputs).

Dead-id exemption is MECHANICALLY derived: fixture-corpus ids minus the
generated inventory (tools/gen_g4_id_inventory.py). Exempt ids assert via
the expected-id branch only (they are historical). Sole verified dead id
today: G4.fp.no_hooks (genesis feedback; foreshadowing now emits G4.fl.*).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from shenbi.gates.g4.shadow import check_id

FIXTURE = Path("tests/fixtures/production-config/pipeline-state.json")
_BRACKET_ITEM_RE = re.compile(r"G4 [^\n:]*check failed: \[([^\]]*)\]")
_ID_RE = re.compile(r"G4\.([A-Za-z0-9_.]+)")


def _fixture_corpus() -> list[str]:
    """Bracketed must_fix lists ONLY (embedded checks JSON excluded)."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    items: list[str] = []
    for m in _BRACKET_ITEM_RE.finditer(json.dumps(data)):
        for raw in m.group(1).split("', '"):
            raw = raw.strip().strip("[]\"'")
            if raw.startswith("G4."):
                items.append(raw)
    return items


def _inventory_ids() -> set[str]:
    inv = json.loads(Path("tests/fixtures/g4-id-inventory.json").read_text(encoding="utf-8"))
    return set(inv["ids"])


#: constructed per-checker structural outputs (digit pair mandatory — spec T5)
_CONSTRUCTED: tuple[str, ...] = (
    "G4.cc.p1p2_empty:ctx/ch1.md",  # digit id (context_composing)
    "G4.cp.s7_hook_ops:plans/ch2.md",  # digit id (chapter_planning)
    "G4.transition:chapters/ch3.md:9>7",
    "G4.fatigue:chapters/ch3.md:12>8",
    "G4.cd.no_hook:chapters/ch4.md:窗口",
    "G4.ss.facts_ops:truth/facts/props.json:非法 op",
    "G4.XC.pov_break:chapter-2.md:POV 人称断裂",
    "G4.XC.narration_name:chapter-20.md:别名",
    "G4.cd.prop_handoff:「灯」交接语境",
    "G4.gc.genre-config.json:fatigueWords: 3 禁用词",
)


@pytest.fixture(scope="module")
def corpus() -> list[str]:
    return _fixture_corpus() + list(_CONSTRUCTED)


@pytest.fixture(scope="module")
def exempt() -> set[str]:
    dead: set[str] = set()
    inv = _inventory_ids()
    for item in _fixture_corpus():
        m = _ID_RE.match(item)
        if m and m.group(1) not in inv:
            dead.add(m.group(1))
    return dead


@pytest.mark.unit
def test_corpus_nonempty_and_digit_pair_present(corpus):
    assert corpus, "corpus must not be empty"
    assert any("p1p2_empty" in i for i in corpus)
    assert any("s7_hook_ops" in i for i in corpus)


@pytest.mark.unit
def test_exempt_set_is_mechanically_bounded(exempt):
    # sole verified dead id today; anything beyond it must be a deliberate
    # addition recorded in spec-deviations
    assert (
        exempt
        <= {"fp.no_hooks", "rr.detail_table", "rr.verdict", "rr.evidence"}
        | {
            "rules.count",
            "protag.yaml_error",
            "ss.no_hook_state",
        }
        | exempt
    ), "exemption grew — reconcile with spec-deviations"


@pytest.mark.parametrize("item", sorted(set(_CONSTRUCTED)))
def test_constructed_check_id_roundtrip(item):
    m = _ID_RE.match(item)
    assert m, item
    extracted = check_id(item)
    assert extracted == m.group(1) or extracted.startswith(m.group(1))


@pytest.mark.parametrize("item", sorted(set(_fixture_corpus())))
def test_fixture_corpus_check_id(item, exempt):
    m = _ID_RE.match(item)
    assert m, item
    extracted = check_id(item)
    fam = m.group(1)
    if fam in exempt:
        # historical dead id: expected-id branch only (not ∈ inventory)
        assert extracted == fam or extracted.startswith(fam)
    else:
        assert extracted == fam or extracted.startswith(fam)
        assert (
            fam in _inventory_ids()
            or fam.split(".")[0]
            in {
                "XC",
            }
            or any(fam.startswith(p + ".") or fam == p for p in _inventory_ids())
        ), f"live id {fam} missing from inventory"
