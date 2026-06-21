# Bug-Hunt Report: shenbi-writing-skills

## Defect Detection Results

### Defect 1: POV switch limit rule changed from hard cap to unrestricted

- **Detected**: yes
- **Location**: `shenbi-pov-transition.md` — 铁律 section, rule 1: "单章 POV 切换无上限 — 视角切换数量由创作自由度决定，无硬性限制"
- **Violated Rule**: SKILL.md iron rule — "单章 POV 切换上限为 3 次。超过 3 次切换 = 读者认知负担崩溃，MUST 合并或删除视角。"
- **Evidence**: The original iron rule establishing a hard cap of 3 POV switches per chapter has been replaced with a permissive "无上限" (no limit) rule that defers to "创作自由度" (creative freedom). This directly contradicts the SKILL.md's core POV management rule, which treats the 3-switch cap as a MUST-level constraint to prevent reader cognitive overload. Changing a MUST to a suggestion fundamentally undermines the skill's purpose.
- **Severity**: error

## Summary

- **Total defects planted**: 1 (POV switch limit rule removed)
- **Defects detected**: 1/1
- **False positives**: 0

| # | Defect | Severity | SKILL.md Rule Violated |
|---|--------|----------|----------------------|
| 1 | POV switch cap changed from 3 to unlimited | error | 铁律: 单章POV切换上限为3次 |
