#!/usr/bin/env python3
"""Closure check (spec §5.5 #3, Task 18): every ``reads:`` entry has a producer.

A producer is a skill that writes/updates the file, a pipeline-produced file,
or an externally-seeded one (Producer Registry, Task 17).

Failure semantics (the marquee CI mechanism):
  * ORPHAN_READ  → exit 1 (FAIL, block PR). A read with no producer is a broken
    contract the downstream consumer cannot rely on.
  * DANGLING_WRITE → stderr WARN (non-blocking). A write with no consumer is
    harmless drift worth flagging, not blocking.

Matching is glob-aware via ``dag_key`` (Task 3) so a concrete producer write
and a glob consumer read join under one canonical key. It is ALSO glob-superset
aware: a read glob like ``characters/**/*.md`` is satisfied by a producer that
writes ``characters/major/*.md`` — ``dag_key`` normalizes each to a distinct
declared glob, so a pure key-equality check would raise false-positive orphans
for the real (clean-repo) character reads. A read is therefore satisfied if its
canonical key equals a producer key OR a producer's canonical write path matches
into the (possibly broader) read glob.

I4: ``load_all_contracts`` lives in ``shenbi.sync_contracts`` (NOT legacy), and
``load_registry`` returns the typed ``TruthFilesRegistry`` model (Task 10) —
read its model attributes (``reg.concepts``, ``c.name``, ``c.producer``).
"""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shenbi import sync_contracts

#   contract-set loader is resolved at CALL TIME — tests monkeypatch
#   ``shenbi.sync_contracts.load_all_contracts``; a bound ``from`` import would
#   bypass the patch.)
from shenbi.contracts.graph import dag_key
from shenbi.contracts.legacy import load_registry


def find_closure_violations() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return ``(orphan_reads, dangling_writes)``.

    ``orphan_reads``  — ``(skill, path)`` per read with no producer (blocking).
    ``dangling_writes`` — ``(skill, dag_key)`` per write with no consumer (warn).
    """
    contracts = sync_contracts.load_all_contracts()
    reg = load_registry()  # typed TruthFilesRegistry model (post-Task 10)

    # Producer index: canonical key -> producing skills, plus the raw write globs
    # for the glob-superset check.
    producers: dict[str, set[str]] = {}
    producer_keys: list[str] = []
    for skill, c in contracts.items():
        for f in [*c.get("writes", []), *c.get("updates", [])]:
            key = dag_key(f, reg)
            producers.setdefault(key, set()).add(skill)
            producer_keys.append(key)

    external = {c.name for c in reg.concepts if c.producer == "external"}
    pipeline = {c.name for c in reg.concepts if c.producer in {"pipeline", "shared"}}

    orphan: list[tuple[str, str]] = []
    for skill, c in contracts.items():
        for f in c.get("reads", []):
            key = dag_key(f, reg)
            # External/pipeline-seeded files are produced outside the skill graph.
            if key in external or f in external:
                continue
            if key in pipeline or f in pipeline:
                continue
            # Exact canonical-key match (producer writes the same file/glob).
            if key in producers:
                continue
            # Glob-superset: a producer's canonical write path matches INTO the
            # (possibly broader) read glob — e.g. a write of
            # ``characters/major/*.md`` satisfies a read of ``characters/**/*.md``.
            # ``dag_key`` keeps these as distinct declared globs, so key-equality
            # alone would raise a false-positive orphan for the clean repo.
            if any(fnmatch.fnmatch(pk, f) for pk in producer_keys):
                continue
            orphan.append((skill, f))

    # DANGLING_WRITE (warn, non-blocking): a producer key with no reader.
    all_read_keys = {dag_key(r, reg) for c in contracts.values() for r in c.get("reads", [])}
    dangling: list[tuple[str, str]] = []
    for key, sks in producers.items():
        if key in external or key in pipeline or key in all_read_keys:
            continue
        dangling.append((next(iter(sks)), key))

    return orphan, dangling


def main() -> int:
    """Print violations; exit 1 if any ORPHAN_READ, else 0.

    ORPHAN_READ → stderr (FAIL, blocking). DANGLING_WRITE → stderr (WARN).
    """
    orphan, dangling = find_closure_violations()
    for skill, f in orphan:
        print(f"ORPHAN_READ: skill={skill} reads={f} no producer", file=sys.stderr)
    for skill, f in dangling:
        print(f"DANGLING_WRITE (warn): skill={skill} writes={f} no consumer", file=sys.stderr)
    return 1 if orphan else 0


if __name__ == "__main__":
    sys.exit(main())
