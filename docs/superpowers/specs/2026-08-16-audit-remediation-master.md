> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-03 — §8 记账执行清单落盘：批次 A 13 簇全 Done 后的矩阵标注/ledger 回写/#25 解散/INDEX 刷新) | **Severity:** 🔴 P0（总纲）| **方法:** 聚类→spec 映射与依赖排序
> **系列:** 2026-08-15 全项目审计 · 阶段 5 总纲（master）| **依赖:** phase4-clustering.md（37 簇唯一权威输入）| **范围:** 全部 37 簇修复 spec 的优先级矩阵、依赖顺序、量级与既有 spec 关系 | **核心洞察:** 774 条 findings 的修复不是 774 个动作，是 37 个根因收口；跨簇依赖（写路径先于读方对账、审计谓词先于失败分类、计量先于成本报告）决定合入顺序，否则修复互踩

# 2026-08-15 审计修复总纲（audit-remediation-master）

## 元信息
- 输入：`docs/superpowers/audit-runs/2026-08-15/phase4-clustering.md`（37 簇簇总表，全覆盖 774 条、0 硬残条、737 条 merged-into 关系）
- 本总纲全部计数由簇总表机械加总推导，不手抄 findings-ledger 单条数字
- spec 产出分三批并行：批次 A（C1-C13）、批次 B（C14-C26）、批次 C（C27-C37 + 本总纲）；三批 37 个簇 spec 已全部落盘（文件名见 §2.4 矩阵），INDEX 登记以该文件为准（批次 A=#27-#39、批次 C=#40-#51、批次 B 登记由其自身完成）

## 1. 总览数字（机械推导）

| 维度 | 值 |
|---|---|
| 簇数 | 37 |
| 覆盖 findings | 774（0 硬残条；737 条 merged-into 供回写） |
| 簇最高严重度分布 | **P0 ×7 簇 =191 条**（C1/C16/C11/C3/C10/C4/C32）；**P1 ×26 簇 =483 条**；**P2 ×4 簇 =100 条**（C24/C8/C15/C29） |
| 纯 M 簇 | **0 个**（最低簇严重度为 P2）——无需"文档卫生批量合并"spec；M 级条目已并入所在簇由代表簇 spec 覆盖 |
| 证据等级 | 实验佐证 35 簇（含 C23/C36 机械对账实跑）；推理假设 1 簇（C29，T1615 三规模实测旁证——修复前须最小实证） |
| 簇规模极值 | 最大 C1=67；≥20 条 17 簇；≤6 条 3 簇（C5/C7/C36，窄根因独立 spec） |

## 2. 优先级矩阵（37 簇全量）

批次列：A=C1-C13、B=C14-C26、C=C27-C37。量级：S≤1 天 / M=2-5 天 / L≥1 周（按成员数×修复面广度估）。

### 2.1 P0 簇（7 簇，先行主线）

| 簇 | 根因短语 | 条数 | 批次 | 量级 | 关键前置 |
|---|---|---|---|---|---|
| C32 | 写审计假阳性机器+diff 谓词漏洞 | 11 | C | M | 无（先行——C33/C1 的输入） |
| C3 | truth 追加写路径零接线 | 21 | A | L | 无 |
| C34 | 路径/布局三套分裂 | 14 | C | M | 无（C1 验收的地基） |
| C1 | 读方↔写方键空间从未对账 | 67 | A | L | C3 定稿写方 + C34 路径协议（验收期） |
| C4 | decisions-sidecar 四层断裂 | 17 | A | M | C3 staging 提交路由（sidecar 同生共死面） |
| C10 | token 计量 dead-wire | 20 | A | M | 无（先行——成本类验收的输入） |
| C16 | fixture 真实性失真/G0.9 零执法 | 31 | B | L | 无（C14 重写断言的输入） |
| C11 | 并发/锁/durability 缺失 | 24 | A | L | 与 C3 写路径同 PR 面联合验收 |

### 2.2 P1 簇（26 簇，按修复面分组）

| 修复面 | 簇（条数/量级/关键前置） |
|---|---|
| 执行面·章循环与状态 | C30（20/L；前置 C3）、C19（12/M；独立裁决 spec #26 已存在）、C37（43/L；前置各接线裁决+R0 分桶表）、C5（6/S-M；G3 独立性接线）、C7（5/S-M；helper 接线，supersede #14） |
| 契约/声明面 | C2（13/M；Layer B 字段过滤链）、C20（21/M；frontmatter↔正文 lint）、C21（12/S-M；DEPRECATED 路由下线）、C22（29/M；五类登记表对账门禁）、C8（24→P2 批；enums 收编） |
| 门禁/checker 面 | C13（35/M-L；吞错/部分校验）、C12（28/M；裸崩面）、C6（21/M；drift/style 链）、C9（18/M；阈值多源）、C34 已列 P0 行 |
| 计量/观测/性能面 | C28（13/M；前置 C10 落账）、C33（11/M；前置 C32 rc 语义 + C10）、C29（8/S-M；P2 见批量行但无前置） |
| 测试质量面 | C14（26/M-L；前置 C16 真实 fixture）、C15（12→P2 批）、C17（18/M；nightly/benchmark 基线） |
| 产物/流程/安全卫生面 | C18（17/M；生产树清洗+派发沙箱）、C31（10/M；注入/越权，supersede #22）、C26（11/S；shell/just 注入面）、C27（9/S-M；供应链口径，supersede #15）、C35（18/M；审计自身 lint，全程可并行）、C36（3/S；print 纯度，独立） |

### 2.3 P2 批量簇（4 簇）

| 簇 | 根因短语 | 条数 | 批次 | 处置 |
|---|---|---|---|---|
| C24 | 文档语义矛盾 | 56 | B | 单一"语义对账"spec 批量修订（阈值/词表/流程矛盾节） |
| C23 | 文档机械漂移 | 46 | B | 并入同一"文档对账工具+CI"spec（doc-links 启用 + 计数/断链/行号批量），phase4 §7 建议与 C24 合并处理 |
| C8 | 状态/词表多源 | 24 | B | enums.py 收编 + lint 补洞（是 C1/C29 的词表输入，实际执行宜提前） |
| C15 | 关键零覆盖 | 12 | B | 补测 + 覆盖率 per-module 底线（依赖 C14/C16 先治断言与 fixture） |

## 3. 跨簇依赖顺序（关键链）

1. **C32 → C33 → 成本类**：写审计 rc 语义先定（假阳性清零），失败分类才可信；重试成本量化靠 C10 落账。
2. **C3 → C1（验收）**：truth 写方键空间定稿后，C1 的读方对账 lint 验收才有效（对账对象必须稳定）；C34 路径协议同为 C1 验收前置（gate 假 FAIL 先消路径错位，否则对账 lint 报警混入噪音）。
3. **C10 → C28/C33**：token 计量接线先于一切"省了多少 token"的收益验证（审计波去冗余、重试预算成本）。
4. **C3（staging 提交路由）→ C30 R1 → C4**：staging 生命周期语义定稿 → sidecar 同生共死 → decisions 链验收。
5. **C19（spec #26 三路裁决）→ C37 R2 解冻 / C28 R3**：快照面裁决前，C37 不得删差分快照三件套，C28 不得增量化未定归属的实现。
6. **C16 → C14 → C15**：fixture 真实化先于断言重写（重写需要真实行为可对照），断言真实化先于补覆盖（否则补的是自证测试）。
7. **C8 词表单源 → C1/C29**：词表触发器读键与 gate 输出新字段（input_sampled 等）都消费单源枚举。
8. **C35/C36/C27 全程并行**：纯流程/工具面，无生产代码依赖，可作任何等待期的填充工作。
9. **C37 收尾**：R0 分桶表把"接线桶"移交各簇后，删除桶在全部认领簇合入后执行，避免删掉要接线的面。

## 4. 预计工作量级汇总

| 量级 | 簇 | 估时 |
|---|---|---|
| L（≥1 周/簇） | C1、C3、C11、C16、C30、C37、C13 | 7 簇 ≈ 7-10 周 |
| M（2-5 天/簇） | C4、C10、C32、C34、C2、C6、C9、C14、C17、C18、C19、C20、C22、C23、C24、C25、C28、C33、C35、C8、C12、C15 | 22 簇 ≈ 9-15 周总量（三批并行可压缩） |
| S-M/S（≤1-2 天/簇） | C5、C7、C21、C26、C27、C29、C31、C36 | 8 簇 ≈ 1-2 周总量 |

并行度建议：3 条泳道（执行面 / 契约面 / 卫生面）+ 1 条 P0 主线（C32→C3→C34→C1），全量收敛预计 6-9 周墙钟（不含跨簇联合验收的重测）。

## 5. 与既有活跃 spec 的关系（INDEX 现有 23 个）

| 既有 spec（编号） | 处置 | 说明 |
|---|---|---|
| #17 full-project-audit-design（08-14 总纲） | **supersede（本总纲）** | 08-14 轮 10 根因簇图已被 37 簇聚类取代；保留为历史 run 记录，建议归档 |
| #7 data-loss-cluster | supersede → C3/C11/C30/C19 批次 spec | 数据丢失四症状已按根因归簇 |
| #12 cost-ledger | supersede → C10 spec | TokenLedger 接线面全量入 C10 |
| #21 truth-write-path | supersede → C3 spec | T7 写原语矩阵全量入 C3 |
| #10 audit-chain | supersede → C32 spec | 写审计/快照 diff 面 |
| #22 security-injection | supersede → C31 spec | T12-01/04/05 未修复核重立为 T1206/T1207/T1204 |
| #15 deps-supply-chain | supersede → C27 spec | 供应链口径与 D1-01 |
| #18 fixture-authenticity | supersede → C16 spec | fixture 治理 + 测试质量洞拆 C14/C15/C17 |
| #19 decisions-chain | supersede → C4 spec | T1-01/02/03 全链 |
| #8 gate-effectiveness | supersede → C1/C34/C13 分面 | F408 族按根因拆簇 |
| #9 contract-single-source | supersede → C2/C22 | 契约模型与登记表对账 |
| #11 drift-chain | supersede → C6 | drift 链实现层缺陷 |
| #13 config-governance | supersede → C9（+C4 severity 面） | 绕过向量与阈值多源 |
| #14 stats-determinism | supersede → C7（+C6） | 确定性 helper 接线 |
| #20 z11-output-contracts | supersede → C18/C30 | 章节头/META 归 C18，state 产物归 C30 |
| #23 z8-contract-drift | supersede → C20/C21/C22 | 声明/路由/登记表分簇 |
| #24 tooling-gate-chain | supersede → C33/C7/C2/C34 | lint 接线/重试/字段过滤分簇 |
| #16 minor-findings-batch（M 批量） | **解散关闭** | 无纯 M 簇——M 级条目随所在簇 spec 处置 |
| #25 p2-batch | **解散关闭** | 287 条 P2 已按根因归入 37 簇（大头 C24/C23/C37） |
| #26 snapshot-subsystem-wiring（08-15） | **保留 = C19 执行 spec** | 唯一直接复用；C37/C28 依赖其裁决 |
| #5（prompt 设计）、#3/#4（08-01 token 审计） | 归档候选 | 设计/审计产物已被本批吸收（#4 重试面→C33，#3 确定性→C7） |

处置协议：被 supersede 的 spec 在对应簇 spec 首个 PR 合入时移 archive/ 并在 INDEX 删行；本总纲长期保留为 37 簇索引直到全部簇关闭。

## 6. 执行与回写协议

1. 每簇 spec 完成时：findings-ledger 按 phase4 §3 merged 清单批量回写（737 条），簇代表条目关闭即成员关闭
2. 联合验收对（不可拆分合入）：C32+C33、C3+C11+C30 R1、C16+C14、C1 验收期挂 C3/C34
3. 新发现按 C35 R2 的承接清单机制处理（不再断链）；严重度校准按 phase4 §4 的 11 项提案随 C35 R4 落账
4. 总纲维护：簇状态变化（spec Done/Rejected）时更新 §2 矩阵行内标注，不改历史计数

## 风险
- 三批并行 spec 对同一修复面（security.yml、ci.yml、staging）各有主张——以先合入者为准，后到者只做对账不重排（各 spec 已注明合写占位）
- 量级估计基于成员数×修复面广度，未含联合验收重测——P0 主线（C32→C3→C34→C1）建议预留 30% 缓冲
- C29 为推理假设簇：其 spec 已内置"修复前最小实证"闸门，实证推翻则簇降级并回写 phase4 注记

## 7. 附录·37 簇全矩阵（机械推导自 phase4 簇总表，按簇号升序）

spec 文件名为 2026-08-16 落盘实名；量级 S≤1 天 / M=2-5 天 / L≥1 周。前置列仅列硬依赖（验收期依赖见 §3）。

| 簇 | 根因短语 | 条数 | 最高严重度 | spec 文件（2026-08-16-） | 批次 | 量级 | 硬前置 |
|---|---|---|---|---|---|---|---|
| C1 | 读方↔写方键空间从未对账 | 67 | P0 | audit-reader-writer-key-reconciliation-fix.md | A | L | C3+C34（验收期） |
| C2 | Layer B 字段级 reads 断裂 | 13 | P1 | audit-layerb-field-reads-fix.md | A | M | — |
| C3 | truth 追加写路径零接线 | 21 | P0 | audit-truth-upsert-wiring-fix.md | A | L | — |
| C4 | decisions-sidecar 四层断裂 | 17 | P0 | audit-decisions-chain-fix.md | A | M | C3（staging 面） |
| C5 | G3 独立性/反坍缩空转 | 6 | P1 | audit-g3-independence-fix.md | A | S-M | — |
| C6 | 语言学漂移/CJK 盲区 | 21 | P1 | audit-linguistic-drift-cjk-fix.md | A | M | — |
| C7 | 确定性 helper 零接线 | 5 | P1 | audit-deterministic-helper-wiring-fix.md | A | S-M | — |
| C8 | 状态/词表多源 | 24 | P2 | audit-status-vocab-single-source-fix.md | A | M | — |
| C9 | 阈值/配置契约多源 | 18 | P1 | audit-threshold-config-coherence-fix.md | A | M | — |
| C10 | token 计量 dead-wire | 20 | P0 | audit-token-metering-fix.md | A | M | — |
| C11 | 并发/锁/durability | 24 | P0 | audit-concurrency-durability-fix.md | A | L | 与 C3 联合验收 |
| C12 | 裸崩边界 | 28 | P1 | audit-crash-boundary-guards-fix.md | A | M | — |
| C13 | 静默吞错/部分校验 | 35 | P1 | audit-silent-swallow-partial-validation-fix.md | A | M-L | — |
| C14 | 弱断言/自证测试 | 26 | P1 | audit-weak-assertions-fix.md | B | M-L | C16 |
| C15 | 关键零覆盖 | 12 | P2 | audit-zero-coverage-fix.md | B | M | C14/C16 |
| C16 | fixture 真实性失真 | 31 | P0 | audit-fixture-authenticity-fix.md | B | L | — |
| C17 | 测试基础设施失效 | 18 | P1 | audit-test-infra-fix.md | B | M | — |
| C18 | 生产产物污染 | 17 | P1 | audit-artifact-contamination-fix.md | B | M | — |
| C19 | 快照子系统半迁移 | 12 | P1 | audit-snapshot-unify-fix.md（+INDEX #26 裁决 spec） | B | M | — |
| C20 | 技能契约声明面断裂 | 21 | P1 | audit-skill-contract-declaration-fix.md | B | M | — |
| C21 | 注册/触发路由漂移 | 12 | P1 | audit-skill-routing-deprecated-fix.md | B | S-M | — |
| C22 | 平行登记表无对账 | 29 | P1 | audit-registry-reconcile-fix.md | B | M | — |
| C23 | 文档机械漂移 | 46 | P1 | audit-docs-mechanical-drift-fix.md | B | M | — |
| C24 | 文档语义矛盾 | 56 | P2 | audit-docs-semantic-conflicts-fix.md | B | M | — |
| C25 | CI/just 双向手工同步 | 24 | P1 | audit-ci-just-sync-fix.md | B | M | — |
| C26 | shell/just 注入误用 | 11 | P1 | （批次 B spec；见 INDEX 登记） | B | S | — |
| C27 | 供应链审计盲区 | 9 | P1 | c27-supply-chain-audit-design.md | C | S-M | — |
| C28 | 性能反模式 | 13 | P1 | c28-perf-antipatterns-design.md | C | M | C10 |
| C29 | 截断/采样静默 | 8 | P2 | c29-truncation-observability-design.md | C | S-M | 最小实证闸门 |
| C30 | 章循环/staging 生命周期 | 20 | P1 | c30-chapter-loop-staging-design.md | C | L | C3 |
| C31 | 注入/越权安全面 | 10 | P1 | c31-injection-authorization-design.md | C | M | — |
| C32 | 写审计机制缺陷 | 11 | P0 | c32-write-audit-mechanism-design.md | C | M | —（C33 的前置） |
| C33 | 重试/失败分类分裂 | 11 | P1 | c33-retry-failure-taxonomy-design.md | C | M | C32+C10 |
| C34 | 路径/布局契约分裂 | 14 | P1 | c34-path-layout-contract-design.md | C | M | —（C1 验收地基） |
| C35 | 审计过程自身缺陷 | 18 | P1 | c35-audit-process-hygiene-design.md | C | M | —（全程并行） |
| C36 | print 违禁散点 | 3 | P1 | c36-print-purity-design.md | C | S | — |
| C37 | 死代码零执法 | 43 | P1 | c37-dead-code-enforcement-design.md | C | L | C3/C7/C19/C28 裁决 |

列校验：条数列合计 = 774；P0 行 7（C1/C3/C4/C10/C11/C16/C32）合计 191；P2 行 4（C8/C15/C24/C29）合计 100；P1 行 26 合计 483——与 §1 总览一致。C26 文件名为 `2026-08-16-audit-shell-injection-fix.md`（批次 B 登记为 INDEX #64，占位消除）。

## 8. 记账执行清单（2026-09-03 修订新增 · master 维护 pass）

截至本修订，13 簇已完成（批次 A 全部：C1=PR #107、C2=PR #114、C3=PR #117、C4=PR #120、C5=PR #122、C6=PR #124、C7=PR #127、C8=PR #129、C9=PR #132、C10=PR #137、C11=PR #140、C12=PR #142、C13=PR #145）。本节为一次性记账 pass 的权威执行清单：

- **T1 矩阵状态标注**：§2.1/§7 矩阵为 13 个 Done 簇行补 `✅ Done (PR #N)` 标注（§6.4 协议补执行，不改历史计数）；§7 文件名列同步为 archive/ 实名（注意两种归档形态并存：C1-C5/C7 保留原文件名，C6/C8-C13 为 `specNN-…-Done-PR*.md` 改名形态）
- **T2 findings-ledger 回写**：按 phase4 §2 簇总表压缩成员清单，把 13 个 Done 簇的成员条目状态 `open`/`verified` → `closed (C-cluster spec #NN, PR #N)`；剔除/残余判定以各归档簇 spec 自身的修订记录为权威（§8 不复述枚举——如 C6 六条已修剔除、C9 F202/F436/F603、C13 剔除面以 spec39 修订记录为准），「已修 elsewhere」条目关闭时注明实际修复 PR；各簇 spec 记录的残余/遗留观察缺口条目保持 open 并加注。19 行畸形重复行（F901-F919 dupes）不参与
- **T3 #25 解散归档**：§5 判「解散关闭」执行——`2026-08-14-p2-batch-design.md` 移 archive/ 加解散注记，INDEX 删行、计数 28→27。解散注记须载明：(a) #25 属 2026-08-14 审计轮 ledger 家族，master §5 的归簇依据是 2026-08-15 再审计 37 簇——执行前先对 #25 的 Z1-整体层/家族主条目做一次 grep 级残余核对（如 F0-03 门禁计数漂移、F0-06 python 版本三处不一致无 08-15 对应行者，逐条给出承接归宿或记为总纲 §8 deviation）；(b) 此前九次 DEFER（"依赖全部子 spec"）由本解散显式 supersede——剩余承接以 §7 矩阵 24 个活跃簇为准
- **T4 INDEX 刷新**：「最后更新」日期更新；删除 #25 行后计数头同步
- **T5 完成后核对**：`just check` 全绿（docs workflow mkdocs --strict 对 specs/ 面生效）；归档移动的 #25 文件内相对链接核查（本仓 spec 文件为纯文件名文本引用，无相对链接面——执行时复查）

执行边界：本 pass 不动任何生产代码、不改 24 个仍活跃簇 spec 的内容与计数；ledger 只改状态列与注记，不改任何证据列。spec 号映射 = 批次 A 序：#27=C1 … #39=C13。
