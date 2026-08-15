# Z7 区独立复核报告（review-r1，fresh-context）

- 轮次: 2026-08-15 全项目深度审查 | 复核 agent: Z7-review
- 对象: Z7-a（tests/unit 236）/ Z7-b（73）/ Z7-c（tests/tiers 445）/ Z7-d（fixtures 等 166）四段初审（F701–F764, F776–F790）
- 本轮新增角度: (a) 计数三方对账（测试声称数 vs 实际测试数/断言数/参数化维度数）；(b) "全量/仅"断言的采样截断复查
- 编号段: F765–F775
- 方法: 只读。全部命令实跑（grep/sed/python3 只读脚本/`uv run pytest --collect-only -q`）。未执行任何测试运行态；未 git add/commit。
- 方法披露: 首次 `pytest --collect-only -q`（未加 --no-cov）因 pyproject addopts 含 --cov 重写了未跟踪产物 tests/coverage/coverage.xml（git status 干净，任何完整测试运行会重新生成）；后续 collect 均加 --no-cov。见 F770。

## 0. 抽样统计

| 项 | 数量 |
|---|---|
| findings 涉及文件重读/核实 | 82（Z7-a 26、Z7-b 22、Z7-c 20、Z7-d 14；含 src 侧 8 处） |
| 未涉 findings 深读抽样 | 15（unit 6 / pipeline 2 / tiers 3 / fixtures+contracts 4） |
| 机械全量补核 | 43 条 fixture 路径逐一存在性、deps.json 99 条 _tool_hashes 逐一重哈希、tests/unit 全量弱断言扫描（or True / len>=0 / assert True / PASS-FAIL 双收）、src 全模块 ↔ tests 零引用交叉（find 45 个模块）、9 t2 + 3 t3 相位闭包全比对、四段 .files 行数对账 |
| 偏差说明 | 未涉 findings 深读抽样低于"每段 ≥15"目标（Z7-c/Z7-d 各 3-4），以机械全量核验补足；已如实标注 |

对账基线：`wc -l zones/Z7-{a,b,c,d}.files` → 236/73/445/166 = 920，四段报告声称的清单数全部精确一致（无截断遗漏）。

## 1. 计数三方对账与截断检查（本轮角度）

### 1.1 通过项（精确复现）

| 声称 | 出处 | 复核结果 |
|---|---|---|
| "场景引用 fixture 路径 0 断链（43 个不同路径）" | Z7-c 机械核验 B 段 | `grep -rhoE 'tests/fixtures/[A-Za-z0-9_./-]+' tests/tiers/ \| sort -u` → 43 行，逐一 `[ -e ]` → missing=0。**精确复现** |
| "_tool_hashes 99 条中 66 条漂移（63 过期+3 删除）" | F756 | 重算（剥 `sha256:` 前缀后）→ total=99 drift=63 deleted=3 ok=33；删除项 = summarize_round.py / contract.py / update_progress.py。**精确复现**（注：不剥前缀会得 drift=96 的假象，初审算法理解正确） |
| "20 技能 × 12 契约断言" | Z7-a g4 参数化描述 | `_SKILL_CHECKERS` 元组数 = 20（test_all_skills_parametrized.py:31-50）；文件 assert 语句 = 13（docstring 自称 "~12"，加 ~ 号，可接受） |
| "18 review skills" | t2 audit seed / t3 long-form seed | deps.json audit prerequisites = 18 项，逐一为 review-*。一致 |
| "16 步表" | Z7-a/Z7-b 多处 | `python3 -c "from shenbi.pipeline.chapter_loop import CHAPTER_STEPS; print(len(...))"` → 16 |
| "grep 到 10 处 skip 站点" | F712 | 同 grep 实跑 → 11 行命中，其中 1 行为 docstring 提及 xfail（test_coverage_thresholds.py:30），实际站点 = 10，处置表 10 条逐一对应。**无截断** |
| "32/32 逐字节副本" | F781 | 独立哈希比对重跑 → exact duplicates: 32 |
| "68 份 rubric 含 75-89: PASS (acceptable)" | F760 | grep → 68 |
| "18 份旧 applicability 表头" | F757 | `grep -rln "Bug-hunt Standard" tests/tiers/t1-skill/` → 18；scoring.py:88 仅识别 `Dimension scope` |
| "371 项 doc_links skip" | F732 | d1-11 日志: "2887 passed, 373 skipped"（371 doc_links + 2 其他）自洽；**但该计数已过期**（见 F769） |
| Z7-d "166/166 在盘"、"全 fixtures 对 novel-output 镜像 4/4 登记" | Z7-d | 抽样复核一致（F777/F778/F779/F784 五点抽验全中） |

### 1.2 计数漂移与不可复现项 → 见 F768 / F769。

### 1.3 全仓 collect 对账

`uv run pytest --collect-only -q`（本次）→ **3292 tests collected**；d1-11-collect-only.log（d1 时点）→ **3264**。差值 +28 与 docs/ 新增 .md 数精确吻合（见 F769），无 collect 错误、无截断（-q 清单 3475 行 > 测试数）。

## 2. 漏报（新 findings）

### F765 | book_spine_init G4 检查器零测试引用，77% 覆盖率为 import 虚高 | error | P2
- 证据: `grep -rn "book_spine_init\|book-spine-init" tests/ --include="*.py"` → **零命中**（skills 名仅出现于 src/shenbi/gates/g4/generic.py:325 的映射与 genesis.py:75,101）；d1-06:71 `src/shenbi/gates/g4/book_spine_init.py … 77% 21-22, 25->24, 28->27, 31, 34`——缺失行正是函数体（not_found/missing_field/missing_section 分支，book_spine_init.py:15-34），77% 来自 generic.py 的模块级 import。
- 根因: F717 的检查器覆盖缺口清单列了 memory_distill（12%）、score_*（not_found/SKIP 分支）但漏掉 book_spine_init：它同样不在 20 技能参数化清单（test_all_skills_parametrized.py:31-50 无此条目）、无专属测试文件（对比 escalation_review 有 test_g4_escalation_review.py）。Z7-c F758 记其 T1 为 RUBRIC-ONLY、"由 T2 genesis 覆盖"——但 T2 是 LLM 判定剧本，非 Python 断言，检查器逻辑实际零护栏。
- 验证: 上述 grep + `sed -n '15,34p' src/shenbi/gates/g4/book_spine_init.py`（frontmatter 字段/核心冲突/themes/主角弧/主线钩子校验逻辑全文无测试驱动）。
- 建议方向: 纳入参数化清单或补专属测试（正/负例各一即可覆盖 21-34 行）。

### F766 | contracts/skills 三个语义校验器验证分支零覆盖（34%/38%/40%） | error | P2
- 证据: d1-06: `contracts/skills/chapter_planning.py 34%（28-36,40-44,48-57）`、`context_composing.py 38%（25-27,31-34,38-43）`、`volume_outlining.py 40%（26-29,33-37,41-45）`。三模块携带生产语义规则：chapter_planning.py:8-10（章>3 须有 typed change、hook op 白名单 open/advance/resolve/defer、defer 静默≥4 须有激活计划）、context_composing.py:25-45（9 节计数、hook_debt 须带 source_file、3 连续同型结尾禁令）。`grep -rln "ChapterPlanning\|ContextComposing\|VolumeOutlining" tests/ --include="*.py"` → 仅 tests/unit/pipeline/test_skill_integration.py，且该文件只做 SKILL.md 文本断言（:188-207），从不 import 校验模型。
- 根因: 这些模型经 registry 动态发现加载（src/shenbi/contracts/registry.py:51 `importlib.import_module(f"shenbi.contracts.skills.{name}")`），属活代码；F717 的覆盖缺口清单未收录这三个模块。
- 验证: 上述 grep + d1-06 三行 + registry.py:51-52。
- 建议方向: 为三个 validator 各补 2-3 个负例（违规 payload → ValueError），同时覆盖 pydantic 校验与 registry 发现路径。

### F767 | F716 弱断言清点不完整：同类"PASS/FAIL 双收"另有 6 处 | error | M
- 证据: 全量扫描 `grep -rn 'in {"PASS", "FAIL"}\|in ("PASS", "FAIL")…' tests/ --include="*.py"` → 共 8 处；F716 仅列 test_g2.py:40、test_g5.py:225 两处。遗漏：tests/unit/gates/test_g1.py:75、test_g3.py:89、test_g6.py:66、test_g6.py:86、tests/unit/gates/g4/test_foreshadowing_plant_regression.py:40、:58。
- 根因: F716 的集合式清点非机械全量。 mitigating：6 处中多数带"gate must complete, not raise / yload may tolerate"的显式 no-crash 意图注释，属有意 smoke；但与 F716 已列两处同类同性质，清单应完整。
- 验证: 上述 grep 输出（8 行）+ 逐行上下文读取。
- 建议方向: 并入 F716 处置（精确化或显式标注 no-crash 意图）。

### F768 | Z7-a "三个代表性文件 96 tests collected" 未指名文件、不可复现 | documentation | M
- 证据: Z7-a.md:8 声称"验证三个代表性文件可收集（96 tests collected）"，全文仅 :392 提到 test_review_checklist.py 是三者之一。复现尝试（均 --no-cov）：`test_g5+test_g6+test_review_checklist` → 69；`test_scoring+test_g6+test_review_checklist` → 121；`test_scoring+test_g5+test_review_checklist` → 104。无一为 96。
- 根因: 验证性计数未绑定可复现的文件三元组，三方对账失败（声称数 ↔ 实际收集数无法对上）。
- 验证: 上述三条 collect 命令输出。
- 建议方向: 报告中的量化验证声明应附精确命令行；不构成对 findings 的反驳（该声明不支撑任何 finding 结论）。

### F769 | doc_links 参数化计数随 docs/ 单调增长，"371 项"类计数自设计上过期 | error | P2
- 证据: `find docs -name "*.md" \| wc -l` → 390，`ls *.md \| wc -l` → 9，合计 399 个参数化项（test_doc_links.py:36 `_markdown_docs()` = docs/ rglob + 根 glob）；d1 时点 371。本次全仓 collect 3292 vs d1 日志 3264，差 +28 = 审查轮自身写入 docs/superpowers/audit-runs/ 的 .md 数。
- 根因: 参数化维度绑定活文档目录。后果：(a) F732 的 skip 噪音随每份新文档增长（本轮审查自身贡献 +28）；(b) 任何"全量 N 项"静态计数瞬时过期；(c) 该测试若真启用，每次 docs 变更都改变收集规模。
- 验证: 上述 find/ls/collect 输出对照。
- 建议方向: 并入 F732 处置——恢复执行场所时同步考虑目录范围钉定（如仅 docs/framework/）或生成清单文件钉死快照。

### F770 | pytest addopts 全局含 --cov：collect-only 也会重写 coverage 产物 | observation | M
- 证据: 首次 `uv run pytest --collect-only -q`（未加 --no-cov）输出 "Coverage XML written to file tests/coverage/coverage.xml … Total coverage: 16.08%"——收集态即触发覆盖率合并写盘。
- 根因: pyproject.toml addopts 挂全局 --cov。后果：两段式覆盖率设计（--no-cov 相位读 XML）依赖文件系统时序；任何非完整测试调用（collect-only、单文件调试）都会用 16% 级别的垃圾值覆盖 coverage.xml。若有人随后只跑 `--no-cov` 相位会误判。产物未跟踪（git status 干净），无仓库污染。
- 验证: 本次 collect 输出 + `git status --porcelain` → 干净。
- 建议方向: addopts 中 --cov 改为按需（justfile/CI 传参），或在文档注明调试时须加 --no-cov。

## 3. 误报核查（对四段初审）

**零误报。** 64 条 findings（F701–F719、F726–F750、F751–F764、F776–F790）中，P0×1、P1×11 全部逐条代码级复核成立，P2/M 按 ~70% 抽样复核成立，无一被推翻。关键复核记录：

| Finding | 复核方式 | 结果 |
|---|---|---|
| F701 | 读 test_safe_write.py:62-100 全文 | 成立：两测试自建 lockfile+自 chmod，零 `_acquire_lock` 调用 |
| F702 | sed 435-441 | 成立：`or True` 原样在案 |
| F704 | sed test_cli.py:815-862、test_final_review_fixes.py:50-75 | 成立：step_index 回滚与 prompt 拼接均在测试体内模拟 |
| F705 | sed 515-548 + git ls-files | 成立：写真实 deps.json，宣称的只读 skip 未实现 |
| F708 | src/g5.py:150-171 + test pin 139-163 | 成立：单捕获组 + group(2) + 宽 except |
| F709 | g6_checks.py:44-64 + **g6.py:66 `sorted(glob)`** | 成立且无隐情：管线章节命名为 `chapter-{n:03d}` 零填充（audit_context_cache.py:49 等），字典序=数值序，intro_map ≤ cn 恒成立，守卫确不可达（pin 测试用显式有序列表直调，与生产序一致） |
| F710 | test_g_reconcile.py:1-16,33-46 | 成立：docstring 自认 sidestep |
| F711 | grep HARD_FAIL src/ | 成立：仅 chapter_revision.py:38,97 两处 |
| F712 | ls truth/ 两文件 + grep 10 站点 | 成立 |
| F726 | chapter_loop.py:2567-2571（接线）+ 327-390 两 helper 全文 | 成立：扁平条目喂嵌套期望，`chapter_results.get(skill)` 恒 None → 恒 False；另发现比初审更糟：即使形状修复，`audit_history[-3:]` 取的是跨技能混合尾 3 条，per-skill streak 语义还需要按 skill 过滤 |
| F727 | grep drift_alerts src/ → 唯一消费端 :1794 | 成立 |
| F728/F729 | 测试体 vs dispatch_helper.py:613-635 | 成立："Simulate" 注释自认；`_input_key` 同参双调断相等 |
| F730 | grep src 零调用者 + :2161/:3073 接线 | 成立 |
| F736 | regex 原文 + 测试 | 成立：`第四周Saturday` 经英文分支匹配，`周[一二三四五六日]` 分支无任何用例 |
| F744 | `_FILE_PRIORITY_WEIGHTS` 键表（dispatch_helper.py:253-265） | 成立：键为 "chapter"/"chapter-current"，非 "chapter-current.md"，前支恒 False、后支恒 True |
| F751 | 六组独立内容级验证（详见 §2 初审报告引用行号） | 成立：Hard Rule grep=0、第 2/4/6 节在 :28/:70/:97 齐全、time_period/fanfic_mode 缺席、十个人名/词全 0、hook-ch1-001..003、custom-scene-transition 不存在（74 目录） |
| F752/F753/F754 | scenario 原文 + wc/head report-example.txt + expected-output 原文 | 成立：自引用表格逐字在案；874097B 钢铁是怎样炼成的；四类期望证据路径均为未物化轮次产物 |
| F755 | python3 读 deps drafting 9 项 vs seed.md 6 步 | 成立（缺 review-resonance/foreshadowing-recall/score-arc） |
| F757/F760 | grep 18/68 + scoring.py:88 + thresholds.py:10 | 成立 |
| F756 | 99 条逐一重哈希 | 成立且计数精确 |
| F758/F759/F762/F763 | find 各目录 1 文件 ×5、ls 74 目录、g0_purity.py:26 仅扫 scenario.md、"11 truth" 两处原文 | 成立 |
| F776–F790 | difflib（仅 2 行 H1 差）、sha 三同（df81acba75e3）、manifest abc123/xyz789、黑石饼/老周 novel-output 零命中、32/32 哈希、G0 基线无 G0.13-16、mutation 占位、5/5 孤儿词干 grep、stop_words 单行、sensitive 3 词、genre-config 键差分、.gitkeep-only 目录 | 全部成立 |

**精度注记（不构成误报，供终审修正措辞）**:
1. F751 中 "shenbi-chapter-drafting 声称『然而4x/不过3x/与此同时2x』，实测三词合计 1 次"——实测 `grep -o` 计数为 然而=1、不过=1、与此同时=0，**合计 2 次**（非 1）。结论方向不变（声称 9 次 vs 实际 2 次）。
2. Z7-d F778 称 chapter-7/8/9-example 三文件 2494 字节——实测哈希一致成立；字节数未单独复核（未验证）。

## 4. 覆盖空洞（机械交叉：src ↔ tests 零引用）

对 src/shenbi 全部 45 个非 __init__/__main__ 模块做词干级 tests/ 引用交叉，**零测试引用仅 2 个**：

| 模块 | 判定 |
|---|---|
| src/shenbi/cli_utils.py（22 行） | 非空洞：d1-06:10 显示 100%（经 emit_json 消费端间接覆盖） |
| src/shenbi/gates/g4/book_spine_init.py | **真空洞** → F765（77% 为 import 虚高） |

加上 F766（contracts/skills 三校验器）与初审 F717 已列项（memory_distill 12%、drift baseline 19%、sync_contracts 56%、audit_context_cache 54%、safe_write 锁竞争、dispatcher/cli.py 0%、10×__main__.py 0%），Z7 区覆盖空洞清单至此闭合。<60% 且未被任何段报告点名的模块已全部检出（awk 全表扫描 d1-06，仅上述各项）。

## 5. 严重度异议

### F771 | 跨段严重度不一致：F708/F709/F710/F757（P2）与 F726/F727（P1）同类不同级，建议统一升 P1 | severity-dispute | P1（建议）
- 证据: 失败类别同为"生产特性在正常路径静默失效"：
  - F726（P1）审计级联形状断裂 → 级联永不触发；
  - F727（P1）drift_alerts 无写入端 → 条件步永不运行；
  - F708（P2）G5.3 数值一致性 group(2) IndexError 被吞 → 检查永不发射；
  - F709（P2）future_knowledge 守卫数学不可达 → 检查永不发射；
  - F710（P2）GR.2 不剥 -scores → 生产命名正常通过被误报 FAIL（这是**主动产生错误结果**，比不发射更重）；
  - F757（P2）applicability 机制对 18/82 份 rubric 解析为空 → 声称的权重重归一化永不发生。
- 根因: Z7-a 对"src bug 被 pin"类取 P2（视为死代码/边界），Z7-b 对"死接线"类取 P1（视为正常路径功能错误）。决策表中 P1 = "正常路径可复现功能错误"——G5.3/G6.4 检查失效与 GR.2 假阳性在每次正常 gate 运行中都可复现，与级联失效无本质差别；且"不确定时取更高严重度"。GR.2（F710）甚至输出错误 FAIL（假阳性阻断），接近"契约被静默违反"的 P0 边界。
- 验证: 本报告 §3 各条复核命令。
- 建议方向: F708/F709/F710 升 P1（F710 优先），F757 至少 P1 评估；或终审明示"死检查=不发射"与"死接线=不执行"的降级理由并回写 Z7-b 同类项。

### F772 | F777（P1）降级讨论：零消费者死文件的契约违反 | severity-dispute | 维持 P1（记录张力）
- 证据: F777 的 9 个 chapter-N-draft.md 经词干 grep 全库零引用（本复核抽验 5 个孤儿全部 0 命中）——不进入任何活跃判定路径，无 masking、无错误置信。
- 分析: 按表 P1 字面成立（违反 AGENTS.md G0.9 显式契约）；但"死文件"场景的实际危害等价 P2（死代码）。对照 Z7-d 自身将 F776/F779 维持 P1 的理由（活跃路径：G0.14 锁定 / 快照消费），F777 缺少该理由。
- 建议方向: 终审可接受 P1（按字面）或降 P2（按危害），二选一并说明；不建议为此单独返工。

### 其他严重度复核结论（维持，不另立编号）
- F751 P0 **维持**：决策表 P0 例证"场景断链致测试空转掩盖缺陷"逐字命中；内容级断链六组证据独立复核全中。
- F734 P2 **维持**：弱断言有 unit 层 scored→finalized 真实覆盖（test_phase_runner.py:587）缓解，非裸奔。
- F705 P2 **维持但标注 borderline**：xdist 并发窗口极窄且 finally 恢复；若终审按"tracked 文件可损坏"取数据风险视角可升 P1。
- F776/F779 P1 **维持**（活跃校准/快照路径）。

## 6. 结论

1. 四段初审质量高：64 条 findings 复核零误报，机械计数类声明（43 路径/99 哈希/20 技能/18 技能/16 步/32 副本/68 rubric/10 skip）全部精确复现——初审的量化验证无截断、无凑数。
2. 漏报集中在两类：(a) 检查器/校验器覆盖缺口清单不全（F765 book_spine_init、F766 contracts/skills×3）；(b) 集合式弱断言清点不全（F767）。均为 P2/M 增量，无新增 P0/P1 级漏报。
3. 主要系统性风险仍由初审 F751（P0 场景断链）与 F726/F727（P1 死接线）承载；复核确认其证据与定级。
4. 本轮角度新增可操作项：F769（doc_links 计数随文档增长）、F770（collect-only 覆盖率副作用）、F768（验证声明可复现性规范）。

— 复核完毕。所有验证命令输出已在审查记录中留痕；未验证项已在文中逐处标注。
