# Planning Phase Seed

Use the output from Architecture phase as input (outline/story_frame.md, outline/volume_map.md, outline/rhythm_principles.md, outline/thread_map.md, genre-config.json).

Agent instructions:
1. Run shenbi-chapter-planning for chapter 1 with Architecture output. Produces plans/chapter-1-plan.md with all 8 memo sections. Approve.
2. Run shenbi-foreshadowing-plant with chapter-1-plan.md. Produces truth/pending_hooks.md with planted hooks (≤8 operations). Approve.
3. Run shenbi-context-composing with chapter-1-plan.md and pending_hooks.md. Produces context/chapter-1-context.md with P1-P7 sections. Approve.

After each skill, verify handoff integrity: does the next skill find all required input files?
