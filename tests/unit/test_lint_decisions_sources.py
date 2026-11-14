"""Spec #90 T3: STEM_TO_SKILL derivation + value-set + fourth-source reconciliation."""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
LINT = REPO / "tools" / "lint_decisions_sources.py"


def _load_lint():
    spec = importlib.util.spec_from_file_location("lds", LINT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stem_derivation_matches_hand_table() -> None:
    mod = _load_lint()
    derived = mod.derive_stem_to_skill()
    expected = {
        "chapter-N-context-decisions": "context-composing",
        "market-radar-decisions": "market-radar",
        "chapter-N-decisions": "chapter-drafting",
        "chapter-N-plan-decisions": "chapter-planning",
        "chapter-N-revision-decisions": "chapter-revision",
        "state-settling-decisions": "state-settling",
        "genre-config-decisions": "genre-config",
        "short-N-decisions": "short-drafting",
    }
    assert derived == expected


def test_ambiguous_stem_fails_loud(tmp_path, monkeypatch) -> None:
    """Two skills whose writes normalize to the SAME stem → SystemExit.

    Naive N→* fnmatch would map chapter-N-decisions.json onto
    chapter-N-revision-… as well; strict {N}/{N+1}→N normalization keeps the
    8 mappings unique — any residual ambiguity must fail loudly (spec T3).
    """
    mod = _load_lint()
    import shutil

    fake = tmp_path / "repo"
    shutil.copytree(REPO / "docs", fake / "docs")
    skills = fake / "skills"
    skills.mkdir()
    for name in ("shenbi-fake-one", "shenbi-fake-two"):
        (skills / name).mkdir()
        (skills / name / "SKILL.md").write_text(
            "---\n"
            "name: " + name + "\n"
            "description: structural probe (G0.9 constructed input)\n"
            "contract:\n"
            "  kind: artifact\n"
            "  reads: []\n"
            "  writes:\n"
            "    - chapters/chapter-N-plan-decisions.json\n"
            "  updates: []\n"
            "---\n"
            "# fake\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(mod, "REPO", fake)
    monkeypatch.setattr(mod, "SKILLS", skills)
    monkeypatch.setattr("shenbi.contracts.loader.SKILLS", skills)
    with pytest.raises(SystemExit):
        mod.derive_stem_to_skill()


def test_value_set_drift_red(tmp_path, monkeypatch) -> None:
    """AC4: adding one Handling value to the pydantic model → value-set face red."""
    import shutil

    mod = _load_lint()
    # Shadow REPO with a tmp copy carrying an extra Handling value.
    fake = tmp_path / "repo"
    (fake / "src/shenbi/contracts/schemas").mkdir(parents=True)
    shutil.copytree(REPO / "docs", fake / "docs")
    schemas = (REPO / "src/shenbi/contracts/schemas/decisions.py").read_text(encoding="utf-8")
    schemas_drift = schemas.replace(
        'Handling = Literal["compensate_via_pacing", "explicit_callout", "defer_to_next_chapter", "ignore"]',
        "Handling = Literal["
        '"compensate_via_pacing", "explicit_callout", "defer_to_next_chapter", "ignore", "extra_probe"]',
        1,
    )
    assert schemas_drift != schemas, "anchor string drifted — recalibrate"
    (fake / "src/shenbi/contracts/schemas/decisions.py").write_text(schemas_drift, encoding="utf-8")
    monkeypatch.setattr(mod, "REPO", fake)
    monkeypatch.setattr(mod, "DECISIONS_PY", fake / "src/shenbi/contracts/schemas/decisions.py")
    monkeypatch.setattr(mod, "SCHEMA_DOC", fake / "docs/framework/decisions-schema.md")
    errs = mod._value_set_face()
    assert any("Handling" in e and "extra_probe" in e for e in errs), errs


def test_no_own_frontmatter_parser() -> None:
    """AC3: the lint must not carry its own frontmatter parsing (load_contract instead).

    AST-level assertion per spec ruling — a bare text grep on a keyword is NOT
    sufficient (deleting a comment must not be what passes this check).
    """
    import ast

    src = LINT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(
        (
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "_skill_names_from_writes"
        ),
        None,
    )
    assert fn is not None
    call_names = {
        getattr(c.func, "attr", getattr(c.func, "id", ""))
        for c in ast.walk(fn)
        if isinstance(c, ast.Call)
    }
    assert not ({"search", "match", "findall"} & call_names), (
        "must delegate parsing to load_contract"
    )
    assert "load_contract" in src
