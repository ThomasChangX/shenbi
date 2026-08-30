> **Date:** 2026-08-14 | **Status:** Done (PR #88) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 4/7） | **依赖:** data-loss-cluster | **范围:** truth 文件写路径（write_truth_file/upsert/staging/契约语义）| **核心洞察:** 双写者键格式漂移（T7-01）、结构化记录丢失（T7-02）、staging/committed 分叉（T7-03）、契约自相矛盾（T7-06）

# Truth 写路径（补齐 D）

> **2026-08-30 阶段 1 重裁（SDD #21）**：key_field 接线、hooks 数据恢复、truth_index dual-source、clear_staging 调用点、G4 读 committed、R4 整体已被 PR #43/#44/#70/#42 修复。本期 scope 收窄为下述 R1/R2/R3 的**残留**部分。

## R1 · resonance_trend 双写者键格式统一（T7-01, P1）
- 残留证据：框架行构造器 `_build_resonance_trend_row`（chapter_loop.py:1403）7 列 `| Ch{N} |` vs skill 契约 9 列 key `{N}`（review-resonance SKILL.md:160-165）；upsert 整格键比较 `Ch55 != 55` → 同章两写者都跑产双行
- 修复（audit r1 C1/I1a/I1b 并入）：**框架写者改「key 不存在才写」**——写前查该章 key 是否已存在（truth_io 加 `has_markdown_row` 辅助或等价检查），skill 已写的富行（四维/角色/confidence）绝不被框架占位行覆盖；占位行本身对齐 9 列、confidence 列用空格与 skill 一致；oneoff 迁移旧 `Ch{N}` 7 列历史行为 `{N}` 9 列（或验收明确仅对新章生效，实现时定）
- **验收：两写者同章先后写入后同章仅一行且保留 skill 富行；历史行归一化后同章无 `Ch{N}` 残留**

## R2 · pending_hooks 读取器统一（T7-02, P1）
- 残留证据：context_curation.py:361-385 `_read_pending_hooks` 只读 frontmatter `hooks:` 键（真实文件无 → 持续静默 `[]`，喂 P0-9 危机计算）；G6.7 解析器 g6.py:116-120 按 `## hooks`+`- id:` 假设解析 → 假 hook/`??` 未解（≡ p2-batch F450，本 spec 认领，p2-batch 改交叉引用）
- 修复（audit r1 C2/I2a + r2 I-2/I-3 并入）：**新 shared 解析模块 `src/shenbi/pipeline/truth_readers.py` 提供 `read_pending_hooks(project_dir) -> list[dict]`**——表感知解析器，字段映射与裁决规则：
  - state 以**最新章「生命周期状态更新」表的后状态列为准**；呈现表「当前生命周期」列仅交叉校验（其值可为 `RELEVANT→TRIGGERED(待track确认)` 转移+批注串，归一化取箭头后段、剥批注）
  - `frontmatter last_chapter` → last_reinforced **上界**（非下界，防掩蔽 OVERDUE）；真实 last_reinforced 优先从 REINFORCE 操作行/「培育间隔检查」表推导
  - plant_chapter/max_distance 源自「距离上限逼近」表——注意 max_distance 值嵌在**列名**（`max_distance(14)`），需解析列名提取，per-hook 上限不同时不得静默失败
  - context_curation `_read_pending_hooks`、g6.7、truth_index `_index_hooks`（body 源）三方全部改调它——**单一解析源，禁第二套格式**；解析失败显式标记而非混入 unresolved/默认值造假（禁 silence=999 全 URGENT 式虚假通过；「距离上限逼近」表按语义可能只列逼近上限的 hook，缺表行时 plant_chapter 同样显式标记而非默认值）
- **验收：真实 pending_hooks.md 经 read_pending_hooks 解析出 ≥7 条含非空 state 的记录；context_curation/G6.7/truth_index 三消费方均经同一解析源非空消费**

## R3 · staging 双写者 last-writer-wins 根因修复（T7-03, P1）
- 残留证据：dispatch_helper.py:1184-1201 `_route_append_dedup_write` staging 分支每次以 LIVE truth 为合并基整写 staging → 并行两写者（chapter_loop.py:2477-2491 ThreadPoolExecutor）last-writer-wins，先写者增量丢失；运行时 staging/truth/pending_hooks.md 与 committed 版实质冲突；staging/plans 残留 111 文件
- 修复（audit r1 C3/I3a/I3b 并入）：三件——
  1. staging 合并基改**链式**：staging 文件存在则以 staging 为基（否则 live），先写者增量不再被后写者抹掉
  2. staging 分支的 read-merge-write 序列包进 **per-path lock**（复用 truth_io `_path_lock` 机制，当前分支绕过 `write_truth_file` 直接 safe_write 无锁）；验收测试须含**并发两写者**用例
  3. commit 端窗口（r2 I-1 并入）：`commit_staging` 当前只收裸路径、无 update_mode/key_field——修复需先落 **staging 写入 sidecar 元数据**（staging 时持久化各 target 的 update_mode/key_field），commit 时读 sidecar 判定 append_dedup 目标；行级裁决规则显式定义：**live 行与 staging 行同 key 冲突时以 live 为准、staging 仅补 live 缺失的 key**（staging 是本章快照基线+增量，live 是最新权威，禁 staging 陈旧行覆盖 live 新写行——退化回 last-writer-wins 即本 R 要修的病）
  4. 一次性清理（oneoff）：staging/plans 仅当 plans/ 已有对应已提交版本才删；staging/truth/* 先 diff——staging 含而 live 缺的行先重放合并再删（禁直接删=丢数据、禁直接提交=覆盖 live）；resume 清理可考虑按文件粒度（实现时评估，非硬性）
- **验收：并发两写者同章都写后 staging 两写者增量均在；commit 不抹 live 新增行；staging/plans 清空且无数据丢失**

## R4 · state-settling 契约权威语义裁决（T7-06, P1）——已修剔除（2026-08-30 阶段 1 重裁）
- PR #43（c168903 + c112a95）已落：frontmatter 6 updates 全 `append_dedup` + 正文 Update Mode Rules + truth_io keyed upsert 三处一致。本 spec 不再实施

## P2 清单
- **T7-04（P2）** LLM 元叙述 + 未闭合代码栅栏泄漏进 truth 文件；后写完整性检查只覆盖章节/审计，truth 文件从不检查
- **T7-05（P2）** `update_mode:` frontmatter 契约"写一次、读零次、生产全缺"
