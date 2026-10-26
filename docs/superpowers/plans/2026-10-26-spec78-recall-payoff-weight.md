# Spec #78 实施计划 — 回触与爽点重量门

> Spec: `docs/superpowers/specs/2026-10-25-spec78-recall-payoff-weight.md`（rev3 GO）
> 全部 task infra → 协调者亲做；F947：全离线，零 dispatch

## Task 1: recall_registry seeding + recall_weight 核心模块（tdd_red_green）

- **Create** `src/shenbi/text/recall_weight.py`：
  - `load_recall_registry(path) -> list[RecallEntry]`（行解析）
  - `seed_recall_registry(project_dir) -> Path`：cards+volume_map → truth/recall_registry.md（化名展开：deng 卡 aliases_note 萤→行「萤」死亡章从节点表 cell `volume_map.md:53` 「萤死在怀里」正则取证（萤死|而死|战死 族）；minor 文本启发式 已故/已消散；weight 启发式+manual_override；高权重半窗 max(半窗, authored 间隙)）；CLI `python -m shenbi.text.recall_weight seed <dir>`
  - manual_override sidecar = `truth/recall-registry-seed-decisions.json`（shenbi-decisions-v1；adjustments[].manual_override+rationale≤100 字——P2.5；**不入 lint_decisions_sources 三源对账**：seeding 是 CLI 工具非 skill dispatch，G2/G4 文件列表外——deviations 记录该豁免）
  - detect_recall 物象词库**优雅降级**：prop_registry/name_registry 缺席时跳过该词库（仅 catchphrases+inline 注入词）——truth/ 三表未落地项目不崩
  - `detect_recall(body, entry) -> bool`（三词库：prop_registry 实体/各卡 catchphrases/name_registry+化名 对白域）
  - `recall_warnings(project_dir, chapter) -> list[str]`（`- [recall] chN 名 超窗n章` 行；窗口=recall_window 或半窗）
  - `emotion_band_warnings(project_dir, chapter) -> list[str]`（memo emotion_tone 冷章行 + 连续计数）
  - `escalation_action(project_dir, chapter) -> str | None`（3 连冷→节点取用注入文本；5 连→"CHECKPOINT"；卷末降级 WARN）
- **Modify** `src/shenbi/contracts/skills/genre_config.py`：`market_params.recall_window ∈[3,20]`（缺省 8）
- **Modify** `docs/framework/truth-files.yaml` + settling SKILL writes：recall_registry 条目（#75 三表连锁）
- **Test**：seeding（deng 化名 L53 取证/塾师启发式/weight override/半窗下限）、recall 检测三词库+降级、窗口 WARN（超窗=间隔>窗口）、冷章行+连续计数、escalation 取用（**本卷 scope：当前卷节点表第一个 章>当前章 的 转折/收官 行**）/卷末降级
- WARN 发射面声明（I4）：`[recall]`/`[emotion-band]` 行=lint/审计钩子面（audit_drift）；payoff 密度窗 WARN=G4.cd 检查面（checks 列表）；三新 kind 均结构性排除于 count_drift_alerts（白名单 regex 构造性豁免——无代码）

## Task 2: plan_format v3 机制 + G4 扩展（tdd_red_green + characterization）

- **Modify** `src/shenbi/gates/g4/chapter_planning.py`：令牌集 {v1,v2,v3}；v3 ⊇ v2 全套 + 张力拍分级行 `[微|章|大]` 合法性 + payoff 行 `类型｜轴｜量` 轴 ∈ {债,名声,名字数,进度}
- **Modify** `src/shenbi/gates/g4/chapter_drafting.py`：v3 域——连续微钩（读前章 memo 声明纯读路径）> max_consecutive_micro = FAIL；payoff_density 窗无轴登记 payoff = WARN
- **Modify** `skills/shenbi-chapter-planning/SKILL.md`：v3 模板行（张力拍分级/payoff 轴量/回触拍）+ plan_format 值域注
- **Modify** `novel-xinghuo-vol1/outline/rhythm_principles.md` **L110**（钩子类型表「情感」行的「不许抒情超过一段」域）+ **L161**（战争卷禁止抒情范围句）：追加低成本回触许可子句（「不直给抒情；回触须以物象/小调/台词低成本形态」）；`deng.md:104` 她死后当章禁止抒情段补同款子句——**「不抒情不回忆」逐字串只存在于生成备忘（ch4:10 类）与 spec 文档**，备忘层归 #79 重生成，本批不编辑备忘；T4 文本检查=grep L110/L161 新子句在场
- **Modify** `skills/shenbi-review-highpoint/SKILL.md:93`：强度词表降级声明（四轴登记为兑现唯一口径；类型/强度=期待管理标签——spec I6 编辑面）
- **Test**：令牌真值表 v3 五态/v2 冻结回归/微钩连续 FAIL（inline v3 序列）/轴合法性/密度窗 WARN

## Task 3: 改向通道接线 + 审计钩子（characterization）

- **Modify** `src/shenbi/pipeline/dispatch_helper.py`：planning 强制注入块（escalation 节点文本/回触拍/文体修复指令三族分流；:1402 骨架块先例）
- **Modify** `src/shenbi/pipeline/cli.py:440-477` check_triggers：emotion 族连续注入生效窗口内**门控 genre_config_update_on_drift 触发**（跨族共发抑制的正确落点——dispatch_helper 无触发器权限）；抑制=读 audit_drift 窗口推导，无新状态
- **Modify** `src/shenbi/pipeline/chapter_loop.py`：审计边界钩子调 recall_weight（行落 audit_drift）；5 连冷 → set_checkpoint ESCALATION
- **Create** `tools/lint_recall_weight.py` CLI 壳
- **Test**：注入块内容断言（三族分流）/checkpoint 触发/抑制语义（cli.py 门控单测）/audit_drift 行 schema 结构性排除
- **契约升级声明随 commit**（N3）：plans 全 v1；#79 删旧章前 pipeline 冻结重生成——无在途工件受影响（AGENTS 纪律）

## Task 4: 验收全量

- **萤超窗 WARN = inline 构造 registry 驱动**（G0.9）：tmp 项目带 inline recall_registry（萤/死亡章 2/末触 ch2）+ ch2-10 fixture 章拷贝 + META 剥离口径 + 三词库 inline 注入——超窗边界语义=间隔 **> 窗口** 才 WARN；真实项目 seeding 为 T1 单测面（fixture truth/ 无 cards/volume_map——seeding 不可跑，按设计）
- inline v3：微钩连续 FAIL；半合米 payoff 不计兑现+密度窗 WARN
- 改向：3 冷注入/5 冷熔断/卷末降级 WARN/recall+style 族注入物分流
- 禁忌条款：rhythm_principles 文本字符串检查
- `just check` EXIT=0

## 验收覆盖表

| spec §2 | task | 验证 |
|---|---|---|
| 萤超窗 WARN+禁忌文本检查 | T4 | inline registry 驱动 lint 实跑 + grep L110/L161 新子句 |
| 微钩连续 FAIL（inline v3） | T2+T4 | pytest |
| 重量单测（半合米/四轴/密度窗） | T2+T4 | pytest |
| 改向单测（3注入/5熔断/降级/分流） | T3+T4 | pytest |
