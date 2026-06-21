# Bug-Hunt Report: shenbi-short-drafting

## Defect Detection Results

### Defect 1: Sequential generation violation — chapter 3 drafted before chapter 2's truth files existed

- **Detected**: yes
- **Location**: `generation-log.md` lines 7-8 — "T+45min 开始生成第3章" vs "T+52min 第2章 truth 文件写入完成"
- **Violated Rule**: 铁律 #1 — "批量生成必须按顺序 — 第1章先于第2章，禁止并行生成（依赖前一章状态）"
- **Evidence**: The generation log shows chapter 3 generation started at T+45min, but chapter 2's truth files (chapter-summaries, pending-hooks) were not written until T+52min. This means chapter 3 was generated without chapter 2's state information, violating the sequential dependency requirement.
- **Severity**: error

### Defect 2: Cross-chapter consistency failure — cloak color changed from crimson (ch4) to blue (ch6) with no transition

- **Detected**: yes
- **Location**: `chapters/chapter-4.md:3` — "那件深红色的斗篷"; `chapters/chapter-6.md:11` — "那件蓝色的斗篷"
- **Violated Rule**: 铁律 #4 — "跨章一致性必查 — 修订后必须重读相邻 2 章确认一致性"; 铁律 #5 — "整书风格统一"
- **Evidence**: Chapter 4 describes Lin Feng's cloak as "深红色" (crimson/deep red), while chapter 6 describes it as "蓝色" (blue). No scene between chapters 4-6 describes a clothing change or market purchase that would explain the color transition. This is a prop/position inconsistency that should have been caught during cross-chapter consistency checks.
- **Severity**: error

### Defect 3: Per-chapter audit skipped for chapter 8 — "rushed schedule" excuse

- **Detected**: yes
- **Location**: `batch-summary.md:14` — chapter 8 row shows "skipped — rushed schedule" instead of audit results
- **Violated Rule**: 铁律 #2 — "每章独立审计 — 起草后逐章过审计链路"; 铁律 #3 — "修订不超过 3 轮"
- **Evidence**: The batch summary explicitly marks chapter 8's audit as "skipped — rushed schedule" with 0 revision rounds. The SKILL.md requires every chapter to pass through the full audit chain (memo-compliance, anti-ai, character, motivation, pacing, continuity) before acceptance. No chapter may skip auditing regardless of schedule pressure.
- **Severity**: error

## Summary

- **Total defects planted**: 3 (out-of-order generation, cross-chapter inconsistency, skipped audit)
- **Defects detected**: 3/3 (all planted defects detected)
- **False positives**: 0

| # | Defect | Severity | SKILL.md Rule Violated |
|---|--------|----------|----------------------|
| 1 | Sequential generation violation (ch3 before ch2 truth) | error | 铁律 #1: 批量生成必须按顺序 |
| 2 | Cross-chapter consistency failure (crimson→blue cloak) | error | 铁律 #4: 跨章一致性必查 |
| 3 | Skipped audit for chapter 8 | error | 铁律 #2: 每章独立审计 |
