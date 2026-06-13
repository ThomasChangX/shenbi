# Management Phase Seed

Use the output from Drafting phase as input (chapters/chapter-1.md, truth/*, characters/*).

Agent instructions:
1. Run shenbi-snapshot-manage with current truth files. Creates snapshots/ snapshot with checksums for all 11 truth files. Approve.
2. Run shenbi-drift-guidance with audit reports and truth files. Produces truth/drift_guidance.md with ≤5 drift items, each with targeted_chapter and source audit reference. Approve.
3. Run shenbi-intent-management with drift_guidance.md and current_focus.md. Updates truth/author_intent.md and truth/current_focus.md with P0/P1/P2 priorities. Approve.
4. Run shenbi-chapter-pattern on chapter-1.md. Produces outline/chapter_patterns.md with pattern classification, entropy calculation, and next-chapter suggestions. Approve.
5. Run shenbi-volume-consolidation after all chapters in volume complete. Produces volumes/volume-1-summary.md (≤500 words) with unresolved hook list and per-chapter summaries. Approve.

After each skill, verify handoff integrity and that no truth file was modified without human approval.
