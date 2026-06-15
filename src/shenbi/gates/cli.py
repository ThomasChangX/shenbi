"""CLI entry point for gate validation.

Replaces the P-1.D forwarder. Dispatches to shenbi.gates.g* modules directly.

Argument parsing mirrors the legacy tests/validate-gate.py main() to preserve
the dispatch protocol: shell callers and shenbi-dispatch depend on the
JSON-decode (G1), comma-split (G2/G4), and shorthand-name mapping (G4)
conventions.
"""

import json
import sys

from shenbi.cli_utils import emit_json
from shenbi.gates.g0 import gate_G0
from shenbi.gates.g1 import gate_G1
from shenbi.gates.g2 import gate_G2
from shenbi.gates.g3 import gate_G3
from shenbi.gates.g4 import gate_G4, gate_G4_bughunt, gate_G4_clean
from shenbi.gates.g5 import gate_G5
from shenbi.gates.g6 import gate_G6
from shenbi.gates.g7 import gate_G7
from shenbi.gates.g_dispatch import gate_G_DISPATCH
from shenbi.gates.g_reconcile import gate_G_RECONCILE
from shenbi.gates.g_transition import gate_G_TRANSITION
from shenbi.gates.shared import write_gate_marker
from shenbi.logging import configure_logging, get_logger

log = get_logger(__name__)

# Shorthand skill name -> full shenbi-* name. Mirrors legacy validate-gate.py.
SHORT_MAP = {
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


def main() -> int:
    configure_logging()
    if len(sys.argv) < 2:
        usage = """Usage: shenbi-validate <GATE> [args...]

Gates: G0 G1 G2 G3 G4 G5 G6 G7 G_TRANSITION G_DISPATCH G_RECONCILE

Examples:
  shenbi-validate G0 outline-example.md
  shenbi-validate G2 path/to/file.md,path/to/file2.md chapter
  shenbi-validate G4 chapter-drafting path/to/file.md
  shenbi-validate G4 worldbuilding path/to/file1,path/to/file2
  shenbi-validate G7 tests/rounds/round-003-2026-01-01"""
        log.info("usage", message=usage)
        return 1

    gate = sys.argv[1]
    args = sys.argv[2:]

    def arg(i: int, default: str | None = None) -> str | None:
        return args[i] if i < len(args) else default

    result: object = None
    if gate == "G0":
        result = gate_G0(seed_file=arg(0), round_dir=arg(1))

    elif gate == "G1":
        files_raw = arg(1, "[]") or "[]"
        try:
            input_files = json.loads(files_raw)
        except (json.JSONDecodeError, ValueError):
            input_files = []
        result = gate_G1(skill_name=arg(0), input_files=input_files, round_dir=arg(2))

    elif gate == "G2":
        a0 = arg(0) or ""
        files = a0.split(",") if a0 else []
        ftype = arg(1, "chapter") or "chapter"
        rd = arg(2, None)
        pd = arg(3, None)
        result = gate_G2(files, ftype, rd, pd)

    elif gate == "G3":
        result = gate_G3(arg(0), arg(1), arg(2))

    elif gate == "G4":
        skill_or_type = arg(0, "") or ""
        a1 = arg(1)
        file_list = a1.split(",") if a1 else []
        rd = arg(2, None)

        if skill_or_type in ("bughunt", "bug-hunt"):
            result = gate_G4_bughunt(file_list)
        elif skill_or_type == "clean":
            result = gate_G4_clean(file_list)
        else:
            full_name = SHORT_MAP.get(skill_or_type, skill_or_type)
            result = gate_G4(full_name, "generative", file_list, rd)
            write_gate_marker("G4", full_name, "generative", result, rd, file_list)

    elif gate == "G5":
        result = gate_G5(phase_name=arg(0), round_dir=arg(1), project_dir=arg(2))
    elif gate == "G6":
        pipeline_name = arg(0)
        result = gate_G6(pipeline_name, arg(1), arg(2))
        write_gate_marker("G6", pipeline_name or "", "generative", result, arg(1))
    elif gate == "G7":
        result = gate_G7(arg(0) or "")
    elif gate == "G_TRANSITION":
        result = gate_G_TRANSITION(arg(0) or "", arg(1) or "", arg(2) or "")
    elif gate == "G_DISPATCH":
        result = gate_G_DISPATCH(arg(0) or "", arg(1) or "")
    elif gate == "G_RECONCILE":
        result = gate_G_RECONCILE(arg(0) or "")
    else:
        log.error("unknown_gate", gate=gate)
        return 1

    # Gate functions return JSON strings; emit via emit_json to keep stdout
    # machine-readable. If a future gate returns a non-JSON string, wrap it.
    assert isinstance(result, str)
    try:
        emit_json(json.loads(result))
    except (json.JSONDecodeError, ValueError):
        emit_json({"result": result})
    # Legacy validate-gate.py returns 0 for all known gates regardless of PASS/FAIL.
    # Preserve that contract so shell callers that check $? see no behavior change.
    return 0


if __name__ == "__main__":
    sys.exit(main())
