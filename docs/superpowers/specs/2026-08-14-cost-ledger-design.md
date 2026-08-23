> **Date:** 2026-08-14 | **Status:** Design (Revised 2026-08-24) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** dispatch_helper.py | **核心洞察:** 标签注入缓解是恒等替换 no-op，声明的安全缓解未生效
> **Revised 2026-08-24（SDD #12 价值门）**：原 R1（F302 TokenLedger 接线不全，P0）已由 0d36d31（C10 T1+T2，PR #39）在 main 完整修复——ledger 记账移入 `_dispatch_via_api`（dispatch_helper.py:1722/:1778 双调用点，无 state 门槛），chapter 从 `path_ctx.chapter`/`extract_chapter` 取（:1656-1660，不再 `getattr(state,"chapter",0)` 恒 0），测试 `tests/pipeline/test_dispatch_helper_ledger.py` 覆盖。R1 删除。残留仅 R2。

# 文档包装注入缓解

## R2 · 注入缓解 no-op（F300, P1）
- 证据：dispatch_helper.py:752 `content.replace("<", "\u003c")`——Python 字符串字面量 `"\u003c"` 就是 `"<"`，恒等替换；注释（:749-751）声称防 `</document>` 标签注入，:753 直接把 safe_content 拼进 `<document>` wrapper，`<` 原样穿透
- 修复：转义为 `"\\u003c"`（真实反斜杠转义序列）；**验收：`<` 被替换为非 `<` 的可见序列，有回归测试锁定**
