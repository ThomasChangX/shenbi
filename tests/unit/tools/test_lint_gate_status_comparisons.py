"""Spec #91 T1 lint: gate-status comparison guard (red-green)."""

from tools.lint_gate_status_comparisons import (  # repo convention (test_lint_status_strings.py:8)
    scan,
    scan_file,
)


def test_clean_tree_zero_violations():
    # against the real repo src face (post-Task-2 rewiring)
    out = scan()  # default domain = pipeline/ + phase_runner.py (I4: domain built-in)
    assert out == []


def test_detects_new_private_definition(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("def _gate_passed(r):\n    return True\n")
    out = scan_file(f.read_text(), str(f))
    assert any("_gate_passed" in v for v in out)


def test_detects_bare_compare(tmp_path):
    f = tmp_path / "bad2.py"
    f.write_text('if g4.get("status") == "PASS":\n    pass\n')
    out = scan_file(f.read_text(), str(f))
    assert any("PASS" in v for v in out)


def test_allows_enum_emit_and_non_status_compare(tmp_path):
    f = tmp_path / "ok.py"
    f.write_text(
        "x = GateStatus.PASS.value  # emit, not compare\n"
        'if name == "PASS-ish":\n    pass\n'  # not a status-keyed compare
    )
    assert scan_file(f.read_text(), str(f)) == []
