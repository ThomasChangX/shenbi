# CI Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce PR CI wall-clock from ~16.6min to ~8min and billable minutes from ~90 to ~20 by shrinking the matrix, deleting dead code, merging redundant jobs, and migrating low-frequency checks to a dispatch-only nightly workflow.

**Architecture:** Surgical edits to `.github/workflows/ci.yml` (matrix reduction, job merge, path filter, dead-code deletion) plus a new `.github/workflows/nightly.yml` (dispatch-only, collecting Windows/3.13/doc-links). No application code changes.

**Tech Stack:** GitHub Actions (YAML), `uv`, pytest.

**Spec:** `docs/superpowers/specs/2026-07-09-ci-optimization-design.md`

## Global Constraints

- All YAML must pass `uv run yamllint --strict .github/workflows/` (enforced by the `action-validation` job).
- No application code (`src/shenbi/`, `tests/`) is touched — only `.github/workflows/`.
- `continue-on-error` only on `python-version == '3.13'` (triggers only on push(main)).
- Windows is removed from the matrix entirely (defensive support, not a target platform).
- The new `nightly.yml` must have NO active `schedule:` trigger (dispatch-only).
- Commit messages follow Conventional Commits (`chore:`, `ci:`, etc.).

---

## Prerequisites

Before Task 1, create a feature branch (do not commit to `main` directly):

```bash
git checkout -b ci/optimize-pr-matrix
```

All tasks commit to this branch. Task 5 pushes it and opens a PR.

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `.github/workflows/ci.yml` | Modify | Matrix reduction, delete mutation-testing, merge contract-sync+plugin-manifest into codegen-idempotency, renovate path filter, delete doc-links, collapse Windows test step |
| `.github/workflows/nightly.yml` | Create | Dispatch-only workflow collecting windows-smoke, python-313-migration, doc-links |

No other files change.

---

### Task 1: Matrix reduction + collapse Windows test step (Part 1)

**Files:**
- Modify: `.github/workflows/ci.yml` (strategy block lines 12-23, test steps lines 54-64, comment lines 19-22)

**Interfaces:**
- Produces: a `quality` job that produces 4 matrix legs on PR (ubuntu/macOS × 3.11/3.12) and 6 on push(main) (adds 3.13 × 2 OS), with a single unconditional test step.

- [ ] **Step 1: Replace the strategy block (lines 12-23)**

Replace this exact text:

```yaml
  quality:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12", "3.13"]
    # 3.13 allow-failure during rollout (spec Risk table).
    # Windows coverage threshold is 88 (vs 89 POSIX) because fcntl-based
    # locking (~50 lines in filelock_utils.py) is structurally unreachable
    # on Windows — covered on POSIX, uncovered on Windows.
    continue-on-error: ${{ matrix.python-version == '3.13' }}
```

with:

```yaml
  quality:
    runs-on: ${{ matrix.os }}
    strategy:
      # PR: fail fast to cancel sibling jobs on failure (save billable
      # minutes). push(main): full visibility, no early cancel.
      fail-fast: ${{ github.event_name == 'pull_request' }}
      matrix:
        # Windows removed — defensive support, not a target platform.
        # See .github/workflows/nightly.yml windows-smoke for fallback
        # code regression protection (dispatch-only).
        os: [ubuntu-latest, macos-latest]
        # PR: 3.11 + 3.12 only. push(main): adds 3.13 (migration monitoring).
        python-version: ${{ github.event_name == 'pull_request'
                && fromJson('["3.11", "3.12"]')
                || fromJson('["3.11", "3.12", "3.13"]') }}
    # 3.13 allow-failure during rollout (spec Risk table).
    # Only triggers on push(main) — PR never includes 3.13.
    continue-on-error: ${{ matrix.python-version == '3.13' }}
```

- [ ] **Step 2: Collapse the two Windows/POSIX test steps into one**

Replace this exact text (lines 54-64):

```yaml
      - name: Run tests (parallel, excluding last)
        if: matrix.os != 'windows-latest'
        run: uv run pytest -n auto -m "not last" --hypothesis-profile=ci
      - name: Run tests (parallel, excluding last, Windows)
        if: matrix.os == 'windows-latest'
        # 88% threshold on Windows: fcntl-based locking (~50 lines in
        # filelock_utils.py) is structurally unreachable on Windows but
        # covered on POSIX — the 1% gap is permanent platform divergence.
        run: uv run pytest -n auto -m "not last" --hypothesis-profile=ci --cov-fail-under=85
      - name: Run coverage threshold test (serial, last only)
        run: uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci
```

with:

```yaml
      - name: Run tests (parallel, excluding last)
        run: uv run pytest -n auto -m "not last" --hypothesis-profile=ci
      - name: Run coverage threshold test (serial, last only)
        run: uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci
```

- [ ] **Step 3: Validate YAML locally**

Run: `uv run yamllint --strict .github/workflows/ci.yml`
Expected: no errors (warnings on line-length are acceptable if the existing config allows them).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: shrink quality matrix (remove Windows, gate 3.13 to push)

PR matrix: ubuntu/macOS × 3.11/3.12 = 4 jobs (was 9).
push(main): adds 3.13 × 2 OS = 6 jobs.
Collapses the Windows-specific test step (dead code after removal).
fail-fast: true on PR (cancel siblings), false on main."
```

---

### Task 2: Delete mutation-testing dead job + merge codegen jobs (Part 2)

**Files:**
- Modify: `.github/workflows/ci.yml` (delete mutation-testing lines 105-140, replace contract-sync + plugin-manifest-freshness lines 66-153)

**Interfaces:**
- Produces: a single `codegen-idempotency` job (merged from `contract-sync` + `plugin-manifest-freshness`) and the deleted `mutation-testing` job.

- [ ] **Step 1: Replace contract-sync job with merged codegen-idempotency**

Replace this exact text (lines 66-79):

```yaml
  contract-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - name: Regenerate contract-derived artifacts
        run: uv run shenbi-sync-contracts
      - name: Regenerate auto-check docs (spec P6)
        run: uv run python tools/generate_autocheck_docs.py
      - name: Idempotency — generated artifacts must match committed
        run: git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/
```

with:

```yaml
  codegen-idempotency:
    # Merges former contract-sync + plugin-manifest-freshness. Both follow
    # the same pattern: run generators, git diff for drift. Sharing one
    # uv sync saves ~25s of redundant environment setup.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      # Three generators run sequentially (each <1s, order-independent).
      - name: Contract artifacts (deps.json, body views, DAG)
        run: uv run shenbi-sync-contracts
      - name: Auto-check docs (spec P6)
        run: uv run python tools/generate_autocheck_docs.py
      - name: Plugin manifests (.claude/.codex/.cursor/.opencode)
        run: uv run shenbi-generate-plugins
      - name: Idempotency — all generated artifacts must match committed
        run: |
          git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/ \
                                .claude-plugin/ .codex-plugin/ .cursor-plugin/ .opencode/
```

- [ ] **Step 2: Delete the plugin-manifest-freshness job**

Delete this exact text (lines 142-153):

```yaml
  plugin-manifest-freshness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - name: Verify plugin manifests are up to date
        run: |
          uv run shenbi-generate-plugins
          git diff --exit-code .claude-plugin/ .codex-plugin/ .cursor-plugin/ .opencode/
```

- [ ] **Step 3: Delete the mutation-testing dead job**

Delete this exact text (lines 105-140):

```yaml
  mutation-testing:
    runs-on: ubuntu-latest
    # DISABLED on PRs: mutmut 3.x's mutants/ workspace omits the full
    # src/shenbi/ package (ModuleNotFoundError: shenbi.gates.g4) and skills/,
    # so the suite cannot establish a green baseline there. Re-enable (and
    # drop this guard) once mutmut is reconfigured for this project layout.
    if: false
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - name: Run mutation testing
        run: |
          # mutmut 3.x reads source_paths from [tool.mutmut] config;
          # per-file CLI scoping is not supported (no --paths-to-mutate
          # or --use-cache flags in 3.x). Changed-file detection only
          # decides whether to run mutmut at all.
          BASE="origin/${{ github.event.pull_request.base.ref }}"
          CHANGED=$(git diff --name-only "${BASE}...HEAD" \
            -- 'src/shenbi/')
          if [ -z "$CHANGED" ]; then
            echo "No Python changes; skipping mutation testing"
            exit 0
          fi
          uv run mutmut run
      - name: Compare to baseline (blocks on regression > 5%)
        run: |
          # compare_mutation_score.py runs 'mutmut results' internally
          # and parses output; it only accepts --baseline and --threshold
          # (Plan 2 PR-23). No --current flag exists.
          uv run python tools/compare_mutation_score.py \
            --baseline tests/baselines/mutation-score.txt
```

- [ ] **Step 4: Validate YAML locally**

Run: `uv run yamllint --strict .github/workflows/ci.yml`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: merge codegen jobs + delete dead mutation-testing

- contract-sync + plugin-manifest-freshness -> codegen-idempotency
  (shared uv sync, single git diff over all artifact paths)
- delete mutation-testing (was if:false dead code, zero value)"
```

---

### Task 3: Renovate path filter + delete doc-links job (Part 3)

**Files:**
- Modify: `.github/workflows/ci.yml` (action-validation job lines 89-103, doc-links job lines 155-170)

**Interfaces:**
- Produces: `action-validation` with a `gh api`-based renovate conditional; `doc-links` job removed.

- [ ] **Step 1: Replace action-validation job to add renovate path filter**

Replace this exact text (lines 89-103):

```yaml
  action-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - name: Validate GitHub Actions YAML
        run: uv run yamllint --strict .github/workflows/
      - name: Validate Renovate config schema
        run: |
          # renovate-config-validator is provided by the renovate npm package.
          # Using npx avoids adding a persistent dep.
          npx --yes -p renovate renovate-config-validator renovate.json
```

with:

```yaml
  action-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - name: Validate GitHub Actions YAML
        run: uv run yamllint --strict .github/workflows/
      - name: Validate Renovate config schema
        # Only run when renovate.json changes (saves 43s npx download).
        # Uses gh api (not git diff) because the default checkout is
        # shallow (fetch-depth: 1) — git diff against origin/<base> would
        # silently return empty and permanently disable this check.
        if: ${{ github.event_name == 'pull_request' }}
        run: |
          CHANGED=$(gh api repos/${{ github.repository }}/pulls/${{ github.event.pull_request.number }}/files \
            --jq '[.[] | select(.filename == "renovate.json")] | length')
          if [ "$CHANGED" -gt 0 ]; then
            npx --yes -p renovate renovate-config-validator renovate.json
          else
            echo "renovate.json unchanged — skipping"
          fi
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: Delete the doc-links job**

Delete this exact text (lines 155-170):

```yaml

  doc-links:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm install -g markdown-link-check
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - run: uv run pytest -n auto tests/integration/test_doc_links.py -q --no-cov
```

- [ ] **Step 3: Validate YAML locally**

Run: `uv run yamllint --strict .github/workflows/ci.yml`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: gate renovate validator to renovate.json changes, drop doc-links

- action-validation: renovate validator runs only when renovate.json
  changes (gh api query, not git diff — avoids shallow-clone bug)
- doc-links removed (migrated to nightly.yml in next task)"
```

---

### Task 4: Create nightly.yml (Part 4)

**Files:**
- Create: `.github/workflows/nightly.yml`

**Interfaces:**
- Produces: a dispatch-only workflow with three jobs: `windows-smoke`, `python-313-migration`, `doc-links`. No active schedule.

- [ ] **Step 1: Create the nightly.yml file**

Create `.github/workflows/nightly.yml` with this exact content:

```yaml
name: Nightly
# ─────────────────────────────────────────────────────────────
# Current state: DISABLED (does not auto-execute)
#
# These checks have regression value but are not worth running
# automatically per-PR or on a schedule at this time:
#   - windows-smoke:        Smoke test for Windows fallback code
#                           (defensive support, not a target platform)
#   - python-313-migration: Python 3.13 migration monitoring
#   - doc-links:            Markdown link checks (internal + external).
#                           External links depend on third-party site
#                           availability (flaky); internal links are a
#                           valid signal but gated here for simplicity.
#
# To enable: uncomment the schedule trigger below and monitor
# Actions failure alerts.
# ─────────────────────────────────────────────────────────────
on:
  # schedule:
  #   - cron: '0 6 * * *'   # Uncomment to enable daily auto-execution
  workflow_dispatch:        # Manual trigger only

jobs:
  windows-smoke:
    # Windows fallback code regression protection. The ~50 lines of
    # sys.platform != "win32" branches in filelock_utils.py / safe_write.py
    # are # pragma: no cover in tests (structurally untestable). This smoke
    # test ensures import + basic flow still works on Windows.
    runs-on: windows-latest
    env:
      PYTHONUTF8: "1"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv python install 3.12
      - run: uv sync --frozen --group dev
      - run: uv run pytest -n auto -m "not last" --cov-fail-under=85

  python-313-migration:
    # 3.13 migration monitoring. No continue-on-error: nightly itself is
    # non-blocking (not in any branch protection), so setting it would
    # silently suppress 3.13 regression signals. Failure here = real
    # regression, should be visible.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv python install 3.13
      - run: uv sync --frozen --group dev
      - run: uv run pytest -n auto -m "not last" --hypothesis-profile=ci

  doc-links:
    # Markdown link checks (internal relative links + external HTTP links).
    # External links depend on third-party site availability (flaky risk);
    # kept here to avoid external outages blocking PRs. Internal link rot
    # (e.g. renamed file) also surfaces here instead of per-PR — accepted
    # trade-off.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm install -g markdown-link-check
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen --group dev
      - run: uv run pytest -n auto tests/integration/test_doc_links.py -q --no-cov

  # ─────────────────────────────────────────────────────────────
  # Future: mutation-testing
  # Currently disabled due to mutmut 3.x incompatibility (mutants/ workspace
  # omits src/shenbi/ package + skills/, cannot establish green baseline).
  # Re-enable once mutmut is reconfigured for this project layout.
  # ─────────────────────────────────────────────────────────────
```

- [ ] **Step 2: Validate YAML locally**

Run: `uv run yamllint --strict .github/workflows/nightly.yml`
Expected: no errors.

- [ ] **Step 3: Verify schedule is commented out (dispatch-only invariant)**

Run: `grep -n "schedule:" .github/workflows/nightly.yml`
Expected: the only match is the commented line `# schedule:` (line ~24). If an uncommented `schedule:` exists, the dispatch-only invariant is violated.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/nightly.yml
git commit -m "ci: add dispatch-only nightly.yml for low-frequency checks

Collects windows-smoke, python-313-migration, doc-links.
schedule: is commented out (dispatch-only) — zero automatic resource
consumption. Uncomment schedule + monitor alerts to re-enable."
```

---

### Task 5: Post-edit validation (spec Validation section)

**Files:**
- Read-only: `.github/workflows/ci.yml`, `.github/workflows/nightly.yml`

**Interfaces:**
- Produces: confirmation that the edits are structurally correct before pushing.

- [ ] **Step 1: Verify ci.yml job inventory (no leftover dead jobs)**

Run:
```bash
grep -E "^  [a-z].*:" .github/workflows/ci.yml | grep -v "^  #"
```
Expected jobs present: `quality:`, `codegen-idempotency:`, `dependency-review:`, `action-validation:`.
Expected jobs ABSENT: `mutation-testing:`, `contract-sync:`, `plugin-manifest-freshness:`, `doc-links:`.

If any absent job still appears, a deletion in Tasks 2-3 was incomplete.

- [ ] **Step 2: Verify nightly.yml job inventory**

Run:
```bash
grep -E "^  [a-z].*:" .github/workflows/nightly.yml | grep -v "^  #"
```
Expected: `windows-smoke:`, `python-313-migration:`, `doc-links:`.

- [ ] **Step 3: Verify matrix produces intended leg counts (YAML lint + manual review)**

Run: `uv run yamllint --strict .github/workflows/ci.yml .github/workflows/nightly.yml`
Expected: no errors.

Manually confirm the strategy block in ci.yml reads:
- `os: [ubuntu-latest, macos-latest]` (no windows)
- `python-version` conditional: PR → `["3.11", "3.12"]`, else → `["3.11", "3.12", "3.13"]`
- `fail-fast: ${{ github.event_name == 'pull_request' }}`

- [ ] **Step 4: Verify single test step (no dead Windows step)**

Run: `grep -c "Run tests (parallel" .github/workflows/ci.yml`
Expected: `1` (exactly one "Run tests (parallel" step). If `2`, the Windows step wasn't collapsed.

- [ ] **Step 5: No commit (validation-only task)**

This task produces no code changes. If all checks pass, the implementation is complete. Push and open a PR to validate on real CI.

- [ ] **Step 6: Push and validate on real CI (spec Validation item 1-2)**

After pushing and opening a PR:
- Confirm the `quality` job shows exactly **4** matrix legs (not 9).
- In a separate PR that modifies `renovate.json`, confirm the `Validate Renovate config schema` step **runs** (not "skipping").

```bash
git push -u origin HEAD
gh pr create --title "ci: optimize PR CI (matrix shrink, codegen merge, nightly)" \
  --body "See docs/superpowers/specs/2026-07-09-ci-optimization-design.md"
```
