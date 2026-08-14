# 全项目深度审查 · Final Report（2026-08-14）

> **状态**: 阶段 0-6 全部执行完成，G1-G6 通过，等待人类裁决（G7）
> **审查载体**: docs/superpowers/full-project-audit-prompt.md v2（2026-08-14 执行）

## 1. 覆盖统计

| 维度 | 数值 |
|---|---|
| tracked 文件（表 A） | 2738（全部 deep-read / self-artifact） |
| 磁盘产物（表 B） | 13 类（audited / generated-excluded / cache-ignored） |
| Z1-Z11 分区 | 全部初审 + 多轮独立复核（src 区 9-19 轮/区） |
| 线程 T1-T15 | 全部执行（15 条，98 findings） |
| G6 meta-audit | 228 样本 ok / 0 fake-deep-read / 0 覆盖空洞（Z11 4 处子声称修正） |
| 覆盖缺口（d1-06） | 1448 真实未覆盖行（85.16% cov 版本，修复 2 次污染事故） |

## 2. Findings 统计

| 严重度 | 数量 | 说明 |
|---|---|---|
| P0 | 5 | F324 volume_map 解析 / F397 append_dedup 数据丢失 / F364 atexit 清 staging / F302 TokenLedger 少计 / F1300 章节被摘要覆写 |
| P1 | 118 | 门禁击穿（G3.4 伪造/门序回归/GR.2 masking）、审计链失效、drift 链失效、注入链、fixtures 56% mock、契约断裂 |
| P2 | 483 | 边界/错误处理/统计错误/死代码/漂移 |
| M | 155 | 文案/命名/格式/过期注释 |
| false-positive | 1 | F325（复核反证撤销） |
| merged | 35 | 同根因去重合并 |

**总 findings: 761**（635 verified + 90 specced + 35 merged + 1 FP）

## 3. 核心根因簇（10 簇，详见 phase4-root-cause-clusters.md）

1. **pipeline 永不完成**（P0×5 独立根因）：volume_map 中文格式 / total_chapters 自锁 / closure 目录 G4 / N 占位 G4 / closure prompt-build——生产 56 章书实证停在 chapter-loop
2. **数据丢失**（P0×4）：append_dedup no-op / atexit 清 staging / materialize 覆盖 / 章节摘要覆写
3. **门禁有效性**（P1×8）：G3.4 伪造 scorer / 并行波无 G3 / 门序回归 / GR.2 masking / P2.5 空串 / G7.1b / G4 目录参
4. **契约信源断裂**（P1×5）：deps.json 缺 5 skill / 契约模型 dead-wire / 字段过滤死码 / rubric no-op / 计数漂移
5. **审计链失效**（P1×6）：快照根错位 / N 占位不一致 / declared 无 chapter / 路径绕过 / deleted 零拦截
6. **drift 链失效**（P1×5）：baseline 零调用 / off-by-one / 门控 / 吞异常 / 判据 12 格式
7. **成本计量**（P0/P1）：TokenLedger 接线不全 / 注入缓解 no-op
8. **配置治理绕过**（P1/P2×8）：4 绕过向量 + 治理层零接线
9. **确定性助手统计错误**（P2 大簇×21）：标点双计/熵/引号/TTR/排比
10. **文档漂移**（M 大簇）

## 4. 轮次历史（G4 收敛记录）

- Z1: 16 轮（13→9→5→6→4→6→1→2→6→2→3→2→2→0✓）
- Z2: 17 轮（20→6→8→3→7→1→2→3→2→2→1→3→4→2→2→1→2）——按人类裁决"无新 P0/P1"通过
- Z3: 19 轮 + 校准补复核（22→11→10→8→11→7→5→1→3→2→5→3→2→3→3→2→3→4→2）——按人类裁决通过
- Z4: 16 轮（19→12→9→6→10→6→3→11→3→4→2→3→4→2→1→2）——按人类裁决通过
- Z5: 6 轮（12→4→8→6→6→2→0✓）字面收敛
- Z6: 17 轮（11→8→10→7→3→3→1→3→2→5→2→2→2→1→2→2→2）——按人类裁决通过
- 线程 T1-T15: 各 1 轮

## 5. 产出

- 12 份 spec（1 总纲 + 10 子 spec + 1 M 批量）→ `docs/superpowers/specs/2026-08-14-*-design.md`
- INDEX 登记 14 活跃 spec（#6-#16 新增）
- 台账：coverage-ledger（G1 通过）/ findings-ledger（761）/ meta-audit.md（G6 通过）
- 中间产物：phase4-root-cause-clusters.md / d1/ 基线 12 项扫描 / zone-reports 50+ / thread-reports 15

## 6. 遗留风险（诚实声明）

1. **低置信度文件**：无整区低置信；Z11 类别级 2 处子声称已修正；F1316（config-change-log 等值条目）成因二义
2. **generated-excluded**：dist/ site/ tests/coverage/（可再生成已验证）
3. **未实机验证**：codex CLI 实机执行（环境无 codex 认证）、Windows 路径（nightly disabled）
4. **历史产物不可恢复**：novel-output ch2/9/12/44/55 正文被摘要覆写（P0 已录，修复防复发）
5. **共享 coverage.xml 写竞争**：审计期间 4 次被并行测试覆写（D1-02 族），修复为独占 COVERAGE_FILE 运行
6. **git 卫生**：96MB 孤儿 blob（T1501）、gh-pages 产物入库（T1502）、孤儿分支（T1503）——`git gc --prune=now` 可清

## 7. 建议执行顺序（阶段 5 spec 依赖拓扑）

1. 簇 1+2（P0：pipeline 完成性 + 数据丢失）
2. 簇 3（门禁可信）
3. 簇 5（审计可信）
4. 簇 4/6/7/8
5. 簇 9/10 + M 批量
