# Bug-Hunt Report: shenbi-chapter-planning
**Date**: 2026-06-12
**Skill**: `skills/shenbi-chapter-planning/SKILL.md`
**Test type**: bug-hunt
**Result**: PASS -- all planted defects detected

## Detection Summary
| # | Finding | Severity | Evidence location | Detected |
|---|---------|----------|-------------------|---|
| 1 | Chapter memo missing section "读者此刻在等什么" (reader expectation management) | error | `outline/chapter-7-plan.md` L29 (section-2 heading slot occupied by wrong heading at L30) | YES |
| 2 | Chapter memo missing section "日常/过渡承担什么任务" (daily/transition task mapping) | error | `outline/chapter-7-plan.md` L41 (section-4 heading slot absent; file jumps from section 3 content to section 5 content) | YES |
| 3 | Chapter memo missing section "章尾必须发生的改变" (end-of-chapter change commitment) | error | `outline/chapter-7-plan.md` L59 (section-6 heading slot absent; file jumps from section 5 content to section 7 content) | YES |

## File Heading Structure (L1-L104)

The chapter-7-plan.md heading structure reveals the 3 gaps:

| Line | Actual Heading | Required Heading | Status |
|------|---------------|------------------|--------|
| L13 | `## 1. 当前任务` | `## 1. 当前任务` | CORRECT |
| L29 | *(absent -- gap)* | `## 2. 读者此刻在等什么` | **MISSING** |
| L30 | `## 2. 该兑现的 / 暂不掀的` | *(section 3 content)* | MISLABELED |
| L41 | *(absent -- gap)* | `## 4. 日常/过渡承担什么任务` | **MISSING** |
| L42 | `## 3. 关键抉择过三连问` | *(section 5 content)* | MISLABELED |
| L59 | *(absent -- gap)* | `## 6. 章尾必须发生的改变` | **MISSING** |
| L60 | `## 4. 本章 hook 账` | *(section 7 content)* | MISLABELED |
| L90 | `## 5. 不要做` | *(section 8 content)* | MISLABELED |

Only 5 of 8 required section headings exist in the file. The existing 5 headings are all renumbered (content from sections 3, 5, 7, 8 occupies positions 2, 3, 4, 5). Three required headings are entirely absent: sections 2, 4, and 6.

## Detection 1: Missing Section "读者此刻在等什么"
### Defect Location
`tests/rounds/round-003-2026-06-11/novel-output/shenbi-chapter-planning-bughunt/outline/chapter-7-plan.md` L29 -- the heading slot between section 1 (L13-L28) and the next heading (L30) does not contain the required "## 2. 读者此刻在等什么".

### Defect Description
The SKILL.md L90-L98 defines 8 required section headings with exact string matching. Section 2 "## 2. 读者此刻在等什么" must appear after section 1. In `chapter-7-plan.md`, section 1 "## 1. 当前任务" correctly occupies L13-L28. At L29, there is a blank line. At L30, the heading "## 2. 该兑现的 / 暂不掀的" appears -- this is section 3 content occupying the section 2 heading position. The required heading string "## 2. 读者此刻在等什么" does not appear anywhere between L1 and L104.

The absence is confirmed by three independent checks:
- **Heading string match**: The string "读者此刻在等什么" does not appear in the file (verified by full-text search across L1-L104)
- **Positional evidence**: The heading at the section-2 slot (L30) is "## 2. 该兑现的 / 暂不掀的", not the required "## 2. 读者此刻在等什么"
- **Structural count**: Only 5 headings exist in the file; 8 are required per SKILL.md L205

### Skill Rule Applied
**铁律一: NO CHAPTER WITHOUT A MEMO** -- "没有章节备忘就动笔 = 删除重来" (SKILL.md L34)

The SKILL.md L90-L98 defines the exact 8-section structure. SKILL.md L99 states: "缺任意一段即为不合格输出。" The 可自动检查的计数规则 at SKILL.md L205 specifies "段完整性 -- 8/8 段全部存在" as the first check item, with "缺任意段" as the unqualified condition.

**Evidence**:
- `chapter-7-plan.md` L13: `## 1. 当前任务` -- correct, section 1 heading
- `chapter-7-plan.md` L30: `## 2. 该兑现的 / 暂不掀的` -- wrong heading at section 2 position; the required string is `## 2. 读者此刻在等什么`
- SKILL.md L92: Required heading `## 2. 读者此刻在等什么`
- SKILL.md L99: "缺任意一段即为不合格输出"
- SKILL.md L205: "段完整性 -- 8/8 段全部存在 -- 缺任意段"

## Detection 2: Missing Section "日常/过渡承担什么任务"
### Defect Location
`tests/rounds/round-003-2026-06-11/novel-output/shenbi-chapter-planning-bughunt/outline/chapter-7-plan.md` L41 -- the heading slot between the content of section "该兑现的 / 暂不掀的" (L30-L40) and the next heading (L42) does not contain the required "## 4. 日常/过渡承担什么任务".

### Defect Description
The SKILL.md L94 requires section 4 "## 4. 日常/过渡承担什么任务" to appear after section 3. The file contains section 3 content at L30-L40 (under the mislabeled heading "## 2. 该兑现的 / 暂不掀的"). At L41, there is a blank line. At L42, the heading "## 3. 关键抉择过三连问" appears -- this is section 5 content occupying the section 3 heading position. The required heading "## 4. 日常/过渡承担什么任务" does not appear anywhere between L1 and L104.

The absence is confirmed by three independent checks:
- **Heading string match**: The string "日常/过渡承担什么任务" does not appear in the file (verified by full-text search across L1-L104)
- **Positional evidence**: The section-4 position (between L40 and L42) contains only a blank line; the file jumps from section 3 content to section 5 content with no section 4 heading
- **Structural count**: Only 5 headings exist in the file; 8 are required per SKILL.md L205

### Skill Rule Applied
**铁律一: NO CHAPTER WITHOUT A MEMO** -- same rule as Detection 1. Each missing section independently violates SKILL.md L99 ("缺任意一段即为不合格输出") and SKILL.md L205 (段完整性 check).

**Evidence**:
- `chapter-7-plan.md` L30-L40: Content of "该兑现的 / 暂不掀的" (actual section 3) under mislabeled heading "## 2"
- `chapter-7-plan.md` L42: `## 3. 关键抉择过三连问` -- section 5 content at position 3, proving section 4 heading is skipped
- `chapter-7-plan.md` L41: Blank line where "## 4. 日常/过渡承担什么任务" should appear
- SKILL.md L94: Required heading `## 4. 日常/过渡承担什么任务`
- SKILL.md L99: "缺任意一段即为不合格输出"

## Detection 3: Missing Section "章尾必须发生的改变"
### Defect Location
`tests/rounds/round-003-2026-06-11/novel-output/shenbi-chapter-planning-bughunt/outline/chapter-7-plan.md` L59 -- the heading slot between the content of section "关键抉择过三连问" (L42-L58) and the next heading (L60) does not contain the required "## 6. 章尾必须发生的改变".

### Defect Description
The SKILL.md L96 requires section 6 "## 6. 章尾必须发生的改变" to appear after section 5. The file contains section 5 content at L42-L58 (under the mislabeled heading "## 3. 关键抉择过三连问"). At L59, there is a blank line. At L60, the heading "## 4. 本章 hook 账" appears -- this is section 7 content occupying the section 4 heading position. The required heading "## 6. 章尾必须发生的改变" does not appear anywhere between L1 and L104.

The absence is confirmed by three independent checks:
- **Heading string match**: The string "章尾必须发生的改变" does not appear in the file (verified by full-text search across L1-L104)
- **Positional evidence**: The section-6 position (between L58 and L60) contains only a blank line; the file jumps from section 5 content to section 7 content with no section 6 heading
- **Structural count**: Only 5 headings exist in the file; 8 are required per SKILL.md L205

### Skill Rule Applied
**铁律一: NO CHAPTER WITHOUT A MEMO** -- same rule as Detections 1 and 2. Each missing section independently violates SKILL.md L99 ("缺任意一段即为不合格输出") and SKILL.md L205 (段完整性 check).

**Evidence**:
- `chapter-7-plan.md` L42-L58: Content of "关键抉择过三连问" (actual section 5) under mislabeled heading "## 3"
- `chapter-7-plan.md` L60: `## 4. 本章 hook 账` -- section 7 content at position 4, proving section 6 heading is skipped
- `chapter-7-plan.md` L59: Blank line where "## 6. 章尾必须发生的改变" should appear
- SKILL.md L96: Required heading `## 6. 章尾必须发生的改变`
- SKILL.md L99: "缺任意一段即为不合格输出"

## False Positive Check
Confirmed no clean content incorrectly flagged. Each existing section was individually verified:

- **Section 1 "当前任务" (L13-L28)**: Correctly populated with priority source declaration ("优先级来源: 卷纲 Key Result" at L15), conflict explanation (L17-L22), and specific actions (L24-L27). Passes SKILL.md L114 不合格条件 check (priority source not missing).

- **Section "该兑现的 / 暂不掀的" (L30-L40, mislabeled as section 2)**: Correctly lists兑现清单 (L32-L34) and 压住的底牌 (L36-L40). Content quality is not in question -- only the heading is misnumbered.

- **Section "关键抉择过三连问" (L42-L58, mislabeled as section 3)**: Correctly covers Why (L46-L51), Interest (L53), and Persona (L55-L58) for the core decision. Content is structurally valid per SKILL.md L148-L154.

- **Section "本章 hook 账" (L60-L88, mislabeled as section 4)**: Correct 4-column format (ID/操作/推进方式/沉默章数) at L66. 操作 values valid (advance/defer per SKILL.md L185). 沉默章数 numeric format correct. 激活方案 provided for 3 defer lines with 沉默章数 ≥ 4 (L82-L87). Phase 1 declaration present at L62-L63. Full hook density 9 operations within 8 budget.

- **Section "不要做" (L90-L104, mislabeled as section 5)**: Contains 7 valid avoidance items (L92-L103), all specific and actionable, not generic advice. Passes SKILL.md L200 "无" / "N/A" legality check.

The defect is strictly the absence of 3 required section headings. No existing content was incorrectly flagged, and no false positives were introduced.
