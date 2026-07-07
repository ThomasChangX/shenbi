# Clean-Context Handoff — Decisions-Sidecar + Field-Level Reads

**Date**: 2026-07-07
**Status**: Approved (design phase, pre-implementation)
**Scope**: Layer A (decisions-sidecar artifact, 7 skills) + Layer B (field-level reads, 12 skills) + 6 consistency modifications to existing framework code.

## Problem

Shenbi's multi-skill architecture is already clean-context at the runtime level — each `dispatch_codex` call is an independent `subprocess.run(["codex", "exec", prompt])` with zero cross-dispatch memory state. Every skill's context is rebuilt from files declared in its contract `reads`, not inherited from a previous agent's "brain."

However, this clean-context property is **not fully exploited** because intent handoff between skills is incomplete:

1. **Ephemeral skills don't persist their reasoning.** `shenbi-context-composing` (kind=ephemeral, writes=[]) assembles a layered context package but its curation decisions (which chapters selected, which rules included, why drift was handled a certain way) exist only in the assembled `context/chapter-N-context.md` as implicit structure. The next skill reads the result but not the intent.

2. **Natural-language artifacts lose intent.** When `chapter-drafting` writes `chapters/chapter-N.md`, the downstream skills (`state-settling`, `review-*`) see the prose but not the decisions behind it (why this opening, why this pacing adjustment, why this foreshadowing placement).

3. **Reads are file-level, not field-level.** Contracts declare `reads: [truth/audit_drift.md]` but don't say which fields matter. Downstream skills must read entire files and guess what to focus on — a context-filtering gap that LangChain's handoff docs explicitly call out as a design decision ("different agents may need different context depending on their role").

This creates a "game of telephone" effect (Anthropic's term): intent degrades at each skill boundary because the handoff artifact carries results but not decisions. Cross-model dispatch amplifies this — a different model reading the same file may interpret the implicit intent differently.

## Goals

- **Fully align with clean-context best practice** (Anthropic multi-agent research system + LangChain handoffs). All skills remain independently dispatchable, zero memory inheritance, cross-model capable.
- **Eliminate the game of telephone** by persisting curation/authoring decisions as structured artifacts (decisions-sidecar JSON) that downstream skills read as lightweight references.
- **Add field-level context filtering** so downstream skills know which parts of a file to focus on, without reading the entire file blindly.
- **Preserve downstream autonomy** — decisions convey "what was selected and on what basis," not "how to think about it." Avoid anchoring downstream agents on upstream reasoning.

## Non-Goals

- **Atomic segments / forced same-model.** The previous design iteration proposed Layer C (atomic segments forcing same-model on tightly-coupled skill chains). This is **rejected** — the architecture is already clean-context (each dispatch is a fresh process), so "same model inherits implicit context" is a false premise. Forcing same-model violates clean-context without solving any real problem.
- **Reasoning trace persistence.** We persist structured decision summaries, not reasoning chains. Anthropic explicitly warns that raw reasoning traces "confuse the receiving agent" and increase token cost without proportional value.
- **Centralized intent log.** A single `truth/intent-log.md` or `decisions.jsonl` would violate bounded-context-window design and create concurrent-write conflicts on parallel chapter pipelines. Rejected.
- **Embedding decisions in artifact frontmatter.** Putting YAML decisions in `chapter.md` frontmatter violates the "lightweight reference" principle — the reference should be separate from the artifact it describes.

## Industry Best Practice Alignment

This design is grounded in two primary sources:

### Anthropic — "How we built our multi-agent research system"

Key applicable principles (from the engineering blog post, June 2025):

1. **"Subagent output to a filesystem to minimize the 'game of telephone.'"** Direct subagent outputs should bypass the main coordinator via artifact systems where "specialized agents can create outputs that persist independently." Subagents "pass lightweight references back to the coordinator." This is the foundation of Layer A.

2. **"Works particularly well for structured outputs."** The artifact pattern is explicitly scoped to structured outputs (code, reports, data visualizations), not universally applied. This justifies the role-based grading in Section 2.1 — decisions.json is added where it adds value, not everywhere.

3. **"Summarize completed work phases and store essential information in external memory."** Handoffs carry summaries, not full reasoning. This shapes the P2 optimization (rationale only on manual_override).

4. **"Agents can spawn fresh subagents with clean contexts while maintaining continuity through careful handoffs."** Clean-context and continuity are not in tension — continuity comes from persisted artifacts, not memory inheritance. This is the core insight that makes Layer C unnecessary.

### LangChain — "Handoffs" documentation

1. **"Context filtering strategy: Will each agent receive full conversation history, filtered portions, or summaries?"** This is the foundation of Layer B — field-level reads are the "filtered portions" strategy.

2. **"Why not pass all subagent messages? The receiving agent may become confused by irrelevant internal reasoning."** This drives the P2 optimization — rationale is only included when it's relevant (manual_override), not for every routine decision.

3. **"Different agents may need different context depending on their role."** This justifies role-based grading — review skills don't need decisions.json, drafting skills do.

## Approach

Two-layer design (Layer C from previous iteration deleted):

```
Layer A — Decisions-sidecar artifact
  Range: 7 skills (2 ephemeral must-do + 5 natural-language artifact must-do)
  Mechanism: each skill's writes gains an independent decisions.json
  Solves: ephemeral handoff amnesia + creative intent loss
  Aligns: Anthropic "artifact + lightweight reference"

Layer B — Field-level reads contract
  Range: 12 skills (6 high-coupling + 6 medium-coupling)
  Mechanism: frontmatter reads gains {file, fields} dict-form
  Solves: downstream doesn't know which fields to focus on
  Aligns: LangChain "context filtering strategy"
```

Three core principles:

1. **Clean-context fully aligned.** All skills remain cross-model capable. Intent travels via artifacts, never via memory or same-model assumption.
2. **Intent as artifact, not reasoning trace.** decisions.json carries structured decision summaries (enum fields + conditional one-line rationale), never reasoning chains.
3. **Role-based context filtering.** Different skill roles produce/consume different decisions, per LangChain's guidance.

---

## Layer A: Decisions-Sidecar Artifact

### A.1 Role-Based Grading

Per Anthropic's "particularly well for structured outputs" scoping:

| Role | Skills | Layer A Action | Rationale |
|------|--------|---------------|-----------|
| **ephemeral** (must) | `shenbi-context-composing`, `shenbi-market-radar` | kind→artifact + add decisions.json to writes | No artifact = no reference for downstream = max telephone effect |
| **natural-language artifact** (must) | `shenbi-chapter-drafting`, `shenbi-chapter-planning`, `shenbi-chapter-revision`, `shenbi-state-settling`, `shenbi-short-drafting` | add decisions.json to writes (kind stays artifact) | Artifact is result but intent ("why written this way") is lost; decisions lets downstream see intent |
| **structured artifact** (skip) | `shenbi-genre-config`, `shenbi-book-spine-init`, `shenbi-score-*` | no change | Artifact is already structured output; reference is sufficient |
| **review/report** (skip) | all `shenbi-review-*` | no change | Output is itself evaluation; no downstream intent to propagate |

**Total: 7 skills modified.**

### A.2 Unified Decisions Schema (v1)

All skills share one schema; role-specific fields are optional:

```json
{
  "$schema": "shenbi-decisions-v1",
  "skill": "shenbi-context-composing",
  "chapter": 5,
  "produced_at": "2026-07-07T12:00:00Z",
  "selections": [
    {
      "target": "truth/chapter_summaries.md",
      "selected": ["ch1", "ch2", "ch3", "ch4"],
      "basis": "adjacent_to_target_chapter",
      "omitted": []
    },
    {
      "target": "world/rules.md",
      "selected": ["rule_2", "rule_4"],
      "basis": "manual_override",
      "omitted": ["rule_1", "rule_3", "rule_5"],
      "rationale": "rule_5 与本章 POV 冲突，故排除"
    }
  ],
  "adjustments": [
    {
      "issue_id": "drift_003",
      "severity": "medium",
      "handling": "compensate_via_pacing",
      "rationale": "drift 已由 plan 的慢节奏吸收"
    }
  ],
  "budget": {
    "context_tokens_estimate": 8500,
    "limit": 12000,
    "trim_applied": "none"
  }
}
```

### A.3 P2 Optimization: Rationale Only on Anomaly

**Core insight**: routine decisions don't need explanation — only deviations from routine do. Anthropic warns about "irrelevant internal reasoning"; routine-decision rationale is exactly that.

**Rule**: `rationale` field is:
- **Forbidden** when `basis` is a routine enum (`adjacent_to_target_chapter`, `arc_relevance`, `volume_scope`)
- **Required** when `basis == manual_override`
- **Always required** in `adjustments[]` (drift handling is inherently anomalous)

**Effect**:
- 90%+ of selections are routine → zero rationale → zero anchoring
- 10% manual_override → rationale present → downstream knows it's an exception, handles with higher vigilance
- Token cost: decisions.json shrinks from ~400-500 token to ~200-300 token average

**Why this beats alternatives** (evaluated in design phase):
- P1 (cut rationale entirely): loses intent on anomalies — over-compressed
- P3 (separate rationale audit file): file count bloat, "don't read by default" is a soft convention — over-engineered
- P4 (structured rationale): schema complexity not worth it — over-designed
- P5 (downstream declares not-reading rationale): fields are soft constraint, LLM still sees full file — weak enforcement

### A.4 Enum Definitions

```python
# src/shenbi/gates/g4/_decisions_schema.py (new)

DECISIONS_SCHEMA_VERSION = "shenbi-decisions-v1"

VALID_BASIS = {
    "adjacent_to_target_chapter",  # routine: chapters near target
    "arc_relevance",               # routine: related to current arc
    "volume_scope",                # routine: within current volume
    "manual_override",             # anomaly: human/skill explicitly overrode routine
}

VALID_HANDLING = {
    "compensate_via_pacing",       # drift absorbed by pacing adjustment
    "explicit_callout",            # drift surfaced explicitly in text
    "defer_to_next_chapter",       # drift deferred to next chapter
    "ignore",                      # drift below threshold, no action
}

VALID_TRIM = {"none", "oldest_first", "lowest_relevance", "manual"}

ROUTINE_BASIS = VALID_BASIS - {"manual_override"}
```

### A.5 Per-Skill Decisions Content

Each of the 7 skills records different decision types:

| Skill | selections targets | adjustments type | Notes |
|-------|-------------------|-----------------|-------|
| `context-composing` | truth files, world/rules, chapters | drift adjustments, budget trims | Primary use case — curates layered memory |
| `market-radar` | market data sources, trend signals | none (or trend_exceptions) | Genre/market analysis decisions |
| `chapter-drafting` | plan beats (which used/modified), foreshadowing placements | pacing deviations from plan, opening strategy | Records "why I deviated from plan" |
| `chapter-planning` | arc elements selected for this chapter, beats chosen | plan deviations from volume outline | Records "why this chapter shape" |
| `chapter-revision` | review issues addressed, revision strategies | issues deferred, severity calls | Records "why I fixed it this way" |
| `state-settling` | state deltas recorded, summaries written | conflicts detected, resolutions | Records "what state changed and why" |
| `short-drafting` | outline elements used, structure choices | length adjustments, tone shifts | Records short-story-specific decisions |

### A.6 Downstream Consumption

`chapter-drafting` (and other consumers) gain decisions.json in their reads:

```yaml
# skills/shenbi-chapter-drafting/SKILL.md frontmatter
contract:
  reads:
    - plans/chapter-N-plan.md
    - context/chapter-N-context.md
    - context/chapter-N-context-decisions.json   # ← NEW: G1 enforces read
    - style/style_profile.md
    - genre-config.json
    - truth/audit_drift.md
```

**G1 enforces this**: if `context-composing` didn't produce decisions.json, G1 blocks `chapter-drafting` from starting. This is a hard contract, not optional.

---

## Layer B: Field-Level Reads Contract

### B.1 Mechanism (Existing, Extended)

`legacy.py:54` `_normalize_read_item` already supports dict-form `{file, fields}`. 2 review skills already use it. Layer B extends this to 12 core skills.

**Before**:
```yaml
reads:
  - plans/chapter-N-plan.md
  - truth/audit_drift.md
```

**After**:
```yaml
reads:
  - file: plans/chapter-N-plan.md
    fields: [chapter_goal, beats, foreshadowing_directives, pacing_zone]
  - file: truth/audit_drift.md
    fields: [active_drifts, severity, compensation_directives]
```

### B.2 Scope (12 Skills, Two Batches)

**Batch 1 (6 skills, high coupling — done in Phase 3)**:
- `shenbi-context-composing` (overlaps with Layer A)
- `shenbi-chapter-drafting` (overlaps with Layer A)
- `shenbi-chapter-planning` (overlaps with Layer A)
- `shenbi-state-settling` (overlaps with Layer A)
- `shenbi-foreshadowing-plant`
- `shenbi-foreshadowing-track`

**Batch 2 (6 skills, medium coupling — done in Phase 3)**:
- `shenbi-chapter-revision`
- `shenbi-short-drafting`
- `shenbi-style-polishing`
- `shenbi-length-normalizing`
- `shenbi-review-continuity`
- `shenbi-review-pacing`

### B.3 Field Naming Convention

To prevent field-name drift:
- **markdown files**: fields = `##` H2 headings (snake_cased)
- **json files**: fields = top-level keys

This enables automated lint: scan truth file's actual headings/keys, compare to contract.fields, report mismatches.

### B.4 G1 Enhancement (Soft Check, Non-Blocking)

```python
# src/shenbi/gates/g1.py — new soft check

def check_fields_exist(skill: str, inputs: list[str], fields_map: dict) -> list[str]:
    """WARN (not FAIL) if declared fields not found in input files."""
    warnings = []
    for path, fields in fields_map.items():
        if not fields:
            continue
        content = _read_input(path)
        actual = _extract_headings_or_keys(content, path)
        missing = set(fields) - actual
        if missing:
            warnings.append(f"{path}: declared fields {missing} not found in file")
    return warnings  # WARN only, does not block dispatch
```

**Why WARN not FAIL**: truth files evolve, field names change. Hard-blocking would make skills unstartable when a truth file renames a heading. WARN keeps problems visible without fragility. A separate CI lint catches drift periodically.

### B.5 CI Lint: Contract Fields vs Truth File Consistency

New script `scripts/lint_contract_fields.py`:
- Scan all skills' contract.reads dict-form fields
- For each file, read actual headings (markdown) or keys (json)
- Compare declared fields vs actual
- Output mismatch report

Hooked into `justfile` via `just lint` or `just check`, runs in CI.

---

## Consistency Modifications to Existing Code

Adding decisions.json is not an isolated change — 6 existing files must be synchronized to avoid registration failures, G2 misclassification, G4 misses, and output-format ambiguity.

### M1+M2: truth-files.yaml Registration (Two Copies)

**Files**: `docs/framework/truth-files.yaml`, `site/framework/truth-files.yaml`

```yaml
concepts:
  - {name: context/chapter-N-context-decisions.json, kind: decisions}   # NEW
  - {name: chapters/chapter-N-decisions.json, kind: decisions}           # NEW

patterns:
  - {parametric: context/chapter-N-context-decisions.json, glob: context/chapter-*-context-decisions.json}  # NEW
  - {parametric: chapters/chapter-N-decisions.json, glob: chapters/chapter-*-decisions.json}                 # NEW

globs:
  - {pattern: context/chapter-*-context-decisions.json}   # NEW
  - {pattern: chapters/chapter-*-decisions.json}            # NEW
```

New `kind: decisions` at registry level (contract.kind stays `artifact`; the registry kind drives `derive_file_type`).

### M3: derive_file_type Decisions Branch

**File**: `src/shenbi/dispatcher/executor.py`

```python
def _decisions_file_set() -> set[str]:
    """Files listed as kind='decisions' in truth-files.yaml."""
    return {
        name for name, kind in bootstrap_registry().items() if kind == "decisions"
    }

def derive_file_type(skill: str) -> str:
    """Derive G2 FILE_TYPE from the contract layer."""
    try:
        c = load_contract(skill)
    except ContractError:
        return "chapter"
    kind = c["kind"]
    if kind == OutputKind.REPORT:
        return "report"
    if kind == OutputKind.EPHEMERAL:
        return "chapter"
    outputs = {*c["writes"], *c["updates"]}
    if outputs & _truth_file_set():
        return "truth"
    if outputs & _decisions_file_set():     # NEW
        return "decisions"                   # NEW
    return "chapter"
```

### M4: G2 Decisions Validation Branch

**File**: `src/shenbi/gates/g2.py`

New branch before `file_type == "chapter"`:

```python
if file_type == "decisions":
    for fp in fps:
        p = Path(fp)
        # G2.dec.1 — valid JSON
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            mf.append({"id": "G2.dec.1", "file": fp, "s": "FAIL", "r": "invalid JSON"})
            continue
        # G2.dec.2 — schema version
        if data.get("$schema") != "shenbi-decisions-v1":
            mf.append({"id": "G2.dec.2", "file": fp, "s": "FAIL",
                       "r": f"schema version mismatch: {data.get('$schema')}"})
        # G2.dec.3 — required keys
        required = {"skill", "chapter", "selections", "produced_at"}
        missing = required - data.keys()
        if missing:
            mf.append({"id": "G2.dec.3", "file": fp, "s": "FAIL",
                       "r": f"missing keys: {missing}"})
        else:
            checks.append({"id": "G2.dec", "file": fp, "s": "PASS"})
        continue  # skip G2.6/G2.7 word count — critical for JSON files
```

**Critical**: the `continue` skips G2.6/G2.7 (Chinese word count) which would otherwise misfire on JSON and always FAIL.

### M5: phase_runner rglob Expansion

**File**: `src/shenbi/phase_runner.py`

```python
# cmd_post_skill() — before:
output_files = [str(f) for f in proj.rglob("*.md") if f.stat().st_size > 0][:20]

# after:
output_files = []
for f in proj.rglob("*"):
    if f.stat().st_size == 0:
        continue
    if f.suffix == ".md":
        output_files.append(str(f))
    elif f.suffix == ".json" and "decisions" in f.name:
        output_files.append(str(f))
    if len(output_files) >= 20:
        break
```

### M6: dispatch_helper Multi-File Output Format

**File**: `src/shenbi/pipeline/dispatch_helper.py`

When contract has multiple writes, emit multi-file output format template:

```python
if len(output_paths) > 1:
    user_parts.append(
        "This skill produces MULTIPLE files. Output each file separately:\n"
        "```file: <path1>\n<content1>\n```\n"
        "```file: <path2>\n<content2>\n```\n"
        "Decisions JSON must conform to shenbi-decisions-v1 schema "
        "(see docs/framework/decisions-schema.md)."
    )
```

### M7: New Schema Document

**File**: `docs/framework/decisions-schema.md` (new)

Single source of truth for:
- Schema version `shenbi-decisions-v1`
- Field definitions (selections/adjustments/budget)
- Enum value lists (basis/handling/trim_applied)
- Per-skill required-field differences
- Example JSON

Referenced by both G4 validation logic and skill authors.

### Files NOT Modified (Verified)

| Component | Why Not |
|-----------|---------|
| `derive_input_files()` | Already generic, reads from contract["reads"], auto-supports .json |
| `write audit` (snapshot_tree) | Path-based snapshot, file-type agnostic |
| `G1` (existence check) | Already generic |
| `G3` (independence) | Unrelated to file types |
| `G6/G7` (audit) | Audits by skill output, not file type |
| `safe_write` | Generic write, content-agnostic |
| `deps.json` | Lists prerequisites, not output files |

---

## Testing Strategy

### T1: Unit Tests

| Target | File | Key Cases |
|--------|------|-----------|
| `derive_file_type` decisions branch | `tests/unit/test_derive_file_type.py` (extend) | writes with decisions.json → "decisions"; without → "chapter" (regression) |
| G2 decisions branch | `tests/unit/test_g2.py` (extend) | valid decisions.json → PASS; missing $schema → G2.dec.2 FAIL; invalid JSON → G2.dec.1 FAIL; **word count NOT run** (critical regression assertion) |
| G4 decisions schema | `tests/unit/test_g4_context_composing.py` (new) | basis enum valid/invalid; rationale on routine basis → FAIL; rationale missing on manual_override → FAIL; rationale >100 chars → FAIL |
| registry resolve new paths | `tests/unit/test_contracts.py` (extend) | `context/chapter-N-context-decisions.json` resolves; unregistered path still ContractError |
| phase_runner rglob | `tests/unit/test_phase_runner.py` (extend) | .json decisions files included; non-decisions .json excluded |
| P2 rationale rule | `tests/unit/test_decisions_schema.py` (new) | routine basis + rationale → FAIL; manual_override + no rationale → FAIL; adjustments + no rationale → FAIL |

**Fixture principle**: per G0.9, decisions.json test fixtures must be real skill outputs copied to `tests/fixtures/`, not hand-crafted mocks. Phase 1's real context-composing output becomes the test baseline.

### T2: Integration Test

New test: `tests/rounds/test_decisions_handoff_integration.py`

```
Verification chain:
  context-composing produces context.md + decisions.json
    → G2 file_type=decisions PASS
    → G4 schema validation PASS
  chapter-drafting reads include decisions.json
    → G1 validates decisions.json is read (non-empty)
    → chapter-drafting produces chapter.md + chapter-decisions.json
    → G2/G4 PASS
```

**Go/no-go assertion**: chapter-drafting output quality (scored by independent subagent per G3.4) ≥ pre-change baseline. If score drops >2 points, decisions.json is anchoring downstream (P2 insufficient) — escalate to re-evaluating schema (possibly cut rationale entirely, fall back to P1).

### T3: Regression Tests

| Regression Point | Verification |
|-----------------|--------------|
| 67 unchanged skills' G2 still uses chapter/truth/report branches | Run `derive_file_type` on all 67, compare to pre-change results |
| phase_runner rglob change doesn't affect .md-only skills | Run existing T2 planning/drafting phases, output_files list unchanged |
| truth-files.yaml additions don't break existing resolve | All existing contracts' reads still resolve successfully |
| Clean-context invariant | New property test: consecutive dispatches of same skill don't share process state (locks in existing behavior against regression) |

---

## Implementation Phasing

Four phases, each with explicit go/no-go gates:

### Phase 1 — Infrastructure + 2 Ephemeral Skills (3-4 days)

1. Modify truth-files.yaml (M1+M2): register new paths
2. Modify derive_file_type + G2 decisions branch (M3+M4)
3. Modify phase_runner rglob (M5)
4. Modify dispatch_helper output format (M6)
5. Create decisions-schema.md (M7)
6. Modify context-composing + market-radar frontmatter + body
7. All unit tests pass

**GO/NO-GO**: Run 1 chapter. context-composing produces decisions.json and G2/G4 pass?
- NO → schema or G2 branch has issues. Stop, fix before Phase 2.

### Phase 2 — 5 Natural-Language Artifact Skills (2-3 days)

1. Modify chapter-drafting/planning/revision/state-settling/short-drafting: add decisions.json to writes + decisions.json to reads of consumers
2. Add G4 schema validation for each skill's specific decisions
3. Unit tests + T2 integration test

**GO/NO-GO**: Run full T2 chapter-prep → drafting chain. Score ≥ baseline?
- Drop >2 points → decisions anchoring downstream. Re-evaluate schema (consider cutting rationale entirely).

### Phase 3 — Layer B Field-Level Reads (3-4 days)

1. Batch 1: 6 high-coupling skills get {file, fields} dict-form
2. G1 soft-check WARN logic
3. CI lint script, hooked into `just check`
4. Batch 2: 6 medium-coupling skills

**GO/NO-GO**: Lint reports zero mismatches? G1 WARN doesn't block existing dispatch?

### Phase 4 — Regression + Documentation (2 days)

1. Full T1/T2 regression
2. Update AGENTS.md with decisions.json mechanism
3. Finalize docs/framework/decisions-schema.md
4. `just check` fully green

**Total: 10-13 days.**

---

## Cost Analysis

### One-Time Cost

| Work Item | Effort |
|-----------|--------|
| M1-M7 consistency modifications | 2-3 days |
| Layer A: 7 skills frontmatter + body + G4 | 2-3 days |
| Layer B: 12 skills field-level reads | 3-4 days |
| Tests (unit + T2 integration + regression) | 2-3 days |
| Documentation + schema | 1 day |
| **Total** | **10-13 days** |

### Runtime Cost (Per Chapter)

| Cost Item | Before | After | Change |
|-----------|--------|-------|--------|
| context-composing LLM call | 1 | 1 + ~300 token JSON (P2 optimized) | +2-3% |
| chapter-drafting reads | ~8k token | +decisions.json ~250 token | +3% |
| 7 skills each produce decisions | 0 | 7 × ~250 token (P2 avg) | +1.75k token/chapter |
| G2/G4 decisions validation | 0 | 7 schema checks | +tens of ms, negligible |
| Gate failure re-run rate | baseline | est. -20-40% | **saves** |
| **Net runtime** | — | +3-5% token, partially offset by fewer re-runs | **slight increase** |

**Honest assessment**: runtime cost increases slightly (3-5% token), less than the pre-P2 estimate (5-8%) because P2 shrinks average decisions.json size. Gate failure reduction partially offsets but doesn't fully negate the increase.

---

## Risk Register

| Risk | Layer | Severity | Mitigation | Residual |
|------|-------|----------|------------|----------|
| Decisions schema enum incomplete, skill decisions don't fit | A | Medium | `manual_override` fallback + review after 3 chapters | Low |
| **Downstream anchored by rationale** | A | **Medium** (down from Medium-High) | P2: rationale only on manual_override; Phase 2 go/no-go checks score drop >2 | Low |
| G2 decisions branch misfires, blocks legitimate output | M4 | Medium | Unit test coverage + Phase 1 real-run validation | Low |
| truth-files.yaml two copies out of sync | M1+M2 | Low | Lint: docs/ vs site/ consistency check | Low |
| Field-level annotations drift from truth file evolution | B | Medium | CI lint scans actual headings vs declared fields | Low |
| 7 skills produce low-quality decisions | A | Medium | G4 schema validation + 5-chapter manual sampling | Medium |
| Old round compatibility during migration | Global | Medium | decisions.json optional for old rounds, G4 soft-check period | Low |
| Clean-context regression (implicit state introduced) | Global | Low | Property test locks invariant | Low |

**Largest residual risk**: downstream anchoring. P2 compresses anchoring surface to ~10% (only manual_override decisions carry rationale), and Phase 2 go/no-go explicitly checks for score degradation. If anchoring persists despite P2, the fallback is P1 (cut rationale entirely, keep only enum + selected/omitted).

---

## Best Practice Alignment Summary

| Best Practice (Anthropic/LangChain) | Alignment |
|-------------------------------------|-----------|
| Artifact + lightweight reference, minimize telephone | ✅ Layer A decisions.json is artifact, downstream reads as reference |
| Summary, not reasoning trace | ✅ Structured decision summary, not reasoning chain |
| Context filtering strategy (full/filtered/summary) | ✅ Layer B fields = filtered strategy |
| Careful handoffs maintain continuity | ✅ decisions artifact carries intent across handoff |
| **Clean-context subagents** | **✅ Fully aligned** — all skills cross-model capable, zero memory inheritance |
| Treat context management as first-class | ✅ Context handoff elevated from implicit prompt to explicit contract |
| "Works particularly well for structured outputs" | ✅ Role-based grading applies decisions only where it adds value |
| "Irrelevant internal reasoning confuses receiver" | ✅ P2: rationale only on anomalies, routine decisions are rationale-free |

**All 8 best practices fully aligned.**

---

## Key Decisions Log

| Decision | Chosen | Rejected Alternatives | Rationale |
|----------|--------|----------------------|-----------|
| Atomic segments (Layer C) | **Deleted** | Keep as Layer C | Architecture already clean-context; same-model assumption is false premise |
| Layer A scope | **Role-graded (7 skills)** | All ephemeral only / all artifact skills | Anthropic "structured outputs" scoping justifies grading |
| decisions.json approach | **Sidecar artifact** | Frontmatter-embedded / centralized log | Sidecar = lightweight reference; others violate best practice |
| rationale inclusion | **P2: anomaly-only** | Always / never / structured / separate file | P2 compresses anchoring to 10% while preserving intent on exceptions |
| G1 fields check | **WARN non-blocking** | Hard FAIL | Truth files evolve; hard-block creates fragility |
| decisions file_type | **New "decisions" type** | Reuse chapter/truth | JSON needs different G2 validation (no word count) |

---

## Open Questions (Deferred to Implementation)

1. **market-radar decisions content**: its decisions schema is less clear than context-composing (what does a "market analysis decision" look like?). Resolve during Phase 1 implementation — may need a market-radar-specific selections schema.
2. **short-drafting overlap with chapter-drafting**: short-drafting may share most decisions fields with chapter-drafting. Decide during Phase 2 whether to share schema or fork.
3. **chapter-revision reads chapter-drafting's decisions**: chapter-revision produces its own decisions.json (Layer A.5), but should its `reads` also include `chapters/chapter-N-decisions.json` from the prior drafting pass? Likely yes (revision needs to understand drafting intent to revise coherently), but the exact contract reads update is deferred to Phase 2 when implementing chapter-revision.
