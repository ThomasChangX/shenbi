# Import Phase Seed

Use `tests/fixtures/report-example.txt` (UTF-8) as the source novel.

Agent instructions:
1. Run shenbi-import-analysis on the full text.
2. Run shenbi-character-extraction with analysis output.
3. Run shenbi-world-extraction with analysis output.
4. Run shenbi-canon-import with analysis output.

After each skill, verify handoff integrity.
