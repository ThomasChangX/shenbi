# Expected Output: shenbi-chapter-planning Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Chapter memo missing required section 2: "读者此刻在等什么" — reader expectation management not addressed | error | `plans/chapter-7-plan.md`: missing section 2 |
| 2 | Chapter memo missing required section 4: "日常/过渡承担什么任务" — daily/transition task mapping not addressed | error | `plans/chapter-7-plan.md`: missing section 4 |
| 3 | Chapter memo missing required section 6: "章尾必须发生的改变" — no end-of-chapter change commitment | error | `plans/chapter-7-plan.md`: missing section 6 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with sections 1, 3, 5, 7, 8 (they are present and correct)
- Issues with goal derivation (present sections follow priority chain)
- Issues with hook accounting (section 7 is properly populated)

## Expected Output Structure
- Quality check report with finding table
- Enumeration of all 3 missing sections
- Severity classification for each missing section
