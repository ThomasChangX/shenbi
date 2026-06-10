# Expected Output: shenbi-canon-import Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Deviation transparency violation — protagonist's core motivation changed from "seeking justice for family" (original, episode 1) to "seeking power for personal gain" without being declared in deviations.md | error | `import/canon/character.md`: protagonist motivation; `import/canon/deviations.md`: missing entry |
| 2 | Evidence traceability violation — 4 event entries lack chapter/episode/paragraph citations to the original work | error | `import/canon/event.md`: entries without source citations |
| 3 | Mode fidelity violation — relationship section preserves canon exactly (canon-compliant behavior) while character section diverges (AU behavior); mode applied inconsistently across sections | error | `import/canon/relationship.md` vs `import/canon/character.md` |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with world canon section, which is correctly extracted with citations
- Issues with timeline section, which is complete with source references
- Issues with declared deviations in deviations.md (those that exist are valid)

## Expected Output Structure
- Quality check report covering all 5 canon sections and deviations.md
- Identification of undeclared deviation with original work evidence
- Missing citation inventory for event section
- Mode consistency analysis across all sections
