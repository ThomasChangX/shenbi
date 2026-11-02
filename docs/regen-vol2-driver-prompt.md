# 卷二开卷驱动 Prompt：星火燃穹·卷二 ch37-44 首四束（渡 3 债务征服开卷）

> 使用方式：新开 ZCode session（工作目录 = 本仓库），把本文全部内容作为首条消息发送。
> 上游协议：监控循环／裁决分级／裁决知识库／断点协议／纵向采集沿用 `docs/probe-vol1-driver-prompt.md` v2.2；验收口径与判据 8 评分配方见 `docs/regen-vol1-driver-prompt.md`；判据 5 挂账口径与检查点四行必答沿用 `docs/regen-vol1-continue-prompt.md`。本文件只写卷二开卷差异面。
> 前置（spec #84）：T0 修复轮已完成（G4 真门全 PASS+regen-accept --through 36+章头断言三件）；章头注入器已参数化 `chapter_header_style: two_line_zh`——管线写路径自动按两行式中文章头规范化。

## 任务定位

卷二《渡 3 债务征服》KR1：斡脱钱庄→驿站站户→渡3；**卷界=第 37-86 章**（volume_map 第二卷 span）。卷一是「立足卷」，低温合法；卷二是冲突卷——**开卷必须把卷一欠的追读债还给读者**。ch37-44 首四束（每束 2 章）执行本协议；ch45+ 转常规驱动（每 10 章检查点制）。

## 首四束三件套逐束全量检查（非抽样——spec #84 T1-1）

每束收束时对两章**逐章全量**核三件套，任一不中=当章 revision（blocking）：

1. **热开篇**：危机/对手动作开场（灰烬线或斡脱债主任一上门），非工序低温；
2. **主角自选目标出口**：那罕亲口说出要什么（南下/春天之约/还账的具体第一步）+ 倒计时锚——承接 ch36「船开在清明前」（按引文重锚，不按行号）；
3. **章尾热钩**（危机型）——声明温度 vs 正文温度**背离→blocking**：抽读正文尾段实判，不信任声明面单方面口径。

门面真相（防误依赖）：hot_hook_floor 自 ch37 起累计窗口数据，**ch46 前不满 window=10 不执法**（bootstrap skip），且 genre-config 该键 shadow:true 期仅 WARN——首四束三件套**唯一执法=本节驱动侧协议**。

## 断供钩清偿表（卷二前 12 章内每钩付息或显式挂起；每束收束对表）

| 钩 | 时限 | 处置 |
|---|---|---|
| 七三一编号卡（35 章债，ch1:103 种） | 前 6 章 | 一次实质推进（哪怕一句：档案房换卡/卡被取走） |
| 老驼纸条（灯-横线-小圈，ch2:31） | 与骨哨路线图并轨 | 同为老驼遗物，天然同匣解读窗口付息 |
| 帖木哥归否 | 前 12 章 | 一句交代（班期表空格的回收） |
| 「我见过另一支」第三哨（ch18:190） | 前十二章或后段 | 挂起声明**必带清偿锚**（#82 T2 口径：挂而不排即红） |
| 萤饼债/春天之约 | 卷二 KR 本体 | 不挂起——主角自选目标的物质锚 |
| 笔迹链三处同钩（ch13:309-311/ch14:333/ch26:169-173「末一钩往上挑」） | 卷二内 | 挂起声明带清偿锚（灰烬=墨管事是否写过借调令/附籍册——卷二付息素材，spec #84 r5 升格） |

## 金手指进度条首片（T1-3）

卷二前 10 章内一次「记起来」的实质碎片（新规则/新代价/一片前世画面——**非机制解释**），兑现 #82 T6 供给下限首拍；呼应 ch2「还没记起来」悬念纪律。

## 完颜嫂罚单（T0-11 选转卷二）

ch37-38 内即付（认罚/摊封结局实写），不许继续悬空。

## 开卷束规划审查（T1-5）

- 规划审查按 #82/#83 新门全跑；首束=三门首实弹（cold_streak_cap/hook_max_age/quote_anchor 族）；
- **shadow 促转检查点**：`uv run python tools/lint_shadow_promotion.py novel-xinghuo-vol1 --ledger novel-xinghuo-vol1/vol1-ledger.md`——**连续 2 束 WARN 零误伤才转正**（#82 协议，非首束即转）；转正动作=genre-config 该键 `shadow: false`＋台账记录；干净跑无 WARN 即无物可转（零误伤记录在案即可）；
- ch37 staged 计划（`staging/plans/chapter-37-plan.md`）若仍为冷三连旧版（emotion_tone:平/金句位:静/章尾张力拍:微）＝**先驳回重规划再派发**（spec #84 Task 9；余额行=一百三十三文）。

## 每束收尾固定动作

1. **章头形态断言**（仓库根执行；只核已生成章、排 -pre-rev 备份）：
   ```bash
   for f in novel-xinghuo-vol1/chapters/chapter-*.md; do
     case "$f" in *pre-rev*) continue;; esac
     n=$(basename "$f" .md); n=${n#chapter-}
     [ "$n" -lt 37 ] && continue
     echo "$f $(grep -cE '^# 第[0-9]+章$' "$f") $(grep -cE '^# Chapter [0-9]+:' "$f")"
   done
   ```
   → 每行 `1 0`（唯一性：恰一行章号行；重复插入不过闸）；
2. 三件套逐章全量核（上节）；
3. 断供钩清偿表对表推进；
4. **shadow 促转留痕**：`uv run python tools/lint_shadow_promotion.py novel-xinghuo-vol1 --ledger novel-xinghuo-vol1/vol1-ledger.md` 每束跑一次（「连续 2 束 WARN 零误伤」判定依赖逐束留痕，台账逐束记一行）；
5. 修后章 clobber 防线：T0 修过的章（ch1-36）若再修订，diff 复核 `-pre-rev` 备份（备份是恢复非阻断——plan Task 1 节 11 口径）；
6. 检查点四行必答（温度谱/胜利账/钩龄表/挂起清单——#82 T5 口径，数据取自快照+勘误面；**频率注**：每束记简版一行，每 10 章检查点出全量四行+抽读 ≥2 章沿用 vol1 协议）。

## 停检点与成本护栏（沿用卷一口径）

- 每 10 章检查点：`uv run python tools/report_longitudinal.py novel-xinghuo-vol1` + `just regen-accept novel-xinghuo-vol1 --through N`；累计 >$10 先分析再继续；硬顶 $25；
- 判据 5 预期保持 FAIL（口径失配已挂账 spec 队列，见 `docs/regen-vol1-continue-prompt.md:60` 口径）——**禁止用正文口癖灌水追指标**。

## 挂账不做（防过度施工）

- 不重排卷三+兑现曲线（#82 同款红线）；
- 不补卷一 follower 指标面历史（#83 T5 只保卷二起）；
- 引号体例/双结尾去重无 checker（spec #84 §4 挂账）——发现问题记台账，不现场建门；
- 首四束不引入 T1 协议外的新监控面。
