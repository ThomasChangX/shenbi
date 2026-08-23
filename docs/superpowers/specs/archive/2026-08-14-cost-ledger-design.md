> **Date:** 2026-08-14 | **Status:** Rejected (2026-08-24 · R1 已由 PR #39 修复；R2 与活跃 spec #45/C31 R2（F308）重复立案，F300 归属 #45 唯一所有) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** dispatch_helper.py | **核心洞察:** 标签注入缓解是恒等替换 no-op，声明的安全缓解未生效
> **Revised 2026-08-24（SDD #12 价值门）**：原 R1（F302 TokenLedger 接线不全，P0）已由 0d36d31（C10 T1+T2，PR #39）在 main 完整修复——ledger 记账移入 `_dispatch_via_api`（dispatch_helper.py:1722/:1778 双调用点，无 state 门槛），chapter 从 `path_ctx.chapter`/`extract_chapter` 取（:1656-1660，不再 `getattr(state,"chapter",0)` 恒 0），测试 `tests/pipeline/test_dispatch_helper_ledger.py` 覆盖。R1 删除。
> **Rejected 2026-08-24（SDD #12 阶段 3 设计审查发现 + 回阶段 1 改判）**：残留 R2（F300，dispatch_helper.py:752 恒等替换 no-op）与活跃 spec #45（`2026-08-16-c31-injection-authorization-design.md`）R2「转义修复（F308）」指向同一行、同一修法，且 #45 验收更宽（全仓 `replace(x, esc(x))` 形态零残留 + `</document>` 不截断解析回归 + T1201 判定伪造簇联动）。首过价值门未检出系两批审计 F 编号体系不同（2026-08-14 F300 vs 2026-08-15 C31 F308）。F300 归属 #45 唯一所有，本 spec 驳回收档。执行 #45 时注意：F300/F308 同源，C31 R2 完成即同时闭合两者。

# 文档包装注入缓解（已驳回）

## R2 · 注入缓解 no-op（F300, P1）→ 归属 spec #45/C31 R2
- 证据：dispatch_helper.py:752 `content.replace("<", "\u003c")`——Python 字符串字面量 `"\u003c"` 就是 `"<"`，恒等替换；注释（:749-751）声称防 `</document>` 标签注入，:753 直接把 safe_content 拼进 `<document>` wrapper，`<` 原样穿透
- 修复：见 spec #45 R2（`&lt;` / CDATA / 真实转义 + 全仓清剿）
