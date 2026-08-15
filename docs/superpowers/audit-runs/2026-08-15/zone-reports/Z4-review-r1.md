# Z4 复核报告（r1，fresh-context）— src/shenbi/gates/

- 复核轮：2026-08-15 全项目深度审查，Z4 区独立复核
- 编号段：F432–F448（初审已用 F401–F431）
- 复核方式：52 个清单文件全量重读 + 本轮新角度（(a) G4 注册表/豁免表/状态词表 ↔ 单源与磁盘双向核对；(b) checker 声称的文件名族 ↔ skills frontmatter writes 及**真实调用面传入文件集**对账）
- 只读约束：仓库零写入；所有验证脚本在 /tmp/z4rev/，输出实际运行并粘贴；pytest 未执行（禁令），覆盖类断言标"未复验"
- 附加对账源（超出 Z4.files 的只读引用，用于调用面核对）：src/shenbi/phase_runner.py、src/shenbi/pipeline/{chapter_loop,dispatch_helper,triggers,genesis,closure,audit_layer}.py、src/shenbi/dispatcher/executor.py、src/shenbi/audit/_shared.py、src/shenbi/paths.py、src/shenbi/status.py、tools/lint_status_strings.py、tests/tiers/deps.json、command-to-give.md、skills/*/SKILL.md

## 总体结论

初审对 checker 本体（幂等性、decisions 单源、G3.4 独立性）的结论复核成立。但本轮"声明面↔调用面"对账发现初审的核心盲区：**初审只读了 checker 与注册表本身，未对账"每个 checker 实际收到的文件集"**。由此发现 4 条 P1 级新缺陷（G5.5 第三注册表漂移假 FAIL、CLI project_dir 接线错误致 T2 RoundPaths 假 FAIL、pipeline 从不把 decisions.json 喂给 G4（chapter-revision G4 空转 PASS）、T2 传 writes+updates 使 score 检查器向 truth 侧车索要 RouteC），并修正 F401 的触发链与严重度、F414 的计数。

---

## 一、漏报（初审未发现的新 findings）

### F432 | G5.5 第三注册表 G5_CHECKER_GLOBS 漂移：缺项技能回退 `["*.md"]` 使专属 checker 扫全部 md 文件 → 生产相位假 FAIL | 漏报 | P1
- 证据: src/shenbi/gates/g5.py:224-249（G5_CHECKER_GLOBS 仅 19 项，缺 shenbi-book-spine-init/shenbi-score-arc/shenbi-score-volume/shenbi-score-stratum/shenbi-memory-distill/shenbi-escalation-review/shenbi-chapter-revision/shenbi-market-radar/shenbi-short-drafting 等全部 9 个新 checker 技能）；g5.py:271 `globs = G5_CHECKER_GLOBS.get(pr, ["*.md"])` —— 缺省 glob 比 SHORT_MAP 缺省（降级为 generic 弱检查，F414）**更宽**：fnmatch 的 `*` 匹配含 `/` 的整条路径，专属 checker 于是跑在**每一个** phase 输出 md 文件上
- 根因: 与 SHORT_MAP（cli.py:32-53）、G4_CHECKER_SKILLS（shared.py:247-270）并列的第三份 checker→文件族映射，新增 checker 技能时漏同步；且缺省值语义反转（不是"跳过"而是"全匹配"）
- 验证: tests/tiers/deps.json t2-phases —— genesis 前置含 shenbi-book-spine-init、drafting 前置含 shenbi-score-arc、management 前置含 shenbi-memory-distill/shenbi-score-volume/shenbi-score-stratum。/tmp/z4rev/repro_g55.py（完整 genesis 语义）输出：
  ```
  genesis G5 status: FAIL
    must_fix: G5.5:volume_map.md:G4_fail:shenbi-book-spine-init
    must_fix: G5.5:current_state.md:G4_fail:shenbi-book-spine-init
    must_fix: G5.5:factions.md:G4_fail:shenbi-book-spine-init
  ```
  /tmp/z4rev/repro_g55_min.py（无混淆最小复现，精确模拟 g5.py:271 缺省路径）输出：
  ```
  shenbi-book-spine-init x outline/volume_map.md -> FAIL  must_fix=['G4.bsi.missing_field:updated:', ...]
  shenbi-book-spine-init x truth/current_state.md -> FAIL  must_fix=['G4.bsi.missing_field:updated:', ...]
  shenbi-score-arc x outline/volume_map.md -> FAIL  must_fix=['G4.no_route_c:...', 'G4.no_route_a:...']
  shenbi-score-arc x truth/current_state.md -> FAIL  must_fix=[...Route C...]
  shenbi-memory-distill x outline/volume_map.md -> FAIL  must_fix=['G4.md.no_chapter_ref:...']
  shenbi-score-volume x outline/volume_map.md -> FAIL  must_fix=[...Route C...]
  ```
  生产入口确认：phase_runner.py:117/307 `cmd_start`/`cmd_finalize` 对每个相位跑 G5，FAIL 即 BLOCKED+exit 1
- 建议方向: 缺省 glob 改为"跳过该技能"（或仅当技能有 dedicated checker 时才需登记），并加 G5_CHECKER_GLOBS ↔ generic.checkers 键的漂移门禁（可并入 F406 的 G0.12 修正）

### F433 | CLI G4 分支把 project_dir 恒等 rd，而文档化 T2 协议 rd≠project_dir → RoundPaths 型 checker 在正确文件已传入 fps 时仍 not_found 假 FAIL | 漏报 | P1
- 证据: src/shenbi/gates/cli.py:113-120（`rd = arg(2)`; `project_dir=rd` 无独立入参）；权威协议 command-to-give.md:99 `shenbi-phase post-skill <phase> <skill> --round-dir <round-dir> --project-dir <round-dir>/project-output`（两目录显式不同）；phase_runner.py:216 `run_gate("G4", [skill, files, str(round_dir)])` 只把 round_dir 传给 CLI。RoundPaths 型 checker（worldbuilding/faction_builder/foreshadowing_track/relationship_map/story_architecture/power_system/location_builder/pacing_design/plot_thread_weaver/character_design 共 10 个）**忽略 fps**，按 `rp.read(rel)` = round_dir/rel → 缺失 → project_dir/rel（= round_dir/rel，同一个错目录）重读（src/shenbi/paths.py:19-24）→ not_found
- 根因: CLI 分发协议没有第 4 参承载 project_dir；RoundPaths 的双目录回退在 rd==project_dir 被硬绑后退化为同路径两次探测。对照 g7.py:151 G7.13 重跑显式用 `str(rd / "project-output")` —— 同一代码库内两种约定并存（并入 F413 布局分裂的又一实例，但危害独立成级）
- 验证: /tmp/z4rev/repro_cli_rd.py（faction 文件存在于 proj 且以绝对路径传入 fps，rd=独立 round 目录，精确模拟 T2 post-skill 语义）输出：
  ```
  exit: 0
  status: FAIL must_fix: ['G4.factions.not_found']
  ```
  文件合法、已传入、已存在，checker 仍假 FAIL。T2 后果链：cmd_post_skill 记 G4 FAIL → phase_runner.py:229-232 emit BLOCKED + sys.exit(1) → 相位推进被假失败阻断；且 marker 因非 PASS 不写（shared.py:195-196）→ pre-score 再被 missing_markers 阻断（phase_runner.py:250-258）
- 建议方向: CLI G4 增加可选第 4 参 project_dir 并由 phase_runner 透传；或 RoundPaths.read 增加对 fps 中已存在文件的同名优先解析

### F434 | pipeline 主路径从不把 decisions.json 传给 G4：chapter-drafting 的 decisions 恒 SKIP，chapter-revision 的 G4 为空转 PASS（checks=[]）——违反 AGENTS.md decisions-sidecar 显式契约 | 漏报 | P1
- 证据: AGENTS.md（decisions-sidecar 节）"G4 validates schema + P2.5 rules"；实际接线：chapter_loop.py:168/259 drafting/revision 步 `output_path="chapters/chapter-N.md"`（单一主产物）；chapter_loop.py:565-584 `_resolve_g4_files` 只返回该单文件；dispatch_helper.py:1928-1949 run_gate_g4 原样转发。composite 分区（decisions_validator.py:167-172）把 .md 给 existing、.json 给 decisions —— json 恒为空列表
- 根因: "每步单 output_path" 的管线文件解析与"复合 checker 需要全部 writes"的校验面从未对账（本轮角度 (b) 的核心命中）
- 验证: /tmp/z4rev/repro_pipeline_g4.py（真实管线语义：文件列表=["chapters/chapter-5.md"]，rd=proj，chapters/chapter-5-decisions.json 按契约存在于磁盘）输出：
  ```
  G4 drafting (files=chapter only) status: FAIL
  decisions-related checks: [{'id': 'G4.dec', 's': 'SKIP', 'r': 'no files'}]
  G4 chapter-revision (files=chapter only) status: PASS gate: G4-composite-g4_decisions checks: []
  ```
  （drafting 的 FAIL 来自最小 fixture 缺疲劳词等，与本条无关；关键证据是 `G4.dec SKIP no files` 与 revision 的 `PASS + checks: []` 空转）。chapter-revision 的 decisions 文件在管线中只被 `_ensure_revision_decisions_exists`（chapter_loop.py:1964-2014）读写，从不进任何 G4/G2 校验
- 建议方向: _resolve_g4_files 对 composite/decisions 技能返回解析后的全部 contract writes+updates；或 G4 后独立跑一次 g4_decisions 对 *.decisions.json

### F435 | T2 post-skill 传 writes+updates 全集，score-arc/volume/stratum checker 对**每个**传入文件索要 Route C → truth 侧车（audit_drift/volume_score_trend/book_spine）必然假 FAIL | 漏报 | P1
- 证据: score_arc.py:26-30（与 score_volume.py:26-30、score_stratum.py:26-30 逐字同）：对 fps 中每个文件执行 `"RouteC" not in normalized` 检查，无文件名过滤；而契约声明多产物：score-arc writes audits/arc-N-score.md + updates truth/audit_drift.md；score-volume + truth/volume_score_trend.md；score-stratum updates truth/book_spine.md（skills/shenbi-score-{arc,volume,stratum}/SKILL.md frontmatter）；T2 文件集 = derive_output_files（src/shenbi/audit/_shared.py:52-55 `[*c["writes"], *c["updates"]]`，phase_runner.py:194-201 调用）
- 根因: checker 文件名族（"任何传入文件都是 Route C 报告"）与技能声明面（评分报告 + truth 追加两类异构产物）未对账；管线侧（triggers.py:196-251 单 output_path=audits/*.md）因只传评分报告而侥幸不触发，T2 侧必然触发
- 验证: /tmp/z4rev/repro_score_family.py（stratum-1-score.md 含 RouteC/锚点，book_spine.md 为合法书脊文件，两者一起传入，精确 T2 语义）输出：
  ```
  shenbi-score-stratum -> FAIL must_fix: ['G4.no_route_c:must have Route C section', 'G4.no_route_a:must have Route A anchor section']
  shenbi-score-arc -> FAIL must_fix: ['G4.no_route_c:...', 'G4.no_route_a:...']
  ```
  management 相位 post-skill（deps.json 前置含 score-volume/score-stratum）即被 BLOCKED
- 建议方向: 三个 score checker 只检查 `audits/` 下文件（或以 `*-score.md` 为文件名族），truth 侧车跳过；顺带消除 F427 的三份复制

### F436 | G0.cc 的 E11 阈值一致性与 floor>=60 检查在生产为死线：gate_G0 调 check_config_coherence 从不传 resonance_global_floor | 漏报 | P2
- 证据: src/shenbi/gates/g0_config_coherence.py:65-80（`if resonance_global_floor is not None:` 门控 E11 + floor_too_low 两类检查）；唯一生产调用 g0.py:672 `cc_issues = check_config_coherence(project_dir)`（无 kwarg → 恒 None → 仅第 3 类 critical_audit_disabled 生效）；g0.py:654-656 注释却宣称 "configuration coherence (threshold mismatch + critical audit disabled)"。其余调用方全在 tests/（tests/unit/gates/test_g0_config_coherence.py 等，均显式传 kwarg）
- 根因: 参数门控设计为"调用方从 PipelineState 取实效 floor"，但 G0 运行点从未接线；测试直接传参掩盖死线
- 验证: `grep -rn "check_config_coherence" src/ tests/ --include="*.py"` → 生产调用仅 g0.py:672（无 kwarg），其余 20 处全为测试
- 建议方向: gate_G0 从项目 state 读 floor 后传入，或删除死检查并修正 g0.py 注释

### F437 | 文档化的三段式 `shenbi-validate G4 <skill> <file>` 相对路径调用以未捕获 ValueError 崩溃（traceback 而非 FAIL） | 漏报 | P2
- 证据: cli.py:66 自带用法示例 `shenbi-validate G4 chapter-drafting path/to/file.md`（无 rd）；AGENTS.md 关键命令节 `shenbi-validate G4 <skill> <files> <type>`（第 4 参被 cli 实为 rd，属文档漂移）。无 rd 时：RoundPaths checker 直接 raise（worldbuilding.py:28-29），generic 路径在 resolve_input_path raise（shared.py:70-74，Task 15b 移除 CWD 回退）
- 根因: Task 15b 删除静默 CWD 回退后，CLI 顶层未接住 ValueError，用法文案也未更新
- 验证: 仓库根执行 `uv run python -m shenbi.gates.cli G4 worldbuilding AGENTS.md`（相对路径、无 rd，符合用法示例形态）输出：
  ```
  File ".../g4/worldbuilding.py", line 29, in g4_worldbuilding
      raise ValueError("round_dir or project_dir required for G4 RoundPaths checkers")
  ValueError: round_dir or project_dir required for G4 RoundPaths checkers
  ```
- 建议方向: CLI 顶层捕获 ValueError → 输出干净 FAIL JSON；更新 cli.py:63-68 与 AGENTS.md 的参数说明

### F438 | derive_file_type 对 decisions-双产物技能返回 "decisions"，G2 据此跳过章节 .md 的全部质检；叠加 composite 对 .md 的静默跳过 → short-drafting 正文与 chapter-revision 修订稿在 T2 路径零结构校验 | 漏报 | P2
- 证据: executor.py:69-91 derive_file_type（outputs∩decisions 文件集 → "decisions"）；g2.py:83-84 decisions 分支 `if not fp.endswith(".json"): continue`（.md 只剩 G2.1-2.3 存在/非空/UTF-8）；decisions_validator.py:93-96 g4_decisions 对 .md 静默 skip。实测 derive_file_type：shenbi-chapter-drafting/-short-drafting/-chapter-revision/-context-composing/-market-radar 全部 → "decisions"
- 根因: "一个技能一个 file_type" 的 G2 模型无法表达"章节 .md 按 chapter 查 + decisions.json 按 decisions 查"的混合校验；chapter-drafting 因 g4_chapter_drafting 接手 .md 而幸免，short-drafting（无 .md 专属 checker）与 chapter-revision（composite 的 existing=g4_decisions 跳过 .md，见 F434）两侧全空
- 验证: G2 侧 uv run python -c（7 字超短章节）输出：
  ```
  G2 decisions on under-length chapter -> PASS | checks: ['G2.1', 'G2.2', 'G2.3']
  G2 chapter on same file -> FAIL | must_fix: ['G2.6:...chapter-1.md', 'G2.8:...', 'G2.9:...']
  ```
  G4 侧见 F434 复核输出（short-drafting 同理走 g4_decisions-only，.md 恒 skip）。管线端 G2 整体跳过（executor.py:216-219），修订稿仅靠轮末 G6.3 兜底；T2 端无兜底
- 建议方向: G2 按文件扩展名分流 file_type（.json→decisions，.md→derive 的 chapter/truth），或 composite 技能的 .md 强制走结构 checker

### F439 | 5 个 decisions 生产技能的 SKILL.md 均不记载 DecisionsDoc 必填字段（$schema/skill/chapter/produced_at）——校验面强制的 schema 在声明面零文档 | 漏报 | P2
- 证据: `grep -c "shenbi-decisions-v1\|produced_at" skills/shenbi-{market-radar,short-drafting,chapter-revision,context-composing,chapter-drafting}/SKILL.md` → 全部 0；全 skills/ 引用 decisions-schema 的文件数 0。校验面：contracts/schemas/decisions.py:69-83（DecisionsDoc 必填 $schema/skill/chapter/produced_at，extra=forbid）；g4_decisions（decisions_validator.py:109-118）与 G2.dec（g2.py:158-163）双点强制。管线仅在多产物提示里附一句 doc 路径（dispatch_helper.py:736-740），且子代理读不到仓库 docs；T1/T2 的 prompt 由调用方给定（shenbi-dispatch CLI 协议），schema 灌输无保证
- 根因: 角度 (b) 的声明面↔校验面对账缺口：契约 frontmatter 只写文件路径不写内容契约；AGENTS.md 说 schema 见 docs/framework/decisions-schema.md，但技能（LLM 唯一稳定可见的声明面）从不内联必填字段
- 验证: 上述 grep 输出（粘贴）；deps.json:310 显示 market-radar 属 _out_of_pipeline（不进相位/管线，恰是 schema 灌输最无保证的技能，而它挂的是 decisions-only checker）
- 建议方向: 5 个技能的 SKILL.md 增加最小合法 decisions.json 模板（或 dispatcher 对 decisions 写入者自动注入 schema 块）

### F440 | G0.12 注释称 "dedicated checkers for 20 skills"，实际 G4_CHECKER_SKILLS=22、注册表=31 | 漏报 | M
- 证据: g0.py:537-539 注释 vs shared.py:247-270（22 项）与 generic.py:302-335（31 项）
- 根因: 三次扩表未同步注释（F406 的计数漂移在注释层的残留）
- 验证: `uv run python -c "...len(G4_CHECKER_SKILLS)=22, checkers dict=31..."`（本轮双向核对输出：checkers dict: 31；in checkers but not G4_CHECKER_SKILLS: 9 项；checkers keys NOT on disk: []）
- 建议方向: 注释删除具体数字或引用常量

### F441 | score 三 checker 输出无技能前缀的 check id（"G4.not_found"/"G4.no_route_c"/"G4.no_route_a"，SKIP id 为裸 "G4"）——与其他 checker 的前缀约定（G4.bsi/G4.er/G4.md/…）冲突且占据通用 id 空间 | 漏报 | M
- 证据: score_arc.py:23-32 / score_volume.py:23-32 / score_stratum.py:23-32（三处逐字同，id 均无 sa/sv/ss 前缀，三文件间还互相同名）；对照 book_spine_init.py:21-31（G4.bsi）、escalation_review.py:23-31（G4.er）
- 根因: F427 指出的复制粘贴三胞胎在 id 词表上的延伸；must_fix 串无技能前缀时无法区分来源
- 验证: 读三文件比对（F435 复核输出中 must_fix='G4.no_route_c:...' 即此 id）
- 建议方向: 合并为一个参数化 checker 并补 G4.sa/G4.sv/G4.ss 前缀

### F442 | chapter-revision 复合 checker 角色倒置 + gate 名误标：g4_chapter_revision 被当作 decisions_checker 传入，结果 gate 名为 "G4-composite-g4_decisions" | 漏报 | M
- 证据: generic.py:333 `make_composite_checker(g4_decisions, g4_chapter_revision)`（chapter-revision 是唯一把结构 checker 放第二参的接线）；decisions_validator.py:192/197 gate 名取 `existing_checker.__name__` → 结果串为 "G4-composite-g4_decisions"，无法从结果辨认这是 chapter-revision 的门
- 根因: make_composite_checker 的参数语义（existing/decisions）假设结构 checker 恒在首位；F434 复核输出 `gate: G4-composite-g4_decisions checks: []` 即此名
- 验证: 读 generic.py:333 + decisions_validator.py:147-197；/tmp 复核输出（见 F434）
- 建议方向: 复合 gate 名改为含技能名（调用方可传 skill_name），或对调 chapter-revision 的参数并复核分区语义

### F443 | _load_protagonist_names 把项目专属主角名 "林烽" 硬编码为框架默认值 | 漏报 | M
- 证据: chapter_drafting.py:141/162/332（characters/protagonist.md 缺失或无 name 时默认 ["林烽","他"]）
- 根因: 星火项目的数据渗入框架运行时；对任何其他项目该检查退化为"他"计数（几乎恒过），检测力归零但不误伤
- 验证: 读文件三处（grep "林烽" 输出行号 141/162/332）
- 建议方向: 默认改为空列表+检查 SKIP，或从 novel.json 读主角

### F444 | memory-distill L5 触发把 truth/book_spine.md 当蒸馏产物校验（要求章号引用）——文件族错配，当前真实文件仅偶然通过 | 漏报 | M
- 证据: triggers.py:244-249（L5 步 output_path="truth/book_spine.md"）；memory_distill.py:26-27 对**每个**传入文件要求 `第\d+章|chapter.*\d+`；书脊是声明型骨架文件，不是章蒸馏物。真实文件 novel-output/xinghuo-ranqiong/truth/book_spine.md 的模式命中数=1（grep -c 输出 1，边缘通过；status 仍为 pending_intent 的早期数据）
- 根因: checker 文件族按"arc 蒸馏物"设计，L5 触发复用同一 checker 校验异构产物（与 F435 同类但未爆）
- 验证: grep -c 于真实文件输出 1；未运行管线触发路径（标注：触发级假 FAIL 未验证，仅文件族错配已判）
- 建议方向: L5 步跳过章号检查或改用 book_spine_init checker

---

## 二、误报 / 事实修正（初审结论需更正的部分）

### F445 | 对 F414 的修正：SHORT_MAP 缺的不是 9 个而是 11 个——漏了 shenbi-review-arc-payoff 与 shenbi-review-resonance | 误报修正（范围低估） | 维持 P2
- 证据: cli.py:32-53 SHORT_MAP 20 项；generic.py:302-335 注册表 31 项
- 根因: 初审按"新增 checker"清单核对，漏算两个早已存在 dedicated checker 的 review 技能同样无简写映射
- 验证: 本轮双向核对输出：
  ```
  SHORT_MAP covers: 20 ; dedicated skills missing from SHORT_MAP:
  ['shenbi-book-spine-init','shenbi-chapter-revision','shenbi-escalation-review','shenbi-market-radar',
   'shenbi-memory-distill','shenbi-review-arc-payoff','shenbi-review-resonance','shenbi-score-arc',
   'shenbi-score-stratum','shenbi-score-volume','shenbi-short-drafting']   # = 11
  ```
  后果同 F414：简写 `shenbi-validate G4 review-resonance ...` → SHORT_MAP.get 回退原名 → gate_G4("review-resonance") 查表失败 → generic 降级，且 marker 名（G4-review-resonance-generative）与 phase_runner.py:250 期望的 G4-shenbi-review-resonance-generative 不符 → pre-score 阻断
- 验证: 上述 python 输出（实际运行）
- 建议方向: 同 F414（从注册表派生）

### F446 | 对 F401 的触发链与严重度异议：pipeline 并不传 decisions json（checker 半边根本不运行，而非假 FAIL），T2 传绝对路径可正常工作；假 FAIL 仅限"相对 json + rd + CWD≠rd"的手动 CLI 形态 | 严重度异议 P1→P2（缺陷本体成立） | P2
- 证据: 初审称"files 来自 _resolve_g4_files/chapter_loop.py:565-584 为契约相对路径 … pipeline 子进程继承父 CWD 故必然假 FAIL"。实际：chapter_loop.py:259 修订步 output_path="chapters/chapter-N.md"，_resolve_g4_files（565-584）只返回该单文件——**decisions json 从不进入 fps**，composite 把无 json 的列表喂给 g4_chapter_revision → 循环零次 → 无 crash 也无假 FAIL，而是**空转**（见 F434，复核实测 `PASS + checks: []`）。T2 路径 derive_output_files 返回绝对路径（audit/_shared.py:57-58 以 round_dir 实参绝对化）→ g4_chapter_revision `Path(fp)` 对绝对路径工作正常。初审 verify1 的相对路径复现只对应手动 CLI 形态（该形态真实存在且符合 AGENTS.md 示例风格，故缺陷本体保留）
- 根因: 初审未对账调用面文件集（本轮角度 (b)）；把"checker 忽略 rd"正确观察外推成了"pipeline 必然假 FAIL"的错误结论
- 验证: /tmp/z4rev/repro_pipeline_g4.py 输出（F434 节粘贴）：revision 调用返回 PASS 而非 crash/FAIL；调用面证据 chapter_loop.py:259+565-584、phase_runner.py:216+audit/_shared.py:57-58（读码）
- 建议方向: 修 resolve_input_path(fp, rd)（一审建议仍对）；严重度改 P2；其生产影响主体由 F434（空转 PASS）承接

### F447 | 对 F402 的补充证据：状态词表 lint 只拦截"词表内"字面量，"HARD_FAIL" 因越表而逃逸——status 单源的门禁存在盲区 | 误报修正之补充（F402 维持 P2） | P2（门禁盲区部分）
- 证据: tools/lint_status_strings.py:29-31（`_is_status_value` 仅当字面量 ∈ STATUS_STRING_LITERALS 才违规）；status.py:91-100 词表不含 "HARD_FAIL"；chapter_revision.py:97 因此未触发 lint（本轮 `uv run python tools/lint_status_strings.py` exit 0）
- 根因: lint 防"第二来源重定义既有状态"，不防"引入词表外新状态串"；越表状态绕过单源契约且类型层不可见（"HARD_FAIL" 非 GateStatus 成员）
- 验证: lint 实跑输出 exit: 0；`"s": "..."` 全区扫描仅五种合法值 + chapter_revision 的越表 "HARD_FAIL"（`grep -rn '"status": "..."'` 与 `'"s": "..."'` 扫描输出：PASS×163/SKIP×57/FAIL×48/WARN×23/UNIMPLEMENTED×12，无其他越表值）
- 建议方向: lint 增加"词表外全大写下划线串出现在 status 键"的启发式；或 chapter_revision 改用 GateStatus.FAIL（一审建议）

（其余初审 findings F402–F430 逐条代码复读均成立，未发现整条误报；F403 的 8 处崩溃点抽查 g5.py:57/67、g6.py:50/56、g7.py:34-63、g_dispatch.py:35-43、g_transition.py:36-44、g_reconcile.py:33 与初审一致；F417/F418 涉及的覆盖率数字未复验——pytest 禁令，标注"未复验"，但 F417 的"无专门测试文件"经 `ls tests/unit/gates{,/g4}` 复核成立：g4/ 目录无 test_memory_distill.py、无 test_book_spine_init.py。）

---

## 三、覆盖空洞（初审审查方法的结构性缺口）

### F448 | 初审未做"调用面文件集"对账：四份注册表中的两份（G5_CHECKER_GLOBS、SHORT_MAP↔checkers）与"每个 checker 实际收到什么文件"均无漂移门禁 | 覆盖空洞 | P2
- 证据: 同一映射关系存在四个平行定义源——generic.py:302-335（checkers，31）、shared.py:247-270（G4_CHECKER_SKILLS，22）、cli.py:32-53（SHORT_MAP，20）、g5.py:224-249（G5_CHECKER_GLOBS，19）；G0.15（g0.py:606-625）只校验 G4_CHECKER_SKILLS ⊆ 磁盘技能（子集、单向），不校验 checkers 键 ⊆ 磁盘、SHORT_MAP/G5_GLOBS ⊆ checkers。本轮双向核对：checkers 键全部真实存在（`checkers keys NOT on disk: []`），但任何未来 typo 将静默降级 generic 而无门禁
- 根因: F432/F414/F445 三个 drift 的共同根因：注册表无单源、无双向门禁；初审逐文件深读时把注册表当"事实"而非"待对账对象"
- 验证: 本轮 python 双向核对输出（F445 节粘贴）+ g0.py:606-625 读码
- 建议方向: G0.12/G0.15 扩为四表一致性检查（或从 generic.checkers 键派生其余三表）

另一方法论空洞（不单列编号）：初审的"声称检查的不变量"取自 checker docstring/注释，未与 AGENTS.md 契约逐条对账——F434（AGENTS.md "G4 validates schema+P2.5" vs 实际从不喂文件）与 F436（g0.py 注释宣称 threshold mismatch vs 死线）都落在这个缝隙里。

## 四、严重度异议汇总

| 初审编号 | 初审判级 | 复核意见 | 依据 |
|---|---|---|---|
| F401 | P1 | **降为 P2**（缺陷成立，触发面大幅窄于初审描述；pipeline 空转问题已拆为 F434 另立 P1） | F446 |
| F414 | P2 | 维持，但缺项 9→11（F445） | F445 |
| F402 | P2 | 维持，补 lint 盲区证据（F447） | F447 |
| F406/F417/F418 | P2 | 维持（F417/F418 覆盖数字未复验，pytest 禁令） | — |
| 其余 F402–F431 | — | 复读成立，无异议 | 逐条代码复读 |

## 五、本轮角度发现摘要（词表/字面量 + 声明面↔磁盘面/调用面）

1. 状态词表：区内 check "s" 值仅五种合法 GateStatus 值（扫描计数 163/57/48/23/12），唯一越表串为 chapter_revision 的 "HARD_FAIL"（F402/F447）；词表 lint 对越表串失明。jload ValueError 八处不设防（F403）复核成立。
2. 注册表四源（31/22/20/19）漂移全景：checkers↔磁盘 双向无错（当前）；G4_CHECKER_SKILLS 落后 9（F406）；SHORT_MAP 落后 11（F445 修正）；G5_CHECKER_GLOBS 落后 12+ 且缺省语义反转致 P1 假 FAIL（F432，初审完全漏检）。豁免表存在、全空、被读不用（F406 复核成立，`{"generative": [], "bughunt": [], "clean": []}`）。
3. 文件族对账（声明面 writes ↔ checker 检查面 ↔ 调用面实传文件）：decisions 生产者 5/5 已接线但 pipeline 从不喂 json（F434）；score 技能 truth 侧车被当评分报告（F435）；short-drafting/chapter-revision 的章节正文在 T2 两侧（G2 decisions 分流 + G4 md 跳过）均零校验（F438）；memory-distill L5 书脊错配（F444）；market-radar 等 5 技能声明面不载 schema（F439）；RoundPaths 十 checker 忽略 fps 且依赖被硬绑的 project_dir=rd（F433）。
4. CLI 契约面：用法示例三段式 G4 相对路径崩溃（F437）；AGENTS.md `shenbi-validate G4 <skill> <files> <type>` 第 4 参描述与 cli 实参（rd）不符（文档漂移，并入 F437）。

## 六、验证命令与产物索引（均在 /tmp/z4rev/，仓库零写入）

- repro_g55.py / repro_g55_min.py —— F432（G5 genesis 假 FAIL + 无混淆最小复现）
- repro_cli_rd.py —— F433（CLI rd≠project_dir → RoundPaths not_found）
- repro_pipeline_g4.py —— F434（G4.dec SKIP no files；revision 复合空转 PASS）
- repro_score_family.py —— F435（score 检查器对 truth 侧车索要 Route C）
- `uv run python -c` derive_file_type 枚举 + G2 decisions/chapter 对照 —— F438
- `uv run python -m shenbi.gates.cli G4 worldbuilding AGENTS.md` —— F437
- `uv run python tools/lint_status_strings.py`（exit 0）+ 两轮 grep 词表扫描 —— F447
- 双向注册表核对 python 单行（31/22/20/11 项清单）—— F445/F448
- 未验证项（逐条声明）：F444 的管线触发级假 FAIL（未运行管线）；F417/F418 的覆盖率数字（pytest 禁令）；F433 的端到端 T2 相位运行（以 command-to-give.md 协议 + phase_runner 读码 + CLI 等价复现替代）。
