#!/usr/bin/env python3
"""Independent Gate executor. Usage: validate-gate.py <GATE> [args...]

Gates: G0 G1 G2 G3 G4 G5 G6 G7 G_TRANSITION G_DISPATCH G_RECONCILE
Each gate function returns JSON via passed() or fail() helpers.

PR-19 (P-1.E): shared helpers extracted to shenbi.gates.shared. This file
retains gate function definitions; future PRs split them into per-gate modules.
"""

import json
import sys

try:
    import yaml
except ImportError:
    yaml = None

from shenbi.gates.g0 import gate_G0
from shenbi.gates.g1 import gate_G1
from shenbi.gates.g2 import _is_important_chapter, gate_G2  # noqa: F401
from shenbi.gates.g3 import gate_G3

# ---------------------------------------------------------------------------
# G4 — T1 Skill-Specific Gates
# ---------------------------------------------------------------------------
# All G4 checkers (generic + per-skill) extracted to src/shenbi/gates/g4/ in
# PR-19 Task 4. This file imports them for backwards compatibility.
from shenbi.gates.g4 import (  # noqa: F401
    g4_generic_bughunt,
    g4_generic_clean,
    g4_generic_generative,
    gate_G4,
    gate_G4_bughunt,
    gate_G4_clean,
)
from shenbi.gates.g4.anti_detect import g4_anti_detect  # noqa: F401
from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting  # noqa: F401
from shenbi.gates.g4.chapter_planning import g4_chapter_planning  # noqa: F401
from shenbi.gates.g4.character_design import g4_character_design  # noqa: F401
from shenbi.gates.g4.context_composing import g4_context_composing  # noqa: F401
from shenbi.gates.g4.faction_builder import g4_faction_builder  # noqa: F401
from shenbi.gates.g4.foreshadowing_plant import g4_foreshadowing_plant  # noqa: F401
from shenbi.gates.g4.foreshadowing_track import g4_foreshadowing_track  # noqa: F401
from shenbi.gates.g4.genre_config import g4_genre_config  # noqa: F401
from shenbi.gates.g4.length_normalizing import g4_length_normalizing  # noqa: F401
from shenbi.gates.g4.location_builder import g4_location_builder  # noqa: F401
from shenbi.gates.g4.pacing_design import g4_pacing_design  # noqa: F401
from shenbi.gates.g4.plot_thread_weaver import g4_plot_thread_weaver  # noqa: F401
from shenbi.gates.g4.power_system import g4_power_system  # noqa: F401
from shenbi.gates.g4.relationship_map import g4_relationship_map  # noqa: F401
from shenbi.gates.g4.state_settling import g4_state_settling  # noqa: F401
from shenbi.gates.g4.story_architecture import g4_story_architecture  # noqa: F401
from shenbi.gates.g4.style_polishing import g4_style_polishing  # noqa: F401
from shenbi.gates.g4.volume_outlining import g4_volume_outlining  # noqa: F401
from shenbi.gates.g4.worldbuilding import g4_worldbuilding  # noqa: F401
from shenbi.gates.g5 import gate_G5
from shenbi.gates.g6 import gate_G6
from shenbi.gates.g7 import gate_G7
from shenbi.gates.g_dispatch import gate_G_DISPATCH
from shenbi.gates.g_reconcile import gate_G_RECONCILE
from shenbi.gates.g_transition import gate_G_TRANSITION
from shenbi.gates.shared import (  # noqa: F401 — re-exported for legacy callers
    ALL_SKILLS,
    CHAPTER_WORD_CEILING,
    CHAPTER_WORD_FLOOR,
    FATIGUE_BASE,
    FIXTURES,
    G4_CHECKER_SKILLS,
    META_NARRATIVE,
    PROJECT,
    SKILLS,
    TESTS,
    TRANSITION_SPECIFIC,
    _find_report,
    _normalize_file_paths,
    count_transition_words,
    fail,
    jload,
    passed,
    read_genre_config,
    unimplemented,
    word_count_md,
    write_gate_marker,
    yload,
)

# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-gate.py <GATE> [args...]")
        print()
        print("Gates: G0 G1 G2 G3 G4 G5 G6 G7 G_TRANSITION G_DISPATCH G_RECONCILE")
        print()
        print("Examples:")
        print("  validate-gate.py G0 outline-example.md")
        print("  validate-gate.py G2 path/to/file.md,path/to/file2.md chapter")
        print("  validate-gate.py G4 chapter-drafting path/to/file.md")
        print("  validate-gate.py G4 worldbuilding path/to/file1,path/to/file2")
        print("  validate-gate.py G7 tests/rounds/round-003-2026-01-01")
        print("  validate-gate.py G_TRANSITION generative bug-hunt tests/rounds/round-003")
        print("  validate-gate.py G_DISPATCH generative tests/rounds/round-003")
        sys.exit(1)

    gate = sys.argv[1]
    args = sys.argv[2:]

    def arg(i, default=None):
        return args[i] if i < len(args) else default

    if gate == "G0":
        print(gate_G0(seed_file=arg(0), round_dir=arg(1)))

    elif gate == "G1":
        files_raw = arg(1, "[]")
        try:
            input_files = json.loads(files_raw)
        except (json.JSONDecodeError, ValueError):
            input_files = []
        print(gate_G1(skill_name=arg(0), input_files=input_files, round_dir=arg(2)))

    elif gate == "G2":
        files = arg(0, "").split(",") if arg(0) else []
        ftype = arg(1, "chapter")
        rd = arg(2, None)
        pd = arg(3, None)
        print(gate_G2(files, ftype, rd, pd))

    elif gate == "G3":
        print(gate_G3(arg(0), arg(1), arg(2)))

    elif gate == "G4":
        skill_or_type = arg(0, "")
        file_list = arg(1, "").split(",") if arg(1) else []
        rd = arg(2, None)

        # Map shorthand names to full shenbi- prefixed skill names
        short_map = {
            "chapter-drafting": "shenbi-chapter-drafting",
            "worldbuilding": "shenbi-worldbuilding",
            "character-design": "shenbi-character-design",
            "story-architecture": "shenbi-story-architecture",
            "power-system": "shenbi-power-system",
            "faction-builder": "shenbi-faction-builder",
            "location-builder": "shenbi-location-builder",
            "relationship-map": "shenbi-relationship-map",
            "pacing-design": "shenbi-pacing-design",
            "plot-thread-weaver": "shenbi-plot-thread-weaver",
            "genre-config": "shenbi-genre-config",
            "volume-outlining": "shenbi-volume-outlining",
            "chapter-planning": "shenbi-chapter-planning",
            "foreshadowing-track": "shenbi-foreshadowing-track",
            "foreshadowing-plant": "shenbi-foreshadowing-plant",
            "context-composing": "shenbi-context-composing",
            "anti-detect": "shenbi-anti-detect",
            "length-normalizing": "shenbi-length-normalizing",
            "state-settling": "shenbi-state-settling",
            "style-polishing": "shenbi-style-polishing",
        }

        if skill_or_type in ("bughunt", "bug-hunt"):
            print(gate_G4_bughunt(file_list))
        elif skill_or_type == "clean":
            print(gate_G4_clean(file_list))
        else:
            full_name = short_map.get(skill_or_type, skill_or_type)
            result = gate_G4(full_name, "generative", file_list, rd)
            print(result)
            write_gate_marker("G4", full_name, "generative", result, rd, file_list)

    elif gate == "G5":
        print(gate_G5(phase_name=arg(0), round_dir=arg(1), project_dir=arg(2)))

    elif gate == "G6":
        pipeline_name = arg(0)
        result = gate_G6(pipeline_name, arg(1), arg(2))
        print(result)
        write_gate_marker("G6", pipeline_name, "generative", result, arg(1))

    elif gate == "G7":
        print(gate_G7(arg(0)))

    elif gate == "G_TRANSITION":
        print(gate_G_TRANSITION(arg(0), arg(1), arg(2)))

    elif gate == "G_DISPATCH":
        print(gate_G_DISPATCH(arg(0), arg(1)))

    elif gate == "G_RECONCILE":
        print(gate_G_RECONCILE(arg(0)))

    else:
        print(
            json.dumps(
                {
                    "status": "UNKNOWN_GATE",
                    "gate": gate,
                    "valid_gates": [
                        "G0",
                        "G1",
                        "G2",
                        "G3",
                        "G4",
                        "G5",
                        "G6",
                        "G7",
                        "G_TRANSITION",
                        "G_DISPATCH",
                        "G_RECONCILE",
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
