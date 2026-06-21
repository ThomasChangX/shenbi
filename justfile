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

# Lint bare status strings (spec D3)
lint-status:
	uv run python tools/lint_status_strings.py

# Regenerate contract-derived artifacts (deps.json expected_outputs, DAG, index, body views)
generate:
	uv run shenbi-sync-contracts

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
    rm -rf tests/coverage/ site/ .cache/
    rm -rf .pytest_cache .ruff_cache .mypy_cache .basedpyright_cache

# Pre-commit run on all files
precommit:
    uv run pre-commit run --all-files

# Mutation testing
mutate:
    uv run mutmut run --use-cache

# Compare mutation score to baseline
mutate-check:
    @test -f tools/compare_mutation_score.py && test -f tests/baselines/mutation-score.txt \
      || { echo 'mutate-check requires Plan 2 (tools/compare_mutation_score.py + tests/baselines/mutation-score.txt)'; exit 1; }
    uv run python tools/compare_mutation_score.py --baseline tests/baselines/mutation-score.txt

# Generate changelog from conventional commits
changelog:
    uv run git-cliff --unreleased -p CHANGELOG.md
