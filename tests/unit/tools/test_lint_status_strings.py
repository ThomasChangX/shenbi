"""spec #34 T3: lint_status_strings inverted faces (strict src / tests / tree)."""

from __future__ import annotations

import ast
from pathlib import Path

from tools.lint_status_strings import _unregistered_code_domains, _Visitor, tree_face


def _violations(src: str, strict: bool = True) -> list[str]:
    v = _Visitor("x.py", strict, frozenset({"PASS", "FAIL"}), src.splitlines())
    v.visit(ast.parse(src))
    return v.violations


def test_strict_face_flags_any_bare_literal() -> None:
    # F447 inversion: unknown value (not in ANY vocab) is caught...
    assert _violations('d = {"s": "PASSED"}') != []
    # ...and known values are caught too (only member expressions are legal)
    assert _violations('d = {"s": "PASS"}') != []


def test_member_expression_legal() -> None:
    assert _violations('d = {"s": GateStatus.PASS}') == []
    assert _violations('d = {"s": GateStatus.WARN if x else GateStatus.FAIL}') == []


def test_lookup_key_not_flagged() -> None:
    assert _violations('d = {"status": rec.get("status")}') == []


def test_empty_string_not_flagged() -> None:
    assert _violations('d = {"s": ""}') == []


def tests_face_tolerates_registered_and_legacy() -> None:
    assert _violations('d = {"status": "PASS"}', strict=False) == []
    assert _violations('d = {"status": "DONE"}', strict=False) == []  # legacy alias
    assert _violations('d = {"status": "garbage"}', strict=False) != []


def test_vocab_ok_marker_exempts() -> None:
    src = 'd = {"status": "half-done"}  # vocab-ok: negative test'
    assert _violations(src) == []


def test_tree_face_strict_keys(tmp_path: Path) -> None:
    bad = tmp_path / "chapter-1-revision-decisions.json"
    bad.write_text('{"severity": "catastrophic"}', encoding="utf-8")
    vios: list[str] = []
    tree_face(vios, tmp_path, frozenset({"low", "medium", "high"}))
    assert any("out-of-vocab severity" in v for v in vios)


def test_tree_face_prose_status_tolerated(tmp_path: Path) -> None:
    doc = tmp_path / "chapter-2-decisions.json"
    doc.write_text('{"p1": {"x": {"status": "maintained"}}}', encoding="utf-8")
    vios: list[str] = []
    tree_face(vios, tmp_path, frozenset({"PASS"}))
    assert vios == []


def test_tree_face_legacy_alias_tolerated(tmp_path: Path) -> None:
    # DONE is a registered consumer-side alias — read tolerance, no flag
    doc = tmp_path / "progress.json"
    doc.write_text('{"skills": {"s": {"status": "DONE"}}}', encoding="utf-8")
    vios: list[str] = []
    tree_face(vios, tmp_path, frozenset({"done"}))
    assert vios == []


def test_tree_face_case_drift_flagged(tmp_path: Path) -> None:
    # 'Completed' is a case-variant of registered 'completed' but NOT a
    # registered alias — flagged so new writes converge on canonical form
    doc = tmp_path / "state.json"
    doc.write_text('{"genesis": {"state": "Completed"}}', encoding="utf-8")
    vios: list[str] = []
    tree_face(vios, tmp_path, frozenset({"completed"}))
    assert any("case/legacy drift" in v for v in vios)


def test_registration_gate_passes_on_current_tree() -> None:
    # T901: every status-like domain in src/ is registered — live gate check
    vios: list[str] = []
    _unregistered_code_domains(vios)
    assert vios == []


def test_registration_gate_detects_literal_subscript(monkeypatch) -> None:
    """Literal domains parse as Subscript, not Call — the gate must see them."""
    import tools.lint_status_strings as m

    monkeypatch.setattr(m, "parse_registry", lambda *a, **k: [])
    vios: list[str] = []
    m._unregistered_code_domains(vios)
    assert any("Severity not registered" in v for v in vios)  # Literal domain in enums.py
    assert any("GateStatus not registered" in v for v in vios)  # StrEnum domain in status.py
