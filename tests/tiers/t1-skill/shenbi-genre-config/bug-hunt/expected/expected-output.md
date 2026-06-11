# Expected Output: shenbi-genre-config Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | No backup of genre-config.json was created before modification — original file overwritten without rollback capability | error | `genre-config.json` modification log: no backup path recorded |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the new banned word entries (they are valid additions)
- Issues with the new audit dimension settings (they are properly calibrated)
- Issues with JSON structural validity (the file is well-formed)

## Expected Output Structure
- Quality check report with finding table
- Specific citation of the missing backup in the modification log
- Severity classification for each issue
