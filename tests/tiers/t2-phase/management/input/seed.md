# Management Phase Seed

Use the output from Drafting phase as input (chapters/chapter-1.md, truth/*, characters/*).

Agent instructions:
1. Run shenbi-snapshot-manage with current truth files. Creates snapshots/ snapshot with checksums for all truth files registered in truth-files.yaml. Approve.
2. Run shenbi-drift-guidance with audit reports and truth files. Produces truth/drift_guidance.md with ≤5 drift items, each with targeted_chapter and source audit reference. Approve.
3. Run shenbi-intent-management with drift_guidance.md and current_focus.md. Updates truth/author_intent.md and truth/current_focus.md with P0/P1/P2 priorities. Approve.
4. Run shenbi-chapter-pattern on chapter-1.md. Produces outline/chapter_patterns.md with pattern classification, entropy calculation, and next-chapter suggestions. Approve.
5. Run shenbi-volume-consolidation after all chapters in volume complete. Produces volumes/volume-1-summary.md (≤500 words) with unresolved hook list and per-chapter summaries. Approve.
6. Run shenbi-memory-distill with current truth files. Produces truth/arcs/arc-1.md and truth/book_strata.md. Approve.
7. Run shenbi-review-arc-payoff with volume chapters. Produces audits/volume-1-payoff.md. Approve.
8. Run shenbi-score-stratum on the volume. Produces audits/stratum-1-score.md. Approve.
9. Run shenbi-score-volume on the volume. Produces audits/volume-1-score.md. Approve.

After each skill, verify handoff integrity and that no truth file was modified without human approval.
