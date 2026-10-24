# 长探针驱动 Prompt v2：星火燃穹·卷一全程（自包含版）

> 使用方式：新开 ZCode session（工作目录 = 本仓库），把本文全部内容作为首条消息发送。
> 该 session 会自动加载 AGENTS.md 与 MEMORY.md 索引；本 prompt 自包含运行所需的全部操作知识。
>
> **v2（2026-10-24）重写说明**：phase3 两份驱动 prompt（driver/continue）已删除——其共享协议
> （监控循环/裁决分级/裁决知识库/修复协议/断点协议）已全部内联进本文件。首跑段（genesis+ch1-5、
> 裁决 #001-#025、五个框架修复 1421337c/33cb0c68/a4efe32e/40324b34/2a00fa81）项目目录已废弃，
> 本版为**重开后的全新首跑**——五修复已在 main，ch1 起即修复批全量首验。首跑段数据结论已内化为
> 本文件的基线数字与已知边界；过程细节见 memory `poc-e2e-vol1-probe-run`。

## 任务定位

- **种子**：`tests/fixtures/outline-example.md`（星火燃穹：千万字/1400 章/12 卷，组诗定名版——payload 与根目录 outline-example.md 逐字节镜像，G0.11 守卫）。
- **目标**：**卷一完整闭环**——全链（genesis→卷纲→逐章 planning/drafting/settle/review）＋卷界收束（卷末章＋arc-payoff/volume-consolidation/score-volume）。
- **卷界动态口径（铁律，首跑段实测教训）**：**收束章号以 genesis 生成的 volume_map 为准，不以 seed 的 110 章为准**。首跑段实测 volume-outlining 自主再分配卷界（卷1=ch1-90、卷2=ch91-190…，自注「差额已由上游卷界吸收」，全书总量守恒待卷界验收对账）。genesis-complete 裁决时读取 volume_map 并**把实际卷一末章号记为运行参数**，此后所有派生口径（里程碑后段观察窗/卷界段/成本时长预期）按实际卷界计算；seed 章号仅作对照记档。
- **中期里程碑（强制，不是可选项）**：ch30「黄金三十章收官」处停一次，出**新契约中期验证报告**（观察项 1-16 阶段结论）——留存锚闸作用域恰在 N≤30，此点必须收一份完整数据再续跑。ch30 是里程碑非卷界。
- **三重目的**：(1) 常规长跑验证（一次过率/成本/纵向数据）；(2) **新契约实弹验证**——G4.cp 三声明硬闸（emotion_tone / payoff 拍 / 留存锚）、G4.cd 账目钩词表、G4.vo 金句与爽点主型行、review-highpoint 声明验收；(3) **卷界技能族首验**——arc-payoff 五维卷评＋假兑现铁律 6、volume-consolidation、score-volume、卷末三连（铭记章→账目清算章→渡问钩）；(4) **修复批全量首验**（首跑段五修复从未在 ch1 起点的干净环境跑过——观察项 15）。
- **驱动模式**：主 agent 监督模式——runner 自跑，session 监控/分级裁决/TDD 修复/纵向采集。
- **防剧透铁律（本探针专属 P1 级）**：卷名组诗（藏头"星火燃穹，薪火相传，一灯长明"）与"无名小调之词=组诗"是卷十二终章彩蛋——**正文、章名、任何 truth/plan/context 文件不得出现组诗全文、藏头句或"组诗"字样**。每次裁决顺带抽查；发现泄漏按 P1 处理（正文层修复，不动装置）。

## 运行参数

- novel 目录：`novel-xinghuo-vol1`（全新 init；若目录已存在=残留，先确认是否重开）
- 成本预期（90 章口径，实际以 volume_map 为准）：修复后预估 ~$0.10-0.14/章 × ~91 章 ≈ **$9-13**；首跑段基线 $1.32/143 派发（drafting 占 42%、其中 60% 是重试浪费——thinking=low 落地后重试面应坍缩）；**硬顶 $25** 维持；每 10 章成本检查点（累计 >$10 先分析再继续）
- 时长预期：~30 分钟/章 → 90 章约 **45-50 小时**，必然跨多个 session，按断点协议操作
- 卷界段观察窗（观察项 11-14）：实际卷末章前 ~10 章起进入卷界观察态（90 章口径即 ch80-91 段）

## 启动序列

```bash
export SHENBI_LLM_API_KEY=$(grep -oE '^SHENBI_LLM_API_KEY=.*' .env | cut -d= -f2-)   # source .env 不注入 uv run 子进程——必须 export；不要回显完整 key
pgrep -f run_pipeline   # 确认无残留 runner，有则先清
just pipeline-init tests/fixtures/outline-example.md novel-xinghuo-vol1
# C30 对齐三查（uv run 与 CI 同构，系统 python 不算证据）：
uv run python -c "import json; n=json.load(open('novel-xinghuo-vol1/novel.json')); print(n['title'], n.get('target_chapters'))"   # 应输出 星火燃穹 1400
nohup ./run_pipeline.sh novel-xinghuo-vol1 > /tmp/vol1-run1.log 2>&1 & disown
```

genesis-complete 裁决（Tier 1）时必做：读取 `truth/volume_map.md` 记录卷一实际末章号与各卷区间 → 写入 vol1-ledger.md 运行参数节（此后按此口径推进；与 seed 差异记对照档，不立项）。

## 监控循环（每次轮询的模板）

```bash
sleep 580   # 或按需 540-600
uv run python -c "
import json
s = json.load(open('novel-xinghuo-vol1/pipeline-state.json'))
p = s.get('pending_checkpoint', s.get('pending', {}))
print('pending:', json.dumps(p, ensure_ascii=False)[:300])
print('budget:', json.dumps(s.get('chapter_loop', {}).get('retry_budget_consumed', {})))
"
```

runner 在每个 checkpoint 处退出（blocked）；提交裁决后重启 runner 继续（日志序号递增：/tmp/vol1-run2.log…）。runner 死于派发中（非 checkpoint）时 pipeline-state.json 的章号/step/retry 指针即断点——直接重启 runner，run_pipeline 会从状态机位置续跑（首跑段实测此形态可行）。

## 裁决分级政策

章数多、checkpoint 多，全量人工复核不可行。分级：

**Tier 1 — 全量裁决**（写完整裁决书 + **独立 subagent 出裁决意见**——评分/审计类判断不得由被审对象自身做出，AGENTS.md G3.4 同源）：
- escalation（任何）；genesis-complete、volume-boundary、book-closure；ch30 里程碑
- 任何含 BLOCKING/CRITICAL 的 per-chapter，或 retry_budget >0 的章
- settle 出现新 hook 状态迁移异常 / 增量块数与章号不匹配

**Tier 2 — 轻量 approve**（三行裁决书，机器门全绿即可放行；每次裁决前必跑取数，任一非零或本章有 retry → 升 Tier 1）：

```bash
D=novel-xinghuo-vol1; mkdir -p $D/adjudications
uv run python -c "
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
tail -n +$((C+1)) $D/pipeline-resume.log > /tmp/vol1-newlog.txt
grep -cE "BLOCKING|CRITICAL" /tmp/vol1-newlog.txt                    # 期望 0
grep -c "matrix_structure\|hooks_structure" /tmp/vol1-newlog.txt    # 期望 0
# 代词无机器门：人工抽查 staging 正文主角代词（知识库 #3，已发布前章为事实源）
```

裁决书模板：`novel-xinghuo-vol1/adjudications/adjudication-NNN.md`（NNN 全程递增；**放项目目录内而非 /tmp**——跨 session 不丢，已被 /novel-*/ gitignore 覆盖）。Tier 2 格式三行：checkpoint、核对结论（引 2-3 个机器证据）、决策 approve。提交：

```bash
export SHENBI_LLM_API_KEY=$(grep -oE '^SHENBI_LLM_API_KEY=.*' .env | cut -d= -f2-)
just pipeline-review novel-xinghuo-vol1 <approve|modify|reject> novel-xinghuo-vol1/adjudications/adjudication-NNN.md
wc -l < novel-xinghuo-vol1/pipeline-resume.log > novel-xinghuo-vol1/adjudications/.log-cursor   # 决策提交后推进游标
nohup ./run_pipeline.sh novel-xinghuo-vol1 > /tmp/vol1-runK.log 2>&1 & disown
```

## 裁决知识库（遇到对应场景按此执行）

1. **modify 契约**：`modify` 会 discard staging 并重派发——手改 staging 副本必被丢弃。人工修订必须：落 **live/committed 路径**（正文在 `chapters/chapter-N.md`）提交 modify；或把修订指令写进 **feedback 文件**走 modify_feedback（重派 prompt 会注入，模型在重生成中并入并在产物里显式记录）。
2. **重派发行为**：chapter-memo modify → 回拨重跑 chapter-planning；per-chapter modify → 触发 re-settle；escalation approve → 重置重试计数并重派失败步骤。
3. **代词纪律**：设定文件双写「她/他」是模板形态；正文代词以**已发布前章为事实源**（本 seed 主角阿烬为**女性**）。单写「她」只能指女性角色；发现指主角的单写漂移 = P1，走 per-chapter modify 手改 live 正文 + truth 同步（替换前先做同句双代词消歧）。
4. **hook 账核对**：计划 hook 账只能引用 pending_hooks 已注册的 MH 系列（open/advance/defer/resolve）；`CP-` 等未注册前缀 = 自造 hook（P2，modify 删除）；advance 的机器表达 = registry 行合法迁移 + detail 段 colon bullet。
5. **settle 验证点**：sidecar `state-settling-decisions.json` 的 chapter 与当前章一致；matrix 增量块数 = 已收束章数；双 structure 在 resume log 零出现（全程监控）。
6. **word_count 重派已带前稿扩写指令（2a00fa81）**：重派不是盲重写——反馈自动附前稿全文＋「逐字保留、既有场景内扩写、禁止整章重写」，扩写量锚定实测缺口。若重派后字数仍发散（±15% 外），查注入面是否吞了前稿，不要归咎模型。
7. **空正文族 = thinking 预算挤占（40324b34 thinking=low 已配 drafting/revision）**：修复前基线 9 次/4 章；本跑预期 **0**。单次出现按 transient 重派一次；≥2 次/10 章 = 配置回退或注入面变化，立项。
8. **escalation 报告分类不可直接信**（误归因已两次复现，第三次立项）：报告的「输出侧格式类」等归因先亲查 `_quarantine/`+`diagnostics/`+`trace.jsonl` 再定性。
9. **decisions-stub**（模型长输出尾部弃写 sidecar，输出 6 字符空壳）：首跑段 2/5 章。出现即走 salvage（重派该步）；**再复现 ≥2 次立框架票**。
10. **重复章题 H1**（首跑 ch5 活数据：`# Chapter 5:`/章题 H1 之外，META 包装后正文前又现一行重复章题 `# 例在，人在`——drafting 重派疑似重发标题行，G4 现无闸）：单章出现走正文层 modify 删重复行；**≥2 章复现立框架票**（G4 加「章题行唯一性」预检候选）。
11. **挂账观察项（勿过度施工）**：`ensure_table_header` 精确匹配双表头边界；current_state SHELL 模板残留 genesis 示例势力名（P3）。
12. **失败取证路径**：`_quarantine/`（隔离输出）、`diagnostics/`（失败留档）、`trace.jsonl`（派发时间线）、`cost/token-ledger.jsonl`（逐派发成本）、`pipeline-resume.log`（gate 与合并事件）。

## 新契约观察项（每次裁决顺带记录——本探针核心交付物之一）

1. **留存锚闸**（G4.cp.retention_anchor，N≤30 硬闸）：拦截次数；锚章对齐**以生成 volume_map/卷纲为基线**（首跑段实测创世重排锚位：智识小胜 ch4→ch10 与老塾师之死合并、组织钩散 ch56 首设点+ch110 固定点——这是已知行为非缺陷；本跑重排可能再现，记录实际排布即可）；其余非锚章占比高不是失真，锚章缺位才是。ch31 起闸转 SKIP，确认无越界拦截。
2. **payoff 拍声明质量**：类型应取自卷一爽点主型（扮猪吃虎＋基建经营头脑）；「无＋理由」连续 ≥3 章 = 爽点断供（P1）。
3. **highpoint 声明验收**：蓄压-释放比拦截的误报/真偷工判别（先查正文再定性）。
4. **账目钩过闸真实性**（G4.cd has_ledger：≥2 处独立数字串）：过闸章抽样 3 章人查，看是否有"末段凑两个数字"的投机过闸。
5. **七型钩轮换**：chapter-pattern MONOTONY_ENDING（N=2）报警率；>10% 章触发 = 词表或写作侧问题，记 P2 候选。
6. **emotion_tone 抑扬**：连续同基调 N=4 报警率；卷一基调应随剧情下沉（围城→城破→夺名→驿站之冬）但每 3-4 章有呼吸（完颜嫂式喜剧位）。
7. **金句落位**：卷区段「金句与梗位」行 → 章中兑现。前 5 句按 seed 排期：ch1 三句（"别人穿越送金手指，我穿越送债务。"/"预知历史的唯一用处…"/老驼"记住的事，别烂在肚里。"）＋ ch2 两句（"权贵永远先走…"/"你不是不死——你只是还会再来。"）。逐字还是化用？记档（首跑段结论：落位超 seed 设计，专业级——本跑看是否复现）。
8. **悬念账本埋设**：ch2 无名小调初哼（哼调不写词）；ch3 灰烬"下辈子再见，我总会站在赢的一边"（五百年宿敌定约）。
9. **遗物匣**：ch2 红纸包（第一件遗物）；ch16《鉴录》首批名字；ch20 帖木哥最后一班岗（站房的灯亮到天明）。
10. **组诗防泄漏**（见铁律；首跑段全库干净，本跑维持抽查）。

## 卷界面观察项（实际卷末章前 ~10 章起与收束时记录——核心交付物之二）

11. **arc-payoff 五维卷评 + 假兑现铁律 6 首验**：卷一钩（灰烬终约/灯之谜/小调）的 resolve 判定是否走"暂缓"第三态（跨卷窗口）；core 钩无假兑现垫场时是否按敷衍计分。
12. **中点反转落位**：卷一中点反转"预知失效：救不了城，救下了名录——金手指换了形态"应落在**卷长 45-55% 窗口**（90 章口径 ≈ ch40-50；按实际卷界换算）。落位与否记档。
13. **卷末三连**：卷末章区间应兑现 铭记章→账目清算章→渡问钩 三连结构；卷一卷末钩子按 seed（骨哨在雪夜发烫/《鉴录》半部南去/公司先遣船测绘新航道/货单"活货"栏）。
14. **卷级技能族实弹**：volume-consolidation、score-volume、ledger/pool 归档在卷界的执行与产物完整性；卷二卷区段（若生成）是否带「爽点主型」行与「金句与梗位」行。

## 修复批持效验证（观察项 15——五修复从未在 ch1 起点干净环境跑过）

- **thinking=low（40324b34）**：空正文 0 复发（修复前基线 9 次/4 章）——判据见知识库 #7
- **word_count 前稿扩写（2a00fa81）**：首个字数重派章的收敛性（扩写后 vs 实测缺口 ±15% 内）；棘轮（首试偏短→重试加码→过闸超发）与振荡（重派反恶化）双形态应消失
- **水平线归一化（33cb0c68）**：live outline 零 `---` 垃圾线；G4.lb 基线脆弱性维持观察（<3 完整新地点重派仍败为已知边界）
- **区间格正则族 + 总览表 bootstrap（1421337c）**：`第N-M章` 族过闸；线索总览表自动镜像（首跑 12 线索行自愈复现）
- **executor 帽 49152（a4efe32e）**：drafting 不再触 length_truncation 钉顶

## 保量对账（观察项 16——千万字目标的量纲护栏）

- 每 10 章对账：gate 口径成稿字数 vs 计划字数超发率（首跑段基线：ch1 +18.6%/ch2 +12.7%/ch3 +0.8%/ch4 +9.1%——写方自估虚高 15-25% 是模型能力边界，未修，thinking=low 不治）
- **卷界 volume-budget ±3% 强制对账**（`just volume-budget novel-xinghuo-vol1`）
- 预警线：+9~19% 超发若持续 1400 章 → 总量 10.9-11.9M 越千万目标 9-19%——超发率不收敛写入收束报告（GO/NO-GO 判据之一），不在章层修

## 新契约已知边界（不要误判为缺陷）

- 留存锚窗口固定 30 章（G4 硬编码；retentionWindow 配置指针是历史死键已拔除——评审决议）。
- 章长 ~7143 字/章是种子数学（千万字/1400 章）；微粒钩 2500-3500 字铺、牵引点 800-1200 字是审计底账——两套口径是分层不是矛盾。
- G4.vo.quote_line 是 WARN 级不拦；「爽点主型」行缺失时 payoff 拍走题材词表回退，合法。
- 假兑现垫场的验收主体在 arc-payoff（卷界）——章层面只记录 hook 账推进方式列的「假兑现」标注是否出现。
- G4.cp.missing_* 若在**新产出**的备忘上高频触发（>3 章）→ 不是模型问题，是 dispatch 注入面缺口，框架 P1 走 TDD。

## 首跑段已知残留（记档未动手——勿当新缺陷重复诊断）

- threads_overview 全档回退（live 缺 `## 线索详情`/`## 章节推进表` 标题；token 成本随卷增长，成本曲线异常再立项）；pool 侧 `sync_pool_overview_rows` 同构无 bootstrap（当前无受害者）。
- escalation 报告误归因两次复现（第三次立项，见知识库 #8）；attempt2 诊断档缺位（复现立项）。
- genre-config `max=12000` 死配置（G4 单向地板无上限闸——保量对账的观察面即它的替代护栏）。
- resonance 基线 78-84（首跑 ch1-4 = 78/84/79/81）低于 Phase3 带（80+）——单卷内判趋势不判绝对值。
- 卷界再分配本身（110→90）是 volume-outlining 自主行为，全书总量守恒在卷界验收对账——不立项。

## P0-P2 处理协议（运行中出现框架缺陷时）

1. 按 `superpowers:systematic-debugging` 四阶段：先 Phase 1 证据（错误原文、复现、trace 时序、多组件边界），**禁绝先改后查**；2+ 同一失败 = 框架级缺陷假设。
2. 区分三层：框架代码缺陷（修代码）/ gate 误报（修检查）/ 内容缺陷（modify 产物，不动代码）。
3. 修复走 TDD（red→green）+ Conventional Commits；宽面回归（`uv run pytest tests/unit/pipeline/ tests/unit/gates/ tests/pipeline/ -q`）；修完提交、裁决放行、续跑。
4. **防过度施工**：只修实际发生的问题；观察项只记录不动手。

## 纵向数据采集（边跑边记：novel-xinghuo-vol1/vol1-ledger.md）

- 逐章行：章号/实测字数（gate 口径）/超发率/cost/tokens/一次过 or retry（含 retry 类型）/新闸拦截明细/emotion_tone/payoff 拍（类型｜强度）/章尾钩型/resonance 分/空正文计数。
- 汇总面：全链一次过率；双 structure（matrix/hooks）零出现验证；escalation 分类统计（注意知识库 #8 误归因）；drafting 重试占比（首跑段 42%×60% 浪费——修复后应显著坍缩）；观察项 1-16 逐项结论。

## 中止与续跑

- 止损三条件（任一即停）：硬顶 $25；同一框架缺陷 3 次修复仍复发（质疑架构，写报告）；连续 3 章 escalate 同一根因。
- **断点两种形态**：① checkpoint 停（pending_checkpoint 非 none）→ 按裁决分级处理；② 派发中死亡（pending=none）→ pipeline-state.json 的章号/step/retry 指针即断点，清残留直接重启 runner 续跑（首跑段实测形态）。
- **多 session 续跑**：新 session 重读本 prompt + memory 索引即可接管；重启前 `pgrep -f run_pipeline` 清残留；裁决序号接续项目内最大值：`ls novel-xinghuo-vol1/adjudications/ | grep -oE '[0-9]+' | sort -n | tail -1`（**正则勿加 `^` 锚定——文件名字母开头，加了会空输出**）；裁决书与 `.log-cursor` 都在项目目录内，跨 session 不丢。
- **跨契约升级续跑**：若暂停期间 main 落了新的「必填字段+硬闸」批，重启 runner 前先 `uv run python tools/plan_craft_backfill.py novel-xinghuo-vol1 --apply`（默认 dry-run 先看报告）。
- 停跑时把当次 /tmp/vol1-runK.log 尾部（~200 行）cp 进 `novel-xinghuo-vol1/diagnostics/`——/tmp 跨重启不保，裁决证据链要落在项目内。
- runner 进程不随 session 存活：始终 `nohup … & disown`，启动后 `pgrep` 验证。
- **卷一收束后即停**：不开跑卷二——GO 与否走收束报告，卷二是下一个探针/长跑的事。

## 收束（卷界完成后）

1. 终验扫描：总派发/总成本/章数/实测字数（`wc -m`，非宣称值）/超发率与保量对账结论/双 structure 计数/escalation 分类/hook 终态对账/卷界总量守恒对账（volume-budget ±3%）。
2. **新契约实弹验证报告**（观察项 1-10）＋**卷界面验证报告**（11-14）＋**修复批持效报告**（15）＋**保量结论**（16）。
3. GO/NO-GO 建议：卷二续跑 / 修复批先行 / 契约回滚项清单。
4. 写 session memory（含断点章号、pending 状态、下一 session 首任务）。

## 挂账不做（防过度施工）

- 不修种子内容层问题（除非 P0 阻塞）——组诗/节奏四修/卖点表刚过四轮定稿与双评审，实弹数据先行。
- 不动千万字工程挂账项（A2 locations/relationships 长跑化、B 归档参数化、C 再预算护栏等）。
- 不给七型钩/抑扬排程加新机器闸（检测面够用；第二次同类契约变更才上 plan_format 版本化——AGENTS.md 纪律）。
- 不跑发布切分——发布层已有 `tools/release_split`（spec #70，`just release-split`），发布是交付后动作非探针职责；chapters 产物留存即可直接切。
- 卷二不开跑（见中止与续跑）。
