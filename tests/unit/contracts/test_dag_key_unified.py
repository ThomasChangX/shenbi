"""dag_key unified to patterns-first (spec #60 T0b)."""

from __future__ import annotations

import pytest

from shenbi.contracts import load_registry
from shenbi.contracts.graph import dag_key, normalize_to_glob

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "path",
    [
        "truth/arcs/arc-N.md",
        "audits/chapter-N-anti-ai.md",
        "truth/pending_hooks.md",
        "world/power_system.md",
        "chapters/chapter-N.md",
        "chapters/chapter-{N-3}.md",
    ],
)
def test_dag_key_equals_normalize(path: str) -> None:
    reg = load_registry()
    assert dag_key(path, reg) == normalize_to_glob(path, reg)


def test_divergence_example_gone() -> None:
    """The audit's divergence case: unified key must not collapse into truth/*.md."""
    reg = load_registry()
    assert dag_key("truth/arcs/arc-N.md", reg) == normalize_to_glob("truth/arcs/arc-N.md", reg)
