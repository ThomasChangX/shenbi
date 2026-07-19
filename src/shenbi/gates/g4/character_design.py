"""G4 checker for shenbi-character-design."""

from __future__ import annotations
from typing import Any
import re
from pathlib import Path

from shenbi.gates.shared import (
    PROJECT,
    fail,
    passed,
    resolve_input_path,
    yload,
)
from shenbi.paths import RoundPaths


def g4_character_design(
    fps: list[str],
    rd: str | None = None,
    project_dir: str | None = None,  # threaded by 15a, consumed by 15b
    repo_root: str | None = None,  # threaded by 15a, consumed by 15b
) -> str:
    """Character-design: frontmatter fields, voice_profile arrays, relationship pairs."""
    c: list[dict[str, Any]] = []
    mf: list[str] = []

    if rd is None and project_dir is None:
        raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
    rp = RoundPaths(
        round_dir=Path(str(rd or project_dir)),
        project_dir=Path(str(project_dir or rd)),
        repo_root=Path(repo_root or PROJECT),
    )

    for fp in fps or []:
        pf = resolve_input_path(fp, rd)

        # protagonist.md checks
        if "protagonist" in str(fp) and pf.suffix == ".md":
            try:
                fm = yload(str(pf))
            except Exception:
                mf.append(f"G4.protag.yaml_error:{fp}")
                continue

            required_fields = [
                "name",
                "role",
                "personality_tags",
                "core_value",
                "goal_surface",
                "goal_deep",
                "fear",
                "arc_type",
                "arc_starting",
                "arc_turning",
                "arc_ending",
                "voice_profile",
            ]
            for f in required_fields:
                if (
                    f not in fm
                    or (isinstance(fm[f], (list, dict)) and not fm[f])
                    or (isinstance(fm[f], str) and not fm[f].strip())
                ):
                    mf.append(f"G4.protag.missing_{f}:{fp}")
                else:
                    c.append({"id": f"G4.protag.{f}", "s": "PASS"})

            # voice_profile sub-checks
            vp = fm.get("voice_profile", {})
            if isinstance(vp, dict):
                thresholds = {
                    "speech_patterns": 2,
                    "catchphrases": 1,
                    "avoid_patterns": 1,
                }
                for arr_name, min_len in thresholds.items():
                    val = vp.get(arr_name, [])
                    if not isinstance(val, list) or len(val) < min_len:
                        mf.append(
                            f"G4.voice.{arr_name}:need_{min_len}_got_{len(val) if isinstance(val, list) else 0}"
                        )
                    else:
                        c.append(
                            {
                                "id": f"G4.voice.{arr_name}",
                                "s": "PASS",
                                "count": len(val),
                            }
                        )
            else:
                mf.append("G4.voice.not_a_dict")

        # relationships.md checks
        if "relationships" in str(fp) and pf.suffix == ".md":
            content = pf.read_text(encoding="utf-8")
            # Count ## 关系对 headings (not table rows — bug fix #5)
            rel_pairs = len(re.findall(r"## 关系对", content))
            # Also accept table-based format (| col1 | col2 | ...) as valid pairs
            # The character-design SKILL instructs agents to use table format,
            # while the relationship-map skill uses heading format. Accept either.
            if rel_pairs < 3:
                # Count relationship table data rows (skip header/separator rows)
                table_rows = len(re.findall(r"^\|.*\|.*\|", content, re.MULTILINE))
                # Each data row represents a relationship pair; skip header + separator
                data_rows = max(0, table_rows - 2)
                if data_rows >= 3:
                    c.append(
                        {"id": "G4.rel.pairs", "s": "PASS", "count": data_rows, "format": "table"}
                    )
                else:
                    mf.append(f"G4.rel.pairs:need_3_got_{rel_pairs}_heading_{data_rows}_table")
            else:
                c.append({"id": "G4.rel.pairs", "s": "PASS", "count": rel_pairs})

    # G4.cd.major_chars (EXISTING -- raise threshold from >=2 to >=3):
    # characters/major/ must have >= 3 .md files
    major_dir = rp.read("characters/major")
    if major_dir.exists():
        major_files = list(major_dir.glob("*.md"))
        if len(major_files) >= 3:
            c.append(
                {
                    "id": "G4.cd.major_chars",
                    "s": "PASS",
                    "count": len(major_files),
                }
            )
        elif len(major_files) >= 1:
            mf.append(f"G4.cd.major_chars:need_3_got_{len(major_files)}")
        else:
            mf.append("G4.cd.major_chars:need_3_got_0")
    else:
        mf.append("G4.cd.major_chars:directory_missing")

    # G4.cd.minor_chars (NEW): characters/minor/ must have >= 2 .md files
    minor_dir = rp.read("characters/minor")
    if minor_dir.exists():
        minor_files = list(minor_dir.glob("*.md"))
        if len(minor_files) >= 2:
            c.append(
                {
                    "id": "G4.cd.minor_chars",
                    "s": "PASS",
                    "count": len(minor_files),
                }
            )
        elif len(minor_files) >= 1:
            mf.append(f"G4.cd.minor_chars:need_2_got_{len(minor_files)}")
        else:
            mf.append("G4.cd.minor_chars:need_2_got_0")
    else:
        mf.append("G4.cd.minor_chars:directory_missing")

    # G4.cd.archetype: validate archetype_sources in major character files
    major_dir = rp.read("characters/major")
    if major_dir.exists():
        for mf_path in sorted(major_dir.glob("*.md")):
            archetype_issues = _validate_archetype(mf_path, c)
            mf.extend(archetype_issues)

    # Also check protagonist for archetype
    for fp in fps or []:
        pf = resolve_input_path(fp, rd)
        if pf.suffix == ".md" and "protagonist" in str(fp):
            archetype_issues = _validate_archetype(pf, c)
            mf.extend(archetype_issues)
            break

    if mf:
        return fail("G4-character-design", c, "scoring", mf)
    return passed("G4-character-design", c)


def _validate_archetype(
    file_path: Path,
    checks: list[dict[str, Any]],
) -> list[str]:
    """Validate archetype_sources frontmatter in a character archive.

    Returns a list of failure strings (empty if valid).
    """
    local_failures: list[str] = []
    char_name = file_path.stem

    try:
        fm = yload(str(file_path))
    except Exception:
        return [f"G4.cd.archetype.yaml_error:{char_name}"]

    archetype_sources = fm.get("archetype_sources", [])

    if not archetype_sources or not isinstance(archetype_sources, list):
        local_failures.append(f"G4.cd.archetype.missing:{char_name}")
        return local_failures

    for i, source in enumerate(archetype_sources):
        prefix = f"G4.cd.archetype.{char_name}[{i}]"

        # Historical figure name (must be specific, not abstract)
        name = source.get("name", "")
        if not name or not isinstance(name, str) or len(name) < 3:
            local_failures.append(f"{prefix}.name:too_short_or_missing")
            continue

        abstract_terms = [
            "elder",
            "mentor",
            "warrior",
            "sage",
            "hero",
            "villain",
            "trickster",
            "maiden",
            "crone",
            "everyman",
        ]
        if name.lower() in abstract_terms:
            local_failures.append(f"{prefix}.name:abstract_type_not_historical_figure")

        # traits_borrowed: >= 3
        borrowed = source.get("traits_borrowed", [])
        if not isinstance(borrowed, list) or len(borrowed) < 3:
            local_failures.append(
                f"{prefix}.traits_borrowed:need_3_got_{len(borrowed) if isinstance(borrowed, list) else 0}"
            )

        # traits_discarded: >= 2
        discarded = source.get("traits_discarded", [])
        if not isinstance(discarded, list) or len(discarded) < 2:
            local_failures.append(
                f"{prefix}.traits_discarded:need_2_got_{len(discarded) if isinstance(discarded, list) else 0}"
            )

        # adaptation_rationale: >= 100 characters
        rationale = source.get("adaptation_rationale", "")
        if not isinstance(rationale, str) or len(rationale) < 100:
            local_failures.append(
                f"{prefix}.adaptation_rationale:need_100_chars_got_{len(rationale) if isinstance(rationale, str) else 0}"
            )

        if not local_failures:
            checks.append(
                {
                    "id": f"G4.cd.archetype.{char_name}",
                    "s": "PASS",
                    "archetype_name": name,
                    "borrowed_count": len(borrowed),
                    "discarded_count": len(discarded),
                    "rationale_chars": len(rationale),
                }
            )

    return local_failures
