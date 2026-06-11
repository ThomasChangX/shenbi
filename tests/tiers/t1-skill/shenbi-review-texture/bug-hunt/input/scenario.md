# Bug-Hunt Test: shenbi-review-texture

## Skill Under Test
`skills/shenbi-review-texture/SKILL.md`

## Test Setup
A novel project exists with drafted chapter 7 at `drafts/chapter-7.md`. The chapter contains a paragraph (paragraph 11) that reads: "然后他走进房间，接着看到了桌上的信，之后他拿起信封，随后他打开了信纸，然后他开始阅读上面的文字。" This single paragraph contains 4 sequential markers (然后×2, 接着×1, 之后×1, 随后×1) and zero conflict or tension.

## Scenario
The agent runs a texture audit on chapter 7. The audit report at `audit/texture-review-ch7.md` does not flag paragraph 11 as a laundry-list violation. Despite the paragraph having 4 sequential markers and zero conflict, it is not identified as a problem.

## Planted Defect

| Location | Defect | Expected severity |
|----------|--------|-------------------|
| `drafts/chapter-7.md`: paragraph 11 | Laundry-list paragraph not flagged — 4 sequential markers (然后×2, 接着×1, 之后×1, 随后×1) with zero conflict in a single paragraph; exceeds ≥3 threshold | error |

## Agent Task
Run shenbi-review-texture audit on chapter 7. Find the planted defect where a laundry-list paragraph is not flagged.
