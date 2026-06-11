# Expected Output: shenbi-snapshot-manage Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Snapshot completeness violation — only 8 of 11 truth files archived; missing `ability_registry.md`, `faction_records.md`, and `timeline.md` | error | `snapshots/pre-chapter-25/`: directory contents vs expected 11 truth files |
| 2 | Metadata inconsistency — metadata claims "11 files archived" but actual file count is 8 | error | `snapshots/pre-chapter-25/metadata.json`: file_count field |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the 8 included files (they have correct content and non-zero size)
- Issues with checksum integrity (included files pass checksum verification)

## Expected Output Structure
- Quality check report with finding table
- File-by-file comparison: expected 11 truth files vs actual 8 found
- Specific list of 3 missing files
- Metadata field comparison showing count mismatch
