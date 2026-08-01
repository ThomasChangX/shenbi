# Cluster 06: Enterprise Baseline Files & Engineering Polish

- Status: **accepted** (per parent [README.md](README.md), 2026-06-15)
- Date: 2026-06-15
- Parent: [README.md](README.md)
- Audit findings covered: F26–F31



## Problem Statement

The repository lacks standard enterprise/open-source project hygiene files
and several modern Python engineering conveniences. Audit found 6 categories
of missing or incomplete items.

### Evidence

#### F26: Missing standard project files

```
✗ LICENSE                   # pyproject.toml declares MIT but no file
✗ SECURITY.md               # no vulnerability disclosure policy
✗ CONTRIBUTING.md           # no contributor guide
✗ CODEOWNERS                # no code ownership rules
✗ CHANGELOG.md              # no release notes
✗ CODE_OF_CONDUCT.md        # no community standards
✗ .github/PULL_REQUEST_TEMPLATE.md
✗ .github/ISSUE_TEMPLATE/   # no issue templates
✗ .github/CODEOWNERS
✗ .github/SECURITY.md       # GitHub security policy pointer
```

`pyproject.toml:6` declares `license = { text = "MIT" }` — SPDX notation
implies the license text exists somewhere. Without a LICENSE file, this is
non-binding under most legal interpretations.

#### F27: No task runner

Every CI job, every dev command, every documentation example uses a different
verbose uv invocation:

```bash
# CI
uv run pytest -n auto -m "not last" --hypothesis-profile=ci

# Dev (current docs say)
uv run pytest tests/unit/test_scoring.py -v

# Local sanity check
uv run ruff check . && uv run mypy src/shenbi/ && uv run pytest
```

No `justfile`, no `mise.toml`, no `Makefile`. Commands drift between
contexts.

#### F28: PEP 735 dependency groups not adopted

`pyproject.toml:17-36` uses `[project.optional-dependencies]` (PEP 508
extras):

```toml
[project.optional-dependencies]
dev = [...]
docs = [...]
```

Issues with extras:
- They're included in wheel metadata. Anyone who installs `shenbi[dev]`
  from PyPI gets test deps in their environment.
- They pollute the package's dependency graph for downstream consumers.
- uv 0.5+ (2024) supports PEP 735 `[dependency-groups]` which are
  dev-only and never enter wheel metadata.

#### F29: `mkdocs.yml` minimal

```yaml
site_name: Shenbi
theme:
  name: material
plugins:
  - search
  - mkdocstrings
```

No `nav`, no `awesome-pages` plugin, no versioning, no social cards, no
i18n. For a 59-skill framework, navigation is essential. Currently the docs
site is unusable.

#### F30: SBOM generated but not stored

`.github/workflows/security.yml:14-19`:

```yaml
- run: uv run cyclonedx-py environment -o sbom.cdx.json
- uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.cdx.json
```

Generated as artifact (deleted after 90 days), not attached to releases.
`.gitignore:59` excludes `sbom.cdx.json` from git. **SBOM is ephemeral.**

#### F31: Hypothesis failure cases not committed

Already covered in Cluster 04 PR-33.

## Root Cause Analysis

### Root cause 1: Project was prototype-grade, not production-grade

Original Shenbi was a personal project. LICENSE/SECURITY/CONTRIBUTING were
deferred until "the project matures". P-1 was supposed to bring it to
enterprise baseline but the scope was deferred (Cluster 01).

**Fix**: PR-40 adds all standard files in one PR. None optional.

### Root cause 2: Modern Python tooling adoption lagged

PEP 735 was accepted 2024-07. `just` has been popular since 2020. mkdocs
Material has had nav since 2018. None of these were adopted because P-1.B
was scoped to "minimal viable tooling".

**Fix**: PR-41 (PEP 735), PR-42 (justfile), PR-43 (mkdocs nav).

### Root cause 3: SBOM treated as CI check, not as deliverable

The security workflow generates SBOM as a CI artifact, signaling "we
generated it" but not preserving it. **Industry practice** (SLSA Level 3):
SBOM is a release artifact, attached to every published version.

**Fix**: PR-39 (Cluster 05) attaches SBOM to GitHub releases.

## Target State

After P-1.E Cluster 06 completes:

```
shenbi/
├── LICENSE                            # NEW
├── SECURITY.md                        # NEW
├── CONTRIBUTING.md                    # NEW
├── CODE_OF_CONDUCT.md                 # NEW (Contributor Covenant 2.1)
├── CHANGELOG.md                       # NEW
├── README.md                          # UPDATED
├── justfile                           # NEW: task runner
├── pyproject.toml                     # UPDATED: PEP 735 groups
├── mkdocs.yml                         # UPDATED: nav, plugins
├── .github/
│   ├── CODEOWNERS                     # NEW
│   ├── SECURITY.md                    # NEW (pointer to /SECURITY.md)
│   ├── PULL_REQUEST_TEMPLATE.md       # NEW
│   └── ISSUE_TEMPLATE/
│       ├── bug.md                     # NEW
│       ├── feature.md                 # NEW
│       ├── skill-proposal.md          # NEW
│       └── config.yml                 # NEW (contact links)
└── docs/
    └── ...
```

## Components (PRs)

### PR-40: enterprise baseline files

**Files created**:

#### `LICENSE` (MIT)

```
MIT License

Copyright (c) 2026 ThomasChangX

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

#### `SECURITY.md`

```markdown
# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest main | ✅ |
| < 1.0 | ❌ (pre-release) |

## Reporting a Vulnerability

Email: <security email or GitHub Security Advisory>

Please **do not** open a public GitHub issue for security vulnerabilities.
Use GitHub's "Report a vulnerability" feature under the Security tab, or
email directly.

**Response time**: 72 hours for initial response, 14 days for fix or
disclosure timeline agreement.

## Disclosure

We follow coordinated disclosure. Once a fix is available, we publish a
GitHub Security Advisory with CVE assignment (if applicable).

## Supply Chain

- All dependencies locked in `uv.lock` with hashes
- SBOM (CycloneDX format) generated per release and attached to GitHub Releases
- pip-audit runs on every PR and weekly
- CodeQL static analysis runs on every PR and weekly
```

#### `CONTRIBUTING.md`

Sections: development environment setup, code style, PR process, CI checks,
testing guidelines, ADR process, the no-deferral rule (see Cluster 01 root
cause 2).

#### `CODE_OF_CONDUCT.md`

Contributor Covenant 2.1 (standard).

#### `CHANGELOG.md`

```markdown
# Changelog

All notable changes to Shenbi are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- P-1.E Foundation Completion: enterprise baseline files, src layout migration,
  structural fixes (see `docs/superpowers/specs/2026-06-15-p-1.e-foundation-completion/`)

## [0.2.0] - 2026-06-14

### Added
- P-1 Foundation Hygiene: uv, ruff, mypy, basedpyright, pytest, structlog,
  typed exceptions, ADRs (partial — see P-1.E for completion)

## [0.1.0] - 2026-05-XX

### Added
- Initial Shenbi framework with 59 skills
- 7-gate validation system (G0-G7)
- Three-tier testing (T1/T2/T3)
```

#### `.github/CODEOWNERS`

```
# Default owner
*                       @ThomasChangX

# Framework code
src/shenbi/             @ThomasChangX
tests/                  @ThomasChangX

# Documentation
docs/                   @ThomasChangX

# Skills (per-domain ownership can be added as project grows)
skills/                 @ThomasChangX
```

#### `.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## Summary

<!-- One sentence describing what this PR changes -->

## Type of change

- [ ] bug fix
- [ ] new feature
- [ ] refactor
- [ ] documentation
- [ ] test
- [ ] build/CI

## Checklist

- [ ] This PR fulfills all stated goals (no work deferred without linked issue)
- [ ] No new `print()` in `src/shenbi/` framework code
- [ ] No new `ignore_errors` or `exclude` in tooling config
- [ ] No `P-1.E`-style deferral comments added
- [ ] Tests added/updated; `pytest` passes locally
- [ ] `ruff check`, `mypy`, `basedpyright` all pass
- [ ] CHANGELOG.md updated (or N/A: <reason>)
- [ ] ADR added/updated for any architectural decision

## Test plan

<!-- How did you verify this works? -->

## Linked issues

<!-- "Closes #N" or "Refs #N" -->
```

#### `.github/ISSUE_TEMPLATE/`

3 templates: `bug.md`, `feature.md`, `skill-proposal.md`. Plus `config.yml`
with contact links.

**Acceptance**:

- [ ] All 8 enterprise files present at repo root or `.github/`
- [ ] LICENSE matches `pyproject.toml` declaration
- [ ] First-time contributor experience tested (clone → read CONTRIBUTING.md → set up dev env)
- [ ] GitHub UI recognizes templates (PR template auto-fills, issue template picker works)

### PR-41: PEP 735 dependency groups

**`pyproject.toml` changes**:

```toml
[project]
dependencies = [
    "pydantic>=2.5.0",
    "pyyaml>=6.0.1",
    "structlog>=24.1.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    # ... all current dev deps
]
docs = [
    "mkdocs>=1.5.3",
    "mkdocs-material>=9.5.4",
    "mkdocstrings[python]>=0.24.0",
]
```

Remove `[project.optional-dependencies]`. Update CI to use
`uv sync --group dev` instead of `uv sync --extra dev`.

**Acceptance**:

- [ ] No `[project.optional-dependencies]` in `pyproject.toml`
- [ ] `[dependency-groups]` section present
- [ ] `uv sync --group dev` works
- [ ] CI uses `--group dev` and `--group docs`
- [ ] Built wheel (`uv build --wheel`) doesn't include dev deps in metadata
      (verify via `unzip -p dist/*.whl '*/METADATA' | grep Requires-Dist`)

### PR-42: task runner (justfile)

**Files created**: `justfile`

```makefile
# Run from project root
set dotenv-load := true
set positional-arguments := true

# Default: show available recipes
default:
    @just --list

# Install dependencies (dev group by default)
install group="dev":
    uv sync --group {{group}}

# Run all checks (ruff + mypy + basedpyright + tests)
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src/shenbi/
    uv run basedpyright
    uv run pytest -n auto -m "not last" --hypothesis-profile=ci
    uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci

# Run tests only (fast unit tests)
test *args:
    uv run pytest -n auto -m "unit" {{args}}

# Run tests including integration
test-all *args:
    uv run pytest -n auto -m "not last" {{args}}

# Run a single test file
test-file file:
    uv run pytest {{file}} -v

# Fix lint and formatting
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Run gates CLI (e.g., just gate G0 <seed>)
gate name *args:
    uv run shenbi-validate {{name}} {{args}}

# Dispatch a skill
dispatch skill test_type round_dir *prompt:
    uv run shenbi-dispatch {{skill}} {{test_type}} {{round_dir}} {{prompt}}

# Build docs site
docs:
    uv run mkdocs serve

# Build wheel and sdist
build:
    uv build

# Clean all build artifacts
clean:
    rm -rf dist/ build/ src/shenbi.egg-info/
    rm -rf tests/coverage/
    rm -rf .pytest_cache .ruff_cache .mypy_cache .basedpyright_cache

# Pre-commit run on all files
precommit:
    uv run pre-commit run --all-files

# Migration testing (mutmut)
mutate:
    uv run mutmut run --use-cache

# Compare mutation score to baseline
mutate-check:
    uv run python tools/compare_mutation_score.py --baseline tests/baselines/mutation-score.txt
```

**Acceptance**:

- [ ] `justfile` exists at project root
- [ ] `just` is mentioned in `CONTRIBUTING.md` as the primary command entry point
- [ ] `just check` runs all CI checks locally
- [ ] `just test <filename>` works for individual test files

### PR-43: mkdocs navigation + plugins

**`mkdocs.yml` (new content)**:

```yaml
site_name: Shenbi
site_description: Novel-writing AI skill framework
repo_url: https://github.com/ThomasChangX/shenbi
repo_name: ThomasChangX/shenbi
edit_uri: edit/main/docs/

theme:
  name: material
  language: zh
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.indexes
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.code.annotate
    - content.tabs.link
  palette:
    - scheme: default
      primary: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode

plugins:
  - search:
      lang:
        - zh
        - en
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true
            show_signature_annotations: true
            separate_signature: true
            show_category_heading: true
            heading_level: 2
            docstring_style: google
  - awesome-pages

nav:
  - Home: index.md
  - Getting Started:
      - Installation: getting-started/installation.md
      - First novel: getting-started/first-novel.md
      - Concepts: getting-started/concepts.md
  - Skills:
      - Index: skills/index.md
      - Foundation: skills/foundation.md
      - Architecture: skills/architecture.md
      - Planning: skills/planning.md
      - Drafting: skills/drafting.md
      - Review: skills/review.md
      - Management: skills/management.md
  - Framework:
      - Gates: framework/gates.md
      - Scoring: framework/scoring.md
      - Dispatcher: framework/dispatcher.md
      - Logging: framework/logging.md
  - API:
      - Exceptions: api/exceptions.md
      - Logging: api/logging.md
  - Architecture Decisions: adr/index.md
  - Contributing: contributing.md
  - Changelog: changelog.md
```

**Acceptance**:

- [ ] `mkdocs build --strict` passes
- [ ] Site has multi-level nav
- [ ] API docs auto-generated from `src/shenbi/` docstrings
- [ ] ADRs listed in their own section
- [ ] Dark mode toggle works

### PR-33: hypothesis failure case persistence

Covered in Cluster 04 PR-33 (duplicated for visibility here; PR number
reserved).

## Cross-cluster Dependencies

- **PR-40 is independent** — can land first.
- **PR-41 is independent** — but CI workflow (PR-35) should land in same
  batch to update `--extra dev` → `--group dev`.
- **PR-42 is independent**.
- **PR-43 depends on PR-18** — mkdocstrings generates from `src/shenbi/`.

## Risks

| Risk | Mitigation |
|------|------------|
| PEP 735 not supported by older uv versions | Document minimum uv version (0.5+) in CONTRIBUTING.md; setup-uv@v3 uses recent version |
| `just` not installed on dev machines | CONTRIBUTING.md documents `brew install just` / `cargo install just` |
| LICENSE choice (MIT vs Apache 2.0) might be wrong for project goals | Confirm with decider; default to MIT per existing declaration |
| MkDocs nav reveals gaps in docs (many sections empty) | Stub all sections with "TODO"; track in issue tracker |

## Open Questions → Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Add `mkdocs-material-social-cards`? | **Yes.** | Free for OSS; auto-generates OpenGraph images per page; improves social shares and link previews in Slack/Discord/Twitter. Low effort, real engagement value. |
| 2 | Require DCO (Developer Certificate of Origin) sign-off? | **No — small project.** | DCO adds friction (`git commit -s`) without legal benefit until corporate contributors arrive. Revisit at v1.0 or when a non-original-author contributes. |
| 3 | GitFlow or trunk-based? | **Trunk-based with feature branches.** | Trunk-based is [industry standard for small/medium projects](https://trunkbaseddevelopment.com/); GitFlow's release branches add ceremony without value for pre-1.0 software. Feature branches with squash-merge + short-lived (< 1 week) is the pattern. |
| 4 | Auto-generate CHANGELOG from conventional commits? | **Yes — `git-cliff`.** | `commitizen` is interactive (bad for CI); `git-cliff` is config-driven. Conventional Commits already required by `CLAUDE.md`. `git-cliff` reads commit history and emits Keep-a-Changelog format. Add to PR-41 (PEP 735) and configure in `cliff.toml`. |
