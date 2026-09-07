"""G0.17/G0.18/G0.19 fixture authenticity enforcement tests (spec #54 C16).

Negative samples are constructed in tmp_path per spec T0 — they never live
under tests/fixtures/.
"""

from pathlib import Path

from shenbi.gates.g0_purity import (
    ENFORCEMENT_WAVES,
    check_fixture_provenance,
    check_scenario_reference_closure,
    check_variant_bypass,
    load_provenance,
)
from shenbi.status import GateStatus


def _make_scenario(t1: Path, skill: str, test_type: str, body: str) -> None:
    sc = t1 / skill / test_type / "input" / "scenario.md"
    sc.parent.mkdir(parents=True)
    sc.write_text(body, encoding="utf-8")


def _make_fixture(fixtures: Path, rel: str, content: str = "x\n") -> Path:
    p = fixtures / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _make_tree(tmp_path: Path) -> tuple[Path, Path]:
    t1 = tmp_path / "t1-skill"
    fixtures = tmp_path / "tests" / "fixtures"
    t1.mkdir(parents=True)
    fixtures.mkdir(parents=True)
    return t1, fixtures


def test_negative_missing_path(tmp_path: Path) -> None:
    t1, _ = _make_tree(tmp_path)
    _make_scenario(t1, "shenbi-x", "bug-hunt", "uses `tests/fixtures/nope.md` here")
    res = check_scenario_reference_closure(t1, tmp_path)
    assert res[0]["id"] == "G0.17"
    assert res[0]["s"] is GateStatus.WARN  # P0 wave starts in warn mode
    ENFORCEMENT_WAVES["P0"] = "fail"
    try:
        res = check_scenario_reference_closure(t1, tmp_path)
        assert res[0]["s"] is GateStatus.FAIL
    finally:
        ENFORCEMENT_WAVES["P0"] = "warn"


def test_negative_no_provenance(tmp_path: Path) -> None:
    t1, fixtures = _make_tree(tmp_path)
    _make_fixture(fixtures, "a.md")
    _make_scenario(t1, "shenbi-x", "generative", "reads `tests/fixtures/a.md`")
    res = check_fixture_provenance(t1, fixtures)
    assert res[0]["id"] == "G0.18"
    assert res[0]["s"] is GateStatus.WARN
    ENFORCEMENT_WAVES["P1"] = "fail"
    try:
        res = check_fixture_provenance(t1, fixtures)
        assert res[0]["s"] is GateStatus.FAIL
    finally:
        ENFORCEMENT_WAVES["P1"] = "warn"


def test_negative_fake_generated_by(tmp_path: Path) -> None:
    t1, fixtures = _make_tree(tmp_path)
    _make_fixture(
        fixtures,
        "b.md",
        "---\ngenerated_by: manual\nprovenance: hand-made note\n---\nbody\n",
    )
    _make_scenario(t1, "shenbi-x", "generative", "reads `tests/fixtures/b.md`")
    assert load_provenance(fixtures / "b.md") is None  # illegal tri-state
    res = check_fixture_provenance(t1, fixtures)
    assert res[0]["s"] is GateStatus.WARN
    assert "b.md" in res[0]["r"]


def test_carrier_self_exempt(tmp_path: Path) -> None:
    t1, fixtures = _make_tree(tmp_path)
    _make_fixture(fixtures, "a.txt", "words\n")
    (fixtures / "a.txt.provenance.json").write_text(
        '{"provenance": "upstream-copy", "source": "upstream tree"}', encoding="utf-8"
    )
    _make_scenario(t1, "shenbi-x", "generative", "reads `tests/fixtures/a.txt`")
    res = check_fixture_provenance(t1, fixtures)
    assert res[0]["s"] is GateStatus.PASS
    # sidecar itself never enters the scan target set
    res = check_variant_bypass(t1, fixtures)
    assert res[0]["s"] is GateStatus.PASS


def test_variant_bypass_detects_unreferenced(tmp_path: Path) -> None:
    t1, fixtures = _make_tree(tmp_path)
    _make_fixture(fixtures, "foo-example.md", "---\nprovenance: real-output\n---\n")
    _make_fixture(fixtures, "foo-example-variant.md")  # unreferenced, no provenance
    _make_scenario(t1, "shenbi-x", "generative", "reads `tests/fixtures/foo-example.md`")
    res = check_variant_bypass(t1, fixtures)
    assert res[0]["id"] == "G0.19"
    assert res[0]["s"] is GateStatus.WARN
    assert "foo-example-variant.md" in res[0]["r"]
    ENFORCEMENT_WAVES["P2"] = "fail"
    try:
        res = check_variant_bypass(t1, fixtures)
        assert res[0]["s"] is GateStatus.FAIL
    finally:
        ENFORCEMENT_WAVES["P2"] = "warn"


def test_closure_zero_violations(tmp_path: Path) -> None:
    t1, fixtures = _make_tree(tmp_path)
    _make_fixture(fixtures, "ok.md", "---\nprovenance: real-output\nsource: s\n---\n")
    _make_scenario(t1, "shenbi-x", "clean", "reads `tests/fixtures/ok.md`")
    assert check_scenario_reference_closure(t1, tmp_path)[0]["s"] is GateStatus.PASS
    assert check_fixture_provenance(t1, fixtures)[0]["s"] is GateStatus.PASS
    assert check_variant_bypass(t1, fixtures)[0]["s"] is GateStatus.PASS


def test_promotion_guard(tmp_path: Path) -> None:
    """FAIL promotion requires live count == 0 — guard proves warn-mode blocks FAIL."""
    t1, _ = _make_tree(tmp_path)
    _make_scenario(t1, "shenbi-x", "bug-hunt", "uses `tests/fixtures/missing.md`")
    # wave in warn mode: violations > 0 must NOT produce FAIL
    for wave in ("P0", "P1", "P2"):
        ENFORCEMENT_WAVES[wave] = "warn"
    res = check_scenario_reference_closure(t1, tmp_path)
    assert res[0]["s"] is GateStatus.WARN
    # zero violations + fail wave → PASS (guard passes through)
    _make_scenario(t1, "shenbi-y", "bug-hunt", "no refs")
    ENFORCEMENT_WAVES["P0"] = "fail"
    try:
        res = check_scenario_reference_closure(t1, tmp_path)
        # missing.md still referenced by shenbi-x → live count > 0 → FAIL stays
        assert res[0]["s"] is GateStatus.FAIL
    finally:
        ENFORCEMENT_WAVES["P0"] = "warn"


def test_template_dir_in_scope(tmp_path: Path) -> None:
    """_template scenarios are scanned (F751 main battlefield)."""
    t1, fixtures = _make_tree(tmp_path)
    _make_scenario(t1, "_template", "bug-hunt", "uses `tests/fixtures/tpl.md`")
    res = check_scenario_reference_closure(t1, tmp_path)
    assert res[0]["s"] is GateStatus.WARN


def test_whitelist_exempt(tmp_path: Path) -> None:
    t1, fixtures = _make_tree(tmp_path)
    _make_fixture(fixtures, "report-example.txt", "novel")
    (fixtures / "report-example.txt.provenance.json").write_text(
        '{"provenance": "upstream-copy", "source": "public domain novel"}',
        encoding="utf-8",
    )
    _make_scenario(t1, "shenbi-x", "generative", "imports `tests/fixtures/report-example.txt`")
    res = check_fixture_provenance(t1, fixtures)
    assert res[0]["s"] is GateStatus.PASS
