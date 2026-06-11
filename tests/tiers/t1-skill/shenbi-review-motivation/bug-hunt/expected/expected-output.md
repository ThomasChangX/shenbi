# Expected Output: shenbi-review-motivation Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Broken causal chain — 林墨's betrayal of 苏晴 (revealing her location to antagonist) has no trigger or judgment; causal chain missing links: no trigger event → no judgment process → action occurs; missing prior motivation | error | `drafts/chapter-8.md`: paragraphs 14-15 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other character actions that have complete causal chains
- Issues with the consequences of the betrayal (consequence link is present in the narrative)

## Expected Output Structure
- Causal chain reconstruction table for each major action
- Finding table identifying the broken chain
- Missing links clearly specified (trigger: absent, judgment: absent)
- Fix recommendation: add trigger event and judgment internal monologue before the betrayal action
