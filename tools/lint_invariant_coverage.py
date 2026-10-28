#!/usr/bin/env python3
"""Lint: invariant census coverage reconciliation (spec #80 T12, §2).

Reconciles ``docs/framework/invariants.md`` (13-dim × four-slot census)
against repo reality, per the phase-column mechanism (spec rev3 R2-M3 /
rev4 R3-M10):

1. **census shape** — 13 dimension rows, phase column ∈ {P1,P2,P3};
2. **due-row four-slot** — any row with 期相 ≤ CURRENT_PHASE must have all
   four slots (载体/声明/门检/审计) non-hole; a hole is a documented gap
   only while its phase is in the future;
3. **mutant obligation** — rows whose obligation column is Yes and whose
   mutant names are due (not deferred by an inline ``P2 增…`` marker) must
   have a matching ``test_mutant_<name>_killed_by_`` case in
   ``tests/gates/test_invariant_mutants.py`` (hyphen↔underscore normalized,
   plan R1-M13);
4. **INDEX required section** — every Active spec entry in
   ``docs/superpowers/specs/INDEX.md`` carries the 「触及的不变量维度」
   line, and a non-无 listing must reference at least one census dim name
   (existence-level check; full claimed⊆census reconciliation is P2+ scope
   per plan R1-M16 narrowing);
5. **literal non-definition** — the census must not contain ``= "…"``
   value-definition forms (op/dim value sets live in src StrEnum →
   status-vocab.md; the census only references).

``CURRENT_PHASE`` is a module constant bumped per batch (P1 now; P2 when
F18 lands). P1 checks the P1-phase subset only — the code→table full
check-id sweep is P2+ (plan R1-M16).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "framework" / "invariants.md"
INDEX = REPO / "docs" / "superpowers" / "specs" / "INDEX.md"
MUTANT_TESTS = REPO / "tests" / "gates" / "test_invariant_mutants.py"

CURRENT_PHASE = "P1"
_PHASE_RANK = {"P1": 1, "P2": 2, "P3": 3}
FOUR_SLOTS = ("载体", "声明", "门检", "审计")
CENSUS_ROW_COUNT = 13
_SEPARATOR_ROW = re.compile(r"^:?-{3,}:?$")
_DEF_LEAK = re.compile(r'=\s*"')


def parse_census(doc: Path = DOC) -> tuple[list[str], list[dict[str, str]]]:
    """Parse the census markdown table -> (header, rows-as-dicts)."""
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in doc.read_text("utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(_SEPARATOR_ROW.fullmatch(c) for c in cells):
            continue
        if header is None:
            header = cells
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    if header is None:
        raise ValueError(f"census table not found in {doc}")
    return header, rows


def _is_hole(value: str) -> bool:
    return not value or value.startswith("—")


def _due(phase: str) -> bool:
    return _PHASE_RANK.get(phase, 99) <= _PHASE_RANK[CURRENT_PHASE]


def mutant_test_name(census_name: str) -> str:
    """R1-M13 normalization: census hyphen form -> test-name prefix."""
    return f"test_mutant_{census_name.replace('-', '_')}_killed_by_"


def _due_mutant_names(cell: str) -> list[str]:
    """Obligation names due at CURRENT_PHASE.

    Obligation cells look like ``Yes（name-swap）`` or
    ``Yes（prop-chain-break；P2 增 settle-illegal-op）`` — a segment carrying
    a P<N> marker with N > CURRENT_PHASE defers the names inside it.
    """
    names: list[str] = []
    body = cell[3:] if cell.startswith("Yes") else cell  # strip the Yes verb
    for segment in re.split(r"[；;，,]", body):
        phase_m = re.search(r"P([123])", segment)
        if phase_m and int(phase_m.group(1)) > _PHASE_RANK[CURRENT_PHASE]:
            continue
        for token in re.findall(r"[\w]+-[\w-]+", segment):
            if token not in names:
                names.append(token)
    return names


def _index_active_entries(index: Path) -> list[tuple[str, str]]:
    """Active spec entries -> (number, entry block text)."""
    text = index.read_text("utf-8")
    entries: list[tuple[str, str]] = []
    for m in re.finditer(r"^### #(\d+) · (.+)$", text, re.MULTILINE):
        number = m.group(1)
        start = m.start()
        nxt = re.search(r"^### #\d+ ·|^---\s*$", text[start + 1 :], re.MULTILINE)
        block = text[start : start + 1 + nxt.start()] if nxt else text[start:]
        if "**状态**：Active" in block or "**Status**: Active" in block:
            entries.append((number, block))
    return entries


def _census_faces(problems: list[str], doc: Path, mutant_tests: Path | None) -> list[str]:
    """Faces 1-3: shape / due-row slots / mutant obligations -> census names."""
    census_names: list[str] = []
    _header, rows = parse_census(doc)
    if len(rows) != CENSUS_ROW_COUNT:
        problems.append(f"{doc}: census must have exactly {CENSUS_ROW_COUNT} rows, got {len(rows)}")
    mutant_src = mutant_tests.read_text("utf-8") if mutant_tests else ""
    for row in rows:
        dim = row.get("维度", "?")
        census_names.append(dim)
        phase = row.get("期相", "")
        if phase not in _PHASE_RANK:
            problems.append(f"{doc}: 「{dim}」期相 {phase!r} ∉ {{P1,P2,P3}}")
            continue
        if not _due(phase):
            continue
        for slot in FOUR_SLOTS:
            if _is_hole(row.get(slot, "")):
                problems.append(
                    f"{doc}: 「{dim}」{slot} 缺槽——期相 {phase} ≤ {CURRENT_PHASE}"
                    "（缺槽只允许出现在未来期相行）"
                )
        cell = row.get("mutant 义务", "")
        if cell.startswith("Yes"):
            for name in _due_mutant_names(cell):
                if mutant_test_name(name) not in mutant_src:
                    problems.append(
                        f"{doc}: 「{dim}」mutant 义务 {name} 到期（期相 {phase} ≤"
                        f" {CURRENT_PHASE}）但 {mutant_tests or 'tests'} 无"
                        f" {mutant_test_name(name)}* 用例"
                    )
    return census_names


def _index_face(problems: list[str], index: Path, census_names: list[str]) -> None:
    """Face 4: Active entries carry the required section (existence level)."""
    for number, block in _index_active_entries(index):
        if "触及的不变量维度" not in block:
            problems.append(
                f"{index}: 活跃 spec #{number} 缺「触及的不变量维度」必填节（INDEX 登记与编号约定）"
            )
            continue
        line_m = re.search(r"触及的不变量维度\*\*：([^\n]+)", block)
        listing = line_m.group(1) if line_m else ""
        if listing.startswith("无"):
            continue
        if not any(name in listing for name in census_names):
            problems.append(
                f"{index}: #{number}「触及的不变量维度」未引用任何普查表维度名——"
                f"列表须引用 {DOC.name} 维度列（或写 无）"
            )


def check(
    doc: Path = DOC,
    index: Path = INDEX,
    mutant_tests: Path | None = MUTANT_TESTS,
) -> list[str]:
    """All predicate faces; returns violation strings (empty = pass)."""
    problems: list[str] = []
    census_names = _census_faces(problems, doc, mutant_tests)
    _index_face(problems, index, census_names)
    # face 5: literal non-definition
    if _DEF_LEAK.search(doc.read_text("utf-8")):
        problems.append(
            f'{doc}: 检出 = "…" 值定义形态——字面量只引用不定义'
            "（权威=src StrEnum → status-vocab.md）"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    """Print every violation; exit 1 if any face found one."""
    del argv  # no flags in P1
    violations = check()
    for v in violations:
        print(v)
    print(
        f"lint_invariant_coverage: CURRENT_PHASE={CURRENT_PHASE}, "
        f"{'OK' if not violations else f'{len(violations)} violation(s)'}"
    )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
