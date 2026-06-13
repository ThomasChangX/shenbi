## Repository Guidelines

### Project Structure

```
shenbi/
├── skills/                  # 59 novel-writing AI skills (SKILL.md each)
├── tests/
│   ├── tiers/               # T1-skill, T2-phase, T3-pipeline test cases + rubrics
│   ├── fixtures/            # Isolated test inputs (real skill output, no hand-crafted mocks)
│   ├── rounds/              # Per-round output: novel-output/, skill-traces/, tN-reports/
│   ├── scoring.py           # Rubric-based 0–100 scorer
│   ├── validate-gate.py     # G0–G7 gate enforcement
│   ├── round-exec.sh        # Round creation + G0 validation
│   ├── phase-runner.py      # T2/T3 phase state machine
│   ├── summarize-round.py   # Round aggregation + G7 close validation
│   └── dispatch-subagent.sh # Subagent dispatch wrapper (G1→G2 gating)
├── docs/superpowers/        # Specs (specs/) and implementation plans (plans/)
├── outline-example.md       # Seed novel concept (星火燃穹)
├── CLAUDE.md / GEMINI.md    # Agent entry points
├── command-to-give.md       # Full execution protocol
└── goal-prompt.md           # Long-running goal definition
```

### Key Commands

- `bash tests/round-exec.sh <model> T1` — Create a new test round; runs G0 environment check.
- `python3 tests/validate-gate.py G0 <seed>` — Gate 0: seed exists, UTF-8, skill dirs present.
- `python3 tests/validate-gate.py G2 <files> <type>` — Gate 2: output file validation (UTF-8, word count, placeholders).
- `python3 tests/validate-gate.py G4 <skill> <files>` — Gate 4: skill-specific structural validation.
- `python3 tests/scoring.py <rubric> <scores.json> --test-type generative` — Score output against rubric; exit 0=success, 2=validation failure.
- `python3 tests/summarize-round.py <round_dir>` — Aggregate round scores; runs G7 close validation.
- `bash tests/round-exec.sh --validate <round_dir>` — Post-round integrity check.

### Skill Authoring

Every skill is `skills/<name>/SKILL.md` with YAML frontmatter:
- `name`: lowercase-kebab
- `description`: ONLY when-to-use trigger conditions, ≤500 chars. Never describes what the skill does.

Critical skills include DOT flowcharts for authoritative process definition and anti-rationalization tables. Use "your human partner" for the author, "truth files" for project state, "chapter memo" for the 8-section planning doc.

### Testing

Three-tier framework: **T1** per-skill (generative/bug-hunt/clean), **T2** phase chains, **T3** end-to-end pipelines. All scored 0–100 via `scoring.py` with `--test-type` dimension filtering.

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

Scripts under `tests/` use Python 3, `pathlib.Path` for file I/O, `json` for structured output. Gate functions return `passed()`/`fail()` helpers. Keep gate checkers idempotent—every function is a pure validation with no side effects on output files.
