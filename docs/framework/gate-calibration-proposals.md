# G4 门标定提案（七项交裁）· spec #116 T3

> **只提案，不改行为**（用户裁定 2026-11-15）：本件全部提案项交用户逐项裁定后
> 由后续批次执行；本批 `git diff` 仅 docs/tools/tests。每项四栏——现状（数字）/
> 提案（≥1 具体选项）/红测/回滚（单 commit 条件）。
>
> **数字来源**：Task 1 实跑报告 `reports/2026-11-20-gate-power-vol1.md`（50 章
> 回放，2026-11-20）；spec #116 附录 A（2026-11-15 census）；Goodhart r1
> `reports/2026-11-15-goodhart-escape-execution.md` 与 r2
> `reports/2026-11-15-goodhart-r2-single-chapter.md`。
> **红测引用形态（M-1 裁定）**：直接引用
> `tests/unit/gates/g4/test_gate_power_negatives.py::<测试名>`（与
> `docs/framework/gate-power-baseline.md` 证据列同源形态，不另造 t4_evidence
> 列）；「落地批补」= 提案落地批次新增红测（本件不写）。

### voice_density（`G4.cd.voice_density`，最高优先项）

| 栏 | 内容 |
|---|---|
| 现状（数字） | vol1 50 章回放 **14/50 must_fix FAIL**（36 PASS，firing 0.28）——真语料唯一成规模开火的散文门；Goodhart r2 两臂 **15/18 章失败**（A 8/9、B 7/9），B 人格「按词表精确投放」也只把 0-1 个/章提到 1 个，未稳定到阈值 **≥2 逐字口癖/账房动词**（mf 形 `1<2`）；r1 A1 4/4 产出章同门失败。词表阈值与真实散文分布错位是两臂共同死因（r2 §4：「该门是词表阈值问题，不是写手博弈问题」）。 |
| 提案 | **选项 A（重标定）**：阈值 ≥2 → ≥1（词表不变）——覆盖 14/50 must_fix 章的实弹分布（真语料 0-1 个/章）；**选项 B（两级拆分）**：「逐字口癖**在场**」保 hard（≥1 即过，absent 才 FAIL）＋「密度**下限**」降 WARN 报告行（劝谏面，不拦章）——把「在场性」与「密度」解耦，保留声口缺席的硬拦截；**选项 C**：词表按真语料命中分布收窄（扩账房动词实弹命中形）。 |
| 红测 | 已有 `test_voice_stripped_fails_voice_density_gate`（钉 `1<2` 臂——选项 A/B 落地时该测试随阈值同步改钉）；落地批补：带内/带外样本双向（spec r2/C1 要求——≥1 过、0 个 FAIL、密度带 WARN 三态）。 |
| 回滚 | 阈值/两级拆分回退＝单 commit（回滚面＝`src/shenbi/text/voice_lexicon.py` 单文件：`DEFAULT_VOICE_DENSITY_MIN=2`（:33）＋`ACCOUNTING_VERBS`（:16）；`chapter_drafting.py` 仅 import（:11-13）非定义点。注意阈值可被 genre config `voice_density_min.min_per_chapter` 覆盖（`chapter_drafting.py:1403-1408`）——回滚须同查项目 config 覆盖键，revert 词表文件＋清覆盖键即恢复 ≥2 单级）。 |

### hook（`G4.cd.chapter_end_hook`）

| 栏 | 内容 |
|---|---|
| 现状（数字） | 50/50 PASS 零 FAIL/WARN；归因再推导：**15/50（30%）章仅靠单字张力词命中**（窗内无？、无账目行、无多字标记）；单字命中 `还`=38 章、`账`=38 章——单字集 却但还仍瞒藏账欠谜 与主角声口「账房腔：用记账动词描述一切」（`novel-xinghuo-vol1/characters/protagonist.md` voice_profile）**同词表**：账房腔写法天然喂饱 hook 门，门测的是母题不是张力。 |
| 提案 | **选项 A（多字/结构臂）**：窗口命中改为「多字张力词 ∨ ？ ∨ 账目行（≥2 独立数字串）」任一，单字命中降为 WARN 报告行；**选项 B（词表不相交）**：张力单字集与本项目母题词表（账/欠/还/藏）强制不相交——从 SINGLE_CHAR_TENSION 剔除母题字，或项目配置声明排除；**选项 C**：维持现状＋分类 `floor-untested`（登记依据＝15/50 单字-only 数据）。 |
| 红测 | `test_hook_killed_real_chapter_fails_hook_gate`（尾 8 叙事段张力词全灭→FAIL——门能失败）。选项 A/B 落地批补：单字-only 章样本断言降级面（FAIL→WARN）。 |
| 回滚 | 词表/臂权重回退＝单 commit（门本体张力词表＝`chapter_drafting.py` `_check_chapter_end_hook`（:1161 起）的**内联正则字面量**（:1211-1212，多字＋单字同式），非独立常量；`tools/gate_power_replay.py` 的 `HOOK_TENSION_RE`/`SINGLE_CHAR_TENSION`（:110/:113）是回放工具的**诊断镜像**，改门词表须同步改镜像保持归因同源）。 |

### protagonist（`G4.cd.protagonist_presence`）

| 栏 | 内容 |
|---|---|
| 现状（数字） | 50/50 PASS；名字表 frontmatter 正则与 YAML 双取致**重复 append**（`chapter_drafting.py:495`/`:508`，实弹表 `['那罕','那罕','他']`——重复项使 count 加倍）；实弹总数（去重名单 那罕＋他 再推导）**中位 76 / 最小 49 vs 阈值 3**（附录 A 双取口径中位 93/最小 64，同源不同 roster）；仅 `他` 一项在 50/50 章 ≥3——门实际上只数了代词。 |
| 提案 | **选项 A（修 roster）**：去重双 append（`:495`/`:508` 二选一）——纯 bug 修，不改阈值；**选项 B（名字单独下限）**：名字（非代词 `他`）单独 ≥1 或 POV 声明替代——堵「代词撑满门」面；**选项 C（重标定）**：阈值 3 → 按真语料分布的下界（如最小 49 的分数位），保留防消失 floor。 |
| 红测 | `test_protagonist_vanished_real_chapter_fails_presence_gate`（那罕→术赤、他→此人 全章替换→FAIL）；选项 B 落地批补：代词-only 章样本（名字 0/代词 ≥3）断言新臂。 |
| 回滚 | roster 去重/阈值回退＝单 commit（`_load_protagonist_names` 单函数面）。 |

### transition（`G4.transition`）

| 栏 | 内容 |
|---|---|
| 现状（数字） | 50/50 PASS；narrative 口径每章计数**中位 0 vs 阈值 max(5, wc//1000)=5**（历史放宽链 1/3000→1/1000 的注记见 spec #116 §0）；化合物（必然/果然/偶然…）全语料总命中仅 **3 次**——化合物扩展假说在本语料**不成立**（负结果，记档）。 |
| 提案 | **选项 A（retire）**：移除检查（连发射面）——中位 0 对阈值 5 表示门在真实散文上恒真，且无 Goodhart 对照面（r1/r2 零次 transition 逃生证据）；**选项 B（重标定）**：阈值 5 → 1-2（或改 per-1000 密度口径），保留防「转折词灌水」floor；**选项 C（维持＋分类）**：`floor-untested`，化合物不扩展（负结果锚）。 |
| 红测 | `test_transition_flooded_real_chapter_fails_transition_gate`（每叙事段首轮注 不过，/此时，…→FAIL，证门能失败）；选项 A 落地批＝删门＋删行＋baseline 行转 `retired`（证据=本提案与用户裁定记录）。 |
| 回滚 | retire/revert 或阈值回退＝单 commit。 |

### scene_concreteness / surge / fatigue / meta（逐项分类组，均 50/50 PASS 零点火）

| 门 | 现状（数字） | 提案 | 红测 | 回滚 |
|---|---|---|---|---|
| `G4.cd.scene_concreteness` | 50/50 PASS（视觉动词窗恒真，附录 A 同） | 分类 `floor-untested`（证据＝红测）或维持 `unclassified` 至跨书语料 | `test_scene_visuals_stripped_fails_concreteness_gate`（视觉动词→在、「」剥除→FAIL） | 分类行编辑即回（无行为改动） |
| `G4.cd.surge` | 50/50 PASS（长句配额恒真）；WARN-only 发射面 | 分类裁定：`floor-untested`（配额从未触下界）或 `decorative`（须书面机理） | `test_surge_killed_warns_surge_quota_gap`（≥35 字句 ，→。→WARN） | 同上 |
| `G4.fatigue` | 50/50 PASS（暗道面 9>8 阈从未触） | 分类 `floor-untested` 或维持 | `test_fatigue_flooded_fails_fatigue_gate`（×9「他心中暗道。」→FAIL） | 同上 |
| `G4.meta` | 50/50 PASS（META_NARRATIVE 闭集词零命中） | 分类 `floor-untested`（闭集词零命中＝floor 有效从未需要）或 `decorative`（须书面机理：真实章文体不产元叙事） | `test_meta_injected_fails_meta_gate`（由此可见/综上所述 注入段→FAIL） | 同上 |

### simile（`G4.cd.simile_band`）

| 栏 | 内容 |
|---|---|
| 现状（数字） | **28/50（56%）WARN** 落 [2,4] 带外（22 PASS，0 FAIL——纯劝谏面）；计量吃 `ctx.content` 原文含 PRE/POST（污染面），Task 1 双口径对照列实测 raw per_1000 均值 2.02 vs narrative-only 2.02（**均值面不敏感**——污染不改变本语料均值，带判定按章计量）。alarm fatigue 风险：56% 章带 WARN 使 WARN 通道失聪。 |
| 提案 | **选项 A（路由）**：WARN → 报告行（门输出降为 per-chapter 计量报告，不进 WARN 通道）——保留计量、去劝谏噪音；**选项 B（降报告行＋带重标定）**：按真语料分布重设 [2,4] 带后再评估残留 WARN 率；**选项 C（narrative-only 换装）**：计量面换 strip_narrative_body 后口径（M7 对照列已铺设），消除 PRE/POST 污染。 |
| 红测 | `test_simile_flooded_warns_pileup_side`（尾窗追加 6 喻体句→WARN >4 堆叠侧）；选项 A 落地批补：断言报告行存在且 WARN 通道无行。 |
| 回滚 | 路由/带宽回退＝单 commit（带常数与发射臂同文件）。 |

### ending archetype（`G4.cd.ending_diversity`）

| 栏 | 内容 |
|---|---|
| 现状（数字） | `ending_archetype_of` **47/50 返回 None**（未归类收束）——分类器覆盖面 3/50；`G4.cd.ending_diversity` 50 章回放 **0 行发射**（哨兵无数据＝盲哨兵）；WARN-only 发射面。 |
| 提案 | **选项 A（扩分类器）**：按 vol1 实际收束形扩 archetype 词表/结构规则（账目/悬念/情绪等实弹形态），使 None 率降后再评估多样性哨兵判别力；**选项 B（退役哨兵）**：移除 `ending_diversity` 检查（47/50 None 下哨兵恒静默，判别力缺失有数字依据）；**选项 C（维持＋分类）**：`decorative`（须书面机理）至扩分类器批次。 |
| 红测 | `test_ending_repeated_helper_three_ledger_closers`（三连账目收束→helper 级可捕获——分类器对该形态有判别力的存在性证明）；选项 B 落地批＝删门＋baseline 行转 `retired`。 |
| 回滚 | 扩表/退役回退＝单 commit（`ending_archetype_of` 单函数面）。 |

---

## 交裁与落地纪律

- 每项裁定后落「落地批」：改常量/删门＋同步改钉红测＋baseline 行改分类并清
  证据义务（`floor-untested`→红测链接、`retired`→本提案＋裁定记录）；
- 所有阈值/词表改动遵循 #93 threshold-authority 的单源纪律（不另立副本）；
- 跨书语料到位后重跑 `just gate-power <dir>` 刷新「最近回放数」再复核分类
  （单书语料边界，spec 风险节 B5）。
