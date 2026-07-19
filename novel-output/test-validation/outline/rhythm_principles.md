Done. Produced all three skeleton files per the `shenbi-story-architecture` contract.

**What was generated**

- `outline/story_frame.md` — YAML frontmatter with the three-layer conflict definitions (surface: 三方源脉争夺 / personal: 苏衍的清醒即罪证 / deep: 神罚还是人祸), plus the four required prose paragraphs (前台故事, 后台故事, 主角旅程, 暗流伏笔种子 — six foreshadowing seeds mapped to 卷一埋/卷二显/卷三爆).
- `outline/volume_map.md` — 3 volumes × 15 chapters = 45 chapters, each volume decomposed into 3 KRs of 5 chapters with per-chapter nodes (开篇/承接/转折/收官), 节奏原则, and 跨卷衔接. Ending at ch45 aligns with `novel.json` ("找到立足之地，开始组织反抗").
- `outline/rhythm_principles.md` — skeleton only: 知识惊悚 pacing philosophy, per-volume chapter-type rough ratios, golden-opening 3-chapter beat, golden-finger cost rhythm (rule-001), and an explicit handoff to `shenbi-pacing-design` for all detailed tension curves and consecutive-limit checks (authoritative source: `genre-config.json`).

**Two notes for your review**

- I treated `novel.json` `target_word_count: 3000` as per-chapter (45 chapters × 3000 ≈ 135k words for the first arc). If it was meant as a total cap, the volume map will need to shrink — flag me and I'll re-scale.
- The task's explicit "Files to create" list named only the three files, and the skill's `contract.writes` lists no decisions sidecar, so I did **not** emit a `*-decisions.json`. The `shenbi-decisions-v1` schema also requires a `chapter: int` field that doesn't fit a pre-chapter planning skill. Say the word if your pipeline expects a sidecar anyway and I'll add one.
