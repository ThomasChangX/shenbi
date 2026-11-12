"""Read-extractor name roster — single source (spec #87 T2).

Zero-dependency leaf: contracts must never import shenbi.pipeline (the
reverse edge has 0 precedent). loader.READ_EXTRACTORS derives from this
roster; read_extractors.REGISTRY keys must equal it (module assert + test).
"""

READ_EXTRACTOR_NAMES: frozenset[str] = frozenset(
    {
        "volume_chapter",
        "hooks_audit_scoped",
        "hooks_inventory_scoped",
        "hooks_overview",
        "threads_overview",
        "relationships_overview",
        "locations_overview",
        "book_strata_current",
        "matrix_scoped",
        "volume_opening_protocol",
        "recent_increments",
    }
)
