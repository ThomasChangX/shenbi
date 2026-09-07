# Calibration anchors

This directory holds calibration anchor fixtures used by the positive
quality-gates framework. Each anchor is a prose excerpt paired with the
score band an independent subagent is expected to assign it. The anchors
let a reviewer skill self-check whether its scoring is drifting away from
the established baseline.

## Anchor schema (spec #54 C16 / T805)

Every anchor file is Markdown with exactly four sections, in this order:

```markdown
## provenance

provenance: real-output | upstream-copy | synthetic-sample
source: <file+line pointer for real excerpts; explicit synthetic
disclosure for synthetic-sample anchors>

## excerpt

<the prose passage under evaluation. Real excerpts (real-output /
upstream-copy) must be genuine passages from a shipped chapter, imported
canon, or fixture — never invented for the test. Synthetic-sample anchors
must say so explicitly in the provenance section; they calibrate relative
banding, not real-product fidelity.>

## expected_band

<dimension-name band → N-M>

For example: `情感落地 high → 24-30`

## rationale

<why this excerpt earns that band: which concrete textual features move
it into the high/mid/low range. This is what makes the anchor calibratable
rather than merely a label.>
```

Current corpus (2026-08 audit-era, disclosed per spec #54 T3.10): all 27
anchors are `synthetic-sample` — the corpus was authored during the audit
period and is not derived from `novel-output/` chapters. Future anchors
built from real prose must use `real-output`/`upstream-copy` with a
file+line source pointer.

## Layout

Three anchors per dimension — `high`, `mid`, `low` — covering the full
0–30 score range, under per-dimension subdirectories of `arc-payoff/` and
`resonance/`.

## Integrity locking

G0.14 computes a combined SHA256 (CRLF→LF normalized, matching the gate's
own normalization) over every file under this tree (excluding `.gitkeep`)
and compares it to the locked value at `tests/tiers/deps.json` →
`_calibration_hashes.combined`. Any added, removed, or modified anchor
trips the gate until the lock is refreshed.

Re-lock after authoring or editing anchors:

```bash
tests/lock-tool-hashes.sh
```
