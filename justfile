# Run from project root
set dotenv-load := true
set positional-arguments := true

# Recipe-authoring covenant (spec #64 C26 / F1031): recipes taking
# natural-language or flag-value parameters MUST NOT interpolate {{param}}
# into the shell line (just substitutes textually BEFORE the shell parses,
# so `;`/`$()` in the value execute). Use positional references ("$1",
# "${@:N}") — see tests/test_justfile_injection.py. `${@:N}` is bash-only,
# hence the explicit bash shell below (dash would abort: Bad substitution).
set shell := ["bash", "-cu"]

# Default: show available recipes
default:
    @just --list

# Install dependencies (dev group by default)
install group="dev":
    uv sync --group "$1"

# Run all checks (single source of truth — CI calls this; see spec #63 C25)
check:
    uv lock --check
    uv run python tools/lint_status_strings.py
    uv run python tools/lint_routing_faces.py
    uv run python tools/audit-skill-descriptions.py
    uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume
    uv run python tools/lint_bare_writes.py
    uv run python tools/lint_bare_subprocess_json.py
    uv run python tools/check_severity_vocab.py
    uv run python tools/lint_repo_consistency.py
    uv run python tools/lint_key_reconciliation.py --strict
    uv run python tools/lint_decisions_sources.py
    uv run python tools/lint_helper_usage.py
    uv run python tools/lint_threshold_reconciliation.py
    uv run python tools/lint_dead_code_allowlist.py
    uv run python tools/lint_audit_run.py
    uv run python tools/lint_artifact_contamination.py
    uv run python tools/count_active_specs.py
    uv run python tools/check_fixture_mirror.py
    uv run python tools/lint_no_forbid_with_computed_field.py src/shenbi/contracts
    uv run python tools/lint_no_fs_mutation.py src/shenbi
    just lint-contracts
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src/shenbi/
    uv run basedpyright
    uv run shellcheck run_pipeline.sh tools/pre-push-check.sh tests/round-exec.sh tests/lock-tool-hashes.sh tests/test-gates.sh
    uv run shenbi-sync-contracts >/dev/null
    uv run python tools/generate_autocheck_docs.py
    uv run shenbi-generate-plugins
    git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/ .codex-plugin/
    uv run pytest -n auto --dist loadscope -m "not last" --hypothesis-profile=ci --timeout=120 --cov=shenbi --cov-branch --cov-report=json:coverage.json --cov-report=xml:tests/coverage/coverage.xml --cov-report=term-missing --cov-fail-under=85
    uv run python tools/check_module_coverage.py coverage.json
    uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci

# Enforce per-module coverage floors only (spec #53 C15 T3) — self-sufficient:
# runs the suite with a JSON coverage report, then checks tools/module-coverage-floors.json
module-coverage:
    uv run pytest -n auto -m "not last" --cov=shenbi --cov-branch --cov-report=json:coverage.json -q
    uv run python tools/check_module_coverage.py coverage.json

# Run tests only (fast unit tests)
test *args:
    uv run pytest -n auto -m "unit" --no-cov "$@"

# Run tests including integration
test-all *args:
    uv run pytest -n auto -m "not last" --no-cov "$@"

# Run a single test file
test-file file:
    uv run pytest "$1" -v --no-cov

# Fix lint and formatting
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Lint bare status strings (spec D3)
lint-status:
	uv run python tools/lint_status_strings.py

# Lint routing faces: DEPRECATED skills must not be routed anywhere (spec #59 T3)
lint-routing:
	uv run python tools/lint_routing_faces.py

# Lint audit-run artifacts: ledger rows, count reconciliation, carryover (spec #49)
audit-lint *args:
    uv run python tools/lint_audit_run.py "$@"

# Lint contract.reads fields vs truth file headings/keys (spec B.5)
lint-contract-fields:
	uv run python scripts/lint_contract_fields.py

# All contract lints: graph closure (Task 18) + field drift (B.5) + load/completeness (§5.5)
lint-contracts:
	uv run python tools/lint_contract_graph.py
	uv run python scripts/lint_contract_fields.py
	uv run python tools/lint_contracts.py
	uv run python tools/lint_contract_prose.py --fail

# Regenerate contract-derived artifacts (deps.json expected_outputs, DAG, index, body views)
generate:
	uv run shenbi-sync-contracts

# Run gates CLI (e.g., just gate G0 <seed>)
gate name *args:
    uv run shenbi-validate "$1" "${@:2}"

# Dispatch a skill
dispatch skill test_type round_dir *prompt:
    uv run shenbi-dispatch "$1" "$2" "$3" "${@:4}"

# Build docs site
docs:
    uv run mkdocs serve

# Build wheel and sdist
build:
    uv build

# Clean all build artifacts (tracked .gitkeep preserved — spec #63 F1039)
clean:
    rm -rf dist/ build/ src/shenbi.egg-info/
    mkdir -p tests/coverage && find tests/coverage -mindepth 1 ! -name .gitkeep -delete
    rm -rf site/ .cache/
    rm -rf .pytest_cache .ruff_cache .mypy_cache .basedpyright_cache

# Pre-commit run on all files
precommit:
    uv run pre-commit run --all-files

# Generate changelog from conventional commits
changelog:
    uv run git-cliff --unreleased -p CHANGELOG.md

# Initialize a novel pipeline from a seed file
pipeline-init seed project_dir="" *args:
    if [ -n "$2" ]; then uv run pipeline init "$1" --project-dir "$2" "${@:3}"; else uv run pipeline init "$1" "${@:3}"; fi

# Check pipeline status
pipeline-status project_dir:
    uv run pipeline status "$1"

# Submit a checkpoint review
pipeline-review project_dir decision feedback="":
    if [ -n "$3" ]; then uv run pipeline review "$1" "$2" --feedback "$3"; else uv run pipeline review "$1" "$2"; fi

# Resume pipeline execution
pipeline-resume project_dir:
    uv run pipeline resume "$1"
