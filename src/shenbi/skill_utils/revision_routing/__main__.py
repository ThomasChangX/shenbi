"""Standalone runner: python -m shenbi.skill_utils.revision_routing"""

from shenbi.skill_utils.revision_routing.route import route_revision
import json
import sys


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="revision_routing", description="Route a diagnosis to revision mode (spec §5.2)."
    )
    parser.add_argument("--diagnosis", required=True, help="JSON diagnosis string.")
    args = parser.parse_args()
    diagnosis = json.loads(args.diagnosis)
    sys.stdout.write(json.dumps({"mode": route_revision(diagnosis)}) + "\n")


if __name__ == "__main__":
    main()
