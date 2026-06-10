# Expected Output: shenbi-story-architecture Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | KR-3 ("protagonist grows stronger") is vague and immeasurable — lacks concrete criteria and chapter range mapping | error | `story/okr.md`: Objective 2, KR-3 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the story_frame.md prose format (it uses correct narrative paragraphs)
- Issues with the three-layer conflict coherence (conflicts are mutually reinforcing)
- Issues with foreshadowing seeding (≥3 lines are properly seeded)

## Expected Output Structure
- Quality check report with finding table
- Specific citation of the vague KR and why it fails the executability standard
- Severity classification for each issue
