# Expected Output: shenbi-short-packaging Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Spoiler violation — blurb version 1 reveals act 3 climax resolution: protagonist sacrifices powers to seal the rift and lives as an ordinary person | error | `import/packaging/blurbs.md`: blurb version 1 |
| 2 | Evidence backing violation — selling points 2 and 4 lack chapter.paragraph citations | error | `import/packaging/selling_points.md`: points 2, 4 |
| 3 | Cover prompt usability violation — missing color palette and style keywords fields | error | `import/packaging/cover_prompt.md`: field inventory |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with title candidate quantity (3 titles provided, within 3-5 range)
- Issues with title distinctness (all 3 titles are semantically distinct)
- Issues with platform keyword alignment (keywords match target platform taxonomy)
- Issues with blurb version 2, which correctly avoids spoilers

## Expected Output Structure
- Quality check report covering all packaging materials
- Spoiler analysis comparing blurb content against act 3 plot points
- Evidence citation audit for each selling point
- Cover prompt field completeness check
