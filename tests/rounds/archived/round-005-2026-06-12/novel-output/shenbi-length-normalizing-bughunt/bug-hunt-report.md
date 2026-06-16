# Bug-Hunt Report: shenbi-length-normalizing

## Defect Detection Results

### Defect 1: Teahouse scene ADDED to normalized chapter (new narrative content)

- **Detected**: yes
- **Location**: `chapter-draft.md` lines 86-91 (between "没人问他从哪来" paragraph and "巷子最尽头" paragraph)
- **Violated Rule**: 铁律 #1 — "不改变叙事内容 — 压缩/扩写不能增删事件、改变角色行为、影响伏笔"
- **Evidence**: The following passage exists in the NORMALIZED chapter (`chapter-draft.md`) but NOT in the ORIGINAL chapter (`chapter-draft-example.md`):

  > 巷子中段有一间茶馆。招牌上的字掉了两个，只剩"茶"和半个"楼"字。门口支着一块黑板，用粉笔歪歪扭扭写着今日特价。林烽推门进去，里面烟雾缭绕，七八张木桌坐了大半。角落里两个穿灰袍的男人压低声音说话，林烽经过时听到"北线第三军开拔"几个字。他没停，找了个靠墙的位置坐下。

  This constitutes:
  - A new event: Lin Feng visiting a teahouse (event addition)
  - New character behavior: intelligence-gathering "信息就是货币" (behavior addition)
  - New foreshadowing: "北线第三军开拔", "粮草不够" military movement hints (foreshadowing introduction)
  - New setting: teahouse with specific atmosphere details (setting addition)

- **Severity**: error

### Defect 2: Missing required 一致性检查 (consistency checklist) in normalization report

- **Detected**: yes
- **Location**: `normalization-report.md` — entire file contains no `### 一致性检查` section
- **Violated Rule**: SKILL.md 输出格式 — 字数归一化汇总 section must include `### 一致性检查` with six checkbox items (事件序列未变, 角色行为未变, 伏笔提及未变, 3000字底线, 25%底线, 两条底线)
- **Evidence**: SKILL.md defines the required output format including:

  ```
  ### 一致性检查
  - [ ] 事件序列未变
  - [ ] 角色行为未变
  - [ ] 伏笔提及未变
  - [ ] 3000 字底线已满足
  - [ ] 25% 底线已满足
  - [ ] 两条底线均满足（或已触发 REJECT）
  ```

  The `normalization-report.md` ends at `### 策略应用` and contains no `### 一致性检查` section.

- **Severity**: error

### Defect 3: Report falsely claims no changes while content was added

- **Detected**: yes
- **Location**: `normalization-report.md:8` — "归一化后字数: 4570 (变化: 0, 0%)"; line 30 — "无需处理：正文字数 4570 落在 3000-10000 可接受区间内"
- **Violated Rule**: 铁律 #1 — 输出格式准确性; the report should reflect actual state
- **Evidence**: The report claims zero changes, but the normalized chapter contains approximately 200+ characters of new narrative (teahouse scene) that are absent from the original. The word count "4570" was not recalculated after the scene was injected.

- **Severity**: error

### Defect 4: AI-typical phrasing check not applicable

- **Detected**: N/A (the injected teahouse scene does not contain AI-typical phrasing markers: 仿佛, 似乎, 不由得, 缓缓地, 微微, 不禁, 淡淡的, 嘴角微扬, 瞳孔微缩)
- **Violated Rule**: 铁律 #5 — "保持声音指纹 — 扩写/压缩不能引入 AI 味句式"
- **Evidence**: No AI-typical phrases found in the added teahouse scene content. The injected content uses concrete sensory details rather than abstract emotional markers.

- **Severity**: N/A (no violation detected for this rule in the injected content)

## Floor Gate Analysis (铁律 #3, #4)

The SKILL.md defines two numeric thresholds:
- **3000 字扩写线** (铁律 #2): Chapters < 3000 words trigger expansion
- **10000 字压缩线** (铁律 #3): Chapters > 10000 words trigger compression
- **压缩双底线** (铁律 #4): After compression, result must be ≥ 3000 AND ≥ 25% of original

**Assessment for this case**: The original chapter body is ~4570 Chinese characters, placing it firmly in the 3000-10000 acceptable range. Per SKILL.md flow diagram, the correct behavior is "Done — within acceptable range" with no normalization applied. The 25% floor gate (≥ 1142.5 characters = 4570 × 0.25) is not triggered because no compression occurred.

**Defect impact on floor gate**: Although the planted teahouse scene addition does not directly violate the floor gate (since no compression was performed), the normalization report's false claim of "变化: 0, 0%" masks the actual word count difference. If the added content were properly counted (~4800 characters), the chapter would still be within range, so no floor gate violation would occur. The defect is in reporting accuracy, not gate mechanics.

## Summary

- **Total defects planted**: 2 (teahouse scene addition + missing consistency checklist)
- **Defects detected**: 2/2 (both planted defects detected)
- **Additional findings**: 1 (falsely claimed zero changes)
- **False positives**: 0

| # | Defect | Severity | SKILL.md Rule Violated |
|---|--------|----------|----------------------|
| 1 | Teahouse scene ADDED to normalized chapter (new event, behavior, foreshadowing) | error | 铁律 #1: 不改变叙事内容 |
| 2 | Missing 一致性检查 checklist | error | 输出格式: 字数归一化汇总 |
| 3 | Report falsely claims zero changes | error | 铁律 #1 + 输出格式准确性 |
