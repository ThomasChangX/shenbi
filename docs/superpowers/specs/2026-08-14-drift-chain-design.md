> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** skill_utils/drift_detection/ + chapter_loop.py | **核心洞察:** 语言漂移 3 层干预全链失效（未接线 + 门控 + 吞异常），且真实格式与检测假设分叉

# Drift 检测干预链失效

## R1 · establish_baseline 零调用（F602, P1；从属 F389）
- 证据：baseline.py:24 唯一写 `style/linguistic_baseline.json` 的函数全仓零调用；chapter_loop 每章走 no_linguistic_baseline 分支；plan 07-19-07 Task 5a 明确要求接线
- 修复：chapter 3 后接线 establish_baseline；**验收：第 4 章起 baseline 文件存在**

## R2 · 对话塌陷 off-by-one（F601, P1）
- 证据：linguistic_drift.py:215 `max(...,5.0)` vs :218 `> 5.0` → 对话塌陷 is_drift 恒 False
- 修复：`max(...,5.01)` 或 OR 条件；**验收：dialogue ratio<0.2 → is_drift=True**

## R3 · severity 阶梯被 is_drift 门控（F612, P1）
- 证据：chapter_loop.py:2023 `if result.is_drift:` 包裹全部干预；baseline 污染时 severity=ESCALATE 但 is_drift=False → 安全网静默放行
- 修复：按 `severity != NONE` 驱动干预；**验收：stm 110‰ 触发 ESCALATE**

## R4 · 调用点吞 DriftEscalationError（F620, P1）
- 证据：chapter_loop.py:2722-2727 `except Exception` 吞 raise（注释自称 non-blocking 与函数内 raise 矛盾）
- 修复：按异常类型处理或删除 raise；**验收：ESCALATE 到达暂停逻辑**

## R5 · 判据 12 真实格式分叉（F637, P1）
- 证据：真实 pending_hooks.md 无 `## hooks` YAML 块与 `## 活跃伏笔` 表（ch25→ch56 间格式分叉）→ 检测恒空转；测试 fixture 格式与真实分叉
- 修复：格式决策（恢复权威格式 or 更新解析器）+ 真实 fixture 测试；**验收：真实文件检出 drift**
