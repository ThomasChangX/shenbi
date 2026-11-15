"""spec #92 T4: pre-push hook is a constructive subset of just check faces.

Asserts: (1) hook invokes the just sub-recipes (not hand-copied tool lines),
(2) no copy of the retired --cov-fail-under flag anywhere in the hook,
(3) the documented exception faces appear in the hook and are absent from
justfile.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = (REPO / "tools" / "pre-push-check.sh").read_text(encoding="utf-8")
JUST = (REPO / "justfile").read_text(encoding="utf-8")


def test_hook_calls_just_recipes() -> None:
    for recipe in ("lint", "type", "test-ci"):
        assert re.search(rf"^\s*just {recipe}\s*$", HOOK, re.M), f"hook missing call: just {recipe}"


def test_hook_has_no_copied_threshold_flag() -> None:
    assert "--cov-fail-under" not in HOOK


def test_exception_faces_are_hook_only() -> None:
    # "mkdocs build --strict" (not bare "mkdocs" — justfile's docs: serve
    # recipe legitimately contains that word)
    for face in ("pip-audit", "mkdocs build --strict", "dead code check"):
        assert face in HOOK
        assert face not in JUST, f"{face} leaked into justfile"
    # pip-audit/mkdocs/dead-code are hook(+CI security.yml)-only by design (spec exception table)


def test_justfile_has_sub_recipes() -> None:
    for recipe in ("^lint:", "^type:", "^test-ci:"):
        assert re.search(recipe, JUST, re.M), f"justfile missing recipe {recipe!r}"
