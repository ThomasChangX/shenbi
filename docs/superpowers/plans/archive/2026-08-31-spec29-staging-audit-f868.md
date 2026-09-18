# Plan · spec #29 Revised — R1-R3（staging 写审计 / F868 / F814 残留）

> Date: 2026-08-31 | Spec: docs/superpowers/specs/2026-08-16-audit-truth-upsert-wiring-fix.md (Revised)

## 任务

### T1 · R1 staging 写审计归一化（infra，协调者实现）

`_with_write_audit`（dispatch_helper.py:2118）：

1. 签名加 `uses_staging: bool = False`；`dispatch_skill` 两个调用点（:2253/:2265）透传既有 `uses_staging` 局部量。
2. `uses_staging=True` 时：
   - watch 面扩为 `watch + [f"staging/{p}" for p in watch]`；
   - pre/post 快照后做**键归一化**：快照键 `staging/<declared>` 且去前缀后 ∈ 声明集 → 重命名为去前缀键；其余（staging 内越权写、非声明 staged 路径）保留原键 → audit_writes 按 undeclared 报违规（期望行为）。
   - 注意双写可见性：同章 live+staged 同文件并存时归一化后 post 用 staged 内容（后写胜语义，与提交路由一致）；归一化实现为「staged 键存在时覆盖同名声明键」。
3. 单测（tests/unit/pipeline/test_dispatch_skill_write_audit.py 追加，沿用其 fake-api 模式）：
   - staged 声明写（fake 写 `staging/genre-config.json`… 不适用——选真实 uses_staging 技能契约（state-settling 类 truth 路径）或直接用 genre-config + 手工 staging 前缀 watch 推导）：断言账本记录 changed 含归一化键、无空过；
   - staging 内越权写（fake 额外写 `staging/truth/undeclared.md`，watch 面含 staging/truth glob 时）→ 违规。
   - 现有测试全数保持绿（默认 uses_staging=False 零行为变化）。

### T2 · R2 F868 volume-consolidation 三面一致（skill 面）

1. frontmatter `reads` 增 `truth/volume_summaries.md`（放在 pending_hooks 之前，与消费顺序一致）。
2. 正文「追加」语义**四处全部对齐**（阶段 3 审查 I2）：:72 输出格式段、:112 归档步骤、:114 执行步骤 6、:169 精确输出模板引导句——统一改为「读取既有 `truth/volume_summaries.md`（若存在），保留全部既有卷章节，追加本卷章节后输出完整文件」；执行步骤清单同步加读旧步骤。
3. mode 保持 `create_or_overwrite`（H2 分节散文结构，非键控表行，不走 append_dedup——依据 spec R2 修复方向的第二选项）。
4. 改动后跑 `shenbi-sync-contracts` 再生 auto-block/body（sync_contracts.py:124-137），再生产物一并 pathspec commit（just check 含幂等闸）。
5. 验证：`shenbi-validate G4 shenbi-volume-consolidation` 通过。

### T3 · R3 声明形态对齐（零行为变更 + F840 键轴修正）

1. `skills/shenbi-score-volume/SKILL.md` `writes:` 段的 `truth/volume_score_trend.md`（append_dedup, key: chapter）条目挪入 `updates:` 段（legacy.py:178-202 双段构建，路由行为不变）。
2. `skills/shenbi-review-arc-payoff/SKILL.md:28-29` 的 `truth/arc_payoff_trend.md` 声明键 `chapter` → `volume`（文件行模板首列即 volume，:151-153；修 F840 功能性键错配）。
3. G4 + 既有 lint 通过。

### T4 · 验收收口

spec 验收 1-4 逐条实跑 + `just check` 全绿。

## 纪律

- pathspec commit（显式列文件）；不碰用户 unstaged 改动。
- TDD：T1 先写 RED 测试再实现。
