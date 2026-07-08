# Decisions Schema v1

**Version**: `shenbi-decisions-v1`
**Status**: Active (spec 2026-07-07-clean-context-handoff-design.md, Layer A)

## Purpose

Decisions-sidecar artifacts (`*-decisions.json`) persist structured decision
summaries that downstream skills read as lightweight references (Anthropic
"artifact + lightweight reference" pattern). This document is the single
source of truth for the schema.

## Schema

```json
{
  "$schema": "shenbi-decisions-v1",
  "skill": "shenbi-context-composing",
  "chapter": 5,
  "produced_at": "2026-07-07T12:00:00Z",
  "selections": [
    {
      "target": "truth/chapter_summaries.md",
      "selected": ["ch1", "ch2"],
      "basis": "adjacent_to_target_chapter",
      "severity": "low",
      "omitted": []
    }
  ],
  "adjustments": [
    {
      "issue_id": "drift_003",
      "severity": "medium",
      "handling": "compensate_via_pacing",
      "rationale": "drift absorbed by plan pacing"
    }
  ],
  "budget": {
    "context_tokens_estimate": 8500,
    "limit": 12000,
    "trim_applied": "none"
  }
}
```

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `$schema` | string | yes | Must be `shenbi-decisions-v1` |
| `skill` | string | yes | Skill name that produced this file |
| `chapter` | int | yes | Chapter number |
| `produced_at` | string | yes | ISO 8601 timestamp |
| `selections` | array | yes | List of selection decisions |
| `adjustments` | array | no | Drift/conflict adjustments |
| `budget` | object | no | Context budget tracking |

## Enums

### `selections[].basis`
- `adjacent_to_target_chapter` (routine)
- `arc_relevance` (routine)
- `volume_scope` (routine)
- `manual_override` (anomaly)

### `selections[].severity`
- `low` (default — rationale forbidden)
- `high` (P2.5 escape hatch — rationale required)

### `adjustments[].handling`
- `compensate_via_pacing`
- `explicit_callout`
- `defer_to_next_chapter`
- `ignore`

### `budget.trim_applied`
- `none`
- `oldest_first`
- `lowest_relevance`
- `manual`

## P2.5 Rationale Rules

| Condition | rationale field |
|-----------|----------------|
| routine basis + severity `low` | **FORBIDDEN** |
| routine basis + severity `high` | **REQUIRED** |
| `manual_override` (any severity) | **REQUIRED** |
| `adjustments[]` (any) | **REQUIRED** |
| rationale present | ≤100 chars |

## Per-Skill Differences

| Skill | selections targets | adjustments type |
|-------|-------------------|-----------------|
| `context-composing` | truth files, world/rules, chapters | drift, budget trims |
| `market-radar` | market data, trend signals | trend exceptions |
| `chapter-drafting` | plan beats, foreshadowing | pacing deviations, opening |
| `chapter-planning` | arc elements, beats | plan deviations |
| `chapter-revision` | review issues, strategies | deferred issues |
| `state-settling` | state deltas, summaries | conflicts, resolutions |
| `short-drafting` | outline elements, structure | length, tone shifts |
