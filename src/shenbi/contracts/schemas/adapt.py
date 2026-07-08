"""Adapter: pydantic ValidationError -> gate micro-failure dicts.

Bridges the contract layer (which raises ``pydantic.ValidationError``) and the
gate layer (which reports per-file micro-failures as ``{id, file, s, r}``
dicts). Used by the gate validators (Task 9).
"""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import ValidationError


class GateFailure(TypedDict):
    """A single gate micro-failure: ``{id, file, s, r}``."""

    id: str
    file: str
    s: str
    r: str


def pydantic_err_to_gate_failures(
    err: ValidationError, file_path: str, prefix: str
) -> list[GateFailure]:
    """Map a pydantic :class:`ValidationError` to gate micro-failure dicts.

    Each error becomes ``{"id": f"{prefix}.{e['type']}", "file": file_path,
    "s": "FAIL", "r": f"{loc}: {msg}"}`` where ``loc`` is the dotted location of
    the offending field.
    """
    return [
        {
            "id": f"{prefix}.{e['type']}",
            "file": file_path,
            "s": "FAIL",
            "r": f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}",
        }
        for e in err.errors()
    ]


def decisions_err_to_g2_failures(err: ValidationError, file_path: str) -> list[dict[str, Any]]:
    """Map a :class:`DecisionsDoc` ``ValidationError`` to the legacy ``G2.dec.{1,2,3}``
    numeric IDs so existing G2 test assertions hold after the cutover to pydantic.

    Legacy contract (from the pre-cutover checks):

    * ``G2.dec.2`` — wrong schema version. The ``DecisionsDoc._version`` model
      validator raises a ``value_error`` at the root ``loc == ()`` whose message
      names ``$schema``; an absent ``$schema`` surfaces at ``loc == ('$schema',)``
      with ``type == 'missing'``. Both are classified as a schema-version fault.
    * ``G2.dec.3`` — any other validation fault (missing required keys, bad
      selection/adjustment, etc.).
    """
    fails: list[dict[str, Any]] = []
    for e in err.errors():
        loc = ".".join(str(x) for x in e["loc"])
        msg = e["msg"]
        is_schema_fault = loc == "$schema" or "schema" in msg.lower()
        if is_schema_fault:
            fails.append({"id": "G2.dec.2", "file": file_path, "s": "FAIL", "r": f"{loc}: {msg}"})
        else:
            fails.append({"id": "G2.dec.3", "file": file_path, "s": "FAIL", "r": f"{loc}: {msg}"})
    return fails
