# 发布切分层（release-split）设计

> **Date:** 2026-10-24 | **Status:** Active (2026-10-24 立项 SDD #70) · Revised 2026-10-24（价值门驳斥四处修订：试点更数/对账恒等式精确化/剥离语义钉死/provenance 载体形态） | **Severity:** 🟠 P1（用户点名） | **方法:** 独立确定性工具（零管线改动） | **系列:** 发布层（源自方案 A 用户定稿） | **依赖:** 无 | **范围:** tools/release_split.py + just 任务 + 单测 + ch1-4 夹具

> 2026-10-24 定稿。决策路径：起点/番茄发布单元 ~2200 字（番茄推荐 2000-2200、红线 ≥2000；起点主流 2000-3000）与创作单元（种子数学 10,000,000÷1400=7145 字/章）冲突——经 brainstorming 三方案对比，用户选定 **方案 A：创作层不动＋发布切分层**。备选 B（重锚 4546×2200 原生章：种子丰富批返工＋商业节奏底账重设计＋管线成本 2-3×）与 C（3500 折中：番茄仍超带）已否决。

## 1. 定位与边界

- 独立发布层工具 `tools/release_split.py`，与 pool-lint / ledger-archive 同族的 just 任务。
- **只读** `chapters/chapter-N.md`（已收束正文）；产物全部落 `publish/` 新目录；**绝不写管线任何面**（truth/outline/plans/chapters 一概不碰）。
- 无 LLM 调用——纯确定性文本切分。无平台 API/自动上传。
- 命令：`just release-split <project_dir> [--platform fanqie|qidian]`。

## 2. 平台档位

| 档 | 目标 | 硬下限（不可越） | 软上限（可微越） |
|----|------|----------------|----------------|
| fanqie | 2200 | 2000 | 2400 |
| qidian | 2700 | 2000 | 3000 |

切分数 `n` = 满足 `chars/n ≤ 软上限` 的最小整数；若 `chars/n < 2000` 则 `n-1`（接受微越软上限，硬下限优先）。整章 `< 2×2000` → 单更（章题不带序号），报告标记 `single-release`。

## 3. 切点算法（确定性）

1. 候选切点 = 段落边界（空行分隔）。剥离语义**钉死复用** `shenbi.gates.shared.strip_narrative_body`（五类命名 H2 节 + `<!--META-BEGIN/END-->` 包装；ch2 的 `## REVISION_CHECK` 变体实证在 POST 包装内、gate 计数不含——包装剥离即全覆盖）。剥离面（META 块 + 章题两行 H1）不入产物；章题取第二个 H1 供更题模式使用，`# Chapter N:` 英文行与章题行均计入剥离面对账。
2. 逐更推进：目标位置 ≈ 累计 `chars/n`；在目标前后各 ~15% 窗口内给候选打分取最优：
   - **+2 张力收尾**：切点前一段以 `？`/`！`/短物象句/对话轮收束（drafting 契约的牵引点密度 800-1200 字/个为背景依据；实测真实产物段落极短——中位 ~15 非空白字符、单章 300-420 段，窗口内候选恒过密，设计压力在平手裁决与「短物象句/对话轮」判定规则，非候选可得性）；
   - **+1 场景边界**：切点后一段以时间/地点/说话人转换词开头（翌日、入夜、到了、走出门……小型标记词表，词表外不认）；
   - **−2 场景腰斩**：切点后一段是场景开场而切点前一段不属于该场景（防把场景开头与铺垫分家）；
   - 平手取更早者。
3. 约束兜底：任何切法导致某更 `<2000` → 该切点前移至满足下限的最近段落边界；无解 → 并入前一更并复查下限。
4. 切点质量四档入账：`tension`（张力收尾）/`scene`（场景边界）/`plain`（普通段落）/`weak`（无张力标记且非场景边界）——weak 不阻拦，报告呈现。

## 4. 产物

```
publish/
├── releases.json          # 对账账本（schema: shenbi-releases-v1）
└── releases/
    └── release-NNNN.md    # 发布就绪正文（纯叙事段，无 META、无章题行）
```

- `releases.json` 每章条目：`[{seq, file, chars, range, cut_quality, head, tail}]`＋章级对账行＋全局 totals（更数/总字数/min/max/weak 数）。
- 更题模式缺省 `{章题}（一）（二）…`（中文序数；单更裸章题）；`--title-pattern` 可覆写。更题只进 releases.json（平台侧填章节名字段），不写进正文文件。
- `chars` 口径复用 `shenbi.gates.shared.total_chars_md_text`（与 G4 地板同一函数）。**对账恒等式 = 无损分解审计**：`total_chars_md_text(章原文) == Σ total_chars_md_text(更_i) + Σ total_chars_md_text(剥离段_j)`（剥离段 = 章题两行 + 全部 META 面，同函数逐段计量；gate 口径含章题行字符，故 Σ(更) 单独不等于章 gate 口径——以分解恒等为准，防切分丢字/重字）。
- 幂等增量：按章为键；已标记 `published: true` 的条目冻结（重切若改变其内容哈希即报错退出）；未冻结章可重切、其后更序号顺延重编。

## 5. 验证与试点

- 单测夹具：ch1-4 真产物复制入 `tests/fixtures/publish/`（**YAML frontmatter 三态载体**：`provenance: real-output` + `source: novel-xinghuo-vol1/chapters/chapter-N.md`——G0.18 载体契约（`g0_purity.py` PROVENANCE_STATES 三态）+ `tests/fixtures/chapters/` 先例；源目录 gitignored 属接受的悬垂引用先例；**禁入 MIRROR_MAP**——源不在仓内，注册 = CI 永久 missing-mirror WARN）。
- 测试面：带内约束（任意章任意档位每更 ≥2000）/ 无损分解审计 / 切点下限兜底 / 单更形态 / published 冻结拒绝 / 幂等重跑。
- 试点验收：对 ch1-4 以 fanqie 档试切（按 §2 公式预期 **14 更：4+4+3+3**——ch4=7792 gate 字符 → n=4 触发 7792/4=1948<2000 → n−1=3；原稿 15 更为笔误），人工抽查切点阅读感。

## 6. 非目标

不改管线/种子/商业节奏批；不做自动上传与平台对接；不做更级钩位重排的机器改写（weak 切点只报告不改写——改写属内容层）；探针 ch5 断点续跑与本工具施工互不阻塞。

## 7. 施工面清单

`tools/release_split.py`（新）＋ `justfile` release-split 目标 ＋ `tests/unit/tools/test_release_split.py` ＋ `tests/fixtures/publish/`（ch1-4 副本）＋ `AGENTS.md` 命令清单一行。无 src/shenbi/ 改动（gate 口径函数只 import——tools 先例 `lint_truth_pool.py:36`，venv 安装实证），无契约/SKILL 变更，无 backfill 义务。注记：`tests/unit/tools/` 已存在（14 文件先例，subprocess + `@pytest.mark.unit` 模式）；新测试文件须过 basedpyright strict（pyproject include=`["tests","src/shenbi"]`）；`tools/` 在 ruff T201/mypy 豁免面。
