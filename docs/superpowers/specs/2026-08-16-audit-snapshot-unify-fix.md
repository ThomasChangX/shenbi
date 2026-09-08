> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-08 · 价值门 GO，scope 按 T0 路径 3 裁剪为 T4-only：词面定稿 + 契约对账 + 磁盘遗留处置；失效面 F306/F317/F348/F351/F792-src/F1109-代码面已随 #26 移除自然消解) | **Severity:** 🟠 P1 | **INDEX 编号**：#57
> **系列:** 2026-08-15 全项目深度审计 · 阶段 5 修复 spec（簇 C19）| **代表 finding:** F351 | **簇规模:** 12 条 | **严重度上限:** P1
> **范围:** src/shenbi/pipeline/{snapshot_diff,chapter_loop,crash_recovery,state_heal}.py、docs/framework/truth-files.yaml、tests 快照族、novel-output 生产快照 | **证据等级:** 实验佐证（Z3-review-r1 + Z7-review-r2 + Z11-a 生产实证）
> **与既有 spec 关系:** **依赖 #26**（2026-08-15-snapshot-subsystem-wiring-design.md，F303 三路裁决：接线/收敛后接线/移除）——本 spec 承接 #26 裁决结果，收口其未覆盖的布局单源化、TRUTH_FILES 完备性、命名统一与生产实证复验；执行顺序 #26 先决

# C19 · 快照子系统半迁移收口（snapshot-unify）

## 背景（根因 + 证据）

**根因**：快照子系统处于半迁移态——差分实现完整但生产零调用（唯一调用方是紧急清理），恢复链零调用，legacy 平铺与差分目录双布局并存，ring-buffer 文件名不匹配，truth 文件覆盖集残缺——同一功能四套事实（代码/测试/词表/磁盘）互不承认（T1503：差分版仅活在测试里）。

代表证据：
- **F351**（P1）：step-15 `pipeline-pre-revision-snapshot` 为空操作；差分快照系统正常流程零调用点（唯一生产调用方是紧急清理）
- **F1109**（P1，生产实证）：快照机制失能——实际落盘的是拼接审计而非正文副本，且未覆盖 ch1–4/ch56
- **F792**（P2）：布局分叉——生产 legacy 平铺 + 根 manifest（51 文件）vs 全部测试的差分目录布局；legacy 写入分支零覆盖，真实项目无法进 closure
- **F306**（P2）：ring-buffer 全文备份永不命中——零填充模式与非填充章节文件名不匹配，修订回滚无法恢复章节
- **F317**（P2）：state_heal._heal_last_snapshot 只识别 legacy 平面快照，不识别默认差分快照目录
- **F348**（P2）：snapshot `TRUTH_FILES` 集合缺 book_strata.md / volume_summaries.md / arcs/——触发器阶段写入的累积 truth 完全不入差分快照
- **F350**（P2）：紧急快照不入 snapshots/manifest.json（不受保留策略管理、永久累积）+ 快照文件命名三套并存
- **F890**（P2）：声明面 snapshots/chapter-NNN/*（sequel 读 / snapshot-manage 写）vs 磁盘面 D20 平文件不一致
- **F1155**（P2）：truth-files.yaml D20 注释与新 snapshot 契约矛盾，仅加 supersession 注记未彻底协调
- T708（部分恢复混合态——只写不还的后果面）、T710（T7 报告其余 P2 项 A）

## 目标

以 #26 三路裁决的输出为前提，把快照子系统收敛为**单一布局、单一命名、单一 truth 覆盖集、写读闭环**（或按裁决路径 3 诚实移除），并使生产实证（F1109）可复验地恢复。

## 任务分解

### T0 · 前置（#26 已决）
1. 读 #26 裁决结果（接线/收敛后接线/移除三选一）；本 spec T1–T4 按路径裁剪：
   - 路径 1/2（保留快照）：执行 T1–T4 全量
   - 路径 3（移除）：只执行 T4 的词表/文档收口 + 磁盘残留清理，F792/F306/F317/F348 随移除自然消解

### T1 · 布局与命名单源化（F792/F350/F890/F306）——（路径 3 下不执行，随 #26 移除自然消解）
2. 布局二选一定稿（差分目录为默认建议，与测试族一致）：legacy 写入分支删除或降级为一次性迁移器（读 legacy → 写差分，迁完即废）
3. 命名三套收敛为一套（零填充/非填充统一为一种 chapter 文件名模式）；ring-buffer 匹配逻辑用定稿命名重写并用真实文件名测试（F306 红灯：改名前永不到达的分支改名后必须到达）
4. 紧急快照并入 snapshots/manifest.json 与保留策略（F350）

### T2 · truth 覆盖集与恢复链（F348/F317/T708）——（路径 3 下不执行）
5. TRUTH_FILES 单源化：改为从 truth-files.yaml 派生（消灭代码内手抄集合——与 C22 词表对账协同），至少补 book_strata/volume_summaries/arcs
6. state_heal._heal_last_snapshot 识别定稿布局（F317）；restore 链接到 cli rollback（#26 路径 1/2 时），消除"只写不还"（T708）

### T3 · 生产实证复验（F1109/F351）——（路径 3 下不执行；F1109 仅存活磁盘遗留面，归 T4 item 11）
7. step-15 接线后对 novel-output（或回放项目）跑一轮 pre-revision 流程：快照含**正文副本**（非审计拼接）、覆盖全部活跃章（含 ch1–4 末章）、manifest 完整
8. 恢复演练：从最新快照 restore 单章 + truth 子集，断言内容一致

### T4 · 词面定稿与三面对账（F1155/F792/F890/F1109 遗留面/T710）
9. truth-files.yaml D20 概念定稿重写（删 supersession 注记式和稀泥），三项词面裁决逐一落地：
   - **目录布局 `snapshots/chapter-NNN/`（含 manifest.json）正名为 skill 域快照**——snapshot-manage 写 / sequel-writing 读，chapter_loop.py:134 已指定其为回滚机制，删除「fictional/deprecated」措辞
   - **平铺 `snapshots/chapter-N-emergency.md` 登记为 crash_recovery 紧急域**（crash_recovery._snapshot_chapter_files 是唯一 src/ 快照写方，label 恒 emergency；时间戳平铺命名属已移除写方，不再登记）
   - **`snapshots/manifest.json` 改 kind 为 drift/config 标记**（chapter_loop._update_last_drift_manifest 实写 last_drift_chapter，非快照索引）；同步清理 chapter_loop._load_manifest/_save_manifest 过时 docstring（「chapters」字典描述）与 `{"chapters": {}}` 返回骨架
10. 声明面（SKILL.md 契约）与词表/磁盘同口径；F1154 的 snapshot-manage fixture 换真实产物（C16 #54 已归档，其 archive 明记 F1154 blocked-on 本 spec 布局冻结——现解除，唯一归属本 spec；禁止在 `tests/fixtures/` 下现造 manifest——G0.9 域；tmp_path 内单测自建输入不在此列，如 test_g4_directory.py:30 / test_write_audit_glob.py:135 属正常测试建制）；快照测试族对两个存活面断言：skill 目录快照（tests/fixtures/snapshots）+ 紧急平铺快照（tests/fixtures/snapshot-dir），差分行为零断言
11. 磁盘遗留处置：novel-output/xinghuo-ranqiong/snapshots/ 下 51 个时间戳平铺快照（+1 manifest.json）出自已移除的 chapter_loop 写方——按文件裁决去留并记录；g0.py MIRROR_MAP 两条以 novel-output 时间戳快照为上游源（fixture=tests/fixtures/snapshot-dir/chapter-00{5,6}-*.md），上游类已整体移除，镜像校验失去对象 → **从 MIRROR_MAP 摘除该两条并注明理由**（选 b；fixture 自身保留为真实历史产物，G0.9 满足）

**T4 执行注记**：truth-files.yaml 消费方 = contracts/{loader,registry,schemas/registry}.py、dispatcher/executor.py、gates/g6.py、audit/snapshot.py、tools/lint_decisions_sources.py（间接：sync_contracts.py、tools/migrate_contract_to_frontmatter.py）——yaml 改动后必须 `just lint-contracts` 绿 + `just generate` 生成物 diff 为空；改 SKILL.md 契约同义务（禁手改生成物）；`tests/unit/contracts/test_registry_pipeline_producers.py:22,51` 硬编码 snapshots/manifest.json producer 与 D20_FICTIONAL_DIR_CONCEPT 断言需同步更新

**已知接受的残留**（下轮审计勿重复立案）：F350 半存活——紧急平铺快照仍无保留策略管理（无 prune），T4-only scope 出范围

### 批量清理（M 级成员）
本簇无 M 级成员（12 条全 P1/P2）。

## 验收标准（2026-09-08 按 T4-only scope 重写；原 1/3/4 条引用已移除的 TRUTH_FILES/差分快照/恢复链，随路径 3 作废）

1. truth-files.yaml D20 区 `grep -inE "supersed|fictional|deprecated"` 零注记式和稀泥命中；每布局恰一套词面（目录=skill 域、emergency 平铺=crash_recovery 域、manifest.json=drift 标记），yaml globs 与登记一一对应
2. 声明面↔词表↔磁盘三面同口径：snapshot-manage 写面、sequel-writing 读面与 yaml 登记一致；`just lint-contracts` 绿 + `just generate` diff 为空
3. F1154：snapshot-manage manifest.json fixture 为真实技能产物（或显式缺失报告），无现造 manifest
4. novel-output snapshots 遗留处置记录在 PR（逐文件去留 + g0.py MIRROR_MAP 两条摘除后——fixtures 自身保留于 tests/fixtures/snapshot-dir 为真实历史产物——`just check` 全绿）
5. 本 spec 与 #26 路径 3 的验收对照说明进 PR 描述

## 风险与回滚

- **风险**：布局迁移动生产快照数据——迁移器先 dry-run 报告 diff，人工确认后执行；原布局打包 tag 可回退
- **风险**：TRUTH_FILES 派生化改变快照体积（arcs/ 目录可能大）——保留策略（prune）同步调参
- **风险**：与 C3（truth 写路径）/C11（并发写）共享文件面——T2/T3 实施时走 write_safety 纪律，PR 顺序在 C3 之后
- **回滚**：每任务独立 PR；迁移器幂等可重跑；#26 路径 3 时本 spec 大部分自动失效（仅 T4 生效），无沉没成本

## 簇成员清单（12 条，自查用）

F306, F317, F348, F350-F351, F792, F890, F1109, F1155, T708, T710, T1503（代表 F351；T1503=F351 历史面）
