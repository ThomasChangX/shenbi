"""G4 skill-specific checkers.

PR-19 (Task 3): creates a router that lazy-loads checkers from the legacy
tests/validate-gate.py module via importlib. This breaks the circular import
between gate modules (g5/g6/g7 reference gate_G4) and the still-monolithic
validate-gate.py.

PR-19 (Task 4): the checkers will be moved here from validate-gate.py,
replacing the importlib indirection with direct module imports.
"""

import importlib.util
from pathlib import Path

_VG_PATH = Path(__file__).resolve().parents[4] / "tests" / "validate-gate.py"

_vg_module = None


def _vg():
    """Lazy-load the validate-gate module (circular import safe)."""
    global _vg_module
    if _vg_module is None:
        spec = importlib.util.spec_from_file_location("_vg_legacy", _VG_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load {_VG_PATH}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _vg_module = mod
    return _vg_module


def gate_G4(skill_name, test_type, file_paths, round_dir=None):
    """G4: Route to the correct per-skill checker. Delegates to legacy module."""
    return _vg().gate_G4(skill_name, test_type, file_paths, round_dir)


def gate_G4_bughunt(file_paths):
    """G4.b: Bug-hunt checks. Delegates to legacy module."""
    return _vg().gate_G4_bughunt(file_paths)


def gate_G4_clean(file_paths):
    """G4.c: Clean checks. Delegates to legacy module."""
    return _vg().gate_G4_clean(file_paths)
