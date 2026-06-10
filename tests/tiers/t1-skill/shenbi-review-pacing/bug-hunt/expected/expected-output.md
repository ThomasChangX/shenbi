# Expected Output: shenbi-review-pacing Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Chapter 7 misclassified as QUEST — content contains high-stakes confrontation, rapid dialogue exchanges, emotional escalation, and cliffhanger ending, matching FIRE definition per rhythm_principles.md | error | `audit/pacing-review.md`: chapter 7 classification; `drafts/chapter-7.md`: paragraphs 3-15 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with other chapter classifications (chapters 4-6, 8 are correctly classified)
- Issues with pacing rhythm balance (correct outside the misclassification)

## Expected Output Structure
- Chapter type classification table for last 5 chapters
- Per-chapter evidence supporting the classification
- Finding table identifying the misclassification
- Fix recommendation: reclassify chapter 7 as FIRE
