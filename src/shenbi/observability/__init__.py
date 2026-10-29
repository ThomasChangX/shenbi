"""Observability domain (spec #81): dispatch archive + escape-hatch counter.

Write side is the dispatch path ONLY (fail-safe: an observability failure
never masks the dispatch outcome — same discipline as
``_persist_failed_write_output``). Readers (``tools/observe_report.py``, the
P2 ``dispatch_replay`` skeleton) never write here.
"""

from shenbi.observability.archive import (
    ArchiveFrame,
    archive_enabled,
    bump_stats,
    next_seq,
    put_blob,
    quota_bytes,
    sha256_of,
    skill_contract_sha,
    write_dispatch_archive,
)
from shenbi.observability.escape import (
    DRIFT_THRESHOLD,
    escape_hatch_drift_check,
    update_escape_hatch_state,
)

__all__ = [
    "DRIFT_THRESHOLD",
    "ArchiveFrame",
    "archive_enabled",
    "bump_stats",
    "escape_hatch_drift_check",
    "next_seq",
    "put_blob",
    "quota_bytes",
    "sha256_of",
    "skill_contract_sha",
    "update_escape_hatch_state",
    "write_dispatch_archive",
]
