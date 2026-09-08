# T1 派发层验证结论（spec #56 T1.1/T1.2 · 2026-09-08）

## T1.1 argv 断言（tests/unit/pipeline/test_dispatch_cli_argv.py）

- codex 分支：`_find_ide_cli()` argv[0]=codex，含 `sandbox_permissions=workspace-write`，7 模式元叙述 0 注入 ✓
- zcode 分支：与 codex 共享同一份 flag 面（`argv_zcode[1:] == argv_codex[1:]`）✓
- **deviation（zcode 专属 flag 未测）**：`dispatch_helper.py:2398` docstring 自认 "flags are codex-specific. zcode support requires separate testing"。zcode 分支由 argv 断言测试覆盖共享面；既有捕获产物 fixture 均出自 codex 形态 argv，zcode 独立产物例不可得（离线 F947 约束下不 dispatch 取样）
- 人工抽查：`### FILE:` 标记形态的既有 dispatch 产物样本（tests/fixtures 下 dispatch 输出）无元叙述注入 ✓

## T1.2 快照嵌埋核实（F1108 增量）

- `grep -rn "audit" src/shenbi/pipeline/ --include="*snapshot*"` → 0 命中（exit 1）
- `grep -rn "snapshots/" src/shenbi/pipeline/` → 恰 4 处良性命中：`chapter_loop.py:1691/1704`（manifest 加载/持久化）、`closure.py:115/180`（路径模板）——无审计全文嵌埋位点
- **结论**：快照内嵌审计全文纯属历史 manual-era dispatch 行为，现行代码无该路径 → 按 spec 记 deviation，不开发；快照体积收益归 T3.6 存量剥离
