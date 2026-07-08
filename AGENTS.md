## Repository Guidelines

### Project Structure

```
shenbi/
├── src/shenbi/             # Framework runtime code
│   ├── exceptions.py       # Typed exception hierarchy
│   ├── logging.py          # structlog configuration
│   ├── scoring.py          # Rubric-based 0-100 scorer
│   ├── phase_runner.py     # T2/T3 phase state machine
│   ├── gates/              # G0-G7 gate enforcement
│   ├── dispatcher/         # Sub-agent dispatch
│   └── skill_utils/        # Skill Python helpers
├── tests/                  # Test code only (unit, integration, property, benchmark)
│   ├── rounds/             # Active + archived rounds
│   ├── fixtures/           # Real skill outputs (no mocks)
│   └── baselines/          # Differential testing baselines
├── skills/                 # 67 functional (shenbi-*) + 2 meta (using-shenbi, shenbi-writing-skills) = 69 total
├── docs/                   # Documentation, ADRs, specs, plans
├── .github/workflows/      # CI: ci, security, docs, codeql, release
├── pyproject.toml          # PEP 621 + tool config
├── uv.lock                 # Locked deps with hashes
├── justfile                # Task runner (just check, just test, etc.)
├── CLAUDE.md / GEMINI.md / AGENTS.md  # Multi-agent entry points
└── command-to-give.md      # Execution protocol
```

### Key Commands

Use entry points (not `python3 tests/X.py`):

- `just check` — Run all CI checks locally
- `just test` — Fast unit tests only
- `shenbi-validate G0 <seed>` — Gate 0: environment check
- `shenbi-validate G2 <files> <type>` — Gate 2: output validation
- `shenbi-validate G4 <skill> <files>` — Gate 4: skill-specific structural check
- `shenbi-score <rubric> <scores.json> --test-type generative` — Score output
- `shenbi-phase start <phase> --round-dir <dir>` — Phase state machine
- `shenbi-dispatch <skill> <test_type> <round_dir> <prompt>` — Sub-agent dispatch

Or via `just`:
- `just gate G0 outline-example.md`
- `just dispatch shenbi-worldbuilding generative /tmp/round "prompt"`
- `just pipeline-init <seed>` — Initialize novel pipeline from seed
- `just pipeline-status <dir>` — Check pipeline status
- `just pipeline-review <dir> <decision>` — Submit checkpoint review
- `just pipeline-resume <dir>` — Resume pipeline execution

Install: `uv sync --group dev` (PEP 735 dependency groups, not extras).

### Skill Authoring

Every skill is `skills/<name>/SKILL.md` with YAML frontmatter:
- `name`: lowercase-kebab
- `description`: ONLY when-to-use trigger conditions, ≤500 chars. Never describes what the skill does.

Critical skills include DOT flowcharts for authoritative process definition and anti-rationalization tables. Use "your human partner" for the author, "truth files" for project state, "chapter memo" for the 8-section planning doc.

### Decisions-Sidecar Artifacts

Skills that produce natural-language or ephemeral outputs also produce a
`*-decisions.json` sidecar artifact (Layer A). This carries structured
decision summaries (selections, adjustments, budget) that downstream skills
read as lightweight references.

Key rules:
- `kind: ephemeral` skills migrate to `kind: artifact` with decisions.json in writes
- Schema: `shenbi-decisions-v1` (see `docs/framework/decisions-schema.md`)
- P2.5 rationale rule: rationale FORBIDDEN on routine+low-severity, REQUIRED on manual_override + high-severity + adjustments
- G2 validates decisions.json as `file_type="decisions"` (skips word count)
- G4 validates schema + P2.5 rules
- Downstream skills declare decisions.json in their `reads:`

### Field-Level Reads

Skills can declare which fields of a truth file they consume via dict-form
reads (Layer B):

```yaml
contract:
  reads:
    - file: truth/current_state.md
      fields: [主角状态, 当前世界局势, 活跃线索]
```

The dispatcher filters file content to only declared fields before the LLM
sees it (LangChain "filtered portions" strategy). If a declared field is
missing from the file, the escape hatch returns the full file + logs WARN.

### Testing

Three-tier framework: **T1** per-skill (generative/bug-hunt/clean), **T2** phase chains, **T3** end-to-end pipelines. All scored 0–100 via `shenbi-score` with `--test-type` dimension filtering.

Thresholds: **≥94** for tier advancement, **≥90** for individual test pass, **100** as convergence target. Gates G0–G7 enforce quality at every stage—no gate can be skipped. Scoring MUST use an independent subagent (G3.4); dispatcher-scored results are invalid.

Fixtures under `tests/fixtures/` are exclusively real skill outputs or upstream-generated copies (G0.9 prohibits hand-crafted mocks). All test scenario inputs must reference `tests/fixtures/` paths.

### Commit Conventions

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
```
feat: add phase-runner.py state machine for T2/T3 execution
fix: resolve G6 marker filename mismatch
test: add integration tests for gate markers and G7 audit
docs: add T2/T3 protocol to command-to-give.md
chore: add round output patterns to .gitignore
```

### Python Conventions

Framework code under `src/shenbi/` uses Python 3.11+, `pathlib.Path` for file I/O, `json` for structured output. Gate functions return `passed()`/`fail()` helpers. Keep gate checkers idempotent—every function is a pure validation with no side effects on output files. No `print()` in framework code; use structlog.
