# Foundation Phase Seed

Requires full mini-project with output from Genesis (world/*, characters/*), Architecture (outline/*), and Drafting (chapters/chapter-1.md, truth/*).

Agent instructions:
1. Run shenbi-foundation-review on the complete project. Produces foundation/review_report.md with 5-dimension scoring, concrete fix suggestions per file/paragraph. Core-conflict veto (<18/30) is unconditional. Approve.
2. Run shenbi-chapter-revision on chapter-1.md using audit findings. Produces chapters/chapter-1-revised.md with non-regression guarantee (blocking/critical/AI-trace counts must not increase). Approve.
3. Run shenbi-truth-sync on revised chapter. Updates truth/* with extracted facts, conflict detection, before/after diffs. Approve.
4. Run shenbi-style-learning on all chapters. Produces config/style_profile.md with 7 statistical dimensions (sentence length, paragraph length, dialogue ratio, etc.). Must be reproducible (same input → same output). Approve.

After each skill, verify: foundation-review threshold enforced, revision non-regression, truth-sync incremental, style-learning reproducible.
