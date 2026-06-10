# Genesis Phase Seed

Use `tests/fixtures/outline-example.md` as the seed outline.

Agent instructions:
1. Run shenbi-worldbuilding with the outline as input. Approve the output.
2. Run shenbi-power-system with worldbuilding output. Approve.
3. Run shenbi-faction-builder with worldbuilding output. Approve.
4. Run shenbi-location-builder with worldbuilding output. Approve.
5. Run shenbi-character-design with all previous output. Approve.
6. Run shenbi-relationship-map with all previous output. Approve.

After each skill, verify handoff integrity: does the next skill find all required input files?
