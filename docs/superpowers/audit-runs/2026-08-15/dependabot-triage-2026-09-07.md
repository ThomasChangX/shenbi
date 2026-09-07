# Dependabot Triage 记录 — 2026-09-07（spec #49 R4 · C35 · T1507）

> 范围声明：本文件只做**triage 决策记录**（每条 upgrade/close + 理由）。实际升级/合并不在 spec #49 范围
> （依赖升级动 uv.lock/生产代码，与「不碰生产代码」边界冲突），另开 chore 批次执行。
> 决策口径：workflow action 大版本跳代 = 升级（CI 基建，兼容面小）；deps-dev 补丁级 = 升级（低风险）；
> 大版本库跳代 = close 待专门批次；安全公告类 = urgent。

| PR | 依赖 | 决策 | 理由 |
|---|---|---|---|
| #87 | github/codeql-action 3→4 | **upgrade** | 大版本但 action 接口稳定，security workflow 基建，建议随 chore 批次最先处理 |
| #53 | pre-commit 4.6.0→4.6.2 | **upgrade** | 补丁级，低风险 |
| #52 | pytest 9.1.0→9.1.1 | **upgrade** | 补丁级，低风险 |
| #51 | coverage 7.14.1→7.15.4 | **upgrade** | 同 minor 内修订，低风险 |
| #50 | mkdocstring[python] >=0.24→>=1.0.6 | **close** | 跨大版本（0.x→1.x），docs 构建面广；待专门批次评估 1.0 破坏性变更后重开 |
| #49 | astral-sh/setup-uv 3→7 | **upgrade** | action 大版本跳代但 changelog 兼容；CI 基建，随 chore 批次 |
| #48 | hypothesis 6.155→6.165 | **upgrade** | 同 major 测试库常规更新，低风险 |
| #47 | actions/checkout 4→7 | **upgrade** | action 标准件，兼容；随 chore 批次 |
| #46 | actions/setup-node 4→7 | **upgrade** | 同上（如 docs workflow 仍需 node） |
| #45 | actions/dependency-review-action 4→5 | **upgrade** | security workflow 标准件，随 chore 批次 |

- **urgent**：无（本轮无安全公告型升级；codeql-action #87 建议优先但不属 urgent）
- 建议执行批次：一个 chore PR 统一升级 8 条 + close #50（注明理由），CI 全绿后合并
