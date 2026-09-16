"""C26 / F1031+F1032 (spec #64): every parameterized justfile recipe must pass
arguments as literal argv entries — no shell re-parsing of interpolated values.

Mechanism: a fake ``uv`` is prepended to PATH (stubbing ``pipeline`` or
``shenbi-dispatch`` themselves is useless — ``uv run`` prepends the project
venv bin to PATH, shadowing them). The stub records every invocation's argv
to $STUB_UV_OUT. A recipe body that textually interpolates ``{{param}}``
unquoted lets ``;``-style payloads execute in the recipe shell (marker file
appears) and word-splits the payload; the positional-arguments pattern
(``"$1"`` / ``"${@:4}"``) delivers them inert.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Six sample classes from the spec (T1.3). Marker variants prove zero
# execution; the payload string itself must arrive as ONE argv entry.
MARKER = "pwned-by-just-recipe"
SAMPLES = [
    f"p; touch {MARKER}",
    "p$(touch pwned-cmdsub)",
    "p`touch pwned-backtick`",
    "it's quoted",
    'say "hello world"',
    "中文提示词 空格",
]

STUB = """#!/usr/bin/env bash
printf '%s\\n' "$@" >> "${STUB_UV_OUT:?}"
[ -z "${STUB_UV_CANNED:-}" ] || cat "${STUB_UV_CANNED}"
exit 0
"""


def make_uv_stub(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    (bin_dir / "uv").write_text(STUB, encoding="utf-8")
    (bin_dir / "uv").chmod(0o755)
    return bin_dir


def run_just(env_extra: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_extra)
    return subprocess.run(
        ["just", *args], capture_output=True, text=True, timeout=60, cwd=REPO_ROOT, env=env
    )


def stub_lines(tmp_path: Path) -> list[str]:
    out = tmp_path / "uv.args"
    return out.read_text(encoding="utf-8").splitlines()


# Mechanical derivation (spec T1.3): parse the justfile for recipe headers
# that declare parameters — a hand-maintained list would let new recipes
# escape the matrix.
def parameterized_recipes() -> dict[str, list[str]]:
    text = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
    recipes: dict[str, list[str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        # Recipe headers are column-0 in this justfile; indented lines are
        # recipe bodies (whose `=`/`:` flags would misfire the header regex).
        if not stripped or line[:1].isspace() or stripped.startswith(("#", "@", "-", "set ")):
            continue
        candidate = stripped.rstrip(":")
        if ":" not in stripped or " " not in candidate:
            continue
        name, _, params = candidate.partition(" ")
        if not name or not params or "{{" in line:
            continue
        if not name.replace("-", "").isalnum() or name[0].isdigit():
            continue
        # Header (ends with ':') whose parameter list is non-empty
        if stripped.endswith(":") or "=" in params:
            recipes[name] = []
    return recipes


EXPECTED_CALLS: dict[str, list[list[str]]] = {
    # recipe -> per-sample argument vectors (payload placed at the natural-
    # language position). All of these route through `uv`, so the stub
    # intercepts every one — no side effects, no LLM.
    "install": [["dev"], ["dev; touch pwned"]],
    "test": [["-q"]],
    "test-all": [["-q"]],
    "test-file": [["tests/test x.py"]],
    "audit-lint": [["--help"]],
    "gate": [["G0"], ["G0; touch pwned"]],
    "dispatch": [["shenbi-x", "generative", "/tmp/r", "p; touch pwned-by-just-recipe"]],
    "pipeline-init": [
        ["seed.md"],
        ["seed.md", "/tmp/dir with space", "--auto"],
    ],
    "pipeline-status": [["/tmp/dir; touch pwned"]],
    "pipeline-review": [
        ["/tmp/d", "approve", "needs work; fix it"],
    ],
    "pipeline-resume": [["/tmp/dir $(touch pwned-cmdsub)"]],
}


@pytest.mark.unit
def test_matrix_all_parameterized_recipes_pass_literals(tmp_path: Path) -> None:
    """Every recipe in EXPECTED_CALLS delivers payloads as literal argv."""
    bin_dir = make_uv_stub(tmp_path)
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "STUB_UV_OUT": str(tmp_path / "uv.args"),
    }
    for recipe, calls in EXPECTED_CALLS.items():
        for call in calls:
            proc = run_just(env, recipe, *call)
            assert proc.returncode == 0, f"{recipe} {call}: {proc.stderr}"

    # Six-class matrix (spec T1.3) through the two natural-language
    # positions: the dispatch prompt (F1031) and the pipeline-review
    # free-form feedback (F1032). Each sample must arrive as ONE argv
    # entry, and no sample may execute anything.
    for sample in SAMPLES:
        for recipe, prefix in (
            ("dispatch", ["shenbi-x", "generative", "/tmp/r"]),
            ("pipeline-review", ["/tmp/d", "approve"]),
        ):
            proc = run_just(env, recipe, *prefix, sample)
            assert proc.returncode == 0, f"{recipe} {sample!r}: {proc.stderr}"
        lines = stub_lines(tmp_path)
        assert sample in lines, f"payload not literal argv: {sample!r}"

    lines = stub_lines(tmp_path)
    # Zero execution: no marker anywhere in the repo root (pwned = the bare
    # `touch pwned` variants used by the install/gate rows).
    for marker in (
        REPO_ROOT / MARKER,
        REPO_ROOT / "pwned-cmdsub",
        REPO_ROOT / "pwned-backtick",
        REPO_ROOT / "pwned",
    ):
        try:
            assert not marker.exists(), f"injection executed: {marker}"
        finally:
            marker.unlink(missing_ok=True)
    # F1031: the `;` payload reaches the stub as ONE argv entry.
    assert "p; touch pwned-by-just-recipe" in lines, "dispatch payload not literal argv"
    # F1032: feedback with spaces/`;` stays one argv entry after --feedback.
    assert "needs work; fix it" in lines
    # F1030/--auto passthrough: `--auto` reaches the pipeline CLI argv.
    assert "--auto" in lines
    # No recipe line word-split the space-containing project dir.
    assert "/tmp/dir with space" in lines


@pytest.mark.unit
def test_matrix_covers_every_parameterized_recipe() -> None:
    """Guard against new parameterized recipes escaping the matrix."""
    expected = set(EXPECTED_CALLS)
    actual = set(parameterized_recipes())
    missing = actual - expected
    assert not missing, f"recipes missing from EXPECTED_CALLS: {missing}"
