# 发布切分层（release-split）设计

> **Date:** 2026-10-24 | **Status:** Active (2026-10-24 立项 SDD #70) · Revised 2026-10-24（价值门驳斥四处 + 设计审查三轮：R1 十二项[R2 操作化/冻结三元/平台隔离/schema 补全/错误契约/闭集词表] + R2 十七项[ch5 三 H1 证伪→全部 H1 行/统一非空白度量/兜底单次遍历/四档谓词归类/章号数值排序] + R3 十四项[空窗口回退/窗口基底钉死/张力叠算上限/flags 矩阵/账本生命周期/孤儿清理/更.chars 防双重剥/RUF 豁免]） | **Severity:** 🟠 P1（用户点名） | **方法:** 独立确定性工具（零管线改动） | **系列:** 发布层（源自方案 A 用户定稿） | **依赖:** 无 | **范围:** tools/release_split.py + just 任务 + 单测 + ch1-5 夹具

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

切分数 `n` = 满足 `chars/n ≤ 软上限` 的最小整数；若 `chars/n < 2000` 则 `n-1`（接受微越软上限，硬下限优先）。单次回退即安全：`n = ceil(chars/2400)` ⇒ `chars ≥ 2400(n-1)+1` ⇒ 回退后均值恒 >2400 ≥2000，无迭代死锁（fanqie 档代数；qidian 档回退分支实际不可达——触发需 chars ∈ (3000, 4000)，而该区间已被单更规则先占）。**公式输入 = gate 口径章字符**（含 H1 行）。整章 `< 2×2000` → 单更（章题不带序号），报告标记 `single-release`——单更可至 ~3999 字（fanqie 软上限 +66%），这是硬下限约束下的唯一合法形态（拆分必破下限），非缺陷。输入章节选择 = 严格正则 `chapter-\d+\.md$`（排除 `-draft`/`-pre-rev`/`-decisions.json` 等伴生文件；ch1-5 实测零误配零漏配）。

## 3. 切点算法（确定性）

1. 候选切点 = 段落边界（空行分隔）。剥离语义**钉死复用** `shenbi.gates.shared.strip_narrative_body`（五类命名 H2 节 + `<!--META-BEGIN/END-->` 包装；ch2 的 `## REVISION_CHECK` 变体实证在 POST 包装内、gate 计数不含——包装剥离即全覆盖）。剥离面 = META 块 + **全部 H1 行**（`^# ` 模式；ch5 实证存在 META 包装外的重复章题 H1——「两行」假设被活数据证伪；全部 H1 行剥离使恒等式对 ch1-5 精确闭合：6517−22==6495）；章题取第二个 H1 供更题模式使用；H1 行不入产物、其非空白字符计入 `stripped_chars`。**零非空白字符段**（如孤立 U+3000 行）在切分前丢弃，不构成候选。
2. 逐更推进：**统一度量 = 非空白字符前缀计数**（与 `chars` 口径同基；目标/窗口/候选位置/`range` 偏移全用此度量，舍入一律 floor）。**目标/窗口基底 = 剥离后正文非空白字符数**（`gate_chars − stripped_chars`；非 gate 口径），目标位置 = `i × 基底/n`（实数除法，`i ∈ {1..n-1}`）；窗口 = 目标 ± `floor(0.15 × 基底/n)`；候选位置 = 边界前的累计非空白字符数。窗口内候选打分取最优；**窗口空 → 全候选集上取 |候选位置−目标| 最小者，平手取更早者**。打分**可加、可叠算**，全部谓词为闭集规则（工具的全部价值在确定性，任何开放性措辞都视为未定义）：
   - **+2 张力收尾**（切点前一段，(a)(b)(c) **各自独立 +2、同段可叠至 +6**）：(a) 最后一个非空白字符 ∈ {`？`，`！`}；(b) 短物象句 = 全段非空白字符 ≤40；(c) 对话轮 = 段首非空白字符 ∈ {`“`，`「`，`『`}（drafting 契约的牵引点密度 800-1200 字/个为背景依据；实测真实产物段落极短——中位 ~15 非空白字符、单章 ~300-420 段，窗口内候选恒过密，设计压力在平手裁决，非候选可得性）；
   - **+1 场景边界**：切点后一段以场景转换词开头（闭集词表 `SCENE_TRANSITION_WORDS`，初始枚举恰 16 词：翌日、次日、清晨、天亮、黄昏、入夜、夜半、午夜、到了、走进、回到、出门、动身、起程、转场、天明；词表外不认；`到了` 类段首误报属质量面——weak 只报告不阻拦）；
   - **−2 场景腰斩**：切点**前**一段以场景转换词开头——把场景开场段与其后续发展切离（操作化形式）。+1 与 −2 判的是**相邻两段**、可同点齐发（后段开场 + 前段也是上一景开场 = 双景紧邻），叠算净负为正确语义；
   - 平手取更早者（候选位置严格全序，平手必有唯一解）。
3. 约束兜底（**单次遍历修复，有界终止**）：更序遍历；短缺更（`<2000`）增长修复——移动其与相邻更的边界切点至满足下限的最近边界（首更只能右移尾切点、末更只能左移首切点、中位更取两向最近边界且平手取右），**每切点至多移动一次**；遍历后仍短缺 → 并入相邻更中字符数较大者（首更并入后一更）并复查下限；并入严格减少更数，至多 n−1 次。**flags 矩阵按成因路径枚举**（互斥完备，可齐发于 flags 数组）：尺寸单更（§2 `<2×2000`）≥2000 → `{single-release}`；尺寸单更 `<2000` → `{single-release, floor-violation}`（可拆性由尺寸规则先占，`forced-single` 专属「切分求解失败」语义）；单段章（无候选切点）→ `{forced-single}`，`<2000` 加 `{floor-violation}`；约束并尽至单更（多段 ≥4000 章修复无解）→ `{forced-single}`（并尽单更恒为全章 ≥4000 字，floor-violation 不可达）——post-merge 超越软上限无上界，接受（硬下限下的合法形态，非缺陷）。
4. 切点质量四档入账（**按谓词触发归类，与净分无关**，报告用途）：`tension`（任一张力谓词触发）/`scene`（无张力触发而场景边界触发）/`plain`（无任何谓词触发）/`weak`（张力与场景皆未触发而腰斩触发）——weak 不阻拦，报告呈现。
5. **错误契约**：CLI 用法错 → argparse 缺省 exit 2；结构畸形输入 → exit 1 + stderr 消息（章文件无第二个 H1 / 文件为空 / 剥离后无正文段 / project_dir 无 `chapters/` 目录或零匹配章 / 同章号重复文件（如 chapter-1 与 chapter-01 并存）/ `--title-pattern` 含未知占位符）。**账本生命周期**：现存 `releases.json` 畸形 JSON 或 `schema != "shenbi-releases-v1"` → exit 1；账本在册章已从 `chapters/` 消失且含冻结条目 → exit 1（人工账本手术）；消失且全未冻结 → 删该章条目 + 顺延重编；`--renumber-published` 遇已消失的冻结更 → 硬错误。发布产物层越界（`floor-violation`/`forced-single`）是报告标记非退出错误；冻结冲突（§4）亦 exit 1。**孤儿清理**：重切后工具删除新账本未引用的 `releases/*.md`（冻结路径除外）。

## 4. 产物

```
publish/
└── <platform>/                 # fanqie | qidian——分档隔离，杜绝跨档互覆
    ├── releases.json           # 对账账本（schema: shenbi-releases-v1）
    └── releases/
        └── release-NNNN.md    # 发布就绪正文（纯叙事段，无 META、无章题行）
```

- `releases.json` 账本级字段：`{schema: "shenbi-releases-v1", platform, generated_at, chapters: [...], totals}`；章级条目：`{chapter, gate_chars, stripped_chars, flags: [], releases: [...]}`（`stripped_chars` **操作化定义** = `total_chars_md_text(章原文) − Σ 更.chars`——即全部 H1 行非空白字符数；META 原文不计入，因 gate 口径本就不见 META 面；`flags` 承载 §3.3 矩阵）；更级条目：`[{seq, file, chars, range, cut_quality, head, tail, title, content_hash, published}]`——**`chars` = 已剥离切片上的纯非空白计数 `len(re.sub(r"\s","",切片))`**（不重跑 strip——防未来章正文含围栏块/`---` 分隔线时双重剥伪报警；`total_chars_md_text` 仅用于章级 gate 口径）；`range` = 该更在剥离后正文中的 `[起, 止)` **非空白字符偏移**；`head`/`tail` = 切片首/末 12 个非空白字符（单行化）；`published` 默认 `false`，**由人工发布后手工置 `true`**（工具从不自动置位）；`content_hash` = 该更正文 sha256 前 16 位（冻结判据的存储形态）。章级 `Σ 更 chars == gate_chars − stripped_chars` 对账 + 全局 totals（更数/总字数/min/max/四档计数/flags 计数）。章序 = **捕获章号数值升序**（`chapter-2` 先于 `chapter-10`；同号重复 → 错误契约）。
- 更题模式缺省 `{章题}（{中文序数}）`（**中文序数 = 章内更序**，一/二/…/十/十一…；单更裸章题）；`--title-pattern` 可覆写（占位符恰两个：`{章题}`/`{中文序数}`，未知占位符 → 错误契约），唯一消费方 = 人工填平台章节名字段（更题只进 releases.json，不写进正文文件）。
- `chars` 口径复用 `shenbi.gates.shared.total_chars_md_text`（与 G4 地板同一函数）于**章级 gate 计量**；**§2 公式的输入 = gate 口径章字符**（含 H1 行，与试点算术一致），切分分布的是剥离后正文字符（两者差 = H1 行字符，≈15 字/章，不构成口径冲突）。**对账恒等式（简化形式）**：`Σ 更.chars == total_chars_md_text(章原文) − 全部 H1 行非空白字符数`（实证 ch1-5 逐章精确闭合；META 面在同函数口径下恒为 0 不出现）——防切分丢字/重字。
- 幂等增量：按章为键；`published: true` 条目**三元冻结**（seq + 文件路径 + content_hash 任一将变即报错退出）；**内容哈希漂移于冻结更（章已重新收束）同样硬错误、无逃生口**——唯一出路是人工账本手术（删该章条目重切），by design；未冻结章可重切，其后未冻结更的全局序号（NNNN 按章序数值升序全局连续编号）顺延重编；若前章重切导致任何已冻结更的 seq 或路径漂移 → **硬错误退出**，附 `--renumber-published` 人工逃生口（显式重编号并逐条列漂移清单，须人工确认已发布平台侧同步改名）。`--platform` 缺省 `fanqie`。幂等测试比较**语义内容**（chapters/releases/totals，忽略 `generated_at`）。

## 5. 验证与试点

- 单测夹具：ch1-4 真产物复制入 `tests/fixtures/publish/`（**YAML frontmatter 三态载体**：`provenance: real-output` + `source: novel-xinghuo-vol1/chapters/chapter-N.md`——G0.18 载体契约（`g0_purity.py` PROVENANCE_STATES 三态）+ `tests/fixtures/chapters/` 先例；源目录 gitignored 属接受的悬垂引用先例；**禁入 MIRROR_MAP**——源不在仓内，注册 = CI 永久 missing-mirror WARN）。ch5 的重复章题 H1 形态以 ch5 复制件覆盖（同 provenance 形态；「全部 H1 行」剥离与恒等式的唯一活体用例）。
- 测试面：§2 n 公式（含 ch4 回退分支 7792→3）/ 带内约束（无 flags 章 + fanqie/qidian 双档每更 ≥2000；带 floor-violation/forced-single 标记章豁免）/ 对账恒等（含 ch5 三 H1 形态）/ **空窗口回退**（构造稀疏段落布局：4500 字 1200/2100/1200 → 窗口 [1913,2587] 空 → 全候选集最近者、平手取早 → 修复链 → forced-single）/ 切点下限兜底（单次遍历修复、首更右移方向、并入较大邻更）/ **flags 矩阵**（§3.3 成因路径全枚举）/ 单更形态 / published 三元冻结拒绝 / 冻结×顺延冲突硬错误 + `--renumber-published` 逃生 / 顺延重编 happy path（上游重切 → 下游未冻结更重编号）/ **孤儿清理**（重切后未引用 releases/*.md 删除、冻结路径保留）/ **账本生命周期**（畸形 JSON/schema 不符 exit 1；在册章消失：含冻结 exit 1、全未冻结删条目重编）/ 幂等重跑（语义内容比较）/ 平台分档隔离 / 畸形输入错误契约（无第二 H1/空文件/零段落/零章目录/同号重复/未知占位符）/ 更题生成（缺省 + `--title-pattern` + 章内中文序数 ≥10）/ 打分四档归类 + 平手取更早者确定性。**测试输入双轨**：真实产物断言走 `tests/fixtures/publish/`（G0.9）；对抗性段落布局/账本状态等结构性用例用测试内构造输入（tmp_path/字面量，`tests/unit/tools/` 既有 206 处 tmp_path 先例——G0.9 约束的是「冒充真实产物的 fixture」，不约束结构性用例）。
- 运行报告：stdout 摘要（tools/ 在 ruff T201 豁免面，打印合法）+ releases.json totals 全量。
- 试点验收：复制 ch1-4 至临时目录（工具按 §2 正则取目录内全部匹配章；含 ch5 则 17 更），以 fanqie 档试切，预期 **14 更：4+4+3+3**（ch4=7792 gate 字符 → n=4 触发 7792/4=1948<2000 → n−1=3；原稿 15 更为笔误），人工抽查切点阅读感。

## 6. 非目标

不改管线/种子/商业节奏批；不做自动上传与平台对接；不做更级钩位重排的机器改写（weak 切点只报告不改写——改写属内容层）；探针 ch5 断点续跑与本工具施工互不阻塞。

## 7. 施工面清单

`tools/release_split.py`（新，含闭集常量 `SCENE_TRANSITION_WORDS` 场景转换词表 = §3.2 枚举的恰 16 词，词表唯一信源；**携 CJK 全角标点数据面 → 需 ruff RUF001-003 per-file-ignores**，`lint_truth_pool.py` 等既有 CJK 工具同款）＋ `justfile` release-split 目标 ＋ `tests/unit/tools/test_release_split.py`（**同样需 RUF001-003 per-file-ignores**）＋ `tests/fixtures/publish/`（ch1-5 副本）＋ `AGENTS.md` 命令清单一行。无 src/shenbi/ 改动（gate 口径函数只 import——tools 先例 `lint_truth_pool.py:36`，venv 安装实证），无契约/SKILL 变更，无 backfill 义务。注记：`tests/unit/tools/` 已存在（14 文件先例，subprocess + `@pytest.mark.unit` 模式）；新测试文件须过 basedpyright strict（pyproject include=`["tests","src/shenbi"]`）；`tools/` 在 ruff T201/mypy 豁免面。
