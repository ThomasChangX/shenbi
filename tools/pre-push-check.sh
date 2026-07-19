#!/usr/bin/env bash
# Pre-push CI simulation — runs the same checks as GitHub CI.
# Install: pre-commit install --hook-type pre-push
set -euo pipefail

echo "=== pre-push: CI simulation ==="

# 1. Lockfile integrity (ci.yml step 1)
echo "--- uv lock --check ---"
uv lock --check

# 2. Ruff lint + format (ci.yml steps 2-3)
echo "--- ruff check ---"
uv run ruff check .
echo "--- ruff format --check ---"
uv run ruff format --check .

# 3. Type checking (ci.yml steps 4-5)
echo "--- mypy ---"
uv run mypy src/shenbi/
echo "--- basedpyright ---"
uv run basedpyright || { echo "basedpyright failed"; exit 1; }

# 4. Custom linters (ci.yml steps 6-9)
echo "--- lint_status_strings ---"
uv run python tools/lint_status_strings.py
echo "--- lint_contracts ---"
uv run python tools/lint_contracts.py
echo "--- lint_repo_consistency ---"
uv run python tools/lint_repo_consistency.py
echo "--- lint_no_forbid ---"
uv run python tools/lint_no_forbid_with_computed_field.py src/shenbi/contracts
echo "--- lint_no_fs_mutation ---"
uv run python tools/lint_no_fs_mutation.py src/shenbi

# 5. Tests (ci.yml step 10)
# --dist loadscope groups tests by module so ThreadPoolExecutor tests
# don't interfere across modules. --timeout prevents indefinite hangs.
echo "--- pytest (with coverage >= 85%) ---"
uv run pytest -n auto --dist loadscope -m "not last" --cov-fail-under=85 --timeout=120

# 6. Dead code detection
echo "--- dead code check (reportUnusedFunction) ---"
UNUSED_COUNT=$(grep -r 'reportUnusedFunction' src/shenbi/ --include='*.py' | grep -v test_ | grep -v __pycache__ | wc -l | tr -d ' ')
if [ "$UNUSED_COUNT" -gt 5 ]; then
    echo "WARNING: $UNUSED_COUNT reportUnusedFunction suppressions found in src/shenbi/"
    echo "These may indicate dead code that should be removed or wired in."
    echo "Review with: grep -rn 'reportUnusedFunction' src/shenbi/"
fi

# 7. Coverage threshold test (serial, last only)
# Must use --no-cov so this invocation doesn't overwrite coverage.xml
# produced by step 5. The test reads the existing coverage.xml.
echo "--- pytest coverage threshold ---"
uv run pytest -p no:xdist -m "last" --no-cov --timeout=60

# 6. Contract sync idempotency (ci.yml contract-sync job)
echo "--- contract-sync idempotency ---"
uv run shenbi-sync-contracts >/dev/null
git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/

# 8. Auto-check docs idempotency
echo "--- autocheck-docs idempotency ---"
uv run python tools/generate_autocheck_docs.py >/dev/null
git diff --exit-code -- skills/

echo "=== pre-push: all checks passed ==="
