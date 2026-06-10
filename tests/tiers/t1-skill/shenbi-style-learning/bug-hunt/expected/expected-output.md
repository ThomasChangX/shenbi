# Expected Output: shenbi-style-learning Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Objectivity violation — profile contains subjective quality judgments: "excellent," "strong," "impressive," "weak" used to assess writing quality instead of reporting objective statistics | error | `config/style_profile.md`: prose analysis sections |
| 2 | Completeness violation — only 5 of 7 required statistical dimensions computed; missing: dialogue-to-narrative ratio, paragraph length distribution | error | `config/style_profile.md`: metrics section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with reproducibility (the statistical computations that are present appear deterministic)
- Issues with downstream usability (the profile structure is appropriate for reference)
- Issues with statistical validity of the 5 dimensions that were computed

## Expected Output Structure
- Quality check report with finding table
- Enumeration of subjective language instances with evidence
- List of missing statistical dimensions
