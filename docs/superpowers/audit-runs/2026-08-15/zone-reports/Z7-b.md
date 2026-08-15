# Z7-b 段报告 — tests/{pipeline,gates,integration,property,benchmark,golden,pressure-tests,coverage} 深读审查

- 审查轮：2026-08-15（全项目深度审查）
- 审查方式：只读语义深读；**未执行任何测试**（正确性靠读代码 + 签名 grep + 只读 python 核验脚本判断）
- 清单：docs/superpowers/audit-runs/2026-08-15/zones/Z7-b.files（73 个文件，全部覆盖，见文末统计）
- 编号段：F726–F750（25 条，全部用尽）
- 交叉参照：docs/superpowers/audit-runs/2026-08-15/d1/d1-06-coverage-gaps.log（下称 d1-06）

## 发现汇总（按严重度）

| 编号 | 标题 | 严重度 | 文件 |
|---|---|---|---|
| F726 | 审计级联（cascade）生产接线形状不匹配 → 永不生效；测试各自为政掩盖 | P1 | tests/pipeline/test_audit_cascading.py |
| F727 | drift-guidance 条件步骤死接线（PipelineState 无 drift_alerts 字段）；MagicMock 虚构属性自证 | P1 | tests/pipeline/test_chapter_steps_restructured.py |
| F728 | SharedAuditContext 注入测试在测试体内"重实现"生产注入块；生产块（dispatch_helper.py:615-634）零覆盖 | P1 | tests/pipeline/test_audit_context_cache.py |
| F729 | C1 回归守卫恒真断言（同一 helper 调两次断言相等），无法检测注入块 key 漂移 | P1 | tests/pipeline/test_dispatch_helper_keys.py |
| F730 | test_volume_align 测的是孤儿模块（volume_align.py 零调用者）；已接线孪生实现 _check_volume_map_alignment 无 pipeline 区测试 | P2 | tests/pipeline/test_volume_align.py |
| F731 | test_docs_accuracy 4 处 pytest.skip 中 3 处"File not yet created"为死分支（文件已存在且有硬断言兄弟测试） | P2 | tests/integration/test_docs_accuracy.py |
| F732 | doc-links 检查在任何场所都不执行（本地 371 项 skip + nightly schedule 注释）；且逐文件 spawn 子进程 | P2 | tests/integration/test_doc_links.py |
| F733 | test_gate_manifest 错标 `@pytest.mark.last`（被快测套件排除且不计覆盖）；历史 list 分支（81-85/104-106）零覆盖 | P2 | tests/gates/test_gate_manifest.py |
| F734 | test_finalize_sets_state 弱断言 `assertIn(state, ["scored","finalized"])` — finalize 完全坏掉也通过 | P2 | tests/integration/test_gate_cli.py |
| F735 | TestEmergencyCleanup 两个自说自话测试：零断言 + 对生产从不调用的 state.save 设 side_effect | P2 | tests/pipeline/test_crash_recovery.py |
| F736 | "Chinese week label"测试经英文分支通过；中文周标签正则分支（周[一二三四五六日]）零覆盖 | P2 | tests/gates/g4/test_title_check.py |
| F737 | audit_context_cache 模块覆盖仅 54%：world_rules/characters/style/hooks/volume 分支 + 截断函数全部未测 | P2 | tests/pipeline/test_audit_context_cache.py |
| F738 | parallel_dispatch 重试/退避/异常循环（77-128、165-188）零覆盖；唯一测试只断言常量不等式 | P2 | tests/pipeline/test_parallel_dispatch_backoff.py |
| F739 | snapshot-skip 压力提示词编码"完整副本"快照语义，与差分 hash+环形缓冲实现（snapshot_diff.py）相矛盾 | P2 | tests/pressure-tests/prompts/snapshot-skip-pressure.md |
| F740 | audit-skipping 压力提示词"全 33 维必跑、跳过=FAIL"与代码内审计级联跳过（CASCADABLE_AUDITS）教义冲突 | P2 | tests/pressure-tests/prompts/audit-skipping-pressure.md |
| F741 | tests/golden/README.md 描述的 golden 评测集（chapter-N-original.md 等）不存在，无任何测试消费 | P2 | tests/golden/README.md |
| F742 | norecursedirs 写 `tests/benchmarks`（复数）但实际目录是 `tests/benchmark`（单数）；benchmark 套件本身为空壳 | P2 | tests/benchmark/（+pyproject.toml:414） |
| F743 | 状态一致性校验不检查 current_step ↔ CHAPTER_STEPS[step_index] 一致性；测试夹具自身就带着错位索引 | P2 | tests/pipeline/test_state_machine_heal.py |
| F744 | 权重表测试近恒真（`"chapter" in str(dict)`）；per-file 截断上限 _INPUT_MAX_CHARS_PER_FILE（:315）未测 | P2 | tests/pipeline/test_budgeted_truncate.py |
| F745 | "executed_concurrently"测试只数 call_count（无并发验证）；single-writer 守卫靠 grep 源码文本 | M | tests/pipeline/test_parallel_steps.py |
| F746 | 名为 returns_empty 实为断言 raises；"short title valid"未过 gate（恒真长度检查） | M | tests/pipeline/test_title_gate_integration.py |
| F747 | st.data() 不 draw → 常量"属性"重复读 YAML 20 次 | M | tests/property/contracts/test_registry_consistency.py |
| F748 | 行内遗留困惑注释（"Wait, 1 from ch1..."）；unknown-skill 分支未测 | M | tests/pipeline/test_audit_cascading.py |
| F749 | hook_fulfillment 实现扫描全 plan 文本而非 Section 7（docstring 与实现漂移；plan 正文引用旧钩子 ID 会误报），测试未覆盖该边界 | P2 | tests/gates/g4/test_hook_fulfillment.py |
| F750 | 集成测试手工捏造 worldbuilding 项目，而真实 world fixtures 已存在（G0.9 边界争议，见正文） | P2 | tests/integration/test_gate_cli.py |

严重度统计：P0×0，P1×4，P2×17，M×4。

---

## Per-file 报告

### tests/benchmark/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [目录占位]
- findings: 无（空文件）。但见 F742（benchmark 套件空壳 + norecursedirs 拼写不匹配）。
- 验证命令: `wc -c tests/benchmark/.gitkeep` → 0
- 置信度: high

### tests/benchmark/__init__.py
- 处置: deep-read
- 声称检查的不变量: [包声明 "Shenbi benchmark test package."]
- findings: [F742]
- 验证命令: `ls tests/benchmark/` → 仅 .gitkeep + __init__.py；`git ls-files tests/coverage/` → 1（.gitkeep）；`sed -n '405,425p' pyproject.toml` → norecursedirs 含 `tests/benchmarks`（复数，不存在的目录）
- 置信度: high
- F742 | benchmark 套件空壳 + norecursedirs 死条目 | error | P2 | tests/benchmark/__init__.py:1 + pyproject.toml:414 | 目录宣称 benchmark 层（AGENTS.md 项目结构列出 benchmark），但无任何基准测试；pyproject 排除的是 `tests/benchmarks` 而实际目录为 `tests/benchmark`，若将来放入测试文件会被意外收集 | 上述命令 | 补基准测试或删除空壳；修正 norecursedirs 拼写

### tests/coverage/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [coverage HTML/XML 输出目录占位]
- findings: 无。工作树中 29MB HTML 产物均未被 git 跟踪（`git ls-files tests/coverage/` → 仅 .gitkeep），非仓库卫生问题。
- 验证命令: `git ls-files tests/coverage/ | wc -l` → 1
- 置信度: high

### tests/gates/__init__.py
- 处置: deep-read
- 声称检查的不变量: [空包文件]
- findings: 无
- 验证命令: `cat tests/gates/__init__.py` → 空
- 置信度: high

### tests/gates/g4/__init__.py
- 处置: deep-read
- 声称检查的不变量: [空包文件]
- findings: 无
- 验证命令: `cat tests/gates/g4/__init__.py` → 空
- 置信度: high

### tests/gates/g4/test_hook_fulfillment.py
- 处置: deep-read
- 声称检查的不变量: [G4.cd.hook_fulfillment：plan 声明的钩子必须出现在章节正文；缺失→issue；无钩子/plan 缺失→空]
- findings: [F749]
- 验证命令: 读 src/shenbi/gates/g4/chapter_drafting.py:24-55；d1-06 第 72 行（chapter_drafting.py 78%，142-166 缺失）
- 置信度: high
- F749 | hook ID 提取范围与 docstring/测试意图漂移 | error | P2 | src/shenbi/gates/g4/chapter_drafting.py:41-49 vs 测试 test_hook_fulfillment.py:9-14,46-52 | 实现用 `re.findall(r"[A-Z]{2,4}-\d+", plan_text)` 扫描**整个 plan 文本**而非 docstring 声称的"Section 7 (Hook Ledger)"；真实 plan 的正文（如"承接第 2 章 MH-001"）会让 MH-001 被当作本章必交付钩子 → 误报 unfulfilled。测试全部用只含 Hook Ledger 表的极简 plan，未覆盖该边界；test_handles_hook_ids_with_letters（:46）甚至无 `## 7.` 头也通过，锁死了宽松行为 | 未执行测试（读码判定）；`grep -n "def check_hook_fulfillment" -A 31 src/shenbi/gates/g4/chapter_drafting.py` | 提取应限定在 Section 7 区段内；测试补"plan 正文引用旧钩子 ID"负例

### tests/gates/g4/test_title_check.py
- 处置: deep-read
- 声称检查的不变量: [G4.cd.title：含章号→HARD FAIL；重复→HARD FAIL；星期标签→WARN；诗意 1-4 字→通过]
- findings: [F736]
- 验证命令: `uv run python -c "...day_pattern.search('第四周Saturday'/'周五'/'第四周')"` → True/True/**False**
- 置信度: high
- F736 | 中文周标签分支零覆盖，测试名与实际验证分支不符 | error | P2 | tests/gates/g4/test_title_check.py:20-22 + src/shenbi/gates/g4/chapter_drafting.py:83-86 | `第四周Saturday` 中 `周[一二三四五六日]` 不匹配（周后跟 'S'），断言经英文 "Saturday" 分支通过；中文分支（周五/周一等）无任何测试，正则若被改坏不会被发现。另：docstring 声称 "Thematic naming encouraged (1-4 Chinese characters)" 检查在实现中不存在（标题长度无检查）——测试也未覆盖 | 见验证命令输出 | 测试名改为覆盖 `周x` 字面量或补 `周五` 用例；删除/实现 docstring 中的长度检查声明

### tests/gates/test_gate_manifest.py
- 处置: deep-read
- 声称检查的不变量: [record/get 往返一致；manifest 层级结构 gates→phase→chapter→skill→gate；缺失返回 None；并发写不丢结果（线程锁）]
- findings: [F733]
- 验证命令: 读 src/shenbi/gates/gate_manifest.py（签名一致：record_gate_result(gate_manifest_dir, phase, chapter, skill, gate, result) / get_gate_result(manifest_dir, phase, chapter, skill, gate)）；`grep -n Thread /Users/.../parallel_dispatch.py` → ThreadPoolExecutor（进程内锁模型成立）；d1-06:109（gate_manifest.py 78%，缺 33-34、81-85、104-106）；justfile:23-24（`-m "not last"` 快测 + `-m "last" --no-cov`）
- 置信度: high
- F733 | `@pytest.mark.last` 错置 + 历史列表分支零覆盖 | error | P2 | tests/gates/test_gate_manifest.py:15；src/shenbi/gates/gate_manifest.py:80-87,104-105 | marker 语义是"必须最后跑（如覆盖阈值）"（pyproject.toml:438），该纯 tmpfile 功能测试被错标 → 从 `just test` 快测套件排除，且 last 阶段 `--no-cov` 不计覆盖。没有任何测试对同一 (skill,gate) 记录两次 → record 的 list 追加分支（:80-87）与 get 的"取最近一条"分支（:104-105）零覆盖（与 d1-06 一致）。并发测试写 distinct (skill,chapter) 对，也测不到 list 路径 | d1-06 第 109 行 + justfile:23-24 | 去掉错置 marker；补"同 gate 二次记录 + get 返回最新"用例

### tests/golden/README.md
- 处置: deep-read
- 声称检查的不变量: [golden 评测集：10-20 章真实产出 + 人工评分 + 校准报告，用于回归与评分校准（P0.5）]
- findings: [F741]
- 验证命令: `ls tests/golden/` → 仅 README.md；`grep -rn "tests/golden" tests/ src/ --include="*.py"` → 无任何 Python 引用；`git ls-files tests/golden` → README.md
- 置信度: high
- F741 | golden 评测集为纸面承诺，校准回路未接线 | error | P2 | tests/golden/README.md:3-10 | README 描述 chapter-N-original.md / chapter-N-scores.json / calibration-report.md，全部不存在；仓库无任何代码消费 tests/golden/。Z7 关注的 golden/baseline 对比逻辑实际在 tests/unit/records/test_golden_parse.py 与 tests/regenerate-baselines.sh（本区外）。评分校准（自动评分 vs 人工分 Pearson/Spearman）无落地物，属死脚手架/文档↔现实漂移 | 上述命令 | 落地 golden 集（真实管线产出）或删除 README 并在测试计划中移除引用

### tests/integration/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [目录占位]
- findings: 无（0 字节）
- 验证命令: `wc -c tests/integration/.gitkeep` → 0
- 置信度: high

### tests/integration/__init__.py
- 处置: deep-read
- 声称检查的不变量: [包声明]
- findings: 无
- 验证命令: `cat` → `"""Shenbi integration test package."""`
- 置信度: high

### tests/integration/test_doc_links.py
- 处置: deep-read（含 skip 处置判断）
- 声称检查的不变量: [docs/ 与根 *.md 的 markdown 链接可解析（mlc-config 忽略外链，纯内链检查）]
- findings: [F732]
- skip 处置: `_require_mlc`（:17-20）session 级 skip —— **keep（写法本身正确且有清晰理由），但接线判 stale**：nightly.yml:19-21 schedule 被注释（仅 workflow_dispatch），ci.yml/docs.yml 不装 markdown-link-check → 该检查在本地（371 项全 skip）与 CI（永不运行）**均不执行**。nightly.yml:11-13 自己承认"internal links are a valid signal but gated here for simplicity"——本测试配置 ignorePatterns 已排除全部 http(s) 外链，flaky 理由对本文件不成立。
- 验证命令: `which markdown-link-check` → not found（本地全 skip 实证）；`grep -n "schedule\|markdown-link-check" .github/workflows/*.yml` → nightly.yml:19-20 注释、:68 安装；codeql/pre-commit 有 schedule 而 nightly 无；`cat tests/fixtures/mlc-config.json` → `ignorePatterns: ^https?://`
- 置信度: high
- F732 | 内链检查无任何执行场所 + 371 次子进程 spawn | optimization | P2 | tests/integration/test_doc_links.py:17-20,36-44 + .github/workflows/nightly.yml:19-21,68 | 测试基础设施存在但死接线：371 个参数化项在每次本地运行中产生 371 条 skip 噪音，唯一可能执行路径（nightly）的 schedule 被注释。当真运行时每文件 spawn 一个 mlc 子进程（371 次）| 上述命令 | 恢复 nightly schedule 或将内链检查并入 ci.yml（如 docs job）；可合并为单测试内循环以减少进程数

### tests/integration/test_docs_accuracy.py
- 处置: deep-read（含 skip 处置判断）
- 声称检查的不变量: [8 个指定文档的 code-span 文件路径必须存在（ALLOWED_MISSING 白名单）；chapter-file-format.md 存在且含 META/strip/not-prose 声明]
- findings: [F731]
- skip 处置: 4 处 pytest.skip 逐条：
  - :64 `not present (may be added by later PR)` → **keep**（DOCS_TO_CHECK 是白名单驱动，缺文档时 skip 合理，非 masking）
  - :85/:94/:103 `File not yet created` → **stale**（文件自 PR #19 起存在；且 test_chapter_file_format_doc_exists（:77-79）对其存在性硬断言——若真缺失该测试直接 FAIL，三个 skip 分支不可达，纯死代码）
- 验证命令: `ls docs/framework/chapter-file-format.md` → 存在；`git log --oneline -2 -- docs/framework/chapter-file-format.md` → dd1fc62 (PR #19)
- 置信度: high
- F731 | 三处 "File not yet created" skip 为不可达死分支 | error | P2 | tests/integration/test_docs_accuracy.py:85,94,103 | 文档已存在 27+ 天；存在性由 :77 的硬断言测试守卫，skip 守卫永不可达，误导读者以为文档可能缺席 | 上述命令 | 删除三处 skip 守卫（保留 :64 的白名单 skip）

### tests/integration/test_gate_cli.py
- 处置: deep-read
- 声称检查的不变量: [G4 PASS 写 marker / FAIL 不写 / 无 round_dir 不写；G2 不写 marker；scoring 缺 marker exit 3 / 有 marker exit 0；T3 需 G6-<pipeline>-<type>.json；phase_runner 生命周期 start→post-skill→pre-score→post-score→finalize；G7.16 检测未 finalize 阶段]
- findings: [F734, F750]
- 验证命令: `grep -n "exit(3)\|G4-{skill_name}\|G6-{pipeline_name}" src/shenbi/scoring.py` → :377 exit(3)、:200/:220 marker 命名一致；`grep -n "def dispatch_escalation" src/shenbi/pipeline/revision_router.py` → :144；读 phase_runner.py:304-333（finalize 语义）；tests/unit/test_phase_runner.py:587-650（finalize 转换单测覆盖存在）
- 置信度: high
- F734 | test_finalize_sets_state 弱断言掩盖 finalize 失败 | error | P2 | tests/integration/test_gate_cli.py:437-462 | 断言 `assertIn(state["state"], ["scored","finalized"])`：G5 在测试环境失败时 finalize 什么都不做（state 保持 scored）也通过；注释自认"G5 may fail in test env"。finalize 完全坏掉（如 cmd_finalize 抛错前不落状态）本测试无法发现。缓解：单元层 tests/unit/test_phase_runner.py:587 覆盖 scored→finalized 转换，故非完全裸奔 | 读码 + 上述 grep | 断言收紧为 finalized，或断言 finalize 步骤被记录且失败时报 BLOCKED rc≠0
- F750 | 手工捏造 worldbuilding 项目 vs 真实 world fixtures 并存 | error | P2 | tests/integration/test_gate_cli.py:27-97 | `_make_worldbuilding_project` 手写 novel.json/story_bible/rules/locations/truth 模板（"Content here."），而 tests/fixtures/ 已有真实产物（world-story-bible-example.md、world-rules-example.md、world-locations-example.md、world-power-system-example.md 等）。AGENTS.md："All test scenario inputs must reference tests/fixtures/ paths"。仓库已有 G0.9 边界裁定先例（test_g4_directory.py:4-7、test_trigger_context.py:3-5 把"gate 内部输入/接线单测"豁免），但本测试是**完整 skill 产出形态的场景**（PASS 路径的 story_bible 结构即被测语义的一部分），与豁免类别不符；手写中文占位文本过 gate 的方式可能与真实产物分布不同（如 bullet 密度、字数） | `ls tests/fixtures/ | grep world` → 5 个 world-*-example.md；`find tests/fixtures -iname "*world*"` | 将 story_bible/rules/locations 等替换为真实 fixture 拷贝，仅保留目录组装逻辑

### tests/pipeline/__init__.py
- 处置: deep-read
- 声称检查的不变量: [空包文件]
- findings: 无
- 验证命令: `cat` → 空
- 置信度: high

### tests/pipeline/test_audit_cascading.py
- 处置: deep-read
- 声称检查的不变量: [N=3 零 HARD 失败连击→可级联审计 skip；HARD 失败/历史不足→不 skip；ALWAYS_RUN/CORE 永不 skip；_audit_short_name 前缀剥离；_get_audit_history 排除当前章及以后]
- findings: [F726, F748]
- 验证命令: `uv run python -c "..._get_audit_history→_should_skip_audit..."` → `history entry shape: {'skill': 'dialogue', 'chapter': 1, ...}`；`should_skip via _get_audit_history output: False`；`should_skip via hand-built nested shape: True`；`grep -n "_get_audit_history\|_should_skip_audit" src/shenbi/pipeline/chapter_loop.py` → 生产接线 :2567-2571
- 置信度: high
- F726 | 级联永不触发：两个 helper 的数据形状在生产接线上不兼容，测试隔离测各自带形状掩盖 | error | P1 | src/shenbi/pipeline/chapter_loop.py:2567-2571（接线）、:327-364（_should_skip_audit 期望 per-chapter dict：`{skill: {...}}`）、:367-390（_get_audit_history 返回扁平 `{skill,chapter,passed,...}`）+ tests/pipeline/test_audit_cascading.py:129-155（"wiring"测试只直接调 _should_skip_audit，从未把 _get_audit_history 输出喂进去） | 生产把扁平条目喂给期望嵌套字典的判定函数：`chapter_results.get(skill)` 恒 None → `return False` → **级联 skip 在真实管线中一次都不会发生**。后果：(a) 8 个 cascadable 审计每章全量调度，持续性 token 浪费（该特性存在的唯一目的就是省钱）；(b) 特性死接线。测试用例全部用与 _should_skip_audit 合身的嵌套形状手搓输入（:11-15 等），唯一声称验证接线的 :129 也没走 _get_audit_history，故形状断裂对套件不可见 | 见验证命令实跑输出（False vs True） | 二选一：让 _get_audit_history 返回嵌套形状，或让 _should_skip_audit 接受扁平条目；并补"真 wiring"测试：build state → _get_audit_history → _should_skip_audit
- F748 | 遗留困惑注释 + unknown-skill 分支未测 | error | M | tests/pipeline/test_audit_cascading.py:115；src/shenbi/pipeline/chapter_loop.py:343-344 | `# 2 from ch1 + 1 from ch2? Wait, 1 from ch1 + 2 from ch2 = 3` 是作者自我纠正的草稿注释留在代码里；_should_skip_audit 的 unknown-skill→False 防御分支无测试 | 读文件 | 清理注释；补 unknown skill 用例

### tests/pipeline/test_audit_context_cache.py
- 处置: deep-read
- 声称检查的不变量: [build_shared_audit_context 提取章节字段；同输入两次构建一致；SharedAuditContext 字段可注入 raw_inputs（Task 6 Step 2）]
- findings: [F728, F737]
- 验证命令: `grep -rn "_INJECT_FROM_CACHE\|shared_context" src/shenbi/pipeline/dispatch_helper.py` → 生产注入块 :613-635（`if shared_context is not None:` 起）；d1-06:128（dispatch_helper.py 80%，615-634 缺失）；d1-06:119（audit_context_cache.py 54%，55-103 缺失）
- 置信度: high
- F728 | 注入测试重实现生产逻辑（模拟自证），生产注入块零覆盖 | error | P1 | tests/pipeline/test_audit_context_cache.py:50-74（"Simulate the injection logic from _build_skill_prompt"）vs src/shenbi/pipeline/dispatch_helper.py:613-635 | 测试体内复制了 _INJECT_FROM_CACHE 逻辑并断言副本的行为；生产注入块（真代码）从未被任何测试执行（d1-06 确认 :615-634 缺失）。若生产块被改坏/删除（如 key 退化为 basename——正是 spec §6.1 C1 防的 bug），本测试照常绿。测试注释自己承认"Simulate" | 上述 grep + d1-06:128 | 改为调 `_build_skill_prompt(..., shared_context=ctx)` 断言 user_prompt 中的 `<document name="truth/world_rules.md">`（与 test_dispatch_helper_xml.py 同模式）
- F737 | 模块 54% 覆盖：5 个数据源分支与两个截断函数全未测 | error | P2 | tests/pipeline/test_audit_context_cache.py:12-37（只建 chapters/chapter-001.md）vs src/shenbi/pipeline/audit_context_cache.py:53-103 | world_rules/character_matrix/style_profile/pending_hooks/volume_map 分支（:53-74）、_summarize_if_large 截断（:84-88）、_extract_volume_chapter（:91-103）无测试——共享上下文缓存的"省钱"主体（truth 文件预抽取与截断预算）完全裸奔；断言 :23 `ctx.world_rules is not None or ctx.world_rules == ""` 等价于 `is not None` 且写得费解 | d1-06:119 | 为每个源文件建最小 fixture（可直接用 tests/fixtures 真实产物）+ 超 5000/3000 字截断用例

### tests/pipeline/test_budgeted_truncate.py
- 处置: deep-read
- 声称检查的不变量: [高优先级文件少截断；总量≤预算×1.1；等大小时高优先级保留更多；权重表存在]
- findings: [F744]
- 验证命令: 读 src/shenbi/pipeline/dispatch_helper.py:253-317（_get_priority 子串匹配、_budgeted_truncate 加权分配 + :315 per-file 上限）；权重键核对：'chapter-current.md'→含'chapter'→1.0、'archive_notes.md'→'archive'→0.2 ✓
- 置信度: high
- F744 | 权重表测试近恒真；per-file 截断上限未测 | error | P2 | tests/pipeline/test_budgeted_truncate.py:22-27；src/shenbi/pipeline/dispatch_helper.py:314-315 | `assert "chapter-current.md" in _FILE_PRIORITY_WEIGHTS or "chapter" in str(_FILE_PRIORITY_WEIGHTS)`：前者恒 False、后者因键名"chapter"存在恒 True —— 近恒真断言，测名声称"weights exist for all keys"但无"all"语义；:315 `result[name] = result[name][:_INPUT_MAX_CHARS_PER_FILE]` 的单文件天花板从未被测试（超长单文件场景缺失，这是防单文件爆 token 的关键边界）| 读码（未执行测试） | 断言具体键与权重值（如 `_FILE_PRIORITY_WEIGHTS["chapter"] == 1.0`）；补超长单文件用例验证 per-file cap

### tests/pipeline/test_chapter_steps_restructured.py
- 处置: deep-read
- 声称检查的不变量: [CHAPTER_STEPS ≤18 且无废弃技能；escalation-review 不在步内；intent-management 仅卷边界；非条件步恒跑；drift-guidance 3+ 告警触发；chapter-revision 随审计发现]
- findings: [F727]
- 验证命令: `uv run python -c "from shenbi.pipeline.chapter_loop import CHAPTER_STEPS; print(len(...))"` → 16 步；`grep -rn "drift_alerts" src/shenbi/` → 唯一命中 chapter_loop.py:1794（getattr 消费端，无任何写入端）；读 state.py:162-183（PipelineState 全字段，无 drift_alerts）；`grep -n "drift-guidance" src/shenbi/pipeline/triggers.py` → :262（卷级 trigger 仍会派发该技能——缓解项）；`grep -n "def _should_run_step" -A 23 chapter_loop.py` → :1845-1846 调 _drift_guidance_triggered
- 置信度: high
- F727 | drift-guidance 条件步骤死接线，测试用虚构属性自证 | error | P1 | tests/pipeline/test_chapter_steps_restructured.py:76-87（MagicMock 手设 state.drift_alerts）+ src/shenbi/pipeline/chapter_loop.py:1792-1795 + src/shenbi/pipeline/state.py:162-183 | `_drift_guidance_triggered` 用 `getattr(state, "drift_alerts", [])`，但 PipelineState **没有该字段**且全仓库无写入点 → 生产中恒为 [] → 恒 False → CHAPTER_STEPS 里的 shenbi-drift-guidance 条件步**永远不会跑**。测试用 MagicMock 挂上虚构属性，验证了一个生产不可能出现的状态形状（mock 自证），把死接线藏住。缓解：该技能仍有卷级 trigger 路径（triggers.py:262），故非技能级丢失，但章内条件步是死代码且其"3+ 连续漂移告警"语义从未生效 | 见验证命令（grep 唯一命中消费端） | 要么给 PipelineState/ChapterLoopStateData 加 drift_alerts 字段并在漂移检测处写入，要么删除该条件步分支与对应测试

### tests/pipeline/test_closure_context.py
- 处置: deep-read
- 声称检查的不变量: [闭包各步 PathContext（ch100→arc8/vol5）；step6 G4 路径 chapter-100-long-span.md；全 10 步 prompt 构建无 UnresolvedPathError；dispatch_skill 注入 [path-context] 行；escalation/anchor genesis 哨兵与真实接线]
- findings: 无。质量高：真实 fixture（volume-map-xinghuo.md）；monkeypatch 目标正确（dh._dispatch_via_api / rr.dispatch_skill / gs.* 为消费端命名空间）；wiring 测试走真实 run_genesis_step/run_closure 链路
- 验证命令: `grep -n "_dispatch_via_api" dispatch_helper.py` → :1492 定义、:1866 模块内调用（patch 有效）；`grep -n "def dispatch_escalation" revision_router.py` → :144 签名匹配；`grep -n "def default" state.py` → :225；`ls tests/fixtures/volume-map-xinghuo.md` → 存在
- 置信度: high

### tests/pipeline/test_cn_extract.py
- 处置: deep-read
- 声称检查的不变量: [ch5+ 节点非桥表垃圾；五桥段全聚合；vol-1@26/vol-2@36 边界；续作行排除；中文卷名真名解析；英文裸行不匹配；双 Objective 形式；窗口边界含端点；多位/带空格章节号]
- findings: 无。真实 fixture 驱动（G0.9/G0.11 在 docstring 声明）；BridgeRow 字段序核对（content,kind,target_volume,activation,status）✓；边界与负例充分
- 验证命令: `grep -n "class BridgeRow" -A 6 src/shenbi/pipeline/_shared.py`；函数签名 grep（read_chapter_node/read_bridges/bridges_for_chapter/_resolve_volume_at_runtime）全匹配
- 置信度: high

### tests/pipeline/test_crash_recovery.py
- 处置: deep-read
- 声称检查的不变量: [SIGTERM/SIGINT+atexit 注册；信号置 flag 并恢复 SIG_DFL；emergency flag 触发清理；清理 best-effort 不抛；reset 恢复默认处理器]
- findings: [F735]
- 验证命令: 读 src/shenbi/pipeline/crash_recovery.py（函数内局部 import 确认：:124 save_state、:145 clear_staging → 测试 patch shenbi.pipeline.machine.save_state / shenbi.pipeline.checkpoint.clear_staging 目标正确）；test_emergency_cleanup_with_mock_state（:82-90）对 save/snap/clear 的断言是真实有效的
- 置信度: high
- F735 | TestEmergencyCleanup 两个自说自话测试 | error | P2 | tests/pipeline/test_crash_recovery.py:144-158 | (a) test_saves_pipeline_state（:145-149）调用后**零断言**（正文只剩注释）——测试名声称验证保存但什么都没验证；(b) test_cleanup_failure_does_not_prevent_exit（:151-158）对 `state.save` 设 RuntimeError side_effect，但生产调用的是模块函数 `save_state(state,...)`（crash_recovery.py:124），`state.save` 从不被调用 → 模拟的失败永不发生，"失败不阻断退出"未被真验证。注：真正的失败路径已由 :92-99 的孪生测试正确覆盖（patch save_state side_effect），故这两个是冗余+误导而非掩盖 | 读码对照 crash_recovery.py:124 | 删除 (a)；(b) 改为 patch `shenbi.pipeline.machine.save_state` 抛错并断言不抛

### tests/pipeline/test_dispatch_helper_autogen_strip.py
- 处置: deep-read
- 声称检查的不变量: [AUTO-GENERATED 与 AUTO-CHECK 块被剥离；无块时原样保留；混合块全剥离]
- findings: 无。纯函数测试，_strip_autogen_blocks 定义于 dispatch_helper.py:181 ✓
- 验证命令: `grep -n "def _strip_autogen_blocks" src/shenbi/pipeline/dispatch_helper.py` → :181
- 置信度: high

### tests/pipeline/test_dispatch_helper_cap_raise.py
- 处置: deep-read
- 声称检查的不变量: [finish_reason=length → cap 提升重发一次且 max_tokens 递增；content_filter → 硬失败无重发；cap 触顶 → fail-fast 无重发；持续 length → 1 次重发后 fail-fast]
- findings: 无。monkeypatch 全部打在 dispatch_helper 模块命名空间的消费点（_call_llm_streaming_with_retry/_build_skill_prompt/_write_parsed_outputs/_parse_structured_output/_get_skill_max_tokens/_MODEL_OUTPUT_CEILING）——目标正确；_MODEL_OUTPUT_CEILING 在 :1594/:1601/:1608 以模块全局读取，patch 生效；max_tokens 经 kwargs 传递（:1566/:1626）与 mock 捕获方式匹配。走真实 _dispatch_via_api 主流程，仅边界 mock，测试真实性好
- 验证命令: `grep -n "_MODEL_OUTPUT_CEILING\|max_tokens=\|def _dispatch_via_api" dispatch_helper.py` → :82(=65536)、:1566、:1593-1594、:1626
- 置信度: high

### tests/pipeline/test_dispatch_helper_finish_reason.py
- 处置: deep-read
- 声称检查的不变量: [streaming chunk 的 finish_reason（length/stop/content_filter/无 choices）被正确捕获且内容拼接正确]
- findings: 无。SimpleNamespace 伪 chunk 是对 OpenAI 流接口的合理替身；_call_llm_streaming 4 元组返回值签名核对（:1392-1397）✓
- 验证命令: `grep -n "def _call_llm_streaming(" -A 5 dispatch_helper.py`
- 置信度: high

### tests/pipeline/test_dispatch_helper_glob.py
- 处置: deep-read
- 声称检查的不变量: [通配符展开为多文件；非通配符单文件；缺失返回空]
- findings: 无。_resolve_read_path(project_dir, read_path) 签名核对（:397）✓
- 验证命令: `grep -n "def _resolve_read_path" dispatch_helper.py` → :397
- 置信度: high

### tests/pipeline/test_dispatch_helper_keys.py
- 处置: deep-read
- 声称检查的不变量: [_input_key 产出项目相对路径；同名 basename 不同目录可区分；注入 key 与磁盘读 key 同形（C1 回归守卫）]
- findings: [F729]
- 验证命令: 读 src/shenbi/pipeline/dispatch_helper.py:505-520（_input_key）与 :613-635（注入块）
- 置信度: high
- F729 | C1"回归守卫"为恒真断言，无法守护注入块 | error | P1 | tests/pipeline/test_dispatch_helper_keys.py:40-42 | `injected_key = _input_key(truth_file, project); disk_key = _input_key(truth_file, project); assert injected_key == disk_key` —— 同一 helper 对同一输入调用两次再断言相等，等价于 `x == x`。docstring 声称"if the injection block used basename keys ... would appear twice"的回归守卫，但注入块（dispatch_helper.py:613-635）根本不在测试路径上：把注入块改回 basename key，本测试依旧绿。唯一非平凡断言是 `"/" in injected_key` | 读码对照注入块 | 断言改为直接检查 _build_skill_prompt(shared_context=...) 产出的 user_prompt 中 document 标签 key 形态（与 F728 同修）

### tests/pipeline/test_dispatch_helper_ledger.py
- 处置: deep-read
- 声称检查的不变量: [_record_token_usage 持久化到 cost/token-ledger.jsonl 且内存累计并存；_log_token_usage 双形态（裸 Usage/包装 response）都落账；无 usage 静默跳过]
- findings: 无。SimpleNamespace 边界替身 + 真实文件写断言；签名核对（_log_token_usage:1278-1282 / _record_token_usage:1314-1318）✓；dead-wire 修复历史在 docstring 记录清楚
- 验证命令: `grep -n "def _record_token_usage\|def _log_token_usage" -A 4 dispatch_helper.py`
- 置信度: high

### tests/pipeline/test_dispatch_helper_xml.py
- 处置: deep-read
- 声称检查的不变量: [prompt 用 <document> 标签而非嵌套 ``` 围栏]
- findings: 无（轻微观察：`"```\n```" not in` 只防相邻围栏，嵌套有内容时不拦截——但作为守卫足够，且依赖真实 SKILL 契约读取路径）
- 验证命令: _build_skill_prompt 存在（多处引用）✓
- 置信度: high

### tests/pipeline/test_executor_config.py
- 处置: deep-read
- 声称检查的不变量: [drafting max_tokens>16384；3 个 score-* 温度≤0.2；9 个判别式 review 温度≤0.2]
- findings: 无。配置契约测试；executor_config.toml 实际值核对（drafting max_tokens=32768:12、score-arc 0.1:35）✓
- 验证命令: `grep -n "max_tokens\|temperature\|overrides" executor_config.toml`
- 置信度: high

### tests/pipeline/test_g4_directory.py
- 处置: deep-read
- 声称检查的不变量: [快照族目录需 manifest 命名条目；characters/ 不需要；空目录 FAIL；闭包快照目录 = snapshots/chapter-{total:03d}/，total 未知→空串]
- findings: 无。G0.9 边界裁定在 docstring 显式记录（目录内容=真实快照拷贝，manifest.json=gate 内部输入）；走真实 g4_generic_generative；fixture tests/fixtures/snapshot-dir/ 存在（chapter-005/006 真实拷贝）
- 验证命令: `ls tests/fixtures/snapshot-dir/`；`grep -n "def g4_generic_generative\|def _closure_snapshot_dir"` → generic.py:22 / closure.py:166
- 置信度: high

### tests/pipeline/test_linguistic_drift.py
- 处置: deep-read
- 声称检查的不变量: [章节缺失→空；系统词密度高→告警；破折号密度高→告警]
- findings: 无（轻微：只测两个正向告警维度，linguistic_drift.py 其余维度（d1-06:170 缺 74,77-78 等）覆盖依赖他处；非本文件缺陷）
- 验证命令: `grep -n "def check_linguistic_drift" linguistic_drift.py` → :314 签名匹配
- 置信度: high

### tests/pipeline/test_parallel_dispatch_backoff.py
- 处置: deep-read
- 声称检查的不变量: [RETRY_JITTER ≥ RETRY_BACKOFF_BASE（去相关并行 worker）]
- findings: [F738]
- 验证命令: d1-06:135（parallel_dispatch.py 65%，77-128、165-188 缺失）；`grep -rn "def test" tests/unit/pipeline/test_parallel_dispatch*.py` → 仅 task 创建/consolidate/safety，无重试循环测试；读 parallel_dispatch.py:70-130（_dispatch_with_retry：semaphore、异常捕获、RETRY_BACKOFF_BASE**attempt + uniform(0,JITTER)、All retries exhausted）
- 置信度: high
- F738 | 退避/重试核心循环零测试覆盖 | error | P2 | tests/pipeline/test_parallel_dispatch_backoff.py:8-17 + src/shenbi/pipeline/parallel_dispatch.py:77-128 | 本区唯一相关测试只断言两个常量的大小关系；重试循环本体（失败重试、异常路径、指数退避+jitter 计算、MAX_RETRIES 耗尽返回）在全部测试层（unit+pipeline）零覆盖，与 d1-06 的 77-128/165-188 缺失一致。并发审计波是管线主干路径，重试语义回归（如 off-by-one、sleep 负值）无护栏 | 上述 grep + d1-06 | 用 mock dispatch_skill（success 两次失败一次）驱动 _dispatch_with_retry，断言重试次数与退避单调性（time.sleep 可 patch）

### tests/pipeline/test_parallel_steps.py
- 处置: deep-read
- 声称检查的不变量: [post-draft 两步都被派发；lifecycle 失败不阻断 settling；settling 失败上报；单写者模式（无模块级 _state_lock）]
- findings: [F745]
- 验证命令: `grep -n "def run_parallel_post_draft_steps" -A 45 chapter_loop.py` → :2395（ThreadPoolExecutor(max_workers=2)，positional dispatch_skill 调用与测试的 args[0] 提取兼容；chapter_loop 模块级 import dispatch_skill → patch 目标正确）；读 state.py:178-183（实例级 _lock 注释，不含 "_state_lock" 字面量 → 文本 grep 守卫当前通过）
- 置信度: high
- F745 | 并发名义测试无数证 + 源码文本 grep 守卫脆弱 | error | M | tests/pipeline/test_parallel_steps.py:16-27,82-93 | (a) test_both_steps_executed_concurrently 只断言 call_count==2 与技能集合——"concurrently"无任何验证（无重叠执行、无线程断言），名不符实；(b) test_state_merged_on_main_thread_single_writer 用 `"_state_lock" not in inspect.getsource(state_mod)` —— 文本匹配：将来有人在 state.py 注释里提到 _state_lock 即假阳性失败，而真正的锁误用（如新增模块级 `lock = threading.Lock()`）检测不到 | 读码 | (a) 改名 both_steps_dispatched 或用事件屏障验证并行；(b) 改为 ast 解析模块级赋值或接受现状并注明局限

### tests/pipeline/test_path_context.py
- 处置: deep-read
- 声称检查的不变量: [arc/stratum/volume 家族按 60//12、55//36、count(≤55) 解析；无 ctx 回退章语义；无 ctx 不可解析→raise；format/parse 往返；注入值剥离路径穿越；上标数字/str 哨兵不炸]
- findings: 无。安全硬化（路径穿越剥离 :121-126）、哨兵反斜杠（:85-91）、首行优先（:110-114）覆盖充分；全部走真实 resolve_contract_path/parse_path_context
- 验证命令: 读 src/shenbi/contracts/paths.py 导出符号（测试 import 全部存在 ✓）
- 置信度: high

### tests/pipeline/test_retry.py
- 处置: deep-read
- 声称检查的不变量: [429/5xx/timeout 重试并最终成功；3 连败放弃；非 429 4xx 不重试]
- findings: 无。MagicMock client + httpx 异常替身合理；call_count 断言验证真实 tenacity 行为；_call_llm_streaming_with_retry（:1464）签名匹配
- 验证命令: `grep -n "def _call_llm_streaming_with_retry" dispatch_helper.py` → :1464
- 置信度: high

### tests/pipeline/test_review_checklist.py
- 处置: deep-read
- 声称检查的不变量: [模板+章 delta 合并；Hook Ledger 提取 hook_deliverables]
- findings: 无（轻微：`len(...) >= 1` 可收紧为确切集合断言）
- 验证命令: `grep -n "def generate_chapter_delta\|def get_checklist" review_checklist.py` → 存在 ✓（d1-06:137 显示该模块 79%，非本文件问题）
- 置信度: high

### tests/pipeline/test_review_reject.py
- 处置: deep-read
- 声称检查的不变量: [REJECT 回滚 genesis 游标至 16；PER_CHAPTER MODIFY 队列 revision 带反馈；escalation REJECT 重置该章预算且不动他章；auto 并行结算无 checkpoint、truth 落盘、staging 清空；review_required 推迟；RetryExhausted→ESCALATION checkpoint 且预算轨迹存活；cmd_review REJECT 真实接线；CHAPTER_MEMO/STATE_SETTLE/VOLUME_BOUNDARY 游标回滚]
- findings: 无。高质量接线测试：patch 目标全为消费端命名空间（cl.set_checkpoint、chapter_loop.run_chapter_step、genesis.run_genesis_step、closure.run_closure_step、cli_mod.load_state/save_state/emit_json）；符号核对：_queue_re_dispatches:77、_orchestrate_to_checkpoint:165、_apply_reject_redo:544、_auto_settle_parallel:896、cmd_review:569、retry_budget_consumed 字段（state.py:151）全部存在
- 验证命令: 上述 grep 批量核对
- 置信度: high

### tests/pipeline/test_scr_extractor.py
- 处置: deep-read
- 声称检查的不变量: [META 块剥离；角色/对白/钩子/事件/段落统计提取；全量抽取产出合法 SCR；缓存落盘；二 call 走缓存]
- findings: 无。test_cache_hit（:118-129）以 extracted_at（datetime.now(UTC).isoformat() 含微秒，scr_extractor.py:444）相等证明缓存命中——论证成立（微秒精度下两次全新抽取不可能同串）；纯函数单测使用内联样例文本属单元测试范畴（与 G0.9 场景输入要求不冲突）
- 验证命令: `grep -n "extracted_at" src/shenbi/pipeline/scr_extractor.py` → :24,:444
- 置信度: high

### tests/pipeline/test_snapshot_diff.py
- 处置: deep-read
- 声称检查的不变量: [差异快照存 hash 非全文；环形缓冲 N=3 近章存全文、旧章 hash-only；truth 文件可还原；环缓冲章全文可还原；hash 检测修改]
- findings: 无。测试设计正确：先写全 4 章再逐章快照 → latest=4 由磁盘状态推导（_is_recent: chapter >= latest-(N-1)，snapshot_diff.py:67-71），ch2 有 content / ch1 hash-only 的断言与实现语义一致；restore 正/负路径齐全
- 验证命令: `grep -n "RING_BUFFER_N\|def _is_recent\|def create_differential_snapshot" snapshot_diff.py` → :15,:67,:74
- 置信度: high

### tests/pipeline/test_state_machine_heal.py
- 处置: deep-read
- 声称检查的不变量: [空 current_step+有效 index → 治愈；已设置不动；越界→chapter_complete；index≤0 不治愈；校验时自动治愈/钳制；边界 index==len 合法]
- findings: [F743]
- 验证命令: `uv run python -c "...CHAPTER_STEPS..."` → [3]='shenbi-chapter-drafting'、[7]='shenbi-state-settling'（test_passes_consistent_state 的 7↔state-settling 一致 ✓）；读 state.py:436-499（_heal 仅填空、_validate 仅查空+越界）
- 置信度: high
- F743 | 校验器不检查 current_step↔CHAPTER_STEPS[step_index] 错位；测试夹具自带错位未察觉 | error | P2 | tests/pipeline/test_state_machine_heal.py:25-31 + src/shenbi/pipeline/state.py:488-499 | _validate_state_consistency 只查"current_step 空但 index>0"与"index 越界"，不查二者**互相矛盾**（如 current_step='shenbi-chapter-drafting' 但 index=4 → 实际第 4 步是 pipeline-post-draft-extract）。测试 :25-31 恰好构造了这种真实错位态（index=4 + drafting）却命名为 "already_set" 且只调用不校验 _heal——错位 corruption 正是本模块声称要防的类别，但该形态静默通过 | 见验证命令的 CHAPTER_STEPS 打印 | _validate 增加 step↔index 一致性检查（或至少加测试断言当前行为以显式记录该盲区）

### tests/pipeline/test_title_gate_integration.py
- 处置: deep-read
- 声称检查的不变量: [H1 标题提取；前章标题加载排除当前/未来章；_run_g4_checks 集成检出章号/重复/星期标题；好标题零 issue]
- findings: [F746]
- 验证命令: 读 chapter_loop 的 _extract_chapter_title/_load_previous_titles/_run_g4_checks（import 存在 ✓，CHAPTER_STEPS 打印确认步骤表）
- 置信度: high
- F746 | 名实不符两处 | error | M | tests/pipeline/test_title_gate_integration.py:31-47,201-216 | (a) test_returns_empty_for_missing_file 实际断言 `pytest.raises(FileNotFoundError)`（docstring 也自认 raise），测试名却说 returns_empty；(b) test_short_chinese_title_still_valid 只断言 `1 <= len(title) <= 20`（title 即手写的"沉"，恒真式检查），从未过 _run_g4_checks —— "single-char title 有效"的 gate 语义未被验证（其值在另一测试 test_good_title... 变体中间接覆盖）| 读码 | (a) 改名 test_missing_file_raises；(b) 补 _run_g4_checks(state,1)==[] 断言

### tests/pipeline/test_total_chapters.py
- 处置: deep-read
- 声称检查的不变量: [update_total_chapters:=max(boundaries)=100 非已写数；genesis 钩子同值；幂等且字节不变；mid-book heal 解锁卷界 trigger（55 边界触发、无过早 closure）；接线真跑 _orchestrate_to_checkpoint；坏 JSON→0；非 int→0]
- findings: 无。真实 fixture + 接线测试用 `monkeypatch.setattr("shenbi.pipeline.triggers.check_triggers", ...)` —— cli.py:190 为函数内延迟 import，patch 源模块生效 ✓（已核对 cli.py:158-225 的延迟 import 模式）
- 验证命令: `grep -n "check_triggers\|update_total_chapters" src/shenbi/pipeline/cli.py` → :158-162,:190,:220-225
- 置信度: high

### tests/pipeline/test_trigger_context.py
- 处置: deep-read
- 声称检查的不变量: [run_triggered_skills 注入 [path-context] 行且 G4 文件按家族解析（arc-5 非 arc-60）；executor/audit 双侧 derive 一致；触发流 prompt 列 arc-5；审计 watch 路径按家族]
- findings: 无。docstring 明示 G0.9 边界（接线单测豁免）；符号核对 derive_input_files:executor.py:94、derive_output_files:audit/_shared.py:38、_audit_watch_paths:executor.py:233 全存在
- 验证命令: 上述 grep
- 置信度: high

### tests/pipeline/test_volume_align.py
- 处置: deep-read
- 声称检查的不变量: [英文卷图章节节点提取（## 与 ### 两种头）；关键词提取；高匹配无警告；低匹配告警]
- findings: [F730]
- 验证命令: `grep -rn "check_volume_alignment\|volume_align" src/shenbi/ --include="*.py"` → **src 内零调用者**（volume_align.py 自身除外）；`grep -n "_check_volume_map_alignment" chapter_loop.py` → :2161 定义、**:3073 真实调用**（走 _shared.read_chapter_node 中文解析）；读 volume_align.py:5-25（纯英文 `## Chapter N` 正则）；d1-06:149（volume_align.py 76%，缺 10,18-19,23,59,63）
- 置信度: high
- F730 | 测试覆盖孤儿孪生实现，已接线实现无 pipeline 区测试 | error | P2 | tests/pipeline/test_volume_align.py:10-50 + src/shenbi/pipeline/volume_align.py:5-25（零调用者、仅英文模式）vs src/shenbi/pipeline/chapter_loop.py:2161-2215（_check_volume_map_alignment，中文能力，:3073 接线） | volume_align.py 是无人调用的平行实现（且只解析英文 `Chapter N` 头，而产品是中文卷图）；真正生效的 _check_volume_map_alignment 没有任何直接测试（70% 缺失阈值、found/missing 分类、>70% 告警语义裸奔——d1-06 中 chapter_loop 大面积缺失含此区）。测试给死模块 76% 覆盖制造"volume alignment 已测"假象。与 2026-08-14 审计 Z3.review7 F310/F37 判定相互印证（该轮已指出 check_volume_alignment 仅测试调用） | 上述 grep（src 零调用者 + :3073 接线点） | 删除 volume_align.py 死模块，测试改为直接测 _check_volume_map_alignment（用 volume-map-xinghuo.md 真实 fixture）

### tests/pipeline/test_volume_map_cn.py
- 处置: deep-read
- 声称检查的不变量: [真实 fixture 边界集精确 {15,35,55,75,100}；KR 子范围不入集；英文 END/RANGE 语义回归锁定]
- findings: 无。精确集合断言 + 负验收 + 回归护栏，质量高
- 验证命令: fixture 存在 ✓（多个测试共用）
- 置信度: high

### tests/pressure-tests/prompts/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [目录占位]
- findings: 无（0 字节）
- 验证命令: `wc -c` → 0
- 置信度: high

### tests/pressure-tests/prompts/audit-skipping-pressure.md
- 处置: deep-read
- 声称检查的不变量: [时间压力下不得自作主张跳过审计维度；须全量 genre-config 审计或交用户决策；反理性化表]
- findings: [F740]
- 验证命令: 读 src/shenbi/pipeline/chapter_loop.py:305-364（CORE/ALWAYS_RUN/CASCADABLE_AUDITS + N=3 streak skip）；pyproject.toml:415（norecursedirs 排除 pressure-tests → 纯手动协议）
- 置信度: high
- F740 | 压力提示词与代码内审计级联教义冲突 | error | P2 | tests/pressure-tests/prompts/audit-skipping-pressure.md:33-51（"跑全部 33 维"、"自作主张跳过 28 维只跑 5 维: FAIL"）vs chapter_loop.py:310-321,327-364 | 代码明确设计了"3 章零 HARD 失败即级联跳过 cascadable 审计"（8 个维度），与提示词"跳维度=FAIL"的硬标准矛盾。按此提示词评分的 agent 若遵守管线内建级联会被判 FAIL（或反过来，提示词教义被用来反对代码优化）。注：F726 证明级联当前实际不生效，但两处规范仍应一致，否则一旦修复 F726 立即冲突 | 读码对照 | 提示词补一段"级联 skip 属系统决策非自作主张"的例外说明，或在代码侧移除级联

### tests/pressure-tests/prompts/chapter-writing-pressure.md
- 处置: deep-read
- 声称检查的不变量: [拒绝无规划直写；先查 chapter memo/PRE_WRITE_CHECK；起草后 anti-ai 审计]
- findings: 无。PRE_WRITE_CHECK 与现行实现一致（chapter_drafting.py:_text_fingerprint 显式处理 PRE_WRITE_CHECK 段）；手动前置条件声明清楚（Phase 1 无导入管线）
- 验证命令: `grep -n "PRE_WRITE_CHECK" src/shenbi/gates/g4/chapter_drafting.py` → 存在
- 置信度: high

### tests/pressure-tests/prompts/foreshadowing-fatigue-pressure.md
- 处置: deep-read
- 声称检查的不变量: [不信任 pending_hooks.md 单一来源；87 条逐一反查；三类清单输出；反理性化表]
- findings: 无。与设计（真相文件交叉验证）一致；评分梯度（PASS/PARTIAL/FAIL）明确可操作
- 验证命令: 读文件全文
- 置信度: high

### tests/pressure-tests/prompts/import-shortcut-pressure.md
- 处置: deep-read
- 声称检查的不变量: [5 步导入管线不可砍步；分批可以砍步不行；超时须报告已完成/未完成]
- findings: 无。五技能输出文件清单与 skills/ 契约对应（import-analysis-report.md / style_fingerprint.json / world_extracted/ / characters_extracted/ / canon.md）
- 验证命令: 读文件全文 + skills 目录技能名抽查
- 置信度: high

### tests/pressure-tests/prompts/snapshot-skip-pressure.md
- 处置: deep-read
- 声称检查的不变量: [每章必须建快照；完整副本 + manifest；铁律优先于临时指示]
- findings: [F739]
- 验证命令: 读 src/shenbi/pipeline/snapshot_diff.py:67-130（hash-only 不可变文件 + 仅 N=3 环缓冲章存全文 + manifest）；test_snapshot_diff.py:12-34（"stores_hashes_not_content"断言）
- 置信度: high
- F739 | 快照压力提示词编码过时"完整副本"语义 | error | P2 | tests/pressure-tests/prompts/snapshot-skip-pressure.md:37-48（"复制全部 11 个 truth 文件"、"只复制部分 truth 文件: FAIL"、"快照必须是完整副本"、50KB/章磁盘论证）vs snapshot_diff.py 差分设计 | 现行实现存 hash 引用 + 仅近 3 章全文（环形缓冲），并不复制全部 truth 文件。按此提示词标准执行/评分的 agent 会与设计行为冲突（把正确的差分快照判为 FAIL，或被诱导改回全量复制）。"从未回滚"反驳论据本身有效，但规格描述漂移 | 上述对照 | 重写提示词以差分+环缓冲语义表述（"必须创建 manifest 与规定的全文/哈希条目"）

### tests/pressure-tests/prompts/state-drift-pressure.md
- 处置: deep-read
- 声称检查的不变量: [9 类变化逐一提取；不凭记忆；呈交人类批准后写入]
- findings: 无。与 state-settling 技能契约一致（审批写入流程）
- 验证命令: 读文件全文
- 置信度: high

### tests/property/.gitkeep
- 处置: deep-read
- 声称检查的不变量: [目录占位]
- findings: 无（与 __init__.py 并存略显冗余，属常见布局）
- 验证命令: `wc -c` → 0
- 置信度: high

### tests/property/__init__.py
- 处置: deep-read
- 声称检查的不变量: [包声明 "Shenbi property test package."]
- findings: 无
- 验证命令: `cat`
- 置信度: high

### tests/property/cjk/__init__.py
- 处置: deep-read
- 声称检查的不变量: [包声明 "CJK property tests."]
- findings: 无
- 验证命令: `cat`
- 置信度: high

### tests/property/cjk/test_cjk_properties.py
- 处置: deep-read
- 声称检查的不变量: [子串命中；破折号/省略号整 token 计数；mixed ≥ cjk_only；词数非负]
- findings: 无。断言直接以 text.count 作 oracle（合理闭式）；字母表含重叠标点覆盖边界
- 验证命令: 读 src/shenbi/text/cjk.py 导出（count_punctuation/count_words/find_terms ✓，d1-06:193 显示 97%）
- 置信度: high

### tests/property/cjk/test_g612_embedded_properties.py
- 处置: deep-read
- 声称检查的不变量: [CJK 包夹敏感词必检出且位置精确；旧 `[^\w]` 边界正则在纯 CJK 失效（回归对照）]
- findings: 无。旧 bug 行为的对照测试（:30-39）是优秀实践——证明替代方案必要性
- 验证命令: 读 find_terms 实现（text/cjk.py）✓
- 置信度: high

### tests/property/cjk/test_punct_properties.py
- 处置: deep-read
- 声称检查的不变量: [每类标点 counts == Σ text.count(token)；—— 不 per-char 翻倍；计数非负]
- findings: 无。PUNCTUATION_TOKENS 驱动的生成器保证 token 全覆盖
- 验证命令: PUNCTUATION_TOKENS 导出 ✓
- 置信度: high

### tests/property/cjk/test_tokenize_frozen.py
- 处置: deep-read
- 声称检查的不变量: [jieba==0.42.1 冻结基线（词+POS）；tokenize 拼接还原原文；确定性]
- findings: 无。隔离 Tokenizer 实例避免 add_word 污染（:10-19 注释明确）；pyproject jieba==0.42.1 pin 与冻结声明一致
- 验证命令: 读文件 + pyproject jieba pin（0.42.1）
- 置信度: high

### tests/property/contracts/__init__.py
- 处置: deep-read
- 声称检查的不变量: [包声明：三表一致性属性（spec 支柱五；判据 5）]
- findings: 无
- 验证命令: `cat`
- 置信度: high

### tests/property/contracts/test_registry_consistency.py
- 处置: deep-read
- 声称检查的不变量: [truth-files.yaml / load_registry / bootstrap_registry 三源概念名集合相等；每个 concept 有 kind；bootstrap ⊆ yaml]
- findings: [F747]
- 验证命令: `ls docs/framework/truth-files.yaml` → 存在（真实单一源）；读 shenbi.contracts.registry 导出 ✓
- 置信度: high
- F747 | st.data() 不 draw 的常量"属性" | optimization | M | tests/property/contracts/test_registry_consistency.py:42-46 | `@given(st.data())` 但 `_data` 参数从未 draw —— 属性恒定，等价于同一断言重复执行 20 次，每次重复读同一 YAML（IO 浪费）且伪装成属性测试 | 读码 | 降级为普通测试，或从 _data 真正 draw 子集做更强性质

### tests/property/drift/__init__.py
- 处置: deep-read
- 声称检查的不变量: [包声明：drift 排除/触发不变量]
- findings: 无
- 验证命令: `cat`
- 置信度: high

### tests/property/drift/test_drift_properties.py
- 处置: deep-read
- 声称检查的不变量: [排除索引不泄漏进递减跨度；全排除→无 finding；volume_decline iff 末卷<倒数第二；至多一个 volume finding]
- findings: 无。iff 性质（:66-72）与"排除真起作用"负性质（:46-63）设计优秀；floats 策略禁 NaN/Inf
- 验证命令: `grep -n "def detect_chapter_drift\|def detect_volume_drift" compute_drift.py` → 存在（签名匹配）
- 置信度: high

### tests/property/gates/__init__.py
- 处置: deep-read
- 声称检查的不变量: [空包文件]
- findings: 无
- 验证命令: `cat` → 空
- 置信度: high

### tests/property/gates/test_capability_fs_properties.py
- 处置: deep-read
- 声称检查的不变量: [read_text/read_bytes 往返；任何写操作 PermissionError；根外路径拒绝；exists/list_dir 只读]
- findings: 无。suppress_health_check(function_scoped_fixture) 使用正确（hypothesis+tmp_path 已知交互）；黑名单字符策略规避代理对问题
- 验证命令: capability_fs.py 100% 覆盖（d1-06:9）相互印证
- 置信度: high

### tests/property/gates/test_g34_independence_properties.py
- 处置: deep-read
- 声称检查的不变量: [无 scorer 记录→FAIL（fail-closed）；同 agent→FAIL；不同 agent→PASS 且 reason 空；无生成 trace→PASS]
- findings: 无。G3.4 fail-closed 语义全覆盖；assume(scorer != gen) 配 filter_too_much 抑制正确
- 验证命令: g3_independence.py 100% 覆盖（d1-06:68）相互印证
- 置信度: high

### tests/property/gates/test_gate_invariants.py
- 处置: deep-read
- 声称检查的不变量: [word_count_md 非负；normalize 返回 list；transition 计数非负；jload dict 往返；G0 空 seed 产出合法 JSON]
- findings: 无（轻微：多数是弱性质——非负/isinstance——但对共享工具函数合理；docstring 对 hypothesis×fixture 冲突的规避说明与实现一致）
- 验证命令: gates/shared.py 导出符号 grep ✓（d1-06:110 92%）
- 置信度: high

### tests/property/stats/__init__.py
- 处置: deep-read
- 声称检查的不变量: [包声明：算术统计不变量]
- findings: 无
- 验证命令: `cat`
- 置信度: high

### tests/property/stats/test_entropy_properties.py
- 处置: deep-read
- 声称检查的不变量: [Σcount==n 精确整数；熵 == round(重算)；0≤H≤log2(k)+舍入容差；单模式 H=0]
- findings: 无。oracle 重算式属性对数学函数是合适形态；舍入上行容差（1e-4）有推导注释
- 验证命令: compute_pattern.PATTERNS 导出 ✓（d1-06:165 93%）
- 置信度: high

### tests/property/stats/test_percentile_properties.py
- 处置: deep-read
- 声称检查的不变量: [P50==地板中点==sentence_stats median；百分位落在 [min,max]；空表零值]
- findings: 无。诚实记录 nearest-rank 方案不保证跨级单调（:40-46 注释），选择正确的不变量
- 验证命令: compute_stats.compute_percentiles/compute_sentence_stats 导出 ✓
- 置信度: high

### tests/property/trace/__init__.py
- 处置: deep-read
- 声称检查的不变量: [包声明：trace hash-链不变量]
- findings: 无
- 验证命令: `cat`
- 置信度: high

### tests/property/trace/test_chain_invariants.py
- 处置: deep-read
- 声称检查的不变量: [任意动作序列写链可完整重放验证；篡改任一字段→链断（replay 空）]
- findings: 无。真实 TraceWriter 落盘 + 真实篡改 + 真实 replay 验证——性质测试真实性的标杆
- 验证命令: trace/replay.py、trace/writer.py 导出 ✓（d1-06:199/201 93%/90%）
- 置信度: high

---

## 覆盖统计

- 清单文件：73；报告条目：73；未覆盖：0
- 深读（非平凡）文件：test_*.py 45 个 + prompts 6 个 + README 1 个 + __init__ 12 个 + .gitkeep 6 个 + benchmark/__init__ 1 个（并入 F742）等；所有 73 条均有独立条目
- findings：25（F726–F750）：P1×4（F726 F727 F728 F729），P2×17，M×4；P0×0
- skip/xfail 处置汇总：
  - test_doc_links `_require_mlc` → **keep（写法）/stale（接线）**（F732，P2）
  - test_docs_accuracy :64 → **keep**；:85/:94/:103 → **stale，建议删除**（F731，P2）
  - 全区无 xfail；无判 masking 级 skip（无证据表明有被掩盖的真实缺陷——均为基础设施/接线空转）
- 与 d1-06 交叉验证一致项：gate_manifest 78%（F733）、audit_context_cache 54%（F737）、dispatch_helper 615-634 缺（F728）、parallel_dispatch 65%（F738）、volume_align 76%（F730）
- 与 2026-08-14 前轮审计交叉：F730 与 Z3.review7 对 volume_align 的判定相互印证（本轮补充了"测试测错孪生"视角）

## 低置信度文件列表

无（全部 high）。关键 P1 均有实跑核验或唯一性 grep 证据：
- F726：只读 python 实跑 `_get_audit_history`→`_should_skip_audit` 得 False（vs 手搓形状 True）
- F727：`grep -rn drift_alerts src/` 唯一命中消费端
- F730：`grep -rn check_volume_alignment src/` 零调用者 + chapter_loop.py:3073 接线点

## 未覆盖文件列表

（无 —— 73/73 全覆盖）
