# CI Optimization Design

**Date:** 2026-07-09
**Status:** Approved (pending implementation)

## Context

CI check times after pushing code are excessive. An evidence-based analysis of
the most recent PR run (#28990844821) revealed:

- **Wall-clock per PR:** 16.6 min (dominated by the slowest matrix job,
  `windows-latest × 3.12`)
- **Billable minutes per PR:** ~90 min (Windows billed at 2x; 9 quality jobs
  + 6 auxiliary jobs)
- **Test step alone:** 773s = 93% of each quality job's runtime
- **Branch protection:** `contexts: []` — no required checks configured, so the
  9 quality jobs consume ~90 billable minutes without being merge-gating

### Evidence summary

| Finding | Evidence |
|---------|----------|
| Windows is defensive-only, not a target platform | `filelock_utils.py` and `safe_write.py` have `# pragma: no cover` Windows branches; no `Operating System ::` classifier in `pyproject.toml`; docs declare "平台无关" |
| Python 3.13 is `continue-on-error` (allowed-to-fail) | `ci.yml:23` — provides no reliable gate signal yet consumes 3 jobs |
| `mutation-testing` job is dead code | `ci.yml:111` `if: false` — completely disabled, zero value |
| `doc-links` checks external HTTP links | 109 tests that depend on external site availability — flaky risk, unrelated to code quality |
| `contract-sync` + `plugin-manifest-freshness` share a pattern | Both are "run generator + git diff"; each pays 22s `uv sync` for <3s of real work |
| `renovate-config-validator` runs every PR | 43s per run (npx downloads renovate) to validate a rarely-changed config file |
| `uv sync --frozen --group dev` runs 14+ times per PR | Across all jobs, ~22s each = significant redundant environment setup |

## Decisions (from brainstorming)

1. **Scope:** Surgical — high-certainty, small-diff, low-risk changes. No full
   `ci.yml` rewrite.
2. **Python 3.13:** Remove from PR matrix; keep on `push(main)` with
   `continue-on-error`.
3. **Windows:** Remove from PR and push matrix entirely. Retain as dispatch-only
   nightly smoke test.
4. **Low-frequency checks (Windows, 3.13, doc-links):** New `nightly.yml`,
   **dispatch-only** (no schedule) — zero automatic resource consumption.
5. **`contract-sync` + `plugin-manifest-freshness`:** Merge into single
   `codegen-idempotency` job (shared `uv sync`).
6. **`pre-push-check.sh`:** No change — it already simulates only core checks
   that remain in PR CI.

## Design

### Part 1: Matrix reduction (`ci.yml` `quality` job)

**Current:** `3 OS × 3 Python = 9 jobs`, no PR/push differentiation.

**After:**

- **PR:** `ubuntu-latest + macos-latest`, Python `3.11 + 3.12` = **4 jobs**
- **push(main):** same OS matrix (ubuntu + macos), Python adds `3.13` =
  **6 jobs**. Windows is removed entirely (see decision 3 + Part 4).
- `fail-fast`: `true` on PR (cancel siblings on failure, save spend), `false`
  on main

```yaml
strategy:
  fail-fast: ${{ github.event_name == 'pull_request' }}
  matrix:
    # Windows removed entirely — it is defensive support, not a target
    # platform (see Part 4 nightly.yml windows-smoke).
    os: [ubuntu-latest, macos-latest]
    python-version: ${{ github.event_name == 'pull_request'
            && fromJson('["3.11","3.12"]')
            || fromJson('["3.11","3.12","3.13"]') }}
```

`continue-on-error` remains `python-version == '3.13'` only (triggers only on
main push; PR never includes 3.13).

### Part 2: Delete dead code + merge redundant jobs (`ci.yml`)

**Delete `mutation-testing` job** (`ci.yml:105-140`):
- `if: false` — completely disabled, zero value.
- Move the mutmut 3.x compatibility note into `nightly.yml` comments (for
  future re-enable reference).

**Merge `contract-sync` + `plugin-manifest-freshness` → `codegen-idempotency`:**

Both follow the identical pattern: run a generator, then `git diff --exit-code`
to detect artifact drift. Merging shares one `uv sync` (saves ~25s) and one
job's overhead:

```yaml
codegen-idempotency:
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

### Part 3: Low-frequency check migration + paths filter (`ci.yml`)

**Remove `doc-links` job from `ci.yml`:** migrates to `nightly.yml` (Part 4).
Rationale: 109 tests perform external HTTP link checks — depend on external site
availability, high flaky risk, unrelated to code quality. Removing it also
eliminates Node.js + npm install + uv sync environment setup (~30s pure
overhead) from every PR.

**`renovate-config-validator` paths filter:**

Currently runs 43s every PR (npx downloads renovate) to validate a rarely-changed
`renovate.json`. The `action-validation` job also contains `yamllint` (<1s,
worth running every time), so the job cannot be filtered wholesale — only the
renovate step:

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
      # Only run when renovate.json changes (saves 43s npx download)
      if: ${{ github.event_name == 'pull_request' }}
      run: |
        if git diff --name-only origin/${{ github.base_ref }}...HEAD | grep -q '^renovate\.json$'; then
          npx --yes -p renovate renovate-config-validator renovate.json
        else
          echo "renovate.json unchanged — skipping"
        fi
```

On `push(main)`, `renovate.json` carries no unvalidated changes (PR already
validated or skipped), so the conditional is PR-only.

### Part 4: New `nightly.yml` (dispatch-only)

Collects all checks that have regression value but do not warrant per-PR
execution. **Dispatch-only** — no `schedule`, so it never runs automatically and
consumes zero CI resources. The file preserves design intent and knowledge for
future re-enablement.

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
#   - doc-links:            External markdown link checks
#                           (depend on external site availability)
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
    # External markdown link checks. Depends on external site availability
    # (flaky risk); kept here to avoid external outages blocking PRs.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm install -g markdown-link-check
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

**Key points:**
- `schedule` is commented out → never auto-runs, zero resource consumption
- `python-313-migration` has **no** `continue-on-error` — in dispatch-only mode,
  failures should be visible (nightly isn't in branch protection anyway)
- mutmut compatibility note preserved as a comment for future reference

## Files changed

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Matrix reduction (Part 1); delete `mutation-testing` + merge codegen (Part 2); renovate paths filter + delete `doc-links` (Part 3) |
| `.github/workflows/nightly.yml` | **New file** — dispatch-only, collects windows-smoke / python-313 / doc-links (Part 4) |

**Unchanged:** `security.yml`, `docs.yml`, `release.yml`, `pre-commit-autoupdate.yml`, `tools/pre-push-check.sh`.

## Expected impact

```
Before (15 jobs/PR):                          After (8 jobs/PR):
────────────────────────────────              ───────────────────────────────
quality × 9 matrix         16.6min wall       quality × 4 (ub/mac×3.11/3.12)  ~8min wall
contract-sync              0.5min             codegen-idempotency (merged)    ~0.5min
plugin-manifest-freshness  0.5min             action-validation (renovate+)   ~0.7min
action-validation          1.2min             dependency-review              0.1min
doc-links                  0.9min             ──────────────────────────────
dependency-review          0.1min             (Windows/3.13/doc-links → nightly.yml, dispatch-only)
mutation-testing           (skip)

Billable: ~90 min/PR                         Billable: ~20 min/PR
Wall-clock: 16.6 min                         Wall-clock: ~8 min

push(main) also shrinks: 9 → 6 quality jobs (Windows gone; 3.13 kept w/ continue-on-error)
```

## What is NOT lost

| Removed/migrated check | Where the protection went |
|------------------------|--------------------------|
| Windows × 3 matrix | `nightly.yml` `windows-smoke` (manual trigger) |
| Python 3.13 × 3 matrix | `nightly.yml` `python-313-migration` (manual trigger) |
| doc-links external links | `nightly.yml` `doc-links` (manual trigger) |
| mutation-testing | Deleted (was `if: false` dead code) |
| contract-sync / plugin generation | Merged into `codegen-idempotency` (still runs on PR) |
| lint / type-check / test core | **Fully retained** — all 4 PR jobs run them |

## Risk

The only accepted trade-off: `nightly.yml` is dispatch-only, meaning Windows,
Python 3.13, and doc-links currently have **no automatic regression protection**.
This is the explicitly accepted trade-off from brainstorming ("not worth the
effort to maintain/monitor alerts"). Mitigation: the file is preserved with
comments; re-enabling requires uncommenting one `schedule` line.

## Open questions

None. All decisions resolved during brainstorming.
