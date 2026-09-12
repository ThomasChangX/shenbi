# Audit Phase Seed

Use the output from Drafting phase as input (chapters/chapter-1.md, truth/*, characters/*, world/*).

Agent instructions:
Run the review skills on the drafted chapter. The group-review family supersedes
the twelve retired single-dimension reviewers (C21); these can run in parallel
since they are independent:

1. shenbi-review-group-character — BDI/voice/dialogue/pov/reader-pull character audits
2. shenbi-review-group-craft — pacing/motivation/memo-compliance/texture craft audits
3. shenbi-review-group-factual — continuity/world-rules/anti-ai factual audits
4. shenbi-review-group-plan — foreshadowing payoff-and-plan audits
5. shenbi-review-highpoint — buildup-payoff comparison on 1-5 scale
6. shenbi-review-sensitivity — platform rule application, prohibited word check
7. shenbi-review-long-span — 6-char n-gram repetition rate computation
8. shenbi-review-era — anachronism detection against declared time period
9. shenbi-review-fanfic — mode strictness (Canon/AU/OOC/CP)
10. shenbi-review-spinoff — timeline-aware information leakage

Each skill produces an audit report. After all complete, verify: cross-audit consistency (no contradictory findings), finding deduplication, severity alignment.
