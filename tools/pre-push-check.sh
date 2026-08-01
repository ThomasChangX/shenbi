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

# 4b. Security audit (ci.yml security workflow)
echo "--- pip-audit (dev group, mirroring CI security.yml) ---"
uv sync --frozen --group dev >/dev/null
uv run pip-audit

# 4c. mkdocs link check (only when docs changes)
# 触发：检测待 push 的 docs 变更。pre-push 阶段已 commit，--cached 和 HEAD diff 都恒空，
#   正确 idiom 是 main...HEAD（推送范围）。
if git diff --name-only main...HEAD 2>/dev/null | grep -qE '^(docs/|mkdocs\.yml)'; then
  echo "--- mkdocs link check (docs changed) ---"
  uv sync --group docs >/dev/null
  # 单次 build 捕获输出与 exit code
  if ! out="$(uv run mkdocs build --strict 2>&1)"; then
    # (a) 死链 → 必失败
    if echo "$out" | grep -q 'contains a link'; then
      echo "$out" | grep 'contains a link'; exit 1
    fi
    # 判 libcairo-only：剥离 libcairo 归因行后若仍有 WARNING/ERROR 则真失败
    # set -euo pipefail 下 grep -vE 空匹配 exit 1 会 abort，故 || true
    non_cairo_problems="$(echo "$out" | grep -E '^(WARNING|ERROR)' \
      | grep -vE 'cairosvg|no library called.*cairo|cairo-2|libcairo' || true)"
    if [ -z "$non_cairo_problems" ]; then
      echo "--- mkdocs: libcairo-only warnings tolerated (§9 out-of-scope) ---"
    else
      echo "$non_cairo_problems"; exit 1
    fi
  fi
fi

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

# 8. Contract sync idempotency (ci.yml contract-sync job)
echo "--- contract-sync idempotency ---"
uv run shenbi-sync-contracts >/dev/null
git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/

# 9. Auto-check docs idempotency
echo "--- autocheck-docs idempotency ---"
uv run python tools/generate_autocheck_docs.py >/dev/null
git diff --exit-code -- skills/

echo "=== pre-push: all checks passed ==="
