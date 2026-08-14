# Z7-c 分区初审报告（agent c）— tests/fixtures/ 119 文件

- 日期：2026-08-14
- 范围：`docs/superpowers/audit-runs/2026-08-14/zones/Z7-c.files` 全部 119 文件（31 个 .gitkeep + 88 个数据文件；deep-read 119/119）
- 只读约束：仅执行 read / grep / python3 只读分析 / sha256sum / diff / git log（只读）；未创建/修改/删除任何仓库文件（本段文件除外）；未 git add/commit。
- 编号段：F800–F827（28 条；P1×11、P2×10、M×7）
- 与 Z7-a 重叠说明：Z7-a.files 含 calibration/arc-payoff 全部 15 文件 + resonance/情感落地、文笔质感 6 文件（共 21 个与 Z7-c 清单重叠的 calibration 锚点）。本报告按 Z7-c 清单对 27 个锚点全部做了独立 deep-read；与 Z7-a 的结论交叉引用（T804/T814），phase 4 去重时注意。

## 0. 总体结论

**tests/fixtures/ 是 G0.9 声称（"exclusively real skill outputs or upstream-generated copies (G0.9 prohibits hand-crafted mocks)"，AGENTS.md:97）与仓库实际内容严重不符的重灾区。** 本区 88 个数据文件中，至少 **44 个（50%）** 判定为手写 mock/伪造/自述非真实输出（chapter-2..10-draft 9、chapter-7/8/9-example 3、snapshots/chapter-025 6、calibration 27 中 26 个锚点正文 + README 自违——按文件计 27、arc/book-spine/book-strata/volume-summary 4 自述 format-reference），与 T8 线程 49/88（56%）结论一致（差异源于部分文件重复计数方式）。逐文件证据见下文。

核心横切问题（全部经本区独立验证，多数与 T8 线程结论吻合）：

1. **章节草稿族整体伪造（F800–F802）**：`chapter-draft-example.md`（219 行，第1章全稿）是唯一"完整"版本；`chapter-2..10-draft.md`（9 个）是它截断到 150 行 + 仅改 H1 标题（"第N章：最新章节"——模板占位标题）的副本；`chapter-7/8/9-example.md`（3 个）是截断到 80 行的副本（H1 改回"毕业即失业与穿越即负债"）。sha256 验证：ch7==ch8==ch9（`df81acba…`，**三个逐字节相同，T8 只报告了 8==9**）；ch2..10 的 diff 仅 `10c10`（H1 行）。所有副本 PRE_WRITE_CHECK 自述"近3章结尾方式: N/A（第一章）"。
2. **同一文件身份漂移（F802）**：`chapter-draft-example.md` 被 127 处 scenario 引用为 chapter 2/3/4-6/7/8-10/9/11/17/20…（互相矛盾；review-continuity bug-hunt 甚至把同一文件同时充当 chapter 2 和 chapter 3），而 `audit-report-example.md` 自述"第1章"、`chapter-plan-example.md` frontmatter `chapter: 1`、`chapter-summaries-example.md` 记为"第1章"。文件自身 H1 与第2章草稿漂移（ch2-draft"第2章：最新章节" vs example"毕业即失业与穿越即负债"）。
3. **伪造快照（F806）**：`snapshots/chapter-025/` 的 manifest 用占位 checksum（`sha256:abc123`/`sha256:xyz789`）、`files:` 引用不存在的 `chapters/chapter-1.md`/`chapter-25.md`；truth 5 文件中有 4 个与顶层 `truth-*.md` **逐字节相同**（`ee8b44…`/`0b2006…`/`417c6a…`/`8faa49…`，`last_chapter: 1` 的第1章数据），仅 current_state 被改写成第25章样式；manifest 声称"第25章/~125,000 字/铁砧镇"与内容（第1章锈泥巷）自相矛盾。该快照被 `shenbi-sequel-writing` generative scenario 当作"25 章后断点快照"喂给续写 agent。
4. **calibration 27 锚点手写（F807–F810）**：commit `14a672e`/`adbe2f8` 自述 "Author 12 human-curated … ~150-word **original Chinese fiction prose excerpt**"；锚点 lore（老周/黑石饼/锈泥巷/灵能催化剂/我替你还）在 shipped 内容（multi-chapter 语料的真实 canon 为田国栋/陈阿满/法西斯）零命中，全仓仅出现在 calibration 锚点 + review-resonance/review-arc-payoff 的 scenario 与 expected-output 中（**场景与锚点互相引用自创 lore 形成闭环**，clean scenario 甚至把与锚点同款的"老周脸/黑石饼/我替你还"prose 直接内嵌进 scenario 作为"被评估的成稿"——F803）；违反 calibration README 自身 schema（"Never invented or hand-crafted for the test; always a genuine passage from a shipped chapter"）；G0.14 把 27 个手写锚点哈希锁进 `tests/tiers/deps.json`（本区按 g0.py 算法重算 `274e76d0…` 与锁值**匹配**，即假基准已固化进门禁）。
5. **死 fixture（F813/F824/F827）**：全库无任何特定引用的 21 个文件——chapter-2..10-draft（9，同时伪造）、chapter-8-example、market-data-example.md、multi-chapter-example.md、parent-canon-example.md、truth-chapter_summaries/emotional_arcs/particle_ledger/character_matrix（4）、world-rules/locations/power-system/story-bible-example（4）。arc/book-spine/book-strata-example 仅被归档 plan 引用（`2026-06-28-hierarchical-system-wave2-memory.md`）与 lint 脚本硬编码（F811）。
6. **空目录被引用（F814）**：19 个仅含 .gitkeep 的目录被 20+ scenario 引用（truth/ 22 处、truth/character_profiles/ 6、characters/ 6、chapters/ 4、samples/reference-texts/ 3、world/factions/ 2、snapshots/chapter-030/ 2 等）；G0.9 门只校验路径前缀（g0_purity.py:33-38 正则 `ref.startswith("tests/fixtures/")`），不校验存在性/真实性。
7. **scenario 与 fixture 断链（F803/F804/F805/F819/F826）**：多个 bug-hunt/clean scenario 的植错前提与实际 fixture 内容不符——chapter_role 声称"高潮/兑现"实际 plan 为"推进/转折"；声称"无 PRE_WRITE_CHECK"（有）、"然而×4/不过×3/与此同时×2"（实际正文 0/0/0）；声称 sensitive_words.txt 含傻逼/白痴/脑残（实际 台独/藏独/法轮功 3 词）；声称 novel-example.json 指定 `target_platform: "qidian"`（实际无此字段）；snapshot-manage bug-hunt 声称快照"8/11 files、manifest claims 11"（实际 5 个 truth 文件、manifest files 列 5 条）；review-arc-payoff 声称 outline-example.md 有 `arc_beats`、truth-pending_hooks 有 hook-007/老周/黑石饼（实际 outline 无 arc_beats、truth 只有 hook-ch1-001..003）。
8. **合规点（正面验证）**：`outline-example.md` root 与 fixture 逐字节一致（`12c31001…`，G0.11 PASS）；`report-example.txt` 为真实公有领域文本（《钢铁是怎样炼成的》中文版，commit 34c3d75）；`mlc-config.json` 为真实工具配置（唯一消费者 tests/integration/test_doc_links.py）；31 个 .gitkeep 全部 0 字节；中文路径 calibration 目录存在性与 G0.14 哈希当前匹配（Windows CRLF 重 lock 漂移风险见 T815，本区不重复）。

---

## 1. 逐文件 deep-read 报告

### tests/fixtures/.gitkeep（31 个，全部 0 字节）
- 处置: deep-read（存在性 + 0 字节 + 目录被引用性）
- 文件清单：`tests/fixtures/.gitkeep`、`audits/`、`calibration/`、`chapters/`、`characters/`、`characters/supporting/`、`config/`、`config/platform-rules/`、`consolidation/`、`consolidation/volume-1/`、`drafts/`、`import/`、`import/analysis/`、`import/canon/`、`import/packaging/`、`samples/`、`samples/reference-texts/`、`skill-triggering-prompts/`、`snapshots/`、`snapshots/chapter-025/`、`snapshots/chapter-030/`、`snapshots/pre-chapter-25/`、`source/`、`story/`、`story/volumes/`、`truth/`、`truth/character_profiles/`、`truth/source_material/`、`world/`、`world/factions/`、`world/locations/`
- 声称检查的不变量:
  - 全部存在且 0 字节（`find` + `wc -c` 逐一验证）✓
  - 目录为 Git 占位（git 跟踪空目录需要 .gitkeep）✓
  - 目录被 scenario 引用为输入 ✗ → F814（19 个空目录被 tests/tiers 引用：truth/ 22、truth/character_profiles/ 6、characters/ 6、chapters/ 4、samples/reference-texts/ 3、world/factions/ 2、snapshots/chapter-030/ 2、import/packaging/ 2、import/canon/ 2、drafts/ 2、world/locations/ 1、truth/source_material/ 1、story/volumes/ 1、source/ 1、snapshots/pre-chapter-25/ 1、skill-triggering-prompts/ 1、consolidation/volume-1/ 1、config/platform-rules/ 1、audits/ 1）
- findings: [F814]
- 验证命令: `find tests/fixtures -name ".gitkeep" | while read f; do wc -c "$f"; done`（31 个全 0）；`grep -rl "tests/fixtures/<dir>" tests/ skills/`（计数如上）
- 置信度: high

### tests/fixtures/arc-example.md
- 处置: deep-read
- 判定: **自述非真实输出（format-reference）**；`arc: 1, chapter_range: 1-12, volume: 1`；零活引用（仅归档 plan `2026-06-28-hierarchical-system-wave2-memory.md` + lint 脚本硬编码）
- 声称检查的不变量:
  - 文件头 G0.9 note 自述 "This fixture is a format reference for scoring skill inputs, not a hand-crafted mock of skill output. Real outputs will replace it" ✗（自认非真实输出，却作为 lint_contract_fields 基准）→ F811
  - 与 volume-summary/book-strata 的卷章节范围一致 ✗（1-12 vs 1-15 vs 1-36）→ F812
  - 正文（梵光社会主义/林烽觉醒/第7章转折）与 outline-example 宇宙一致 ✓
- findings: [F811, F812]
- 验证命令: `read`（28 行全文）；`grep -rln "tests/fixtures/arc-example" .`（仅归档 plan + scripts/lint_contract_fields.py:64）
- 置信度: high

### tests/fixtures/audit-report-example.md
- 处置: deep-read
- 判定: 内容自洽的"审计报告"示例（第1章），与 chapter-draft-example 一致；但被 review-sensitivity 场景当作"漏报白痴词的审计报告"使用 → 断链
- 声称检查的不变量:
  - 自述"第1章 — 毕业即失业与穿越即负债"、审计目标 `chapter-draft-example.md` ✓（与 chapter-draft-example H1 一致，反证 F802 的身份漂移）
  - 报告引用的章内证据（催收员台词、条例、钩子）与 chapter-draft-example 正文一致 ✓（抽查"一百二十银盾/四十七银盾三铜币/第三十一条"均可在正文找到）
  - 字数"5403字"与 chapter-draft-example 自检"~3100字"矛盾 ✗ → F817
  - 行号"行 59"引文实际在 chapter-draft-example:68（偏移 ~9 行，疑似基于不同版本快照）✗ → F817（附注）
  - review-sensitivity bug-hunt 场景声称该报告"未 flag 第6章第9段的'白痴'"——报告与章节均无白痴 ✗ → F804
- findings: [F804, F817]
- 验证命令: `read` 全文；`grep -n "了" chapter-draft-example.md`（行 68）
- 置信度: high

### tests/fixtures/author-intent-example.md
- 处置: deep-read
- 判定: 内容自洽的作者意图（15 章浓缩版），与 outline-example/短篇宇宙一致；15 处引用；无造假证据（弱证据历史 fixture）
- 声称检查的不变量:
  - "15章浓缩版：聚焦主角从利己主义到革命觉醒的核心弧线" 与 short-story-map-example（15 章）一致 ✓
  - 创作约束（三幕/老政委师徒/共情觉醒）与 outline 三幕结构一致 ✓
- findings: 无
- 验证命令: `read` 全文（21 行）；引用闭包（15 处）
- 置信度: high

### tests/fixtures/book-spine-example.md / book-strata-example.md / volume-summary-example.md
- 处置: deep-read（3 文件合并条目）
- 判定: **自述非真实输出（format-reference）**；互相矛盾的章节范围
- 声称检查的不变量:
  - 三文件均带 "G0.9 note: format reference … not a hand-crafted mock … Real outputs will replace it" ✗ → F811
  - book-spine `total_chapters: 15`、volume-summary `chapter_range: 1-15` vs book-strata `chapter_range: 1-36`（同为"第一大弧/第一卷"）✗ → F812
  - 世界铁律（灵能守恒/知识驱动/种姓/殖民）与 outline 核心规则一致 ✓
  - book-spine 主线钩子 MH01/MH02 与 outline 情节线呼应 ✓（MH01 梵光失败教训=outline 前穿越者遗存）
  - 引用：book-spine/book-strata 仅归档 plan + lint 硬编码；volume-summary **零引用** ✗ → F813
- findings: [F811, F812, F813]
- 验证命令: `read` 全文；`grep -rln` 引用闭包；`grep -n "EXAMPLE_FIXTURES" scripts/lint_contract_fields.py`（:61-64）
- 置信度: high

### tests/fixtures/calibration/.gitkeep / README.md
- 处置: deep-read
- 判定: README 过期且与仓库现状自相矛盾
- 声称检查的不变量:
  - "No anchors are authored yet — Phase 2/3 tasks create them … this directory contains only this README and `.gitkeep`" ✗（实际 27 个锚点文件存在）→ F809
  - "G0.14 locks the empty-set hash" ✗（实际锁定 27 锚点组合哈希 274e76d0…）→ F809
  - 锚点 schema："a real prose excerpt — the actual text under evaluation. **Never invented or hand-crafted for the test; always a genuine passage from a shipped chapter, imported canon, or fixture**" ✗（27 锚点全部手写）→ F807/F808
  - "Three anchors per dimension … covering the full 0–30 score range"（部分维度 high 上限 15/20/25，未到 30；维度内 low/mid/high 段连续且不重叠——本区核验 band 表自洽 ✓）
  - README 被 8 处引用（含 lock 脚本/tests），自身是 G0.14 语义的文档源 ✓
- findings: [F809]
- 验证命令: `read` 全文；`find tests/fixtures/calibration -type f | wc -l`（28 = README + 27 锚点）；`grep -n "author" README.md`
- 置信度: high

### tests/fixtures/calibration/arc-payoff/伏笔兑现质量/{high,mid,low}.md
- 处置: deep-read（3 文件合并条目；均全文读取）
- 判定: **手写 mock 锚点**（老周/黑石饼/灵能催化剂 lore 全仓仅 calibration+scenario 命中；正文为"叙述+评论"混合体）
- 声称检查的不变量:
  - schema 三节（excerpt/expected_band/rationale）结构存在 ✓
  - band：high→20-25、mid→11-19、low→0-10（连续不重叠 ✓）
  - excerpt 为"shipped chapter 原文" ✗（第三卷矿道坍塌/老周之死/黑石引灵事件在 shipped 语料零存在；multi-chapter 语料 canon 为田国栋/陈阿满）→ F807
  - excerpt 为"prose 原文"（部分为评论体：low/mid 段"伏笔追踪表上倒是规规矩矩标了 RESOLVED"等是审查语言非小说正文）✗ → F808
  - 锚点引用：仅目录级（`calibration/arc-payoff/` 与 `**/*.md` glob）✗ → F810
- findings: [F807, F808, F810]
- 验证命令: `read` 三文件全文；`grep -rl "老周\|黑石" tests/ skills/ src/`（仅 calibration + review-arc-payoff/review-resonance scenario+expected）；`grep -A2 "expected_band" 各文件`
- 置信度: high

### tests/fixtures/calibration/arc-payoff/弧情感交付/{high,mid,low}.md
- 处置: deep-read（3 文件合并条目）
- 判定: **手写 mock 锚点**（正文为 prose 摘录样式，但仍是自创 lore）
- 声称检查的不变量:
  - 结构三节 ✓；band：high→20-25、mid→11-19、low→0-10 ✓
  - 正文为 prose（林烽催收窗口读契约场景）——形式上符合"摘录"但事件（催收窗口读全文/老周/黑石饼）在 shipped 章节零命中 ✗ → F807
  - high 锚点 prose 与 review-resonance clean scenario 内嵌的"climax passage"高度同源（老周的脸/黑石饼/我替你还）→ 场景与锚点互相印证的自创 lore 闭环 ✗ → F803/F807
- findings: [F803, F807]
- 验证命令: `read` 全文；与 clean scenario 内嵌 prose 比对（grep "我替你还"）
- 置信度: high

### tests/fixtures/calibration/arc-payoff/期待债务结算/{high,mid,low}.md、线索收束/{high,mid,low}.md、角色弧推进/{high,mid,low}.md
- 处置: deep-read（9 文件合并条目；band 表已全部提取）
- 判定: **手写 mock 锚点，且正文为评论体而非 prose 摘录**（9 个文件全部是"本卷…"的元评论，无任何小说正文）
- 声称检查的不变量:
  - 结构三节 ✓；band 连续不重叠（期待债务结算 0-6/7-11/12-15；线索收束 0-8/9-15/16-20；角色弧推进 0-6/7-11/12-15）✓
  - excerpt 为 prose 原文 ✗（全部为评论/概述体："本卷净偿还了读者期待…"）→ F808（9 个文件全部违反）
  - 内容为真实弧/卷事件 ✗（老周黑石饼/催收员身份/灵脉均不在 shipped 语料）→ F807
- findings: [F807, F808]
- 验证命令: `read` 各文件 excerpt 段；band 提取脚本
- 置信度: high

### tests/fixtures/calibration/resonance/情感落地/{high,mid,low}.md、文笔质感/{high,mid,low}.md、场景临场感/{high,mid,low}.md、读者回报/{high,mid,low}.md
- 处置: deep-read（12 文件合并条目；与 Z7-a 重叠的 6 个同样复核）
- 判定: **手写 mock 锚点**（12 个正文均为 prose 摘录样式，但 lore 全为自创：老周/黑石饼/锈泥巷/灵能修炼贷款/催收员）
- 声称检查的不变量:
  - 结构三节 ✓；band 连续不重叠（情感落地 0-12/13-23/24-30；文笔质感 0-10/11-19/20-25；场景临场感 0-10/11-19/20-25；读者回报 0-8/9-15/16-20）✓
  - excerpt 为 shipped 原文 ✗（老周之死场景/锈泥巷晨景/读者回报段均不在任何 shipped 章节；章节语料为多主角 canon）→ F807
  - 12 个文件正文与 review-resonance scenario/expected-output 的 lore 完全同源（闭环）→ F803/F807
- findings: [F803, F807]
- 验证命令: `read` 各文件 excerpt；`grep -rl "锈泥巷" tests/fixtures/`（仅 chapter-draft-example 系 + calibration + scenario）
- 置信度: high

### tests/fixtures/canary-3-chapter-seed.md
- 处置: deep-read
- 判定: 内容自洽的金丝雀测试种子（3 章短篇），与 outline 宇宙一致；7 处引用；无造假证据
- 声称检查的不变量:
  - 三章大纲（穿越即负债/废墟中的发现/不再逃避）与 outline 第1-3章及 parent-canon 一致 ✓（outline 第2章"霓虹灯下的烂疮" vs canary"废墟中的发现"——canary 为缩写版，可接受）
  - 金手指设定与 outline 一致 ✓
- findings: 无
- 验证命令: `read` 全文（49 行）；引用闭包（7 处）
- 置信度: medium（历史 fixture，无独立 provenance）

### tests/fixtures/chapter-2-draft.md … chapter-10-draft.md（9 个）
- 处置: deep-read（9 文件合并条目；hash + diff + 抽样全文）
- 判定: **伪造章节草稿**：9 个文件 = chapter-draft-example 截断到 150 行 + 仅 H1 标题不同（"第N章：最新章节"——占位标题）；PRE_WRITE_CHECK 全部自述"第一章"；全库零引用（死+假）
- 声称检查的不变量:
  - 9 个"不同章节"内容互不相同 ✗（sha256 各异但 `diff chN chM` 仅 `10c10`——H1 行）→ F800
  - 各文件标题反映真实章节内容 ✗（H1"第2章…第10章：最新章节"是模板占位；正文是第1章穿越内容，与 outline 第2章"霓虹灯下的烂疮"不符）→ F800
  - PRE_WRITE_CHECK 与章节号一致 ✗（"近3章结尾方式: N/A（第一章）"出现在全部 9 个文件）→ F800
  - 被 scenario 引用 ✗（全库 grep 仅 audit-run 工件自身；tests/skills/src 零命中）→ F813
- findings: [F800, F813]
- 验证命令: `sha256sum chapter-{2..10}-draft.md`（9 个哈希不同）；`diff chapter-2-draft.md chapter-3-draft.md`（仅 10c10）；`diff chapter-draft-example.md chapter-2-draft.md`（10c10 + 151-219 多余）；`grep -rn "chapter-2-draft" tests/ skills/ src/`（0 命中）
- 置信度: high

### tests/fixtures/chapter-7-example.md / chapter-8-example.md / chapter-9-example.md
- 处置: deep-read（3 文件合并条目；hash + diff + 全文读取 ch7）
- 判定: **伪造章节示例**：三个文件**逐字节相同**（`df81acba75e3d59f…`，T8 仅报告 8==9；实测 7==8==9 全同）；= chapter-draft-example 截断到 80 行 + H1 改"毕业即失业与穿越即负债"；ch8-example 全库零引用
- 声称检查的不变量:
  - ch7/ch8/ch9 为三个不同章节成稿 ✗（hash 全同；`diff` 0 行）→ F801
  - 被 context-composing generative 当"recent chapter drafts for ending diversity check"（结局多样性检查需不同结局）✗（三份相同文本无法做多样性检查）→ F801
  - review-resonance generative 声称 ch7-example"with POST_WRITE_SELF_CHECK" ✗（80 行截断版无 POST_WRITE_SELF_CHECK；只有 chapter-draft-example 有）→ F803
  - ch8-example 有引用 ✗（tests/skills/scripts/tools/src 零命中）→ F813
- findings: [F801, F803, F813]
- 验证命令: `sha256sum chapter-7-example.md chapter-8-example.md chapter-9-example.md`（同一哈希）；`diff chapter-7-example.md chapter-8-example.md`（0 行）；`diff chapter-7-example.md chapter-2-draft.md`（10c10 + 81-150 截断）；`grep -rn "chapter-8-example" tests/ skills/ scripts/ tools/ src/`（0 命中）
- 置信度: high

### tests/fixtures/chapter-draft-example.md
- 处置: deep-read（全文 219 行）
- 判定: 完整第1章成稿（唯一"完整"版本），内部自洽、质量较高（POST_WRITE_SELF_CHECK 与实际正文一致：转折词正文 0、AI 标记词正文 0——已逐词核验）；**但被 127 处 scenario 引用为互相矛盾的章节号**（身份漂移）
- 声称检查的不变量:
  - PRE_WRITE_CHECK 核心任务/伏笔/禁忌与 outline 第1章（毕业即失业与穿越即负债）一致 ✓
  - 正文兑现 hook-ch1-001/002/003 ✓（催收员+告示、灵能感知、三处碎片——与 truth-pending_hooks 对应）
  - POST_WRITE_SELF_CHECK 自检属实 ✓（正文"然而/不过/与此同时"0 次；"似乎/仿佛/不由得/不禁"仅在 PRE/POST 检查元数据中出现、正文 0 次——已定位行号）
  - 自述字数"~3100字" vs audit-report"5403字" vs style-profile 第1章"5444字" ✗ → F817
  - 被引用为单一章节 ✗（127 处 scenario 引用，章节号 2/3/4-6/7/8-10/9/11/17/20 互相矛盾；review-continuity bug-hunt 同一文件充当 chapter 2 和 3）→ F802
- findings: [F802, F817]
- 验证命令: `read` 全文；`grep -n "然而\|不过\|与此同时"`（仅行 7 元数据）；`grep -rn "chapter-draft-example" tests/tiers/ | wc -l`（127）；`grep -rhoE "chapter [0-9]+" tests/tiers/ | sort | uniq -c`（2..20 多种章号）
- 置信度: high

### tests/fixtures/chapter-plan-example.md
- 处置: deep-read（全文 135 行）
- 判定: 高质量第1章规划备忘（chapter: 1 / 推进·转折 / 8 节完整），与 chapter-draft-example 一致；但多个 scenario 声称其为"高潮/兑现"章节计划（断链）
- 声称检查的不变量:
  - frontmatter `chapter: 1`、`chapter_type: EXPLORATION`、`chapter_role: 推进/转折` ✓（与 outline 第1章一致）
  - hook 账（open hook-ch1-001 + defer 002/003）与 truth-pending_hooks/章节一致 ✓
  - "不要做"清单与 PRE_WRITE_CHECK 禁忌一致 ✓
  - review-resonance clean/bug-hunt scenario 声称该 plan 声明 `chapter_role: 高潮/兑现` ✗ → F803
  - 行 111 Phase 1 注"pending_hooks.md 为空伏笔池" vs 实际 truth-pending_hooks 有 3 hook（历史声明，Phase 3 已实现）→ 轻微不一致（并入 F818 附注）
- findings: [F803]
- 验证命令: `read` 全文；`grep -n "chapter_role" chapter-plan-example.md`（推进/转折）；`grep -n "chapter_role: 高潮/兑现" tests/tiers/`（仅 scenario 声称）
- 置信度: high

### tests/fixtures/chapter-summaries-example.md
- 处置: deep-read（全文 104 行）
- 判定: 自洽的第1章摘要（与 chapter-draft-example 事件逐条对应）；24 处引用；无造假证据
- 声称检查的不变量:
  - 第1章核心任务/关键事件/出场角色/伏笔与章节正文一致 ✓（抽查 8 条事件全部可在正文找到）
  - "字数: ~3100" 与章节自检一致但与 audit-report 5403 矛盾 ✗ → F817
- findings: [F817]
- 验证命令: `read` 全文；与 chapter-draft-example 正文逐条比对
- 置信度: high

### tests/fixtures/character-profile-example.md
- 处置: deep-read（全文 120+ 行结构扫描 + head 精读）
- 判定: 内容自洽的主角档案（与 outline 主角设定一致）；26 处引用；无造假证据（弱证据历史 fixture）
- 声称检查的不变量:
  - 身份/性格/金手指/恐惧/成长弧线与 outline 主角设定一致 ✓（arc_type GROWTH、梵光覆辙恐惧等）
  - 引用方（scenario）用法与文件定位一致 ✓
- findings: 无
- 验证命令: `read` 结构（## 段清单）；`grep -c "梵光" character-profile-example.md`（3 处，与 outline 一致）
- 置信度: medium

### tests/fixtures/genre-config-example.json
- 处置: deep-read（JSON 解析 + 与真实输出比对）
- 判定: **与真实 genre-config.json（novel-output/xinghuo-ranqiong）结构漂移的示例**——示例键/语言/reviewer 与真实产物不一致，非真实输出副本
- 声称检查的不变量:
  - 与真实输出同构 ✗（chapterTypes 键：示例英文 battle/dialogue/exposition/transition/climax/politics vs 真实中文 战斗/对话/谋略/人物/世界观/过渡；示例多 tropeInventory 键；approval.reviewer 示例 human-partner vs 真实 pipeline-autonomous）→ F820
  - G4 genre_config 校验可消费 ✗（结构差异下 schema 匹配存疑；示例被 17 处引用含 G4/评分场景）→ F820
  - 疲劳词表内容合理 ✓（fatigueWords 与章节 PRE_WRITE_CHECK 的 AI 标记词清单同源）
- findings: [F820]
- 验证命令: `python3` 对比两文件 keys/chapterTypes/approval（novel-output/xinghuo-ranqiong/genre-config.json）
- 置信度: high

### tests/fixtures/import/analysis/03_world.md
- 处置: deep-read（全文 60+ 行）
- 判定: 声称"从第1-25章提取"的世界观反向提取产物，但**仓库无 1-25 章语料**；且同目录 01_parse..08_state 其余 7 个文件不存在
- 声称检查的不变量:
  - 源章节存在 ✗（第1-25章语料不存在；fixture 语料仅第1章 + 1-5 章短稿）→ F815
  - 行号可验证 ✗（第3章 L45-52、第12章 L120-128 等引用的"章节文件"不存在）→ F815
  - 与 import-analysis scenario 闭环 ✓/✗（scenario 声称 chapters/ 有 12 章源稿 + import/analysis/ 有 8 个 pass 文件——实际 chapters/ 空、analysis/ 仅此 1 文件）✗ → F815
  - 内容与 outline 宇宙一致 ✓（锈泥巷/铁砧镇/田国栋/新富族）
- findings: [F815]
- 验证命令: `find tests/fixtures/import/analysis`（仅 03_world.md）；`ls tests/fixtures/chapters/`（仅 .gitkeep）；`read` 全文
- 置信度: high

### tests/fixtures/market-data-example.md
- 处置: deep-read（head 40 行 + 结构扫描）
- 判定: 自述"真实收集数据"（Qidian/Zhihu 2025-2026），**全库零引用（死 fixture）**；数据无法仓库内独立核验
- 声称检查的不变量:
  - 被 shenbi-market-research 消费 ✗（tests/skills/src 零命中）→ F824
  - 数据真实性可核验 ✗（无来源 URL/快照；"玄鉴仙族月票 52358"等数字不可独立验证）→ F824
  - 目标作品字段与 outline 一致 ✓
- findings: [F824]
- 验证命令: `grep -rln "tests/fixtures/market-data-example" tests/ skills/ scripts/ tools/ src/`（0 命中）；`read` head
- 置信度: high

### tests/fixtures/market-data/qidian-urban-fantasy-2026-06.md
- 处置: deep-read（全文 67 行）
- 判定: 声称"Qidian 24h Hot List + Monthly Ticket Rankings"快照；标题/作者为真实网文作品（我在东京当阴阳师/山间月、夜的命名术/会说话的肘子、诡秘之主/爱潜水的乌贼等真实存在），**数字无法独立核验**（弱证据）；6 处引用（shenbi-market-radar generative）
- 声称检查的不变量:
  - 榜单条目为真实作品 ✓（作品/作者名可对照公开信息，本区抽查 5 条均为知名作品）
  - 数字（阅读量/月票）可核验 ✗（无快照源，仓库内无法验证）→ F823
  - 模式分析（饱和元素/趋势）格式自洽 ✓
- findings: [F823]
- 验证命令: `read` 全文；web 常识对照（无法工具验证，标注弱证据）
- 置信度: medium

### tests/fixtures/mlc-config.json
- 处置: deep-read
- 判定: **真实工具配置**（markdown-link-checker ignore/timeout/retry 配置，96 字节）；唯一消费者 tests/integration/test_doc_links.py（路径存在且可用）✓ 合规
- 声称检查的不变量:
  - JSON 合法 ✓；字段与 mlc 工具语义一致 ✓；被引用且路径有效 ✓
- findings: 无
- 验证命令: `read`；`grep -rln "mlc-config" tests/`（test_doc_links.py）
- 置信度: high

### tests/fixtures/multi-chapter-example.md
- 处置: deep-read（全文 58 行）
- 判定: 5 章短稿的索引/矩阵文档，自述"历史测试数据集（round test 已清理）"；**文件本身零引用（死）**，但目录被 review-arc-payoff generative 引用
- 声称检查的不变量:
  - 索引（章数/字数/人物矩阵/伏笔追踪）与 chapter-1..5.md 一致 ✓（抽查：第3章陈阿满处决、第5章老李头牺牲与正文一致）
  - 字数声称（24,180）与实际 CJK 字符数（约 25,760 纯正文）偏差约 6%（不含标点/标记）——索引内自洽（4,572+5,018+4,704+4,624+5,262=24,180 ✓），但无法与任何脚本重算值精确吻合 → F825（弱）
  - 被引用 ✗（文件级零引用；目录级被 1 个 scenario 引用）→ F813
- findings: [F813, F825]
- 验证命令: `read` 全文；`python3` CJK 计数（ch1: 4851 vs 声称 4572）；引用闭包
- 置信度: medium

### tests/fixtures/multi-chapter-example/chapter-1.md … chapter-5.md
- 处置: deep-read（5 文件 head 精读 + diff 抽样）
- 判定: **5 个互不相同、格式自洽的完整章节**（各 189-217 行、6000-7000 字符），为真实 LLM 成稿样态（弱证据：commit 6bab764 批量引入，round 已清理无 provenance）；目录被 review-arc-payoff generative 引用
- 声称检查的不变量:
  - 五章互不相同 ✓（`diff` 各行不同；主角林烽/田国栋/老陈/陈阿满/老李头连续出场）
  - 章内事件与 multi-chapter-example.md 索引一致 ✓（抽查第2章灰旗/第3章不想跪着活/第5章夜袭）
  - 与 calibration 锚点 lore 一致 ✗（锚点"老周/黑石饼/锈泥巷"在此语料零命中——真实 canon 是田国栋/法西斯；锚点宇宙与 chapter-draft-example 同源而非此语料）→ F807（旁证）
  - 章节号连续（第1-5章）且无自相矛盾 ✓
- findings: [F807（旁证）]
- 验证命令: `diff chapter-1.md chapter-2.md | wc -l`（423 差异行）；`head -8` 各文件；`grep -c "田国栋\|陈阿满" 各文件`
- 置信度: medium（弱证据真实历史输出）

### tests/fixtures/novel-example.json
- 处置: deep-read（全文）
- 判定: 最小小说元数据（与 outline 一致）；22 处引用；**无 `target_platform` 字段但 review-sensitivity scenario 声称有**
- 声称检查的不变量:
  - 字段（title/genre/language/status/core_concept/themes/target_word_count/ending_direction/mode）与 outline 一致 ✓
  - review-sensitivity bug-hunt scenario 声称 "novel-example.json specifies `target_platform: "qidian"`" ✗（JSON 无此字段）→ F805
- findings: [F805]
- 验证命令: `read` 全文；`grep -n "target_platform" tests/fixtures/novel-example.json`（0 命中）
- 置信度: high

### tests/fixtures/outline-example.md
- 处置: deep-read（全文 93 行）
- 判定: **合规点**：root `outline-example.md` 与 fixture 逐字节一致（`12c310019712…`，G0.11 PASS，MIRROR_MAP 覆盖）；内容为完整大纲；43 处引用
- 声称检查的不变量:
  - G0.11 哈希一致 ✓（root == fixture，sha256 相同）
  - 章节大纲第1章"毕业即失业与穿越即负债"与 chapter-draft-example H1 一致 ✓
  - 含 `arc_beats` 字段 ✗（review-arc-payoff scenario 声称 "outline-example.md lists arc_beats with hook-007's payoff"——实际 outline 无 arc_beats、无 hook-007）→ F826
- findings: [F826]
- 验证命令: `sha256sum outline-example.md tests/fixtures/outline-example.md`（同 `12c31001…`）；`grep -c "arc_beats\|hook-007" tests/fixtures/outline-example.md`（0）
- 置信度: high

### tests/fixtures/parent-canon-example.md
- 处置: deep-read（全文 25 行）
- 判定: 声称 100 章 parent canon 时间线（仅列第1-3章摘要）；**全库零引用（死）**；100 章声称与 fixture 语料规模不符
- 声称检查的不变量:
  - 第1-3章摘要与 outline 一致 ✓（阿莲/锻钢城/空袭对应 outline 第2-3章）
  - chapters: 100 有语料支撑 ✗（仓库内 100 章书籍不存在）→ F813
  - 被引用 ✗ → F813
- findings: [F813]
- 验证命令: `read` 全文；引用闭包（0）
- 置信度: high

### tests/fixtures/pending-hooks-example.md / pending-hooks-init.md
- 处置: deep-read（全文）
- 判定: pending-hooks-example 与 truth-pending_hooks 同源（3 hook）；pending-hooks-init 为 0 hook 初始态；**同 hook-ch1-001 内容在两份文件间漂移**
- 声称检查的不变量:
  - example 与 truth-pending_hooks 结构一致 ✓（同 hook id/维度/微妙度）
  - hook-ch1-001 content 一致 ✗（example："强制劳役或灵能剥离" vs truth："强制劳役或灵能僭越罪"——同一钩子两种罚则表述）→ F818
  - init 为空池（活跃 0/已解决 0）✓；init 被 5 处引用、example 被 28 处引用 ✓
- findings: [F818]
- 验证命令: `read` 全文；`grep -n "灵能剥离\|灵能僭越" pending-hooks-example.md truth-pending_hooks.md`
- 置信度: high

### tests/fixtures/report-example.txt
- 处置: deep-read（head 20 + tail 5 + git 溯源）
- 判定: **合规点**：真实公有领域文本（《钢铁是怎样炼成的》中文版，874KB 全本），commit 34c3d75 引入；41 处引用
- 声称检查的不变量:
  - 文本真实性 ✓（尼·奥斯特洛夫斯基《钢铁是怎样炼成的》第一章可见；"（全书完）"结尾）
  - 非生成物 ✓（公有领域排版文本，非 skill 输出也非 mock）
- findings: 无
- 验证命令: `head -20`/`tail -5`；`git log --follow -- report-example.txt`（34c3d75）
- 置信度: high

### tests/fixtures/sensitive_words.txt
- 处置: deep-read（xxd 字节 + 行数）
- 判定: 3 词敏感词表（台独/藏独/法轮功），格式正确（每行一个）；**但 G6.12 全文章节扫描近乎空转，且 scenario 声称的词（傻逼/白痴/脑残）不在表内**
- 声称检查的不变量:
  - 格式（每行一词、UTF-8）✓
  - 词表覆盖面（G6.12 扫描用）✗（仅 3 词）→ F821
  - review-sensitivity scenario 声称含傻逼/白痴/脑残 ✗ → F804
- findings: [F804, F821]
- 验证命令: `xxd sensitive_words.txt`（e58fb0e78bac=台独 等）；`grep -c "" sensitive_words.txt`（3 行）
- 置信度: high

### tests/fixtures/short-story-map-example.md
- 处置: deep-read（结构扫描 + 关键节精读）
- 判定: 内容自洽的 15 章短篇大纲（与 author-intent/outline 一致）；11 处引用（short-outline/packaging/drafting 系列）
- 声称检查的不变量:
  - 三幕结构/章节任务与 outline 及 multi-chapter 宇宙一致 ✓（第3章陈阿满处决、第7章田国栋牺牲对应）
  - 卡兰大陆地名与 multi-chapter-example 一致 ✓（chapter-2.md:39 有"卡兰大陆"）
  - 流程记录（生成/复核/修订三步）格式自洽 ✓
- findings: 无
- 验证命令: `read` 结构；`grep -rn "卡兰" tests/fixtures/`（multi-chapter 同源）
- 置信度: medium

### tests/fixtures/snapshots/chapter-025/manifest.md
- 处置: deep-read（全文 32 行）
- 判定: **伪造快照 manifest**：占位 checksum、files 引用不存在的 chapters/、声称第25章/~125,000 字与内容矛盾
- 声称检查的不变量:
  - checksum 为真实哈希 ✗（`sha256:abc123`/`sha256:xyz789` 占位值）→ F806
  - files 引用的文件存在 ✗（`chapters/chapter-1.md`、`chapters/chapter-25.md` 不存在；truth/*.md 存在）→ F806
  - 断点状态与 truth 内容一致 ✗（manifest 声称第25章/铁砧镇/田国栋第7章牺牲；实际 truth 为第1章锈泥巷数据）→ F806
  - 被 sequel-writing generative 当真实断点快照引用（数据污染面）✗ → F806
- findings: [F806]
- 验证命令: `read` 全文；`find tests/fixtures/snapshots/chapter-025`（无 chapters/ 目录）
- 置信度: high

### tests/fixtures/snapshots/chapter-025/truth/{chapter_summaries,character_matrix,emotional_arcs,pending_hooks,current_state}.md
- 处置: deep-read（5 文件；hash + diff + 全文读 current_state）
- 判定: **伪造快照 truth**：4 个文件与顶层 truth-*.md 逐字节相同（第1章数据），仅 current_state 被改写为第25章样式
- 声称检查的不变量:
  - 快照反映第25章状态 ✗（chapter_summaries/character_matrix/emotional_arcs/pending_hooks 与顶层第1章文件逐字节相同——`ee8b44…`/`0b2006…`/`417c6a…`/`8faa49…`；frontmatter `last_chapter: 1`）→ F806
  - current_state 为第25章 ✗/✓（被改写为 last_chapter: 25 + 铁砧镇内容，但字段残缺：无 进行中的情节线/已揭示的伏笔/待解决的冲突/世界状态变化 表——与 truth-current_state 结构不一致）→ F806
  - 与 manifest 一致 ✗（manifest 声称"老政委田国栋第7章牺牲"与 multi-chapter canon 中田国栋为活导师矛盾——跨 fixture 矛盾）→ F806
  - 顶层 truth-* 与快照双份重复存放 ✗ → F816
- findings: [F806, F816]
- 验证命令: `sha256sum`（4 对逐字节相同）；`diff snapshots/.../current_state.md truth-current_state.md`（结构差异）
- 置信度: high

### tests/fixtures/stop_words_zh.txt
- 处置: deep-read（字节 + 行数）
- 判定: **格式违反自身 spec + 零消费者**：单行 47 个逗号分隔词（spec 要求每行一个）
- 声称检查的不变量:
  - 格式符合 spec ✗（1 行、逗号分隔 vs "每行一个停用词"）→ F822
  - 有消费者 ✗（src/tests/scripts 零命中；chapter_loop/volume_align 硬编码停用词集）→ F822
- findings: [F822]
- 验证命令: `wc -l`（1）；`grep -c ","`（1 行含 46 个逗号）；`grep -rln "stop_words_zh" src/ tests/ scripts/`（0）
- 置信度: high

### tests/fixtures/style-profile-example.md
- 处置: deep-read（结构扫描 + 各章统计精读）
- 判定: 自述"历史测试数据集 + 纯统计（零 LLM）"的风格画像（15 章样本）；17 处引用；内部统计自洽（15 章字数合计=83,151 与头部声明一致 ✓），但样本语料不存在
- 声称检查的不变量:
  - 统计自洽 ✓（各章字数 5,444+5,903+…+5,366=83,151 与"样本总字数: 83151"精确一致）
  - 样本章节存在 ✗（15 章样本语料已清理，无法复核统计真实性——弱证据）→ 无独立 finding（并入 F825 类弱证据观察）
  - 第1章字数 5,444 与 chapter-draft-example 自检"~3100"矛盾 ✗ → F817
- findings: [F817]
- 验证命令: `read` 各章统计表；`python3` 求和验证 83,151
- 置信度: medium

### tests/fixtures/truth-chapter_summaries.md / truth-emotional_arcs.md / truth-particle_ledger.md / truth-character_matrix.md
- 处置: deep-read（4 文件合并条目；head + 结构）
- 判定: 第1章 truth 数据（与 chapter-draft-example 宇宙一致），格式自洽；**4 个文件全库零引用（死）**；其中 chapter_summaries/emotional_arcs/character_matrix 与伪造快照的对应文件逐字节相同（F816）
- 声称检查的不变量:
  - frontmatter（last_chapter: 1、filled_by: state-settling、星火燃穹）一致 ✓
  - 与 truth-current_state/truth-pending_hooks 数据一致 ✓（particle_ledger 债务数字 120+47=167 与章节一致）
  - 被引用 ✗（全库仅归档 spec/audit 工件）→ F813
- findings: [F813, F816]
- 验证命令: `read` head；引用闭包（0 活引用）；`sha256sum` 与快照比对
- 置信度: high

### tests/fixtures/truth-current_state.md
- 处置: deep-read（全文 56 行）
- 判定: 自洽的第1章当前状态（与章节正文逐条对应）；8 处引用（含 regenerate-baselines.sh / G2-truth.json 基线）；无造假证据
- 声称检查的不变量:
  - 情节线/角色位置/伏笔/冲突/世界状态与 chapter-draft-example 一致 ✓（本金 120+47 银盾、日千分之三复利、hook-ch1-001..003 微妙度 0.45/0.75/0.80 均与 truth-pending_hooks 一致）
  - `last_chapter: 1` 与内容一致 ✓
- findings: 无
- 验证命令: `read` 全文；与 truth-pending_hooks 微妙度交叉比对
- 置信度: high

### tests/fixtures/truth-pending_hooks.md
- 处置: deep-read（head 30 行 + 结构）
- 判定: 自洽的第1章伏笔池（hook-ch1-001..003）；12 处引用；与 pending-hooks-example 存在同钩子内容漂移（F818）
- 声称检查的不变量:
  - 活跃 3/已解决 0 与章节状态一致 ✓
  - review-arc-payoff scenario 声称含 hook-007/resolved_this_arc ✗（只有 hook-ch1-001..003，全 PLANTED）→ F826
  - 与 pending-hooks-example 的 hook-ch1-001 罚则表述一致 ✗（"灵能僭越罪" vs "灵能剥离"）→ F818
- findings: [F818, F826]
- 验证命令: `read`；`grep -n "hook-" truth-pending_hooks.md`（仅 ch1-001..003）
- 置信度: high

### tests/fixtures/world-rules-example.md / world-locations-example.md / world-power-system-example.md / world-story-bible-example.md
- 处置: deep-read（4 文件合并条目；结构扫描 + head 精读）
- 判定: 内容自洽、与 outline 世界观一致的世界设定文档（铁律 10 条/地点图谱/灵能十阶/世界观圣经）；**4 个文件全库零引用（死）**
- 声称检查的不变量:
  - 世界规则与 outline 核心规则一致 ✓（灵能守恒/知识驱动/种姓禁锢/殖民三支柱）
  - 地点（锈泥巷/锻钢城/千钧之城/白塔议会区/钨灯镇）与 outline 势力对应 ✓（但"锈泥巷位于首都铁脊城第三环"与 truth-current_state 的"梅德兰帝国锈泥巷贫民窟"及快照"铁砧镇"不直接冲突但无法互相印证——弱）
  - 被引用 ✗（tests/skills/scripts/tools/src 零命中）→ F813
- findings: [F813]
- 验证命令: `read` 结构；`grep -rln "world-rules-example" tests/ skills/ scripts/ tools/`（0 命中）
- 置信度: high

---

## 2. Findings（F800–F827）

| ID | 严重度 | 结论 | 证据 |
|---|---|---|---|
| **F800** | P1 | **chapter-2..10-draft.md（9 文件）为伪造章节草稿**：9 个文件 = chapter-draft-example 截断到 150 行 + 仅 H1 标题不同（"第N章：最新章节"占位标题）；PRE_WRITE_CHECK 全部自述"第一章"；与 outline 第2-10章内容不符；全库零引用（死+假） | `diff` 仅 `10c10`；`diff chapter-draft-example.md chapter-2-draft.md`（10c10 + 151-219 截断）；`grep -rn "chapter-2-draft" tests/ skills/ src/` 0 命中 |
| **F801** | P1 | **chapter-7/8/9-example.md（3 文件）逐字节相同**（T8 仅报 8==9）：`df81acba…` 三文件同一哈希；= chapter-draft-example 截断到 80 行 + 改 H1；被 context-composing generative 当"不同章节成稿"做结局多样性检查（三份相同文本无法检查）；**chapter-8-example 零引用** | `sha256sum` 三文件同值；`diff` 0 行；context-composing scenario:6-7；`grep -rn "chapter-8-example" tests/ skills/` 0 命中 |
| **F802** | P1 | **chapter-draft-example.md 身份漂移**：127 处 scenario 引用为 chapter 2/3/4-6/7/8-10/9/11/17/20…（互相矛盾；review-continuity bug-hunt 把同一文件同时充当 chapter 2 和 3）；audit-report-example 自述"第1章"、chapter-plan-example `chapter: 1`；文件自身 H1（毕业即失业与穿越即负债=outline 第1章标题）与"第2章"漂移 | `grep -rn "chapter-draft-example" tests/tiers/ | wc -l`=127；review-continuity bug-hunt:7；audit-report-example:3；outline-example:62 |
| **F803** | P1 | **review-resonance clean/bug-hunt scenario 与 fixture 断链**：声称 plan 声明 `chapter_role: 高潮/兑现`（实际 chapter-plan-example=推进/转折）；把与 calibration 锚点同款的自创 lore prose（老周脸/黑石饼/我替你还）**直接内嵌进 scenario 作为"被评估的成稿"**（该 prose 不在任何 fixture 章节中）；generative scenario 声称 chapter-7-example"with POST_WRITE_SELF_CHECK"（80 行截断版无） | scenario:7/14；chapter-plan-example:16；`grep -c "POST_WRITE_SELF_CHECK" chapter-7-example.md`=0；`grep -rn "我替你还" tests/`（仅 scenario/expected/锚点） |
| **F804** | P1 | **chapter-drafting / review-sensitivity bug-hunt 植错前提不成立**：声称"无 PRE_WRITE_CHECK"（有）、"然而×4/不过×3/与此同时×2"（实际正文 0/0/0）、"第6章第9段'你这个白痴'"（白痴 0 命中）、sensitive_words.txt 含傻逼/白痴/脑残（实际 3 词：台独/藏独/法轮功） | `grep -c "PRE_WRITE_CHECK" chapter-draft-example.md`=1；`grep -o "然而\|不过\|与此同时"` 仅元数据行；`xxd sensitive_words.txt`；`grep -c "白痴" chapter-draft-example.md`=0 |
| **F805** | P2 | **review-sensitivity scenario 声称 novel-example.json 指定 `target_platform: "qidian"`**——JSON 无此字段（键：title/genre/language/status/core_concept/themes/target_word_count/ending_direction/mode） | `read novel-example.json`；`grep -n "target_platform" novel-example.json` 0 命中；scenario:7 |
| **F806** | P1 | **snapshots/chapter-025 为伪造快照**：manifest 占位 checksum（`sha256:abc123`/`xyz789`）、`files:` 引用不存在的 chapters/；truth 5 文件 4 个与顶层第1章 truth-*.md 逐字节相同（last_chapter:1），仅 current_state 改写；manifest 声称"第25章/~125,000 字/铁砧镇/田国栋第7章牺牲"与内容及 multi-chapter canon 矛盾；被 sequel-writing generative 当真实 25 章断点喂续写 agent（数据污染面） | `sha256sum` 4 对相同；`read manifest.md`；`find snapshots/chapter-025`（无 chapters/）；sequel-writing scenario:7,20 |
| **F807** | P1 | **calibration 27 锚点全为手写 mock**：commit 14a672e/adbe2f8 自述 "Author 12 human-curated … original Chinese fiction prose excerpt"；锚点 lore（老周/黑石饼/锈泥巷/灵能催化剂/我替你还）在 shipped 语料零命中（真实 canon=田国栋/陈阿满）；违反 calibration README 自身 schema（"Never invented or hand-crafted"）；**G0.14 将手写锚点哈希锁进 deps.json**（本区按 g0.py 算法重算 `274e76d0…` 与锁值匹配=假基准固化进门禁） | commit message；`grep -rl "老周" tests/fixtures/`（仅 calibration）；g0.py:64-130 算法重算匹配；README.md:20-22 |
| **F808** | P2 | **calibration 锚点 schema 违反之二**：arc-payoff 的 期待债务结算(3)/线索收束(3)/角色弧推进(3) 共 9 个锚点正文为**评论/概述体**（"本卷净偿还了读者期待…"）而非 README schema 要求的 prose excerpt（"the actual text under evaluation"）；伏笔兑现质量 3 个为叙述+评论混合体 | `read` 9+3 文件 excerpt 段；README.md:20-22 |
| **F809** | M | **calibration README 过期自相矛盾**："No anchors are authored yet … contains only this README and `.gitkeep`"、"G0.14 locks the empty-set hash"——实际 27 个锚点存在且哈希被锁定 | `read README.md`:9-11；`find calibration -type f | wc -l`=28 |
| **F810** | P2 | **calibration 锚点零单文件引用**：27 个锚点全部仅目录级/glob 引用（`calibration/resonance/`、`calibration/arc-payoff/`、`**/*.md`），无任何单文件路径引用；9 个 low 锚点无单文件引用 | 引用闭包脚本（27 锚点均只经 dir-prefix 命中） |
| **F811** | P1 | **arc/book-spine/book-strata/volume-summary-example（4 文件）自述非真实输出**（"G0.9 note: … not a hand-crafted mock … Real outputs will replace it"），却作为 scripts/lint_contract_fields.py `EXAMPLE_FIXTURES` 硬编码基准（T302 自洽闭环的基准本身是 mock） | 文件头注释；lint_contract_fields.py:52-64,117-129 |
| **F812** | P2 | **弧系列 fixture 章节范围互相矛盾**：arc-example `chapter_range: 1-12`、volume-summary-example `1-15`、book-strata-example `1-36`、book-spine `total_chapters: 15`——同为"第一大弧/第一卷"，章节数 12/15/36 三方冲突 | `read` 4 文件 frontmatter |
| **F813** | P2 | **21 个零特定引用死 fixture**（全库活代码无引用）：chapter-2..10-draft（9，兼伪造 F800）、chapter-8-example、market-data-example.md、multi-chapter-example.md、parent-canon-example.md、truth-chapter_summaries/emotional_arcs/particle_ledger/character_matrix（4）、world-rules/locations/power-system/story-bible-example（4）。（T8 的 T812 计 28 个含 calibration 9 个 low 锚点——本区按"无任何特定引用"口径为 21；arc/book-spine/book-strata 仅归档 plan + lint 硬编码引用，另计 F811） | 引用闭包脚本（排除 site/audit-runs/.pytest_cache 后逐一 grep 确认） |
| **F814** | P1 | **19 个空目录（仅 .gitkeep）被 20+ scenario 引用**：truth/ 22、truth/character_profiles/ 6、characters/ 6、chapters/ 4、samples/reference-texts/ 3 等；G0.9 只校验路径前缀（g0_purity.py:33-38），不校验存在性/真实性 → generative agent 读到空目录 | `find` 空目录清单 + `grep -rl "tests/fixtures/<dir>" tests/ skills/` 计数 |
| **F815** | P1 | **import-analysis 链断**：import-analysis clean/bug-hunt scenario 声称 chapters/ 有 12 章源稿、import/analysis/ 产出 01_parse..08_state 8 文件——实际 chapters/ 空（仅 .gitkeep）、import/analysis/ 仅 03_world.md；03_world.md 声称"从第1-25章提取"并引用不存在章节的具体行号（第3章 L45-52 等）；bug-hunt expected-output 引用不存在的 02_characters.md/04_plot.md | `ls tests/fixtures/chapters/ tests/fixtures/import/analysis/`；`read 03_world.md`；import-analysis scenario:7 |
| **F816** | P2 | **truth-* 与伪造快照双份逐字节重复**：truth-chapter_summaries/character_matrix/emotional_arcs/pending_hooks 与 snapshots/chapter-025/truth/ 对应文件 4 对逐字节相同（同一第1章数据两处存放，其中一处是伪造快照的一部分） | `sha256sum`（ee8b44/0b2006/417c6a/8faa49 成对相同） |
| **F817** | M | **chapter-draft-example 字数自述矛盾**：POST_WRITE_SELF_CHECK "~3100字"、chapter-summaries-example "~3100" vs audit-report-example "5403字" vs style-profile 第1章 "5444字"；audit 引文行号（行59）与正文实际行号（行68）偏移 | `grep -n "3100\|5403\|5444"` 三文件 |
| **F818** | M | **同 hook-ch1-001 内容双版本漂移**：pending-hooks-example "强制劳役或**灵能剥离**" vs truth-pending_hooks "强制劳役或**灵能僭越罪**"（同一钩子的罚则表述不一致） | `grep -n "灵能剥离\|灵能僭越"` 两文件 |
| **F819** | P1 | **snapshot-manage bug-hunt scenario 植错前提与实际快照不符**：声称快照"contains only 8 of the 11 truth files"、manifest "claims 11 files archived"、缺失 3 个文件（pending-hooks-example/chapter-plan-example/author-intent-example）——实际快照有 5 个 truth 文件、manifest files 列 5 条、被指缺失的文件是顶层 example 而非快照文件；且 scenario 声称的"11 truth files in tests/fixtures/truth/"中多数路径重复且不属于该目录 → 植错测试无法按剧本执行 | `read` scenario.md；`read manifest.md`；`ls snapshots/chapter-025/truth/` |
| **F820** | P2 | **genre-config-example.json 与真实输出结构漂移**：chapterTypes 键英文（battle/dialogue/exposition/transition/climax/politics）vs 真实（novel-output/xinghuo-ranqiong）中文（战斗/对话/谋略/人物/世界观/过渡）；示例多 tropeInventory 键；approval.reviewer 示例 human-partner vs 真实 pipeline-autonomous——示例非真实输出副本 | `python3` 双文件 keys/chapterTypes/approval 比对 |
| **F821** | P2 | **sensitive_words.txt 仅 3 词**（台独/藏独/法轮功），G6.12 全文章节敏感扫描近乎空转；scenario 声称的敏感词（傻逼/白痴/脑残）与文件不符（并入 F804 影响面） | 文件 3 行；`grep -n "sensitive_words" src/shenbi/gates/g6.py` |
| **F822** | P2 | **stop_words_zh.txt 格式违反自身 spec 且零消费者**：spec 要求"每行一个停用词"，文件为单行 47 词逗号分隔；src/tests/scripts 零引用（chapter_loop/volume_align 用硬编码停用词集） | `wc -l`=1；`grep -rln "stop_words_zh" src/ tests/ scripts/`=0 |
| **F823** | M | **market-data/qidian-urban-fantasy-2026-06.md 声称真实榜单数据（弱证据）**：作品/作者为真实知名网文（我在东京当阴阳师/夜之命名术/诡秘之主 等），但阅读量/月票数字无快照源、无法仓库内独立核验 | `read` 全文；唯一消费者 shenbi-market-radar generative scenario |
| **F824** | P2 | **market-data-example.md 自述"真实收集数据"但全库零引用（死 fixture）**；数据（月票 52,358 等）不可核验 | 引用闭包（0）；`read` head |
| **F825** | M | **multi-chapter-example/ 5 章为弱证据"真实历史输出"**（正文互不相同、格式自洽、commit 6bab764 批量引入、round 已清理无 provenance）；索引 multi-chapter-example.md 死文件；字数声称（24,180）与实测 CJK 计数（4,851/5,329/5,042/4,953/5,583）偏差约 6% 但索引内自洽 | `diff` 各章；`python3` CJK 计数；git log 6bab764 |
| **F826** | P2 | **review-arc-payoff bug-hunt scenario 引用 fixture 中不存在的内容**：声称 outline-example.md "lists arc_beats"（outline 无 arc_beats）、truth-pending_hooks "mark hook-007 as resolved_this_arc"（实际只有 hook-ch1-001..003 全 PLANTED）、"hook-007 老周留下的半块黑石饼"（老周/黑石仅存在于手写锚点+scenario 闭环）→ 剧本与 fixture 断链 | `grep -c "arc_beats" outline-example.md`=0；`grep -n "hook-" truth-pending_hooks.md`；scenario:7 |
| **F827** | M | **parent-canon-example.md 死文件**：声称 chapters: 100 的 parent canon，仓库内无 100 章语料支撑；全库零引用（并入 F813 清单） | `read` 全文；引用闭包（0） |

## 3. 覆盖统计

- deep-read 文件数：**119 / 119**（88 个数据文件全部语义深读 + 31 个 .gitkeep 全部存在性/空字节/目录引用性核验）
- 未覆盖文件列表：**空**（无）
- 判定汇总（88 个数据文件）：
  - 手写 mock / 伪造 / 自述非真实输出：**44（50%）**——chapter-2..10-draft（9）、chapter-7/8/9-example（3）、snapshots/chapter-025（manifest 1 + truth 5）、calibration 锚点（27）、自述 format-reference（4）
  - 弱证据"真实历史输出/真实数据"（无 provenance 或不可核验）：**13**——multi-chapter-example/ 5 章、truth-*（6）、market-data/qidian、canary-3-chapter-seed（部分）
  - 真实/合规（可验证）：**7**——outline-example（G0.11 一致）、report-example.txt（公有领域）、mlc-config.json（工具配置）、sensitive_words.txt（真实数据但空转）、stop_words_zh.txt（真实数据但违 spec）、calibration/README.md（文档但过期）、genre-config-example.json（结构自洽但漂移）
  - 其余（内容自洽示例、无造假证据）：24
- 新增 finding：28 条（F800–F827；P1×11、P2×10、M×7）
- 与既有线程 findings 的关系：F800/F801/F802/F803/F804/F806/F807/F809/F810/F811/F813/F814/F815/F816(部分)/F820/F821/F822/F824/F826 与 T8 线程 T801–T816 同根，本报告提供逐文件独立证据并修正两处（① ch7-example 与 ch8/ch9 也逐字节相同（T802 只报 8==9）；② chapter-8-example 零引用（T812 未列））；F805/F808/F812/F817/F818/F819/F823/F825/F827 为本区新增（不在 T8xx 中）。
