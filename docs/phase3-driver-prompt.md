# Phase 3 长跑驱动 Prompt

> 使用方式：新开 ZCode session（工作目录 = 本仓库），把本文全部内容作为首条消息发送。
> 该 session 会自动加载 AGENTS.md 与 MEMORY.md 索引；本 prompt 自包含运行所需的全部操作知识。

---

## 任务定位

执行 **Phase 3：20 万字最小探测长度长跑**。目的：验证框架在接近生产长度（项目终极目标千万字稳定生成）下的纵向稳定性——不是短探针的"零缺陷单点验证"，而是**长程数据采集**：质量趋势、失败分类、成本曲线、人工干预频次。

前置状态（已达成，勿重复验证）：V2 收敛循环 probe28→33 六轮 GO（见 memory `poc-e2e-session27-probe33-go.md`）：批 #20-#27 全部根因修复并经 probe33 独立验证轮确认零框架缺陷暴露（89 派发 $0.70、matrix_structure/hooks_structure 全程零、advance 场景一次过）。git clean，`just check` 应全绿（如需确认可跑一次）。

## 运行参数

- **项目目录**：`novel-xinghuo-phase3`（seed 与 probe 系列相同：`tests/fixtures/outline-example.md`，novel.json = 星火燃穹，C30 对齐）
- **目标**：跑到 book-closure（约 118 章 / 5 卷 ≈ 20 万字），或累计正文字数 ≥20 万字，先到者。**口径规则**：章均实际 ~1570 字（挂账观察项 #7），book-closure 先到时全程约 18-19 万字——收尾报告与 longitudinal 数据一律按 `chapters/*.md` 实测字数如实报告，不得宣称"20 万字达标"；字数缺口本身记为 pacing 观察数据
- **成本预算**：软顶 $25（按 probe33 速率估算全程 ~$15-18；每卷边界 ~$3 检查点）；硬顶 $30 触发即停并报告
- **时长预期**：~30 分钟/章（含裁决周转），全程 50-70 小时——**必然跨多个 session**，按"多 session 续跑协议"操作

## 启动序列

```bash
export SHENBI_LLM_API_KEY=$(grep -oE '^SHENBI_LLM_API_KEY=.*' .env | cut -d= -f2-)   # 不要回显完整 key
just pipeline-init tests/fixtures/outline-example.md novel-xinghuo-phase3
# 确认 C30 对齐：
python3 -c "import json; print(json.load(open('novel-xinghuo-phase3/novel.json'))['title'])"   # 应输出 星火燃穹
# 启动 runner（每次启动前确认无残留 runner：pgrep -f run_pipeline）：
nohup ./run_pipeline.sh novel-xinghuo-phase3 > /tmp/phase3-run1.log 2>&1 & disown
```

## 监控循环（每次轮询的模板）

```bash
sleep 580   # 或按需 540-600
python3 -c "
import json
s = json.load(open('novel-xinghuo-phase3/pipeline-state.json'))
p = s.get('pending_checkpoint', s.get('pending', {}))
print('pending:', json.dumps(p, ensure_ascii=False)[:300])
print('budget:', json.dumps(s.get('chapter_loop', {}).get('retry_budget_consumed', {})))
"
```

runner 在每个 checkpoint 处退出（blocked）；提交裁决后重启 runner 继续（日志序号递增：/tmp/phase3-run2.log…）。

## 裁决分级政策（Phase 3 与短探针的关键差异）

短探针逐 checkpoint 全量裁决；118 章约 400 个 checkpoint，全量人工复核不可行。采用分级：

**Tier 1 — 全量裁决**（写完整裁决书 + 独立复核）：
- escalation（任何）
- genesis-complete、volume-boundary、book-closure
- 任何含 BLOCKING/CRITICAL 的 per-chapter，或 retry_budget >0 的章
- settle 出现新 hook 状态迁移异常 / 增量块数与章号不匹配

**Tier 2 — 轻量 approve**（一行式裁决书，机器门全绿即可放行）：
- 干净的 chapter-memo / state-settle / per-chapter（0 BLOCKING/CRITICAL、settle 零重试、结构检查零、代词合法）
- 裁决书仍要落盘（保持审计链完整），格式可为三行：checkpoint、核对结论（引 2-3 个机器证据）、决策 approve

Tier 2 证据取数（每次裁决前必跑；任一非零或本章有 retry → 升 Tier 1）。`pipeline-resume.log` 跨重启追加，用行号游标只看上次裁决之后的新增段：
```bash
D=novel-xinghuo-phase3; mkdir -p $D/adjudications
python3 -c "
import json
s = json.load(open('$D/pipeline-state.json'))
cp = s.get('pending_checkpoint', {})
print('checkpoint:', cp.get('type'), '| chapter:', cp.get('chapter'))
print('context:', (cp.get('context') or '')[:160])
cur = cp.get('chapter')
rb = s.get('chapter_loop', {}).get('retry_budget_consumed', {})
print('retry_budget(本章):', {k: v for k, v in rb.items() if cur and k.startswith(f'ch{cur}-')})
"
L=$(wc -l < $D/pipeline-resume.log); C=$(cat $D/adjudications/.log-cursor 2>/dev/null || echo 0)
tail -n +$((C+1)) $D/pipeline-resume.log > /tmp/phase3-newlog.txt
grep -cE "BLOCKING|CRITICAL" /tmp/phase3-newlog.txt                    # 期望 0
grep -c "matrix_structure\|hooks_structure" /tmp/phase3-newlog.txt    # 期望 0
# 代词无机器门：人工抽查 staging 正文主角代词（知识库 #3，已发布前章为事实源）
```

裁决书模板：`novel-xinghuo-phase3/adjudications/adjudication-NNN.md`（NNN 全程递增；放项目目录内而非 /tmp——跨 session / 机器重启不丢，且已被 /novel-*/ gitignore 覆盖），提交：
```bash
export SHENBI_LLM_API_KEY=$(grep -oE '^SHENBI_LLM_API_KEY=.*' .env | cut -d= -f2-)
just pipeline-review novel-xinghuo-phase3 <approve|modify|reject> novel-xinghuo-phase3/adjudications/adjudication-NNN.md
wc -l < novel-xinghuo-phase3/pipeline-resume.log > novel-xinghuo-phase3/adjudications/.log-cursor   # 决策提交后推进游标
nohup ./run_pipeline.sh novel-xinghuo-phase3 > /tmp/phase3-runK.log 2>&1 & disown
```

**Tier 1 异常裁决必须用独立 subagent 出裁决意见**（主 agent 监督模式，见 memory `poc-e2e-staged-calibration-plan`；评分/审计类判断不得由被审对象自身做出，AGENTS.md G3.4 同源）。

## 裁决知识库（33 轮探针沉淀，遇到对应场景按此执行）

1. **modify 契约**（cli.py C30 audit-T1 I2）：`modify` 会 discard staging 并重派发——手改 staging 副本必被丢弃。人工修订必须：落 **live/committed 路径**（正文在 `chapters/chapter-N.md`）提交 modify；或把修订指令写进 **feedback 文件**走 modify_feedback（重派发 prompt 会注入，模型会在重生成中并入并在产物里显式记录）。
2. **重派发行为**：chapter-memo modify → 回拨重跑 chapter-planning；per-chapter modify → 触发 re-settle（#45）；escalation approve → 重置重试计数并重派失败步骤。
3. **代词纪律**：设定文件双写「她/他」是模板形态；正文代词以**已发布前章为事实源**（本 seed 历史上是阿烬/顾烬=他）。单写「她」只能指女性角色；发现指主角的单写漂移 = P1，走 per-chapter modify 手改 live 正文 + truth 同步（替换前先做同句双代词消歧）。
4. **hook 账核对**：计划 hook 账只能引用 pending_hooks 已注册的 MH 系列（操作 open/advance/defer/resolve）；`CP-` 等未注册前缀 = 自造 hook（P2，modify 删除）；advance 的机器表达 = registry 行合法迁移（PLANTED→RELEVANT→…）+ detail 段 colon bullet（last_reinforced/证据完整重述）。
5. **settle 验证点**：sidecar `state-settling-decisions.json` 的 chapter 与当前章一致；matrix 增量块数 = 已收束章数；`matrix_structure`/`hooks_structure` 在 resume log 中零出现（全程监控）。
6. **已知 transient（勿立项）**：settle 偶发 `output_length=0`（模型把补全预算耗在推理通道、正文空、no_files_parsed 隔离）——**重派一次即愈**；仅当 ≥2 次复现才按 systematic-debugging 立项查 json_mode/reasoning 配置。
7. **挂账观察项（勿过度施工）**：`ensure_table_header` 的 `header in content` 精确匹配在 live 已有字样略异表头 + create-path 场景可能双表头（当前 pending_hooks 合并不走该路径）；current_state SHELL 模板残留 genesis 示例势力名（P3）；章均字数 ~1570 vs 目标 1700（卷级 pacing 复核职责，volume-boundary 时看趋势）。
8. **失败取证路径**：`_quarantine/`（隔离输出）、`diagnostics/`（失败留档）、`trace.jsonl`（派发时间线，含 chapter/success）、`cost/token-ledger.jsonl`（逐派发成本）、`novel-*/pipeline-resume.log`（gate 与合并事件）。

## P0-P2 处理协议（运行中出现框架缺陷时）

1. 按 `superpowers:systematic-debugging` 四阶段：先 Phase 1 证据（错误原文、复现、trace 时序、多组件边界），**禁绝先改后查**；2+ 同一失败 = 框架级缺陷假设。
2. 区分三层：框架代码缺陷（修代码）/ gate 误报（修检查）/ 内容缺陷（modify 产物，不动代码）。
3. 修复走 TDD（red→green）+ Conventional Commits；宽面回归（`uv run pytest tests/unit/pipeline/ tests/unit/gates/ tests/pipeline/ -q`）；修完提交、裁决放行、续跑。
4. **防过度施工**：只修实际发生的问题；观察项只记录不动手。

## 纵向数据采集（Phase 3 核心交付物，边跑边记）

维护 `novel-xinghuo-phase3/phase3-longitudinal.md`，每 10 章追加一节：

- 章级评分趋势（review-resonance overall 分序列；probe31 基线 80 分档）
- 失败分类统计：escalation 次数×根因类（gate 误报/模型 transient/内容缺陷/框架缺陷）、每章平均派发数与重试数
- 成本曲线：累计 $ 与派发数（`cost/token-ledger.jsonl` 求和），每卷边界记录一次
- 人工干预清单：每次 modify/reject 的章号、问题类、修订量
- 结构健康：matrix 增量块数、hook 状态分布、pending_hooks 字节增长趋势（长程 token 压力指标，probe33 曾见 7787 字符截断 WARN）

## 中止与续跑

- **每卷边界**（~22 章）做一次 Tier 1 全量裁决 + 数据节追加 + 成本检查（>$3/卷预期时先分析再继续）。
- **中止条件**：硬顶 $30；或同一框架缺陷 3 次修复仍复发（质疑架构，停下写报告）；或连续 3 章 escalate 同一根因。
- **多 session 续跑**：新 session 重读本 prompt + memory 索引即可接管；状态全在 `novel-xinghuo-phase3/pipeline-state.json`（pending checkpoint 即断点）；重启 runner 前先 `pgrep -f run_pipeline` 清残留；裁决书序号接续项目内最大值（`ls novel-xinghuo-phase3/adjudications/ | grep -oE '[0-9]+' | sort -n | tail -1`）——裁决书与 `.log-cursor` 都在项目目录内，跨 session/重启不丢；若意外缺失，裁决内容可从 pipeline-state.json 的 checkpoint trail 重建对账。
- runner 进程不随 session 存活的问题：始终用 `nohup … & disown`，启动后 `pgrep` 验证。

## 收尾（book-closure 或中止后）

1. 终验扫描：总派发/总成本/章数/实测字数（`wc -m chapters/*.md` 汇总，非目标宣称值）/双 structure 计数/escalation 分类统计/hook 终态对账。
2. 写 session memory（含 Phase 3 纵向数据结论 + 遗留观察项）+ MEMORY.md 索引行。
3. 最终报告：GO/NO-GO for 千万字目标 + 纵向判据缺口是否补齐（对照 memory `goal-prompt-smoke-assessment` 所列：纵向判据/失败分类/扩展性数据）。
4. 不要提交 novel-*/ 与 /tmp 产物（已 gitignore）；只提交框架修复与文档。

---

*生成于 2026-10-06，V2 GO 判定后。基线证据：probe33（session27）。*
