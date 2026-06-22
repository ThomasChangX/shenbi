# Calibration anchors

This directory holds calibration anchor fixtures used by the positive
quality-gates framework. Each anchor is a short excerpt of **real prose**
paired with the score band an independent subagent is expected to assign
it. The anchors let a reviewer skill self-check whether its scoring is
drifting away from the established baseline.

No anchors are authored yet — Phase 2/3 tasks create them per anti-trope
dimension. Until then this directory contains only this README and
`.gitkeep`, and G0.14 locks the empty-set hash.

## Anchor schema

Every anchor file is Markdown with exactly three sections, in this order:

```markdown
## excerpt

<a real prose excerpt — the actual text under evaluation. Never invented
or hand-crafted for the test; always a genuine passage from a shipped
chapter, imported canon, or fixture.>

## expected_band

<dimension-name band → N-M>

For example: `情感落地 high → 24-30`

## rationale

<why this excerpt earns that band: which concrete textual features move
it into the high/mid/low range. This is what makes the anchor calibratable
rather than merely a label.>
```

## Layout

Three anchors per dimension — `high`, `mid`, `low` — covering the full
0–30 score range. Anchors may sit directly in this directory or in a
per-dimension subdirectory:

``+calibration/
├── 情感落地-high.md      # or 情感落地/high.md
├── 情感落地-mid.md
└── 情感落地-low.md
```

## Integrity locking

G0.14 computes a combined SHA256 over every file under this tree
(excluding `.gitkeep`) and compares it to the locked value at
`tests/tiers/deps.json` → `_calibration_hashes.combined`. Any added,
removed, or modified anchor trips the gate until the lock is refreshed.

Re-lock after authoring or editing anchors:

```bash
tests/lock-tool-hashes.sh
```
```
