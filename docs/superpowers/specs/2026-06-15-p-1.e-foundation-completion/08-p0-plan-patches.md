# Cluster 08: P0 Plan Patches (Informational — Executed in P0 Spec)

- Status: **accepted** (per parent [README.md](README.md), 2026-06-15)
- Date: 2026-06-15
- Parent: [README.md](README.md)
- Audit findings covered: F35–F41
- **Execution context**: This cluster is NOT executed in P-1.E. It documents
  design defects in the original P0 brainstorming (session `8031a07e`) that
  must be patched into the P0 spec when it is written. P-1.E's role is to
  surface them; P0's role is to incorporate them.

## Problem Statement

The P0 brainstorming (session `8031a07e`, lines 922-1075) reached 8 settled
design decisions through extensive Q&A. Audit found **7 design defects**
that diverge from industry best practice. Each defect is documented below
with the brainstorming decision, the audit finding, and the corrected
design to be incorporated into the P0 spec.

### Defects summary

| ID | Decision | Defect | Patch |
|----|----------|--------|-------|
| F35 | Q3 graph.yaml = only place for relations | Confuses derived data with curated data | Patch-01 below |
| F36 | Q5 Pydantic as schema | Missing JSON Schema export step | Patch-02 |
| F37 | Q7 manifest + lockfile | Missing lockfile migration mechanism | Patch-03 |
| F38 | Q8 N=5 LLM consensus | Suboptimal vs. differential + reviewer pattern | Patch-04 |
| F39 | Approach 1 Foundation-First | Industry favors Spike-First for migrations | Patch-05 |
| F40 | (missing) | No observability story for AI framework | Patch-06 |
| F41 | (missing) | `[project.scripts]` deferred indefinitely | Patch-07 |

---

## Patch-01: graph.yaml role clarification (Q3 fix)

### Original brainstorming decision (line 949-967 of session 8031a07e)

> meta.yaml only carries per-skill unchanging attributes + own role tag.
> Cross-skill relationships maintained in independent `tests/tiers/graph.yaml`.
> graph.yaml is the **唯一关系源** (only source of relationships).

### Defect

The decision treats **all** cross-skill data as "relationships" and routes
them through graph.yaml. But there are two distinct kinds of cross-skill
data:

1. **Derived data**: Skill A's `reads: [world/story_bible.md]` implies
   "A depends on whatever skill writes story_bible.md". This is derivable
   from per-skill meta.yaml.
2. **Curated data**: "Skill A belongs to phase 'genesis' and pipeline
   'long-form'". This is editorial categorization, not derivable.

**Putting derived data in graph.yaml means it lives in two places**
(meta.yaml's `reads`/`writes`, AND graph.yaml's `edges`), which guarantees
drift.

### Industry standard

npm `package.json` `dependencies`, Cargo `Cargo.toml` `[dependencies]`,
Python `pyproject.toml` `dependencies`: all follow **单向声明 + 派生反向索引**
(unidirectional declaration + derived reverse index). The dependent declares;
the dependency doesn't. Tools (`cargo tree`, `pipdeptree`) derive the
reverse index on demand.

### Patched design

**Two distinct data layers**:

```yaml
# 1. Per-skill meta.yaml (source of truth for skill identity + IO contract)
name: shenbi-character-design
reads:
  - {path: world/story_bible.md}
  - {path: novel.json}
writes:
  - {path: characters/protagonist.md, schema: schemas/protagonist.py}
  - {path: characters/major_characters.md, schema: schemas/major_characters.py}
```

```yaml
# 2. tests/tiers/graph.yaml (curated editorial data ONLY)
# No dependency edges here — those are derived from per-skill reads/writes.
vertical_slice:
  skills:
    - shenbi-worldbuilding
    - shenbi-character-design
    - shenbi-story-architecture
    # ...
  chapter_target: 3

phases:                                  # phase membership is curated
  genesis:
    - shenbi-genre-config
    - shenbi-worldbuilding
  architecture:
    - shenbi-story-architecture
    - shenbi-power-system
  planning:
    - shenbi-chapter-planning
    - shenbi-foreshadowing-plant
  # ...

pipelines:                               # pipeline membership is curated
  long-form:
    phases: [genesis, architecture, planning, drafting, audit, foundation, management]
  short-form:
    phases: [genesis, architecture, planning, drafting, packaging]
```

**`build_registry.py` derives the dependency graph**:

```python
def derive_dependencies(skills: dict[str, SkillMetadata]) -> DependencyGraph:
    """Build dependency graph from per-skill reads/writes declarations.

    For each file path, find the skill that writes it. Any skill that reads
    that path depends on the writer.
    """
    file_writers = build_file_writer_index(skills)
    edges = []
    for skill_name, meta in skills.items():
        for read in meta.reads:
            writer = file_writers.get(read.path)
            if writer and writer != skill_name:
                edges.append((skill_name, writer, "depends_on"))
    return DependencyGraph(edges=edges)
```

**Result**: `registry.lock.json` contains both the curated graph.yaml
data AND the derived dependency edges. Downstream consumers don't care
which is which.

### P0 spec must say

> meta.yaml holds per-skill IO contract. graph.yaml holds phase/pipeline
> membership. Dependencies are **derived** from reads/writes by
> `build_registry.py`. Never declared in two places.

---

## Patch-02: Pydantic → JSON Schema export (Q5 fix)

### Original brainstorming decision (line 978-994)

> Each output file uses a Pydantic model. Pydantic is the AI ecosystem
> fact standard (OpenAI Function Calling, LangChain, DSPy, Anthropic,
> FastAPI, Hugging Face).

### Defect

Pydantic models are only consumable by Python. Non-Python consumers
(Cursor, Codex, Gemini, future Rust dispatcher, future TypeScript types,
any agent SDK in another language) cannot import Python modules.

For an AI framework explicitly designed for multi-agent use (Claude Code,
Codex CLI, Gemini CLI, Cursor, OpenCode — at least 4 non-Python
consumers), **Pydantic alone is insufficient**.

### Industry standard

OpenAI's structured output API accepts JSON Schema. Anthropic's tool use
API accepts JSON Schema. JSON Schema is the lingua franca of cross-language
data contracts. Pydantic v2's `model.model_json_schema()` produces
standards-compliant JSON Schema (Draft 2020-12).

### Patched design

**Two-layer schema**:

```
skills/<name>/
└── schemas/
    ├── protagonist.py              # Pydantic model (Python source)
    └── generated/
        └── protagonist.schema.json # JSON Schema (generated, git-tracked)
```

**`build_registry.py` step**: For every Pydantic model in
`skills/<name>/schemas/*.py`, generate
`skills/<name>/schemas/generated/<ModelName>.schema.json`.

```python
def export_json_schemas(skills: dict[str, SkillMetadata]) -> None:
    for skill_name, meta in skills.items():
        for write in meta.writes:
            if not write.schema:
                continue
            pydantic_module = import_pydantic_module(write.schema)  # e.g., "schemas/protagonist.py"
            for model_class in iter_pydantic_models(pydantic_module):
                schema = model_class.model_json_schema()
                output_path = (
                    SKILLS_DIR / skill_name / "schemas" / "generated"
                    / f"{model_class.__name__}.schema.json"
                )
                output_path.write_text(json.dumps(schema, indent=2) + "\n")
```

**Consumers**:
- Python tools: import Pydantic models directly.
- Non-Python tools: read `generated/*.schema.json`.
- IDE plugins: read JSON Schema for autocomplete in skill output files.

### P0 spec must say

> Every Pydantic schema has a corresponding JSON Schema export. The export
> is generated by `build_registry.py` and committed. Non-Python consumers
> MUST consume the JSON Schema, not the Pydantic source.

---

## Patch-03: lockfile migration mechanism (Q7 fix)

### Original brainstorming decision (line 1003-1016)

> Manifest + Lockfile mode. `registry.lock.json` contains
> `source_hashes`, `aggregated snapshot`. Git-tracked.

### Defect

The lockfile has `schema_version: "2026.1"` but no mechanism for:
- When to bump schema_version
- How to migrate old lockfiles to new schema_version
- How downstream consumers detect stale lockfiles

Cargo has `Cargo.lock` `version = 3` with documented migrations.
npm has `lockfileVersion` with changelog. Terraform has state mv commands.
**Shenbi has nothing**.

### Industry standard

Three components:

1. **Versioned schema** with explicit `schema_version` field.
2. **Migration functions**: `migrate_v1_to_v2(lockfile) → lockfile_v2`.
3. **Auto-upgrade on read**: `load_registry.py` detects old schema_version,
   migrates in-place, writes back, logs warning.

### Patched design

```python
# src/shenbi/registry/migrations.py

SCHEMA_VERSION = "2026.2"  # current

MIGRATIONS = {
    # from_version → migration_function
    "2026.1": migrate_v1_to_v2,
    "2026.2": None,  # current, no migration needed
}

def load_lockfile(path: Path) -> Lockfile:
    raw = json.loads(path.read_text())
    version = raw.get("schema_version", "2026.1")
    while version != SCHEMA_VERSION:
        migrator = MIGRATIONS.get(version)
        if not migrator:
            raise RegistryCorruptError(
                f"No migration from schema_version {version}"
            )
        raw = migrator(raw)
        version = raw["schema_version"]
        log.warning("registry_lockfile_migrated",
                    from_version=version, to_version=raw["schema_version"])
    # Write back if migrated
    if raw["schema_version"] != original_version:
        path.write_text(json.dumps(raw, indent=2) + "\n")
    return Lockfile(**raw)
```

**Versioning rules**:
- Patch version bump (2026.1 → 2026.1.1): backward-compatible (renames,
  documentation). Old code reads new lockfile fine.
- Minor version bump (2026.1 → 2026.2): additive (new optional fields).
  Old code reads new lockfile but ignores new fields; new code reads old
  lockfile via migration.
- Major version bump (2026 → 2027): breaking. Migration function required.

### P0 spec must say

> `registry.lock.json` is versioned. `load_registry.py` auto-migrates
> old lockfiles. Major version bumps require explicit migration function
> in `src/shenbi/registry/migrations.py`. Consumers MUST support at least
> one prior schema version via auto-migration.

---

## Patch-04: N=5 LLM consensus → N=2 + differential + property (Q8 fix)

### Original brainstorming decision (line 1024-1042)

> N=5 LLM consensus mechanism. Five independent LLM instances generate
> the schema; supermajority (4/5) or unanimity required. This is
> N-version programming, NASA standard for high-reliability firmware.

### Defect

N-version LLM programming was popularized by Microsoft AutoGen (2023).
**2024-2025 research** showed N-version LLM has lower ROI than
alternatives:

1. **LLMs share failure modes**. All 5 instances may make the same
   mistake (e.g., misread a skill's contract). N-version assumes
   independent failures, which LLMs violate.
2. **Cost scales linearly**. N=5 costs 5× a single generation, but
   reliability gain is sub-linear.
3. **Property-based testing catches more bugs**. Hypothesis with
   1000 iterations explores more edge cases than 5 LLM guesses.

### Industry standard (2025)

**Generator + Reviewer + Property testing** (the "RAG + Critic" pattern):

1. **Generator** (1 LLM call): produces schema candidate.
2. **Reviewer** (1 LLM call, different model): critiques the candidate.
   If reviewer approves, accept. If reviewer rejects, generator revises
   (max 3 iterations).
3. **Property-based testing** (Hypothesis, 1000 iterations): generates
   random instances of the schema and verifies round-trip
   serialization/deserialization, constraint satisfaction, etc.
4. **Mutation testing** (10+ mutations per schema): manually construct
   schema-violating instances and verify the schema rejects them.
5. **Static analysis on generated code**: ruff + mypy strict on the
   Pydantic model itself (catches the model definition being malformed).

Total LLM calls: 2-4 (vs 5 for N-version). Reliability: equivalent or
better. Cost: 40-60% lower.

### Patched design

Replace "N=5 consensus" with "Generator + Reviewer + Property + Mutation":

```python
def migrate_skill_schema(skill_name: str, generator: AgentFn, reviewer: AgentFn) -> MigrationResult:
    """Migrate one skill's schema with generator+reviewer+testing pattern."""
    # 1. Generate candidate
    candidate = generator(skill_name)

    # 2. Review (max 3 iterations)
    for iteration in range(3):
        review = reviewer(candidate, skill_name)
        if review.approved:
            break
        candidate = generator(skill_name, feedback=review.feedback)
    else:
        return MigrationResult(status="review_failed", candidate=candidate)

    # 3. Property-based testing (1000 iterations)
    property_results = run_property_tests(candidate)
    if not property_results.all_passed:
        return MigrationResult(status="property_failed",
                               candidate=candidate,
                               failures=property_results.failures)

    # 4. Mutation testing
    mutation_results = run_mutation_tests(candidate)
    if mutation_results.survival_rate > 0.1:  # > 10% mutations survive
        return MigrationResult(status="mutation_failed",
                               candidate=candidate,
                               results=mutation_results)

    # 5. Static analysis
    static_results = run_static_analysis(candidate)  # ruff + mypy
    if static_results.errors:
        return MigrationResult(status="static_failed",
                               candidate=candidate,
                               errors=static_results)

    return MigrationResult(status="accepted", candidate=candidate)
```

**Reviewer agent** must use a different model family from generator (e.g.,
generator=Sonnet, reviewer=GPT-4o) to reduce shared-failure-mode risk.

### P0 spec must say

> Migration tooling uses Generator+Reviewer+Property+Mutation+Static
> pattern. Generator and Reviewer use different model families. Total
> LLM calls per skill: 2-4. N-version consensus (N≥3) is NOT used.

---

## Patch-05: Foundation-First → Spike-First (Approach fix)

### Original brainstorming decision (line 1042-1057)

> Approach 1: Foundation-First. Write all infrastructure first, then
> migrate. Each step has clear deliverable.

### Defect

Foundation-First has a known failure mode for migration projects: the
infrastructure is built without real consumer feedback, leading to over-
or under-engineering. **Industry consensus** (Cargo, npm, Babel, Webpack,
all major migrations) favors Spike-First or Parallel Tracks.

### Industry standard

**Spike-First migration**:

1. Pick 3 representative skills (one foundation, one drafting, one review).
2. Migrate them MANUALLY (no tools, just hand-craft meta.yaml + schemas).
3. Extract patterns and edge cases from the manual migration.
4. Build tools based on real needs (codemod, validators, etc.).
5. Use tools to migrate remaining 55 skills.

This avoids the "generalizing from theory" trap. The Shenbi audit already
showed a similar failure mode: `voice_profile` field was discovered to
cause skill bloat during brainstorming, which would have been caught
earlier with a spike.

### Patched design

```
Phase 1: Spike (3 skills manually migrated, 1-2 weeks)
  - shenbi-worldbuilding (foundation skill, complex IO contract)
  - shenbi-chapter-drafting (drafting skill, prose-heavy output)
  - shenbi-review-character (review skill, scoring-heavy)
  Output: 3 reference migrations + spike report documenting patterns

Phase 2: Tooling (based on spike findings, 1-2 weeks)
  - Pydantic base classes
  - build_registry.py + load_registry.py
  - validate_skill.py + validate_registry.py
  - migrate_skill.py codemod (informed by spike manual migrations)
  - LLM generator+reviewer tools (Patch-04)
  Output: tool suite with 100% spike-skill coverage

Phase 3: Batch migration (remaining 55 skills, 1-2 weeks)
  - Run codemod + LLM tools on each skill
  - Per-skill review + iteration (max 5 attempts)
  Output: all 58 shenbi-* skills migrated

Phase 4: Validation (1 week)
  - Property-based testing across all skills
  - Mutation testing across all skills
  - Human review sample (10%)
  Output: validation report
```

**Spike skill selection criteria**:
- Covers different IO contract shapes (JSON, prose-md, truth-md)
- Covers different skill categories (foundation, drafting, review)
- Covers different complexity (high IO + schema, low IO + schema)
- Has historical run data (already tested in some round) — for sanity check

### P0 spec must say

> P0 follows Spike-First approach. Phase 1 migrates 3 skills manually
> before any tooling is written. Tooling design in Phase 2 is informed
> by Phase 1 findings. Foundation-First is explicitly rejected.

---

## Patch-06: Observability story (new section)

### Original brainstorming decision

**No observability discussion.** Brainstorming covered schemas, registry,
scenarios, defects, migration — but never how to observe the framework
running.

### Defect

For an AI framework where:
- Skills execute via LLM calls (non-deterministic, slow, expensive)
- Migration tooling uses LLM calls (Patch-04)
- Tests run sub-agent dispatches
- Round execution takes hours

...observability is essential. Without it, debugging "why did this skill
fail?" requires re-running the skill, hoping for the same outcome.

### Industry standard

**OpenTelemetry** (OTLP) is the 2024+ standard for observability.
**Phoenix** (Arize), **LangSmith** (LangChain), **Helicone** are
AI-specific observability backends. All support OpenTelemetry export.

A framework that doesn't emit OTLP-compatible traces is invisible to
modern observability stacks.

### Patched design

**Define metrics schema, don't implement collector** (P3 scope):

```python
# src/shenbi/observability/metrics.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class SkillExecutionMetric:
    """OTLP-compatible metric for a single skill execution."""
    skill_name: str
    test_type: Literal["generative", "bug-hunt", "clean"]
    round_id: str
    duration_ms: int
    token_count: int | None         # None if not reported
    score: int                       # 0-100
    status: Literal["pass", "fail", "rejected", "error"]
    error_class: str | None          # if status == "error"

@dataclass
class SchemaValidationMetric:
    """OTLP-compatible metric for a schema validation."""
    schema_name: str
    instance_path: str
    valid: bool
    error_count: int
    duration_ms: int

@dataclass
class MigrationMetric:
    """OTLP-compatible metric for a single skill migration attempt."""
    skill_name: str
    iteration: int
    generator_model: str
    reviewer_model: str
    status: Literal["accepted", "review_failed", "property_failed",
                    "mutation_failed", "static_failed"]
    duration_ms: int
```

**Emitters**: structlog can emit these as JSON log lines. P3 work adds
OTLP exporter for direct collector integration.

**Trace context**: every skill execution starts a new trace span.
Sub-skills (chapter drafting during chapter planning) nest under parent
spans. W3C TraceContext headers propagate through sub-agent dispatch.

### P0 spec must say

> P0 defines metrics schema (`src/shenbi/observability/metrics.py`) and
> emits metrics via structlog. OTLP collector integration is P3 scope.
> Every skill execution creates a trace span; trace context propagates
> through sub-agent dispatch via W3C TraceContext headers.

---

## Patch-07: `[project.scripts]` entry points (new section)

### Original brainstorming decision

P-1.E defers `[project.scripts]` (see Cluster 02 root cause 2). P0
brainstorming didn't address this either.

### Defect

P0 introduces `build_registry.py`, `load_registry.py`,
`validate_registry.py`, `validate_skill.py`, `migrate_skill.py` — 5 new
tools. Without entry points, users invoke them as
`python tests/build_registry.py ...` (or `python src/shenbi/registry/build.py ...`
post Cluster 02). Not discoverable, not installable, not scriptable.

### Patched design

P-1.E PR-18 adds entry points for existing tools. P0 adds new entry
points for its tools:

```toml
[project.scripts]
# From P-1.E
shenbi-validate = "shenbi.gates.cli:main"
shenbi-dispatch = "shenbi.dispatcher.cli:main"
shenbi-score = "shenbi.scoring:main"
shenbi-summarize = "shenbi.summarize_round:main"
shenbi-progress = "shenbi.update_progress:main"
shenbi-phase = "shenbi.phase_runner:main"
shenbi-generate-plugins = "shenbi.plugins.generate:main"

# From P0
shenbi-build-registry = "shenbi.registry.build:main"
shenbi-load-registry = "shenbi.registry.load:main"
shenbi-validate-registry = "shenbi.registry.validate:main"
shenbi-validate-skill = "shenbi.skills.validate:main"
shenbi-migrate-skill = "shenbi.skills.migrate:main"
```

**Discoverability**: `just gate G0 <seed>` becomes the user-facing alias.
Entry points enable `just` to call them consistently.

### P0 spec must say

> All P0 tools (`shenbi-build-registry`, `shenbi-load-registry`,
> `shenbi-validate-registry`, `shenbi-validate-skill`,
> `shenbi-migrate-skill`) are installed as `[project.scripts]` entry
> points. Users invoke via `just` (e.g., `just build-registry`) or
> directly (`shenbi-build-registry`).

---

## Summary: What the P0 spec must incorporate

When the P0 spec is written (after P-1.E completes), it must include:

1. **Q3 restated**: meta.yaml has IO contract; graph.yaml has phase/pipeline
   membership only; dependencies derived by `build_registry.py`.
2. **Q5 supplemented**: every Pydantic schema has JSON Schema export.
3. **Q7 supplemented**: lockfile has versioning + migration mechanism.
4. **Q8 replaced**: Generator + Reviewer + Property + Mutation + Static,
   not N=5 consensus.
5. **Approach changed**: Spike-First, not Foundation-First.
6. **New section: Observability**: metrics schema defined; trace context
   propagated; collector integration deferred to P3.
7. **New section: Entry points**: all P0 tools installed as
   `[project.scripts]`.

## Cross-cluster Dependencies

This cluster has no P-1.E PRs. It's purely informational. The 7 patches
are referenced from the P0 spec when it's written.

## Risks

| Risk | Mitigation |
|------|------------|
| P0 spec writer ignores this cluster | P0 brainstorming skill requires reading `08-p0-plan-patches.md` before starting spec |
| Industry best practice shifts again before P0 starts | Spec author re-verifies each patch against current industry state at P0 spec time |
| Spike-First discovers skills are even more divergent than expected | Spike report informs Phase 2 tooling scope; budget contingency in P0 plan |

## Open Questions → Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Generator + Reviewer same vendor (Anthropic) or cross-vendor (Anthropic + OpenAI)? | **Cross-vendor.** | Per Cluster 08 Patch-04: "Generator and Reviewer use different model families to reduce shared-failure-mode risk." Same-vendor models share training data biases and failure modes. Cross-vendor maximizes independence. P0 spec time picks the specific pair based on benchmark results. |
| 2 | Include LLM cost in observability metrics? | **Yes — `cost_usd` field in `SkillExecutionMetric`.** | Cost tracking is essential for any LLM-heavy framework. Without it, runaway skill execution (e.g., infinite retry loop) is invisible until invoice arrives. Pydantic field with 2 decimal precision; populated from provider's pricing API. |
| 3 | Lockfile migration: auto-write or explicit invocation? | **Auto-write with `log.warning` for minor/patch bumps; explicit `shenbi-migrate-lockfile --major` invocation required for major bumps.** | Minor/patch migrations are non-destructive (additive); auto-write reduces friction. Major bumps may delete/rename fields; explicit invocation forces operator awareness. Two-tier policy matches Cargo/npm/terraform conventions. |
