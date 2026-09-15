#!/usr/bin/env bash
# Pre-push fast pre-flight — a SUBSET of the CI gates. The authority is
# `just check` (spec #63 C25); this hook adds push-time ergonomics only.
# Install: pre-commit install --hook-type pre-push
set -euo pipefail

echo "=== pre-push: fast pre-flight (full gates: just check) ==="

# 1. Lockfile integrity (just check line 1)
echo "--- uv lock --check ---"
uv lock --check

# 2. Ruff lint + format (just check ruff lines)
echo "--- ruff check ---"
uv run ruff check .
echo "--- ruff format --check ---"
uv run ruff format --check .

# 3. Type checking (just check mypy/basedpyright lines)
echo "--- mypy ---"
uv run mypy src/shenbi/
echo "--- basedpyright ---"
uv run basedpyright || { echo "basedpyright failed"; exit 1; }

# 4. Custom linters (subset of just check lint lines)
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

# 4b. Security audit (security workflow; not in just check)
echo "--- pip-audit (uv.lock full set, mirroring CI security.yml — spec #41 R1) ---"
uv export --frozen --all-groups --all-extras --no-emit-project -o /tmp/req-audit.txt
uv run pip-audit -r /tmp/req-audit.txt --no-deps --disable-pip

# 4c. mkdocs link check (only when docs changes)
# 触发：检测待 push 的 docs 变更。pre-push 阶段已 commit，--cached 和 HEAD diff 都恒空，
#   正确 idiom 是 main...HEAD（推送范围）。
if ! git merge-base main HEAD >/dev/null 2>&1; then
  echo "pre-push: cannot resolve main...HEAD (shallow clone?); skipping mkdocs gate explicitly" >&2
elif changed="$(git diff --name-only main...HEAD)" && grep -qE '^(docs/|mkdocs\.yml)' <<<"$changed"; then
  echo "--- mkdocs link check (docs changed) ---"
  uv sync --frozen --group docs >/dev/null
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
  uv sync --frozen --group dev >/dev/null  # restore dev env for subsequent pytest/mypy/ruff
fi

# 5. Tests (just check pytest lines, flag-aligned)
# --dist loadscope groups tests by module so ThreadPoolExecutor tests
# don't interfere across modules. --timeout prevents indefinite hangs.
echo "--- pytest (with coverage >= 85%) ---"
uv run pytest -n auto --dist loadscope -m "not last" --cov=shenbi --cov-branch --cov-report=xml:tests/coverage/coverage.xml --cov-report=term-missing --cov-fail-under=85 --timeout=120

# 6. Dead code detection
echo "--- dead code check (reportUnusedFunction) ---"
# set -euo pipefail 下命令替换继承 pipefail：零命中 grep 退 1 会崩整钩（F1036），故 || true 守卫
UNUSED_COUNT=$( { grep -r 'reportUnusedFunction' src/shenbi/ --include='*.py' | grep -v test_ | grep -v __pycache__ || true; } | wc -l | tr -d ' ')
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

# 8. Contract sync idempotency (just check codegen idempotency)
echo "--- contract-sync idempotency ---"
uv run shenbi-sync-contracts >/dev/null
git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/ .codex-plugin/

# 9. Auto-check docs idempotency
echo "--- autocheck-docs idempotency ---"
uv run python tools/generate_autocheck_docs.py >/dev/null
git diff --exit-code -- skills/

echo "=== pre-push: all checks passed ==="
