> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟥 P0 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** cost/ + dispatch_helper.py | **核心洞察:** TokenLedger 系统性少计（决策表 P0 例字面命中），成本数据不可信

# TokenLedger 计量链

## R1 · 接线不全（F302, P0；从属 F531/F532）
- 证据：dispatch_skill(state=) 仅 chapter_loop.py:2794 一处传 state；genesis/closure/triggers/并行 post-draft/审计波均未传 → TokenLedger 少计大部分调用；`getattr(state,"chapter",0)` 恒 0（PipelineState 无 chapter 属性）→ by_chapter 全坍缩 "0" 桶
- 修复：全调用路径传 state；chapter 从 chapter_loop.current_chapter 取；**验收：真实 pipeline 运行后 token-ledger.jsonl 覆盖全部 dispatch**

## R2 · 注入缓解 no-op（F300, P1）
- 证据：dispatch_helper.py:734 `content.replace("<", "\u003c")`——Python 字符串字面量 `"\u003c"` 就是 `"<"`，恒等替换；注释声称防 </document> 标签注入
- 修复：转义为 `"\\u003c"` 或 `"&lt;"` 等真实转义；**验收：`<` 被替换**
