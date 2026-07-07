# Clean-Context Handoff — Decisions-Sidecar + Field-Level Reads

**Date**: 2026-07-07
**Status**: Approved (design phase, pre-implementation)
**Scope**: Layer A (decisions-sidecar artifact, 7 skills) + Layer B (field-level reads with real context filtering, 12 skills) + 7 consistency modifications to existing framework code.

## Problem

Shenbi's multi-skill architecture is already clean-context at the runtime level — each `dispatch_codex` call is an independent `subprocess.run(["codex", "exec", prompt])` with zero cross-dispatch memory state. Every skill's context is rebuilt from files declared in its contract `reads`, not inherited from a previous agent's "brain."

However, this clean-context property is **not fully exploited** because intent handoff between skills is incomplete:

1. **Ephemeral skills don't persist their reasoning.** `shenbi-context-composing` (kind=ephemeral, writes=[]) assembles a layered context package but its curation decisions (which chapters selected, which rules included, why drift was handled a certain way) exist only in the assembled `context/chapter-N-context.md` as implicit structure. The next skill reads the result but not the intent.

2. **Natural-language artifacts lose intent.** When `chapter-drafting` writes `chapters/chapter-N.md`, the downstream skills (`state-settling`, `review-*`) see the prose but not the decisions behind it (why this opening, why this pacing adjustment, why this foreshadowing placement).

3. **Reads are file-level, not field-level.** Contracts declare `reads: [truth/audit_drift.md]` but don't say which fields matter. Downstream skills must read entire files and guess what to focus on — a context-filtering gap that LangChain's handoff docs explicitly call out as a design decision ("different agents may need different context depending on their role"). The `read_fields` field is already stored in `Contract.read_fields` (legacy.py:47) but **never consumed** — `_build_skill_prompt` (dispatch_helper.py:151) reads plain strings, ignoring `read_fields` entirely. Layer B closes this gap by implementing real filtering.

This creates a "game of telephone" effect (Anthropic's term): intent degrades at each skill boundary because the handoff artifact carries results but not decisions. Cross-model dispatch amplifies this — a different model reading the same file may interpret the implicit intent differently.

## Goals

- **Fully align with clean-context best practice** (Anthropic multi-agent research system + LangChain handoffs). All skills remain independently dispatchable, zero memory inheritance, cross-model capable.
- **Eliminate the game of telephone** by persisting curation/authoring decisions as structured artifacts (decisions-sidecar JSON) that downstream skills read as lightweight references.
- **Add field-level context filtering** so downstream skills know which parts of a file to focus on, without reading the entire file blindly. This requires implementing real filtering in `_build_skill_prompt` (currently `read_fields` is stored but never consumed).
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

3. **"Summarize completed work phases and store essential information in external memory."** Handoffs carry summaries, not full reasoning. This shapes the P2.5 optimization (rationale only on manual_override + high-stakes).

4. **"Agents can spawn fresh subagents with clean contexts while maintaining continuity through careful handoffs."** Clean-context and continuity are not in tension — continuity comes from persisted artifacts, not memory inheritance. This is the core insight that makes Layer C unnecessary.

### LangChain — "Handoffs" documentation

1. **"Context filtering strategy: Will each agent receive full conversation history, filtered portions, or summaries?"** This is the foundation of Layer B — field-level reads are the "filtered portions" strategy.

2. **"Why not pass all subagent messages? The receiving agent may become confused by irrelevant internal reasoning."** This drives the P2.5 optimization — rationale is only included when it's relevant (manual_override + high-stakes), not for every routine decision.

3. **"Different agents may need different context depending on their role."** This justifies role-based grading — review skills don't need decisions.json, drafting skills do.

## Approach

Two-layer design (Layer C from previous iteration deleted):

```
Layer A — Decisions-sidecar artifact
  Range: 7 skills (2 ephemeral must-do + 5 natural-language artifact must-do)
  Mechanism: each skill's writes gains an independent decisions.json
  Solves: ephemeral handoff amnesia + creative intent loss
  Aligns: Anthropic "artifact + lightweight reference"

Layer B — Field-level reads contract with real filtering
  Range: 12 skills (6 high-coupling + 6 medium-coupling)
  Mechanism: frontmatter reads gains {file, fields} dict-form + _build_skill_prompt
             consumes read_fields to filter file content before LLM sees it
  Solves: downstream doesn't know which fields to focus on (currently reads full files)
  Aligns: LangChain "context filtering strategy" (filtered portions — now actually implemented)
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
      "severity": "low",
      "omitted": []
    },
    {
      "target": "truth/arcs/arc-N.md",
      "selected": ["arc_climax_beat"],
      "basis": "arc_relevance",
      "severity": "high",
      "rationale": "本章是高潮兑现点，arc_climax_beat 必须兑现"
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

### A.3 P2.5 Optimization: Rationale on Anomaly + High-Stakes Escape Hatch

**Core insight**: routine decisions don't need explanation — only deviations from routine do. Anthropic warns about "irrelevant internal reasoning"; routine-decision rationale is exactly that.

**Rule**: `rationale` field is:
- **Forbidden** when `basis` is a routine enum (`adjacent_to_target_chapter`, `arc_relevance`, `volume_scope`) **AND** `severity` is not `high`
- **Required** when `basis == manual_override`
- **Required** when `severity == high` (regardless of basis — high-stakes routine decisions carry intent worth transmitting)
- **Always required** in `adjustments[]` (drift handling is inherently anomalous)

**P2.5 escape hatch**: some routine decisions are high-stakes (e.g., selecting the climax chapter under `basis: arc_relevance`). Forcing these to be rationale-free would lose intent exactly where it matters most. The optional `severity: high` flag lets the skill author mark these decisions as requiring rationale, without breaking the "compress routine anchoring" principle for the 90% of low-stakes routine decisions.

**Effect**:
- ~90% of selections are routine + low-stakes → zero rationale → zero anchoring
- ~5% manual_override → rationale present → downstream knows it's an exception
- ~5% high-stakes routine (`severity: high`) → rationale present → downstream knows to pay attention
- Token cost: decisions.json shrinks from ~400-500 token to ~220-320 token average (slightly above P2's ~200-300 due to high-stakes rationale inclusion)

**Why this beats alternatives** (evaluated in design phase):
- P1 (cut rationale entirely): loses intent on anomalies — over-compressed
- P2 (rationale only on manual_override, no severity): misses high-stakes routine decisions (e.g., climax chapter selection) — blind spot
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

VALID_SEVERITY = {
    "low",     # default for routine decisions — rationale forbidden
    "high",    # high-stakes routine decision — rationale required (P2.5 escape hatch)
}

VALID_HANDLING = {
    "compensate_via_pacing",       # drift absorbed by pacing adjustment
    "explicit_callout",            # drift surfaced explicitly in text
    "defer_to_next_chapter",       # drift deferred to next chapter
    "ignore",                      # drift below threshold, no action
}

VALID_TRIM = {"none", "oldest_first", "lowest_relevance", "manual"}

ROUTINE_BASIS = VALID_BASIS - {"manual_override"}

# P2.5 rationale rule:
# - basis in ROUTINE_BASIS and severity != "high" → rationale FORBIDDEN
# - basis == "manual_override" → rationale REQUIRED (severity ignored)
# - severity == "high" (any basis) → rationale REQUIRED
# - adjustments[] → rationale ALWAYS REQUIRED (anomalous by definition)
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

### B.1 Mechanism (Existing Storage + New Filtering)

**Storage (already exists)**: `legacy.py:54` `_normalize_read_item` already supports dict-form `{file, fields}` and stores it in `Contract.read_fields`. 2 review skills (`shenbi-review-arc-payoff`, `shenbi-review-resonance`) already declare fields.

**Filtering (NEW — the real fix)**: `_build_skill_prompt` (dispatch_helper.py:151-191) currently reads `contract.get("reads", [])` as plain strings and writes entire file contents into the prompt — `read_fields` is **never consumed**. Layer B implements real filtering so the LLM only sees the declared fields, not the entire file. This is what actually aligns with LangChain's "filtered portions" strategy.

**Before (current behavior — full file read)**:
```python
# dispatch_helper.py:151 (current)
for read_path in contract.get("reads", []):
    resolved = _resolve_path(read_path, chapter)
    full_path = project_dir / resolved
    if full_path.exists():
        raw_inputs[resolved] = full_path.read_text(encoding="utf-8")  # ENTIRE file
```

**After (Layer B — real filtering)**:
```python
# dispatch_helper.py:151 (modified)
fields_map = contract.get("read_fields", {})   # ← NEW: consume the stored field map
for read_path in contract.get("reads", []):
    resolved = _resolve_path(read_path, chapter)
    full_path = project_dir / resolved
    if not full_path.exists():
        raw_inputs[resolved] = f"[file not found: {resolved}]"
        continue
    text = full_path.read_text(encoding="utf-8")
    fields = fields_map.get(resolved) or fields_map.get(read_path)
    if fields:
        text = _filter_to_fields(text, fields, resolved)   # ← NEW: real filtering
    raw_inputs[resolved] = text

def _filter_to_fields(text: str, fields: list[str], path: str) -> str:
    """Return only the declared fields from a file.
    - markdown: extract ## H2 sections whose heading matches a field name
    - json: project to only the declared top-level keys
    - If no fields match, return full text + WARN (escape hatch).
    """
    if path.endswith(".md"):
        return _extract_h2_sections(text, fields)
    if path.endswith(".json"):
        return _project_json_keys(text, fields)
    return text  # unknown extension: no filtering (safe default)
```

**Escape hatch (critical)**: if `_filter_to_fields` returns empty (no declared field found in the file), the implementation falls back to returning the full file text and logs a WARN. This prevents silent information loss when a truth file's headings have drifted from the contract declaration.

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

### B.4 G1 Soft Check (Non-Blocking, Pre-Filter Validation)

```python
# src/shenbi/gates/g1.py — new soft check (runs before dispatch)

def check_fields_exist(skill: str, inputs: list[str], fields_map: dict) -> list[str]:
    """WARN (not FAIL) if declared fields not found in input files.

    Runs before _build_skill_prompt's filtering, so the skill author sees
    field-name drift warnings before the LLM ever sees filtered content.
    """
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

**Why WARN not FAIL**: truth files evolve, field names change. Hard-blocking would make skills unstartable when a truth file renames a heading. WARN keeps problems visible without fragility. The escape hatch in B.1 ensures that even if a field is missing, the LLM still receives the full file (no silent information loss).

### B.5 CI Lint: Contract Fields vs Truth File Consistency

New script `scripts/lint_contract_fields.py`:
- Scan all skills' contract.reads dict-form fields
- For each file, read actual headings (markdown) or keys (json)
- Compare declared fields vs actual
- Output mismatch report

Hooked into `justfile` via `just lint` or `just check`, runs in CI.

---

## Consistency Modifications to Existing Code

Adding decisions.json is not an isolated change — 7 existing files must be synchronized to avoid registration failures, G2 misclassification, G4 misses, output-format ambiguity, and phase_runner file_type bypass.

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

### M5: phase_runner Output Discovery — Root-Cause Fix (Replaces rglob Patch)

**File**: `src/shenbi/phase_runner.py`

**Problem**: `cmd_post_skill()` (line 150) uses `proj.rglob("*.md")` to discover outputs — a heuristic that doesn't know which files the skill actually wrote. The original spec proposed expanding rglob to include `.json` decisions files, but that's a patch on the wrong mechanism.

**Root-cause fix**: use `derive_output_files(skill, chapter, proj)` which already returns the authoritative list from the contract.

```python
# cmd_post_skill() — before:
output_files = [str(f) for f in proj.rglob("*.md") if f.stat().st_size > 0][:20]

# after:
from shenbi.dispatcher.executor import derive_output_files
chapter = _extract_chapter_from_state(state)  # or pass chapter through cmd_post_skill
output_files = [p for p in derive_output_files(skill, chapter, proj)
                 if Path(p).exists() and Path(p).stat().st_size > 0]
```

**Why this is better than rglob expansion**:
- No file-extension heuristics (`.md` vs `.json` vs future formats)
- No "decisions" substring matching (brittle)
- Contract is the single source of truth — if the contract says the skill writes it, it's discovered
- Future-proofs against new file types (no rglob changes needed when adding new artifact kinds)
- Removes 5 lines of heuristic code instead of adding 7 lines of more complex heuristics

### M6: dispatch_helper Multi-File Output Format

**File**: `src/shenbi/pipeline/dispatch_helper.py`

When contract has multiple writes, emit multi-file output format template:

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

### M8: phase_runner Hardcoded file_type Fix (NEW — discovered in verification)

**File**: `src/shenbi/phase_runner.py:153`

**Problem discovered during spec verification**: `cmd_post_skill()` calls G2 with a hardcoded `"chapter"` file_type:

```python
# phase_runner.py:153 (current — the bug)
g2 = run_gate("G2", [",".join(output_files), "chapter", str(round_dir)])
                              # ^^^^^^^^^^ hardcoded — bypasses derive_file_type
```

This means M3 (`derive_file_type` returns `"decisions"`) and M4 (G2 decisions branch) are **completely ineffective on the T2/T3 dispatch path** — phase_runner always passes `"chapter"`, so G2 never enters the decisions branch. Only the T1 dispatch path (`executor.py`) calls `derive_file_type` correctly.

**Fix**:

```python
# phase_runner.py:153 (after)
from shenbi.dispatcher.executor import derive_file_type
file_type = derive_file_type(skill)
g2 = run_gate("G2", [",".join(output_files), file_type, str(round_dir)])
```

**Why this matters**: without M8, M3+M4 are dead code on the T2/T3 path. A skill producing decisions.json through the pipeline would have its decisions.json validated as a "chapter" file — triggering G2.6/G2.7 Chinese word count on JSON and always FAILing. This is the exact failure M4 was designed to prevent, but M4 can't prevent it if phase_runner bypasses the file_type derivation.

**Verification**: grep confirms `phase_runner.py:153` is the only G2 call site with a hardcoded file_type. `executor.py:227` already calls `run_g2(output_files, file_type, round_dir)` with the derived type.

| Component | Why Not |
|-----------|---------|
| `derive_input_files()` | Already generic, reads from contract["reads"], auto-supports .json |
| `write audit` (snapshot_tree) | Path-based snapshot, file-type agnostic |
| `G1` (existence check) | Already generic |
| `G3` (independence) | Unrelated to file types |
| `G6/G7` (audit) | Audits by skill output, not file type |
| `safe_write` | Generic write, content-agnostic |
| `deps.json` | Lists prerequisites, not output files |

**Note**: `_build_skill_prompt` (dispatch_helper.py) IS modified by Layer B (B.1) to consume `read_fields` and filter file content — it is no longer in the "not modified" list.

---

## Testing Strategy

### T1: Unit Tests

| Target | File | Key Cases |
|--------|------|-----------|
| `derive_file_type` decisions branch | `tests/unit/test_derive_file_type.py` (extend) | writes with decisions.json → "decisions"; without → "chapter" (regression) |
| G2 decisions branch | `tests/unit/test_g2.py` (extend) | valid decisions.json → PASS; missing $schema → G2.dec.2 FAIL; invalid JSON → G2.dec.1 FAIL; **word count NOT run** (critical regression assertion) |
| G4 decisions schema | `tests/unit/test_g4_context_composing.py` (new) | basis enum valid/invalid; rationale on routine+low-severity basis → FAIL; rationale missing on manual_override → FAIL; rationale missing on severity:high → FAIL; rationale >100 chars → FAIL |
| registry resolve new paths | `tests/unit/test_contracts.py` (extend) | `context/chapter-N-context-decisions.json` resolves; unregistered path still ContractError |
| phase_runner output discovery (M5) | `tests/unit/test_phase_runner.py` (extend) | `derive_output_files` returns contract-declared outputs; non-contract files excluded; .json decisions included via contract not via extension heuristic |
| phase_runner G2 file_type (M8) | `tests/unit/test_phase_runner.py` (extend) | skill with decisions writes → G2 receives "decisions" not "chapter"; regression: skill with only chapter writes → G2 still receives "chapter" |
| P2.5 rationale rule | `tests/unit/test_decisions_schema.py` (new) | routine+low-severity + rationale → FAIL; routine+high-severity + no rationale → FAIL; manual_override + no rationale → FAIL; adjustments + no rationale → FAIL |
| Layer B real filtering (B.1) | `tests/unit/test_dispatch_helper.py` (new) | markdown with declared H2 fields → only those sections in prompt; json with declared keys → only those keys; missing field → fallback to full file + WARN (escape hatch) |

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

**Go/no-go assertion**: chapter-drafting output quality (scored by independent subagent per G3.4) ≥ pre-change baseline. If score drops >2 points, decisions.json is anchoring downstream (P2.5 insufficient) — escalate to re-evaluating schema (fall back to P2: cut severity escape hatch; or P1: cut rationale entirely).

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
3. Fix phase_runner output discovery (M5: replace rglob with derive_output_files)
4. **Fix phase_runner hardcoded "chapter" (M8): call derive_file_type** — critical, without this M3+M4 are dead on T2/T3 path
5. Modify dispatch_helper output format (M6)
6. Create decisions-schema.md (M7)
7. Modify context-composing + market-radar frontmatter + body
8. All unit tests pass

**GO/NO-GO**: Run 1 chapter. context-composing produces decisions.json and G2/G4 pass?
- NO → schema or G2 branch has issues. Stop, fix before Phase 2.
- Also verify: G2 receives `file_type="decisions"` (not "chapter") — if not, M8 is broken.

### Phase 2 — 5 Natural-Language Artifact Skills (2-3 days)

1. **First: resolve Open Question #4** — investigate PRE_WRITE_CHECK overlap for chapter-drafting and check the other 4 skills for existing intent-embedding mechanisms. May narrow scope.
2. Modify chapter-drafting/planning/revision/state-settling/short-drafting: add decisions.json to writes + decisions.json to reads of consumers
3. Add G4 schema validation for each skill's specific decisions (incl. P2.5 severity rule)
4. Unit tests + T2 integration test

**GO/NO-GO**: Run full T2 chapter-prep → drafting chain. Score ≥ baseline?
- Drop >2 points → decisions anchoring downstream. Re-evaluate schema (consider cutting rationale entirely).

### Phase 3 — Layer B Field-Level Reads + Real Filtering (4-5 days)

1. **Implement `_filter_to_fields` in dispatch_helper.py** (B.1) — markdown H2 extraction + JSON key projection + escape hatch fallback
2. **Wire `read_fields` into `_build_skill_prompt`** (B.1) — consume the stored field map, replace full-file reads with filtered reads
3. Batch 1: 6 high-coupling skills get {file, fields} dict-form
4. G1 soft-check WARN logic (B.4) — pre-filter validation
5. CI lint script (B.5), hooked into `just check`
6. Batch 2: 6 medium-coupling skills
7. Unit tests for filtering (escape hatch, missing field, markdown vs json)

**GO/NO-GO**: Lint reports zero mismatches? G1 WARN doesn't block existing dispatch? **Filtering reduces token without breaking skill output quality** (spot-check: run chapter-drafting with filtered vs unfiltered reads, compare scores — drop >2 points = filtering too aggressive, widen fields or fallback to full file)?

### Phase 4 — Regression + Documentation (2 days)

1. Full T1/T2 regression
2. Update AGENTS.md with decisions.json mechanism
3. Finalize docs/framework/decisions-schema.md
4. `just check` fully green

**Total: 11-14 days.**

---

## Cost Analysis

### One-Time Cost

| Work Item | Effort |
|-----------|--------|
| M1-M8 consistency modifications (M8 is new) | 2-3 days |
| Layer A: 7 skills frontmatter + body + G4 | 2-3 days |
| Layer B: 12 skills field-level reads + real filtering in dispatch_helper | 4-5 days (up from 3-4 — real filtering implementation + escape hatch) |
| Tests (unit + T2 integration + regression) | 2-3 days |
| Documentation + schema | 1 day |
| **Total** | **11-14 days** (up from 10-13 due to Layer B real filtering + M8) |

### Runtime Cost (Per Chapter)

| Cost Item | Before | After | Change |
|-----------|--------|-------|--------|
| context-composing LLM call | 1 | 1 + ~320 token JSON (P2.5 optimized) | +2-3% |
| chapter-drafting reads | ~8k token | +decisions.json ~270 token (P2.5 avg, slightly above P2) | +3% |
| 7 skills each produce decisions | 0 | 7 × ~270 token (P2.5 avg) | +1.9k token/chapter |
| Layer B filtering savings | 0 | -~2-4k token/chapter (filtered reads vs full files) | **saves** |
| G2/G4 decisions validation | 0 | 7 schema checks | +tens of ms, negligible |
| Gate failure re-run rate | baseline | est. -20-40% | **saves** |
| **Net runtime** | — | +1-3% token (down from +3-5% — Layer B filtering offsets decisions.json cost) | **near-neutral** |

**Honest assessment**: P2.5 adds slightly more token than P2 (~+20 token/decision for high-stakes rationale), but Layer B real filtering **saves** ~2-4k token/chapter by not sending full file contents. Net runtime cost is now near-neutral (1-3%), a meaningful improvement over the pre-filtering estimate (3-5%). Gate failure reduction is pure savings on top.

---

## Risk Register

| Risk | Layer | Severity | Mitigation | Residual |
|------|-------|----------|------------|----------|
| Decisions schema enum incomplete, skill decisions don't fit | A | Medium | `manual_override` fallback + review after 3 chapters | Low |
| **Downstream anchored by rationale** | A | **Medium** | P2.5: rationale only on manual_override + high-stakes; Phase 2 go/no-go checks score drop >2; fallback to P2/P1 | Low |
| G2 decisions branch misfires, blocks legitimate output | M4 | Medium | Unit test coverage + Phase 1 real-run validation | Low |
| **phase_runner hardcoded "chapter" not fixed (M8 missed)** | M8 | **High** | M8 fix: call `derive_file_type(skill)`; unit test asserts file_type propagation | Low (after M8) |
| truth-files.yaml two copies out of sync | M1+M2 | Low | Lint: docs/ vs site/ consistency check | Low |
| **Layer B filtering drops needed-but-undeclared fields** | B | **Medium** | Escape hatch: missing field → fallback to full file + WARN; G1 pre-check warns on field drift | Low |
| Field-level annotations drift from truth file evolution | B | Medium | CI lint scans actual headings vs declared fields | Low |
| 7 skills produce low-quality decisions | A | Medium | G4 schema validation + 5-chapter manual sampling | Medium |
| chapter-drafting decisions.json duplicates PRE_WRITE_CHECK | A | Medium | Open Q #4: investigate overlap before Phase 2; may narrow L-A.2 scope | Medium |
| Old round compatibility during migration | Global | Medium | decisions.json optional for old rounds, G4 soft-check period | Low |
| Clean-context regression (implicit state introduced) | Global | Low | Property test locks invariant | Low |

**Largest residual risk**: downstream anchoring. P2.5 compresses anchoring surface to ~90% (only manual_override + high-stakes routine decisions carry rationale), and Phase 2 go/no-go explicitly checks for score degradation. If anchoring persists despite P2.5, the fallback is P2 (cut severity escape hatch, rationale only on manual_override) or P1 (cut rationale entirely, keep only enum + selected/omitted).

---

## Best Practice Alignment Summary

| Best Practice (Anthropic/LangChain) | Alignment |
|-------------------------------------|-----------|
| Artifact + lightweight reference, minimize telephone | ✅ Layer A decisions.json is artifact, downstream reads as reference |
| Summary, not reasoning trace | ✅ Structured decision summary, not reasoning chain |
| Context filtering strategy (full/filtered/summary) | ✅ Layer B implements real filtering in `_build_skill_prompt` — LLM sees only declared fields, not full file (was: annotation-only, now: actual filtering) |
| Careful handoffs maintain continuity | ✅ decisions artifact carries intent across handoff |
| **Clean-context subagents** | **✅ Fully aligned** — all skills cross-model capable, zero memory inheritance |
| Treat context management as first-class | ✅ Context handoff elevated from implicit prompt to explicit contract |
| "Works particularly well for structured outputs" | ✅ Role-based grading applies decisions only where it adds value |
| "Irrelevant internal reasoning confuses receiver" | ✅ P2.5: rationale only on anomalies + high-stakes routine, low-stakes routine is rationale-free |

**All 8 best practices fully aligned.**

---

## Key Decisions Log

| Decision | Chosen | Rejected Alternatives | Rationale |
|----------|--------|----------------------|-----------|
| Atomic segments (Layer C) | **Deleted** | Keep as Layer C | Architecture already clean-context; same-model assumption is false premise |
| Layer A scope | **Role-graded (7 skills)** | All ephemeral only / all artifact skills | Anthropic "structured outputs" scoping justifies grading |
| decisions.json approach | **Sidecar artifact** | Frontmatter-embedded / centralized log | Sidecar = lightweight reference; others violate best practice |
| rationale inclusion | **P2.5: anomaly + high-stakes** | Always / never / structured / separate file / P2 (no severity) | P2.5 compresses anchoring to ~90% routine while preserving intent on anomalies AND high-stakes routine decisions (climax chapter selection etc.) |
| G1 fields check | **WARN non-blocking** | Hard FAIL | Truth files evolve; hard-block creates fragility |
| decisions file_type | **New "decisions" type** | Reuse chapter/truth | JSON needs different G2 validation (no word count) |
| phase_runner output discovery | **derive_output_files (root-cause fix)** | rglob expansion (patch) | Contract is single source of truth; no file-extension heuristics |
| phase_runner G2 file_type | **M8: call derive_file_type (NEW)** | Hardcoded "chapter" (current bug) | Without M8, M3+M4 are dead code on T2/T3 path |

---

## Open Questions (Deferred to Implementation)

1. **market-radar decisions content**: its decisions schema is less clear than context-composing (what does a "market analysis decision" look like?). Resolve during Phase 1 implementation — may need a market-radar-specific selections schema.
2. **short-drafting overlap with chapter-drafting**: short-drafting may share most decisions fields with chapter-drafting. Decide during Phase 2 whether to share schema or fork.
3. **chapter-revision reads chapter-drafting's decisions**: chapter-revision produces its own decisions.json (Layer A.5), but should its `reads` also include `chapters/chapter-N-decisions.json` from the prior drafting pass? Likely yes (revision needs to understand drafting intent to revise coherently), but the exact contract reads update is deferred to Phase 2 when implementing chapter-revision.
4. **chapter-drafting PRE_WRITE_CHECK overlap (raised in spec verification)**: `chapter-drafting` already embeds a `PRE_WRITE_CHECK` block as the first section of `chapters/chapter-N.md` (SKILL.md:64 — "PRE_WRITE_CHECK 必须作为章节文件的第一个区块输出"), recording "本章核心任务 / 要兑现的伏笔 / 本章禁忌 / 近3章结尾方式 / AI味重点防范". This partially overlaps with what Layer A's decisions.json would record for chapter-drafting. Before Phase 2 implementation, investigate: (a) does decisions.json duplicate PRE_WRITE_CHECK, or capture different intent (e.g., pacing deviations, foreshadowing placement rationale)? (b) should the 4 other NL-artifact skills (chapter-planning, chapter-revision, state-settling, short-drafting) also be checked for existing embedded-intent mechanisms before adding decisions.json? If overlap is high, consider narrowing L-A.2 scope to skills without existing intent-embedding, or making decisions.json conditional (only written when deviating from plan).
