"""Gate file-list protocol helpers (C13 / F116, spec #39 T8).

The G2/G4 CLI passes file lists as a single comma-joined argv token. A path
containing a comma therefore silently mis-aligns producer/consumer splits.
Until the protocol migration (C34 / spec #48) lands, producers fail fast on
comma-containing paths instead of passing a corrupted list downstream.
"""

from __future__ import annotations


def join_gate_file_list(files: list[str]) -> str:
    """Join gate file lists; raise on comma-containing paths (F116 fail-fast).

    Empty list -> "" (consumers treat empty argv as "no files").
    """
    for f in files:
        if "," in f:
            raise ValueError(
                f"gate file list cannot contain commas (C34 protocol migration pending): {f}"
            )
    return ",".join(files)
