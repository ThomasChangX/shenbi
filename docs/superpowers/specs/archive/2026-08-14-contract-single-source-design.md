> **Date:** 2026-08-14 | **Status:** Done (PR #66) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查 | **依赖:** 无 | **范围:** contracts/ + skills/ + deps.json | **核心洞察:** 契约单一信源在多处断裂且 lint 有覆盖洞

# 契约单一信源断裂

## R1 · deps.json 缺 5 skill 登记（F0-02, P1；从属 F624）
- 证据：foreshadowing-lifecycle + 4 个 review-group-* 在 skills/ 与 truth-files.index.json、executor_config 有引用，但不在 deps.json；lint_repo_consistency 未抓
- 修复：lint 增加 skill 目录↔deps.json 闭包检查；登记或显式 out-of-pipeline；**验收：lint 对缺失登记报错**

## R2 · 三契约模型 dead-wire（F201, P1）
- 证据：chapter_planning/context_composing/volume_outlining 契约模型无生产消费者，g4 携带私有且规则不同的实现（双源发散）
- 修复：g4 消费契约模型或删除死模型；**验收：单源规则**

## R3 · 字段级 reads 部分匹配静默丢字段（F218, P1）
- 证据：fields.py 部分匹配时未命中字段无声、无 WARN、matched=True；AGENTS.md:87-89 契约"任一缺失 → 全文 + WARN"
- 修复：部分缺失同样 WARN（含缺失清单）；**验收：部分匹配 → WARN + 缺失清单**

## R4 · scoring 维度过滤 38/82 rubric no-op（F115, P1）
- 证据：解析器只认 `| Dimension scope |` 表头，38 个真实 rubric（含 4 个 N/A 豁免技能）静默返回全部维度；rubric 宣称 "renormalizes weights" 不成立
- 修复：兼容 `| # | Dimension |` 表 + 豁免语义；**验收：worldbuilding bug-hunt 排除 dim4**

## R5 · skills 计数漂移（F0-01, P2→P1 随簇）
- AGENTS.md/README/index 声称 69 vs 实际 74；改为动态生成或同步
