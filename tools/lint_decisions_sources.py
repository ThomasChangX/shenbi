"""Three-source decisions-declaration reconciliation (spec #30 T4, T106/F439).

Every skill that produces a decisions sidecar must be declared consistently in:
  1. docs/framework/decisions-schema.md   (Per-Skill Differences table)
  2. docs/framework/truth-files.yaml      (kind: decisions entries)
  3. skills/<skill>/SKILL.md              (contract writes containing "decisions")

Spec #90 T3: the retired hand-rolled YAML walk is replaced by load_contract
(new write-semantics keys silently broke the scan; malformed functional
contracts now raise here — a deliberate fail-loud side-sentry). STEM_TO_SKILL
is derived from the contracts (strict {N}/{N+1}→N normalization, ambiguity =
exit 1). A value-set face reconciles decisions-schema.md enums against
contracts/schemas/decisions.py Literals, and a fourth face reconciles the
derived producers against G4_DECISIONS_WIRED (generic.py).

Exit 0 = all sources agree; exit 1 = drift report on stdout.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from shenbi.contracts.loader import load_contract  # noqa: E402
from tools.lint_contracts import META_SKILLS  # noqa: E402 — lint_contract_prose.py:48 precedent

SKILLS = REPO / "skills"
TRUTH_FILES = REPO / "docs" / "framework" / "truth-files.yaml"
SCHEMA_DOC = REPO / "docs" / "framework" / "decisions-schema.md"
DECISIONS_PY = REPO / "src" / "shenbi" / "contracts" / "schemas" / "decisions.py"
GENERIC_PY = REPO / "src" / "shenbi" / "gates" / "g4" / "generic.py"


def _skill_names_from_writes() -> set[str]:
    """Skills whose contract writes/updates declare a *decisions*.json output.

    Spec #90 T3: load_contract replaces the retired hand-rolled YAML walk.
    Malformed functional contracts raise here — a deliberate fail-loud
    side-sentry, not accidental coupling.
    """
    result: set[str] = set()
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        skill_dir = skill_md.parent.name
        if skill_dir in META_SKILLS:
            continue  # meta skills carry no contract block (loader would raise)
        contract = load_contract(skill_dir)
        if any(p.endswith("-decisions.json") for p in (*contract["writes"], *contract["updates"])):
            result.add(skill_dir.removeprefix("shenbi-"))
    return result


# `chapter-{N+1}-decisions.json` and `chapter-N-decisions.json` normalize to the
# same stem; bare N (fnmatch digit glob) is already the normalized form.
_NORM = re.compile(r"\{N\+1\}|\{N\}|(?<![A-Za-z-])N(?![A-Za-z-])")


def _normalize_pattern(path: str) -> str:
    return _NORM.sub("N", path)


def derive_stem_to_skill() -> dict[str, str]:
    """Derive stem→skill mapping from contracts (spec #90 T3; ambiguity = exit 1)."""
    mapping: dict[str, str] = {}
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        skill_dir = skill_md.parent.name
        if skill_dir in META_SKILLS:
            continue
        contract = load_contract(skill_dir)
        for p in (*contract["writes"], *contract["updates"]):
            if p.endswith("-decisions.json"):
                stem = Path(_normalize_pattern(p)).stem
                short = skill_dir.removeprefix("shenbi-")
                if stem in mapping and mapping[stem] != short:
                    print(
                        f"lint_decisions_sources: ambiguous decisions stem '{stem}' "
                        f"claimed by {mapping[stem]} and {short} — tighten patterns"
                    )
                    sys.exit(1)
                mapping[stem] = short
    return mapping


def _truth_file_skills() -> set[str]:
    text = TRUTH_FILES.read_text(encoding="utf-8")
    entries = re.findall(r"name:\s*([\w\-/{}.]+decisions\.json),\s*kind:\s*decisions", text)
    derived = derive_stem_to_skill()
    skills = set()
    for path in entries:
        stem = Path(path).stem
        skill = derived.get(stem)
        if skill is None:
            print(
                f"lint_decisions_sources: unmapped decisions file '{path}' — "
                "no contract declares this stem"
            )
            sys.exit(1)
        skills.add(skill)
    return skills


def _schema_doc_skills() -> set[str]:
    text = SCHEMA_DOC.read_text(encoding="utf-8")
    m = re.search(r"## Per-Skill Differences.*?\n(\|.*\n)+", text, re.DOTALL)
    if not m:
        return set()
    return {row.strip("` ") for row in re.findall(r"\|\s*`([\w\-]+)`\s*\|", m.group(0))}


def _value_set_face() -> list[str]:
    """Spec #90 T3: decisions-schema.md enums == contracts/schemas/decisions.py Literals."""
    import re as _re  # noqa: PLC0415 — lint_registry_reconcile precedent

    schema_src = DECISIONS_PY.read_text(encoding="utf-8")
    doc_src = SCHEMA_DOC.read_text(encoding="utf-8")
    errs: list[str] = []
    for lit_name, section in [
        ("Handling", "adjustments[].handling"),
        ("SeverityLevel", "selections[].severity"),
        ("Basis", "selections[].basis"),
        ("Trim", "budget.trim_applied"),
    ]:
        m = _re.search(rf"^{lit_name} = Literal\[(.*?)\]", schema_src, _re.MULTILINE | _re.DOTALL)
        code_vals = set(_re.findall(r'"([\w]+)"', m.group(1))) if m else set()
        # Section headers contain [] — re.escape is mandatory. Boundary must stop
        # at both ### and ## level headings. NOTE: this is an f-string — the
        # brace quantifier MUST be doubled ({{2,3}}) or it becomes a replacement
        # field (plan review round-2 R2).
        doc_sec = _re.search(
            rf"### `{_re.escape(section)}`(.*?)(?=\n#{{2,3}} |\Z)",
            doc_src,
            _re.DOTALL,
        )
        doc_vals = set(_re.findall(r"`([\w]+)`", doc_sec.group(1))) if doc_sec else set()
        if code_vals != doc_vals:
            errs.append(f"value-set: {lit_name} code={sorted(code_vals)} doc={sorted(doc_vals)}")
    return errs


def _wired_face(producers: set[str]) -> list[str]:
    """Spec #90 T3: derived producers == G4_DECISIONS_WIRED (generic.py)."""
    import ast  # noqa: PLC0415 — tools/ scope enforces it (plan review round-3)

    generic_src = GENERIC_PY.read_text(encoding="utf-8")
    tree = ast.parse(generic_src)
    wired: set[str] | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and getattr(node.target, "id", "") == "G4_DECISIONS_WIRED"
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.args[0], (ast.Set, ast.List))
        ):
            wired = {
                el.value
                for el in node.value.args[0].elts
                if isinstance(el, ast.Constant) and isinstance(el.value, str)
            }
    if wired is None:
        return ["G4_DECISIONS_WIRED: extraction-empty: literal not found"]
    wired_short = {w.removeprefix("shenbi-") for w in wired}
    if wired_short != producers:
        return [f"G4_DECISIONS_WIRED: wired={sorted(wired_short)} producers={sorted(producers)}"]
    return []


def main() -> int:
    """Reconcile the decisions-declaration sources; exit 1 on drift."""
    writes = _skill_names_from_writes()
    truth = _truth_file_skills()
    doc = _schema_doc_skills()
    drift = False
    for label, a, b in [
        ("SKILL-writes", writes, truth),
        ("truth-files", truth, writes),
        ("SKILL-writes", writes, doc),
        ("schema-doc", doc, writes),
        ("truth-files", truth, doc),
        ("schema-doc", doc, truth),
    ]:
        missing = a - b
        if missing:
            drift = True
            print(f"{label} declares {sorted(missing)} but counterpart does not")
    errs = _value_set_face() + _wired_face(writes)
    if errs:
        drift = True
        print("\n".join(errs))
    if not drift:
        print(f"lint_decisions_sources: OK ({len(writes)} producers aligned across 3 sources)")
        return 0
    print(f"  writes={sorted(writes)}\n  truth={sorted(truth)}\n  doc={sorted(doc)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
