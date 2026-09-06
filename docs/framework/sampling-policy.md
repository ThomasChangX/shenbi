# Sampling Policy（检查面采样策略）

> C29 (spec #43) 目标 3 成文：哪些 gate 检查**有意**只读输入的一部分、采多少、为什么。
> 其余检查读全文。所有下列采样点都在检查结果 JSON 中披露（`input_sampled` /
> `files_sampled` / `findings_capped`，见
> [gates.md](gates.md#result-schema-sampling-disclosure-c29)）。
>
> **登记范围**：本表登记 C29 改动面的全部采样点（下三表）+ 既有的已自披露先例
> （G6.10 `chapters_sampled`）。仓内其余历史截断点（g0.py rubric `[:10]`、
> g_transition.py `[:10]`、g2.py removals `[:5]`、g4 各 errors `[:5]`、
> plot_thread_weaver `[:3]`）不在 C29 改动面内、尚无披露——遗留清单，
> 待后续清理 spec 承接（C35 审计过程卫生域）。

## 字符前缀采样（`clip_with_disclosure`）

| 检查 | 采样点 | 量 | 理由 |
|------|--------|-----|------|
| G6.4 timeline 扫描 | `g6_checks.py` chapter 文本 | 5000 字 | 时间线标记集中于章首；全集扫描成本线性超线性收益 |
| G6.4 信息状态双 pass | `g6_checks.py` `_chapter_text` | 3000 字 | 实体首次引入多在章前 1/3；双 pass 已是 2× 成本 |
| G6.8 ghost voice | `g6.py` chapter 文本 | 5000 字 | 角色名出现检测对章尾低频事件可容忍漏报（WARN 级检查） |
| G6.8 catchphrase | `g6.py` chapter 文本 | 5000 字 | 口头禅重复出现，前缀命中概率极高 |
| G6.9 数值约束 | `g6.py` ch_contents | 3000 字 | 数值密集段多在场景前部 |
| G5.3 数值一致性 | `g5.py` output 文件 | 5000 字 | 跨文件数值冲突抽首段即可暴露 |
| G5.3 术语混用 | `g5.py` character 文件 | 3000 字 | 术语密度稳定，前缀代表性足够 |

## 文件计数采样

| 检查 | 采样点 | 量 | 理由 |
|------|--------|-----|------|
| G5.3 outline 扫描 | outline 目录 | 前 3 文件 | outline 文件族大且同构（披露 `files_sampled` 的 `outline:3/N` 段） |
| G5.3 输出文件扫描 | world+outline 合集 | 前 8 文件 | 性能封顶（`output:8/N` 段） |
| G5.3 角色文件 | characters 目录 | 前 6 文件 | 角色文件同构（`chars:6/N` 段） |
| G6.8 章节采样 | chapters | 前 15 章 | voice 检查对长篇的代表性截断（`files_sampled: "15/N"`） |

## 发现项封顶（findings，非输入采样）

| 检查 | 采样点 | 量 | 理由 |
|------|--------|-----|------|
| G5.3 conflicts 输出 | 冲突列表 | 前 10 条 | must_fix 列表信噪比 |
| G6.4 violations 输出 | 时间线违例 | 前 10 条 | 既有行为（g6_checks，C29 登记补录） |
| G6.8 catchphrases | 每角色 | 前 3 条 | top-N 代表性（`角色名:3/N` 带归属） |
| G6.9 数值约束 | constraints | 前 10 条 | 性能封顶 |
| G6.10 style outliers | 离群章节 | 前 8 条 | 既有行为（非本 spec 改动面） |

## 修改纪律

- 新增检查如需采样，必须走 `clip_with_disclosure()`（字符型）或显式
  `files_sampled`/`findings_capped` 披露（计数型），并在本表登记。
- 调整采样量时同步本表与本表引用的行号。
- 读全文的检查不得静默降级为采样。
