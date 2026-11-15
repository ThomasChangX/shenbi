# 外部读者锚定盲评包（spec #115 T3 · 预注册 2026-11-15）

**用途**：检验 `shenbi-review-resonance` 的 `overall` 分是否能预测真实读者的阅读反应。
**执行**：3 名盲评人，每人独立评 12 章，每章 5 项 1-7 分；$0 API、约 6 人时。

## 0. 预注册修正（r2，2026-11-15，数据收集前）

原预注册写「低分带（overall ≤76）4 章 / 中分带 4 / 高分带 4」。**母体检查发现低分带在 32 条已评分行中只有 2 章（ch2=74、ch3=76），无法抽出 4 章**。为保持预注册的 n=12 与分带定义不变量，r2 修正为：

- 低分带 ≤76：**全取 2 章**（ch2、ch3）；
- 中分带 77-80：按章号均匀取 5 章（ch1、ch9、ch16、ch29、ch45）；
- 高分带 ≥81：按章号均匀取 5 章（ch12、ch19、ch31、ch41、ch49）。

分层数不等（2/5/5）在分析中如实分层报告，不做加权合并；ICC/ρ 以 12 章整体与分带描述并报。此修正发生在任何人工评分之前。

## 1. 盲评纪律（必须遵守）

1. 不得打开 `key.csv`（章号映射）；不得读 `novel-xinghuo-vol1/truth/resonance_trend.md`、任何 `audits/*resonance*`、或本预注册的判据表（`docs/research/2026-11-15-quality-external-anchor-prereg.md` 第 2 节）。
2. 按 `order-raterN.csv` 的顺序阅读 `chapters/item-XX.md`；每章 10-15 分钟，一次读完一章再评分。
3. 章文件里的 `PRE_WRITE_CHECK` / `POST_WRITE_SELF_CHECK` 方括号自检块**不是正文**，请忽略；只评故事本身。
4. 5 项均用 1-7 分（1=非常低，4=中性，7=非常高）；可写 `notes`，但不强制。
5. 填自己的 `ratings-raterN-template.csv`（item_id 已按随机顺序预填），保存为 `ratings-raterN.csv`；不要在文件名/备注里写章节号。

## 2. 五项 rubric

| q | 维度 | 问题 |
|---|---|---|
| q1 | 继续读意愿 | 读完这章，你想不想立刻读下一章？ |
| q2 | 情绪冲击 | 这章有没有让你产生明确的情绪反应（揪心/爽/好笑/压抑等）？ |
| q3 | 记忆点 | 合上页面后，你能记住至少一个具体画面/句子/动作吗？ |
| q4 | 代入感 | 你是否感到「在场」而非在听概述？ |
| q5 | 推荐意愿 | 你会不会把这一章推荐给同好？ |

## 3. 交付

- `ratings-rater1.csv`、`ratings-rater2.csv`、`ratings-rater3.csv` 放回本目录；
- 运行 `uv run python reports/external-anchor-20261115/analyze.py`；
- 输出 `analysis.md`：ICC(2,k)、Spearman ρ（overall + 四维分）、bootstrap 95% CI、分带描述、作废记录。

## 4. 作废/停机（预注册）

- 任一评人事前看到 resonance 报告/trend/判据表 → 该评人全部评分作废；
- 研究期间章文件 mtime 变化 → 该章作废；作废 ≥3 章 → 暂停重抽样；
- 评人报告「无法理解 rubric」→ 记录并暂停，修订指导语后重来（不得中途改判据）。

## 5. 文件

- `chapters/item-*.md`：匿名章文（交付形态，含自检块）；
- `key.csv`：item→chapter（**评人不得打开**）；
- `order-raterN.csv`：随机阅读顺序（seed=20261115）；
- `ratings-raterN-template.csv`：按随机顺序预填 item_id 的评分表；
- `analyze.py`：ICC(2,k)+Spearman+bootstrap 分析脚本。
