> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 4/7） | **依赖:** data-loss-cluster | **范围:** truth 文件写路径（write_truth_file/upsert/staging/契约语义）| **核心洞察:** 双写者键格式漂移（T7-01）、结构化记录丢失（T7-02）、staging/committed 分叉（T7-03）、契约自相矛盾（T7-06）

# Truth 写路径（补齐 D）

## R1 · resonance_trend 双写者键格式统一（T7-01, P1）
- 证据：框架写者 7 列键 `Ch{N}` vs skill 写者 9 列键 `{N}`；真实文件 ch55 出现 2 行
- 修复：单写者或统一键格式；key_field 形参接线（当前死代码）；**验收：真实文件无重复行**

## R2 · pending_hooks 结构化记录恢复（T7-02, P1）
- 证据：ch53 快照 22 条 hooks → 当前 0 条；全部 frontmatter 读取器静默空读；G6.7 垃圾解析假 hook
- 修复：权威格式决策（YAML frontmatter vs body 表）→ 恢复数据 + 读取器统一；**验收：hooks 记录可被全部读取器消费**

## R3 · staging/committed 分叉治理（T7-03, P1）
- 证据：staging/pending_hooks 与 truth/pending_hooks 对 P0-9 计算冲突；G4 校验 staging 而下游读 committed；clear_staging 未生效（staging/plans 残留 111 个）
- 修复：G4 校验 committed 或提交后重校验；clear_staging 修复；**验收：staging 清空后 committed 与 staging 一致**

## R4 · state-settling 契约权威语义裁决（T7-06, P1）
- 证据：frontmatter append_dedup vs 正文 replace 自相矛盾——F397 修复前置
- 修复：裁决权威语义（建议 append_dedup 累积 + 显式快照文件）并同步 frontmatter/正文/实现；**验收：契约三处一致**

## P2 清单
- **T7-04（P2）** LLM 元叙述 + 未闭合代码栅栏泄漏进 truth 文件；后写完整性检查只覆盖章节/审计，truth 文件从不检查
- **T7-05（P2）** `update_mode:` frontmatter 契约"写一次、读零次、生产全缺"
