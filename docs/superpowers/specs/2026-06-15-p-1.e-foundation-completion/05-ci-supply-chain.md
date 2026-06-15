# Cluster 05: CI / Supply Chain Hardening

- Status: **accepted** (per parent [README.md](README.md), 2026-06-15)
- Date: 2026-06-15
- Parent: [README.md](README.md)
- Audit findings covered: F19–F25

## Problem Statement

The current CI pipeline (`.github/workflows/{ci,docs,security}.yml`) passes
but does not enforce several industry-standard supply chain and security
practices. Audit found 7 specific gaps.

### Evidence

#### F19: No `uv lock --check` in CI

`.github/workflows/ci.yml:23`:

```yaml
- run: uv sync --frozen --extra dev
```

`uv sync --frozen` fails if `uv.lock` doesn't satisfy `pyproject.toml`.
**But it does not detect the opposite**: a `pyproject.toml` change without
a corresponding `uv.lock` update. The CI passes locally and in PR, but
on the next clean install someone gets a different dep set.

Industry standard: `uv lock --check` verifies the lockfile is up-to-date
with pyproject.toml. Should run before `uv sync`.

#### F20: No uv cache in CI

`.github/workflows/ci.yml:21`:

```yaml
- uses: astral-sh/setup-uv@v3
```

No `with: enable-cache: true`. Every CI job downloads ~80 Python packages
from PyPI. Each job ~60s slower than necessary.

#### F21: Python 3.13 not in matrix

```yaml
matrix:
  os: [ubuntu-latest, macos-latest]
  python-version: ["3.11", "3.12"]
```

Python 3.13 was released 2024-10-07 (GA). `requires-python = ">=3.11"` so
3.13 is officially supported but never tested. Free-threading changes,
new typing features (PEP 695 defaults), and `__init__.py`-less namespace
package changes might subtly break.

#### F22: No CodeQL static security scanning

GitHub provides free CodeQL analysis for OSS projects. Detects:
- SQL injection / command injection patterns
- Hardcoded credentials
- Path traversal
- Insecure deserialization
- Many more (100+ query suites)

No `.github/workflows/codeql.yml` exists.

#### F23: Renovate automerges minor updates

`renovate.json`:

```json
{
  "matchUpdateTypes": ["minor", "patch"],
  "automerge": true,
  "automergeType": "pr",
  "automergeStrategy": "squash"
}
```

Industry consensus (SLSA Level 3+, OpenSSF Scorecard): automerge only
patch updates. Minor updates can include behavioral changes (semver allows).
A minor Pydantic bump (2.5 → 2.6) introduced `model_config` vs `Config`
changes that broke many downstream projects. Same for any dep.

**Current policy**: minor update → auto-merged without human review.

#### F24: pre-commit hook revs manually pinned, no autoupdate automation

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.13   # released 2024-01; current is v0.6.x
```

Renovate doesn't update pre-commit revs (different format). Without a
workflow running `pre-commit autoupdate`, hooks rot.

#### F25: pre-commit hook references non-existent file

`.pre-commit-config.yaml:43-48`:

```yaml
- id: registry-lockfile-fresh
  name: registry.lock.json freshness (P0 scaffolding, no-op in P-1)
  entry: tests/build_registry.py
  language: system
  files: ^(skills/.*\.yaml|tests/tiers/.*\.yaml)$
  pass_filenames: false
```

`tests/build_registry.py` does not exist. The hook currently skips because
`files:` matches nothing (no `.yaml` files yet in `skills/` or `tests/tiers/`).
**The moment P0 creates a `skills/<name>/meta.yaml`**, this hook fails with
"No such file or directory".

This is a landmine. Either remove the hook or stub `build_registry.py`.

## Root Cause Analysis

### Root cause 1: CI was set up to "pass", not to "enforce"

P-1.B's CI workflow was added to satisfy "we have CI". The specific gaps
(uv lock check, cache, CodeQL) were never added because no one asked "what
does this CI actually verify?" Industry standard: CI is a quality gate, not
a green checkmark.

**Fix**: PR-35 adds the missing checks. Acceptance criteria for each check
explicitly state what it catches and what failure looks like.

### Root cause 2: Renovate was configured with permissive defaults

Renovate's `config:recommended` includes "automerge minor/patch". The
project copied the recommended config without reviewing the automerge rule.
**Industry recommendation**: `config:recommended` for general config, but
explicitly set `automerge: false` for non-patch updates.

**Fix**: PR-36 narrows automerge to patch only.

### Root cause 3: pre-commit hook was added speculatively

The `registry-lockfile-fresh` hook was added during P-1.A as a placeholder
for P0 functionality. But "placeholder" wasn't marked as such — it appears
as a working hook. Future contributors see it and assume it's functional.

**Fix**: PR-37 removes the hook. P0 spec re-adds it when
`build_registry.py` actually exists. (See Cluster 08.)

### Root cause 4: No CI reviewer role in PRs

P-1 didn't designate "what should CI verify before merge". Without an
explicit checklist, each PR author guesses. Some verify ruff + mypy,
others add pytest, none verify uv lock.

**Fix**: Canonical PR-40 (Cluster 06) adds `PULL_REQUEST_TEMPLATE.md` with required
CI status checks. Branch protection (configured via GitHub UI, documented
in `CONTRIBUTING.md`) requires all checks pass.

## Target State

After P-1.E Cluster 05 completes:

| Check | Pre-P-1.E | Post-P-1.E |
|-------|-----------|------------|
| `uv lock --check` | not in CI | runs in every CI job before `uv sync` |
| uv cache | not enabled | `enable-cache: true` in all jobs |
| Python versions | 3.11, 3.12 | 3.11, 3.12, 3.13 |
| OS matrix | ubuntu, macos | ubuntu, macos, (windows optional) |
| CodeQL | not configured | Python analysis on every PR + weekly |
| Renovate automerge | minor + patch | patch only |
| pre-commit autoupdate | manual | weekly workflow + auto PR |
| pre-commit landmine | `registry-lockfile-fresh` references missing file | hook removed |

## Components (PRs)

### PR-35: CI hardening

**Files modified**: `.github/workflows/ci.yml`

**New CI job structure**:

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  quality:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      - run: uv python install ${{ matrix.python-version }}
      - name: Verify uv.lock is up to date
        run: uv lock --check
      - run: uv sync --frozen --extra dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src/shenbi/
      - run: uv run basedpyright
      - name: Run tests (parallel, excluding last)
        run: uv run pytest -n auto -m "not last" --hypothesis-profile=ci
      - name: Run coverage threshold test (serial, last only)
        run: uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci

  action-validation:
    ...

  mutation-testing:                       # NEW JOB
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --extra dev
      - name: Run mutation testing
        run: |
          # Scope to changed Python files for incremental speed
          CHANGED=$(git diff --name-only origin/main HEAD -- 'src/shenbi/**/*.py' | tr '\n' ',' | sed 's/,$//')
          if [ -n "$CHANGED" ]; then
            uv run mutmut run --use-cache --paths-to-mutate "$CHANGED"
          else
            echo "No Python changes; skipping mutation testing"
          fi
      - name: Compare to baseline
        run: uv run python tools/compare_mutation_score.py --baseline tests/baselines/mutation-score.txt
```

**Acceptance**:

- [ ] `uv lock --check` runs and passes in CI
- [ ] `enable-cache: true` reduces job time by ≥ 30s
- [ ] Matrix includes Python 3.13
- [ ] Mutation testing job runs on PRs and **blocks on regression**: if mutation score drops > 5% from baseline (`tests/baselines/mutation-score.txt`), CI fails. Absolute threshold (60%) is enforced only after PR-23 stabilizes the baseline; during initial rollout the regression check is the gate.
- [ ] CI total runtime ≤ 5 minutes

### PR-36: CodeQL workflow

**Files created**: `.github/workflows/codeql.yml`

```yaml
name: CodeQL
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 4 * * 1'  # Weekly Monday 04:00 UTC

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        language: [python]
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          queries: +security-and-quality
      - uses: github/codeql-action/analyze@v3
```

**Acceptance**:

- [ ] CodeQL workflow runs on every PR and weekly
- [ ] Security tab in GitHub shows CodeQL alerts
- [ ] Initial run shows 0 critical alerts (or documented exceptions)

### PR-37: renovate policy fix

**Files modified**: `renovate.json`

**New content**:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended", ":semanticCommits"],
  "schedule": ["before 6am on monday"],
  "timezone": "Asia/Shanghai",
  "packageRules": [
    {
      "groupName": "ruff",
      "matchPackagePatterns": ["ruff"]
    },
    {
      "groupName": "pytest",
      "matchPackagePatterns": ["pytest"]
    },
    {
      "description": "Patch updates can automerge after CI passes",
      "matchUpdateTypes": ["patch"],
      "automerge": true,
      "automergeType": "pr",
      "automergeStrategy": "squash"
    },
    {
      "description": "Minor updates require human review (may include behavioral changes)",
      "matchUpdateTypes": ["minor"],
      "automerge": false,
      "labels": ["minor-bump"]
    },
    {
      "description": "Major updates require human review and labels",
      "matchUpdateTypes": ["major"],
      "automerge": false,
      "labels": ["major-bump"]
    },
    {
      "description": "Pre-commit hook revs updated weekly",
      "matchManagers": ["pre-commit"],
      "automerge": false,
      "labels": ["pre-commit"]
    }
  ],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"],
    "automerge": true,
    "automergeType": "pr",
    "automergeStrategy": "squash"
  }
}
```

**Acceptance**:

- [ ] Only `patch` updates automerge
- [ ] Minor/major updates create PRs with labels, no automerge
- [ ] Vulnerability alerts (Dependabot-style) automerge after CI

### PR-38: pre-commit autoupdate workflow + landmine removal

**Step 1: Remove landmine**

Modify `.pre-commit-config.yaml`: delete the entire `registry-lockfile-fresh`
hook block. It will be re-added in P0 when `build_registry.py` exists.

**Step 2: Add autoupdate workflow**

`.github/workflows/pre-commit-autoupdate.yml`:

```yaml
name: Pre-commit autoupdate
on:
  schedule:
    - cron: '0 2 * * 1'  # Monday 02:00 UTC
  workflow_dispatch:

jobs:
  autoupdate:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install pre-commit
      - run: pre-commit autoupdate
      - name: Create PR if changes
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore: pre-commit autoupdate"
          title: "chore: pre-commit autoupdate"
          branch: pre-commit-autoupdate
          labels: dependencies, pre-commit
```

**Acceptance**:

- [ ] `.pre-commit-config.yaml` no longer references `tests/build_registry.py`
- [ ] `pre-commit-autoupdate.yml` workflow exists
- [ ] First run creates a PR (or reports no updates needed)
- [ ] `CONTRIBUTING.md` documents that pre-commit revs auto-update weekly

### PR-39: SBOM attach to GitHub releases + release workflow

**Files created**: `.github/workflows/release.yml`

```yaml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --extra dev
      - name: Generate SBOM
        run: uv run cyclonedx-py environment -o sbom.cdx.json
      - name: Build sdist and wheel
        run: uv build
      - name: Generate changelog for tag
        id: changelog
        run: |
          prev_tag=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
          if [ -n "$prev_tag" ]; then
            notes=$(git log --format='- %s (%h)' ${prev_tag}..HEAD)
          else
            notes=$(git log --format='- %s (%h)')
          fi
          echo "notes<<EOF" >> $GITHUB_OUTPUT
          echo "$notes" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          body: ${{ steps.changelog.outputs.notes }}
          files: |
            dist/*.whl
            dist/*.tar.gz
            sbom.cdx.json
```

**Acceptance**:

- [ ] `release.yml` workflow triggers on tag push (`v*`)
- [ ] Creates GitHub Release with auto-generated changelog
- [ ] Attaches wheel, sdist, and SBOM
- [ ] First release tag (e.g., `v0.2.0`) produces all 3 artifacts

## Cross-cluster Dependencies

- **PR-35 depends on PR-18** (src layout) and **PR-25** (no mypy overrides):
  CI runs `mypy src/shenbi/` which requires the new layout and clean type
  checking.
- **PR-38 (Step 1: remove landmine) is independent** — should land FIRST to
  unblock P0 brainstorming.

## Risks

| Risk | Mitigation |
|------|------------|
| CodeQL initial scan finds many false positives | Triage in first week; mark false positives with `// codeql: disable` comments with reason |
| Pre-commit autoupdate breaks hooks (new rev has stricter rules) | CI catches before merge; rollback by reverting the autoupdate PR |
| Python 3.13 reveals compatibility issues in deps | Pin 3.13 to allowed-failure initially; promote once stable |
| Mutation testing job is slow (10+ min) | Use `mutmut run --use-cache` for incremental analysis; cache persists across runs. Run on PRs but with `--paths-to-mutate` scoped to changed files (per `git diff --name-only`). 10-min wall time is acceptable for a blocking gate. |

## Open Questions → Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Add `windows-latest` to CI matrix? | **Yes, but split: Python tests on Windows; shell-dependent tests skip on Windows via `@pytest.mark.skip_on_windows` (custom marker).** | Shenbi declares `requires-python = ">=3.11"` without OS restriction (pyproject.toml:8). Cross-platform claim must be tested. `pathlib.Path` is cross-platform but `tests/dispatch-subagent.sh` is bash-only. Windows testing catches `ntpath` vs `posixpath` bugs in skill Python scripts. |
| 2 | `dependency-review-action` for PRs touching `pyproject.toml`? | **Yes.** | GitHub-native, free for OSS, catches license incompatibilities + known vulns at PR time (before merge). Industry standard for SLSA Level 2+. |
| 3 | Auto-publish to PyPI on release? | **No until v1.0.** | Manual `twine upload` until API stability is declared. Automatic publish creates "release lock-in" — once a version is on PyPI, it can't be un-published (only yanked). Document manual process in `CONTRIBUTING.md`. Revisit at v1.0. |
| 4 | Add Snyk or OSV-scanner? | **No — pip-audit + CodeQL is sufficient at current scope.** | pip-audit consumes the Python Packaging Advisory Database (canonical source). CodeQL covers source-code vulns. Adding Snyk duplicates pip-audit's signal with a vendor lock-in cost. Reconsider at v1.0 if threat model expands. |
