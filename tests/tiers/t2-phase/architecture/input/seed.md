# Architecture Phase Seed

Use the output from Genesis phase as input (novel.json, genre-config.json, world/*, characters/*, truth/*).

Agent instructions:
1. Run shenbi-story-architecture with Genesis output. Produces outline/story_frame.md with three-layer conflict and dual-line structure. Approve.
2. Run shenbi-volume-outlining with story_frame.md. Produces outline/volume_map.md with per-volume Objectives and KRs. Approve.
3. Run shenbi-pacing-design with volume_map.md. Produces outline/rhythm_principles.md with 4-beat cycles and scene type catalog. Approve.
4. Run shenbi-plot-thread-weaver with rhythm_principles.md. Produces outline/thread_map.md with A/B/C line classification and advancement table. Approve.
5. Run shenbi-genre-config with all previous output. Updates genre-config.json with fatigue words, audit dimensions, chapter word defaults. Approve.

After each skill, verify handoff integrity: does the next skill find all required input files?
