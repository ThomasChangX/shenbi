# Expected Output: shenbi-review-fanfic Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Severity misclassification — character deviation (哈利 running from confrontation) classified as "warning" but Canon mode requires "error" per SKILL.md severity table; character's canonical bravery trait violated | error | `audit/fanfic-review-ch4.md`: character deviation finding; `novel.json`: fanfic_mode = "Canon"; `skills/shenbi-review-fanfic/SKILL.md`: severity table |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with plot elements that are consistent with canon (correct)
- Issues with character behavior that matches the source material (correct)

## Expected Output Structure
- Fanfic mode identification from novel.json
- Character behavior deviation check against source material
- Severity classification per SKILL.md severity table for the declared mode
- Finding table identifying the misclassified severity
- Fix recommendation: reclassify finding from "warning" to "error" per Canon mode severity table
