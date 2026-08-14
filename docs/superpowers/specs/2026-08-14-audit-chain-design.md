> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** audit/ + dispatcher/executor.py + pipeline/ | **核心洞察:** 支柱四写审计在主路径被绕过且快照根错位，双重失效

# 审计链失效

## R1 · 审计快照根错位（F513, P1；从属 F235）
- 证据：executor.py:244/264 `snapshot_tree(PROJECT_DIR, ...)` 快照框架仓库根而非 round_dir；技能实际写 round_dir → 比对错树；测试 monkeypatch 掩蔽
- 影响：写越权静默全过；仓库根 tracked truth 文件命中 glob → 假阳性 GATE_FAIL（F235）
- 修复：快照根改 round_dir；修正测试暴露错位；**验收：round_dir 写越权被拦截**

## R2 · 审计链 N 占位符不一致（F247, P1）
- 证据：`_audit_watch_paths` 带 chapter 解析 N，`_declared_patterns` 不带（chapter=None）→ 40 个 N 写技能恒判"未声明写入"
- 修复：declared 面解析 N 与 watch 对齐；**验收：chapter-drafting 派发 rc=0**

## R3 · declared 面不带 chapter（F524, P1）
- 证据：`_declared_patterns(skill)` 无 chapter → N/NNN 路径全丢弃 → 空目录幻影键即 violations（当前已活体触发）
- 修复：derive_output_files 带 chapter；**验收：chapter-parametric 技能审计 PASS**

## R4 · API/IDE 路径绕过写审计（F512, P1）
- 证据：dispatch_helper API/IDE 路径不调 write-audit，仅 legacy CLI 路径执行；docstring 与实际 routing 不符
- 修复：接线 API/IDE 路径或显式降级声明；**验收：API 派发产生 write-audit.jsonl**

## R5 · deleted/added 零拦截（F507, P1；F518）
- 证据：compute_file_change deleted/added 时 detail 全空 → check_write_ownership 全 level 无违规 → 删除/未授权键创建静默过审
- 修复：deleted/added 分支补检查；**验收：删除 OWNERSHIP 文件 → GATE_FAIL**
