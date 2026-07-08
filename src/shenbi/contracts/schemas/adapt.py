"""Adapter: pydantic ValidationError -> gate micro-failure dicts.

Bridges the contract layer (which raises ``pydantic.ValidationError``) and the
gate layer (which reports per-file micro-failures as ``{id, file, s, r}``
dicts). Used by the gate validators (Task 9).
"""

from __future__ import annotations

from typing import TypedDict

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
