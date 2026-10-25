# Spec #77 · 文体指纹 WARN 闸（style-fingerprint-warn）

> **Date:** 2026-10-25（rev2 2026-10-26 阶段 3 审查清偿） | **Status:** Active | **Severity:** 🟡 P2 | **方法:** 四项指纹确定性检测，WARN 级进 audit_drift（不阻断；连续态为 #78 改向权输入） | **系列:** 市场适配层（novel-market-overhaul） | **依赖:** #76（voice_lexicon 单源+校准条款）、#71（strip/切分机制） | **范围:** style_fingerprint 模块+CLI / 四指标阈值定档 / audit_drift 行 schema / chapter_loop 审计边界钩子

> 源自总设计 §3。问题依据（旧九章定量）：问号密度 ch9 每 83 字一问（ch6 每 99 字）——问答体审讯式推进，且问号密度与事件密度负相关（事件章 17、情感章 4）；比喻 1.95 处/千字且喻体全出自纸/账/册/布/绳同一意象域；9 章中 7 章以清点/数数开场。词表 lint 管词面不管声口，三项指纹全部漏检。

## 0. 机制裁定（阶段 3 审查落定）

- **写入者**：新确定性模块 `src/shenbi/text/style_fingerprint.py`（compute_drift CLI 先例）+ `python -m shenbi.text.style_fingerprint <dir> --chapter N`——计算+打印 WARN 行；**钩子 = chapter_loop 单章审计边界**（收束后、下章 context 组装前调用，行落 truth/audit_drift）；compute_all_stats 不改（其唯一调用面是 style-learning 预注入，非事后步）
- **行 schema（#78 契约）**：`- [style-warn:<指纹名>] ch<N> <detail>`——**带章标**；**排除于 count_drift_alerts**（不参与既有 drift-guidance 升级——该通道语义不动）；#78 连续计数器 = 审计时对近 N 章文件的无状态窗口重算（helper_injection 窗口先例，N=3），不依赖行内状态
- **阈值归置（#76 同款模式）**：genre-config 可选块 `styleFingerprint`（问号/千字上限、喻体占比上限、喻体最小样本、开头同族连续数、对白域最小字数）+ 模块常量缺省（validator 不代入，消费端回退——无破坏性）
- **词表归置**：喻体域六类词表（纸账册/粮食物/器物/自然/身体）入 `src/shenbi/text/voice_lexicon.py`（SIMILE_DOMAINS——与 ACCOUNTING_VERBS 同源同纪律，版本化注释）；**「其他」>70% 降级 INFO「词表需扩」不 WARN**；开头动词族（清点/数数/拆包/量取…）同址常量 OPENING_VERB_FAMILIES（书 tic 词表，genre-config seed 可扩）
- **口径**：喻体提取 = SIMILE_MARKERS 单源（gates/shared 既有）→ 至 一样/般/似的 止的名词窗（非比喻「好像/像是」用例钉测试）；字面记账动词（ACCOUNTING_VERBS）不入喻体口径（#76 校准条款）；对白域 = find_quote_spans 既有（密度计免归属）；问号含半角 ?；开头 = strip_narrative_body 后**首条非对白句**

## 1. 四项指纹指标（阈值均 styleFingerprint 可覆写）

1. **问号密度**：对白域每千字问号数上限（缺省 12）；**对白域 ≥300 字才计**（小样本防噪）；连续两章超限 = WARN「问答体退行」
2. **喻体域集中度**：近 3 章窗口，喻体**样本 ≥5** 且单域占比 >70% = WARN「比喻同域」（样本下限取代「超带」——与密度带解耦）；「其他」>70% = INFO
3. **开头同构**：近 3 章首条非对白句的动作动词族归类，**同族连续 ≥3 章** = WARN「开头模板」
4. **数数开头频次**：指标 3 分类器的窗口聚合派生统计——卷内计数动作开篇占比上限（缺省 50%，**最小 6 章窗才计**）；与指标 3 共享分类器输出，非独立词表

## 2. 施工面

- `style_fingerprint.py` 四指标（strip_narrative_body 口径剥 META）+ CLI；voice_lexicon 增 SIMILE_DOMAINS/OPENING_VERB_FAMILIES
- genre_config `styleFingerprint` 可选块三态校验（越域 FAIL）
- chapter_loop 审计边界接线（行写入 audit_drift；纯计算幂等）
- 连续态留痕 = 窗口重算即时值（WARN 行 detail 携带 `连续k章`），#78 落地时消费

## 3. 验收

- 旧九章复跑：问号密度（ch9 连续态）/喻体域（同域 >70%+样本足）/开头同构（≥3 连续）三项 WARN 真阳性；数数开头占比 7/9 > 50% 派生统计报值
- **对照组按指标界定**：问号密度在事件高密度章（如 ch2/ch4 类）不误报（喻体/同构 tics 为语料整体真阳性，无脱罪章——不设对照）
- WARN 只进 audit_drift（[style-warn:*] 行）不进 G 硬闸、不入 count_drift_alerts；`just check` 全绿
