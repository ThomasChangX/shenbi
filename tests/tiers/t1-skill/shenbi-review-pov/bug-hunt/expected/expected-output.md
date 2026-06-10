# Expected Output: shenbi-review-pov Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Information leakage — 林墨 (POV) knows 苏晴 works for the antagonist, but was never present at the revelation; secret was revealed in chapter 7 private conversation between 苏晴 and antagonist where 林墨 was absent; no acquisition channel exists | error | `drafts/chapter-9.md`: paragraph 6; `truth/chapter_summaries.md`: chapter 7 summary confirms private conversation with 林墨 absent |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with 林墨's knowledge that he legitimately acquired in prior chapters
- Issues with the narrative perspective in other paragraphs (correctly limited)

## Expected Output Structure
- POV knowledge audit table listing all character knowledge claims
- Acquisition channel verification for each claim
- Finding table identifying the leaked information
- Fix recommendation: remove the knowledge claim or add a scene where 林墨 learns the secret through a legitimate channel
