# Cluster 07: Documentation & Configuration Drift

- Status: **accepted** (per parent [README.md](README.md), 2026-06-15)
- Date: 2026-06-15
- Parent: [README.md](README.md)
- Audit findings covered: F32–F34



## Problem Statement

After P-1 (claimed complete) and during P-1.E brainstorming, audit found
**4 categories of multi-agent entry files and project documentation in
various states of staleness**. New contributors (human or AI agents using
Codex, Cursor, Gemini, OpenCode, or Claude Code) reading these files get
wrong information about the project structure.

### Evidence

#### F32: Multi-agent entry files all stale

```
AGENTS.md         # last modified 2026-06-14 02:45 — pre P-1.E realization
CLAUDE.md         # unchanged; no mention of P-1 / pyproject / structlog / ADRs
GEMINI.md         # unchanged; describes 59 skills (58 actual shenbi- + 1 meta)
command-to-give.md # 6 references to novel-output/ (renamed target in P-1.D PR-15)
```

All four files describe the **pre-P-1 architecture**:

- No `pyproject.toml` mentioned (GEMINI.md, AGENTS.md treat Shenbi as
  shell-script-only)
- No `structlog` / typed exceptions / ADRs mentioned
- `novel-output/` referenced 6+ times (rename not propagated)
- `tests/` described as containing all framework code (true today, false
  after Cluster 02 PR-18)
- No mention of `uv` (GEMINI.md describes Gemini CLI tool mapping but
  not how to run Python commands)

#### F33: 4 plugin manifests with no single source of truth

```
.claude-plugin/plugin.json    # version 0.2.0
.codex-plugin/plugin.json     # version unknown
.cursor-plugin/plugin.json    # version unknown
.opencode/plugins/shenbi.js   # JavaScript, different format entirely
```

These must be hand-synced whenever:
- A skill is added, removed, or renamed
- Plugin metadata (version, author) changes
- Plugin capabilities evolve

**Already drifted**: `.claude-plugin/plugin.json` is version 0.2.0,
`pyproject.toml` is 0.1.0. Three of four plugin files have been touched
by separate commits.

#### F34: GEMINI.md / AGENTS.md skill count wrong

```
GEMINI.md: "All 59 skills are listed in `.claude-plugin/plugin.json`"
AGENTS.md: "├── skills/  # 59 novel-writing AI skills (SKILL.md each)"
```

Actual: 58 `shenbi-*` skills + 1 `using-shenbi` meta skill = 59 total.
But `using-shenbi` is structurally different (it's a meta-skill that
teaches agents how to use Shenbi), so the count "59" is misleading
without qualification.

## Root Cause Analysis

### Root cause 1: Documentation was exempt from PR acceptance criteria

P-1's PRs added code, config, and tests. No PR acceptance criterion
required updating `AGENTS.md` / `GEMINI.md` / etc. Documentation drifted.

**Fix**: Canonical PR-40 (Cluster 06) `PULL_REQUEST_TEMPLATE.md` requires:

> If this PR changes user-visible behavior or project structure, list
> which docs were updated (AGENTS.md, GEMINI.md, CLAUDE.md,
> command-to-give.md, README.md, mkdocs nav).

### Root cause 2: 4 plugin manifests with no generator

Each agent platform (Claude Code, Codex, Cursor, OpenCode) has its own
plugin manifest format. Currently all 4 are hand-maintained. Hand-syncing
always drifts.

Industry standard: **single source of truth + generator**. Example:
`tsup` for JS packages (generates package.json, exports, types).
`poetry-core` for Python (generates wheel from pyproject).

**Fix**: PR-45 creates `plugins/master.json` as single source and
`src/shenbi/plugins/generate.py` (entry point: `shenbi-generate-plugins`)
that emits all 4 platform manifests.

### Root cause 3: No "smoke test" for documentation accuracy

CI verifies Python code but not documentation. A doc can claim
`tests/validate-gate.py` exists forever without any test failing. There's
no doc-accuracy CI step.

**Fix**: PR-46 adds `tests/integration/test_docs_accuracy.py` that:
- Extracts file paths mentioned in markdown
- Verifies those files exist
- Fails CI if a doc references a missing file

This is partial — can't verify semantic accuracy, but catches the most
blatant drift.

## Target State

After P-1.E Cluster 07 completes:

| Item | Pre-P-1.E | Post-P-1.E |
|------|-----------|------------|
| AGENTS.md | stale (pre-P-1) | matches post-P-1.E reality |
| GEMINI.md | stale | matches post-P-1.E reality |
| CLAUDE.md | unchanged | updated to reference new structure |
| command-to-give.md | 6 `novel-output` refs | 0 refs (post-PR-22) |
| Plugin manifests | 4 hand-synced | 4 generated from `plugins/master.json` |
| Doc accuracy CI | none | `test_docs_accuracy.py` runs on every PR |
| Skill count claim | "59" ambiguous | "58 functional + 1 meta = 59 total" explicit |

## Components (PRs)

### PR-44: docs sync for AGENTS.md / GEMINI.md / CLAUDE.md / command-to-give.md

**Approach**: Update each file in lockstep. All 4 must reflect post-P-1.E
state (src layout, structlog, typed exceptions, ADRs, uv workflow, no
`novel-output/` references).

**Sections to update in `AGENTS.md`**:

```markdown
## Repository Guidelines

### Project Structure

```
shenbi/
├── src/shenbi/             # Framework runtime code (gates, dispatcher, scoring, ...)
├── tests/                  # Test code only (unit, integration, property, benchmark)
│   ├── rounds/             # Test rounds (active + archived)
│   ├── fixtures/           # Test fixtures (real skill output, no mocks)
│   └── baselines/          # Differential testing baselines
├── skills/                 # 58 functional skills + 1 meta (using-shenbi)
├── docs/                   # Documentation, ADRs, specs, plans
├── .github/workflows/      # CI: ci, security, docs, codeql, release
├── pyproject.toml          # PEP 621 metadata + tool config (uv, ruff, mypy, ...)
├── uv.lock                 # Locked dependencies with hashes
├── justfile                # Task runner entry points
├── CLAUDE.md / GEMINI.md / AGENTS.md  # Multi-agent entry points
├── command-to-give.md      # Full execution protocol
└── goal-prompt.md          # Long-running goal definition
```

### Key Commands

- `just check` — Run all CI checks locally (ruff, mypy, basedpyright, pytest).
- `just gate G0 <seed>` — Gate 0: seed exists, UTF-8, skill dirs present.
- `just gate G2 <files> <type>` — Gate 2: output file validation.
- `just gate G4 <skill> <files>` — Gate 4: skill-specific structural validation.
- `just dispatch <skill> <test_type> <round_dir> <prompt>` — Dispatch subagent.
- `uv sync --group dev` — Install dev dependencies.

Or directly via entry points (after `uv sync`):
- `shenbi-validate G0 <seed>` etc.
```

**Sections to update in `GEMINI.md`**:

- Update tool mapping table to mention `just` and entry points
- Add "P-1.E project layout" section mirroring AGENTS.md
- Update skill count claim to "58 functional + 1 meta"

**Sections to update in `CLAUDE.md`**:

- Add a brief note about P-1.E: "Project follows modern Python baseline
  (uv, ruff, mypy strict, structlog, typed exceptions). See
  `docs/superpowers/specs/2026-06-15-p-1.e-foundation-completion/README.md`."
- Reference `[project.scripts]` entry points
- Reference `justfile` as the canonical command entry

**Sections to update in `command-to-give.md`**:

- Replace all 6 `novel-output/` references with `skill-output/`
- Note: this is also done in PR-22 (rename). Either PR-22 lands first
  and updates command-to-give.md, or PR-44 lands first and updates
  command-to-give.md to the **future** path (anticipating PR-22).
- **Recommendation**: PR-22 lands first, then PR-44 polishes.

**Acceptance**:

- [ ] All 4 files updated in lockstep
- [ ] Zero `novel-output/` references (verified by grep)
- [ ] All 4 files mention: uv, src/shenbi/ layout, structlog, ADRs
- [ ] Skill count claim consistent across files
- [ ] No file path in any of the 4 docs points to a missing file (verified
      by `tests/integration/test_docs_accuracy.py` after PR-46)

### PR-45: multi-agent plugin manifest generator

**Approach**: Single source `plugins/master.json` + generator script.

**`plugins/master.json`** (NEW):

```json
{
  "name": "shenbi",
  "version": "0.2.0",
  "description": "AI skill framework for novel writing",
  "author": "ThomasChangX",
  "homepage": "https://github.com/ThomasChangX/shenbi",
  "license": "MIT",
  "skills": [
    "skills/using-shenbi/SKILL.md",
    "skills/shenbi-writing-skills/SKILL.md",
    "skills/shenbi-worldbuilding/SKILL.md",
    "... all 59 skills ..."
  ],
  "platforms": {
    "claude": {
      "output": ".claude-plugin/plugin.json",
      "format": "claude-code"
    },
    "codex": {
      "output": ".codex-plugin/plugin.json",
      "format": "codex-cli"
    },
    "cursor": {
      "output": ".cursor-plugin/plugin.json",
      "format": "cursor"
    },
    "opencode": {
      "output": ".opencode/plugins/shenbi.js",
      "format": "opencode-js"
    }
  }
}
```

**`src/shenbi/plugins/generate.py`** (NEW, also installed as
`shenbi-generate-plugins` entry point per Cluster 02 PR-18):

```python
"""Generate per-platform plugin manifests from master.json.

Single source of truth for plugin metadata and skill lists. Each platform
(Claude Code, Codex, Cursor, OpenCode) has its own manifest format; this
generator emits all of them from one input.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def load_master() -> dict:
    return json.loads((REPO_ROOT / "plugins" / "master.json").read_text())

def gen_claude(master: dict) -> dict:
    return {
        "name": master["name"],
        "version": master["version"],
        "description": master["description"],
        "author": master["author"],
        "skills": master["skills"],
    }

def gen_codex(master: dict) -> dict:
    # Codex format differs slightly
    return {
        "name": master["name"],
        "version": master["version"],
        "skills": master["skills"],
    }

def gen_cursor(master: dict) -> dict:
    # Cursor format
    ...

def gen_opencode(master: dict) -> str:
    # OpenCode uses JavaScript
    return f"""module.exports = {{
  name: "{master['name']}",
  version: "{master['version']}",
  skills: {json.dumps(master['skills'])}
}};
"""

def main() -> int:
    master = load_master()
    for platform, config in master["platforms"].items():
        if platform == "claude":
            output = gen_claude(master)
            path = REPO_ROOT / config["output"]
            path.write_text(json.dumps(output, indent=2) + "\n")
        elif platform == "codex":
            ...
        # etc.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**CI verification**:

```yaml
- name: Verify plugin manifests are up to date
  run: |
    uv run shenbi-generate-plugins
    git diff --exit-code .claude-plugin/ .codex-plugin/ .cursor-plugin/ .opencode/
```

**Acceptance**:

- [ ] `plugins/master.json` exists with all 59 skill paths
- [ ] `src/shenbi/plugins/generate.py` exists and runs cleanly
- [ ] `shenbi-generate-plugins` entry point works after `uv sync`
- [ ] All 4 platform manifests generated and identical content to current
      (modulo formatting normalization)
- [ ] CI workflow verifies manifests are up to date (fails if drift)
- [ ] `CONTRIBUTING.md` updated: "When adding/removing a skill, update
      `plugins/master.json` and run `shenbi-generate-plugins`."

### PR-46: doc accuracy CI

**Files created**: `tests/integration/test_docs_accuracy.py`

```python
"""Verify documentation accuracy.

Scans markdown files for code-span references to file paths (e.g.,
`tests/validate-gate.py`) and verifies those files exist. Catches the
most common doc drift: stale path references.

Not a substitute for semantic review — only catches missing-file drift.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DOCS_TO_CHECK = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "README.md",
    "CONTRIBUTING.md",
    "command-to-give.md",
]

CODESPAN_PATTERN = re.compile(r"`([^`]+\.\w+)`")

def extract_paths_from_doc(doc_path: Path) -> list[Path]:
    text = doc_path.read_text()
    paths = []
    for match in CODESPAN_PATTERN.finditer(text):
        candidate = match.group(1)
        if "/" in candidate or candidate.endswith((".py", ".md", ".yaml", ".yml", ".toml", ".json", ".sh")):
            paths.append(REPO_ROOT / candidate)
    return paths

def test_docs_reference_existing_files():
    missing = []
    for doc in DOCS_TO_CHECK:
        path = REPO_ROOT / doc
        if not path.exists():
            continue
        for referenced in extract_paths_from_doc(path):
            if not referenced.exists():
                missing.append(f"{doc}: references `{referenced.relative_to(REPO_ROOT)}` which does not exist")
    assert not missing, "Documentation references missing files:\n" + "\n".join(missing)
```

**Exclusions** (for known historical references):

```python
ALLOWED_MISSING = {
    # These may be referenced in historical/archival contexts
    "tests/rounds/round-000-TEMPLATE/...",
}
```

**Acceptance**:

- [ ] `tests/integration/test_docs_accuracy.py` exists
- [ ] Test passes on current main (after PR-44 lands)
- [ ] CI runs this test on every PR
- [ ] PR review checklist updated to reference this test

## Cross-cluster Dependencies

- **PR-44 depends on PR-22** (rename) and **PR-18** (src layout). Docs
  must reflect final paths.
- **PR-45 depends on PR-18** (entry points) — the generator is itself a
  `shenbi-generate-plugins` entry point.
- **PR-46 is independent** — but only meaningful after PR-44 lands.

## Risks

| Risk | Mitigation |
|------|------------|
| Generator output doesn't byte-match hand-written manifests | Format normalization (e.g., always 2-space indent, trailing newline) makes generated output canonical; future changes regenerate |
| Doc accuracy test false positives (e.g., referencing `dist/*.whl` in CI example) | Maintain `ALLOWED_MISSING` set with documented exceptions |
| Master.json schema evolves (new platforms added) | Use Pydantic models to validate master.json structure in generator |

## Open Questions → Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Should `master.json` also generate `mkdocs.yml` nav? | **No — hand-maintained.** | mkdocs nav has more nuance than just skill list (section headings, ordering, "Concepts" vs "Reference" split). Generator would need a nav schema as complex as the result. Reconsider at P0 when skills get restructured into domain groups. |
| 2 | Should `.opencode/` directory stay? | **Yes — keep.** | Per README master OQ resolution: OpenCode is growing; maintenance cost is one plugin file. Generator (PR-45) handles sync. |
| 3 | Doc accuracy test for internal links too? | **Yes — add `markdown-link-check` to PR-46.** | Catches broken doc-to-doc links (e.g., `CLAUDE.md` linking to deleted `docs/foo.md`). `markdown-link-check` is the standard tool. Run as separate test (`tests/integration/test_doc_links.py`) to keep concerns separated. |
