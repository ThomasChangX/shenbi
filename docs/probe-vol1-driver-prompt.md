# 长探针驱动 Prompt：星火燃穹·卷一全程（ch1-110+卷界）

> 2026-10-24 定稿。本探针在 Phase 3 长跑（118 章/$18.52/五卷 87→91）验证过的管线之上，
> 首次实弹运行 2026-10-23 商业节奏契约批（五提交 d8f8e950→567ca2b0），并首次对该种子
> 跑完整卷界收束链（arc-payoff/volume-consolidation/score-volume）。
> 共享协议（监控循环/裁决分级/修复协议/断点协议）与 `docs/phase3-driver-prompt.md` 同构，
> 该文件是本 prompt 的上位参考，冲突处以本文件为准。

## 任务定位

- **种子**：`tests/fixtures/outline-example.md`（星火燃穹：千万字/1400 章/12 卷，组诗定名版——payload 与根目录 outline-example.md 逐字节镜像，G0.11 守卫）。
- **目标**：**卷一《星台雪夜饼初分》完整闭环**——ch1-110 全链（genesis→卷纲→逐章 planning/drafting/settle/review）＋卷界收束（ch110 卷末章＋卷级验收），约 79 万字。
- **中期里程碑（强制，不是可选项）**：ch30"黄金三十章收官"处停一次，出**新契约中期验证报告**（观察项 1-10 阶段结论）——留存锚闸的作用域恰在 N≤30，此点必须收一份完整数据再续跑。
- **三重目的**：(1) 常规长跑验证（一次过率/成本/纵向数据）；(2) **新契约实弹验证**——G4.cp 三声明硬闸（emotion_tone / payoff 拍 / 留存锚）、G4.cd 账目钩词表、G4.vo 金句与爽点主型行、review-highpoint 声明验收；(3) **卷界技能族首验**——arc-payoff 五维卷评＋假兑现铁律 6、volume-consolidation、score-volume、卷末三连（铭记章→账目清算章→渡问钩）。
- **驱动模式**：主 agent 监督模式——runner 自跑，本 session 监控/分级裁决/TDD 修复/纵向采集。
- **防剧透铁律（本探针专属 P1 级）**：卷名组诗（藏头"星火燃穹，薪火相传，一灯长明"）与"无名小调之词=组诗"是卷十二终章彩蛋——**正文、章名、任何 truth/plan/context 文件不得出现组诗全文、藏头句或"组诗"字样**。每次裁决顺带抽查；发现泄漏按 P1 处理（正文层修复，不动装置）。

## 运行参数

- novel 目录：`novel-xinghuo-vol1`
- 章数目标：111（ch1-110 ＋ 卷界收束节点）；ch30 是里程碑非卷界（卷一实为 110 章，勿混）
- 成本预期：~$0.16/章 × 111 ≈ **$18-20**（Phase 3 实测口径）；**硬顶 $25**；每 10 章检查点（>$12 时先分析再继续）；ch30 中期报告为强制停点；卷界 Tier 1 全量裁决
- 时长预期：~30 分钟/章 → **55-60 小时**，必然跨多个 session，按断点协议操作

## 启动序列

```bash
export SHENBI_LLM_API_KEY=$(grep -oE '^SHENBI_LLM_API_KEY=.*' .env | cut -d= -f2-)   # source .env 不注入 uv run 子进程——必须 export
just pipeline-init tests/fixtures/outline-example.md novel-xinghuo-vol1
# C30 对齐三查：novel.json title=星火燃穹；目标章节数=1400；卷章预算合计=1400
#   python3 -c "import json; n=json.load(open('novel-xinghuo-vol1/novel.json')); print(n['title'], n.get('target_chapters'))"
pgrep -f run_pipeline   # 确认无残留，有则先清
nohup ./run_pipeline.sh novel-xinghuo-vol1 > /tmp/vol1-run1.log 2>&1 & disown
```

## 新契约观察项（每次裁决顺带记录——本探针核心交付物之一）

1. **留存锚闸**（G4.cp.retention_anchor，N≤30 硬闸）：拦截次数；8 个锚章章号是否与 seed 留存漏斗对齐（ch1 开篇双钩/ch3 宿敌定约/ch4 智识小胜/ch10 组织钩/ch19-20 情感锤/ch24 智力爽/ch30 悬念入卷）——其余 22 章为合法「非锚章」，占比高不是失真；锚章错位才是。ch31 起闸转 SKIP，确认无越界拦截。
2. **payoff 拍声明质量**：类型应取自卷一爽点主型（扮猪吃虎＋基建经营头脑）；「无＋理由」连续 ≥3 章 = 爽点断供（P1）。
3. **highpoint 声明验收**：蓄压-释放比拦截的误报/真偷工判别（先查正文再定性）。
4. **账目钩过闸真实性**（G4.cd has_ledger：≥2 处独立数字串）：过闸章抽样 3 章人查，看是否有"末段凑两个数字"的投机过闸。
5. **七型钩轮换**：chapter-pattern MONOTONY_ENDING（N=2）报警率；>10% 章触发 = 词表或写作侧问题，记 P2 候选。
6. **emotion_tone 抑扬**：连续同基调 N=4 报警率；卷一基调应随剧情下沉（围城→城破→夺名→驿站之冬）但每 3-4 章有呼吸（完颜嫂式喜剧位）。
7. **金句落位**：卷区段「金句与梗位」行 → 章中兑现。前 5 句按 seed 排期：ch1 三句（"别人穿越送金手指，我穿越送债务。"/"预知历史的唯一用处…"/老驼"记住的事，别烂在肚里。"）＋ ch2 两句（"权贵永远先走…"/"你不是不死——你只是还会再来。"）。逐字还是化用？记档。
8. **悬念账本埋设**：ch2 无名小调初哼（哼调不写词）；ch3 灰烬"下辈子再见，我总会站在赢的一边"（五百年宿敌定约）。
9. **遗物匣**：ch2 红纸包（第一件遗物）；ch16《鉴录》首批名字；ch20 帖木哥最后一班岗（站房的灯亮到天明）。
10. **组诗防泄漏**（见铁律）。

## 卷界面观察项（ch100-111 段与卷界收束时记录——核心交付物之二）

11. **arc-payoff 五维卷评 + 假兑现铁律 6 首验**：卷一钩（灰烬终约/灯之谜/小调）的 resolve 判定是否走"暂缓"第三态（跨卷窗口）；core 钩无假兑现垫场时是否按敷衍计分。
12. **中点反转落位**：卷一中点反转"预知失效：救不了城，救下了名录——金手指换了形态"应在 ~ch50-60 段落位（卷内张力曲线 45-55% 处）；落位与否记档。
13. **卷末三连**：卷末章区间应兑现 铭记章→账目清算章→渡问钩 三连结构；卷一卷末钩子按 seed（骨哨在雪夜发烫/《鉴录》半部南去/公司先遣船测绘新航道/货单"活货"栏）。
14. **卷级技能族实弹**：volume-consolidation、score-volume、ledger/pool 归档在卷界的执行与产物完整性；卷二卷区段（若生成）是否带「爽点主型」行与「金句与梗位」行。

## 新契约已知边界（不要误判为缺陷）

- 留存锚窗口固定 30 章（G4 硬编码；retentionWindow 配置指针是历史死键已拔除——评审决议）。
- 章长 ~7143 字/章是种子数学（千万字/1400 章）；微粒钩 2500-3500 字铺、牵引点 800-1200 字是审计底账——两套口径是分层不是矛盾。
- G4.vo.quote_line 是 WARN 级不拦；「爽点主型」行缺失时 payoff 拍走题材词表回退，合法。
- 假兑现垫场的验收主体在 arc-payoff（卷界）——章层面只记录 hook 账推进方式列的「假兑现」标注是否出现。
- G4.cp.missing_emotion_tone / missing_payoff_beat / missing_retention_anchor 若在**新产出**的备忘上高频触发（>3 章）→ 不是模型问题，是 dispatch 注入面缺口，框架 P1 走 TDD。

## 纵向数据采集（边跑边记：novel-xinghuo-vol1/vol1-ledger.md）

- 逐章行：章号/实测字数/cost/tokens/一次过 or retry/新闸拦截明细/emotion_tone/payoff 拍（类型｜强度）/章尾钩型/resonance 分。
- 汇总面：全链一次过率；双 structure（matrix/hooks）零出现验证；escalation 分类统计；观察项 1-14 逐项结论（误报率/遵守度/泄漏检查/卷界技能族产物）。

## 中止与续跑

- 沿用 phase3-driver-prompt 断点协议：pipeline-state.json 的 pending checkpoint 即断点；裁决序号接续项目内最大值；重启 runner 前 `pgrep -f run_pipeline` 清残留。
- **跨契约升级续跑**：若暂停期间 main 落了新的「必填字段+硬闸」批，重启前先 `uv run python tools/plan_craft_backfill.py novel-xinghuo-vol1 --apply`（默认 dry-run 先看报告）。
- 止损三条件（任一即停）：硬顶 $25；同一框架缺陷 3 次修复仍复发（质疑架构，写报告）；连续 3 章 escalate 同一根因。
- **卷一收束后即停**：不开跑卷二——GO 与否走收束报告，卷二是下一个探针/长跑的事。

## 收束（卷界完成后）

1. 终验扫描：总派发/总成本/章数/实测字数（`wc -m`，非宣称值）/双 structure 计数/escalation 分类/hook 终态对账。
2. **新契约实弹验证报告**（观察项 1-10 逐项：闸口误报率/声明质量/词表轮换遵守度/防泄漏结论）＋**卷界面验证报告**（观察项 11-14：arc-payoff 判定/中点反转落位/卷末三连/卷级技能族产物）。
3. GO/NO-GO 建议：卷二续跑 / 修复批先行 / 契约回滚项清单。
4. 写 session memory（含断点章号、pending 状态、下一 session 首任务）。

## 挂账不做（防过度施工）

- 不修种子内容层问题（除非 P0 阻塞）——组诗/节奏四修/卖点表刚过四轮定稿与双评审，实弹数据先行。
- 不动千万字工程挂账项（A2 locations/relationships 长跑化、B 归档参数化、C 再预算护栏等）。
- 不给七型钩/抑扬排程加新机器闸（检测面够用；第二次同类契约变更才上 plan_format 版本化——AGENTS.md 纪律）。
- 不动发布层（章长口径/双更切分是发布决策，非管线职责）。
- 卷二不开跑（见中止与续跑）。
