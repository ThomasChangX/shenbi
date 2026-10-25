# Spec #78 · 情感回触与爽点重量门（recall-payoff-weight）

> **Date:** 2026-10-25（rev3 2026-10-26 阶段 3 两轮审查清偿） | **Status:** Active | **Severity:** 🟠 P1 | **方法:** 频次门 + 重量分级 + audit_drift 改向权 | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** #73、#74、#75（prop 链+name_registry）、#76（plan_format 纪律）、#77（WARN 计数器先例） | **范围:** 死者 registry / 回触频次门 / 钩子分级轮换门 / 爽点重量评估 / audit_drift 改向权

## 0. 数据源与版本裁定（阶段 3 审查落定）

- **死者 registry**（C1）：truth/recall_registry.md 新表（producer: pipeline seeding + settling 滚动）——行 `| 死者名 | 化名映射 | 死亡章 | emotional_weight(高/中) | 末次回触章 |`；**化名展开**（萤→deng 卡 active 但卷一死亡章 3 已死——seed 时从卡 aliases_note+death 章展开）；minor 卡死者（老塾师）经 current_state/文本启发式入表（缺字段=文本含 已故/已消散/拒用旓名而死 类即入）；emotional_weight 由卡 arc_summary 与主角关系行含「情感」类词定高，缺省中
- **WARN 生产者**（C2）：#78 自带确定性生产者——`tools/lint_recall_weight.py`（离线 CLI+审计边界钩子同 #77 形制）：emotion-band 族行 `- [emotion-band] chN 值/下限`（memo emotion_tone 声明域 vs genre-config emotion_band 下限的窗口累计——**声明口径非正文检测**）；recall 族行 `- [recall] chN 死者名 超窗n章`（M3：两族 kind 均**结构性排除**于 count_drift_alerts，与 style-warn 同款）；连续语义=章号邻接窗口（#77 邻接判定先例）
- **plan_format v3**（C3）：D1 回触拍注入/D2 张力拍分级/D3 payoff 轴量 三新备忘义务全部归 **v3**（v2 语义冻结——#76 已投产不破坏；v1/v2 旧路径持续可跑）；G4.cp 令牌合法集扩 {v1,v2,v3}；**在途声明**：novel-xinghuo-vol1 plans 全 v1，#79 删旧章前 pipeline 冻结重生成——无在途工件受影响（AGENTS 契约升级纪律同批携带）
- **escalation 节点取用**（M4）：改向注入物=volume_map 节点表中**下一个未消费的「转折/收官」节点**提前取用（节点表无 escalation 型——规则声明不改表）；5 章熔断=CheckpointType.ESCALATION set_checkpoint 先例复用
- **改向通道分流**（I3/I4）：kind 分流互斥——emotion-band 族累计 3 → escalation 节点注入（planning dispatch 强制注入块，dispatch_helper 先例）且**抑制**该窗口 shenbi-genre-config 改配置触发（改向优先；注：emotion-band 行本就结构性不可见 check_genre_config_drift——抑制语义仅在跨族共发窗口）；style 族（#77）注文体修复指令（非情节节点）；recall 族 WARN 注回触拍；三族并行不串道
- **tone→band 映射**（R1）：暖=喜、燃=怒、冷=悲/惧/平；冷蓄压累计=连续冷章数（邻接）；连续 ≥3 冷章触发注入
- **v3 ⊇ v2**（R2）：v3 义务包含 v2 全部（声口要求行/金句位三点同步对 v3 仍强制）——G4.cp/G4.cd 版本判定 v3 走 v2 全套检查+新增三项
- **契约声明面**（R3）：truth/recall_registry.md 入 truth-files.yaml（producer: pipeline）+ state-settling SKILL writes/updates 声明（#75 三表同款连锁）
- **生产者落点**（R4）：逻辑入 `src/shenbi/text/recall_weight.py`（运行时钩子消费）；`tools/lint_recall_weight.py` 为离线 CLI 壳（voice_lexicon→lint_voice_meme 形制）
- **emotional_weight 消费**（R5）：高权重→窗口减半（`ceil(recall_window/2)`）；**半窗下限=该角色在 volume_map 已锚回触链的最大 authored 间隙**（override 至高时 seeding 同步校验取 max(半窗, authored 间隙)——防与 #74 大纲对抗）；seeding 支持 decisions sidecar manual_override 修正确认（P2.5 先例）
- **死亡章来源**：化名行的死亡章从 volume_map 节点表取证（卡面无 death 章时——「萤死在怀里」节点）；**卷末降级**：无后续 转折/收官 节点时 escalation 取用降级为 WARN（不跨卷取用）

> 源自总设计 §3。问题依据：萤 ch2 死后正文 7 章零提及、塾师 2 章清零——被「不抒情不回忆」禁忌条款制度性切除；九章章尾全是同频微钩（未答之问/未说破之瞒变体）；payoff 槽位全达标但载荷均半合米级（槽位思维查有无不评估重量）；audit_drift 连续 5 章记录「冷蓄压」但修复动作被限定为补丁（加一处温度），无改向权。

## 1. 施工面

1. **死者回触频次门**：recall_registry（§0）死者 ≤`market_params.recall_window`（**新可选键 ∈[3,20] 缺省 8**——M2）章必有一次低成本回触。**检测词源三库**（I5）：物象=prop_registry 实体名（含变奏保守漏检）；小调=各卡 voice_profile catchphrases；台词=name_registry 登记名+化名在对白域命中（find_quote_spans）。超窗 = WARN 行 + planning dispatch 强制注入回触拍（v3 备忘义务）。**禁忌条款修订**（M1）：编辑面=outline/rhythm_principles.md（「不抒情不回忆」措辞行）+ planning SKILL 模板 §8 生成指令——改「不直给抒情；回触须以物象/小调/台词低成本形态」；验收改文本字符串检查（正文回触挪 #79 判据④）
2. **钩子分级轮换门**：三级由 **memo 声明**（I1）——v3 章尾张力拍行 `章尾张力拍: [微|章|大]＋形态`（声明-特征弱交叉：微钩=问句/瞒变体特征，G4.cd 只对 v3 校验声明在场+分级合法，不做散文检测）；连续微钩计数=**读前章 memo 声明**纯读路径（N1 幂等）；上限=`hook_grading.max_consecutive_micro`（#73 键既有），超限 = G4.cd FAIL（v3 域）
3. **爽点重量评估**：v3 payoff 行 `payoff 拍: 类型｜轴(债/名声/名字数/进度)｜量`；智识小胜计兑现**唯一口径=四轴登记在场**（I6：review-highpoint 小/中/大强度词表降为期待管理标签，优先序声明）；半合米级（纯口头/无轴登记）不计兑现；v1 只查声明结构可离线单测（I7：跨核 settling 增量显式留 #79）；`payoff_density` 频次窗（I2）**并入本交付**——window 内无任何轴登记 payoff = WARN
4. **audit_drift 改向权**：§0 生产者 emotion-band 族行累计；连续 3 章（邻接）→ planning 强制注入 escalation 节点（§0 取用规则）+ 抑制同窗 genre-config 改配置触发；连续 5 章 → set_checkpoint ESCALATION 熔断停等人工。#77 style 族接同一通道但注文体修复指令（§0 分流）

## 2. 验收

- 回触门：旧九章 fixture（tests/fixtures/cross-chapter-regression——N2）复跑萤超窗 WARN（旧粒度章序口径——N4）；禁忌修订=rhythm_principles/SKILL 文本字符串检查（M1——正文回触归 #79 判据④）
- 钩子分级：inline 构造 v3 序列判「连续微钩超限 FAIL」（旧章无声明——I1 口径）
- 重量评估单测：半合米级不计兑现、四轴登记才计、payoff_density 窗 WARN
- 改向单测：3 章冷蓄压 → 注入块含 escalation 节点+genre-config 触发抑制；5 章 → ESCALATION checkpoint；recall/style 族注入物分流断言
