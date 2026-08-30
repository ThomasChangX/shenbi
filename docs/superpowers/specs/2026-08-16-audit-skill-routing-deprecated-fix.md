> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C21）| **代表 finding:** F873 | **簇规模:** 12 条 | **严重度上限:** P1
> **范围:** skills/using-shenbi/SKILL.md（触发表）、tests/tiers/deps.json、GENESIS_STEPS、5+ 个技能 description、DEPRECATED 技能正文 | **证据等级:** 实验佐证（Z8-a/b/c/review-r1，F873/F887 verified）
> **与既有 spec 关系:** #23 的 DEPRECATED 接线拆除面（F904/F950/F1004）并入本 spec；#9 的 deps.json 补登归 C22 词表对账，本 spec 只管路由/触发/描述契约；#23 驳斥归档时补登其残留 **F905 双重调度语义面**（见 T1.6）

# C21 · 技能注册与触发路由漂移修复（skill-routing-deprecated）

## 背景（根因 + 证据）

**根因**：技能退役走了"标 DEPRECATED"半步就停——deps.json 仍注册、using-shenbi 触发表仍路由（14 个 DEPRECATED 技能）、GENESIS_STEPS 仍派发，后继技能（group-*、foreshadowing-lifecycle）零触发行；同时 description 契约（AGENTS.md：仅 when-to-use 触发条件）大面积违反——旧技能还在被路由、新技能没人路由得到，触发体系指向已死链路。

代表证据：
- **F873**（P1，verified）：using-shenbi 触发表路由 **14 个 DEPRECATED 技能**，默认审计列 3 个 DEPRECATED，且 **0 处路由到 group-*/foreshadowing-lifecycle 后继**
- **F887**（P1）：GENESIS_STEPS 仍派发 DEPRECATED 的 shenbi-foreshadowing-plant；另有 3 处正文把 track/plant 当现行链路引用
- **F816**（P1）：foreshadowing-plant DEPRECATED 但 using-shenbi 触发表与 deps.json 仍路由/注册（lifecycle 未进触发表）
- **F834**（P1）：触发映射路由 8 个 DEPRECATED 且 4 个 group-* 替代者零触发行；DEPRECATED 正文仍自称"默认激活/每章必查"
- **F835**（P1）：4 个 review-group-* 的 description 全部描述"做什么/怎么调度"，无 "Use when" 触发条件
- **F877**（P1）：shenbi-writing-skills description 含功能描述从句，违反自身与 AGENTS.md 契约
- **F815**（P1）：foreshadowing-lifecycle description 非触发式；lifecycle-states.md/hook-types.md 相对引用落在他 skill 目录；Phase3 初始态 ACTIVE 与自身输出示例 PLANTED 矛盾；bridge_tracker.md 与 audits 输出写未声明
- P2：F355（OPTIONAL_READS 含已移除技能死条目）、F817（foreshadowing-recall DEPRECATED 仍注册 + "last_reinformed" 拼写漂移）、F819（foreshadowing-track DEPRECATED 仍注册 + 字段分工与 DOT 矛盾 + 死引用）、F842（location-builder description 含功能子句）、F878（using-shenbi description 功能从句，较轻）

## 目标

1. **路由一致**：触发表/deps.json/GENESIS_STEPS 三处对 DEPRECATED 技能零路由、零注册、零派发；后继技能全部有触发行
2. **description 契约合规**：全仓 74 个 skill 的 description 仅为 when-to-use 触发条件（≤500 字符，AGENTS.md 契约），违规者改写
3. 防回潮：lint 检查"DEPRECATED ⇒ 不得出现在任何路由面"+"description 契约"

## 任务分解

### T1 · 触发表与派发面拆除（P1 核心）
1. using-shenbi 触发表：删 14 个 DEPRECATED 路由行（F873/F834）；为 4 个 group-* 与 foreshadowing-lifecycle 补触发行（含默认审计列同步——3 个 DEPRECATED 出列、后继进列）
2. GENESIS_STEPS：foreshadowing-plant → foreshadowing-lifecycle（或按 C3/C20 契约定稿的现行链路），3 处正文现行链路引用同步（F887）
3. deps.json：移除 DEPRECATED 技能注册（F816/F817/F819；与 C22 F231 对账门禁协同——本 spec 删条目，C22 立"deps.json ↔ 磁盘 ↔ using-shenbi 三向闭包"）
4. F355：OPTIONAL_READS 清洗已移除技能死条目
5. DEPRECATED 技能正文：自称"默认激活/每章必查"等现行语气改为明确的退役说明 + 后继指针（防 LLM 读正文复活旧链路）
6. **F905 双重调度语义面（自 #23 补登，2026-08-30 驳斥对账）**：`src/shenbi/pipeline/chapter_loop.py:241-246` 固定 ChapterStep 14 派发 shenbi-review-sensitivity，同时 `src/shenbi/pipeline/audit_layer.py:46` GENRE_ACTIVATION_MATRIX 含 `"sensitivity"` 同名路由——每章可能双派发；且 matrix 头注释声称 "Core-circle dimensions are NOT here" 与 sensitivity/dialogue 在表内自相矛盾。裁决去重（单一触发源，按 C3/C20 契约定稿选定固定步骤或 genre 激活其一），dialogue（DEPRECATED，matrix `:49`）随 T1.1 拆除一并出表

### T2 · description 契约整改
6. 违规清单机械收集：脚本解析 74 个 SKILL.md description，标记含功能描述从句者（启发式：无 "Use when"/触发条件结构、含 "building/generates/schedules" 类动词短语）——覆盖 F835/F842/F877/F878 + F815 前半
7. 逐个改写为 when-to-use 形式；F815 其余项（跨目录相对引用、ACTIVE/PLANTED 矛盾、写未声明）按 C20 契约闭合处理并在此登记
8. audit-skill-descriptions.py（Z10 F1011：未接任何门）接线为 CI 检查或并入 lint_contracts——与 C25 T3 协同

### T3 · 防回潮 lint
9. 新增对账规则（挂 lint_contract_graph 或独立）：(a) DEPRECATED skill 名出现在 deps.json/using-shenbi/GENESIS_STEPS 即 FAIL；(b) 触发表路由的每个技能必须存在于 skills/ 磁盘且非 DEPRECATED；(c) description 契约（长度 + 触发式结构抽查）
10. 规则对当前树跑基线 = 0 违规（T1/T2 完成后），注入一个假路由行验证 FAIL（红灯）

### 批量清理（M 级成员）
本簇无 M 级成员（12 条全 P1/P2）。

## 验收标准（真实数据可复验）

1. `grep -rn "foreshadowing-plant\|foreshadowing-track\|foreshadowing-recall" tests/tiers/deps.json skills/using-shenbi/SKILL.md src/shenbi/` 仅剩 DEPRECATED 技能自身目录与显式退役说明处命中（GENESIS_STEPS 零命中）
2. 4 个 group-* + foreshadowing-lifecycle 在 using-shenbi 触发表各 ≥1 行（`grep -c` 对照）
3. description 契约脚本全仓跑批 0 违规；对 5 个已修技能（group-* 四件 + writing-skills）人工复核 when-to-use 形式
4. 防回潮 lint 红灯验证：临时在 deps.json 加回一个 DEPRECATED 条目 → lint FAIL（记录后还原）
5. `just check` 全绿；`shenbi-dispatch <lifecycle 技能> ...` dry-run 路由可达（后继技能可被触发表解析到）

## 风险与回滚

- **风险**：删路由后旧技能彻底失联——若生产 prompt 仍按旧名调用会 404；保留 DEPRECATED 正文内的"后继指针"作为迁移说明，观察一轮后再议物理删除（物理删除不在本 spec）
- **风险**：GENESIS_STEPS 换 lifecycle 影响管线黄金路径——改动排在 C3/C20 的契约定稿之后，跑一次 T2 短链验证
- **风险**：description 启发式有误判——先 WARN 清单人工过目再改写，避免把合法触发描述改坏
- **回滚**：触发表/deps.json/GENESIS_STEPS 三处改动各自独立 commit；lint 规则可降 WARN

## 簇成员清单（12 条，自查用）

F355, F815-F817, F819, F834-F835, F842, F873, F877-F878, F887, F905（自 #23 补登，双重调度语义面）（代表 F873）
