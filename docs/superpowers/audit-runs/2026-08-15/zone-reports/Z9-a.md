# Z9-a 段初审报告（docs/ 非 superpowers 部分 + 根级 *.md，40 文件）

- 审查轮次: 2026-08-15 全项目深度审查
- 审查 agent: Z9-a（只读）
- findings 编号段: F901–F933（实际使用 F901–F919）
- 抽样清单内条目: 1（docs/framework/chapter-file-format.md → src/shenbi/gates/shared.py:120）；核对 1；漂移 0（实际正则位于 shared.py:121，偏差 1 行，±5 内）
- 高风险文档全查: AGENTS.md、docs/architecture/overview.md、docs/framework/*（全部 file:line 与路径引用逐条核对，见各文件条目）

## 全局核对摘要

- skill 计数（多处文档声称 vs 实际）: 磁盘 `skills/` 共 **74** 个含 SKILL.md 的目录（73 个 `shenbi-*` + `using-shenbi`；功能技能 72 + meta 2）；`tests/tiers/deps.json` 登记 **69**；`docs/skills/index.md`/`README.md`/`docs/index.md`/`AGENTS.md` 均声称 **67+2=69**。5 个磁盘技能（shenbi-foreshadowing-lifecycle、shenbi-review-group-{character,craft,factual,plan}）未出现在任何文档目录中（验证: `for d in skills/*/; do [ -f "$d/SKILL.md" ] && echo "$d"; done | wc -l` → 74；python 对比 deps.json → on disk not in deps 恰为该 5 个；`grep -c "review-group" docs/skills/index.md` → 0）。
- 门槛数字: acceptance.json = `{"t1":94,"t2":94,"t3":94}`，与 AGENTS.md/README/overview/concepts/command-to-give 的 94/90/100 体系一致；覆盖门 85% 实际存在于 `pyproject.toml:452`（fail_under=85，经 addopts `--cov=shenbi` 生效）与 `tools/pre-push-check.sh:70`。
- 命令有效性: justfile 全部 recipe（check/test/fix/gate/dispatch/docs/pipeline-*）与 pyproject 全部 entry points（shenbi-validate/dispatch/score/phase/sync-contracts/generate-plugins/cost/pipeline 等）核对通过；`shenbi-validate G2/G4`、`shenbi-score`、`phase_runner`（start/pre-skill/post-skill/pre-score/post-score/finalize）、`pipeline init --auto` 签名与文档一致。两处命令失效见 F901/F902。
- 内部链接: 40 个清单文件全部相对链接脚本扫描，0 死链。
- mkdocs.yml nav: 13 个 nav 条目全部对应存在的文件；mkdocstrings 插件已配置（api 两页 `:::` 语法可用）；`exclude_docs: superpowers/audit-runs/` 与本段无关但合理。
- 门槛/计数一致但历史化文档: goal-prompt.md（2026-06-13 快照）多处过期，见 F913。

---

## Per-file 报告

### AGENTS.md
- 处置: deep-read
- 声称检查的不变量: [项目结构树各路径存在；skill 计数 67+2=69；命令列表有效；P2.5 rationale 规则与代码一致；decisions G2/G4 行为；field-level reads 过滤；门槛 94/90/100；覆盖门 85%；workflows 清单]
- findings: [F904, F917]（另 F908 中 AGENTS.md:70 的 P2.5 表述欠指定）
- 验证命令: `ls -d skills/*/ | wc -l`→74；`grep -rn "_tool_hashes" src/`→仅 schema/lock 脚本引用；`grep -n "G0.13" src/shenbi/gates/g0.py`→552 行起为 independence markers；`ls tests/rounds`→不存在（b978d3c 删除）；`grep -n "decisions" src/shenbi/gates/g2.py`→76/164 行 file_type="decisions" 跳过字数 ✓；`grep -n "filter_to_fields" src/shenbi/pipeline/dispatch_helper.py`→605 行 ✓；`ls .github/workflows/`→ci/security/docs/codeql/release 均 ✓；justfile 全 recipe ✓
- 置信度: high

### CHANGELOG.md
- 处置: deep-read
- 声称检查的不变量: [Unreleased 引用的 spec 目录存在；0.1.0 条目内部自洽]
- findings: [F914]
- 验证命令: `ls -d docs/superpowers/specs/archive/2026-06-15-p-1.e-foundation-completion`→存在 ✓
- 置信度: high

### CODE_OF_CONDUCT.md
- 处置: deep-read
- 声称检查的不变量: [Contributor Covenant 2.1 模板完整性；联系方式可用]
- findings: [F915]
- 验证命令: 未验证（模板占位符为直接读到的文本证据）
- 置信度: high

### CONTRIBUTING.md
- 处置: deep-read
- 声称检查的不变量: [安装步骤命令有效；mypy overrides 现状描述属实；`.github/PULL_REQUEST_TEMPLATE.md`/`plugins/master.json`/`shenbi-generate-plugins` 存在；plugin-manifest-freshness CI job 存在且有效；测试目录结构存在]
- findings: [F910, F911]
- 验证命令: `grep -n "ignore_errors" pyproject.toml`→91 行 numpy.* ignore_errors=true；`grep -c "\[\[tool.mypy.overrides\]\]" pyproject.toml`→4；`ls .github/PULL_REQUEST_TEMPLATE.md plugins/master.json`→均存在 ✓；`grep -rn "plugin-manifest" .github/workflows/`→仅 ci.yml:69 注释"merged"；`git ls-files .codex-plugin`→空；`grep -n "codex" .gitignore`→20 行 `.codex-plugin/`；`ls tests/unit tests/integration tests/property tests/benchmark`→均存在 ✓；`just --list` 交叉核对 just/fix/check/test ✓
- 置信度: high

### README.md
- 处置: deep-read
- 声称检查的不变量: [Quick Start 命令可执行；pipeline-init 示例命令有效；LLM 环境变量路由描述；文档表链接；技能一览各阶段计数；69 总数；badge workflow 存在]
- findings: [F902]（计数过期归入 F904 证据链：README.md:16/18/22/88）
- 验证命令: `just --dry-run pipeline-init outline-example.md ./my-novel --auto`→`error: justfile does not contain recipe '--auto'`；`uv run pipeline init --help`→支持 `--auto`（flag 本身存在，但 just recipe 不透传）；阶段计数 11/5/3/9/18/4/9/4/3/7 与 deps.json prerequisites 逐相核对全部一致 ✓；`ls .github/workflows/ci.yml docs.yml`→✓；README.md:76 路由优先级 → 未验证（dispatcher modes internal/codex/codex_api 存在，顺序逻辑未深查）
- 置信度: high

### SECURITY.md
- 处置: deep-read
- 声称检查的不变量: [SBOM CycloneDX per release；pip-audit every PR + weekly；CodeQL every PR + weekly；uv.lock 带 hash]
- findings: [F912]
- 验证命令: `grep -n "pip-audit\|cyclonedx" .github/workflows/security.yml release.yml`→security.yml:14-19、release.yml:17-18 ✓；`grep -n "cron" .github/workflows/codeql.yml`→15 行周一 cron ✓；`sed -n '1,13p' security.yml`→仅 push(main)+pull_request，无 cron；`grep -n "cron" nightly.yml`→20 行注释状态
- 置信度: high

### command-to-give.md
- 处置: deep-read
- 声称检查的不变量: [round-exec.sh/lock-tool-hashes.sh 存在；dispatch-subagent.sh 存在；G0.13 工具哈希阻断语义；shenbi-validate/score/phase 命令签名；scoring 退出码 0/1/2/3；G2.5/G4/G0.9/G0.11 检查存在；94/90/100 阈值；"59 个 skill"推进条件]
- findings: [F901, F903, F906]
- 验证命令: `ls tests/dispatch-subagent.sh`→No such file；`git log --oneline --diff-filter=D -- tests/dispatch-subagent.sh`→0f68102 "delete dispatch shim"；`grep -n "sys.exit" src/shenbi/scoring.py`→293(1)/313(0|1)/360(1)/377(3)/432(2) ✓ 四态退出码属实；`grep -o "G2.5" src/shenbi/gates/g2.py`→存在 ✓；`grep -rn "G0.9" src/shenbi/gates/g0_purity.py`→16 行 ✓；G0/G2/G4/G6/G7 CLI 签名与 cli.py:80-130 逐参核对 ✓；`ls tests/tiers/t1-skill | wc -l`→70（69+_template）→"59"过期
- 置信度: high

### docs/_shared-evidence-template/REVIEW_EVIDENCE.md
- 处置: deep-read
- 声称检查的不变量: [四要素格式与 review 技能实际用法一致；严重度枚举 BLOCKING/CRITICAL/MINOR 被技能使用]
- findings: 无
- 验证命令: `grep -rln "BLOCKING" skills/ | head`→review-memo-compliance/review-group-*/review-continuity 等使用 ✓；`grep -n "严重度" skills/shenbi-review-character/SKILL.md`→86 行同枚举 ✓
- 置信度: high

### docs/adr/0000-template.md
- 处置: deep-read
- 声称检查的不变量: [模板字段与现有 ADR 结构一致]
- findings: 无
- 验证命令: 与 0001-0009 结构目测比对一致（未运行命令）
- 置信度: high

### docs/adr/0001-pyproject-uv.md
- 处置: deep-read
- 声称检查的不变量: [uv 唯一依赖管理器；uv.lock 存在带 hash]
- findings: 无
- 验证命令: `ls uv.lock pyproject.toml`→✓；`grep -n "uv " justfile`→全部 recipe 经 uv run ✓
- 置信度: high

### docs/adr/0002-ruff-strict.md
- 处置: deep-read
- 声称检查的不变量: [ruff 同时承担 lint+format 且配置在 pyproject]
- findings: 无
- 验证命令: `grep -n "ruff" pyproject.toml justfile`→[tool.ruff] 存在；`uv run ruff check --help` 级别的配置存在性经 justfile check recipe 交叉印证 ✓
- 置信度: high

### docs/adr/0003-mypy-basedpyright-dual.md
- 处置: deep-read
- 声称检查的不变量: [mypy --strict 与 basedpyright strict 双开]
- findings: 无
- 验证命令: `grep -n "\[tool.mypy\]" -A 3 pyproject.toml`→360 行 strict=true ✓；`grep -n "typeCheckingMode" pyproject.toml`→strict ✓
- 置信度: high

### docs/adr/0004-pytest-framework.md
- 处置: deep-read
- 声称检查的不变量: [7 个 pytest 插件均在依赖中]
- findings: 无
- 验证命令: `grep -n "pytest-cov\|pytest-xdist\|pytest-asyncio\|pytest-timeout\|pytest-benchmark\|pytest-ordering\|hypothesis" pyproject.toml`→28-35 行 7 个全部在 dev group ✓
- 置信度: high

### docs/adr/0005-structlog.md
- 处置: deep-read
- 声称检查的不变量: [structlog JSON+Console 双渲染]
- findings: 无
- 验证命令: `sed -n '19,42p' src/shenbi/logging.py`→JSONRenderer/ConsoleRenderer 双分支 ✓
- 置信度: high

### docs/adr/0006-typed-exceptions.md
- 处置: deep-read
- 声称检查的不变量: [ShenbiError 基类 + FrameworkError/GateError/ScoringError/IntegrityError 分支；to_dict；ErrorGuidance]
- findings: 无
- 验证命令: `grep -n "class.*Error" src/shenbi/exceptions.py`→44/86/127/119/161 行分支齐 ✓；`ls src/shenbi/error_guidance.py`→✓
- 置信度: high

### docs/adr/0007-adr-process.md
- 处置: deep-read
- 声称检查的不变量: [ADR 存于 docs/adr/ 且编号连续]
- findings: 无
- 验证命令: `ls docs/adr/`→0000-0009 + index ✓
- 置信度: high

### docs/adr/0008-validate-gate-modularization.md
- 处置: deep-read
- 声称检查的不变量: [gates/ 按 g0.py...g4/ 拆分；CLI shim 保留]
- findings: 无
- 验证命令: `ls src/shenbi/gates/`→g0-g7+g_dispatch/g_reconcile/g_transition+g4/ ✓；`pyproject.toml:58` shenbi-validate 入口 ✓（"4300+ lines"为当时快照，未复核历史行数）
- 置信度: medium

### docs/adr/0009-dispatcher-python-rewrite.md
- 处置: deep-read
- 声称检查的不变量: ["Shell wrapper stays as 10-line shim" 至今成立]
- findings: [F916]
- 验证命令: `git log --oneline -- tests/dispatch-subagent.sh`→c8d3639 缩为 4 行 shim 后 0f68102 删除；`ls tests/dispatch-subagent.sh`→不存在
- 置信度: medium

### docs/adr/index.md
- 处置: deep-read
- 声称检查的不变量: [索引 9 条与实际 ADR 文件一一对应；链接有效]
- findings: 无
- 验证命令: `ls docs/adr/*.md`→9 个编号文件与表格逐一匹配 ✓
- 置信度: high

### docs/api/exceptions.md
- 处置: deep-read
- 声称检查的不变量: [mkdocstrings 标识符可解析；mkdocs 插件配置存在]
- findings: 无
- 验证命令: `ls src/shenbi/exceptions.py`→✓；`grep -n "mkdocstrings" mkdocs.yml`→已配置 ✓
- 置信度: high

### docs/api/logging.md
- 处置: deep-read
- 声称检查的不变量: [同上]
- findings: 无
- 验证命令: `ls src/shenbi/logging.py`→✓
- 置信度: high

### docs/architecture/overview.md
- 处置: deep-read（高风险全查）
- 声称检查的不变量: [t3-pipelines=3 且阶段序列与 deps.json 一致；8 门 G0-G7；T2=9 阶段；94 门槛源自 acceptance.json；truth-files.yaml kind 数=15；五类示例文件在 yaml 中存在；延伸阅读链接有效]
- findings: [F907]
- 验证命令: `python3 -c "import json; d=json.load(open('tests/tiers/deps.json')); print(len(d['t2-phases']), len(d['t3-pipelines']))"`→9/3 ✓；`cat tests/tiers/acceptance.json`→94/94/94 ✓；`grep -o 'kind: [a-z-]*' docs/framework/truth-files.yaml | sort -u | wc -l`→**16**（truth,report,decisions,outline,world,import,context,config,snapshot,short,character,benchmark,style,reference,plan,chapter）≠15；五类示例文件逐名 grep yaml ✓；链接脚本扫描 0 死链 ✓
- 置信度: high

### docs/basedpyright-overrides.md
- 处置: deep-read
- 声称检查的不变量: [项目级降级值为 "warning"；executionEnvironments 含 tests 与 skill_utils；mypy 对 skill_utils 有 ignore_errors；jload/yload 已收窄为 dict]
- findings: [F909]
- 验证命令: `sed -n '371,412p' pyproject.toml`→reportMissingTypeStubs/reportUnknown* 全为 **"none"**（382,391-395 行）；executionEnvironments 仅 `tests` 一项（400-402 行），无 skill_utils；`grep -n "skill_utils" pyproject.toml`→mypy overrides 中无；`grep -n "def jload" src/shenbi/gates/shared.py`→44 行返回 dict[str, Any] ✓（该项属实）
- 置信度: high

### docs/framework/chapter-file-format.md
- 处置: deep-read（高风险全查 + 抽样条目）
- 声称检查的不变量: [src/shenbi/gates/shared.py:120-121 为 META 剥离实现；word_count_md 存在且剥离；G2.meta_ratio >50% WARN]
- findings: 无
- 验证命令: `grep -n "META-BEGIN" src/shenbi/gates/shared.py`→120 行注释/121 行 re.sub（抽样登记 shared.py:120，偏差 1 行，±5 内，无漂移）；`grep -n "def word_count_md" src/shenbi/gates/shared.py`→100 行 ✓；`sed -n '341,375p' src/shenbi/gates/g2.py`→ratio > 0.5 → WARN + `meta_exceeds_50%_threshold` ✓（"56 chapters/31.3%"统计未验证——无对应可复核数据源）
- 置信度: high

### docs/framework/decisions-schema.md
- 处置: deep-read（高风险全查）
- 声称检查的不变量: [枚举与 contracts/schemas/decisions.py 一致；P2.5 表与 _p25 校验器一致；字段必填性与 pydantic 模型一致；schema 版本串]
- findings: [F908]
- 验证命令: `grep -n "VALID_SEVERITY\|requires =" src/shenbi/contracts/schemas/decisions.py`→12 行 severity={low,**medium**,high}（文档枚举节仅列 low/high）；36 行 `requires = self.severity in ("medium","high") or basis=="manual_override"`（文档 P2.5 表仅写 high）；71-77 行 selections/adjustments/budget 均有默认值（文档标 selections 必填=yes）；DECISIONS_SCHEMA_VERSION="shenbi-decisions-v1" ✓；_RATIONALE_MAX_CHARS=100 ✓
- 置信度: high

### docs/framework/dependency-dag.json
- 处置: deep-read
- 声称检查的不变量: [为由 sync-contracts 生成的产物且与提交一致（CI codegen-idempotency 强制）]
- findings: 无
- 验证命令: `python3 -c "import json; d=json.load(open('docs/framework/dependency-dag.json')); print(list(d.keys()))"`→{"edges":...}；未逐边交叉验证（CI `git diff --exit-code -- docs/framework/` 已强制新鲜度）
- 置信度: medium

### docs/framework/dispatcher.md
- 处置: deep-read
- 声称检查的不变量: [shenbi-dispatch 用法签名；src/shenbi/dispatcher/ 存在]
- findings: 无
- 验证命令: `pyproject.toml:59` 入口 ✓；`ls src/shenbi/dispatcher/`→cli/executor/modes ✓；与 dispatcher/cli.py 参数序一致（skill test_type round_dir [prompt]，经 justfile dispatch recipe 交叉印证）✓
- 置信度: high

### docs/framework/gates.md
- 处置: deep-read
- 声称检查的不变量: [8 门表格与 gates/cli.py 分发表一致；just gate / shenbi-validate 用法]
- findings: 无
- 验证命令: `grep -n "gate == \"G" src/shenbi/gates/cli.py`→G0-G7（另有 G_TRANSITION/G_DISPATCH/G_RECONCILE 未列，属超出而非错误）✓；justfile gate recipe ✓
- 置信度: high

### docs/framework/logging.md
- 处置: deep-read
- 声称检查的不变量: [get_logger 为统一入口；链接 ../api/logging.md 有效]
- findings: 无
- 验证命令: `grep -rn "from shenbi.logging import get_logger" src/shenbi | wc -l`→广泛使用 ✓；链接扫描 ✓
- 置信度: high

### docs/framework/scoring.md
- 处置: deep-read
- 声称检查的不变量: [rubric 路径模式存在；acceptance.json 存在]
- findings: 无
- 验证命令: `ls tests/tiers/t1-skill/shenbi-worldbuilding/rubric.md tests/tiers/acceptance.json`→✓
- 置信度: high

### docs/framework/truth-files.index.json
- 处置: deep-read
- 声称检查的不变量: [覆盖除 2 个 meta 外的全部磁盘技能；为 CI 强制的生成产物]
- findings: 无
- 验证命令: python 集合比对→index 技能 72 个，disk-index 仅差 shenbi-writing-skills/using-shenbi（meta，符合预期）；index-disk 为空 ✓
- 置信度: medium

### docs/framework/truth-files.yaml
- 处置: deep-read（高风险全查）
- 声称检查的不变量: [canonical 词表与 skills 契约一致；"18 dims" 注释与 audit 阶段技能数一致]
- findings: 无（"15 kinds" 的错误在 overview.md/concepts.md 侧，本文件实际 16 种）
- 验证命令: `grep -o 'kind: [a-z-]*' docs/framework/truth-files.yaml | sort -u | wc -l`→16；audit 阶段 18 技能（deps.json）与 62 行注释一致 ✓；CI codegen-idempotency 强制新鲜度 ✓
- 置信度: high

### docs/getting-started/concepts.md
- 处置: deep-read
- 声称检查的不变量: [15 kinds 声称；9 阶段；8 门；90/94/100；G7 定位描述；链接有效]
- findings: [F907（同 overview）, F918]
- 验证命令: kind 计数同上→16≠15；阈值与 acceptance.json ✓；G7 描述"pipeline milestones"与 g7 实际"post-round audit"略偏（并入 M 级观察，未单列）；`sed -n '53,60p'`→56-57 行双 `---` ✓；链接扫描 ✓
- 置信度: high

### docs/getting-started/first-novel.md
- 处置: deep-read（可跟随性重点）
- 声称检查的不变量: [7 阶段技能清单与 deps.json prerequisites 逐相一致；round-exec.sh 存在；shenbi-dispatch 命令有效；pipeline CLI 用法与 just recipe 一致；初始化产物列表与 truth-files.yaml producer=pipeline 一致]
- findings: 无
- 验证命令: python 打印 deps.json 各 phase prerequisites→genesis 11/architecture 5/planning 3/drafting 9/audit 18/foundation 4/management 9/import 4/short-story 3，与文档清单逐名比对**完全一致** ✓；`bash -n tests/round-exec.sh` 级存在性 `ls` ✓；pipeline-state.json/novel.json/genre-config.json/genesis-context/ 在 truth-files.yaml 80-82 行均为 producer: pipeline ✓
- 置信度: high

### docs/getting-started/installation.md
- 处置: deep-read（可跟随性重点）
- 声称检查的不变量: [requires-python >=3.11；docs dependency group 存在；全部表格命令有效]
- findings: 无
- 验证命令: `grep -n "requires-python" pyproject.toml`→>=3.11 ✓；`grep -n "docs = \[" pyproject.toml`→50 行 ✓；表格命令 just check/test/fix/docs/pipeline-* 与 justfile 逐项核对 ✓
- 置信度: high

### docs/index.md
- 处置: deep-read
- 声称检查的不变量: [67+2 计数；8 门；94/100；链接有效]
- findings: [F904（证据链：docs/index.md:21-23）]
- 验证命令: 计数同全局核对→74 实际；链接扫描 0 死链 ✓
- 置信度: high

### docs/roadmap.md
- 处置: deep-read
- 声称检查的不变量: [tests/build_registry.py 仍不存在（P0 延期项前提仍成立）；hook 确已不在 pre-commit 配置中]
- findings: 无
- 验证命令: `ls tests/build_registry.py`→No such file ✓；`grep -n "registry-lockfile-fresh" .pre-commit-config.yaml`→无匹配 ✓（延期描述与现实自洽）
- 置信度: high

### docs/skills/index.md
- 处置: deep-read
- 声称检查的不变量: [目录覆盖全部技能；总数 69 声称；数据源 deps.json 的忠实性；管道外技能清单与 deps.json _out_of_pipeline 一致]
- findings: [F905]
- 验证命令: `grep -c "foreshadowing-lifecycle\|review-group-" docs/skills/index.md`→0（5 个磁盘技能缺失）；deps.json _out_of_pipeline={t1_only_auxiliary:4, t1_only_meta:2, t1_only_drafting_phase:1}=7 与"管道外 7"一致 ✓；README 阶段表与本文档一致 ✓
- 置信度: high

### goal-prompt.md
- 处置: deep-read
- 声称检查的不变量: [59 skill/60 T1 目录/115 fixture 快照与当前一致性；G0 19 项检查；G0.13-16 语义；G7.17/TOOL_TAMPER；summarize-round.py 存在；_tool_hashes 锁定对象；acceptance 阈值]
- findings: [F906（59 skill 部分）, F913, F919]
- 验证命令: `ls tests/tiers/t1-skill | wc -l`→70≠60；G0 检查 ID 全集（g0.py+g0_purity.py+g0_skill_contract.py）→G0.1-16 + 5b + 9b + 9c = **19 项 ✓**（"19 项"数字本身正确）；`grep -o '"G7\.[0-9]*"' src/shenbi/gates/g7.py | sort -u`→最大 G7.16，**无 G7.17**；`grep -rn "TOOL_TAMPER" src/`→0 匹配；`ls src/shenbi/summarize_round.py src/shenbi/update_progress.py src/shenbi/contract.py`→均不存在但 deps.json `_tool_hashes` 仍含这 3 个键；G0.13/14/15/16 现语义（independence/calibration hash/gate registry/skill contract）与文档描述的 progress/queue/summary 语义全部不符；`ls tests/fixtures | wc -l`→66（≠历史 115，快照性质）；outline-example.md:7 目标字数 100000
- 置信度: medium（2026-06-13 历史快照文档，按现状核对）

### outline-example.md
- 处置: deep-read
- 声称检查的不变量: [与 tests/fixtures/outline-example.md 逐字节一致（G0.11 前提）；结构完整可供 pipeline init 消费]
- findings: [F919（20 万字声称在 goal-prompt 侧，本文件目标字数 100000 为事实基准）]
- 验证命令: `diff outline-example.md tests/fixtures/outline-example.md`→无输出（IDENTICAL）✓
- 置信度: high

---

## findings 明细

F901 | 执行协议引用已删除的 dispatch 脚本 | error | P1 | command-to-give.md:48 | 根因: PR-22 (0f68102) 删除 tests/dispatch-subagent.sh 后协议文档未同步，ADR-0009 声称保留的 shim 也一并消失 | 验证: `ls tests/dispatch-subagent.sh`→No such file；`git log --oneline --diff-filter=D -- tests/dispatch-subagent.sh`→0f68102 | 建议: 将第 48 行改为 `uv run shenbi-dispatch`（AGENTS.md 已给出正确入口）

F902 | README pipeline-init 示例命令实测失败 | error | P1 | README.md:45 | 根因: justfile `pipeline-init seed project_dir=""` 只收 2 个位置参数且不透传额外 flag，`--auto` 被 just 解析为 recipe 名 | 验证: `just --dry-run pipeline-init outline-example.md ./my-novel --auto`→`error: justfile does not contain recipe '--auto'` | 建议: README 改为两参数形式，或给 recipe 加 `*extra` 透传

F903 | "G0.13 工具哈希阻断"承诺已静默失效 | security | P1 | command-to-give.md:24 vs src/shenbi/gates/g0.py:552-590 | 根因: G0.13 语义已改为 independence markers；`_tool_hashes` 在 src/ 中无任何 gate 消费（仅 lock 脚本写入 + deps.py schema 声明），中途篡改工具不再被任何 gate 拦截 | 验证: `grep -rn "_tool_hashes" src/`→仅 g0.py:80,128 注释 + schemas/deps.py:62；`grep -n "G0.13" g0.py`→independence markers | 建议: 恢复 G0 内 _tool_hashes 校验或更正协议文档；同时清理 deps.json 中 3 个已删文件的历史条目

F904 | skill 总数 69 声称过期（实际 74） | error | P2 | AGENTS.md:19、README.md:16/18/22/88、docs/index.md:21-23 | 根因: 5 个新技能（foreshadowing-lifecycle、review-group-*×4）落盘后未回写计数 | 验证: `ls -d skills/*/ | wc -l`→74；deps.json→69 | 建议: 统一更新四处计数（72 功能 + 2 meta = 74），或明确"69 = deps.json 登记数"的口径

F905 | 技能目录缺 5 个技能 | error | P2 | docs/skills/index.md（全文 0 处提及该 5 技能；结尾注 "Total unique skills: 69"） | 根因: 目录声称源自 deps.json，而这 5 技能未纳入任何 t2-phase/_out_of_pipeline | 验证: `grep -c "review-group" docs/skills/index.md`→0；skills/shenbi-review-group-craft/SKILL.md 存在完整 contract | 建议: 在 deps.json 登记这 5 技能（或明确其归属）并重生成目录

F906 | "59 个 skill"推进条件过期 | error | P2 | command-to-give.md:85、goal-prompt.md:19-20/65/69-70 | 根因: 0.1.0 时代计数；现 T1 集 69（t1-skill 目录 70 含 _template） | 验证: `ls tests/tiers/t1-skill | wc -l`→70 | 建议: 改为动态口径（"t1-skill 目录全集"）避免硬编码计数

F907 | "15 种 kind"实际为 16 种 | error | P2 | docs/architecture/overview.md:141/166、docs/getting-started/concepts.md:29/31 vs docs/framework/truth-files.yaml | 根因: `chapter` kind 加入后未更新两处计数 | 验证: `grep -o 'kind: [a-z-]*' docs/framework/truth-files.yaml | sort -u | wc -l`→16 | 建议: 计数改为 16 或去掉具体数字引用 yaml

F908 | decisions 枚举与 P2.5 表欠指定 | error | P2 | docs/framework/decisions-schema.md:66-68/86-88 vs src/shenbi/contracts/schemas/decisions.py:12,36；连带 AGENTS.md:70 | 根因: severity 枚举漏列 `medium`（文档自身示例第 33 行还在用 medium）；P2.5 表未覆盖 routine+medium 也 REQUIRED 的代码行为；Fields 表把有默认值的 selections 标为必填 | 验证: `grep -n "VALID_SEVERITY\|requires" decisions.py`→12/36 行 | 建议: 补全枚举与规则表，selections 必填性按 pydantic 默认值更正

F909 | basedpyright 设计笔记三处失实 | error | P2 | docs/basedpyright-overrides.md:13-18/55-58 vs pyproject.toml:382-402 | 根因: 配置从 warning 收紧/改为 none、skill_utils 环境移除后未回写文档 | 验证: `sed -n '371,412p' pyproject.toml`→六规则全 "none"、executionEnvironments 仅 tests；mypy 无 skill_utils override | 建议: 文档按现状改写（顺带修 pyproject.toml:379 注释"warning"与值"none"的自相矛盾）

F910 | "No ignore_errors in mypy overrides" 不实 | error | P2 | CONTRIBUTING.md:44 vs pyproject.toml:84-95 | 根因: numpy.* override 仍含 `ignore_errors = true`，且 4 个 overrides 块仍在 | 验证: `grep -n "ignore_errors" pyproject.toml`→91 行 | 建议: 改为"项目代码零 overrides（第三方 numpy 除外）"的准确表述

F911 | plugin-manifest CI 强制描述失效 | error | P2 | CONTRIBUTING.md:71/80 | 根因: job 已并入 codegen-idempotency（ci.yml:69 注释），且 `.codex-plugin/` 在 .gitignore:20 → `git diff --exit-code -- .codex-plugin/`（ci.yml:89）恒空转 | 验证: `git ls-files .codex-plugin`→空；`grep -rn "plugin-manifest" .github/workflows/`→仅注释 | 建议: 更正 job 名；如需真实强制，将 .codex-plugin 移出 gitignore 并跟踪

F912 | "pip-audit weekly" 不存在 | error | P2 | SECURITY.md:26 vs .github/workflows/security.yml:1-5、nightly.yml:20 | 根因: security.yml 仅 push/PR 触发；nightly cron 处于注释状态 | 验证: `sed -n '1,13p' security.yml` + `grep -n cron nightly.yml` | 建议: 启用 nightly cron 或删去 "weekly"（CodeQL weekly 属实，保留）

F913 | goal-prompt 快照多处与现状矛盾 | error | P2 | goal-prompt.md:34/85-90 | 根因: 2026-06-13 快照未随 b978d3c（删 summarize_round/update_progress/tests/rounds）与 G0 检查语义演进更新：G0.13-16 语义全变、G7.17/TOOL_TAMPER/GATE_MISMATCH 不存在、deps.json `_tool_hashes` 残留 3 个已删文件键 | 验证: 见 goal-prompt.md 条目验证命令 | 建议: 加"历史快照，以 command-to-give.md 为准"声明或整体刷新

F914 | CHANGELOG "7-gate (G0-G7)" 自相矛盾 | error | M | CHANGELOG.md:19 | 根因: G0-G7 为 8 门；0.1.0 历史条目内数字与区间不一致 | 验证: 直接文本证据；AGENTS.md/README/gates.md 均为 8 门 | 建议: 更正为 8-gate

F915 | CoC 联系方式占位符未填 | error | M | CODE_OF_CONDUCT.md:39 | 根因: 模板 `[INSERT CONTACT METHOD]` 未定制 | 验证: 文本证据 | 建议: 填入 GitHub 私信/邮箱等真实渠道

F916 | ADR-0009 "shim 保留"结果已失效 | error | M | docs/adr/0009-dispatcher-python-rewrite.md:12 | 根因: 0f68102 删除 shim，ADR 无后续注记 | 验证: git log 见 F901 | 建议: 在 ADR 追加修订注记（superseded/amended）

F917 | AGENTS.md 结构树含已删除的 tests/rounds | error | M | AGENTS.md:16 | 根因: b978d3c "remove round test infrastructure (superseded by pipeline)" 后未更新结构注释（运行时 round 目录可再生但 "Active + archived" 语义失效） | 验证: `ls tests/rounds`→不存在；`git show --stat b978d3c` | 建议: 更新结构树并注明 round 目录为运行时产物

F918 | concepts.md 连续双水平线 | error | M | docs/getting-started/concepts.md:56-57 | 根因: 删节残留 | 验证: `sed -n '53,60p'` | 建议: 删除多余 `---`

F919 | 目标字数口径不一 | error | M | goal-prompt.md:3/71（"20 万字"）vs outline-example.md:7（目标字数 100000） | 根因: goal 快照写 20 万，种子文件为 10 万 | 验证: 两处直接文本证据 | 建议: goal-prompt 刷新时对齐

## 交叉一致性抽检（补充）
- AGENTS.md（权威）vs 本段各文档: 94/90/100、8 门、9 阶段、3 流水线、G0.9/G0.11/G2.5/G4 语义、decisions G2/G4 行为、field-level reads——全部与代码/相互一致；仅 skill 计数（F904）与 tests/rounds（F917）两处 AGENTS.md 自身过期。
- mkdocs nav 13 条 ↔ 文件：全部存在；nav 未列 chapter-file-format.md/decisions-schema.md/truth-files.yaml 等（作为仓库内参考文档，非站点页面，无断链后果）。
- first-novel.md/installation.md 新用户路径：除继承 F902（README 侧）外可完整跟随。
