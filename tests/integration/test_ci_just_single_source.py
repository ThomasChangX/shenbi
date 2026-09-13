"""C25 spec #63 — CI/just single-source structural invariants (acceptance 1/2).

These tests encode the *converged* state. They are RED before Tasks 2-4 land
and GREEN after. They replace the manual grep-diff acceptance with machine-
readable assertions so future drift fails `just check` itself.
"""

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CI = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
JUSTFILE = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
PYPROJECT = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _check_body() -> str:
    return JUSTFILE.split("check:", 1)[1].split("\n\n", 1)[0]


class TestCISingleSource:
    def test_ci_invokes_just_check(self):
        assert "uvx just check" in CI

    def test_ci_has_no_direct_tool_lint_calls(self):
        direct = re.findall(r"uv run python (?:tools|scripts)/lint_\S+", CI)
        assert direct == [], f"ci.yml still dual-lists lints: {direct}"

    def test_ci_no_direct_pytest(self):
        # 唯一豁免：Hypothesis replay statistics 步骤（CI 结构语义，见 Task 3 I1 裁决）
        pytest_calls = re.findall(r"uv run pytest[^\n]*", CI)
        non_exempt = [c for c in pytest_calls if "tests/property" not in c]
        assert non_exempt == [], f"ci.yml still runs pytest outside just check: {non_exempt}"


class TestAddoptsCoverageIsolation:
    def test_global_addopts_have_no_cov(self):
        addopts = PYPROJECT["tool"]["pytest"]["ini_options"]["addopts"]
        cov_flags = [a for a in addopts if a.startswith("--cov")]
        assert cov_flags == [], f"global addopts still carry coverage: {cov_flags}"

    def test_just_test_is_nocov(self):
        pytest_lines = [l.strip() for l in JUSTFILE.splitlines() if "uv run pytest" in l]
        unit_only = [l for l in pytest_lines if '-m "unit"' in l]
        assert unit_only and all("--no-cov" in l for l in unit_only), unit_only


class TestJustfileCheckScope:
    def test_check_includes_lock_and_codegen_idempotency(self):
        check_body = _check_body()
        assert "uv lock --check" in check_body
        assert "generate_autocheck_docs.py" in check_body
        assert "shenbi-generate-plugins" in check_body
        assert ".codex-plugin/" in check_body

    def test_check_runs_fixture_mirror(self):
        assert "check_fixture_mirror.py" in _check_body()

    def test_check_includes_ci_only_lints(self):
        check_body = _check_body()
        assert "lint_no_forbid_with_computed_field.py" in check_body
        assert "lint_no_fs_mutation.py" in check_body

    def test_codex_plugin_tracked(self):
        gi = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".codex-plugin/" not in gi
