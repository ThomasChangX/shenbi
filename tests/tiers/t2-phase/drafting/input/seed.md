# Drafting Phase Seed

Use the output from Planning phase as input (plans/chapter-1-plan.md, truth/pending_hooks.md, context/chapter-1-context.md).

Agent instructions:
1. Run shenbi-chapter-drafting with chapter-1-plan.md and context/chapter-1-context.md. Produces chapters/chapter-1.md with PRE_WRITE_CHECK and POST_WRITE_SELF_CHECK. Approve.
2. Run shenbi-state-settling on chapter-1.md. Updates truth/current_state.md, truth/character_matrix.md, truth/emotional_arcs.md, truth/chapter_summaries.md. Approve.
3. Run shenbi-foreshadowing-track on chapter-1.md. Updates truth/pending_hooks.md with state transitions and text evidence. Approve.
4. Run shenbi-style-polishing on chapter-1.md. Produces polished version with 润色说明 report. Approve.
5. Run shenbi-anti-detect on polished chapter-1.md. Produces anti-AI audited version with 改写报告. Approve.
6. Run shenbi-length-normalizing on audited chapter-1.md. Produces normalized version with 归一化报告. Approve.

After each skill, verify handoff integrity and that the chapter passes all quality gates.
