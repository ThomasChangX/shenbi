> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 3/7） | **依赖:** 无 | **范围:** novel-output 产物契约（章节格式/truth 注册表/审计产物/滞留文件）| **核心洞察:** 真实项目产物与显式契约大面积背离（章节头/META/注册表），registry 三源分裂

# 产物契约（Z11 补齐 C）

## R1 · 章节格式契约对齐（F1301/F1302, P1）
- 证据：56/56 无 `# Chapter N:` 头（0 命中契约正则）；6 章无 META 块 + ch40 用 `## META` YAML 自创格式
- 修复：格式化器强制章节头/META 块（写入路径校验），存量文件批量修复或显式豁免；**验收：56 章 100% 契约符合**

## R2 · truth registry 三源合一（F1307, P1；F1322, M）
- 证据：根 truth/（bridge_tracker + character_matrix）不在 truth-files.yaml；state_snapshot-pre-rev.md（tracked）也未登记
- 修复：registry 补登记全部 tracked truth 文件或移出；根 truth/ 清理测试残留；**验收：git tracked truth 文件 ↔ registry 双向闭合**

## R3 · 状态/账本产物契约（F1309/F1310/F1313, P1——F640/F324/F302 的产物侧实证）
- 证据：progress.json 空壳仅 scorer 字段（F1309，F640 materialize 零生产者实证）；closure=pending + closure_step=0 + total_chapters 缺位（F1310，簇 1 实证）；cost/token-ledger.jsonl 不存在（F1313，F302 死接线验证）
- 修复：随 F640（materialize 接线/删除调用点）、F324（total_chapters 写入）、F302（TokenLedger 全链接线）一并修复；产物契约纳入 G1 校验
- **验收：真实项目 progress.json 含完整进度；token-ledger.jsonl 存在且有记录**

## P2 清单（审计产物/滞留/漂移）
- **F1308（P2）** staging truth 与正式 truth 内容不一致（pending_hooks 9886 vs 4171）
- **F1311（P2）** audit_reports 状态记录与磁盘 117 个审计文件脱节（resonance+review-summary 全缺）
- **F1312（P2）** 双 resonance gate-marker：`G4-review-resonance-generative.json` 为验证运行写入的污染 marker
- **F1314（P2）** audits 722 无内容重复，但 texture 维度配置=true 而磁盘 0 文件 + sensitivity 双发（F329 实证）
- **F1315（P2）** ch56 审计不完整：6/13 维缺失（dialogue/motivation/resonance/review-summary/sensitivity/world-rules）+ ch56 无 audit_reports 记录
- **F1316（P2）** config-change-log.jsonl 单条无操作条目（old=true/new=true）且时间戳晚于运行结束
- **F1317（P2）** write-audit/trace.jsonl 记录与 GATE_FAIL 语义一致但 root truth 残留仍落盘
- **F1321（P2）** plan-decisions 全部滞留 staging（55 个），plans/ 零 decisions；ch54 缺 plan-decisions

## M 清单（并入 M 批量 spec）
- **F1322（M）** truth/state_snapshot-pre-rev.md（git tracked 生产文件，2026-07-17 旧版管线 pre-revision 快照，src 0 引用、当前代码无 producer）未登记 truth-files.yaml——registry 三源分裂家族第 3 实例（F1307 根 truth/ 2 文件 + 本项目 truth 1 文件），契约词表缺口 + 写所有权/审计覆盖盲区
