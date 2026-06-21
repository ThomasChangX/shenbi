#!/usr/bin/env python3
"""One-time migrator (spec §7.2): body 数据契约 -> frontmatter contract.

Reads the per-skill CLASSIFICATION table below, rewrites each SKILL.md's
frontmatter to add the `contract:` block, and strips the hand-written body
数据契约 block. Idempotent: re-running on already-migrated skills is a no-op.

Run once:  uv run python tools/migrate_contract_to_frontmatter.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"

# (kind, reads, writes, updates) — the authoritative table from Task 12 Step 1.
# Empty list = []. All paths MUST exist in truth-files.yaml (load_contract enforces).
CLASSIFICATION: dict[str, dict[str, object]] = {
    "shenbi-chapter-drafting": {
        "kind": "artifact",
        "reads": [
            "plans/chapter-N-plan.md",
            "style/style_profile.md",
            "genre-config.json",
            "truth/audit_drift.md",
        ],
        "writes": ["chapters/chapter-N.md"],
        "updates": [],
    },
    "shenbi-chapter-planning": {
        "kind": "artifact",
        "reads": [
            "truth/current_state.md",
            "truth/pending_hooks.md",
            "truth/chapter_summaries.md",
            "outline/volume_map.md",
            "outline/story_frame.md",
            "truth/current_focus.md",
            "truth/author_intent.md",
        ],
        "writes": ["plans/chapter-N-plan.md"],
        "updates": [],
    },
    "shenbi-chapter-revision": {
        "kind": "artifact",
        "reads": ["chapters/chapter-N.md", "audits/chapter-N-*.md"],
        "writes": [],
        "updates": ["chapters/chapter-N.md"],
    },
    "shenbi-anti-detect": {
        "kind": "artifact",
        "reads": ["chapters/chapter-N.md", "genre-config.json"],
        "writes": [],
        "updates": ["chapters/chapter-N.md"],
    },
    "shenbi-length-normalizing": {
        "kind": "artifact",
        "reads": ["chapters/chapter-N.md", "novel.json"],
        "writes": [],
        "updates": ["chapters/chapter-N.md"],
    },
    "shenbi-style-polishing": {
        "kind": "artifact",
        "reads": ["chapters/chapter-N.md", "genre-config.json", "style/style_profile.md"],
        "writes": [],
        "updates": ["chapters/chapter-N.md"],
    },
    "shenbi-character-design": {
        "kind": "artifact",
        "reads": ["world/story_bible.md", "world/rules.md"],
        "writes": [
            "characters/protagonist.md",
            "characters/major/*.md",
            "characters/minor/*.md",
            "characters/relationships.md",
        ],
        "updates": [],
    },
    "shenbi-character-extraction": {
        "kind": "artifact",
        "reads": [
            "import/analysis/02_characters.md",
            "chapters/*.md",
            "import/analysis/04_plot.md",
        ],
        "writes": [
            "characters/protagonist.md",
            "characters/major/*.md",
            "characters/minor/*.md",
            "characters/relationships.md",
        ],
        "updates": [],
    },
    "shenbi-worldbuilding": {
        "kind": "artifact",
        "reads": ["novel.json"],
        "writes": [
            "novel.json",
            "genre-config.json",
            "world/story_bible.md",
            "world/rules.md",
            "world/locations.md",
            "truth/*.md",
        ],
        "updates": [],
    },
    "shenbi-world-extraction": {
        "kind": "artifact",
        "reads": ["import/analysis/03_world.md", "chapters/*.md", "import/analysis/04_plot.md"],
        "writes": [
            "world/story_bible.md",
            "world/rules.md",
            "world/locations.md",
            "world/factions.md",
            "world/power_system.md",
        ],
        "updates": [],
    },
    "shenbi-story-architecture": {
        "kind": "artifact",
        "reads": ["world/story_bible.md", "characters/**/*.md"],
        "writes": [
            "outline/story_frame.md",
            "outline/volume_map.md",
            "outline/rhythm_principles.md",
        ],
        "updates": [],
    },
    "shenbi-style-learning": {
        "kind": "artifact",
        "reads": ["chapters/*.md", "import/source/*.txt"],
        "writes": ["style/style_profile.md"],
        "updates": [],
    },
    "shenbi-short-outline": {
        "kind": "artifact",
        "reads": ["novel.json", "truth/author_intent.md", "outline/story_frame.md"],
        "writes": ["outline/short_story_map.md"],
        "updates": [],
    },
    "shenbi-short-drafting": {
        "kind": "artifact",
        "reads": [
            "outline/short_story_map.md",
            "truth/author_intent.md",
            "genre-config.json",
            "style/style_profile.md",
        ],
        "writes": ["chapters/chapter-N.md"],
        "updates": [],
    },
    "shenbi-short-packaging": {
        "kind": "artifact",
        "reads": [
            "outline/short_story_map.md",
            "chapters/*.md",
            "world/story_bible.md",
            "truth/author_intent.md",
        ],
        "writes": ["import/packaging/*"],
        "updates": [],
    },
    "shenbi-import-analysis": {
        "kind": "artifact",
        "reads": ["import/source/*.txt"],
        "writes": ["import/analysis/*.md"],
        "updates": [],
    },
    "shenbi-canon-import": {
        "kind": "artifact",
        "reads": ["source_canon/*"],
        "writes": ["import/canon/*.md"],
        "updates": [],
    },
    "shenbi-snapshot-manage": {
        "kind": "artifact",
        "reads": ["truth/*.md", "chapters/chapter-N.md", "characters/**/*.md"],
        "writes": ["snapshots/chapter-NNN/*"],
        "updates": [],
    },
    "shenbi-volume-consolidation": {
        "kind": "artifact",
        "reads": ["chapters/chapter-N.md", "truth/chapter_summaries.md", "truth/pending_hooks.md"],
        "writes": ["truth/volume_summaries.md"],
        "updates": ["truth/chapter_summaries.md"],
    },
    "shenbi-state-settling": {
        "kind": "artifact",
        "reads": ["chapters/chapter-N.md"],
        "writes": [],
        "updates": [
            "truth/current_state.md",
            "truth/particle_ledger.md",
            "truth/character_matrix.md",
            "truth/emotional_arcs.md",
            "truth/subplot_board.md",
            "truth/pending_hooks.md",
            "truth/chapter_summaries.md",
        ],
    },
    "shenbi-foreshadowing-plant": {
        "kind": "artifact",
        "reads": ["plans/chapter-N-plan.md", "truth/pending_hooks.md", "genre-config.json"],
        "writes": [],
        "updates": ["truth/pending_hooks.md"],
    },
    "shenbi-foreshadowing-track": {
        "kind": "artifact",
        "reads": ["chapters/chapter-N.md", "truth/pending_hooks.md", "truth/chapter_summaries.md"],
        "writes": [],
        "updates": ["truth/pending_hooks.md"],
    },
    "shenbi-foreshadowing-resolve": {
        "kind": "artifact",
        "reads": ["truth/pending_hooks.md", "truth/chapter_summaries.md"],
        "writes": [],
        "updates": ["truth/pending_hooks.md"],
    },
    "shenbi-truth-sync": {
        "kind": "artifact",
        "reads": ["chapters/chapter-N.md", "truth/*.md", "world/*.md", "characters/**/*.md"],
        "writes": [],
        "updates": ["truth/*.md"],
    },
    "shenbi-intent-management": {
        "kind": "artifact",
        "reads": ["truth/author_intent.md", "truth/audit_drift.md"],
        "writes": [],
        "updates": ["truth/author_intent.md", "truth/current_focus.md"],
    },
    "shenbi-faction-builder": {
        "kind": "artifact",
        "reads": [
            "novel.json",
            "world/story_bible.md",
            "world/rules.md",
            "characters/**/*.md",
            "outline/story_frame.md",
        ],
        "writes": [],
        "updates": ["world/factions.md"],
    },
    "shenbi-location-builder": {
        "kind": "artifact",
        "reads": [
            "novel.json",
            "world/story_bible.md",
            "world/rules.md",
            "world/locations.md",
            "outline/story_frame.md",
        ],
        "writes": [],
        "updates": ["world/locations.md"],
    },
    "shenbi-power-system": {
        "kind": "artifact",
        "reads": ["novel.json", "world/story_bible.md", "world/rules.md", "outline/story_frame.md"],
        "writes": [],
        "updates": ["world/power_system.md"],
    },
    "shenbi-pacing-design": {
        "kind": "artifact",
        "reads": [
            "novel.json",
            "outline/story_frame.md",
            "outline/volume_map.md",
            "genre-config.json",
        ],
        "writes": [],
        "updates": ["outline/rhythm_principles.md"],
    },
    "shenbi-plot-thread-weaver": {
        "kind": "artifact",
        "reads": [
            "outline/story_frame.md",
            "outline/volume_map.md",
            "outline/rhythm_principles.md",
            "truth/pending_hooks.md",
        ],
        "writes": [],
        "updates": ["outline/thread_map.md"],
    },
    "shenbi-relationship-map": {
        "kind": "artifact",
        "reads": [
            "characters/**/*.md",
            "characters/relationships.md",
            "truth/character_matrix.md",
            "world/factions.md",
        ],
        "writes": [],
        "updates": ["characters/relationships.md", "truth/character_matrix.md"],
    },
    "shenbi-volume-outlining": {
        "kind": "artifact",
        "reads": ["outline/story_frame.md", "outline/volume_map.md", "truth/author_intent.md"],
        "writes": [],
        "updates": ["outline/volume_map.md"],
    },
    "shenbi-genre-config": {
        "kind": "artifact",
        "reads": ["novel.json", "genre-config.json"],
        "writes": [],
        "updates": ["genre-config.json"],
    },
    "shenbi-sequel-writing": {
        "kind": "artifact",
        "reads": [
            "snapshots/chapter-NNN/*",
            "truth/*.md",
            "outline/volume_map.md",
            "outline/thread_map.md",
        ],
        "writes": ["chapters/chapter-N.md"],
        "updates": ["truth/*.md"],
    },
    "shenbi-context-composing": {
        "kind": "ephemeral",
        "reads": [
            "plans/chapter-N-plan.md",
            "truth/chapter_summaries.md",
            "truth/pending_hooks.md",
            "truth/audit_drift.md",
            "world/rules.md",
            "truth/character_matrix.md",
            "style/style_profile.md",
            "chapters/chapter-N.md",
        ],
        "writes": [],
        "updates": [],
    },
    "shenbi-market-radar": {
        "kind": "ephemeral",
        "reads": ["novel.json", "genre-config.json"],
        "writes": [],
        "updates": [],
    },
    "shenbi-review-anti-ai": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "genre-config.json"],
        "writes": ["audits/chapter-N-anti-ai.md"],
        "updates": [],
    },
    "shenbi-review-character": {
        "kind": "report",
        "reads": [
            "chapters/chapter-N.md",
            "characters/protagonist.md",
            "characters/major/*.md",
            "truth/character_matrix.md",
            "truth/emotional_arcs.md",
        ],
        "writes": ["audits/chapter-N-character.md"],
        "updates": [],
    },
    "shenbi-review-continuity": {
        "kind": "report",
        "reads": [
            "chapters/chapter-N.md",
            "truth/current_state.md",
            "truth/chapter_summaries.md",
            "world/rules.md",
        ],
        "writes": ["audits/chapter-N-continuity.md"],
        "updates": [],
    },
    "shenbi-review-dialogue": {
        "kind": "report",
        "reads": [
            "chapters/chapter-N.md",
            "characters/protagonist.md",
            "characters/major/*.md",
            "truth/character_matrix.md",
        ],
        "writes": ["audits/chapter-N-dialogue.md"],
        "updates": [],
    },
    "shenbi-review-era": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "genre-config.json", "era-reference.md"],
        "writes": ["audits/chapter-N-era.md"],
        "updates": [],
    },
    "shenbi-review-fanfic": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "novel.json", "source_canon/*"],
        "writes": ["audits/chapter-N-fanfic.md"],
        "updates": [],
    },
    "shenbi-review-foreshadowing": {
        "kind": "report",
        "reads": [
            "chapters/chapter-N.md",
            "truth/pending_hooks.md",
            "plans/chapter-N-plan.md",
            "truth/subplot_board.md",
        ],
        "writes": ["audits/chapter-N-foreshadowing.md"],
        "updates": [],
    },
    "shenbi-review-highpoint": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "plans/chapter-N-plan.md", "genre-config.json"],
        "writes": ["audits/chapter-N-highpoint.md"],
        "updates": [],
    },
    "shenbi-review-long-span": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "chapters/*.md", "genre-config.json"],
        "writes": ["audits/chapter-N-long-span.md"],
        "updates": [],
    },
    "shenbi-review-memo-compliance": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "plans/chapter-N-plan.md", "truth/pending_hooks.md"],
        "writes": ["audits/chapter-N-memo-compliance.md"],
        "updates": [],
    },
    "shenbi-review-motivation": {
        "kind": "report",
        "reads": [
            "chapters/chapter-N.md",
            "characters/protagonist.md",
            "characters/major/*.md",
            "truth/character_matrix.md",
        ],
        "writes": ["audits/chapter-N-motivation.md"],
        "updates": [],
    },
    "shenbi-review-pacing": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "genre-config.json", "truth/chapter_summaries.md"],
        "writes": ["audits/chapter-N-pacing.md"],
        "updates": [],
    },
    "shenbi-review-pov": {
        "kind": "report",
        "reads": [
            "chapters/chapter-N.md",
            "genre-config.json",
            "truth/character_matrix.md",
            "truth/current_state.md",
        ],
        "writes": ["audits/chapter-N-pov.md"],
        "updates": [],
    },
    "shenbi-review-reader-pull": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "plans/chapter-N-plan.md", "truth/pending_hooks.md"],
        "writes": ["audits/chapter-N-reader-pull.md"],
        "updates": [],
    },
    "shenbi-review-sensitivity": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "genre-config.json", "novel.json"],
        "writes": ["audits/chapter-N-sensitivity.md"],
        "updates": [],
    },
    "shenbi-review-spinoff": {
        "kind": "report",
        "reads": [
            "chapters/chapter-N.md",
            "truth/parent_canon.md",
            "world/rules.md",
            "truth/pending_hooks.md",
        ],
        "writes": ["audits/chapter-N-spinoff.md"],
        "updates": [],
    },
    "shenbi-review-texture": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "genre-config.json", "plans/chapter-N-plan.md"],
        "writes": ["audits/chapter-N-texture.md"],
        "updates": [],
    },
    "shenbi-review-world-rules": {
        "kind": "report",
        "reads": [
            "chapters/chapter-N.md",
            "world/rules.md",
            "world/power_system.md",
            "world/locations.md",
            "world/story_bible.md",
            "truth/chapter_summaries.md",
            "truth/current_state.md",
        ],
        "writes": ["audits/chapter-N-world-rules.md"],
        "updates": [],
    },
    "shenbi-foundation-review": {
        "kind": "report",
        "reads": [
            "world/*.md",
            "characters/**/*.md",
            "outline/*.md",
            "truth/current_state.md",
            "truth/chapter_summaries.md",
        ],
        "writes": ["foundation/review_report.md"],
        "updates": [],
    },
    "shenbi-drift-guidance": {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "audits/chapter-N-*.md"],
        "writes": ["truth/drift_guidance.md"],
        "updates": ["truth/audit_drift.md"],
    },
    "shenbi-chapter-pattern": {
        "kind": "report",
        "reads": ["chapters/*.md", "truth/chapter_summaries.md", "genre-config.json"],
        "writes": ["outline/chapter_patterns.md"],
        "updates": [],
    },
}


def _yaml_escape(s: str) -> str:
    """Escape a string for a double-quoted YAML scalar."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _yaml_list(items: list[str]) -> str:
    if not items:
        return " []"  # `reads:[]` (no space) is not reliably parsed by PyYAML
    return "\n" + "\n".join(f"    - {i}" for i in items)


def _build_frontmatter(name: str, description: str, spec: dict[str, object]) -> str:
    reads = _yaml_list(spec["reads"])  # type: ignore[arg-type]
    writes = _yaml_list(spec["writes"])  # type: ignore[arg-type]
    updates = _yaml_list(spec["updates"])  # type: ignore[arg-type]
    contract = (
        "contract:\n"
        f"  kind: {spec['kind']}\n"
        f"  reads:{reads}\n"
        f"  writes:{writes}\n"
        f"  updates:{updates}\n"
    )
    # Description is double-quoted+escaped so special chars (e.g. the unquoted
    # colon-space in shenbi-review-fanfic's description) cannot break the YAML.
    return f'---\nname: {name}\ndescription: "{_yaml_escape(description)}"\n{contract}---\n'


def _strip_body_contract(body: str) -> str:
    """Remove the hand-written ## 数据契约 ... (up to the next ## heading)."""
    return re.sub(r"## 数据契约.*?(?=^## |\Z)", "", body, count=1, flags=re.DOTALL | re.MULTILINE)


def migrate_skill(skill: str) -> bool:
    """Rewrite one skill's frontmatter to add the contract; strip the body block."""
    spec = CLASSIFICATION.get(skill)
    if spec is None:
        return False
    md_path = SKILLS / skill / "SKILL.md"
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, flags=re.DOTALL)
    if not m:
        return False
    fm = m.group(1)
    name_m = re.search(r"^name:\s*(.+)$", fm, flags=re.MULTILINE)
    desc_m = re.search(r"^description:\s*(.+)$", fm, flags=re.MULTILINE)
    assert name_m and desc_m, skill
    description = desc_m.group(1).strip()
    # If the existing description was already quoted, unwrap before re-quoting.
    if description.startswith('"') and description.endswith('"') and description != '"':
        description = description[1:-1]
    new_fm = _build_frontmatter(name_m.group(1).strip(), description, spec)
    new_body = _strip_body_contract(m.group(2))
    # The auto-generated body view is rendered by `just generate`, not here.
    md_path.write_text(new_fm + new_body.lstrip("\n"), encoding="utf-8")
    return True


def main() -> int:
    """Migrate every skill in CLASSIFICATION; print the count migrated."""
    done = [s for s in CLASSIFICATION if migrate_skill(s)]
    print(f"migrated {len(done)} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
