# Expected Output: shenbi-character-extraction Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Fabrication violation — "cynical sense of humor" trait for protagonist has zero supporting passages across all 15 source chapters | error | `characters/protagonist.md`: personality section |
| 2 | Voice fingerprint violation — Li Wei's speech patterns contain no statistical extraction from actual dialogue (no word frequency, sentence length, or catchphrase analysis) | error | `characters/major/li-wei.md`: speech patterns section |
| 3 | Relationship network incompleteness — Chen Ming and Old Zhang have 3 interaction scenes (chapters 4, 8, 11) but no entry in relationships.md | error | `characters/relationships.md`: missing entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with arc evidence for the protagonist, which is correctly backed by chapter-specific behavioral evidence
- Issues with other character cards that have proper evidence grounding
- Issues with the protagonist's voice fingerprint, which is statistically extracted

## Expected Output Structure
- Quality check report covering all character cards
- Identification of fabricated trait with explicit "no passage found" evidence
- Voice fingerprint gap analysis for Li Wei
- Missing relationship entries with scene references
