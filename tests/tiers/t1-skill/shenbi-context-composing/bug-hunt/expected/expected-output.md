# Expected Output: shenbi-context-composing Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | P1 item (chapter plan memo) was trimmed — "章尾必须发生的改变" section missing — while lower-priority P2 summaries and P5 world rules are included in full, violating strict priority ordering | error | Assembled context output: P1 section |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with P2 summaries (they are correctly included from recent chapters)
- Issues with hook urgency calculation (hook ordering is correct)
- Issues with ending diversity check (it properly identifies recent ending patterns)

## Expected Output Structure
- Quality check report with finding table
- Specific identification of the trimmed P1 content and the untrimmed lower-priority content
- Severity classification for the priority violation
