# Short Story Phase Seed

Use `tests/fixtures/outline-example.md` as the seed outline (independent of other phases).

Agent instructions:
1. Run shenbi-short-outline with the outline. Produces short/outline.md with 3-step enforcement (generate → review → revise), act proportioning (20/60/20), and chapter tasks. Approve.
2. Run shenbi-short-drafting with short/outline.md. Produces short/chapter-*.md chapters sequentially (strictly in order). Each chapter must pass all audit checks before next chapter starts. 3-round revision cap per chapter. Approve.
3. Run shenbi-short-packaging with all short chapters. Produces short/package.md with 3-5 titles, 2-3 blurbs, 3-5 evidence-backed selling points, and cover prompts. No act-3 spoilers in blurbs. Approve.

After each skill, verify handoff integrity: outline → drafting consistency, packaging matches story content.
