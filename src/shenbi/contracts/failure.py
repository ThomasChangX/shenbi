"""Dispatch-failure classification, co-located with FailureClass (spec #91 T2).

Pure predicate: no logging, no IO. Lives in the contracts layer so pipeline
faces (chapter_loop, parallel_dispatch, genesis) and any future consumers
share one classifier without importing the dispatch machinery.
"""

from __future__ import annotations

from shenbi.contracts.enums import FailureClass


def classify_dispatch_failure(
    exc: BaseException | None = None,
    returncode: int | None = None,
    *,
    stderr: str = "",
) -> FailureClass:
    """C33 R1 (spec #47): classify a dispatch failure for every retry decision.

    Classification points: ① tenacity predicate (_is_retryable), ② write-audit
    rc=2 GATE_FAIL downgrade in _with_write_audit, ③ chapter_loop scoring
    exits, ④ parallel wave retry branch.
    """
    if returncode == 2 and "write-audit GATE_FAIL" in stderr:
        return FailureClass.DETERMINISTIC_GATE
    if returncode == 2:
        # rc=2 is the deterministic-violation exit (write-audit / validation);
        # other nonzero exits (1/-1 subprocess crashes) stay transient —
        # retrying those is spec S11 semantics, guarded by the budget.
        return FailureClass.DETERMINISTIC_CONTENT
    # Exception face: httpx direct OR openai SDK wrappers (cause chain) are
    # transient (predicate: _is_retryable_exception_tree, wired into tenacity
    # via _is_retryable); unknown failures also classify as TRANSIENT — the
    # retry budget (retry_budget_consumed) guards their amplification.
    return FailureClass.TRANSIENT
