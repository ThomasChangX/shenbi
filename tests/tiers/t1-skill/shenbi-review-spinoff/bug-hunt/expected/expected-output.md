# Expected Output: shenbi-review-spinoff Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Timeline leakage — spinoff chapter 3 paragraph 5 references information (mastermind = protagonist's father) that was only revealed in parent chapter 7; spinoff ch3 < parent ch7, so this information is forbidden in the spinoff at this point | error | `drafts/spinoff-chapter-3.md`: paragraph 5; `truth/parent_chapter_summaries.md`: chapter 7 entry |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with information in spinoff ch3 that was revealed in parent chapters 1-2 (legitimate, spinoff ch3 >= parent ch1-2)
- Issues with original spinoff content not derived from the parent novel

## Expected Output Structure
- Timeline comparison table: spinoff chapter number vs parent chapter number for each piece of information
- Information origin tracking: where each fact was first revealed in the parent novel
- Finding table identifying the timeline leakage
- Fix recommendation: remove the leaked information from spinoff chapter 3, or move the spinoff scene to after parent chapter 7 in the timeline
