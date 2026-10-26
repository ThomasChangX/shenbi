# 重生成运行驱动 Prompt：星火燃穹·卷一 v3（regen substrate 自包含版）

> ⚠️ **本运行在 SDD 外，由用户启动**（spec #79 核心原则 8 裁定：重生成运行本体是独立执行项目，
> 非任何 SDD spec 的完成条件）。本文件是 spec #79 交付的执行协议；启动它的 session 拥有全权。
>
> 使用方式：新开 ZCode session（工作目录 = 本仓库），把本文全部内容作为首条消息发送。
> 底层协议（监控循环/裁决分级/裁决知识库/断点协议/纵向采集）沿用
> `docs/probe-vol1-driver-prompt.md` v2.1——本文件只写**差异面**：重置入口、验收口径、判据 8 配方。

## 任务定位

- **背景**：卷一 v2 运行（ch1-10）经用户代感审查判 P0/P1 五断裂族（POV/主角误名撞女主/时间线倒错/红纸包链断/配角性别漂移）+ 结构层代入感缺失；跨章不变量门（#75）、口径重锚（#74）、声口/文体/回触层（#76-#78）已全部落 main。决策：**旧九章全部丢弃，从 ch1 重新生成**。
- **目标**：卷一前 24 章重生成 + `just regen-accept --through 24` 八判据全绿 + 判据 8 G3.4 评分 ≥90。
- **驱动模式**：与 probe-vol1 相同——主 agent 监督模式（runner 自跑，session 监控/分级裁决/TDD 修复/纵向采集）。
- **防剧透铁律**：沿用 probe-vol1（组诗藏头/无名小调之词＝卷十二彩蛋，正文与 truth/plan/context 任何文件不得泄漏）。

## 启动序列（重置入口——与 probe-vol1 的唯一差异在这里）

```bash
export SHENBI_LLM_API_KEY=$(grep -oE '^SHENBI_LLM_API_KEY=.*' .env | cut -d= -f2-)   # 必须 export，source .env 不注入 uv run
pgrep -f run_pipeline   # 确认无残留 runner，有则先清

# 1) 重置（真落盘——本命令是运行项目入口动作；旧章进隔离区，genesis 保留不重跑）
just regen-reset novel-xinghuo-vol1 pre-regen-v1
# 预检（不落盘的对照）：just regen-reset novel-xinghuo-vol1 pre-regen-v1 --dry-run

# 2) 空基线自检：聚合器应报 data error（exit 2）——证明无可评残留
just regen-accept novel-xinghuo-vol1 --through 1 ; echo "exit=$?"   # 期望 exit=2

# 3) 起步（沿用 probe-vol1 启动序列的 runner 段）
nohup ./run_pipeline.sh novel-xinghuo-vol1 > /tmp/vol1-regen-v3.log 2>&1 & disown
```

重置后状态口径（`_quarantine/pre-regen-v1/RESET-MANIFEST.txt` 为取证面）：chapters/plans/adjudications/audits/gate-markers/cost + manifest/trace 已隔离；pipeline-state 除 genesis/config 外全零态（phase=chapter-loop）；章层 truth 表壳化；embeddings/index/context 已清；世界/角色/卷层 truth（#74 修复面）逐字节保留。

## 停检点与成本护栏

- **首个场景簇人工停检点（ch1-2）**：ch2 完成后**停 runner**，跑 `just regen-accept novel-xinghuo-vol1 --through 2`，人工读两章全文做代感复查（对照 v2 五断裂族逐项确认不复发），通过才放行 ch3+。此停检点是硬闸，不许跳过。
- **每 10 章成本检查点**：`uv run python tools/report_longitudinal.py novel-xinghuo-vol1`（成本/纵向面）+ `just regen-accept novel-xinghuo-vol1 --through N`。累计 >$10 先分析再继续；硬顶 $25（沿用 probe-vol1）。
- **多会话恢复游标**：断点协议沿用 probe-vol1；恢复时先 `just pipeline-status novel-xinghuo-vol1` + 读 vol1-ledger.md 断点节，regen 运行**禁止**再跑 regen-reset（tag 已存在会 fail-closed，这是设计内防线）。

## 验收口径（判据 1-8 映射）

`just regen-accept <dir> --through N`（三态：0 全绿 / 1 有 FAIL / 2 数据面缺）：

| # | 判据 | 机器面 | 人工/RUN-PROJECT-ONLY |
|---|------|--------|----------------------|
| 1 | 跨章不变量 | manifest `pipeline-scene-split.G4.xc` gate 键 latest-wins 全 PASS | 维度 9 抽查 |
| 2a | 章字数带 | floor=manifest `G4.word_count`/`G4.ln.word_count`；ceiling=离线复算 ≤ `chapter_word.max`（4000） | — |
| 2b | 起草门 | 其余 `G4.cd.*` 检查 id 零 FAIL | — |
| 2c | 情绪高点 | memo `emotion_tone` 冷连续 ≤3（悲/惧/平 且金句位非燃）；金句位=燃短路 | 维度 8 |
| 3 | 卷纲节点 | `just volume-nodes novel-xinghuo-vol1 1`（含灰烬◆首现≤12——#79 已补槽位标记） | — |
| 4 | 声口/梗位 | lint_voice_meme chapter+volume 双模式 | 维度 7 |
| 5 | 真章盲认 | 真章对白卡面标记 argmax 五主角各 ≥4/5 | 维度 7 |
| 6 | 发布切分 | release_split 临时目录跑通 + SCENE 标记卫生 | — |
| 7 | just check | 手动行：运行 `just check` 确认 EXIT=0 后记档 | — |
| 8 | G3.4 评分 | **RUN-PROJECT-ONLY**（下节配方） | 评分卡全文 |

机器判据全绿 + 判据 8 ≥90 = 重生成验收通过；之后旧章物理清理（`rm -rf _quarantine/pre-regen-v1` 或归档移动）与复盘归档由运行项目收尾。

## 判据 8 评分执行配方（G3.4 独立评分）

- 评分卡：`docs/regen-vol1-scoring-rubric.md`（诡秘轴×2 + 捞尸人轴×2 + 声口/情绪/不变量三人工面 + 通用 15%）。
- dispatch（铁律：**评分必须独立子 agent，runner/监控 session 自评无效**）：

```bash
# G3.4：独立评分 agent（shenbi-score 口径，--test-type generative）
just dispatch shenbi-review-highpoint generative novel-xinghuo-vol1 \
  "按 docs/regen-vol1-scoring-rubric.md 全维度评分 chapters/chapter-1.md..chapter-24.md；每个维度给 0-100 分+章:行证据；维度 3/5 任一 <60 直接 FAIL"
```

- 评分结果记 vol1-ledger.md 判据 8 节（分数+逐维度证据摘要）；CONDITIONAL（75-89）列必修维度修完再评一轮，最多两轮。

## 复盘模板（收束时填，挂 vol1-ledger.md 末节）

```markdown
## 重生成 v3 复盘（日期）
- 判据达成：1-8 逐项（机器行贴聚合器输出；判据 8 贴分数）
- v2 五断裂族复发面：POV/误名/时间线/物象链/性别——逐项「零复发 | N 处（章号+已修）」
- 一次过率/成本/escalation 数 vs probe-vol1 基线（$0.10-0.14/章）
- 框架新缺陷（P0-P2 分级；修复提交号）
- 基板工具体验反馈（regen-reset/regen-accept 改进项 → 下一个 spec 候选）
```

## 挂账不做（防过度施工）

- 不因运行中内容批评改口径文件（volume_map/thread_map/角色卡）——内容问题走正文层修复或裁决知识库，口径文件是 #74/#75 定稿面。
- 不在运行中扩 regen-accept 判据集——新判据想法记 vol1-ledger.md 挂账节，收束后走 spec 队列。
- 不动 `_quarantine/`（隔离区只读；物理清理事属验收后收尾）。
