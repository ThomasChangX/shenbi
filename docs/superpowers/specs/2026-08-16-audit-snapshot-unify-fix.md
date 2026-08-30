> **Date:** 2026-08-16 | **Status:** Design (大部分失效注记：#26 已于 2026-08-30 裁决路径 3——差分快照子系统整体移除，本 spec 按 T0 仅存活 T4 truth-files.yaml/词面协调面，待自身价值门复核) | **Severity:** 🟠 P1
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

### T1 · 布局与命名单源化（F792/F350/F890/F306）
2. 布局二选一定稿（差分目录为默认建议，与测试族一致）：legacy 写入分支删除或降级为一次性迁移器（读 legacy → 写差分，迁完即废）
3. 命名三套收敛为一套（零填充/非填充统一为一种 chapter 文件名模式）；ring-buffer 匹配逻辑用定稿命名重写并用真实文件名测试（F306 红灯：改名前永不到达的分支改名后必须到达）
4. 紧急快照并入 snapshots/manifest.json 与保留策略（F350）

### T2 · truth 覆盖集与恢复链（F348/F317/T708）
5. TRUTH_FILES 单源化：改为从 truth-files.yaml 派生（消灭代码内手抄集合——与 C22 词表对账协同），至少补 book_strata/volume_summaries/arcs
6. state_heal._heal_last_snapshot 识别定稿布局（F317）；restore 链接到 cli rollback（#26 路径 1/2 时），消除"只写不还"（T708）

### T3 · 生产实证复验（F1109/F351）
7. step-15 接线后对 novel-output（或回放项目）跑一轮 pre-revision 流程：快照含**正文副本**（非审计拼接）、覆盖全部活跃章（含 ch1–4 末章）、manifest 完整
8. 恢复演练：从最新快照 restore 单章 + truth 子集，断言内容一致

### T4 · 词表与测试对账（F1155/F792/F890/T710）
9. truth-files.yaml D20 概念按定稿布局重写（删 supersession 注记式和稀泥）；声明面（SKILL.md 契约）与磁盘面同口径
10. 快照测试族从"差分布局专用"改为对生产布局断言；F1154 的 snapshot-manage fixture 换真实产物（与 C16 T4 协同）

### 批量清理（M 级成员）
本簇无 M 级成员（12 条全 P1/P2）。

## 验收标准（真实数据可复验）

1. `git grep -n "TRUTH_FILES" src/` 仅一处定义且来源为 truth-files.yaml 派生（或注释指向派生函数）；对 yaml 注入一个假 concept 后快照内容随之变化（红灯验证）
2. 布局定稿后：生产树 + 测试 + 词表三面 `find <project>/snapshots -maxdepth 1 -type d | wc -l` 与声明一致；命名模式 grep 仅一种（`chapter-\d+\.md` 或定稿形式）
3. F1109 复验脚本输出：快照章覆盖 = 活跃章集合（对照 novel-output 章清单），每章快照含正文副本（字节级或哈希对照）
4. 恢复演练记录：restore 后目标章与源章 hash 一致；restore 不越出 project_dir（与 C31 路径安全协同）
5. #26 自身验收（按其路径）同步达成；本 spec 与 #26 的验收对照表进 PR 描述

## 风险与回滚

- **风险**：布局迁移动生产快照数据——迁移器先 dry-run 报告 diff，人工确认后执行；原布局打包 tag 可回退
- **风险**：TRUTH_FILES 派生化改变快照体积（arcs/ 目录可能大）——保留策略（prune）同步调参
- **风险**：与 C3（truth 写路径）/C11（并发写）共享文件面——T2/T3 实施时走 write_safety 纪律，PR 顺序在 C3 之后
- **回滚**：每任务独立 PR；迁移器幂等可重跑；#26 路径 3 时本 spec 大部分自动失效（仅 T4 生效），无沉没成本

## 簇成员清单（12 条，自查用）

F306, F317, F348, F350-F351, F792, F890, F1109, F1155, T708, T710, T1503（代表 F351；T1503=F351 历史面）
