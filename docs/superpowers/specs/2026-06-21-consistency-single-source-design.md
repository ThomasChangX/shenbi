# Shenbi Consistency: Single Source of Truth — Design

- Status: **accepted, rev 2** (2026-06-21; post-review fixes applied — see §11 changelog)
- Date: 2026-06-21
- Deciders: ThomasChangX (sole maintainer)
- Supersedes: nothing; addresses audit findings A–D (see §1.3)

## TL;DR

A consistency audit on 2026-06-21 found that Shenbi's framework frontmatter and
section taxonomy are clean, but the **machine-consumed I/O contract has drifted**:
the `数据契约` (Data Contract) block lives in Markdown prose, is parsed by regex in
**two duplicated** modules (`executor.py`, `phase_runner.py`), and accepts three
incompatible value shapes (path / prose / glob) that the parser silently collapses —
and, for review skills, the contracts are **incomplete**, hiding the real persisted
output behind the prose `"report only"`. There is no canonical truth-file registry,
`deps.json`'s `expected_outputs` hand-duplicates the skill contracts and drifts, and
three different concepts all overload the key `"status"`.

This spec makes the contract the **single source of truth**, expressed as a
**schema-validated structured block in skill frontmatter**, with `expected_outputs`,
the truth-file registry, and the skill→file dependency DAG **generated** from it. The
hard constraint — *multi-fact-source is non-negotiable* — drives every decision.

The mandate this spec is graded against is **prevention, not detection**: the
design must make each inconsistency class **structurally impossible to land**, not
merely "currently absent." §4 maps every audit finding to the mechanism that makes
its recurrence impossible (or, for free-form prose terminology, honestly states
the ceiling is *detected-at-CI*, with the reason).

## 1. Problem

### 1.1 Hard constraints (non-negotiable)

- **C-HARD-1 — Single source of truth.** No dependency/contract fact may exist in
  more than one editable location. Anything derivable must be **generated**, and
  generated artifacts must be **uneditable-by-construction** (CI rejects hand-edits).
- **C-HARD-2 — Prevention over detection.** For every inconsistency class the spec
  fixes, it must also make the *recurrence* impossible (unexpressible in the
  schema) or auto-rejected at the cheapest possible checkpoint. "Lint catches it"
  is acceptable **only** where the inconsistent form is free-form prose (see §4.2).
- **Objective function.** Maximize **system output quality** and minimize
  **maintenance cost**. **Development/migration cost is explicitly out of scope**
  for choosing between structurally-valid options — root-cause correctness wins.

### 1.2 What is already consistent (out of scope — do not touch)

- **Frontmatter**: every skill is `name: shenbi-*` + `description: Use when ...` (59/59).
- **Section taxonomy core**: `流程` / `铁律` / `数据契约` / `Anti-Rationalization`
  present in all 57 novel-writing skills (`using-shenbi`, `shenbi-writing-skills`
  are meta-skills, legitimately exempt).
- **Gate output envelope**: `{gate, status, timestamp, checks, ...}` produced only
  through `shared.py` `passed()`/`fail()`/`unimplemented()` — uniform.

### 1.3 Audit findings (A–D)

**Layer A — Output-format section header (surface, presentation-only).** 52/57 use
`## 输出格式`; 7 generative skills deviate (chapter-drafting, chapter-revision,
character-design, intent-management, story-architecture, worldbuilding → 0;
foundation-review → 2); worldbuilding uniquely uses `输出契约`; plus ad-hoc
`### Key Results`, `输出`, `输出文件`. **Note:** `输出格式` is human-facing only —
nothing machine-parses it (the machine contract is `数据契约`), so its drift has
~zero impact on system output quality; the fix is presentational hygiene.

**Layer B — Terminology (surface, prose).** `hook ledger` (4×) vs `hook pool` (2×)
— same concept, two names (`hook pool` confined to `shenbi-review-foreshadowing`,
which itself also uses `hook ledger`); `truth files` (23×) vs `truth-files` (1×);
`your human partner` (3×) vs `the author` (1×).

**Layer C — Contract value semantics + report-skill incompleteness (root cause).**
The `数据契约` `Reads`/`Writes`/`Updates` block is parsed by regex
(`src/shenbi/dispatcher/executor.py:51-75`, `src/shenbi/phase_runner.py:111-122`)
but its values take **three incompatible shapes** the parser cannot distinguish:
1. backtick path (`truth/pending_hooks.md`) — intended, machine-resolvable;
2. **prose** — ~17 review skills write `report only`; others write Chinese summary
   phrases (`种植汇总`, `传导汇总`, `市场分析报告`) → parsed to an **empty file list**;
3. **glob** (`characters/major/*.md`, `chapters/*.md`) → passed as literal strings.

The prose form is not merely ambiguous — it masks **incomplete contracts**. Review
skills declare `Writes: report only`, but their reports are **persisted** as
`audits/chapter-N-<dim>.md` files and consumed downstream. Verified:
`tests/tiers/deps.json:107-124` lists 18 `audits/chapter-*-<dim>.md` as expected
outputs; `src/shenbi/gates/g3.py:116` classifies `audits/` paths as report-type
outputs; `shenbi-drift-guidance`'s scenario consumes `audits/` files as input.
So `"report only"` is a **wrong/incomplete contract** omitting the real output path —
the actual root cause, not just an ambiguous value shape. (Corollary test gap:
`tests/fixtures/audits/` is currently empty though drift-guidance reads from it.)

**Layer D — Structural / framework (root cause).**
- **D1 — No canonical truth-file registry.** Paths accrete across skills; no
  single authority names them (synonym risk: unprefixed `era-reference.md` vs the
  `world/*.md` convention; glob-vs-explicit variants).
- **D2 — Duplicated parser.** `executor.py` `derive_input_files`/`derive_output_files`
  and `phase_runner.py` `cmd_pre_skill` independently regex-parse the same
  `**Reads:**`/`**Writes:**`/`**Updates:**` format. Edit one, not the other → silent divergence.
- **D3 — Fragmented status vocabulary.** Three concepts overload `"status"`:
  gate result (`PASS/FAIL/SKIP/WARN`), phase state-machine
  (`created/started/skills_done/scored/finalized` + `ok/blocked/error` + `UNKNOWN`),
  and score classification (`PASS (excellent)`/`PASS (acceptable)`/`CONDITIONAL`/`FAIL`
  + `REJECT`/`MARKER_MISSING`/`UNIMPLEMENTED`). Because results are emitted as
  `json.dumps(...)` strings, type checkers cannot catch a typo like `"PASSED"`
  unless emit sites use typed enum members and typed result structures.
- **D4 — Duplicated output inventory in deps.json.** `tests/tiers/deps.json` is the
  legitimate curated source for phase/pipeline *organization* (`t2-phases[].prerequisites`
  is phase **membership**, `t3-pipelines[].prerequisites` is pipeline **ordering**,
  plus `g4_checker` and `_out_of_pipeline` — none duplicate contract facts). But its
  **`expected_outputs`** field hand-duplicates each skill's `writes` already declared
  in the contract — the real drift surface (consumed by `phase_runner.py`, `scoring.py`).
  The producer/consumer file dependencies are not captured anywhere today.

## 2. Goals & Non-Goals

**Goals**
- G1. One editable location for each skill's I/O contract; everything else derived.
- G2. Every inconsistency class in §1.3 is either impossible to land or
  auto-rejected at commit/runtime — see §4.2 honesty table.
- G3. Contract correctness propagates to gate correctness → output quality (§5.4).
- G4. A contributor changing a skill's I/O edits exactly one thing
  (frontmatter) and runs `just generate`; nothing else is hand-synced.

**Non-Goals**
- N1. Not redesigning the skill taxonomy, gate semantics, or scoring rubric.
- N2. Not migrating skill *behavioral* prose (流程/铁律/Anti-Rationalization).
- N3. Not building a UI/DAG-visualizer now (the DAG is generated as data; a viewer
  is a future capability, see §9).

## 3. Design: Frontmatter Single Source of Truth

### 3.1 Architecture

```
                     ┌─────────────────────────────────────────────┐
   EDITABLE (1)      │  skills/<s>/SKILL.md  frontmatter            │
   single source     │   name, description, contract{...}           │
                     └────────────────────┬────────────────────────┘
                                          │  contract.load_contract (schema-validated)
                     ┌────────────────────┼──────────────────────────────┐
                     ▼                    ▼                              ▼
   GENERATED      contract.py         just generate              body render
   (uneditable       loader        ┌──────┴────────┐       (auto `## 数据契约`
   by construction;                 ▼     ▼         ▼        block, re-derived)
   CI rejects edits)     deps.json   registry  DAG
                         expected_   index     (skill→file producer/
                         outputs     (paths    consumer graph — NEW
                         (gen); org  usage)    artifact, not in
                         fields cur.)          deps.json today)
                     └── runtime: gates / dispatcher / phase_runner / scoring
                         all import contract.py + status.py (single definitions)
```

**Editable surface = exactly one thing per skill**: the frontmatter `contract`.
deps.json's **organizational** fields (membership/ordering/checker) are also a
legitimate curated source (they are not contract facts); only its `expected_outputs`
becomes generated. Everything below the line that *is* derivable is a generated
artifact; hand-editing any of it fails CI (idempotency check, §5.5).

### 3.2 The contract schema (formal)

Contract data moves **into frontmatter** (currently frontmatter carries only
`name`/`description`). Canonical shape, validated by a TypedDict + runtime checker:

```python
# src/shenbi/contract.py
class OutputKind(StrEnum):
    ARTIFACT  = "artifact"   # writes a durable project file → G2 file-validation (chapter/truth type)
    REPORT    = "report"     # emits a report; if persisted, the path is in writes → G2 validates as report-type
    EPHEMERAL = "ephemeral"  # transient guidance, no persisted artifact → output gates skip

class Contract(TypedDict):
    kind: OutputKind
    reads: list[str]    # canonical paths / registered patterns only; MUST resolve in registry
    writes: list[str]
    updates: list[str]  # files mutated in place (subset semantics: also an artifact write)
```

Skill frontmatter becomes:

```yaml
---
name: shenbi-chapter-drafting
description: Use when writing chapter content, generating chapter text, or drafting a new chapter after planning is complete
contract:
  kind: artifact
  reads:
    - plans/chapter-N-plan.md
    - style/style_profile.md
    - genre-config.json
    - truth/audit_drift.md
  writes:
    - chapters/chapter-N.md
  updates: []
---
```

A report skill (e.g. `shenbi-review-anti-ai`) — the report is **persisted** and
consumed downstream, so the path is declared (this is the fix for Layer C's
incomplete-contract bug):

```yaml
contract:
  kind: report
  reads:
    - chapters/chapter-N.md
    - genre-config.json
  writes:
    - audits/chapter-N-anti-ai.md   # persisted report (was hidden behind "report only")
  updates: []
```

`kind` selects the **output-validation strategy**, not whether `writes` is
populated. `REPORT` skills whose output is consumed downstream (per the DAG) MUST
declare the persisted path in `writes` (validated by G2 as report-type; `g3.py`
already routes `audits/` to report-type validation). A genuinely transient report
uses `writes: []`. An `ephemeral` skill has empty `writes`/`updates` and skips
output gates. **A downstream consumer (per DAG) of a report whose producer declares
no persisted path is a CI failure** — the contract-completeness rule that kills the
`"report only"` drift at the root.

**The three incompatible value shapes (Layer C) are eliminated by the schema itself**:
`writes` is a typed `list[str]`; `report only` is not a list → rejected at load.
Globs are not free strings either (see §5.3 patterns).

### 3.3 The body-prose ban (closes the human-restatement loophole)

Single-source is broken the moment a contributor re-describes reads/writes in the
SKILL.md body. Therefore:
- The old hand-written `## 数据契约` block is **removed** from the body.
- An **auto-generated** view **is** rendered into the body (confirmed OD-1), so the
  agent/human still sees I/O at a glance — produced by `just generate`, under a
  banner `<!-- AUTO-GENERATED from frontmatter — do not edit -->`. The generator's
  idempotency check (§5.5) guarantees it always equals frontmatter.
- A lint (§5.5) **rejects** any SKILL.md whose body contains hand-written
  `**Reads:**` / `**Writes:**` / `**Updates:**` or a non-auto-generated contract
  block. This is what makes a second source *unlandable*.

## 4. The Prevention Model (root-cause; the spec's grading criterion)

### 4.1 Principle

> Make the inconsistent form **unexpressible** (the schema cannot hold it) or
> **auto-rejected at the cheapest checkpoint** (load for authors, pre-commit/CI for
> the repo, runtime for consumers). "Detected by a linter" is the floor, not the
> goal — used only where the form is free-form prose and thus cannot be typed.

Mechanisms are layered so each inconsistency is blocked at the earliest, lowest-cost point:

| Layer | What runs | Blocks |
|---|---|---|
| **Write time** (author's machine) | frontmatter schema + registry resolution + contract-completeness on load | untyped/prose/glob values; unregistered paths; missing persisted report writes |
| **Commit time** (pre-commit + CI) | lints: body-ban, loader-uniqueness, generator-idempotency, registry, schema, status-typing, completeness | body restatement; re-implemented parsers; hand-edited generated artifacts; synonym files; bare status strings |
| **Runtime** (gates/dispatcher/scoring) | single `contract.py` loader + typed `status.py` enums + typed result structures | parsing divergence; status typos / cross-domain mixing |

### 4.2 Honesty table — what reaches "impossible" vs "detected"

| Audit class | Recurrence outcome | How |
|---|---|---|
| C (prose/glob/path ambiguity + incomplete report contracts) | **IMPOSSIBLE to land** | frontmatter schema: `reads/writes/updates` are typed path-lists; `OutputKind` enum; loader rejects non-path. Completeness rule: a report consumed downstream (per DAG) with no declared persisted path → `ContractError`. |
| C/body duplication | **IMPOSSIBLE to land** | body-prose ban + generator idempotency (§3.3, §5.5). |
| D2 (parser duplication) | **IMPOSSIBLE to land (going forward)** | single `contract.py`; loader-uniqueness lint rejects any module that reads the frontmatter `contract:` key outside `contract.py` (§5.5). |
| D4 (`expected_outputs` duplicates contracts) | **IMPOSSIBLE to land** | `expected_outputs` is **generated** from member writes (parametric→glob, §5.4) with a completeness validation (orphan entries fail); idempotency CI rejects hand-edits. |
| D3 (status overload) | **IMPOSSIBLE to land** | typed `StrEnum` per domain in `status.py`; **typed result structures** (`GateResult` etc., §5.2) + lint forbidding bare status string-literals outside `status.py`; enforced by **both** mypy and basedpyright (basedpyright is the pre-commit gate). |
| D1/A (file-name synonyms; section-header drift) | **DETECTED at CI** (near-impossible) | registry: every frontmatter path must resolve to a canonical name or registered pattern; introducing a new name requires a one-line registry edit → **visible in PR**. Section headers lint-flagged. |
| B (prose terminology) | **DETECTED at CI** | glossary + banned-synonym lint. **Honest ceiling:** free-form prose cannot be made *impossible* to hold a synonym; the achievable guarantee is *known* drift is rejected at CI and *new* drift is caught the moment it's added to the banned list. |

§4.2's two "detected" rows are the **explicit ceiling**, stated because C-HARD-2
demands honesty about which classes cannot be made structurally impossible and why.
Both are "detected at the cheapest checkpoint (CI/PR)", not silently tolerated.

## 5. Components

### 5.1 `src/shenbi/contract.py` — the single loader (fixes D2)

- One function `load_contract(skill: str) -> Contract` reading frontmatter via the
  existing `shared.yload`, then validating against the `Contract` schema and the
  registry (§5.3) and the completeness rule (§3.2).
- **Deletes** the regex parsing in `executor.py` (`derive_input_files`/`derive_output_files`)
  and `phase_runner.py` (`cmd_pre_skill` inline parse); both import `load_contract`.
- On any malformed/incomplete contract: raise a typed `ContractError` (loud), never
  silently return an empty list (that was the original bug).

### 5.2 `src/shenbi/status.py` — typed status vocabulary + typed results (fixes D3)

Defines and exports the canonical enums; all emit sites use them **via members, never
bare strings**, and emit through **typed result structures** so the enum is enforced:

```python
class GateStatus(StrEnum):    PASS, FAIL, SKIP, WARN
class PhaseState(StrEnum):    CREATED, STARTED, SKILLS_DONE, SCORED, FINALIZED
class CommandStatus(StrEnum): OK, BLOCKED, ERROR
class ScoringStatus(StrEnum): OK, REJECT, MARKER_MISSING, UNIMPLEMENTED
class ScoreClassification(StrEnum): PASS_EXCELLENT, PASS_ACCEPTABLE, CONDITIONAL, FAIL

class GateResult(TypedDict):
    gate: str
    status: GateStatus
    timestamp: str
    checks: list[dict[str, Any]]
    # blocked_action / must_fix present only on FAIL — modeled via total=False supplements
```

`shared.py`'s `passed()`/`fail()` build `GateResult` from enum members. The `UNKNOWN`
fallback in `phase_runner.py:155` becomes a proper `CommandStatus` member or an
explicit error path. Because the result dicts are typed with the enum, `"status":
"PASSED"` is a type error (not merely a runtime risk) under both checkers.

### 5.3 The canonical file registry (fixes D1)

A curated **definition source** of the project's file vocabulary — *not* a duplicate
of per-skill facts (it is "schema", frontmatter is "data"):

- `docs/framework/truth-files.yaml` — the authoritative list of canonical file
  concepts (e.g. `truth/pending_hooks.md`, `world/story_bible.md`, `audits/chapter-N-<dim>.md`,
  `genre-config.json`) plus **parametric patterns** (`chapters/chapter-N.md`,
  `characters/major/*.md`) and **declared globs** (`truth/*.md`). One concept = one
  canonical name → synonyms impossible by construction.
- Every `reads/writes/updates` entry must resolve to a registry concept, parametric
  pattern, or declared glob. An unresolved path → `ContractError` at load + CI.
  **Each parametric pattern declares its glob equivalent** (e.g. `chapters/chapter-N.md`
  → `chapters/chapter-*.md`), so the generator's parametric→glob normalization
  (§5.4) is a **lookup, not inference** — no ambiguity.
- Adding a genuinely new file = **one edit** to this registry; that single edit is
  the PR-visible decision point that prevents silent synonym creation.

### 5.4 The generator (`just generate` / entry point `shenbi-sync-contracts`)

Reads every skill's frontmatter contract **via `contract.load_contract(skill)` per
skill — it does not parse frontmatter independently** (this keeps loader-uniqueness,
§5.5 #4, intact — no third parser) — and **derives**:
- `tests/tiers/deps.json` **`expected_outputs` — fully generated** from each phase's
  member skills' declared `writes`/`updates`:
  - **parametric→glob normalization** — a registered parametric pattern
    (`chapters/chapter-N.md`) → glob (`chapters/chapter-*.md`); declared globs
    (`truth/*.md`) pass through; concrete paths stay concrete.
  - **generator round-trip self-check** — every member skill `write`/`update` is
    emitted as an expected_output and every emitted entry traces to a member write
    (bijection within the phase). This catches generator bugs and any future curated
    leak; it is a correctness check on the generator, not drift, since expected_outputs
    is fully derived.
  - (deps.json's organizational fields — membership, t3 ordering, `g4_checker`,
    `_out_of_pipeline` — stay curated; only `expected_outputs` was the contract
    duplicate. Per OD-2: **keep** deps.json, generate `expected_outputs` in place.)
- `docs/framework/dependency-dag.json` — the **NEW** skill→file producer/consumer
  graph (skill B `reads` file X that skill A `writes` ⇒ A→B). Not in deps.json today;
  enables impact analysis, dead-input and cycle detection, and drives the
  contract-completeness rule (a report consumed with no persisted producer write fails).
- `docs/framework/truth-files.index.json` — generated usage index (which skills
  read/write each file).
- the **auto-generated body `## 数据契约` view** (§3.3, OD-1).

**Output-quality linkage (G3):** because the contract is now correct and validated,
G1 (inputs exist) / G2 (outputs well-formed) / G4 (generative check) operate on the
*right* file sets; `context-composing` assembles the *complete* truth-file context.
Correct contract → correct gates → higher-fidelity output and fewer false PASS/FAIL.

### 5.5 The lints (pre-commit + CI)

1. **contract-schema** — frontmatter `contract` validates against `Contract`; `kind`
   ∈ enum; lists are path-strings resolving in the registry. Applies to the **57
   in-pipeline skills**; the 2 meta skills (`using-shenbi`, `shenbi-writing-skills`)
   are exempt (not in any phase/DAG — see `deps.json` `_out_of_pipeline`).
2. **contract-completeness** — a `REPORT` skill whose output is consumed downstream
   (per DAG) declares a persisted `writes` path (kills the `"report only"` drift).
3. **body-ban** — **scoped to `skills/*/SKILL.md` only** (excludes
   `tests/rounds/archived/**`, which legitimately retain legacy `**Reads:**` blocks);
   rejects hand-written contract blocks or a non-auto-generated `## 数据契约`.
4. **loader-uniqueness** — **only `contract.py` may read the frontmatter `contract:`
   key**; scan for `yload`/`contract`-key access outside `contract.py` and reject.
   (Anchored to the *new* frontmatter format, not the legacy `**Reads:**` regex.)
5. **generator-idempotency** — `just generate` produces zero diff vs. committed
   `deps.json` `expected_outputs` / registry index / DAG / body renders
   (`git diff --exit-code`). Hand-edits to generated artifacts are rejected.
6. **status-typing** — result structures typed (`GateResult` etc.); **no bare status
   string-literals outside `status.py`**; enforced by **both** mypy and basedpyright
   (basedpyright is the pre-commit gate).
7. **terminology/section-header** — glossary banned-synonym check (`hook pool`,
   `truth-files`, `the author`) + canonical section-header set
   (`流程`/`铁律`/数据契约`(auto)`/`Anti-Rationalization`/`输出格式`).

## 6. Audit → Solution mapping

| Finding | Root-cause fix | Prevention mechanism (§4.2) |
|---|---|---|
| A — section-header drift (presentation-only) | normalize the ~7 deviants to `输出格式`; lint the canonical set | CI lint (detected); low impact noted |
| B — terminology | canonical: `hook ledger` (matches existing `truth/particle_ledger.md`); normalize `hook pool`→`hook ledger` (review-foreshadowing); also `truth-files`→`truth files` and `the author`→`your human partner` | glossary + banned-synonym lint (detected — prose ceiling) |
| C — value-shape ambiguity + incomplete report contracts | frontmatter `Contract` schema + `OutputKind` enum + **completeness rule** (report consumed downstream ⇒ persisted `writes`) | schema + completeness: unexpressible (impossible) |
| D1 — no registry | `truth-files.yaml` + resolution | registry: unresolved path rejected (impossible); synonym → PR-visible (detected) |
| D2 — duplicated parser | single `contract.py` | loader-uniqueness lint on the frontmatter `contract:` key (impossible going forward) |
| D3 — status overload | `status.py` enums + typed `GateResult` etc. + bare-string lint | typed enums/structs + mypy **and** basedpyright (impossible) |
| D4 — `expected_outputs` duplicates contracts | **generate** `expected_outputs` from member writes (parametric→glob) + completeness validation | idempotency CI + orphan-validation (impossible) |

## 7. Migration

1. **Registry first.** Author `docs/framework/truth-files.yaml` from the paths
   observed in current contracts + `deps.json` expected_outputs (the audit's
   extracted set). Decide canonical names for the synonym cases.
2. **Migrator script (one-time).** `tools/migrate_contract_to_frontmatter.py`
   parses each skill's existing body `## 数据契约` block → emits frontmatter
   `contract:`. Classification rules:
   - review skills → `kind: report, writes: [audits/chapter-N-<dim>.md]` (verified
     intent: deps.json expects it, `g3.py` routes `audits/` to report-type,
     drift-guidance consumes it);
   - other prose `writes` (`种植汇总`, `传导汇总`, …) → `kind: report`/`ephemeral`
     with the persisted path if one exists, else `writes: []`;
   - globs map to registered patterns; each skill's `kind` classified by inspection.
3. **Rewire consumers.** `executor.py`, `phase_runner.py` → `contract.load_contract`.
   Introduce `status.py` + typed result structures. Generate `expected_outputs` in
   deps.json from member writes (delete the hand-written copy).
4. **Rewrite contract-format unit tests.** `tests/unit/test_dispatcher_executor.py`
   (tests the deleted `derive_input_files`/`derive_output_files`) and
   `tests/unit/test_phase_runner.py:275-322` (hardcode the `**Reads:**`/`**Writes:**`
   body format) encode the old contract shape; rewrite them against
   `contract.load_contract` + frontmatter fixtures.
5. **Remove body blocks.** Strip hand-written `## 数据契约`; render auto-generated view.
6. **Fix the test-input gap.** Populate `tests/fixtures/audits/` so `shenbi-drift-guidance`
   tests have the inputs its scenario references (currently empty).
7. **Rollout.** Skill-family by skill-family (worldbuilding/outline → characters →
   foreshadowing → chapter pipeline → reviews), each behind the new lints green.
   Migration tooling + a frozen snapshot of pre-migration contracts guard against
   silent semantic change (diff the parsed contract pre/post).

## 8. Testing (business-value encoded)

Each test asserts a *behavior*, and the prevention tests assert the inconsistent
form is **rejected** (encoding "inconsistency is impossible"):

- `contract/loader`: valid contract parses; missing/malformed → `ContractError`
  (value: "a skill without a valid contract cannot load").
- `contract/schema`: `writes: report only` (prose) → rejected; invalid `kind` →
  rejected; non-list → rejected (value: "ambiguous value shapes cannot exist").
- `contract/completeness`: a `REPORT` skill consumed downstream (per DAG) with
  `writes: []` → `ContractError` (value: "a report needed by a later skill cannot be
  silently ephemeral — the `report only` bug is impossible").
- `contract/registry`: unresolved path → `ContractError`; parametric pattern + glob
  resolve (value: "unregistered files cannot enter the system silently").
- `generator/expected_outputs`: regenerated `expected_outputs` equals committed
  (idempotency); an orphan expected_output (no producer) → fail; parametric→glob
  normalization correct (value: "hand-edits and missing producers are caught").
- `generator/dag`: producer/consumer edges correct; dead-input + cycle detection
  fire (value: "missing producers and cycles surface").
- `lint/loader-uniqueness`: reading the frontmatter `contract:` key in a module
  other than `contract.py` → lint fails (value: "single loader is enforced").
- `status`: each domain enum exhaustive; cross-domain assignment is a type error;
  bare `"PASS"` literal outside `status.py` → lint/type error (value: "status typos
  cannot land").
- `lint/body-ban`: a hand-written body contract block in `skills/` → rejected;
  archived fixtures under `tests/rounds/archived/**` are not flagged (value: "the
  body cannot become a second source; legacy fixtures are exempt").

## 9. Out of scope / future

- **DAG viewer** — the generated `dependency-dag.json` enables a UI / impact-analysis
  CLI; deferred (N3).
- **Report schemas** — for `kind: report` skills, an optional `report_schema` field
  could define the report's internal shape for stronger validation; deferred until a
  report skill needs it (YAGNI now).
- **Sidecar contract (Approach 3)** — explicitly rejected for single-source
  reasons (two files); frontmatter supersedes it.

## 10. Resolved decisions

- **OD-1 (auto-rendered body block) — RESOLVED 2026-06-21: yes.** Render the
  auto-generated `## 数据契约` view into the body (idempotency-protected).
- **OD-2 (deps.json: keep vs split) — RESOLVED 2026-06-21: keep.** deps.json stays
  the curated organizational source; `expected_outputs` is generated in place. No
  `phases.yaml` split (it would add a file without eliminating any drift surface).
- **OD-3 (canonical foreshadowing term) — RESOLVED 2026-06-21: `hook ledger`.**
  Chosen for semantic fit (stateful append-log), consistency with the existing
  `truth/particle_ledger.md` convention, and file-name alignment
  (`pending_hooks.md`). Normalize the 2 `hook pool` instances in
  `shenbi-review-foreshadowing`; record in the glossary.

## 11. Changelog (rev 2 — post-review fixes)

- **[Critical] C↔D4 co-design.** Resolved the contradiction where the C-fix
  (`report only`→`writes: []`) made the D4-fix (`expected_outputs` from `writes`)
  produce empty audit output. Verified review reports ARE persisted
  (`deps.json:107-124`, `g3.py:116`, drift-guidance consumes `audits/`): review
  contracts now declare `writes: [audits/chapter-N-<dim>.md]` + a completeness rule.
- **[Important] `expected_outputs` fully generated** via parametric→glob
  normalization + completeness validation (orphan entries fail). No curated
  existential-glob category needed (every current entry traces to a producer once
  contracts are complete).
- **[Important] D3 enforcement specified** — typed `GateResult`/etc. result
  structures + bare-status-string lint; both mypy **and** basedpyright named
  (basedpyright = pre-commit gate).
- **[Important] D2 lint reframed** to guard the *frontmatter `contract:` key*
  (was anchored to the legacy `**Reads:**` regex, useless post-migration).
- **[Important] Test migration added** (§7.4) — `test_dispatcher_executor.py` +
  `test_phase_runner.py:275-322` rewritten; empty `tests/fixtures/audits/` populated.
- **[Minor]** A flagged presentation-only (low impact); B enumerates `truth-files` +
  `the author` stragglers; body-ban lint scoped to `skills/` (excludes archived rounds).
