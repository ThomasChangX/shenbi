# Expected Output: shenbi-import-analysis Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Zero guessing violation — fabricated fact: "grew up in a coastal village" and "learned swordsmanship from a retired navy captain" for the protagonist have no corresponding passage in any source chapter | error | `import/analysis/02_characters.md`: protagonist profile |
| 2 | Traceability violation — at least 8 extracted facts in character and plot passes lack chapter.paragraph references | error | `import/analysis/02_characters.md`, `import/analysis/04_plot.md`: uncited facts |
| 3 | Pipeline correctness violation — Pass 4 (plot) references data from Pass 7 (highlights), which violates the serial/parallel dependency order defined in the DOT flowchart | error | `import/analysis/04_plot.md`: data dependency section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with Pass 1 (parse) output, which is correct
- Issues with statistics accuracy, which matches source file
- Issues with Pass 5–8 outputs, which are internally consistent

## Expected Output Structure
- Quality check report covering all 8 pass outputs
- Identification of fabricated facts with explicit "not found in source" evidence
- List of uncited extracted facts requiring chapter.paragraph references
- Pipeline dependency violation report referencing the DOT flowchart
