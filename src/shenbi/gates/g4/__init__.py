"""G4 skill-specific checkers.

Re-exports the gate_G4 router and bughunt/clean wrappers from generic.py.
Per-skill checkers live in sibling modules (worldbuilding.py, etc.).
"""

from shenbi.gates.g4.generic import (
    g4_generic_bughunt,
    g4_generic_clean,
    g4_generic_generative,
    gate_G4,
    gate_G4_bughunt,
    gate_G4_clean,
)

__all__ = [
    "g4_generic_bughunt",
    "g4_generic_clean",
    "g4_generic_generative",
    "gate_G4",
    "gate_G4_bughunt",
    "gate_G4_clean",
]
