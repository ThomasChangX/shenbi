> **Date:** 2026-08-16 | **Status:** Revised 2026-08-31（阶段 3 审查裁决回写）| **Severity:** 🟥 Critical | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5（簇 C4，17 条）| **代表 finding:** F237 | **严重度上限:** P0（F1102/T101）| **涉及文件面:** src/shenbi/contracts/schemas/decisions.py、dispatcher/derive_file_type、gates/g2.py + g4/、5 个 decisions 生产技能 SKILL.md、docs/framework/decisions-schema.md、AGENTS.md P2.5 条款

# decisions-sidecar 契约链修复（audit-decisions-chain）

## 背景

decisions.json sidecar（Layer A）契约在 schema↔写方↔路由↔G2/G4 四层各自为政，生产 145 个 decisions.json 仅 5 个通过校验（F237 原口径 44 非法 JSON + 42 schema 违反；2026-08-31 重测基线：83 非法 JSON + 57 schema 违反，5/145 通过——以重测为准）。四层断裂：

1. **schema 层**：F237——DecisionsDoc 由测试内联字面量反推，与真实生产者全面断裂；F212——rationale 矩阵三处漂移（code 对 medium 强制 rationale，schema 文档与 AGENTS.md 均无 medium 行）；F908——decisions 枚举与 P2.5 表欠指定。
2. **写方层**：F439——5 个 decisions 生产技能的 SKILL.md 均不记载必填字段（$schema/skill/chapter/produced_at）；F791——生产三态（干净 45/尾随 35/散文 9）vs 测试单态。
3. **路由层（P0）**：T101——derive_file_type 对 decisions-双产物技能返回 "decisions"，G2 据此无条件 continue，chapter-drafting/short-drafting 的 .md 主产物静默绕过 G2 全部章节质量检查（实测违规章节 PASS）；F438——T2 路径同族（.md 零结构校验）；F205——单一类型 join + .md 跳过双面。
4. **门禁层**：F434/T103——pipeline 主路径从不把 decisions.json 传给 G4（output_path 单文件 + glob(*.md)），chapter-drafting 的 G4.dec 恒 SKIP；F795——44/89 损坏 sidecar 与 22 个 PASS marker 并存的机制解释；T104——G2/G4 判定分歧 15 例（raw_decode 截断恢复使 G2 比 G4 多放行 15/145）。
5. **声明四源断链**：T106——schema 文档 7 技能 / truth-files.yaml 7 文件 / SKILL writes 5 声明 / 实产 4 类 145 个互不一致，下游 reads 声明率 2/7；T107——AGENTS.md decisions 条款漂移。

注：本簇与已归档的 #19（2026-08-14 decisions 链补齐 spec）同域，本 spec 为 2026-08-15 审计轮的簇级合并版，吸收其未完成面。

## 修复目标

1. 生产 decisions.json 100% schema 有效（当前 5/145）。
2. 混合产物技能的 .md 主产物不再因 decisions 路由绕过 G2/G4。
3. 管线把 decisions sidecar 送 G4（G4.dec 不再恒 SKIP）。
4. 声明四源（schema 文档/truth-files.yaml/SKILL writes/实产）一致，P2.5 rationale 矩阵四源一致。

## 任务分解

- **T1 · 路由修复（T101/F438/F205，P0）**：同一技能的 .md 走章节检查、.json 走 decisions 检查。修订（2026-08-31 阶段 3 审查 I1）：**文件名分区**——在 gate_G2 内按后缀分流（eff_type 机制），CLI `shenbi-validate G2 <files> <type>` 协议零变更，镜像 G4 复合分区先例；原「派发产物清单携带 (path, file_type) 元组」形状作废（更重且破坏 CLI 兼容）。g2.py 现为条件 continue（~:89），语义等价旧指控。
- **T2 · G4 文件集接入（F434/T103/F795）**：`_resolve_g4_files`/state-settling glob 纳入契约全部输出（含 .json sidecar），4 类真实 producer 的 decisions 进 G4.dec 检查列表。
- **T3 · schema 对齐真实生产者（F237/F791）**：以生产 145 样本三态（干净/尾随/散文）为基准重导 DecisionsDoc（必要时放宽为 permissive read + strict write）；写路径 `DecisionsDoc.model_validate` 前置，失败 FAIL 不落盘（含 IDE/codex 直写路径）。
- **T4 · producer 声明补全（F439 + T106）**：5 个生产技能 SKILL.md 输出模板内嵌 decisions 示例段与必填字段清单；prompt 注入 schema/P2.5 摘要；四源对账表（schema 文档↔truth-files.yaml↔SKILL writes↔实产）落地为 lint（与 C22 登记表对账联动）。
- **T5 · P2.5 矩阵四源一致（F212/F431/T108/F908）**：severity × rationale 矩阵以 code 现行为准（medium 强制）回写 decisions-schema.md P2.5 表与 AGENTS.md；错误消息补 medium。
- **T6 · G2/G4 容错对撞（T104）**：raw_decode 截断恢复策略二选一收敛，加同文件 G2/G4 判定对撞测试（15 例回归集）。
- **T7 · 文档同步（T107）**：AGENTS.md decisions-sidecar 条款对齐最终裁决。

## 批量清理（纯 M 成员）

- F431/T108（P2.5 错误消息漏 medium）随 T5 一行修复，不单列。

## 验收标准

1. `python3 -c "..."` 对生产树全量 decisions.json 重跑 schema 校验（复现 F237 命令口径）：通过率从 5/145 升至 100%（或剩余文件全部带明确校验失败标记且不进 PASS marker）。
2. 构造含违规章节的 chapter-drafting 双产物 round，`shenbi-validate G2` 对 .md FAIL（T101 断言，当前实测 PASS）；G4.dec 检查列表含 decisions.json（F434 断言：marker 不再 `{"id":"G4.dec","s":"SKIP","r":"no files"}`）。
3. G2/G4 对撞测试 15 例全绿（T104 断言）。
4. `just check` 全绿。

## 风险与回滚

- 风险（修订 2026-08-31）：WARN-then-FAIL 滚动删除（阶段 3 I2）——pipeline 路径本就跳过 G2（executor.py，交付由 G4/G6 承担），爆炸面限于非管道 dispatch（src/shenbi/dispatcher/executor.py）；Task 内以真实语料测试（15 例对撞套件）代替全量盘点。T3 放宽读取 schema 时防止把"尾随拼接"合法化——raw_decode 恢复仅用于告警归档，不静默放行（与 C13 F507 联动）。
- 回滚：T1/T2 独立 PR 可 revert；schema 变更保持 `shenbi-decisions-v1` 版本号不动（字段级兼容），避免下游 reads 断裂。

## 簇成员清单（与 phase4-clustering.md §2 机械对照）

C4（17 条，代表 F237）：

F205 F212 F237 F431 F434 F438 F439 F791 F795 F908 F1102 T101 T103 T104
T106 T107 T108
