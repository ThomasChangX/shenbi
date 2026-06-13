# Audit Phase Seed

Use the output from Drafting phase as input (chapters/chapter-1.md, truth/*, characters/*, world/*).

Agent instructions:
Run all 18 review skills on the drafted chapter. These can run in parallel since they are independent:

1. shenbi-review-character — BDI coverage, voice fidelity check
2. shenbi-review-continuity — timeline extraction, cross-chapter comparison
3. shenbi-review-dialogue — voice fingerprint matching per speaker
4. shenbi-review-pacing — chapter type classification (QUEST/FIRE/CONSTELLATION)
5. shenbi-review-anti-ai — all 10 deterministic AI-pattern checks
6. shenbi-review-foreshadowing — hook lifecycle tracking with text evidence
7. shenbi-review-world-rules — numerical cross-reference against truth files
8. shenbi-review-sensitivity — platform rule application, prohibited word check
9. shenbi-review-memo-compliance — 8-section memo verification
10. shenbi-review-motivation — causal chain reconstruction
11. shenbi-review-pov — information leakage detection
12. shenbi-review-reader-pull — hook strength, chapter-end suspense classification
13. shenbi-review-highpoint — buildup-payoff comparison on 1-5 scale
14. shenbi-review-texture — laundry-list detection, sequential marker count
15. shenbi-review-long-span — 6-char n-gram repetition rate computation
16. shenbi-review-era — anachronism detection against declared time period
17. shenbi-review-fanfic — mode strictness (Canon/AU/OOC/CP)
18. shenbi-review-spinoff — timeline-aware information leakage

Each skill produces an audit report. After all complete, verify: cross-audit consistency (no contradictory findings), finding deduplication, severity alignment.
