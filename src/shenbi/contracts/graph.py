"""Glob-aware DAG key normalization.

Extracted from sync_contracts.py so that G5.2 (runtime WARN), lint_contract_graph
(CI FAIL), and sync_contracts (DAG generation) all use IDENTICAL matching
semantics by importing from one place.

These functions take the typed ``TruthFilesRegistry`` model (Task 10) and read
its attributes (``registry.patterns`` / ``registry.globs``) rather than dict
access — typed, self-documenting, and consistent with ``load_registry``'s model
return type.
"""

from __future__ import annotations

import fnmatch

from shenbi.contracts.schemas.registry import TruthFilesRegistry


def normalize_to_glob(path: str, registry: TruthFilesRegistry) -> str:
    """Parametric -> its declared glob; a path matching a declared glob resolves
    to that glob; other globs/concrete pass through.

    The globs fallback handles per-dimension audit literals like
    ``audits/chapter-N-anti-ai.md``: the registry has ONE parametric for all
    dims (``audits/chapter-N-<dim>.md``), so a concrete-dim literal can't be
    exact-matched against it. Without this fallback, ``expected_outputs``
    would carry literal ``N``/``NNN`` and G5.4 / ``cmd_pre_score`` would never
    match real numbered files (e.g. ``audits/chapter-005-anti-ai.md``).
    Patterns are tried first so a specific parametric glob wins over a broad
    declared glob.
    """
    for p in registry.patterns:
        if p.parametric == path:
            return str(p.glob)
    for g in registry.globs:
        if fnmatch.fnmatch(path, g.pattern):
            return str(g.pattern)
    return path


def dag_key(path: str, registry: TruthFilesRegistry) -> str:
    """Canonical matching key for a path in the DAG.

    A concrete write (audits/chapter-N-anti-ai.md) and a glob read
    (audits/chapter-N-*.md) must join under one edge, so the completeness check
    can see that a report is consumed downstream. Map any path to a declared
    glob it matches; else its parametric glob; else itself.

    Trade-off: matching is glob-aware, so unrelated files that share a broad
    declared glob (e.g. every ``truth/*.md`` file) collapse to one key and
    over-connect in the DAG. Benign for the completeness check — it only
    scrutinizes REPORT producers, which carry specific audit writes — but it
    adds noise for future impact analysis.
    """
    for g in registry.globs:
        if fnmatch.fnmatch(path, g.pattern):
            return str(g.pattern)
    return normalize_to_glob(path, registry)
