# Z8 分区初审报告（Z8-b 段）

> 审查人：Z8-b 初审 agent（只读）
> 范围：`skills/` 部分 24 个 skill（清单 Z8-b.files 共 33 文件 = 24 SKILL.md + 6 附属参考 md + 3 .gitkeep）
> 方式：24 个 SKILL.md + 6 个附属文件全部 deep-read；对照 `tests/tiers/deps.json`、`docs/framework/truth-files.index.json`、`docs/framework/decisions-schema.md`、`src/shenbi/gates/g4/`、`src/shenbi/pipeline/{dispatch_helper,chapter_loop,context_assemble}.py`、`src/shenbi/contracts/fields.py`、`src/shenbi/gates/g6_checks.py`、`tools/audit-skill-descriptions.py`、`executor_config.toml`、`tests/fixtures/`、`novel-output/xinghuo-ranqiong/` 交叉验证；`.venv/bin/python tools/audit-skill-descriptions.py` 实测。未运行任何写入仓库的命令（仅写入本段文件 Z8-b.md）。
> 发现编号段：F950–F969。
> 只读声明：除本段文件外未创建/修改/删除任何仓库文件；未 git add/commit。

---

## 0. 总览

- deep-read 文件数：**33 / 33**（清单全部覆盖；24 SKILL.md + 6 附属参考文件全量语义深读，3 `.gitkeep` 零字节文件按结构验证）
- 未覆盖文件：**0**
- findings 数：**20**（P1 × 2，P2 × 10，M × 8）
- 低置信度文件：`shenbi-review-spinoff`（spinoff 专案模式未在 novel-output 中出现过，激活路径无真实运行产物可对照）；`shenbi-character-extraction`（import 路径无真实运行产物）。
- 覆盖缺口（d1-06）处置结论：本清单全部文件存在且可读，无覆盖缺口争议项。
- 与既有审计衔接：F950 与 F0-02 同根（deps.json 契约脱节——F0-02 覆盖"缺 5 个新 skill 登记"，F950 覆盖反面"5 个 DEPRECATED skill 仍登记"）；F969 与 Z11-01 衔接（decisions.json 声明 vs 实际无效产物的 Z8 侧证据）；G6.10 对白占比正则死区与 F952 同源。

---

## 1. findings（F950–F969）

### F950 | DEPRECATED skill 仍登记在 deps.json 调度相位 + executor_config + 审计文件写所有权（deprecation 零 enforcement，"Do not dispatch" 无契约效力） | error | P1
- 证据：`tests/tiers/deps.json` t2-phases：planning 相位 prerequisites 含 `shenbi-foreshadowing-plant`（`:47-48`）、audit 相位 prerequisites 含 `shenbi-review-continuity`、`shenbi-review-dialogue`、`shenbi-review-foreshadowing`、`shenbi-review-reader-pull`（`:81-85` 起）；`executor_config.toml:17-19`（`[overrides."shenbi-review-continuity"] temperature=0.2`）、`:67-68`（`[overrides."shenbi-review-dialogue"]`）；这些 SKILL.md 均含 `<!-- DEPRECATED: Superseded by ... (2026-07-19). --> <!-- This skill is retained for reference. Do not dispatch. -->`（foreshadowing-plant:29-30、review-continuity:24-25、review-dialogue:18-19、review-foreshadowing:18-19、review-reader-pull:17-18）；truth-files.index.json 显示被替换审计文件双写者：`audits/chapter-N-continuity.md` writes = [review-continuity, review-group-factual]、`audits/chapter-N-dialogue.md` = [review-dialogue, review-group-character]、`audits/chapter-N-foreshadowing.md` = [review-foreshadowing, review-group-plan]、`audits/chapter-N-reader-pull.md` = [review-reader-pull, review-group-craft]、`audits/chapter-N-pacing.md` = [review-group-factual, review-pacing]、`audits/chapter-N-world-rules.md` = [review-group-factual, review-world-rules]、`audits/chapter-N-anti-ai.md` = [review-anti-ai, review-group-craft]
- 根因：deprecation 只写在 SKILL.md 正文 HTML 注释里，未同步到契约三源（deps.json / truth-files index 写所有权 / executor_config）；替换 skill（review-group-*）登记缺失（F0-02 已录）使旧名继续占据相位槽位。运行时 `chapter_loop.py:205-226` 实际 dispatch 的是 group-*（9-12 步），与 deps.json audit 相位描述的 18 个旧 skill 完全脱节。
- 验证命令+输出：`python3 -c`（读 deps.json 相位 prerequisites）→ planning 含 foreshadowing-plant、audit 含 5 个 DEPRECATED；`grep -rn "DEPRECATED"` 5 个文件命中；`.venv/bin/python tools/audit-skill-descriptions.py` → OK（无 deprecation 检查）。
- 影响：G5/G6/G7 与 T2 相位链基于 deps.json 校验/编排时按"旧 skill 集"判定（audit 相位校验的产物集合与真实 group-* 运行不符）；契约 lint 对死登记零感知；写所有权模型对同一 audit 文件出现"弃用者 + 替代者"双写者冲突（若 write-audit 强制单写者将误 FAIL 真实 group 路径）。
- 建议方向：deprecation 提升到 frontmatter 字段（如 `deprecated: superseded_by`）+ 契约 lint 拒绝 deps.json 中出现 deprecated skill；从 deps.json audit/planning 相位移除 5 个旧名（连同 F0-02 补登记 group-*/foreshadowing-lifecycle 一并做）；清理 executor_config 旧 override；truth-files index 写所有权同步迁移到替代者。

### F951 | context-composing 写契约断链：主产物 context/chapter-N-context.md 无任何 skill 声明写，frontmatter 只声明 decisions.json；近章结尾检查所需 chapter-(N-3..N-1).md 未入 reads | error | P2
- 证据：`skills/shenbi-context-composing/SKILL.md:46-49`（writes 仅 `context/chapter-N-context-decisions.json`，updates 空）；正文 Pipeline 集成模式 `:116`（"策展后的上下文包覆写到 `context/chapter-N-context.md`"）与 输出格式 `:165-183`（9 节 EXACT 标题，未指明落盘路径）；`truth-files.index.json` → `context/chapter-N-context.md` writes = **[]**、reads = [shenbi-chapter-drafting]（读方有、写方无）；`src/shenbi/pipeline/context_assemble.py:365-370`（`Materialize the context package to context/chapter-N-context.md` —— 仅 pipeline Python 路径产出）；铁律 4 `:125` 与 `:123`（近章结尾多样性必须读 `chapters/chapter-(N-3).md`~`chapter-(N-1).md` 末段）vs frontmatter reads `:45`（仅 `chapters/chapter-N.md` 单文件）
- 根因：LLM skill 路径（非 pipeline 直 dispatch）的主输出文件未进 writes 契约；分层记忆升级后"近章结尾"检查新增了对 N-1/N-2/N-3 章正文的读取，frontmatter 未同步。dispatcher 只把 `contract.reads` 注入输入（`dispatch_helper.py:570-597`），N-3..N-1 章正文不会传给 LLM；铁律 4 要求"严禁以摘要替代" → 该检查在契约层面无法执行（要么拿不到原文，要么触发 escape hatch）。
- 验证命令+输出：`python3 -c`（读 index）→ context/chapter-N-context.md writes=[]；`grep -rn "context/chapter-N-context.md" skills/*/SKILL.md` → 仅 chapter-drafting reads 引用；读 dispatch_helper.py:570-597 确认 reads-only 注入。
- 影响：直 dispatch 模式下上下文包无合法写目标（write-audit 会把落盘判为未声明写）；近章结尾多样性检查（G4 auto-check 不变量 "no 3 consecutive endings" 的数据源）契约缺失，字段过滤/输入注入无法支撑。
- 建议方向：frontmatter writes 补 `context/chapter-N-context.md`（create_or_overwrite）；reads 补 `chapters/chapter-(N-1).md`、`chapter-(N-2).md`、`chapter-(N-3).md`（或 glob `chapters/chapter-(N-3).md`~`chapter-(N-1).md` 的显式形式）；与 F952 一样核对字段过滤对 glob 路径的解析。

### F952 | style_profile.md 字段级 reads 漂移：4 个消费 skill 引用旧节号（11. 综合画像 / 6. 修辞模式 / 9. 对白占比），style-learning 现输出仅 8 节且无对白占比 → 每次 dispatch 触发 field_filter_no_match WARN + 全量 escape hatch | error | P2
- 证据：消费方 frontmatter：`shenbi-chapter-drafting/SKILL.md:16-20`、`shenbi-short-drafting/SKILL.md:16-20`、`shenbi-style-polishing/SKILL.md:12-17`（均含 `11. 综合画像`、`6. 修辞模式`、`9. 对白占比`），`shenbi-review-resonance/SKILL.md:17-18`（`11. 综合画像`、`6. 修辞模式`）；生产方 `shenbi-style-learning/SKILL.md` 输出格式仅 8 节：`## 5. 修辞模式`（`:215`）、`## 8. 综合画像`（`:243`），无 9/11 节、无对白占比；`tests/fixtures/style-profile-example.md:160,232,260`（旧格式 `## 6. 修辞模式`、`## 9. 对白占比`、`## 11. 综合画像`——消费方引用的是该旧格式）；`src/shenbi/contracts/fields.py:44-51`（`_filter_md` 无命中 → `log.warning("field_filter_no_match")` + `return text` 全量）；`dispatch_helper.py:591-592`（`content, _matched = filter_to_fields(...)` 忽略 matched 标志）；`src/shenbi/gates/g6_checks.py:185-188`（G6.10 `dia_pat` 正则仍在找 `对白占比|对话占比` 区间——生产方永不产出）
- 根因：bd135bf（2026-07-08 "add field-level dict-form reads to 12 skills"）按旧 11 节格式写字段引用，style-learning 输出已改为 8 节（b66db4a 起）未同步；对白占比在 8 节格式中删除后，3 个消费方 + G6.10 仍依赖它。字段过滤"未命中 → 返回全文件"的 escape hatch 使漂移静默化（只 WARN）。
- 验证命令+输出：`grep -rn "综合画像\|修辞模式\|对白占比" skills/shenbi-*/SKILL.md` → 消费方 11/6/9 vs 生产方 5/8；`grep -rn "对白占比" src/shenbi/skill_utils/style_learning/` → 0（无生产逻辑）。
- 影响：chapter-drafting/short-drafting/style-polishing 每次 dispatch 读 style_profile 都走 escape hatch——Layer B 字段过滤对 style_profile 完全失效（上下文裁剪目的落空 + WARN 噪音）；G6.10 对白占比维度正则死区（该维度恒 SKIP 或退化为表启发式）。
- 建议方向：统一节号——style-learning 输出 8 节（修辞模式=5、综合画像=8），消费方 frontmatter 字段改为 `8. 综合画像` / `5. 修辞模式` / 新增或恢复 `对白占比` 节（若 G6.10 仍需）；或让 compute_stats.py 补算对白占比并回填 9 节。

### F953 | memory-distill 契约 vs 正文漂移：L4/L5 流程读 author_intent + book_spine + arcs/arc-N.md 均未声明 reads，且 book_spine 仅 updates（create_or_overwrite）无 reads → L5 滚动复核在 dispatcher 契约下拿不到书脊原文（盲写风险） | error | P1
- 证据：`shenbi-memory-distill/SKILL.md` frontmatter reads `:8-12`（chapter_summaries/volume_summaries/pending_hooks/character_matrix，无 author_intent/book_spine/arcs）；DOT `:78`（`"L5 spine review?" -> "Read author_intent + book_spine"`）、`:73`（L4 分支 `"Read L2 arcs + volume_summaries"`）；铁律 4 `:89`（"L5 滚动复核不破坏声明……复核只更新数据字段"）、铁律 5 `:90`（L5 字段分区所有权）；frontmatter updates `:18-20`（book_spine create_or_overwrite）；`truth-files.index.json`：`truth/book_spine.md` reads = [context-composing, score-arc, score-stratum, score-volume]（无 memory-distill）、`truth/author_intent.md` reads 无 memory-distill、`truth/arcs/arc-N.md` reads = [context-composing, score-arc]（无 memory-distill）；`dispatch_helper.py:570-597`（只注入 reads 为输入，updates 只作输出路径 `:657-658`）
- 根因：L5 滚动复核需要读 book_spine + author_intent 才能"更新数据字段"，但契约层（frontmatter → index）未声明这两个 reads；dispatcher 不会把 updates 目标作为输入注入 → LLM 在无书脊原文/作者意图的情况下按 create_or_overwrite 整写 book_spine，与铁律 4"不改声明"直接冲突（盲写可能覆盖声明字段）。L4 的 arcs 输入同理缺失。
- 验证命令+输出：`python3 -c`（读 index）→ book_spine reads/updates 列表、author_intent reads 列表、arcs reads 列表均不含 memory-distill；读 dispatch_helper.py:570-597 + 657-658 确认 updates 不作为输入。
- 影响：memory-distill 的 L5 书脊滚动复核（分层记忆架构 L5 维护者）在真实 dispatch 下无输入可依：要么盲写 book_spine（create_or_overwrite 风险覆盖 book-spine-init 声明值），要么跳过 L5 步骤（铁律 4/5 悬空）。
- 建议方向：frontmatter reads 补 `truth/book_spine.md`、`truth/author_intent.md`、`truth/arcs/arc-N.md`；book_spine 从 updates 的 create_or_overwrite 改为文档化合并语义（见 F954）。

### F954 | book_spine.md 双更新者 + updates 用 create_or_overwrite 模式错配（memory-distill 与 score-stratum 均整写同一 L5 声明文件，正文却声称"只更新数据字段"） | error | P2
- 证据：`shenbi-memory-distill/SKILL.md:18-20` 与 `shenbi-score-stratum/SKILL.md:14-16`（均 `updates: truth/book_spine.md mode: create_or_overwrite`）；memory-distill 铁律 4 `:89`（"复核只更新数据字段，不改声明本身"）与铁律 5 `:90`（"memory-distill 只写数据值；诊断值由 score-stratum 写；声明值由 book-spine-init 初始化"）；`truth-files.index.json` → `truth/book_spine.md` updates = [shenbi-memory-distill, shenbi-score-stratum]；score-stratum 正文无任何"更新 book_spine"的描述（update 契约在正文零说明）；`g0_skill_contract.py:132-134`（模式校验只要求存在 mode 字段，不校验 writes/updates 模式语义 → create_or_overwrite 放 updates 过 lint）
- 根因：三个 skill 共写 book_spine（book-spine-init 声明 / memory-distill 数据 / score-stratum 诊断），其中两个用 create_or_overwrite 整写；update 语义（append_dedup/merge_prose 类合并）与 create_or_overwrite（整文件替换）冲突，契约 lint 无模式语义检查故未拦截；score-stratum 的 book_spine 更新未在正文描述（LLM 不知道要写）。
- 验证命令+输出：`python3 -c`（读 index）→ book_spine updates 双写者；读两 SKILL.md frontmatter 与正文；`grep -n "mode" src/shenbi/gates/g0_skill_contract.py` → 无模式枚举校验。
- 影响：同一文件三个写者、两个整写——若按契约原样执行，L5 书脊声明值（核心冲突/themes/主角弧终点）有被整写覆盖的结构性风险；"只更新数据字段"的正文承诺与 create_or_overwrite 模式互相矛盾，LLM 无可靠指引。
- 建议方向：book_spine 改单一更新者（建议 memory-distill 统一写，score-stratum 改读 + 独立诊断输出），或引入"部分更新"模式（如 `update_fields` 白名单）；lint 增加 updates 模式枚举（仅 append_dedup/merge_prose 类）拒绝 create_or_overwrite；score-stratum 正文补 book_spine 更新描述。

### F955 | snapshot-manage 回滚写面未声明：回滚覆盖项目文件（truth/ + chapters/ + world/ 等）但契约 writes 仅声明 snapshots/chapter-NNN/* | error | P2
- 证据：`shenbi-snapshot-manage/SKILL.md:96-100`（回滚"用 `snapshots/chapter-NNN/` 覆盖项目文件（truth/ + chapters/ + 按快照类型的其他文件）"）；frontmatter writes `:15-18`（仅 `snapshots/chapter-NNN/*`）；`truth-files.index.json` → `snapshots/chapter-NNN/*` writes = [shenbi-snapshot-manage]（无项目文件恢复写声明）
- 根因：回滚的"写"（把快照内容恢复到 truth/chapters/world/outline/plans/style）是主操作却未进 writes 契约；若 write-audit 拦截未声明写（F503 同机制），回滚将被判为未声明写而 FAIL，或绕过审计。
- 验证命令+输出：读 SKILL.md:96-100 + frontmatter:15-18；`python3 -c`（读 index）确认。
- 影响：破坏性恢复操作在写契约外——审计要么误拦截真实回滚，要么回滚绕过写审计（不可追踪）。
- 建议方向：writes 补回滚恢复路径（truth/*.md、chapters/*.md、world/*.md、outline/*.md、plans/*.md、style/*.md，或引入 `restore:` 契约键）；明确"回滚 = 快照目录→项目路径的复制写"。

### F956 | foundation-review reads 缺 genre-config.json（评分程序 §六 tropeInventory 对照源）与 truth/book_spine.md（前置文件验证必需），且正文重复两个"## 输出格式"节 | error | P2
- 证据：`shenbi-foundation-review/SKILL.md` frontmatter reads `:9-14`（world/*.md, characters/**/*.md, outline/*.md, current_state.md, chapter_summaries.md——无 genre-config.json / book_spine.md）；前置文件验证 `:40-51`（`genre-config.json`（genre-config）、`truth/book_spine.md`（book-spine-init）为必需）；评分程序 `:217`（"读取 `genre-config.json` 的 `tropeInventory`，将 `outline/story_frame.md` 的弧节拍对照每个套路的 `signatures`"）；正文 `:95` 与 `:125` 两个 `## 输出格式`
- 根因：评分工作表新增反套路维度（spec §7.2 再平衡）后依赖 genre-config.json，前置验证新增 book_spine 后均未同步 reads；输出格式节重复为演进遗留。
- 验证命令+输出：读 SKILL.md:9-14, 40-51, 217；`grep -c "^## 输出格式" skills/shenbi-foundation-review/SKILL.md` → 2。
- 影响：字段过滤后 LLM 拿不到 tropeInventory → 反套路维度评分依据缺失（评分程序无法执行）；book_spine 缺失时"拒绝审核"判定无法落地（LLM 看不到该书）。
- 建议方向：reads 补 `genre-config.json` 与 `truth/book_spine.md`；合并重复输出格式节。

### F957 | review-group-factual description 违反触发条件性契约（描述"做什么/机制"而非"何时用"，lint 盲区放行） | error | P2
- 证据：`shenbi-review-group-factual/SKILL.md:3`（`description: Grouped audit for factual consistency -- continuity, world rules, and pacing in one call; dispatches as a parallel wave via parallel_dispatch.py`——无 "Use when"，描述机制含 "in one call"、实现文件 parallel_dispatch.py）；AGENTS.md 契约（"description: ONLY when-to-use trigger conditions…Never describes what the skill does"）；`src/shenbi/gates/g0_skill_contract.py:25-40`（`_BEHAVIORAL_MARKERS` 仅 startswith 匹配 "this skill/generates/writes/creates/validates/checks/analyzes/computes/extracts" 等，无 "grouped audit/dispatches" 标记）
- 根因：description 写成行为+实现描述；lint 只查前缀行为词，未查"含实现细节/非触发句式"，盲区放行；`.venv/bin/python tools/audit-skill-descriptions.py` → OK 实测证实。
- 验证命令+输出：`.venv/bin/python tools/audit-skill-descriptions.py` → `OK: all descriptions compliant`；读 `_BEHAVIORAL_MARKERS` 确认无覆盖。
- 影响：触发式调度（description 驱动 skill 选择）在 group-* 系列最核心的一个 skill 上失真——读者/调度者无法从 description 判断何时该用它（"when a finished chapter needs continuity/world-rules/pacing audits in one pass"）；同类隐患（描述含实现注记）见 F966。
- 建议方向：改为触发式（"Use when a finished chapter needs continuity, world-rules, and pacing audits in a single pass (grouped parallel dispatch)"）；lint 增加"description 含实现路径/机制词"检查（如 parallel_dispatch.py、in one call、MERGE-2）。

### F958 | review-group-factual 正文 Contract YAML 与 frontmatter 矛盾（writes↔updates 互换），且正文引用陈旧代码行号 chapter_loop.py:1090-1168 | error | P2
- 证据：`shenbi-review-group-factual/SKILL.md:49-65` 正文 Contract 块：`writes: []`、`updates: [audits/chapter-N-continuity.md, audits/chapter-N-world-rules.md, audits/chapter-N-pacing.md]`；frontmatter `:16-23` 反之（`writes` = 三个 audit 文件 create_or_overwrite、`updates: []`）；truth-files.index.json → `audits/chapter-N-continuity.md` writes = [review-continuity, review-group-factual]（与 frontmatter 一致，正文块为陈旧）；Dispatch note `:45`（"invoked at `chapter_loop.py:1090-1168`"）——实际并行审查波在 `chapter_loop.py:2514-2614`（`parallel_review_wave1_start` 等）与 `parallel_dispatch.py:150`（`dispatch_reviews_parallel`），`:1090-1095` 是 checkpoint/state-settling staging 逻辑
- 根因：正文内嵌 Contract YAML 未随 frontmatter 单源迁移更新（正文块是迁移前旧版）；行号引用未随 chapter_loop 重构更新。
- 验证命令+输出：`sed -n '49,65p'`（正文块）+ 读 frontmatter:16-23 对比；`grep -n "parallel_review_wave1_start" src/shenbi/pipeline/chapter_loop.py` → 2567；`grep -n "def dispatch_reviews_parallel" src/shenbi/pipeline/parallel_dispatch.py` → 150。
- 影响：LLM 读到与 frontmatter 矛盾的 Contract 会按错误写语义执行（三个 audit 报告可能被当作"update"而非"write"处理）；行号引用误导维护者定位并行调度代码。
- 建议方向：删除正文 Contract YAML 块（以 frontmatter 单源为准，保留指向 auto-generated 契约的注释）；行号引用改为函数名（`parallel_dispatch.dispatch_reviews_parallel`）。

### F959 | volume-consolidation 写模式与正文矛盾（volume_summaries.md create_or_overwrite vs "追加"）+ 重复"## 输出格式"节 + 执行步骤编号重复 | error | P2
- 证据：`shenbi-volume-consolidation/SKILL.md:11-13`（`writes: truth/volume_summaries.md create_or_overwrite`）；正文 `:72`（"追加到 `truth/volume_summaries.md`（如果不存在则创建）"）、`:169`（"追加到 …必须严格遵循以下格式"）、`:114`（"追加到 `truth/volume_summaries.md`"）；`:68` 与 `:165` 两个 `## 输出格式`；执行步骤 `:112` 与 `:113` 连续两个 "5."（归档 / 生成卷级长程记忆）后接 6-9
- 根因：卷摘要演进为多卷累积文件后正文改为"追加"语义，frontmatter 仍 create_or_overwrite——若按契约整写，历史卷摘要被覆盖（与 context-composing 读 volume_summaries 的跨卷依赖冲突）；重复节/编号为演进遗留。
- 验证命令+输出：读 SKILL.md:11-13, 68, 72, 112-114, 165, 169；`grep -c "^## 输出格式"` → 2；`grep -c "^5\."` → 2。
- 影响：多卷小说中 volume_summaries.md 为累积归档，create_or_overwrite 整写会丢历史卷摘要（长程记忆断裂）；重复节/编号误导 LLM 输出结构。
- 建议方向：volume_summaries.md 改 `updates: append_dedup`（key: volume）或明确"整写含历史卷"语义；合并输出格式节；修复步骤编号。

### F960 | anti-detect 触发输入（anti-ai 审计报告）未入 reads，genre-config.json 声明读而正文零使用 | error | P2
- 证据：`shenbi-anti-detect/SKILL.md` description `:3-6`（"Use when anti-AI audit flags a chapter with critical/blocking-level detectability markers"——触发源是审计报告）；frontmatter reads `:9-11`（仅 `chapters/chapter-N.md` + `genre-config.json`，无 `audits/chapter-N-anti-ai.md`）；DOT `:42`（"Identify AI markers (anti-ai checklist)"——需审计标记清单）；正文 9 手法与汇总模板 `:104-145`（需"触发原因: anti-ai 审计发现 X 个 AI 标记"、"审计前后对比"数据）——这些数据只能来自审计报告；`truth-files.index.json` → `audits/chapter-N-anti-ai.md` writes = [review-anti-ai, review-group-craft]（存在但 anti-detect 不读）；genre-config.json 在正文/汇总/手法中零引用
- 根因：触发条件与汇总模板都依赖 anti-ai 审计输出，但审计报告未声明为 read（LLM 拿不到"哪些标记、什么严重度"）；genre-config 为历史遗留声明。
- 验证命令+输出：读 SKILL.md 全文 grep "genre-config" → 仅 frontmatter/auto 契约出现；`python3 -c`（读 index）确认 audits/chapter-N-anti-ai.md 存在写者。
- 影响：anti-detect 无法知道"审计标记了哪些位置/哪些手法命中"（触发数据源缺失），改写报告中的"审计前后对比"只能自造；genre-config 读浪费输入预算。
- 建议方向：reads 补 `audits/chapter-N-anti-ai.md`（触发审计报告）；删除未用 genre-config.json 或正文补用法。

### F961 | short-drafting 字数下限依赖 novel.json.target_word_count 但 novel.json 未入 reads | error | P2
- 证据：`shenbi-short-drafting/SKILL.md:153`（"**字数最低要求**：从 `novel.json` 的 `target_word_count` 除以章节数计算每章最低字数"）；frontmatter reads `:8-20`（short_story_map.md、author_intent.md、genre-config.json、style_profile.md——无 novel.json）；可自动检查规则 `:174`（"每章字数 ≥ floor（target_word_count / 章节数）"）
- 根因：字数门槛规则依赖 novel.json 数值，但契约 reads 漏登记（对照同型 chapter-drafting 也没有 novel.json——该字段由 genre-config 或 plan 携带？novel.json 是唯一声明 target_word_count 的文件，`truth-files.index.json` novel.json reads 无 short-drafting）。
- 验证命令+输出：读 SKILL.md:8-20, 153, 174；`python3 -c`（读 index）novel.json reads 列表无 short-drafting。
- 影响：LLM 无 target_word_count 输入 → 每章最低字数无法计算，"每章字数 ≥ floor" 规则悬空（自动检查项失去数据源）。
- 建议方向：reads 补 `novel.json`（字段 target_word_count）或把字数下限写入 plan/大纲文件。

### F962 | 三个 review skill 的"缺陷证据格式"引用主体缺失（"遵循  定义的四要素格式"空白） | error | M
- 证据：`shenbi-review-continuity/SKILL.md:114`、`shenbi-review-dialogue/SKILL.md:106`、`shenbi-review-long-span/SKILL.md:100`（均为 `每条缺陷报告必须遵循  定义的四要素格式：`——双空格处引用主体被删空）；对照组 `shenbi-character-extraction/SKILL.md:242`、`shenbi-review-foreshadowing/SKILL.md:137`、`shenbi-review-reader-pull/SKILL.md:171`、`shenbi-review-spinoff/SKILL.md:146`（"遵循四要素格式"完整）
- 根因：模板迁移时引用名（应为某 skill/规范名）被删，留下空引用；同模板四要素格式在 character-extraction 定义最完整。
- 验证命令+输出：`grep -rn "遵循  定义的四要素格式" skills/` → 3 处。
- 影响：引用悬空——LLM 无法得知"谁定义的四要素格式"；文案缺陷。
- 建议方向：补全引用（"遵循 character-extraction 定义的四要素格式"或直接内联四要素说明）。

### F963 | ngram-methodology.md 内部数值矛盾：示例 +15.9/+16.1/+17.9% 标注为满足 ">0.20" 阈值；6 字 n-gram 滑动窗口示例为 5 字窗口且串内容错误 | error | M
- 证据：`shenbi-review-long-span/ngram-methodology.md:54-56`（"连续 3 章同向漂移且每次 > 0.20 = warning"）vs `:59-65`（示例 Ch10→Ch13 为 +15.9%/+16.1%/+17.9%，全部 <20%，却标注 "← 连续 3 章同向 + > 20% = warning"）；`:17`（`"林轩看着他微微笑"` → `["林轩看着他", "轩看着他微", "看着他微笑", "着他微微笑"]`——9 字符串的 6 字符窗口应为 `林轩看着他微`/`轩看着他微微`/`看着他微微笑` 三个，示例输出为 4 个 5 字符串且内容错误）；SKILL.md 输出格式示例 `:136-141` 同用 +15.9/+16.1/+17.9
- 根因：阈值与示例数字脱节（示例按 15% 档写，阈值按 20% 写）；窗口示例手写出错。
- 验证命令+输出：读 ngram-methodology.md:17, 54-65；`python3 -c`（滑动窗口重算）确认 4 个 6 字符窗口 ≠ 示例。
- 影响：审计阈值判定参照矛盾（按示例 15.9% 应不触发，按标注触发）；算法示例错误会误导 LLM 实现。
- 建议方向：示例数字改为 >20%（如 +21%/+22%/+23%）或阈值改 >15%；重算窗口示例。

### F964 | spinoff-violations.md §7"所有违规统一为 error（无 warning）"与 SKILL.md 输出模板 WARNING 行矛盾；伏笔隔离要求 pending_hooks 每钩子有 scope 字段但种植模板无此字段 | error | M
- 证据：`shenbi-review-spinoff/spinoff-violations.md:157`（"所有上述违规统一为 error 级别（无 warning）"）；`shenbi-review-spinoff/SKILL.md:132`（建议修复模板含 `[WARNING] [段落] [问题描述]：[修复方案]`）；spinoff-violations.md:97（"确认所有伏笔有 `scope` 字段（`shared` / `spinoff`）"）；`shenbi-foreshadowing-plant/SKILL.md:99-115` 钩子 YAML 模板（id/content/state/operation/type/dimension/subtlety/plant_chapter/cultivation_interval/last_reinforced/max_distance/escalation_curve/depends_on/core_hook/promoted——无 scope 字段）
- 根因：参考文件与 SKILL.md 模板未同步（严重度分级两处口径不一）；伏笔种植侧未定义 scope 字段而审计侧要求它（跨 skill 字段契约缺口）。
- 验证命令+输出：读两文件对照；`grep -n "scope" skills/shenbi-foreshadowing-plant/SKILL.md` → 0。
- 影响：LLM 按 SKILL.md 模板可输出 WARNING 但参考文件禁止；伏笔隔离检查在无 scope 字段的钩子池上无法判定（范围混淆恒不可检）。
- 建议方向：统一严重度口径（建议保留 error+warning 两级）；种植/生命周期侧补 scope 字段契约。

### F965 | worldbuilding truth 文件数自相矛盾（"全部 11 个" vs 列出 12 个）+ 重复"## 铁律"节 + DOT "Read genre config" 对应文件未入 reads | error | M
- 证据：`shenbi-worldbuilding/SKILL.md:82`（"创建以下 **全部 11 个** truth files 的空模板"后列 state 8 + character 2 + intent 2 = **12 个**：current_state/chapter_summaries/particle_ledger/subplot_board/audit_drift/volume_summaries/pending_hooks/drift_guidance + character_matrix/emotional_arcs + author_intent/current_focus）；`:106`（铁律 7 "spec §4 定义的 11+ 个 truth files"）；`:62` 与 `:104` 两个 `## 铁律`；DOT `:49,52`（"Read genre config"）vs frontmatter reads `:8`（仅 novel.json，genre-config.json 在 writes）
- 根因：truth 文件清单演进后计数未更新（11 为旧计数）；结构节重复；genre-config 读取路径未入 reads（该文件由本 skill 创建后即读，属自产自读）。
- 验证命令+输出：读 SKILL.md:82 数文件 → 12；`grep -c "^## 铁律"` → 2；novel-output/xinghuo-ranqiong/truth/ 实有 12 个 truth 文件（+book_spine/resonance_trend 由其他 skill 产）佐证 12 为真。
- 影响：文案计数误导（遗漏初始化任一 truth file 会连锁失败——`:82` 自述）；DOT/reads 不一致小。
- 建议方向：计数改 12（或"12 个"与 spec §4 对齐）；合并铁律节；reads 补 genre-config.json 或改 DOT。

### F966 | description 含实现/执行注记（"runs in an independent agent"；score-stratum 中英混排）——description 纯度系统性瑕疵 | error | M
- 证据：`shenbi-review-arc-payoff/SKILL.md:5`（"…and character arc — runs in an independent agent"）；`shenbi-review-group-factual/SKILL.md:3`（见 F957）；`shenbi-score-stratum/SKILL.md:3`（"Use when scoring 大弧/书级健康评分 on goal attainment and anchor calibration"——英文句嵌入中文短语）；对照组同区 review-* 均为纯触发式（continuity/dialogue/spinoff 等）
- 根因：部分 skill 把执行约束（独立 agent）与触发条件混写在 description；score-stratum 语言混排。
- 验证命令+输出：读各 description；`python3 -c` 长度检查均 ≤500。
- 影响：description 是调度触发依据，混入执行注记/实现细节降低触发纯度（独立 agent 约束应入 requires_independent_agent 或正文）。
- 建议方向：description 统一为纯 "Use when …"；独立 agent 约束由 `requires_independent_agent: true` 承担（已存在）并从 description 移除。

### F967 | style-learning 输出头"纯统计（零 LLM）"与正文"LLM 转散文"矛盾；style-polishing DOT "prohibitions" 未在 reads 字段声明 | error | M
- 证据：`shenbi-style-learning/SKILL.md:168`（"**生成方式**: 纯统计（零 LLM）"）vs `:38`（"LLM 只负责将统计结果转化为散文描述"）与 `:243-248`（"## 8. 综合画像 [1 段散文]"）；`shenbi-style-polishing/SKILL.md:49`（DOT "Read genre-config.json (fatigueWords + prohibitions)"）vs frontmatter `:9-11`（仅字段 `fatigueWords`）
- 根因：风格画像含 LLM 散文段但头部声明"零 LLM"（口径冲突）；polishing 正文需要 prohibitions 字段但字段声明漏登记。
- 验证命令+输出：读两文件对照。
- 影响：产出物声明失真（下游据此判断画像纯度）；prohibitions 字段过滤后缺失（若 genre-config 有该字段则被过滤掉）。
- 建议方向：style_profile 头改为"统计：compute_stats.py；综合画像：LLM 散文"；polishing reads 字段补 prohibitions。

### F968 | chapter-drafting 黄金三章规则依赖 novel.json.golden_opening_chapters 但 novel.json 未入 reads（anti-ai-reference.md 间接引用）；3 个 .gitkeep 零字节遗留 | error | M
- 证据：`shenbi-chapter-drafting/anti-ai-reference.md:46`（"N = `novel.json.golden_opening_chapters`（默认 3）"）；`shenbi-chapter-drafting/SKILL.md:86`（铁律 6 "参考 anti-ai-reference.md"）vs frontmatter reads `:7-26`（无 novel.json）；`skills/{shenbi-chapter-drafting,shenbi-context-composing,shenbi-worldbuilding}/.gitkeep` 均为 0 字节（目录内已有 SKILL.md，占位冗余）
- 根因：黄金三章纪律由参考文件引入 novel.json 依赖，未同步主 SKILL 契约；.gitkeep 为目录建立期遗留。
- 验证命令+输出：`ls -la skills/shenbi-chapter-drafting/.gitkeep` → 0 字节；读 SKILL.md reads 列表。
- 影响：黄金三章 N 值在字段过滤下不可得（LLM 用默认 3 或猜测）；.gitkeep 无功能影响。
- 建议方向：chapter-drafting reads 补 novel.json（字段 golden_opening_chapters）或把 N 写入 genre-config/plan；删除 3 个冗余 .gitkeep。

### F969 | decisions.json 声明在 writes 但正文零指令（3 个 skill 均如此），dispatcher 只注入通用 schema 注记——decisions 内容契约悬空（Z11-01 无效 decisions 的 Z8 侧证据） | error | M
- 证据：`shenbi-chapter-drafting/SKILL.md:30-31`、`shenbi-short-drafting/SKILL.md:24-25`、`shenbi-context-composing/SKILL.md:47-48`（writes 声明 *-decisions.json）——三正文均无任何 decisions 内容/格式指令；`dispatch_helper.py:725-727`（仅当 `len(output_paths) > 1` 时注入 "Decisions JSON must conform to shenbi-decisions-v1 schema" 一句通用注记）；`docs/framework/decisions-schema.md:92-101`（per-skill selections targets 表列 chapter-drafting/short-drafting/context-composing）；`executor.py:84-85`（按文件名识别 file_type=decisions）
- 根因：decisions 由框架按文件名识别并做 schema 校验/恢复，但"该 skill 应记录哪些选择/调整/预算"无正文或注入指令——LLM 只能自由发挥；与 Z11-01（novel-output 145 个 decisions 中 83 个无效 JSON）呼应。
- 验证命令+输出：`grep -rn "decisions" skills/shenbi-chapter-drafting/SKILL.md skills/shenbi-short-drafting/SKILL.md skills/shenbi-context-composing/SKILL.md` → 仅 frontmatter/auto 契约；读 dispatch_helper.py:725-727。
- 影响：decisions 内容契约无定义处 → 产物 schema 不达标（Z11-01 实测 57% 无效），下游 chapter-revision 读 chapter-N-decisions.json 拿不到可靠决策参考。
- 建议方向：为三个 decisions skill 的正文补"决策记录"节（selections targets/severity/预算规则，对齐 decisions-schema per-skill 表），或由 dispatcher 按 schema 注入该 skill 的 decisions 模板。

---

## 2. per-skill 深度审查记录（Z8 七维度逐项）

### shenbi-anti-detect（SKILL.md 146 行）
- description 触发条件性：通过（纯触发式，含与 polishing 的分界——"distinct from polishing"为高质量触发区分）
- DOT 一致性：通过（9 手法 → 验证 → 重审计 → 判定，与正文一致）；小瑕疵：DOT 只画 anti-ai 重审计，铁律 3 要求 anti-ai + sensitivity 双审计（M 级）
- decisions.json：无声明（updates 类 skill，无需 decisions）✓
- reads 漂移：**F960**——触发源审计报告 audits/chapter-N-anti-ai.md 未入 reads；genre-config.json 声明读而正文零使用
- anti-rationalization 表：有，7 行（含"3 次未过回退""检测是统计指标"）质量高 ✓
- 确定性替换候选：无（改写为 LLM 核心）
- frontmatter 契约一致性：updates merge_prose + no_op_behavior ✓；writes 空 ✓
- G4：g4/anti_detect.py 存在 ✓；置信度 high

### shenbi-chapter-drafting（SKILL.md 160 行 + anti-ai-reference.md 50 行）
- description 触发条件性：通过 ✓
- DOT 一致性：通过（PRE_WRITE_CHECK → 人类批准 → 生成 → 转折词计数 1/3000 → 自检），转折词 1/3000 与 anti-ai-reference.md:22 一致 ✓
- decisions.json：writes 声明 chapters/chapter-N-decisions.json，正文零指令（**F969**）；index 确认 chapter-revision 读它（链存在，内容契约悬空）
- reads 漂移：style_profile 字段 11/6/9 漂移（**F952**）；anti-ai-reference.md 黄金三章依赖 novel.json.golden_opening_chapters 未入 reads（**F968**）；其余 reads（plan/context/style/genre/audit_drift）正文均有使用 ✓
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无（起草核心 LLM；转折词计数可确定化但为内嵌自检）
- frontmatter 契约一致性：writes create_or_overwrite ✓；updates 空 ✓；HARD-GATE（无备忘不写作）与 reads plan 一致 ✓
- G4：g4/chapter_drafting.py 存在 ✓；置信度 high

### shenbi-character-extraction（SKILL.md 245 行）
- description 触发条件性：通过 ✓（含与 character-design 的方向区分）
- DOT 一致性：通过（02_characters → 章节 → 逐角色提取 → 交叉验证 → 写 characters/）；小瑕疵：DOT "Cross-check with relationship_map"（:55）在正文无对应物（relationships.md 自产，交叉验证对象不明，M 级）
- decisions.json：无声明 ✓
- reads 漂移：reads 三文件正文均使用 ✓；无明显漂移
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：部分（scr_extractor.py 先例——位置/对话关键词可确定抽，语义类不可；本 skill 为全档案反向提取，LLM 核心，不候选）
- frontmatter 契约一致性：writes 4 文件 create_or_overwrite ✓ 与正文输出格式一致；四要素缺陷格式在此定义最完整 ✓
- G4：无专属 checker（generic 兜底）——低风险（导入路径产物由 generic 校验）；置信度 medium

### shenbi-context-composing（SKILL.md 227 行）
- description 触发条件性：通过 ✓
- DOT 一致性：基本通过（P1→P7 加载链 + 近章结尾检查）；小瑕疵：Hook 债务简报（第 9 节）与 decisions 写入不在 DOT 中（M 级）
- decisions.json：writes 声明 context/chapter-N-context-decisions.json（唯一 write），正文零指令（**F969**）；decisions-schema per-skill 表确认其为 decisions skill ✓
- reads 漂移：**F951**（主产物 context/chapter-N-context.md 无写者；近章结尾需 chapter-(N-3..N-1).md 未入 reads）；truth/audit_drift.md 与 truth/character_matrix.md 声明读而正文零使用（M 级）；伏笔溯源铁律 5 与 reads（pending_hooks 在 reads ✓）一致
- anti-rationalization 表：有，5 行 ✓
- 确定性替换候选：**是（P1 级，对齐 spec §3.2）**——context_assemble.py 已实现三路检索+重排+预算裁剪并落盘 context/chapter-N-context.md（:365-370）；LLM skill 在 pipeline 模式下仅剩策展层；确定化后 9 节不变量从 G4 后置变生成保证
- frontmatter 契约一致性：auto-check invariants（hook debt has paths / nine sections / no 3 consecutive endings）与正文计数规则一致 ✓；G4 context_composing.py 匹配新旧 P7 标题 ✓
- G4：g4/context_composing.py 存在 ✓；置信度 high

### shenbi-foreshadowing-plant（SKILL.md 168 行 + hook-types.md 32 行）
- description 触发条件性：通过 ✓
- DEPRECATED：**F950**（正文 :29-30 标注被 foreshadowing-lifecycle 取代，仍登记 deps.json planning 相位）
- DOT 一致性：通过（hook 账 → 密度预算 ≤8 → 类型/维度/微妙度/曲线 → 依赖 → append pending_hooks）；hook-types.md 与正文类型/维度/曲线/微妙度档位一致 ✓
- decisions.json：无声明 ✓
- reads 漂移：无（reads 五文件正文均用）；genesis 模式补充 story_frame/volume_map 读取已在 reads ✓
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：部分（hook ID 生成 + pending_hooks upsert 可确定化——hook_planting.py 先例；但 skill 已 DEPRECATED，候选无意义）
- frontmatter 契约一致性：updates append_dedup key=hook_id ✓；writes 空 ✓
- G4：g4/foreshadowing_plant.py 存在（为弃用 skill 保留 checker，同 F950 一并处理）；置信度 high

### shenbi-foundation-review（SKILL.md 256 行 + scoring-rubric.md 56 行）
- description 触发条件性：通过 ✓（含 human partner 询问触发）
- DOT 一致性：通过（六维 25/20/20/15/10/10 → 总分 ≥80 → 通过/返回）；scoring-rubric.md 六维分数带与 SKILL.md 评分工作表一致 ✓（含 15 分核心冲突子门槛一致）
- decisions.json：无声明（kind: report）✓
- reads 漂移：**F956**（genre-config.json 与 book_spine.md 缺失；前置验证 11 文件 vs reads 声明 5 项）
- anti-rationalization 表：有，5 行 ✓
- 确定性替换候选：无（requires_independent_agent，评分核心）
- frontmatter 契约一致性：requires_independent_agent ✓；kind: report ✓；重复"## 输出格式"节（**F956**）；"再平衡说明（spec §7.2）"外部引用无锚点（M 级）
- G4：无专属 checker（generic 兜底）；置信度 high

### shenbi-length-normalizing（SKILL.md 145 行）
- description 触发条件性：通过（阈值触发 3000/10000）✓
- DOT 一致性：通过（<3000 扩写 / >10000 压缩 / 双底线 25% 拒绝，与 HARD-GATE 铁律 2-4 一致）
- decisions.json：无声明 ✓
- reads 漂移：novel.json（target_word_count/genre/language）声明读但正文零使用——阈值是固定 3000/10000，不读 novel.json（M 级：声明读未用；正文也不引用 genre/language）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：部分——触发判定（字数阈值）可确定，扩写/压缩为 LLM 核心（不候选；字数统计可由 compute_stats 类确定）
- frontmatter 契约一致性：updates merge_prose + no_op_behavior ✓；writes 空 ✓
- G4：g4/length_normalizing.py 存在 ✓；置信度 high

### shenbi-memory-distill（SKILL.md 173 行）
- description 触发条件性：通过（12/36 章间隔 + 卷边界触发）✓
- DOT 一致性：通过（L2/L4/L5 分支）；铁律 4 "只更新数据字段" 与 DOT "Write book_spine.md (data fields only)" 一致——但契约模式为 create_or_overwrite（**F953/F954**）
- decisions.json：无声明 ✓
- reads 漂移：**F953**（author_intent/book_spine/arcs 缺失——L4/L5 流程数据源断链）；触发规则"密度驱动触发"自述 Wave 3 前为声明性文档（:60），与运行时脱钩（M 级，跨 Z 区）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：**是（P2 级，对齐 spec §3.4）**——结构字段聚合（钩子兑现表/角色态/未解悬置）可确定聚合，~800 字事件链叙述留 LLM；book_strata "Append" 与 create_or_overwrite 模式矛盾（并入 **F953**）
- frontmatter 契约一致性：book_strata create_or_overwrite vs 正文"Append 到 book_strata"（:127）矛盾（**F953**）；book_spine 双写者（**F954**）
- G4：g4/memory_distill.py 存在 ✓；置信度 high

### shenbi-power-system（SKILL.md 194 行）
- description 触发条件性：通过 ✓
- DOT 一致性：通过（识别题材 → 分级 → 进阶 → 上限 → 边界 → 代价 → 里程碑 → 交叉验证 → 人类审批 → 写 power_system.md）
- decisions.json：无声明 ✓
- reads 漂移：updates 目标 world/power_system.md 不在 reads（若文件已存在（首跑后二次设计），create_or_overwrite 盲写既有体系——M 级，模式同 F954 但单写者风险低）；其余 reads 正文均用 ✓
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无（设计类 LLM 核心）
- frontmatter 契约一致性：updates create_or_overwrite（首跑创建语义可接受）；writes 空 ✓
- G4：g4/power_system.py 存在 ✓；置信度 high

### shenbi-review-arc-payoff（SKILL.md 189 行）
- description 触发条件性：基本通过；含 "— runs in an independent agent" 实现注记（**F966**）
- DOT 一致性：通过（5 维度评分 → 门判定 ≥80 且伏笔兑现质量 ≥15 → 放行/阻断处方）；门逻辑表与正文一致 ✓
- decisions.json：无声明（kind: report；更新 audit_drift/arc_payoff_trend）✓
- reads 漂移：pending_hooks 字段声明（活跃伏笔/伏笔统计/伏笔时间线）vs 正文术语 resolved_this_arc/carried_forward（:76-77,92-93）——字段结构不直接提供该派生数据（M 级：命名与文件结构错位，需 LLM 从状态字段推导）；resonance_trend ✓、volume_map fields ✓、chapters/*.md ✓
- anti-rationalization 表：有，7 行（质量最高之一）✓
- 确定性替换候选：无（requires_independent_agent，评分核心）
- frontmatter 契约一致性：updates append_dedup key=chapter ✓（audit_drift/arc_payoff_trend）；writes audits/volume-N-payoff.md ✓；趋势行机器可解析格式与 drift CLI 契约自述一致
- G4：g4/review_arc_payoff.py 存在 ✓；置信度 high

### shenbi-review-continuity（SKILL.md 157 行）
- description 触发条件性：通过 ✓（但 skill 已 DEPRECATED——见 F950/F966 关联）
- DOT 一致性：通过（时间线/地点/事件/物理四查 + Arithmetic Consistency）
- decisions.json：无声明 ✓
- reads 漂移：无（reads 三文件正文均用；近 3 章摘要由 chapter_summaries 提供）；"默认激活的审计技能（每章必查）"（:45）与 DEPRECATED 矛盾（并入 **F950**）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无（deprecated；且审查核心 LLM）
- frontmatter 契约一致性：缺陷证据格式空引用（**F962**）；updates 空 ✓
- G4：无专属 checker（generic 兜底）；置信度 high

### shenbi-review-dialogue（SKILL.md 159 行）
- description 触发条件性：通过 ✓（DEPRECATED 同 F950）
- DOT 一致性：通过（逐角色声音匹配/口头禅/标签多样性/了字密度）
- decisions.json：无声明 ✓
- reads 漂移：激活条件依赖 genre-config.json auditDimensions 维度 16（:41）但 genre-config.json 未入 reads（M 级，同型 F960 家族；DEPRECATED 后风险低）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无
- frontmatter 契约一致性：缺陷证据格式空引用（**F962**）
- G4：无专属 checker；置信度 high

### shenbi-review-foreshadowing（SKILL.md 144 行 + hook-lifecycle.md 29 行）
- description 触发条件性：通过 ✓（DEPRECATED 同 F950）
- DOT 一致性：通过；hook-lifecycle.md 状态机与正文一致（PLANTED→RELEVANT→TRIGGERED→RESOLVED/ABANDONED，≤8 操作/章，max_distance error）✓；ARCHIVE vs ARCHIVED 命名小混（M 级）
- decisions.json：无声明 ✓
- reads 漂移：激活条件依赖 genre-config.json auditDimensions 6/24（:41）未入 reads（M 级）；大规模召回分支（:121-123, current_chapter>50 调 foreshadowing-recall）跨 skill 调用未反映在 reads（M 级）
- anti-rationalization 表：有，5 行 ✓
- 确定性替换候选：无（DEPRECATED；审查核心 LLM；recall 阈值过滤本身已有 recall.py 确定助手）
- frontmatter 契约一致性：reads 含 subplot_board ✓ 与正文一致；updates 空 ✓
- G4：无专属 checker；置信度 high

### shenbi-review-group-factual（SKILL.md 248 行）
- description 触发条件性：**违反**（**F957**——描述做什么/机制，无 "Use when"）
- DOT 一致性：通过（三个独立维度各自的铁律/检查/输出模板自洽；三报告独立输出）
- decisions.json：无声明 ✓
- reads 漂移：正文 Contract YAML 与 frontmatter 矛盾（**F958**）；frontmatter reads 8 文件与三维度使用匹配 ✓（world/power_system/locations/story_bible 供维度 2，genre-config 供维度 3 pacing——但 frontmatter 对 genre-config 无 fields，正文 Contract 有 fields [pacing, chapterTypes]，M 级小漂移）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无（requires_independent_agent，审查核心）
- frontmatter 契约一致性：kind: report ✓；stale 行号引用（**F958**）；G4 无专属 checker（group 系列均 generic 兜底）
- 备注：deps.json 未登记（F0-02 已录）；置信度 high

### shenbi-review-long-span（SKILL.md 157 行 + ngram-methodology.md 122 行）
- description 触发条件性：通过（含 ≥3 章条件）✓
- DOT 一致性：通过（n-gram 重复/意象循环/句开端/段长漂移四查）；ngram-methodology.md 与正文阈值一致（0.15 默认、>4 意象、>5 开端、3 章漂移），但示例数值矛盾（**F963**）
- decisions.json：无声明 ✓
- reads 漂移：无（chapter-N.md + chapters/*.md + genre-config.json 正文均用；激活条件 auditDimensions 10 + current_chapter≥3 有 genre-config ✓）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：**是（部分，P2 级）**——6 字 n-gram 重复率/意象计数/段长漂移均为确定性统计（ngram-methodology.md 已是现成算法 spec + Python 示例 :112-120；compute_pattern/compute_stats 先例）；LLM 保留判定/阅读体验判断；统计段提升 L1 可省大量 token
- frontmatter 契约一致性：缺陷证据格式空引用（**F962**）；updates 空 ✓
- G4：无专属 checker；置信度 high

### shenbi-review-reader-pull（SKILL.md 178 行）
- description 触发条件性：通过 ✓（DEPRECATED 同 F950）
- DOT 一致性：通过（开头钩子/章尾悬念/期待管理/中段牵引/钩子池压力）
- decisions.json：无声明 ✓
- reads 漂移：激活条件依赖 genre-config.json auditDimensions 32（:40）未入 reads（M 级）；"钩子池压力平衡"读 pending_hooks ✓ 已声明
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无
- frontmatter 契约一致性：缺陷证据格式完整 ✓；updates 空 ✓
- G4：无专属 checker；置信度 high

### shenbi-review-spinoff（SKILL.md 153 行 + spinoff-violations.md 159 行）
- description 触发条件性：通过 ✓（激活条件 = parent_canon.md 存在，该文件在 reads ✓）
- DOT 一致性：通过（原作事件/信息泄漏/世界规则/伏笔隔离四查）；spinoff-violations.md 四类违规判定与正文一致，但严重度口径矛盾（**F964**）
- decisions.json：无声明 ✓
- reads 漂移：无（reads 四文件正文均用）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无（审查核心 LLM；parent_canon 对照判定半确定——事件/时点表比对可部分确定，但语义判定留 LLM）
- frontmatter 契约一致性：scope 字段跨 skill 契约缺口（**F964**）；updates 空 ✓
- G4：无专属 checker；置信度 medium（spinoff 模式无真实运行产物）

### shenbi-score-stratum（SKILL.md 121 行）
- description 触发条件性：基本通过；中英混排（**F966**）
- DOT 一致性：通过（Route C 硬二元 + 软程度 + Route A 锚点 → 报告）；auto-check formula 与正文一致（PASS_THRESHOLD 90 / 0.4·0.6 权重 / 94 晋级线——与 AGENTS.md 阈值体系一致）
- decisions.json：无声明 ✓
- reads 漂移：book_spine 更新无正文描述（**F954**）；benchmarks/anchors/ ✓；book_strata/book_spine reads ✓
- anti-rationalization 表：有，2 行（偏薄，M 级可选）
- 确定性替换候选：无（评分核心；但 Route C 硬二元检查可部分确定——master hooks max_distance 推进/主角弧终点，可作 L1 助手；非候选主项）
- frontmatter 契约一致性：updates book_spine create_or_overwrite（**F954**）；kind: report ✓
- G4：g4/score_stratum.py 存在 ✓；置信度 high

### shenbi-short-drafting（SKILL.md 233 行）
- description 触发条件性：通过 ✓
- DOT 一致性：通过（三步：批量生成→审计→修订，≤3 轮回退）；6 维审计清单 EXACT 模板与修订规则一致 ✓
- decisions.json：writes 声明 short/short-N-decisions.json，正文零指令（**F969**）；decisions-schema per-skill 表确认 ✓
- reads 漂移：**F961**（novel.json.target_word_count 字数下限未入 reads）；style_profile 字段 11/6/9 漂移（**F952**）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无（起草核心 LLM；每章字数 floor 判定可确定化——并入 F961 修复）
- frontmatter 契约一致性：writes create_or_overwrite ✓；updates 空 ✓
- G4：无专属 checker；置信度 high

### shenbi-snapshot-manage（SKILL.md 235 行）
- description 触发条件性：通过 ✓
- DOT 一致性：通过（create/view/rollback/list 四操作；DOT 注记说明主流程外操作过程化描述——自洽）；manifest 模板含 snapshot_kind/checksums ✓
- decisions.json：无声明 ✓
- reads 漂移：**F955**（回滚恢复写未声明）；reads 7 项 glob 覆盖创建/查看操作 ✓（含 foreshadowing_recall_result.md 在 truth glob 内）
- anti-rationalization 表：有，3 行 ✓
- 确定性替换候选：**是（P0 级，对齐 spec §3.1——本区最强候选）**——创建/查看/列表/回滚全为 cp/glob/列表/hash；SKILL.md 自己禁止 LLM 算 checksum（:158-164 "不得由 LLM 自行生成"）；无 G4 checker（spec §3.1 确认）；每章 ~10-15K pass-through token 纯浪费
- frontmatter 契约一致性：writes snapshots/chapter-NNN/* glob ✓（manifest 由 glob 覆盖，未单列——M 级）；保留策略读 config.snapshot_retention_chapters（外部 config）
- G4：无专属 checker（与 spec §3.1 断言一致）；置信度 high

### shenbi-style-learning（SKILL.md 285 行）
- description 触发条件性：通过 ✓
- DOT 一致性：通过（compute_stats.py 确定性统计 → LLM 转散文；bootstrap 分支自洽）
- decisions.json：无声明 ✓
- reads 漂移：无（chapters/import/source/novel.json/genre-config.json 正文均用：bootstrap 种子指纹用 novel.json genre/era + genre-config show_tell_ratio/deep_themes ✓）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：**是（已部分落地）**——统计全由 compute_stats.py 确定（:38 明示）；LLM 仅剩散文转化（综合画像 + 汇总）；可进一步确定化 bootstrap 分支（种子指纹模板填充）；"纯统计（零 LLM）"头部声明矛盾（**F967**）
- frontmatter 契约一致性：writes style/style_profile.md ✓；输出 8 节格式与消费方字段引用漂移（**F952**）；可重现铁律 ✓
- G4：无专属 checker；置信度 high

### shenbi-style-polishing（SKILL.md 117 行）
- description 触发条件性：通过 ✓（含 "audit-passed" 前置 + 与 anti-detect 边界：铁律 5 与 anti-detect description 双向一致 ✓）
- DOT 一致性：通过（节奏/呼吸/用词 → 校验 ±15% 无情节变更 → 输出）
- decisions.json：无声明 ✓
- reads 漂移：style_profile 字段 11/6/1/2（**F952**——1/2 正确、11/6 漂移）；DOT "fatigueWords + prohibitions" 的 prohibitions 未声明（**F967**）
- anti-rationalization 表：有，4 行 ✓
- 确定性替换候选：无（润色 LLM 核心；疲劳词替换可半确定——词表替换可 L1，句法调整留 LLM；非主候选）
- frontmatter 契约一致性：updates merge_prose + no_op_behavior ✓；writes 空 ✓
- G4：g4/style_polishing.py 存在 ✓；置信度 high

### shenbi-volume-consolidation（SKILL.md 252 行）
- description 触发条件性：通过 ✓
- DOT 一致性：通过（合并→归档→长程记忆→写卷摘要→触发 arc-payoff 门）；arc-payoff 门阈值（≥80 且伏笔兑现≥15）与 review-arc-payoff 一致 ✓
- decisions.json：无声明 ✓
- reads 漂移：无（chapters/chapter_summaries/pending_hooks 正文均用；CP 术语缩写声明清晰）
- anti-rationalization 表：有，5 行 ✓
- 确定性替换候选：部分——归档/追加文件操作为确定性；卷摘要叙事为 LLM 核心（不候选）；CP 债务数值可半确定（公式在 foreshadowing-resolve）
- frontmatter 契约一致性：**F959**（create_or_overwrite vs 追加 + 重复节 + 编号重复）
- G4：无专属 checker；置信度 high

### shenbi-worldbuilding（SKILL.md 126 行）
- description 触发条件性：通过 ✓
- DOT 一致性：通过（novel.json 检查 → 脚手架/读 genre → 概念问询 → story_bible/rules/locations → 人类审批 → 落盘）
- decisions.json：无声明 ✓
- reads 漂移：DOT "Read genre config" 对应 genre-config.json 未入 reads（M 级，**F965**）；novel.json reads ✓
- anti-rationalization 表：有，5 行 ✓
- 确定性替换候选：部分——目录脚手架创建/11 个 truth 模板生成（模板填充）可确定化（spec 判据"固定模板填充"100%）；story_bible/rules 散文为 LLM 核心；truth 模板骨架可由 Python 生成（弱候选，P2 边缘）
- frontmatter 契约一致性：**F965**（11 vs 12 计数 + 重复铁律节）；novel.json 单写者 ✓（index 确认）；genre-config.json 与 genre-config skill 双写者（stub→细化，设计内交接，M 级备注）
- G4：g4/worldbuilding.py 存在 ✓；置信度 high

### 附属参考文件
- `shenbi-chapter-drafting/anti-ai-reference.md`（50 行）：与 chapter-drafting 转折词 1/3000、了字控制、标记词 ≤1/章 一致 ✓；黄金三章依赖 novel.json.golden_opening_chapters（**F968**）
- `shenbi-foreshadowing-plant/hook-types.md`（32 行）：与 plant 正文类型/维度/曲线/微妙度档位一致 ✓
- `shenbi-foundation-review/scoring-rubric.md`（56 行）：六维分数带与 SKILL.md 一致 ✓；维度 5/6 表格间缺空行（排版 M 级，不单列 finding）
- `shenbi-review-foreshadowing/hook-lifecycle.md`（29 行）：状态机/密度预算/max_distance 与正文一致 ✓；ARCHIVE vs ARCHIVED 命名小混（并入 M 级备注）
- `shenbi-review-long-span/ngram-methodology.md`（122 行）：**F963**（阈值/示例矛盾 + 窗口示例错误）；含可移植 Python 算法（确定性候选佐证）
- `shenbi-review-spinoff/spinoff-violations.md`（159 行）：**F964**（无 warning 口径矛盾 + scope 字段契约缺口）；parent_canon 必备字段建议完整

### .gitkeep 文件（3 个）
- `shenbi-chapter-drafting/.gitkeep`、`shenbi-context-composing/.gitkeep`、`shenbi-worldbuilding/.gitkeep`：均 0 字节，目录内已有 SKILL.md，占位冗余（并入 **F968** M 级）

---

## 3. 返回摘要

### findings 清单（F950–F969 共 20 条）

| ID | 严重度 | 一句话 |
|---|---|---|
| F950 | P1 | DEPRECATED skill 仍登记 deps.json 相位 + executor_config + 审计文件双写者（deprecation 零 enforcement） |
| F951 | P2 | context-composing 主产物 context/chapter-N-context.md 无写者 + 近章结尾 N-3..N-1 未入 reads |
| F952 | P2 | style_profile 字段级 reads 漂移（11/6/9 vs 实际 8 节，4 消费 skill + G6.10 死正则） |
| F953 | P1 | memory-distill L4/L5 数据源（author_intent/book_spine/arcs）未入 reads，L5 盲写 book_spine 风险 |
| F954 | P2 | book_spine 双更新者 + updates 用 create_or_overwrite 模式错配 |
| F955 | P2 | snapshot-manage 回滚恢复写未声明 |
| F956 | P2 | foundation-review reads 缺 genre-config.json/book_spine.md + 重复输出格式节 |
| F957 | P2 | review-group-factual description 违反触发条件性（lint 盲区） |
| F958 | P2 | review-group-factual 正文 Contract 与 frontmatter 矛盾 + 陈旧行号引用 |
| F959 | P2 | volume-consolidation create_or_overwrite vs 追加 + 重复节/编号 |
| F960 | P2 | anti-detect 触发审计报告未入 reads + genre-config 未用读 |
| F961 | P2 | short-drafting 字数下限依赖 novel.json 未入 reads |
| F962 | M | 3 个 review skill 缺陷证据格式空引用 |
| F963 | M | ngram-methodology 阈值/示例数值矛盾 + 窗口示例错误 |
| F964 | M | spinoff-violations 无 warning 口径矛盾 + scope 字段契约缺口 |
| F965 | M | worldbuilding truth 计数 11 vs 12 + 重复铁律节 + genre-config reads |
| F966 | M | description 含实现注记（runs in an independent agent）/中英混排 |
| F967 | M | style-learning "零 LLM" 声明矛盾；style-polishing prohibitions 未声明 |
| F968 | M | chapter-drafting golden_opening 依赖 novel.json 未声明；.gitkeep 冗余 |
| F969 | M | decisions.json 声明于 writes 但正文零指令（与 Z11-01 呼应） |

### 覆盖统计
- deep-read：**33 / 33**（24 SKILL.md 全量语义深读 + 6 附属参考文件全量 + 3 .gitkeep 结构验证）
- 每 skill 七维度（description 触发条件性 / DOT 一致性 / decisions.json / reads 漂移 / anti-rationalization / 确定性替换候选 / frontmatter 契约）全部逐项判定，见 §2
- 低置信度文件：`shenbi-review-spinoff`、`shenbi-character-extraction`（无真实运行产物可对照激活路径）
- 未覆盖文件：**无**

### 确定性替换候选清单（对齐 2026-08-01-deterministic-skill-replacement-audit-design）
1. **shenbi-snapshot-manage** — P0：纯 cp/glob/hash（spec §3.1 原判据成立；SKILL.md 自禁 LLM 算 checksum）
2. **shenbi-context-composing** — P1：context_assemble.py 已实现 pipeline 主路径（spec §3.2；本区验证 :365-370 落盘 context/chapter-N-context.md）
3. **shenbi-memory-distill** — P2：结构字段聚合确定 + 叙述留 LLM（spec §3.4；同时修 F953/F954 契约）
4. **shenbi-style-learning** — 已部分落地：compute_stats.py 确定性统计（LLM 仅剩散文段，可再压缩）
5. **shenbi-review-long-span** — 部分（新增候选）：n-gram/意象/段长漂移统计可 L1 化（ngram-methodology.md 是现成算法 spec；compute_pattern/compute_stats 先例；LLM 保留判定）
6. 弱候选/否：length-normalizing（触发阈值确定，核心 LLM）、worldbuilding（truth 模板骨架可确定，核心 LLM）、foreshadowing-plant（已 DEPRECATED，hook_planting.py 先例但无意义）

### 未覆盖文件列表
**空**（33/33 全覆盖）
