# Bug-Hunt Report: shenbi-snapshot-manage

## Defect Detection Results

### Defect 1: Required truth file (particle_ledger) skipped from snapshot

- **Detected**: yes
- **Location**: `snapshot-report.md` — file list: "- truth/particle_ledger.md ✗ (SKIPPED — 文件过大，已排除)"
- **Violated Rule**: SKILL.md snapshot completeness — "快照必须包含全部 truth 文件。跳过任何 truth 文件为error级缺陷。'文件过大'不是跳过理由。"
- **Evidence**: The snapshot report lists particle_ledger.md as "✗ SKIPPED" with the justification "文件过大，已排除" (file too large, excluded). However, the snapshot protocol requires all truth files to be included — there is no "too large" exemption. The particle_ledger tracks灵能粒子 state changes and is critical for continuity verification. The snapshot claims to have 12 files but actually only includes 11 truth files, while still reporting completeness. The checksum verification was only done on chapter_summaries.md, not particle_ledger.md, so the skip is undetected by the self-check.
- **Severity**: error

## Summary

- **Total defects planted**: 1 (required file skipped from snapshot)
- **Defects detected**: 1/1
- **False positives**: 0

| # | Defect | Severity | SKILL.md Rule Violated |
|---|--------|----------|----------------------|
| 1 | particle_ledger.md skipped from snapshot | error | 快照完整性: 必须包含全部truth文件 |
