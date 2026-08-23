> **Date:** 2026-08-14 | **Status:** Rejected (2026-08-24 · 纯 catalog 父条目，无独立可执行内容；catalog/排序角色已被 #40 正式取代——INDEX 登记「supersede #17 的 catalog 角色」；簇工作全部由子 spec #6-#16 与 2026-08-15 C 系列承接，子 spec 7 份活跃照常执行) | **Severity:** 🟥 4×P0 / 🟠 45×P1 / 🟡 318×P2 / ⚪ 98×M | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（总纲） | **依赖:** 无 | **范围:** 全仓库 | **核心洞察:** pipeline 存在 5 个独立"永不完成"根因 + 2 个数据丢失根因；G3/G4 门禁有效性被多机制击穿

# 2026-08-14 全项目审查 · 总纲（catalog）

## 覆盖统计
- tracked 文件 2738，deep-read 覆盖 100%（Z1-Z11 全部深读；Z7-Z11 覆盖方式见各子 spec）
- findings 467 条：P0×4 / P1×45 / P2×318 / M×98 / false-positive×1（F325）
- 去重后独立根因：10 簇（见 phase4-root-cause-clusters.md）

## 根因簇图（简版）
1. **pipeline 永不完成**（P0）：F324 volume_map 解析 / F353 total_chapters 自锁 / F371 closure 目录 G4 / F373 N 占位 G4 / F379 closure prompt-build —— 生产 56 章书实证停在 chapter-loop
2. **数据丢失**（P0）：F397 append_dedup no-op / F364 atexit 清 staging / F640 materialize 覆盖 / F326 并行写竞态
3. **门禁有效性**（P1）：F408 G3.4 伪造 / F345 并行波无 G3 / F401 GR.2 masking / F404 P2.5 空串 / F227 门序回归 / F163 G4 目录参
4. **契约信源断裂**（P1）：F0-02 deps.json 缺登记 / F201 契约模型 dead-wire / F218 字段过滤 / F115 rubric 过滤 no-op
5. **审计链失效**（P1）：F513 快照根错位 / F247 N 占位不一致 / F524 declared 无 chapter / F512 路径绕过
6. **drift 链失效**（P1）：F602 baseline 零调用 / F601 off-by-one / F612 门控 / F620 吞异常
7. **成本计量**（P0/P1）：F302 TokenLedger 接线不全 / F300 注入缓解 no-op
8. **配置治理绕过**（P1/P2）：F606/F611/F631/F643/F666/F635
9. **统计错误**（P2 大簇）：标点双计/熵失真/TTR/排比截断等
10. **文档漂移**（M 大簇）：计数/行号/契约文本

## 建议执行顺序
1. 簇 1 + 簇 2（P0，数据与完成性）
2. 簇 3（门禁可信）
3. 簇 5（审计可信）
4. 簇 4/6/7/8（契约/质量链）
5. 簇 9/10（统计与文档）

## 子 spec 清单
（阶段 5 逐条产出；每簇至少一个独立 spec，P2/M 按簇合并）
