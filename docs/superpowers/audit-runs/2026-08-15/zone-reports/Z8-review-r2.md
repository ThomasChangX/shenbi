# Z8 区第 2 轮独立复核报告（review-r2，2026-08-15 轮）

- **复核人**: Z8 独立复核 agent（fresh-context，只读）
- **复核对象**: Z8-a.md（F801–F823）、Z8-b.md（F834–F857）、Z8-c.md（F867–F885）、Z8-review-r1.md（F886–F895）
- **本轮强制新角度**: (a) DOT 流程图节点/边 × 正文步骤节 × frontmatter 契约三方逐技能对照（69/69 含 DOT 技能全量）；(b) 正文内部自洽——正文实际读写文件 vs frontmatter 声明、正文引用的技能名/命令/路径存在性、**updates 目标的运行时写路径接线**
- **编号段**: F824–F829（6 条新 finding；未动用 F896–F899 备用段）
- **只读声明**: 除本文件外未创建/修改/删除任何仓库文件；未 git add/commit；未运行 pytest / shenbi-dispatch / pipeline；novel-output 只读（本轮全部为 grep/sed/read/ls/git-log 只读命令）；机械脚本仅写入 /tmp/z8r2/

---

## 0. 复核方法

1. **DOT 全量抽取**: 69/74 个 SKILL.md 含 digraph（缺失 5 个恰为 r1 F893 所列：4×group-\* + foreshadowing-lifecycle，独立复核一致）。全部 DOT 块抽取至 /tmp/z8r2/dot/ 逐个与正文步骤、frontmatter 对照。
2. **机械对账脚本**（均写 /tmp）: 正文路径提及 vs frontmatter（43 文件命中→人工过滤示例/词表噪声）；DOT 路径 vs frontmatter；writes/updates basename 正文孤儿扫描（排除 AUTO-GENERATED 块）；dict-form fields vs 真实产物节名（novel-output/xinghuo-ranqiong + tests/fixtures 双基准）；updates 目标 vs reads（YAML 正规解析）；全仓 skill 名引用 vs 磁盘目录（comm）；python -m 模块 / src 路径 / helper 函数名存在性。
3. **执行链深读**: dispatch_helper.py 三路由（API/IDE/legacy CLI）× `_write_parsed_outputs` × `_build_skill_prompt` 输入构造 × chapter_loop staging/commit_staging × truth_io upsert 实现 × 全仓 write_truth_file 调用点枚举 + git 历史（76662a5/d4b4e83）考证。
4. **误报复审**: r1 的 10 条 + b 段 24 条中约 30 条逐条重验（行号级 grep/sed），含 r1 自身 M1 误报判定的再复核。

## 1. 总体结论

- 三段初审 + r1 的行号级证据质量**继续维持高**：本轮重验约 30 条 findings（F834–F857 抽验 20+、F886–F895 全部 10 条）**零新误报**；r1 的 M1（Z8-b hook-lifecycle.md "死引用"误报）再复核成立（`ls skills/shenbi-foreshadowing-track/` → SKILL.md + lifecycle-states.md 1882 字节实存）。
- 本轮净增 **6 条**（P1×1、P2×4、M×1）。新产出集中在两个 r1 未覆盖的层面：
  1. **字段级声明的"真实管道产物"基准缺位**（F825/F826/F827）——初审用 fixtures 验证、r1 用磁盘验路径存在性，均未对账节名 vs 真实产物；
  2. **updates 写路径的运行时接线**（F828，本轮最重要）——append_dedup 契约在全仓三条 dispatch 路由上均无 upsert 实现，F868（P0）被证实只是该系统性断线的单例。
- DOT 层面（角度 a 主体）质量总体良好：69 个 DOT 中仅 3 处正文强制步骤缺失（F829，M）+ r1 已立案的 8 处；无"DOT 有正文无"的幽灵步骤（除 F887 已立案的 genesis 派发弃用技能）。

## 2. 漏报（F824–F829）

### F824 | 活跃技能引用幻影 genre-config 键：prohibitions（review-sensitivity，默认审计）+ maxNgramRepetition / coreImages（review-long-span）——schema 硬校验"恰好 8 顶层字段"，键永不可存在 | 漏报 | P2
- 证据: ① `skills/shenbi-review-sensitivity/SKILL.md:41-42`（DOT "Read genre-config.json (prohibitions)"）、`:60`（铁律 4 "genre-config.json 的 prohibitions 列表 = 每章必须为 0"）、`:68`（检查执行 2 "从 genre-config.json 的 prohibitions 读取"）、`sensitive-words.md:77/:87/:122`（三处同一引用；:87 还声称已弃用的 review-anti-ai 与本审计共用该列表）；② `skills/shenbi-review-long-span/SKILL.md:64`（铁律 2 "超出 genre-config.json 的 maxNgramRepetition = error"）、`:81`（"意象词（genre-config.json 的 coreImages 列表）"）、`:47`（DOT "(ngram window + drift threshold)"）；③ 生产者侧 `skills/shenbi-genre-config/SKILL.md` 字段规范表 + `:286`（"**顶层字段数**：恰好 8 个（version, updated, fatigueWords, pacing, chapterTypes, auditDimensions, customRules, approval）"，计数规则 "顶层字段数 ≠ 8 = 不合格"）；④ 真实产物 `novel-output/xinghuo-ranqiong/genre-config.json` 顶层键 = 恰好上述 8 个（python json 实测，嵌套键亦无 prohibitions/maxNgram/coreImages）
- 根因: F1006 家族（eraResearch/eraConstraints）+ F844（pacingRules）+ F914（climaxKeywords）+ F231（povMode）均只覆盖各自技能；`prohibitions`（2 个活跃技能 + 1 个弃用技能 checklist 共 5 文件引用）与 `maxNgramRepetition`/`coreImages`（活跃 long-span）从未入账。review-sensitivity 是 5 个默认常开审计之一（using-shenbi:124），其 4 项核心检查中第 2 项（本书禁忌词，blocking 级）永久空转；long-span 的红线检查（error 级）与意象词提取同样无数据源
- 验证: `grep -rn "prohibitions" skills/ src/ | grep -v audit-runs` → 12 处全部在 skills 侧，src 零实现；`python3 -c "import json; print(list(json.load(open('novel-output/xinghuo-ranqiong/genre-config.json')).keys()))"` → 8 键无一命中；`grep -n "maxNgramRepetition\|coreImages" skills/shenbi-genre-config/SKILL.md` → 0
- 影响面: 由于 8 字段硬校验，即使有人"补写"该键也会使 genre-config 自身不合格——幻影键被双重锁死；默认审计的阻断检查静默失效
- 建议方向: genre-config 落地 prohibitions 生产者（如并入 fatigueWords.禁用 扩展或 customRules 结构化子型）并同步 8 字段计数规则；long-span 的 maxNgramRepetition/coreImages 改为引用实存键或在 genre-config 注册新字段
- 关联修正: F880（style-polishing DOT 引 prohibitions）的修复方向"fields 增加 prohibitions"会制造第二个死字段，应随本条一并裁决

### F825 | foreshadowing-lifecycle 两处契约漂移：volume_map 字段声明为英文 `cross-volume bridges`（真实节名 `### 跨卷桥接`，字段过滤永久 miss）；genesis 模式读 outline/story_frame.md 未声明 reads | 漏报 | P2
- 证据: ① `skills/shenbi-foreshadowing-lifecycle/SKILL.md:10`（`- {file: outline/volume_map.md, fields: [cross-volume bridges]}`）vs 真实产物 `novel-output/xinghuo-ranqiong/outline/volume_map.md` 节名实测（`## 第一卷：…` / `### Key Results` / `### 卷内张力曲线` / `### 跨卷桥接` / `### 黄金三章约束`，grep ^# 实测）与生产者模板 `skills/shenbi-volume-outlining/SKILL.md:200-210`（EXACT 节 `### 跨卷桥接`）——英文字段名对中文节名零命中 → 每次 dispatch field_filter_no_match WARN + 全量 escape hatch；② `:108`（genesis 模式 "reads: outline/story_frame.md + outline/volume_map.md (replaces chapter plan)"）、`:113`（"Read outline/story_frame.md extract three-act cross-volume promises"）vs frontmatter reads（:6-11: plans/chapter-N-plan.md、chapters/chapter-N.md、truth/pending_hooks.md、outline/volume_map.md——无 story_frame.md）
- 根因: F815 五项 + F839（arc-payoff 的 volume_promise/arc_beats）均未覆盖 lifecycle 自己的字段声明；genesis 模式（F887 建议的修复落点）依赖的 story_frame 输入同样断线——若按 F887 把 genesis.py 步骤 9 改派 lifecycle，其 genesis 路径将拿不到 story_frame
- 验证: `grep -n "fields:" skills/shenbi-foreshadowing-lifecycle/SKILL.md`；`grep -n "^#" novel-output/xinghuo-ranqiong/outline/volume_map.md`；机械脚本 /tmp/z8r2/fields_check.py 输出 lifecycle 唯一 miss
- 影响面: lifecycle 是现行伏笔主技能（MERGE-1 后继）；字段 miss 导致 token 浪费 + genesis 修复路径（F887）存在隐藏前置
- 建议方向: fields 改 `[跨卷桥接]`；reads 补 `outline/story_frame.md`（fields: 三幕跨卷承诺 或整读）

### F826 | pending_hooks.md 真实产物为"每章追加日志"结构，与全部活跃字段级消费者声明的账本节名（活跃伏笔/伏笔统计/伏笔时间线）零命中——F845 节名分裂家族在 pending_hooks 上的实例（r1 覆盖空洞#4 疑似项的实证） | 漏报 | P2
- 证据: 消费方（活跃）: `skills/shenbi-chapter-planning/SKILL.md:14-16`（fields: [活跃伏笔, 伏笔统计]）、`skills/shenbi-context-composing/SKILL.md:37-39`（同）、`skills/shenbi-review-arc-payoff/SKILL.md:11-14`（fields: [活跃伏笔, 伏笔统计, 伏笔时间线]）；（弃用）: foreshadowing-track:8、review-reader-pull。真实产物 `novel-output/xinghuo-ranqiong/truth/pending_hooks.md`（grep ^# 实测）: `# 伏笔追踪` / `## 第56章伏笔呈现` / `### 文本强化确认` / `## 第56章生命周期状态更新（foreshadowing-track）` / `### P0-4 TRIGGER 证据` …——**逐章追加日志**，无任何声明节名；对照 fixture `tests/fixtures/truth-pending_hooks.md:12/:73/:81`（## 活跃伏笔 / ## 伏笔统计 / ## 伏笔时间线——静态账本）与 `tests/fixtures/snapshots/chapter-025/truth/pending_hooks.md`
- 根因: pending_hooks 是 4+ 写者文件（state-settling 追加 / lifecycle append_dedup / 已弃用 track 的每章日志 / resolve 状态更新）且无权威模板；真实管道由弃用 track 写出（标题自证 "（foreshadowing-track）"），与 fixture 账本结构、与 lifecycle 自身输出示例（`skills/shenbi-foreshadowing-lifecycle/SKILL.md:154` PLANTED 表）三方互异。r1 覆盖空洞#4 明确列 pending_hooks 为"疑似同族问题，未验证"——本轮实证
- 验证: `grep -n "^#" novel-output/xinghuo-ranqiong/truth/pending_hooks.md | head` vs 上述消费方 fields；`grep -rn "活跃伏笔" skills/*/SKILL.md | cut -d: -f1 | sort -u` → 8 文件（4 活跃）
- 影响面: 逐章主循环（planning→context-composing）+ 卷级审计（arc-payoff）每次 dispatch 字段过滤 miss → escape hatch + WARN；语义上消费者期待的"账本视图"在真实产物中不存在，LLM 需自行从日志反推
- 建议方向: 裁决权威结构（建议 lifecycle 的账本式 + 每章日志归档节），state-settling/lifecycle/resolve 写入格式对齐后在 `_TRUTH_FILE_TITLES` 模板机制（dispatch_helper.py:1210-1219 已按消费者 fields 并集播种节名）中固化
- 附注: `_collect_declared_truth_fields` 只覆盖 current_state/character_matrix/emotional_arcs/chapter_summaries 四文件，pending_hooks 不在播种范围——结构无锚点，漂移无告警

### F827 | chapter_summaries.md 节名分裂：真实产物为逐章 `## 第N章：…`、无 `已完成章节` 包装节，而活跃消费者 chapter-planning/context-composing 声明 fields [已完成章节]——F845 家族扩展；同时修正 Z8-a F807 "通过项"的 fixture-only 局限 | 漏报 | P2
- 证据: 消费方（活跃）: `skills/shenbi-chapter-planning/SKILL.md:17-19`（fields: [已完成章节]）、`skills/shenbi-context-composing/SKILL.md:34-36`（同）；（弃用/惰性）: review-continuity:15-17、foreshadowing-track:9、group-factual 正文块:54（frontmatter 为整读，块本身是 F841 已立案的惰性残留）。真实产物分裂实测: `novel-output/xinghuo-ranqiong/truth/chapter_summaries.md`（:1 `## 第55章：宣告后周一`、:13 `## 第56章：…`——无 `已完成章节`）vs `novel-output/test-validation/truth/chapter_summaries.md:7`（`## 已完成章节` 存在）vs `tests/fixtures/snapshots/chapter-025/truth/chapter_summaries.md:15`（存在 + `### 第N章` 子节）
- 根因: 与 F845（current_state）同族——多代产物间节名漂移、escape hatch 静默化；Z8-a 对 F807 的通过项验证（"字段全命中真实 fixture :15"）只对 fixture 成立，未对真实管道产物复核
- 验证: `grep -n "^#" novel-output/xinghuo-ranqiong/truth/chapter_summaries.md` vs fixture；机械脚本 fields_check.py 输出
- 影响面: 逐章主循环两个必经技能每次 dispatch 字段 miss → WARN + 全量注入（token 浪费面）
- 建议方向: state-settling 固定输出包装节名（对齐消费者声明并回填真实产物），或消费者改声明为结构无关读取；F807 通过项在台账中补注"fixture-only"限定

### F828 | append_dedup 运行时零接线：三条 dispatch 路由均整文件写、全仓唯一 write_truth_file 调用方是 resonance_trend；18 个 updates 目标不在所属技能 reads，API 路由下盲覆写——F868（P0）为该系统性断线的单例 | 漏报 | P1（P0 边界：state-settling 6 个 truth 文件与 arc-payoff 双文件在 API 路由下为数据丢失级）
- 证据:
  1. **通用写路径整文件写**: `src/shenbi/pipeline/dispatch_helper.py:1095-1185`（`_write_one` → `safe_write(full_path, content)`，literal 契约路径含 updates 路径一律整文件写）；`:1177-1180` 注释自认 "append_dedup is intentionally NOT branched here … truth-file upsert is the caller's job (state-settling skill calls write_truth_file with a real key)"——**该注释所述调用方不存在**：`grep -rn "write_truth_file(" src/shenbi/ --include="*.py" | grep -v def | grep -v truth_io` → 唯一命中 `chapter_loop.py:3051`（仅 resonance_trend.md，review-resonance 步骤后持久化趋势行）；dispatcher CLI（route 3 入口 `shenbi.dispatcher.cli`）无任何 write/upsert 逻辑（grep = 0）
  2. **三路由执行器能力**: `dispatch_skill` 路由序（:1820-1900）①API（`SHENBI_LLM_API_KEY`，:1500-1560 纯 OpenAI 调用，**无文件系统访问**，输入仅来自 `_build_skill_prompt` 注入的 contract reads，:600-660）②IDE CLI（:1738-1815，子进程 agent 有文件访问，可自读补救）③legacy CLI。即 append_dedup 语义在 API 路由下既无 caller upsert、也无 agent 自读可能
  3. **18 个 updates 目标不在 reads**（YAML 正规解析，/tmp/z8r2/updates_reads_yaml.py）: state-settling×6（current_state/particle_ledger/emotional_arcs/subplot_board/pending_hooks/chapter_summaries——reads 仅 chapters/chapter-N.md，git 考证 76662a5 起即如此）、review-arc-payoff×2（arc_payoff_trend、audit_drift）、score-arc×1（audit_drift）、review-resonance×1（audit_drift；resonance_trend 由 caller 保护）、drift-guidance×1（audit_drift）、faction-builder/intent-management/memory-distill/pacing-design/plot-thread-weaver/power-system 各×1（自身领域文件）
  4. **指令面放大**: state-settling 正文 `:55-57` 要求 replace-mode 文件 "output the ENTIRE file content"（API 路由下对不可见文件 = 幻觉重建）；arc-payoff 正文趋势行（:150-155 首列 volume 的追加行指令）+ resonance `:150-152`（"仅 append 本维度短板条目"）在整文件写下 = 行级输出覆盖全文件历史；drift-guidance `:42` 单一写者声明 "读取全部条目并合成最终纠偏指导"——条目所在文件（audit_drift.md）恰不在其 reads，合并输入在 API 路由下不可达
  5. **staging 不缓解**: state-settling 走 staging（chapter_loop.py:577-581），但 `checkpoint.py:32-51 commit_staging` 仍是整文件拷贝（safe_write），无 merge
- 根因: truth_io 的 upsert 原语（`_upsert_markdown_bullet/_upsert_markdown_table_row`，truth_io.py:168-246）已实现，但只在 chapter_loop 的 1 个调用点接线；contract 的 updates 声明被 G0.16 校验后即无运行时语义；dispatch_helper 的注释把设计意图（caller 侧 upsert）当成了已存在的事实
- 验证: 上述 grep/sed 输出；`git show 76662a5:skills/shenbi-state-settling/SKILL.md | grep -A3 reads` → reads 自契约单源化起仅 chapter；真实产物 current_state.md（10KB）含 起始章=42-55 的多周目情节线表——累积结构只能由有文件访问的执行器（IDE 路由）或人工补救产出（项目根 DEBUG_USE_MANUAL_CREATE.md 记录 54 条 retry_feedback、Ch35 state-settling 超时升级），API 路径的盲覆写从未被端到端验证
- 影响面: F868（volume-consolidation P0）修复若只按 r1 建议给该技能补 reads，同机制下 17 个目标仍在；`_upsert_markdown_table_row` 对非 `|` 行降级为纯 append 无去重（truth_io.py:206-209），resonance 的 bullet 短板条目即使接线也不去重
- 建议方向: 三选一并全量适用——①dispatch 通用路径对 `mode: append_dedup` 的 literal updates 路径分支调用 truth_io（键从 contract `key:` 取，键值从行首格取）；②把 updates 目标全部纳入各自 reads（至少保证 IDE/人工路径可见）+ 删除 dispatch_helper:1177-1180 的失实注释；③在 G0.16 增加 "updates 目标必须 ∈ reads 或有登记 caller" 的静态校验。修复验收应包含 "API 路由端到端跑一章 state-settling 后 truth 文件历史行仍在"
- 严重度注: 按 §8.1 "生产契约静默违反（数据丢失级）= P0" 的字面，arc-payoff 趋势行与 state-settling 累积文件在 API 路由下满足；因真实运行疑似走 IDE 路由（有自读补救 + 人工门）且多数目标可再生，整条按 P1 报、P0 边界交终审裁决（与 Z8-c 对 F873 的处理方式一致）

### F829 | DOT 省略正文强制步骤：score-arc 的 audit_drift append、genre-config 的备份步骤、chapter-drafting 的多指标自检 | 漏报 | M
- 证据: ① `skills/shenbi-score-arc/SKILL.md:69`（正文 "对 truth/audit_drift.md 仅 append 弧段评分短板条目"）vs 其 DOT（4 节点：Read inputs → Route C hard-binary → Route C soft-degree → Route A anchor → Write audit report——无 audit_drift 节点；对照 review-resonance 的 DOT 明确画了 "追加 resonance_trend 行" 分支）；② `skills/shenbi-genre-config/SKILL.md:183/:214`（修改流程含 cp 备份 .bak.YYYYMMDD）vs DOT（9 节点无备份节点——备份是 F822 所列两处不一致修复的前置动作，DOT 权威流程缺失）；③ `skills/shenbi-chapter-drafting/SKILL.md` DOT 自检链仅 "Count transition words (1/3000)"，铁律 5/6 + anti-ai-reference.md 的 AI 标记词 ≤1、了字 ≥6 句警告、疲劳词检查均无对应节点
- 根因: DOT 与正文各自演进（F855/F852 同型）；AGENTS.md "DOT flowcharts for authoritative process definition" 下省略即跟随者漏步
- 验证: /tmp/z8r2/dot/shenbi-score-arc.dot.txt / shenbi-genre-config.dot.txt / shenbi-chapter-drafting.dot.txt vs 上述行号
- 影响面: 低（正文指令在场，dispatch 加载全文）；score-arc 漏画的是 drift-guidance 依赖的数据追加步骤，长链路下最易被跳过
- 建议方向: 三处 DOT 补节点；建议 lint 化 "updates 声明 ∩ DOT 节点" 非空校验

## 3. 误报 / 事实修正

### 3.1 整条误报：本轮零新增
重验清单（全部成立）: r1 全部 10 条（F886 genesis-context 零消费 ✓、F887 genesis.py:70 派发弃用技能 ✓、F888 孤儿概念 ✓、F889 ✓、F890 快照 0 目录 ✓、F891 truth/world_rules.md 幻影路径 + 键错位 ✓、F892 check_escalation 六参 vs reads 两源 ✓、F893 恰 5 文件无 DOT ✓（独立复算一致）、F894 五文件空引用句 ✓、F895 yaml 零登记 ✓）；b 段抽验 20+（F834/F873 路由表与 group- 零计数 ✓、F835 ✓、F836 ✓、F837 DOT 标签 ✓、F838 decisions 正文零指令 ✓、F840 key: chapter + :153 volume 首列 ✓、F842/F843/F844（_shared 不存在）✓、F845（xinghuo current_state 节名实测分裂）✓、F846 三套阈值 ✓、F847/F874（5 文件双空格句）✓、F848（15.9-17.9% 标注 >20%）✓、F849（novel.py fanfic=0）✓、F850/:118 三态模板 ✓、F851 ✓、F852 ✓、F853（comm 全仓唯一）✓、F855 ✓、F857 ✓、F868（reads/writes 实测）✓、F869（append_dedup vs replace）✓、F870/:276-277 ✓、F871（trend 仅 2 处机械命中）✓、F875 ✓、F876（2 个铁律节 + 11vs12）✓、F877/F878/F879 ✓、F881 ✓、F883（双"5."）✓、F884（DOT 多章）✓）。

**r1 的 M1 再复核成立**（Z8-b 原文 "track 目录内无 lifecycle-states.md" 为误报；文件实存 1882 字节，hook-lifecycle.md:5/:29 跨目录引用可达）。

### 3.2 事实修正 / 证据增补（不推翻原判）
1. **F880 修复方向修正**: prohibitions 键在 genre-config schema（恰好 8 顶层字段硬校验）中不存在（→F824）。F880 的"fields 增加 prohibitions"会制造死字段；本体判定（DOT vs frontmatter 不一致 P2）维持
2. **F807 通过项限定**: "字段级 reads 全部命中真实 fixture" 属实，但对真实管道产物不成立（chapter_summaries/pending_hooks 双双 miss →F826/F827）；台账应补 fixture-only 注记
3. **F868 根因扩展**: F868 是 F828 系统性断线的单例；只修 volume-consolidation 的 reads 不消除同机制 17 个目标
4. **F887 证据增强**: genesis.py 除 :70（GenesisStep 派发）外，:97 的技能名集合中二次出现 shenbi-foreshadowing-plant（弃用引用共 2 处）
5. **F869 消解路径失效**: Z8-c 引 dispatch_helper.py:1070-1078 注释作为 "append_dedup 由 caller 语义性 upsert" 的消解依据——该注释所述 state-settling 调用方全仓不存在（→F828），F869 的"必有一侧失真"实际是"运行时两侧皆未实现"
6. **F812 关联增补**: drift-guidance :42 "读取全部条目并合成" 的条目载体 audit_drift.md 不在其 reads（→F828 证据 4）

## 4. 覆盖空洞

1. **DOT×正文×frontmatter 三方全量对照此前未做**（本轮 69/69 补做）。结论：DOT 层缺陷密度低于字段层与接线层；后续轮若再审 Z8，DOT 角度边际产出预计趋零，不建议重复。
2. **字段级对账的基准选择**: 初审/r1 分别用 fixture / 磁盘存在性；真实管道产物（xinghuo-ranqiong）的节名基准本轮首次系统使用并即产出 F825/F826/F827。遗留未验: emotional_arcs.md 真实节名 vs review-character/ooc-dimensions 引用（弃用消费者，优先级低）。
3. **updates 运行时接线无人认领**: r1 审到 dispatch_helper 半程（F891 缓存层），Z3-r2 曾立案 "append_dedup 全链路零实现"（F360，src 侧）——但 skills 侧的 18 目标清单、dispatch_helper 失实注释、API/IDE 路由能力差异未入账（F828 补）。终审应把 Z3-F360 与 F828 合并裁决，避免双份修复方案冲突。
4. **score-\* 正文不提主数据源**: score-stratum/score-volume/score-arc 正文仅提 book_spine（:84/:86/:88 "读上级目标"），从不提各自首要输入（book_strata/volume_summaries/arcs）——dispatch 注入兜底故功能无损，文档性软缺口，未占号。
5. **group-\* 正文 Contract 块的字段内容**: 块本身惰性（F841 已立案存在性），其 fields 词表错误（如 factual 块 :54 已完成章节 在真实产物 miss）随块删除自然消解，不另立。
6. **正文提及 vs frontmatter 的机械对账噪声模式**（本轮过滤规则）: 章节示例（chapters/chapter-5.md）、缺陷格式示例（world/magic-system.md 等）、裸文件名 truth 简写、`truth/*.md` glob 覆盖——后续轮可直接复用 /tmp/z8r2/ 脚本 + 本过滤规则。

## 5. 严重度异议表

| Finding | 现级 | r2 意见 | 理由 |
|---|---|---|---|
| F868 volume-consolidation 覆写丢卷摘要 | P0（verified） | **维持 P0**，根因升级为 F828 家族 | 机制本轮代码级复核（reads 缺失 + 整文件写 + 防护仅 chapters/ + staging 无 merge）；但修复验收应扩展为 F828 全量目标，否则修一漏十七 |
| F828（新） | P1 | P0 边界待裁决 | API 路由下 state-settling 6 文件 + arc-payoff 双文件为数据丢失级字面命中；因 IDE 路由自读补救 + 人工门 + 多数目标可再生取 P1 报 |
| F849 fanfic 子模式无生产者 | M（建议复评 P2） | **支持升 P2**（与 r1 一致） | NovelConfig extra:forbid + 零生产者 + 静默回退最严档；激活路径真实存在（mode=fanfic 可配） |
| F874 并入 F847（M） | P2→M | **同意合并** | 同族第 5 例；注意 F874 原判 P2 与 F847 原判 M 的段间不一本身就是 F894 的证据，合并取 M 正确 |
| F845 current_state 节名分裂 | P2 | **维持 P2**；F826/F827 为同族新实例同取 P2 | escape hatch 静默化 + token 浪费，无功能中断 |
| F880 style-polishing prohibitions | P2 | **维持 P2，修复方向修正**（→F824） | 见 §3.2-1 |
| F838 market-radar JSON 校验崩溃 | P1（r1 维持） | **维持 P1** | decisions 正文零指令本轮再证（grep 仅 2 处机械命中） |
| F887 genesis 派发弃用技能 | P1 | **维持 P1，证据 +1**（genesis.py:97） | 见 §3.2-4 |
| F812 drift-guidance | P1 | **维持 P1** | 单一写者声明输入不可达为新增加重证据（F828） |

## 6. 收敛判定

- **本轮**: +6（P1×1 = F828；P2×4 = F824/F825/F826/F827；M×1 = F829）
- **硬收敛**（连续 2 轮 0 新 finding 含 M）: **未达**——r1 +10 → r2 +6，需再连续 2 轮零新增。
- **软收敛**（连续 3 轮无新 P0/P1 且每轮 ≤3）: **BLOCKED 双重不符**——①本轮含新 P1（F828）；②Z8 区存在未解 P0（F868，台账 status=verified 未修复），按规则"含未解 P0 的区禁用软收敛"。
- **波动条款**: r2（+6）< r1（+10），无上行波动，无需波动分析行。
- **轮次建议**: 需 r3；建议定向而非全量——①F828 修复方案跨 Z3（F360）/Z8，应合并裁决后定向复核 updates 全量目标；②字段级真实产物对账的遗留面（emotional_arcs、audit_drift 六写者行格式互溶性中仍开放的 bullet 去重问题）可并入 r3；DOT 角度与三方路径对账（r1）边际产出已趋零，r3 不必重复。
