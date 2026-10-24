# 发布切分层（release-split）设计

> **Date:** 2026-10-24 | **Status:** Active (2026-10-24 立项 SDD #70) · Revised 2026-10-24（价值门驳斥四处修订 + 设计审查第一轮十二项修订：−2 规则操作化/冻结三元与顺延冲突/平台分档隔离/schema 补全/错误契约/闭集词表） | **Severity:** 🟠 P1（用户点名） | **方法:** 独立确定性工具（零管线改动） | **系列:** 发布层（源自方案 A 用户定稿） | **依赖:** 无 | **范围:** tools/release_split.py + just 任务 + 单测 + ch1-4 夹具

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

切分数 `n` = 满足 `chars/n ≤ 软上限` 的最小整数；若 `chars/n < 2000` 则 `n-1`（接受微越软上限，硬下限优先）。单次回退即安全：`n = ceil(chars/2400)` ⇒ `chars ≥ 2400(n-1)+1` ⇒ 回退后均值恒 >2400 ≥2000，无迭代死锁。整章 `< 2×2000` → 单更（章题不带序号），报告标记 `single-release`——单更可至 ~3999 字（fanqie 软上限 +66%），这是硬下限约束下的唯一合法形态（拆分必破下限），非缺陷。输入章节选择 = 严格正则 `chapter-\d+\.md$`（排除 `-draft`/`-pre-rev`/`-decisions.json` 等伴生文件）。

## 3. 切点算法（确定性）

1. 候选切点 = 段落边界（空行分隔）。剥离语义**钉死复用** `shenbi.gates.shared.strip_narrative_body`（五类命名 H2 节 + `<!--META-BEGIN/END-->` 包装；ch2 的 `## REVISION_CHECK` 变体实证在 POST 包装内、gate 计数不含——包装剥离即全覆盖）。剥离面（META 块 + 章题两行 H1）不入产物；章题取第二个 H1 供更题模式使用，`# Chapter N:` 英文行与章题行均计入剥离面对账。
2. 逐更推进：目标位置 ≈ 累计 `chars/n`；在目标位置前后各 **精确 ±15%×(chars/n) 字符**窗口内给候选打分取最优。打分**可加、可叠算**，全部谓词为闭集规则（工具的全部价值在确定性，任何开放性措辞都视为未定义）：
   - **+2 张力收尾**（切点前一段满足任一，可叠）：(a) 末字符 ∈ {`？`，`！`}；(b) 短物象句 = 全段非空白字符 ≤40；(c) 对话轮 = 段首非空白字符 ∈ {`“`，`「`，`『`}（drafting 契约的牵引点密度 800-1200 字/个为背景依据；实测真实产物段落极短——中位 ~15 非空白字符、单章 300-420 段，窗口内候选恒过密，设计压力在平手裁决，非候选可得性）；
   - **+1 场景边界**：切点后一段以场景转换词开头（闭集词表，见 §7 常量 `SCENE_TRANSITION_WORDS`；词表外不认）；
   - **−2 场景腰斩**：切点**前**一段以场景转换词开头——把场景开场段与其后续发展切离（操作化形式；原稿「切点前一段属于该场景」不可闭集检测，弃）。注意 +1 与 −2 判的是**相邻两段**、可同点齐发（后段开场 + 前段也是上一景开场 = 双景紧邻），叠算净 −1 为正确语义；
   - 平手取更早者。
3. 约束兜底：某更 `<2000` → 调整该更与相邻更的边界切点至满足下限的最近段落边界（**首更只能后移其尾切点、末更只能前移其首切点**）；调整无解（候选耗尽）→ 并入前一更（首更则并入后一更）并复查下限——并入严格减少更数，n 收敛到 1 后若仍 `<2000` → 保持单更 + 报告标记 `floor-violation`（内容层问题，工具报告不硬失败）。全章无段落间候选切点（单段章）→ 跳过切分直接单更 + 标记 `forced-single`。终止性：并入单调减更数，无死循环。
4. 切点质量四档入账：`tension`（得分含张力收尾贡献）/`scene`（仅场景边界）/`plain`（有得分但两类皆无）/`weak`（得分 ≤0）——weak 不阻拦，报告呈现。
5. **错误契约**（类型化非零退出 + stderr 消息，均针对结构畸形输入）：章文件无第二个 H1（章题提取失败）/ 文件为空 / 剥离后无正文段 / project_dir 无 `chapters/` 目录或零匹配章。发布产物层的越界（`floor-violation`/`forced-single`）是报告标记非退出错误。

## 4. 产物

```
publish/
└── <platform>/                 # fanqie | qidian——分档隔离，杜绝跨档互覆
    ├── releases.json           # 对账账本（schema: shenbi-releases-v1）
    └── releases/
        └── release-NNNN.md    # 发布就绪正文（纯叙事段，无 META、无章题行）
```

- `releases.json` 账本级字段：`{schema: "shenbi-releases-v1", platform, generated_at, chapters: [...], totals}`；章级条目：`{chapter, gate_chars, releases: [...], stripped_chars}`（`stripped_chars` = 剥离面非空白字符数）；更级条目：`[{seq, file, chars, range, cut_quality, head, tail, title, content_hash, published}]`——`range` = 该更在剥离后正文中的 `[起, 止)` 字符偏移；`head`/`tail` = 首尾各 ≤12 字符单行摘要；`published` 默认 `false`，**由人工发布后手工置 `true`**（工具从不自动置位）；`content_hash` = 该更正文 sha256 前 16 位（冻结判据的存储形态）。章级 `Σ 更 chars == gate_chars − stripped_chars` 对账 + 全局 totals（更数/总字数/min/max/weak 数/single-release 与 forced-single 与 floor-violation 计数）。
- 更题模式缺省 `{章题}（{中文序数}）`（单更裸章题）；`--title-pattern` 可覆写（占位符恰两个：`{章题}`/`{中文序数}`），唯一消费方 = 人工填平台章节名字段（更题只进 releases.json，不写进正文文件）。
- `chars` 口径复用 `shenbi.gates.shared.total_chars_md_text`（与 G4 地板同一函数）。**对账恒等式（简化形式）**：`Σ total_chars_md_text(更_i) == total_chars_md_text(章原文) − 章题两行 H1 非空白字符数`（gate 口径含章题行字符；META 面在同函数口径下恒为 0 计入零项，故不出现）——防切分丢字/重字。
- 幂等增量：按章为键；`published: true` 条目**三元冻结**（seq + 文件路径 + content_hash 任一将变即报错退出）；未冻结章可重切，其后未冻结更的全局序号（NNNN 按全账本章序全局连续编号）顺延重编；若前章重切导致任何已冻结更的 seq 或路径漂移 → **硬错误退出**，附 `--renumber-published` 人工逃生口（显式重编号并逐条列漂移清单，须人工确认已发布平台侧同步改名）。

## 5. 验证与试点

- 单测夹具：ch1-4 真产物复制入 `tests/fixtures/publish/`（**YAML frontmatter 三态载体**：`provenance: real-output` + `source: novel-xinghuo-vol1/chapters/chapter-N.md`——G0.18 载体契约（`g0_purity.py` PROVENANCE_STATES 三态）+ `tests/fixtures/chapters/` 先例；源目录 gitignored 属接受的悬垂引用先例；**禁入 MIRROR_MAP**——源不在仓内，注册 = CI 永久 missing-mirror WARN）。
- 测试面：带内约束（任意章任意档位每更 ≥2000）/ 对账恒等 / 切点下限兜底（含首更后移方向）/ 单更形态（single-release/forced-single/floor-violation 三标记）/ published 三元冻结拒绝 / 冻结×顺延冲突硬错误 + `--renumber-published` 逃生 / 幂等重跑 / 平台分档隔离（fanqie/qidian 产物互不覆写）/ 畸形输入错误契约（无第二 H1/空文件/零段落/零章目录）/ 更题生成（缺省 + `--title-pattern` 覆写）/ 打分四档分类。
- 运行报告：stdout 摘要（tools/ 在 ruff T201 豁免面，打印合法）+ releases.json totals 全量。
- 试点验收：对 ch1-4 以 fanqie 档试切（按 §2 公式预期 **14 更：4+4+3+3**——ch4=7792 gate 字符 → n=4 触发 7792/4=1948<2000 → n−1=3；原稿 15 更为笔误），人工抽查切点阅读感。

## 6. 非目标

不改管线/种子/商业节奏批；不做自动上传与平台对接；不做更级钩位重排的机器改写（weak 切点只报告不改写——改写属内容层）；探针 ch5 断点续跑与本工具施工互不阻塞。

## 7. 施工面清单

`tools/release_split.py`（新，含闭集常量 `SCENE_TRANSITION_WORDS` 场景转换词表——词表唯一信源，≈ 翌日/入夜/到了/走出门/次日/清晨/黄昏/入夜时分/夜半/天亮 类时间-地点转换词，初始 ≤20 词、仅词表内生效）＋ `justfile` release-split 目标 ＋ `tests/unit/tools/test_release_split.py` ＋ `tests/fixtures/publish/`（ch1-4 副本）＋ `AGENTS.md` 命令清单一行。无 src/shenbi/ 改动（gate 口径函数只 import——tools 先例 `lint_truth_pool.py:36`，venv 安装实证），无契约/SKILL 变更，无 backfill 义务。注记：`tests/unit/tools/` 已存在（14 文件先例，subprocess + `@pytest.mark.unit` 模式）；新测试文件须过 basedpyright strict（pyproject include=`["tests","src/shenbi"]`）；`tools/` 在 ruff T201/mypy 豁免面。
