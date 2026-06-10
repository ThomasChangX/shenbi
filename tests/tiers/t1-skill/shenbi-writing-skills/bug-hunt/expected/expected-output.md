# Expected Output: shenbi-writing-skills Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Iron law absoluteness violation — rules use "should," "recommended," "prefer" instead of required MUST/NEVER/ALWAYS language in 4 rules | error | `skills/custom-scene-transition/SKILL.md`: iron laws section |
| 2 | Skill completeness violation — anti-rationalization table is missing; only DOT flowchart and red flag checklist present | error | `skills/custom-scene-transition/SKILL.md`: full document (absent section) |
| 3 | Description trap — frontmatter description describes what the skill does ("Creates smooth scene transitions by...") instead of when to trigger it | error | `skills/custom-scene-transition/SKILL.md`: frontmatter description |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with the DOT flowchart (it is present and correct)
- Issues with the red flag checklist (it is present and correct)
- Issues with the output format (frontmatter + markdown structure is followed)

## Expected Output Structure
- Quality check report with finding table
- Each weak iron law quoted with evidence
- Confirmation of missing anti-rationalization table
- Description trap flagged with explanation of correct trigger-only pattern
