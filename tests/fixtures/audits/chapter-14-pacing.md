# 节奏审计报告

**章节**: 第14章
**本章类型**: investigation（衙门报到、校册）
**判定**: 通过
**生成时间**: 2026-10-27T13:06:32Z

### 近5章类型序列

| 章节 | 类型 | 蓄压/爆发状态 |
|------|------|-------------|
| 第11章 | investigation（核马料账） | 蓄压 |
| 第12章 | constellation（灶间粥、情感副线） | 缓冲／蓄压 |
| 第13章 | investigation（借调令核验） | 蓄压 |
| 第14章 | investigation（衙门报到、校册） | 蓄压 |

### 规则检查

- **maxConsecutiveQuest**：genre-config.json 未设 `maxConsecutiveQuest`；按 `chapterTypes.investigation.maxConsecutive=2`、`warningThreshold=3` 检查：第13、14章为连续 2 章 investigation，**达到 maxConsecutive=2 上限，未达 warningThreshold=3**。**临界，需注意**。
- **maxGapFIRE**：本卷前14章仍以蓄压为主，尚无明确 FIRE 章。按 `pacing.maxChaptersPerCycle=15`，第14章已逼近 15 章循环上限。**接近周期上限，建议下一章安排释放**。
- **序列多样性**：近5章（11、12、13、14）含 investigation／constellation 两类，investigation 占 3/4=75% > 50%。**触发单一类型 > 50% 警告**（WARNING）。

### 本章节奏分析

- **类型识别**：本章为 investigation（报到、校册、核三笔差），与章节备忘 `chapter_type` 一致。
- **蓄压-释放结构**：本章无爆发，属蓄压章。但本章有**新元素释放**：合剌登场（新人物关系）、图章房（新场景／权力象征）、三笔差（新认知压力）。合剌的试探与「照册写」的回答构成小型张力释放，非纯蓄压。
- **日常段落功能验证**：门房换牌（信息：第七个、三个在三个不在）、书办立规矩（信息：照正册抄、纸钱三文）、合剌问骨哨（关系推进＋伏笔）、图章房（权力象征＋伏笔）、校册三笔差（认知压力＋MH11推进）。**功能明确，无纯日常**。
- **章末钩子**：「照册写。合剌笑停在脸上，没往下走，也没收回去——像一册摊开的账，两边对不上，谁也没落墨」——关系张力钩子，有效。
- **笑点／轻喜剧护栏**：本章笑点较弱（合剌「路上捡的」的应对略带冷幽默），符合 rule-004「至少一处由人物性格驱动的笑点」的下限。

### 评分: 85/100 通过（含 WARNING）

### 建议修复

- [WARNING] 近5章 investigation 占 75%，触发单一类型 > 50% 警告。建议第15章安排 constellation（情感／日常，如合剌关系深化、帖兰线回访）或 transition 章，打破 investigation 连续。
- [WARNING] 第13、14章连续 2 章 investigation 达 `maxConsecutive=2` 上限，第15章若再为 investigation 将触发 warningThreshold=3。建议第15章换类型。
- [MINOR] 本卷至第14章仍无 FIRE 章，逼近 `maxChaptersPerCycle=15` 上限。建议在第15–16章内安排一处小型爆发（如三笔差的当面对质、或合剌关系的转折），避免读者流失。
