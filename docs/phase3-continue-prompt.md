# Phase 3 续跑驱动 Prompt（session30+：继续修复与优化）

> 使用方式：新开 ZCode session（工作目录 = 本仓库），把本文全部内容作为首条消息发送。
> 该 session 会自动加载 AGENTS.md 与 MEMORY.md 索引；本 prompt 自包含运行所需的全部操作知识。
> 生成于 2026-10-08 session29 收束（三根因修复批 + ch58 解堵验证后）。上游协议源：`docs/phase3-driver-prompt.md`（裁决分级/知识库/纵向采集等未重述条款继续有效）。

---

## 任务定位

继续 Phase 3 长跑至 book-closure（118 章），同时**按优先级处理已知框架项与观察项**。核心纪律不变：长程数据采集优先于进度、修根因不修表象、防过度施工（观察项只记录不动手）。

前置状态（已达成，勿重复验证）：
- **59/118 章闭环在望**（ch58 全链一次过：resonance 89、审计零问题；ch59 drafting 经裁决 195 定向重跑过闸、settle 经裁决 196 approve，现停于 ch59 per-chapter 收束 checkpoint——放行即进 ch60）。卷一 87 / 卷二 88 / payoff 81×2 / CP 399RED→57YELLOW；累计 ≈20 万字符、~$11（实测见 `cost/token-ledger.jsonl`）
- **session29 三批根因修复已落地**（`2738c376` Plan A 读侧切片 / `15202d0d` 触发型 feedback 死线+进度记忆 / `490496e7` frontmatter 程序不变量；`just check` exit 0）。实测 settle prompt 104K→64K tokens（-38%）
- 裁决书至 **196**（序号接续规则见下，以引导序列实拉为准）；memory 最新条目 `poc-e2e-session29-plan-a-landing.md`

## 新 session 引导序列（先跑这个，再看任务清单）

```bash
pgrep -fl run_pipeline | head -2                    # runner 是否还在跑
python3 -c "
import json
s = json.load(open('novel-xinghuo-phase3/pipeline-state.json'))
cp = s.get('pending_checkpoint', {})
print('pending:', cp.get('type'), '| chapter:', cp.get('chapter'), '|', (cp.get('context') or '')[:120])
print('cursor chapter:', s.get('chapter_loop', {}).get('current_chapter'), '| step:', s.get('chapter_loop', {}).get('step_index'))
"
ls novel-xinghuo-phase3/adjudications/ | grep -oE '[0-9]+' | sort -n | tail -1   # 裁决序号接续（文件名字母开头，正则勿加 ^ 锚定——加了会空输出）
C=$(cat novel-xinghuo-phase3/adjudications/.log-cursor); tail -n +$((C+1)) novel-xinghuo-phase3/pipeline-resume.log | grep -vE debug | tail -20   # 上次裁决后新日志（注意：tail -n 不是 -c）
```

- runner 在跑且无 pending checkpoint → 直接进监控循环
- runner 停在 checkpoint → 按裁决分级处理（见上游 prompt；Tier 2 三行裁决随到随放）
- runner 死且无 checkpoint → 重启（先 `pgrep -f run_pipeline` 清残留）

## 任务清单（按优先级）

### T0 — resolve 读切片（**ch70 卷三界前必做**，唯一硬前置）

问题：卷界触发 `shenbi-foreshadowing-resolve` 全池清点，其 pending_hooks 读是全量（当时刻意不切——它是审计者），但池已 121KB（2026-10-08 实测，续涨中）> 32K 单文件帽 → 头尾残篇、中间 TRIGGERED 钩失明 → 清点盲区 + 编造风险。**下次卷界（ch70/71）即触发。**

修法（复用 Plan A 骨架，小改动）：
1. `src/shenbi/pipeline/read_extractors.py` 新增 `extract_hooks_inventory_scoped(content) -> str`：解析 `## 总览` 表的「当前生命周期」列，grounding 集 = **TRIGGERED** 行的钩 ID；输出 = frontmatter + 总览全量 + 该集详情段 + 省略哨兵。异常形态（无总览/无详情/无 TRIGGERED）→ `""`（全量回退 + WARN，纪律同现有 extractor）
2. `contracts/loader.py` READ_EXTRACTORS 注册 `hooks_inventory_scoped`；`src/shenbi/pipeline/dispatch_helper.py` 读循环加路由分支（照抄 `hooks_audit_scoped` 分支形态；注意该文件在 `pipeline/` 下，不在 `dispatcher/` 下）
3. 契约：`skills/shenbi-foreshadowing-resolve/SKILL.md` reads 改 dict-form——`truth/pending_hooks.md → hooks_inventory_scoped`、`truth/chapter_summaries.md → recent_increments`、补读 `truth/volume_summaries.md`（卷级摘要承接中段视野，模式同 settle）
4. TDD：TRIGGERED 行 grounding / 无 TRIGGERED 回退 / 总览畸形回退 / dispatch 循环集成（哨兵入 prompt、WARN-free happy path）
5. `uv run python -m shenbi.sync_contracts` 再生 AUTO 块 → 宽面回归 → `just check` → 提交（conventional commit）

### T1 — 续跑与例行（占大头）

- 监控循环照上游 prompt（每 ~580s 轮询；checkpoint 停→Tier 2 三行裁决→放行→重启）
- **ch60 纵向数据点 #7**：方案 A 后首个段数据（settle prompt 斜率实测、成本/章、resonance 带）——这是「二次方→线性」判定的第一手证据
- **ch70/71 卷三界 Tier 1 全量裁决**：同时验证 T0 修法实战 + **P1 修复首次实战**（观察 `trigger_step_skipped_done` 事件与 feedback 活路由；扇出重入不再重派已过步骤）

### T2 — 观察项（带触发条件，勿提前施工）

| 观察项 | 触发条件 | 动作 |
|---|---|---|
| lifecycle reasoning 洪泛（completion 钉 49152/空输出+计费） | 单轮 ≥2 次「空输出+计费完成」 | 模型侧退化：评估 lifecycle 换模型/降 reasoning，不堆重试（裁决 195 判据 3） |
| 章尾张力 G4.cd.no_hook 复发 | 任一章 drafting 因 no_hook 重试 ≥2 次，或连续 3 章各 ≥2 次 | **前置契约化**：章尾钩口径写入 drafting SKILL.md 产出契约 + 备忘模板段 6 必填项（裁决 195 判据 4；修法是把约束从纠正环升级为主契约） |
| resonance 锚点 1/4 维 payload | 卷三界（ch70/71）评估 | 内容层观察，卷界裁决时定性 |
| character_matrix 增长（114KB，未切片） | 撞墙再说（现走截断保底） | 到墙时按 Plan A 模式扩展 |

### T3 — 后续里程碑

- ch94 卷四界 Tier 1；ch118 book-closure（20 万字口径按 `wc -m chapters/*.md` 实测报告）
- **Phase 3 终报**（POC 交付物）：框架缺陷清零情况、成本曲线、质量带、escalation 族谱与根治台账、GO/NO-GO for 千万字

### 挂账不做（千万字决策点再动，防过度施工）

池内证据滚动归档（二次方增长主导项，硬前置）→ volume_summaries 近卷切片（~卷 8）→ append_dedup 合并代价索引化（数百章）→ CP 阈值随卷数缩放。设计规则：**阈值=模型不变量不放宽；规模=切片/归档动态化**。

## 运行纪律（session28-29 新教训，全部实证）

1. **escalation feedback 必须执行器面向**：≤8 行、只含缺陷定位+修法约束+维持项+贴合风格的例句。裁决书全文（monitor 面向）注入会引发 reasoning 洪泛（ch58 实证）。范式参照 `adjudications/feedback-59-drafting.md`
2. **手改产物陷阱**：chapter_loop 无「产物已存在且过闸→跳过派发」短路——escalation 的 approve/modify/reject 都会重派失败步骤并 create_or_overwrite 覆写手改。内容缺陷的唯一可行修复 = approve + 执行器 feedback 定向重跑（裁决 195 机制核验）
3. **瞬态 vs 内容**：判读三连败先分清终局事件与并发病——截断/空输出会被派发层 cap-raise/A0 自愈，**看终局失败计数**（`chapter_step_failed_retrying` 的 failure=gate/dispatch），别把瞬态当根因（裁决 195 意见书对主 agent 的纠正）
4. **Tier 1 异常必须独立 subagent 出裁决意见书**（监督模式不变）；意见书 prompt 须自含全部证据 + 已核实的机制事实
5. **pre-commit ruff 修型**：提交被回滚（Stashed changes conflicted）→ `git add` 工作区版本重提交即可；yamllint 行长 100
6. zsh 坑：`===X===` 裸串触发命令展开；`pgrep -c` 不存在用 `| wc -l`；heredoc 用 `<<'PY'`；`tail -c +N` 是字节不是行——游标是行数必须 `tail -n +$((C+1))`
7. 启动/裁决命令模板、成本硬顶 $30、中止条件、收尾清单：见上游 `docs/phase3-driver-prompt.md` 对应节（继续有效）
8. 不提交 `novel-*/` 与 `/tmp` 产物；只提交框架修复与文档

## 收束（session 结束时）

1. 纵向台账 `novel-xinghuo-phase3/phase3-longitudinal.md` 追加本 session 节（数据点/修复批/观察项变化）。台账在项目目录内且被 gitignore 覆盖——**勿在 docs/ 或仓库根新建同名文件**（会分裂台账）
2. 写 session memory + MEMORY.md 索引行（含：断点章号、pending 状态、下一 session 首任务）
3. runner 处置：若跨长间隙，留跑（nohup 已脱离 session）；若停于 checkpoint，记录裁决序号与游标即可断点续接

---

*生成于 2026-10-08，session29 收束。基线证据：裁决 191-195、纵向台账 session29 节、四提交（2738c376/15202d0d/490496e7/28550997）。*

*2026-10-08 校订（同日评审轮）：① 序号接续命令去 `^` 锚定（原正则匹配字母开头文件名恒空输出）；② 纵向台账/dispatch_helper 路径写全；③ 基线刷新——裁决至 196（ch59 settle approve）、断点=ch59 per-chapter 收束 checkpoint、钩池 121KB。*
