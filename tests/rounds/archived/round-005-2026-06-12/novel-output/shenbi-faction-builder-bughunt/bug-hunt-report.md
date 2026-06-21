# Bug-Hunt Report: shenbi-faction-builder

## Defect Detection Results

### Defect 1: Faction described as fully unified with zero internal dissent
- **Detected**: yes
- **Location**: `world/factions.md` — first faction section: "内部统一度: 100% — 派系内部意见完全一致，零异议，零分裂倾向"
- **Violated Rule**: SKILL.md internal split requirement — "每个势力必须包含至少一个内部分歧/派系"
- **Evidence**: The faction claims 100% unity with zero dissent. This violates the requirement that factions have internal structure with at least one point of disagreement.
- **Severity**: error

## Summary
- Defects planted: 1, Detected: 1/1, False positives: 0
