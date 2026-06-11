# Expected Output: shenbi-review-dialogue Bug-Hunt

## Expected Findings

| # | Finding | Severity | Evidence location |
|---|---------|----------|-------------------|
| 1 | Voice fingerprint mismatch — 老陈 uses short formal sentences (avg ~10 chars) identical to 苏晴's pattern, instead of expected long colloquial sentences (avg ~25 chars) with "哎呀"/"就是说" fillers per voice_profile | error | `drafts/chapter-5.md`: paragraphs 3, 6, 9, 14 |

## Expected Non-Findings

The agent MUST NOT report:
- Issues with dialogue punctuation or formatting (correct)
- Issues with dialogue attribution (correct)
- Issues with 苏晴's voice matching her profile (苏晴's lines match baseline; the defect is 老陈 deviating from his)

## Expected Output Structure
- Voice fingerprint comparison table per speaker
- Sentence length deviation quantified against baseline
- Vocabulary range comparison against profile
- Finding table with the voice fingerprint mismatch
- Fix recommendation: rewrite 老陈's dialogue to match voice_profile (long, colloquial)
