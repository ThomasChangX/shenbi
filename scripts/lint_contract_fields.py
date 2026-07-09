#!/usr/bin/env python3
"""Lint: contract.reads field declarations vs truth file actual headings/keys.

Scans all skills' contract.reads dict-form fields, resolves each declared file
to a representative on-disk sample (parametric paths via glob; runtime-only
truth files via the ``tests/fixtures`` example fixtures), and reports any
declared field that does not appear as an actual H2 heading (markdown) or
top-level key (JSON). Hooked into ``just check`` via ``just lint-contracts``.

Design notes (spec B.5):
- Truth files like ``plans/chapter-N-plan.md`` are runtime-generated and never
  exist at repo root. They are represented in-repo by example fixtures such as
  ``tests/fixtures/chapter-plan-example.md``. The lint resolves a declared path
  to the most representative available sample and skips paths with no sample
  (WARN-only: a missing sample is not a field-name drift).
- Matching uses the UNIFIED matcher ``shenbi.contracts.fields.match_field``
  (Task 2): strip + fold ASCII whitespace AND U+3000 to a single ASCII space;
  does NOT lowercase (preserves CJK heading semantics). This keeps the lint and
  the runtime field filter (``filter_to_fields``) identical, so any drift the
  lint flags would also be a runtime WARN/FAIL. A declared field that no actual
  heading/key matches is a contract drift -> exit 1 (FAIL, blocks PR).
"""

from __future__ import annotations

import glob as globmod
import json
import sys
from pathlib import Path
from typing import Any

import yaml

# Make the in-tree ``shenbi`` package importable regardless of CWD/invocation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shenbi.contracts.fields import match_field

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
PROJECT_DIR = REPO_ROOT  # truth files live under project root at runtime
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"

# Frontmatter is delimited by "---": a leading "---\n...\n---" yields 3 split parts
# (empty-string before the first delimiter, the body, then the remainder).
_FRONTMATTER_PARTS = 3

# Representative example fixtures for runtime-only truth files.
# Keyed by the declared contract path (parametric form). Values are searched
# in order; the first existing file is used as the sample. ``None`` entries are
# documented no-sample paths (skipped without warning).
EXAMPLE_FIXTURES: dict[str, list[Path] | None] = {
    "plans/chapter-N-plan.md": [FIXTURES_DIR / "chapter-plan-example.md"],
    "style/style_profile.md": [FIXTURES_DIR / "style-profile-example.md"],
    "genre-config.json": [FIXTURES_DIR / "genre-config-example.json"],
    "novel.json": [FIXTURES_DIR / "novel-example.json"],
    "chapters/chapter-N.md": [
        FIXTURES_DIR / "chapter-draft-example.md",
        FIXTURES_DIR / "chapter-8-example.md",
    ],
    "truth/book_spine.md": [FIXTURES_DIR / "book-spine-example.md"],
    "truth/book_strata.md": [FIXTURES_DIR / "book-strata-example.md"],
    "truth/volume_summaries.md": [FIXTURES_DIR / "volume-summary-example.md"],
    "truth/arcs/arc-N.md": [FIXTURES_DIR / "arc-example.md"],
    "truth/current_state.md": [
        FIXTURES_DIR / "snapshots" / "chapter-025" / "truth" / "current_state.md",
        FIXTURES_DIR / "truth-current_state.md",
    ],
    "truth/pending_hooks.md": [
        FIXTURES_DIR / "snapshots" / "chapter-025" / "truth" / "pending_hooks.md",
        FIXTURES_DIR / "truth-pending_hooks.md",
    ],
    "truth/chapter_summaries.md": [
        FIXTURES_DIR / "snapshots" / "chapter-025" / "truth" / "chapter_summaries.md",
        FIXTURES_DIR / "chapter-summaries-example.md",
        FIXTURES_DIR / "truth-chapter_summaries.md",
    ],
    "truth/character_matrix.md": [
        FIXTURES_DIR / "snapshots" / "chapter-025" / "truth" / "character_matrix.md",
        FIXTURES_DIR / "truth-character_matrix.md",
    ],
    # Runtime-only, no representative fixture yet -> skipped (not a drift).
    "outline/volume_map.md": None,
}


def extract_headings_md(text: str) -> set[str]:
    """Extract raw H2 headings (``## Foo``) from markdown (post-``## ``)."""
    headings: set[str] = set()
    for line in text.splitlines():
        if line.startswith("## "):
            headings.add(line[3:].strip())
    return headings


def extract_keys_json(text: str) -> set[str]:
    """Extract raw top-level keys from a JSON object."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    if isinstance(data, dict):
        return set(data)
    return set()


def _field_unmatched(declared: str, actual: set[str]) -> bool:
    """True if no actual heading/key matches ``declared`` via ``match_field``."""
    return not any(match_field(declared, h) for h in actual)


def resolve_sample(path: str) -> Path | None:
    """Resolve a declared (possibly parametric/runtime) path to an on-disk sample.

    Order of preference:
      1. The literal file under the project root (concrete, on-disk truth file).
      2. A curated example fixture (see ``EXAMPLE_FIXTURES``).
      3. A glob-resolved sample for parametric paths (``N``/``NNN`` -> ``*``).

    Returns ``None`` when no representative sample exists (caller skips it).
    """
    # 1. Concrete file at project root.
    literal = PROJECT_DIR / path
    if literal.is_file():
        return literal

    # 2. Curated example fixture.
    if path in EXAMPLE_FIXTURES:
        candidates = EXAMPLE_FIXTURES[path]
        if candidates is None:
            return None  # documented no-sample path
        for cand in candidates:
            if cand.is_file():
                return cand
        return None

    # 3. Parametric glob resolution (e.g. chapters/chapter-N-decisions.json).
    pattern = path.replace("NNN", "*").replace("N", "*")
    matches = sorted(globmod.glob(str(PROJECT_DIR / pattern)))
    if matches:
        return Path(matches[0])

    return None


def _parse_contract(skill_md: Path) -> dict[str, Any] | None:
    """Return the parsed ``contract`` mapping from a SKILL.md, or ``None``."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < _FRONTMATTER_PARTS:
        return None
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _check_read_item(skill_name: str, item: object) -> str | None:
    """Check one reads entry; return an issue string or ``None`` if clean."""
    issue: str | None = None
    if not (isinstance(item, dict) and isinstance(item.get("file"), str)):
        return None
    path: str = item["file"]
    fields = item.get("fields")
    if not fields:
        return None
    if not isinstance(fields, list):
        kind = type(fields).__name__
        return f"{skill_name}: {path} has non-list 'fields' ({kind})"

    sample = resolve_sample(path)
    # No representative sample on disk, or unsupported file type -> not a drift.
    if sample is not None:
        actual = _extract_actual(path, sample)
        if actual is not None:
            declared = [f for f in fields if isinstance(f, str)]
            missing = [f for f in declared if _field_unmatched(f, actual)]
            if missing:
                preview = ", ".join(sorted(actual)[:10]) or "(none)"
                rel = sample.relative_to(REPO_ROOT)
                issue = (
                    f"{skill_name}: {path} declares fields {sorted(missing)} "
                    f"not found in {rel} (actual: {preview})"
                )
    return issue


def _extract_actual(path: str, sample: Path) -> set[str] | None:
    """Extract actual headings (md) or keys (json); ``None`` if unsupported type."""
    content = sample.read_text(encoding="utf-8")
    if path.endswith(".md") or sample.suffix == ".md":
        return extract_headings_md(content)
    if path.endswith(".json") or sample.suffix == ".json":
        return extract_keys_json(content)
    return None


def lint_skill(skill_dir: Path) -> list[str]:
    """Check one skill's contract reads fields against representative samples."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return []

    data = _parse_contract(skill_md)
    if data is None:
        return []

    contract = data.get("contract", {})
    if not isinstance(contract, dict):
        return []
    reads = contract.get("reads", [])
    if not isinstance(reads, list):
        return []

    issues: list[str] = []
    for item in reads:
        issue = _check_read_item(skill_dir.name, item)
        if issue is not None:
            issues.append(issue)
    return issues


def main() -> int:
    """Run the lint over all skills; exit non-zero if any mismatch is found."""
    all_issues: list[str] = []
    if SKILLS_DIR.is_dir():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                all_issues.extend(lint_skill(skill_dir))

    if all_issues:
        print("Contract field mismatches found:", file=sys.stderr)
        for issue in all_issues:
            print(f"  {issue}", file=sys.stderr)
        return 1
    print("All contract field declarations match truth files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
