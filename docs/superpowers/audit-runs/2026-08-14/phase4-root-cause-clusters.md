# 阶段 4 根因簇图（2026-08-14）

> 去重后独立根因簇。每簇 = 一个 spec 单元；括号内为成员 findings（主条目加粗）。

## 簇 1 · pipeline 永不完成（P0 族，5 个独立根因）
- **F324**（volume_map 中文格式 vs 英文解析器 → 卷边界全家失效 + total_chapters 永不写入）
- **F353**（total_chapters 写点自锁：两写点都在 total>0 守卫内）
- **F371**（closure step 10 `final-snapshot/` 目录 G4 恒 FAIL）
- **F373**（N 型触发步骤 G4 用未解析占位路径 → not_found）
- **F379**（closure 5/10 步 prompt 构建期 UnresolvedPathError）→ 从属：F313/F380/F3B5/F245
- 生产佐证：56 章书停在 chapter-loop、closure_step=0、total_chapters=None

## 簇 2 · 数据丢失（P0）
- **F397**（state-settling append_dedup 契约 vs 整文件覆写实现 → 累积 truth 每章丢失）→ 从属：F312
- **F364**（atexit 正常退出清 staging + 篡改 current_step → 人审产物作废）→ 从属：F3B6（钩子累积）/F3B7（无锁写）
- **F640**（materialize_progress 零生产者 → 调用即覆盖 progress.json）
- **F326**（并行 post-draft 双线程写 pending_hooks lost-update）→ 从属：F505/F3A4/F253
- 生产佐证：chapter_summaries.md 仅 2/56 章条目

## 簇 3 · 门禁有效性（P0/P1）
- **F408**（run_gate_g3 伪造 scorer 证据击穿 G3.4）→ 从属：F214/F3AF
- **F345**（并行审计波完全绕过 G3）
- **F444**（G3.3 output_files 无生产者 → 恒 SKIP）
- **F401**（GR.2 -scores 后缀误报 + 测试 masking）
- **F404**（P2.5 rationale 空串绕过）→ 从属：F458/F232
- **F216**（genre_config disabled 维度 customRules 空跳过）
- **F432**（ALL_SKILLS 74 vs scaffold 69 → G7.1b 恒 FAIL）
- **F227**（executor G1/G2 门序回归：先校验后执行）→ 从属：F246
- **F163**（phase_runner G4 第 3 参 round_dir vs project-output → T2 永久阻塞）

## 簇 4 · 契约/信源断裂（P1）
- **F0-02**（deps.json 缺 5 skill + lint 覆盖洞）→ 从属：F624
- **F201**（三契约模型 dead-wire + g4 私有规则发散）
- **F218**（字段级 reads 部分匹配静默丢字段）
- **F115**（scoring 维度过滤 38/82 rubric no-op）
- **F0-01**（skills 计数漂移 69 vs 74）
- **F637**（判据 12 真实格式分叉恒空转）

## 簇 5 · 审计链失效（P1）
- **F513**（审计快照根错位 PROJECT_DIR）→ 从属：F235
- **F247**（审计链 N 占位符解析不一致）
- **F524**（declared 面不带 chapter → 假阳性 GATE_FAIL）
- **F512**（API/IDE 路径绕过写审计）
- **F507**（deleted 零拦截）
- **F301**（并行波使串行审计路径不可达）
- **F354**（并行波吞审计失败）
- **F500**（scoring_bridge dead-wire）/ **F501**（escalation_bridge dead-wire）

## 簇 6 · drift/语言质量链失效（P1）
- **F602**（establish_baseline 零调用）→ 从属：F389
- **F601**（对话塌陷 off-by-one）
- **F612**（severity 阶梯被 is_drift 门控）
- **F620**（调用点 except Exception 吞 DriftEscalationError）
- **F636**（0→正值映射 6.0x 假阳性）
- **F637**（判据 12 格式分叉，同簇 4）

## 簇 7 · TokenLedger/成本计量（P0/P1）
- **F302**（TokenLedger 接线不全）→ 从属：F531/F532
- **F300**（\u003c 转义 no-op 注入缓解失效）
- 其余：F519/F525/F533/F505 各独立机制

## 簇 8 · 配置治理绕过（P1/P2）
- **F606**（floor 类型孔）/ **F611**（auditDimensions 整键绕过）/ **F631**（falsy 绕过）/ **F643**（键缺失语义矛盾）/ **F666**（整键标量崩溃）/ **F635**（治理层零接线）
- **F614**（audit-trail 幻影条目）

## 簇 9 · 确定性助手统计错误（P2 大簇）
- F604/F613（标点双计）、F605（空正则）、F608（引号恒 0）、F621（熵分母）、F645（TTR 引号）、F656（排比截断）、F659（双实现分叉）、F667/F668/F634/F633/F628 等

## 簇 10 · 文档/计数漂移（M 大簇）
- F0-03/F0-04/F0-05/F0-07/F0-08、F217（CONSTELLATION 多源）、F415/F416/F318 等

## 执行顺序建议（依赖拓扑）
1. **簇 1**（F324/F353/F371/F373/F379 修复）+ 簇 2（F397/F364/F640/F326）——数据与完成性
2. **簇 3**（F408/F227/F401/F404）——门禁可信
3. **簇 5**（F513/F247/F524）——审计可信
4. **簇 4/6/7/8**——契约/质量链
5. **簇 9/10**——统计与文档
