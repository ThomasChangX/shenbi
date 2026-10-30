# 卷一续跑驱动 Prompt：星火燃穹·卷一 ch25-60（regen-v3 续跑）

> 使用方式：新开 ZCode session（工作目录 = 本仓库），把本文全部内容作为首条消息发送。
> 上游协议：监控循环／裁决分级／裁决知识库／断点协议／纵向采集沿用 `docs/probe-vol1-driver-prompt.md` v2.2；
> 验收口径与判据 8 评分配方见 `docs/regen-vol1-driver-prompt.md`（其重置入口已消费——**续跑禁止再跑 regen-reset**，
> tag `pre-regen-v1` 已存在会 fail-closed，这是设计内防线）。本文件只写续跑差异面。

## 任务定位

> **2026-10-29 运行中勘误**：卷一实为 **36 章**（管线卷界 `read_volume_boundaries`=[36,86,139,…]；
> volume_map 第36章=「卷一收在『此账必有还之日』」收官行）——本文原写「ch25-60/卷一 60 章」系把
> 种子 rebudget 卷预算上限误当章界。运行终点修正为 **ch36 卷一收官**：`--through 36` + G3.4 全卷终评
> （ch1-36 窗口）；检查点改 ch30（黄金三十章锚）＋ch36 终局。誓言句「此账必有还之日」出口名额=第36章。

- **背景**：ch1-24 已收束——判据 1/2a/2b/2c/3/4/6/7 机器面全绿；判据 8 两轮评分 83.5 → **85.20 CONDITIONAL** 终判
  （2026-10-29，`reviews/rubric-score-24-r2.md`，两轮预算用尽，R1 四项硬修经独立确认）；R3/R4 清偿轮完成
  （章头规范化／声明面同步／老驼识别拍／两处接缝／六文差额落账）；facts 库已落盘
  （`truth/facts/`：props 78／counters 1（鉴录名数=4）／identity 1（那罕，aliases 含林烽））。
- **目标**：ch25-60（卷一全 60 章）生成 + 每 10 章检查点 + 终局 `just regen-accept novel-xinghuo-vol1 --through 60`
  判据全绿（判据 5 除外，见下）+ G3.4 全卷终评（ch1-60 窗口）≥90。
- **驱动模式**：主 agent 监督模式（runner 自跑，session 监控／分级裁决／TDD 修复／纵向采集）。
- **防剧透铁律**：沿用（组诗藏头/无名小调之词＝卷十二彩蛋，任何文件不得泄漏）。
- **代码面**：本续跑首次实弹使用 spec #80（四槽门+facts）与 #81（观测层）代码——运行侧验收一并完成。

## 启动序列（恢复入口——非重置）

```bash
export SHENBI_LLM_API_KEY=$(grep -oE '^SHENBI_LLM_API_KEY=.*' .env | cut -d= -f2-)   # 必须 export，source .env 不注入 uv run
pgrep -f run_pipeline   # 确认无残留 runner，有则先清

just pipeline-status novel-xinghuo-vol1   # 游标应 = ch25, phase=chapter-loop
# 读 novel-xinghuo-vol1/vol1-ledger.md 断点节（R4 清偿轮 + round 2 评分）

nohup ./run_pipeline.sh novel-xinghuo-vol1 > /tmp/vol1-regen-v3-cont.log 2>&1 & disown
```

## ch26-27 新门首触小停检（硬闸，不许跳过）

ch25-26 完成后**停 runner**。#80 四槽门（cd.prop_handoff/cd.counter 读 facts 库）与 #81 观测层
（dispatch 归档/trace 三字段/RETRY/逃逸舱 fail-fast/observe_report）首次进入实弹生成——历史上每个新门批次
首触必有摩擦（v3 ch1 六面首撞先例）。检查点动作：

1. `uv run python tools/observe_report.py novel-xinghuo-vol1`（#81 运行侧验收，产出记台账）
2. ch25/26 manifest 门行零 FAIL；cd.counter 计数推进与 facts 现值一致（前向语义：facts=本章前置值）
3. 人工读 ch25 全文做接缝复查（对照 R4 已修两处接缝的写法）

通过才放行 ch27+；首撞缺陷按分级裁决处置（P0/P1 熔断停循环，P2/P3 记账续跑）。

## 停检点与成本护栏

- **每 10 章检查点（ch30/40/50/60）**：`uv run python tools/report_longitudinal.py novel-xinghuo-vol1` +
  `just regen-accept novel-xinghuo-vol1 --through N`。累计 >$10 先分析再继续；硬顶 $25。
- **判据 5 预期保持 FAIL**（口径失配已挂账 spec 队列，见台账 2026-10-29 R3 取证）——禁止用正文口癖灌水追指标；
  声口人工面由判据 4 + G3.4 声口维覆盖。
- **多会话恢复游标**：断点协议沿用 probe-vol1；恢复时 `just pipeline-status` + 读 vol1-ledger.md 断点节。

## ch25+ 内容 feed-forward（round 2 评分遗留弱项 → 卷纲承诺面，规划层落实）

1. **情绪拍**：卷内至少一次冲顶级兑现 + 至少一章危机上门型热开篇/热章尾钩（ch21-24 尾窗低温带必须打破；情绪拍 80 是 R2 次弱维）
2. **主对手正面交锋**：墨管事/灰烬线须在卷一内开正面窗（completeness 78 的主扣分项：24 章无正面交锋、无爆点章）
3. **断供钩显式推进或挂起声明**：七三一编号卡（ch1 种）、老驼纸条「待查栏」三笔（仅回收一笔）——两者在卷内给推进或明写挂起
4. **接缝纪律**：每章首段承担跨章时间/空间过渡（R4 示范：ch11 粮队交割桥、ch18 四十天压缩+借调令挂起）；跨章角色状态（辎重队老驼线/灯铺线）显式交接
5. **canon 已固化勿动**（violations 会撞 facts 门/评员复查）：
   - 鉴录计数链当前 4（ch3:1→ch7:2→ch8:3→ch9:4；ch16 起三位数搬运另有表述）
   - 双哨：老驼所授·主线（贴身）／帖木哥所持·旧线（ch20 交出「揣了二十年」）；灰烬「另一支」为第三哨悬念不展开
   - 称谓：叙事名那罕（正文零林烽）；余额链 189−6=183−40=143；借调令显式挂起（开春再启）
   - 卷名《星台雪夜饼初分》；章头两行式 `# 第N章`＋`# 章题`（release_split 以第二 H1 提取章题）

## 验收与终评（ch60 收束）

- `just regen-accept novel-xinghuo-vol1 --through 60`：判据 1-4/6/7 全绿（判据 5 按挂账口径豁免记录）
- 判据 8 全卷终评：独立子 agent（general-purpose 聚合评分模式，评分卡 `docs/regen-vol1-scoring-rubric.md`，
  窗口 ch1-60）；≥90=PASS；75-89=CONDITIONAL 列残留必修面。dispatch 参照 regen-vol1-driver-prompt.md 判据 8 节配方改窗口
- 收尾：`_quarantine/pre-regen-v1` 物理清理或归档移动 + 复盘模板（挂 vol1-ledger 末节）+ 旧项目目录处置 +
  纵向采集表 ch19-24/25-60 补行 + 声明面积欠收尾批（scene_hook×11/ch11 自检块，见挂账）

## 挂账不做（防过度施工，沿用+新增）

- 不因运行中内容批评改口径文件（volume_map/thread_map/角色卡）——内容问题走正文层修复或裁决知识库
- 不扩 regen-accept 判据集——新判据想法记 vol1-ledger 挂账节
- 不动 `_quarantine/`（隔离区只读）
- 新增：不改 facts 库种子值（#80 面，发现矛盾走台账）；声明面积欠不在运行中修（收尾批处置）；
  manifest 门行对已生成章不回放重跑（R4 方法论教训——前向门回放必假阳性）
