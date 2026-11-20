"""Judge inter-rater reliability harness (spec #110) — offline, deterministic, zero LLM.

Observation-plane instrument, NOT a gate: nothing in src/shenbi/ may read
its reports (repo discipline, #108 T3 precedent). Replay semantics are
pinned HERE in executable form; spec prose is a gloss.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from shenbi.pipeline.audit_aggregate import extract_finding_units  # noqa: E402
from shenbi.pipeline.llm_output_integrity import check_audit_starve_verdict  # noqa: E402

HARD_SEVERITIES = frozenset({"BLOCKING", "CRITICAL"})
# 单源派发族（SKILL writes 声明的单次派发产物——同族两两 κ 为伪影，族 OR 合成 rater）
SKILL_FAMILY: dict[str, str] = {
    "pov": "group-character",
    "dialogue": "group-character",
    "character": "group-character",
    "motivation": "group-character",
    "texture": "group-craft",
    "reader-pull": "group-craft",
    "anti-ai": "group-craft",
}
_AUDIT_FORM = re.compile(r"chapter-(\d+)-([\w-]+)\.md$")


@dataclass(frozen=True)
class AuditRecord:
    """One valid audit file's dual-caliber ratings (spec r2.2)."""

    chapter: int
    skill: str
    any_binary: int  # 任一 severity finding 存在（证据复现口径）
    hard_binary: int  # BLOCKING/CRITICAL 存在
    hard_count: int  # BLOCKING/CRITICAL 单元数


@dataclass(frozen=True)
class ScanResult:
    """Corpus scan outcome: valid records + invalid disclosure + file total."""

    records: tuple[AuditRecord, ...]
    invalid: tuple[str, ...]
    file_total: int


def scan_audits(audits_dir: Path) -> ScanResult:
    """Walk chapter-<N>-<skill>.md; drop review-summary and starved (invalid)."""
    records: list[AuditRecord] = []
    invalid: list[str] = []
    file_total = 0
    for path in sorted(audits_dir.glob("chapter-*.md")):
        m = _AUDIT_FORM.match(path.name)
        if not m or m.group(2) == "review-summary":
            continue
        file_total += 1
        issues = check_audit_starve_verdict(path)  # #109 T4 单源判定
        if issues:
            invalid.extend(issues)
            continue
        units, _ = extract_finding_units(path.name, path.read_text(encoding="utf-8"))
        hard = sum(1 for u in units if u.severity in HARD_SEVERITIES)
        records.append(
            AuditRecord(int(m.group(1)), m.group(2), 1 if units else 0, 1 if hard else 0, hard)
        )
    return ScanResult(tuple(records), tuple(invalid), file_total)
