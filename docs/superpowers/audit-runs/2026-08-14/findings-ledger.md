# Findings Ledger
| ID | 标题 | 类别 | 严重度 | 证据 | 根因 | 验证 | 影响 | 建议方向 | 深度 | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| D1-01 | pyproject dev group 含 sentence-transformers 与 :17 注释矛盾（dev 安装拉入 torch/CUDA），且使 2 个降级路径测试永远 skip（masking） | deps | P1 | pyproject.toml:17,47; tests/unit/pipeline/test_truth_embed.py:122; test_context_assemble.py:167 | 注释声明已移至 optional，dev group 却仍显式声明；sentence-transformers 经 embeddings 链拉 torch | uv tree 显示 st 在 dev group (*)；pytest -rs 显示 2 skip "sentence_transformers installed; degradation path not testable" | dev 安装违背注释意图（拉 torch/CUDA 巨型依赖）；2 个降级路径测试失去意义 | 从 dev group 移除 sentence-transformers（仅保留 optional），同步 uv.lock | deep-read | open |
| D1-02 | pytest addopts 全局 `--cov` 使 `--collect-only` 触发 cov 插件：输出 16.08% 假 FAIL 报告并覆写 tests/coverage/ | error | P2 | pyproject.toml:420-426 | addopts 无条件附加 cov，collect-only 也执行 | `pytest --collect-only` → "FAIL Required test coverage of 85.0% not reached. Total coverage: 16.08%" | collect-only 产生误导性失败输出；反复覆写 coverage.xml 破坏 G3 证据链 | addopts 用 `--cov` 条件化或 collect-only 时传 --no-cov | deep-read | open |
| D1-03 | G2.12 对文件清单输入报 WARN "may be truncated"（Z8.files 2047 字节清单被截断校验？） | error | P2 | src/shenbi/gates/cli.py G2 路径 | 大文件清单在 G2.12 长度/截断检查中触发 WARN | shenbi-validate G2 zones/Z8.files generative → G2.12 WARN "may be truncated" | 清单文件作 G2 输入时 WARN 但 PASS，语义不清（Z4 深读确认） | Z4 深读后定级 | deep-read | open |
| F0-01 | skills 数量漂移：AGENTS.md:19 声称 69、README.md:10 声称 67、docs/skills/index.md:189 声称 69（67+2），实际 skills/ 74 个 | error | P2 | AGENTS.md:19; README.md:10; docs/skills/index.md:189; skills/ 目录 74 项 | 目录新增 skill 后未同步文档计数 | ls -d skills/*/ \| wc -l = 74；D1③ 74 SKILL.md 解析 | 文档误导（计数作为事实引用） | 更新三处计数或改为动态生成 | deep-read | open |
| F0-02 | deps.json 契约缺 5 skill 登记（foreshadowing-lifecycle + review-group-{character,craft,factual,plan}），truth-files.index.json 与 executor_config.toml 有引用；lint_repo_consistency 未抓 = 契约 lint 覆盖洞 | error | P1 | tests/tiers/deps.json（无此 5 名）; docs/framework/truth-files.index.json:24,34-37; executor_config.toml（foreshadowing-lifecycle override） | 契约三源不同步，lint 无 skill↔deps.json 完整性检查 | python 统计：deps.json 68 vs 目录 74，差 5 全为上述；D1② 5 个 lint 全过 | 契约单信源被破坏且无检测；pipeline 可调度未登记 skill（executor_config 引用） | lint 增加 skill 目录↔deps.json 闭包检查；登记 5 skill 或明确 out-of-pipeline | deep-read | open |
| F0-03 | gate 文档漂移：overview.md:55 "八道门"、gates.md:3 "8 validation gates"、README "8 道" vs CLI 实际 11 gate（G0-G7+G_TRANSITION+G_DISPATCH+G_RECONCILE），活跃文档 0 引用额外 gate | error | P2 | src/shenbi/gates/cli.py:61,131-133; docs/framework/gates.md:3; docs/architecture/overview.md:55 | 3 个内部 gate 未入文档 | cli.py 声明 11 gate；grep 非 archive 文档 0 命中；tests/unit/gates/test_g_{dispatch,reconcile,transition}.py 存在 | 文档与实现门数不符，读者误解门体系 | 更新 gates.md/overview.md 或区分内部 gate | deep-read | open |
| F0-04 | 归档计数漂移：INDEX.md:4 "已归档 99"、:80 "97 个"，实际 specs/archive/ 91 项 | error | M | docs/superpowers/specs/INDEX.md:4,80 | 归档移动后未更新计数 | ls specs/archive \| wc -l = 91 | 索引计数失真 | 修正计数或自动生成 | deep-read | open |
| F0-05 | command-to-give.md:48 引用已删除脚本 tests/dispatch-subagent.sh（0f68102 PR-22 删除 shim），执行者照做会失败 | error | P2 | command-to-give.md:48; git show 0f68102 | 文档未随脚本删除更新 | 文件不存在；git log --diff-filter=D 确认删除 | 执行协议失效（评分分派路径） | 改用 shenbi-dispatch 或更新协议 | deep-read | open |
| F0-06 | python 版本三元不一致：requires-python>=3.11 vs mypy python_version=3.12 vs basedpyright pythonVersion=3.11 | error | P2 | pyproject.toml:8,359,378 | 类型检查基准未对齐 | grep 确认三值 | 类型检查语义基准漂移（3.11 vs 3.12 语法/API 差异可能漏报/误报） | 统一为 3.11 或 CI 实际版本 | deep-read | open |
| F0-07 | SECURITY.md:20-21 声称 pip-audit "runs on every PR and weekly"，security.yml 无 schedule、nightly.yml 无 pip-audit job | error | P2 | SECURITY.md:20-21; .github/workflows/security.yml（仅 push/PR） | 文档声明与 workflow 触发面不符 | grep schedule security.yml = 0 | 供应链审计频率声明失真 | 加 weekly schedule 或改文档 | deep-read | open |
| F0-08 | coverage 注释漂移：pyproject:447-451 声称 >=90% line / >=80% branch、"89 (not 90)"，实际 fail_under=85 | error | M | pyproject.toml:447-452 | 阈值调整后注释未更新 | 读配置确认 fail_under=85 | 注释误导（声称 90 实际 85，监管面解释错误） | 更新注释或调整阈值 | deep-read | open |
| Z11-01 | novel-output 最终产物中 44/89 个 chapters/*decisions.json 无效 JSON（Extra data/空文件/control char），staging 39/56 无效；G4 decisions validator 严格拒绝（G4.dec.invalid_json） | error | P1 | novel-output/xinghuo-ranqiong/chapters/chapter-1-decisions.json 等 44 个（全清单见 Z11 报告）；src/shenbi/gates/g4/decisions_validator.py:99-101 | decisions.json 写路径未剥离 LLM 输出中的 memo/注释后缀（"Extra data: line N" = JSON 后拼接 markdown）；或 G4 未在落盘前校验 | python 全库扫描：145 个 decisions.json 中 83 无效（57%）；validator json.loads 严格 | 真实运行产物大面积违反 decisions-schema 契约；若这些产物过过 G4，说明校验被绕过；若没过，说明 pipeline 落盘了失败产物 | Z11 agent 深查根因（写路径/G4 时序），定级后转 spec | deep-read | open |
| F500 | scoring_bridge 双评员一致性/塌缩检测 dead-wire：validate_dual_scorer/check_single_scorer_collapse 无生产调用方（spec §5.5 补丁2/3 运行时零执行） | error | P2 | src/shenbi/orchestration/scoring_bridge.py:10,21；grep 全仓 src/ 仅自身定义 | 双评员/塌缩检测未接入逐章循环（wave4 plan 目标未达成） | grep 确认生产调用 0；G3.4 由 gates/g3.py:193-206 另行强制 | 安全网特性"看似实现"实际零执行 | 接入或显式废弃删档 | deep-read | verified |
| F501 | escalation_bridge dead-wire：parse_resonance_scores/run_escalation_check 无生产调用；resonance_trend.md 写而不读（chapter_loop 直连 check_escalation） | error | P2 | src/shenbi/orchestration/escalation_bridge.py:10,28；chapter_loop.py:1001 直连 | 桥从未接线；trend 文件唯一消费者是 compute_drift 解析 header | grep 生产调用 0；读 chapter_loop.py:967-1035 确认直连 | 死代码 + trend 写路径浪费 | 接入或废弃 | deep-read | verified |
| F502 | FileChange.status Literal 定义在 contracts/ownership.py:22 而非 enums.py（enums.py:1 明示"所有 Literal 必须从此处 import"） | error | P2 | src/shenbi/contracts/ownership.py:22; src/shenbi/contracts/enums.py:1 | 枚举单一信源契约被违反 | read 两文件确认 | 词表分裂风险 | 移入 enums.py | deep-read | verified |
| F503 | write_audit._declared_patterns 宽 except Exception 吞错：derive_output_files 意外异常 → declared=[] → 未声明写入假阳性 GATE_FAIL | error | P2 | src/shenbi/audit/write_audit.py:25-26 | 吞错掩盖真实异常类别 | read 确认 except Exception: return [] | 假阳性阻断 pipeline | 仅捕获 ContractError | deep-read | verified |
| F504 | ledger.record() 对 usage 值裸 int() 强转，非 int 可强转值 ValueError 崩 hot path（违反"must never crash the pipeline"） | error | P2 | src/shenbi/cost/ledger.py:73-75 | 强转无防御 | read 确认 int(usage.get(...,0)) | 计量热路径可崩 | _safe_int 兜底 | deep-read | verified |
| F505 | TokenLedger._write_lock 每实例一把，dispatch_helper 每次 record 新建实例 → 跨实例并发 append 可交错（iter_records 跳过损坏行=丢计量） | error | P2 | src/shenbi/cost/ledger.py:57; dispatch_helper.py:1333 | 锁作用域与实例生命周期不匹配 | read 确认锁在 __init__ 内 | 并发写丢计量 | 进程级锁/filelock | deep-read | verified |
| F506 | report._try_avg_g3_score 把任意 **/*score*.json 的任意顶层 0-100 数值当 G3 分求平均，CPQ 指标名实不符 | error | P2 | src/shenbi/cost/report.py:18-35,74-79 | 启发式无 schema 过滤 | read 确认 glob 无 schema 校验 | 展示指标失真 | 按 rubric/schema 过滤 | deep-read | verified |
| F507 | 写所有权审计对 deleted 状态零拦截（status=deleted 不触发 record/field 维度）→ 技能删除自身声明写入文件可静默过审 | error | P2 | src/shenbi/audit/write_audit.py:48-64; ownership.py:101-136 | deleted 分支无检查 | read 确认无 deleted 检查路径 | 数据丢失路径可过审 | 补 deleted 检查 | deep-read | verified |
| F508 | d1-06-coverage-gaps.txt 被 collect-only 覆写 coverage.xml 污染（16.08%），Z 区维度 8 依据失效 | error | P2 | d1-baseline.md; d1-11-collect-only-full.log | 审计工件自身被 addopts 全局 --cov 污染（D1-02 同根因） | 协调者已重生成真实 85.16% 版本并更正 | 审计工具链被误导 | 已修复（重提取 7123 行） | deep-read | verified |
| F509 | compute_file_change 对 pre==post（含 None,None）报 status="modified" 幻影条目 | error | M | src/shenbi/audit/snapshot.py:103-104 | 无 pre==post 特判 | read 确认 | 语义瑕疵，不影响判定 | 加 pre is None and post is None 特判 | deep-read | verified |
| F510 | report.main() 尾部 return 2 不可达（subparsers required 仅 report）；print() 在 CLI 入口（AGENTS.md No print 边缘） | error | M | src/shenbi/cost/report.py:90-97 | 死代码 | read 确认 subparsers required | 死代码 | 删除 | deep-read | verified |
| F511 | 归档 spec 文档行号漂移（write_audit.py:31 lazy import 实际在 :22 等，历史态描述） | error | M | specs/archive/2026-08-02-issue24-cyclic-import-refactor-design.md:183 | 历史文档未随重构更新 | read 确认 | 历史文档误导 | 归档文档订正或标注 | deep-read | verified |
| F512 | 写所有权审计（audit/ 包）在主 dispatch 路径被绕过：API/IDE 路径不调 write-audit，仅 legacy CLI 路径执行 | error | P2 | dispatch_helper.py:3-4,1826-1841; dispatcher/cli.py:11; executor.py:228 | 审计接线只覆盖 legacy 路径 | grep dispatch_helper 无 audit_writes 调用 | 主路径产物无写审计 | 接入 API/IDE 路径 | deep-read | verified |
| F601 | detect_drift 对话密度塌陷触发被 >5.0 严格比较吞掉（max(…,5.0)=5.0 不满足 >5.0）→ 对话塌陷 is_drift=False | error | P1 | src/shenbi/skill_utils/drift_detection/linguistic_drift.py:215,218 | off-by-one：触发值=阈值 | PYTHONPATH=src 运行验证 dialogue-collapse-only → is_drift False | 角色消失信号静默放过 | max(…,5.01) 或 OR 条件 | deep-read | verified |
| F602 | establish_baseline 全仓零调用 → style/linguistic_baseline.json 永不生成 → chapter_loop 语言漂移 3 层干预静默失效 | error | P1 | baseline.py:24,78-83; chapter_loop.py:2014-2019 | 建立函数从未接线 | grep 零调用 + find 文件不存在 | 安全网静默失效 | 接线或显式废弃 | deep-read | verified |
| F603 | records drift 只检 md→YAML 方向：YAML 新增 hook 未同步派生表不报 drift | error | P2 | src/shenbi/records/drift.py:82-93 | 只遍历 md_rows | read 确认无反向检查 | 派生视图陈旧仍过 gate | 补反向检查 | deep-read | verified |
| F604 | compute_stats 引号桶 ASCII 引号重复计数（chars 串重复字符，count 双计） | error | P2 | src/shenbi/skill_utils/style_learning/compute_stats.py:27,226 | 字面量含重复字符 | 运行验证 '他说"你好"。' → count 4（应为 2） | 密度口径不一致 | set(chars) 去重 | deep-read | verified |
| F605 | 空 system_terms 正则匹配空串 → 密度 ~1000‰ 假 ESCALATE（健康章节假暂停） | error | P2 | linguistic_drift.py:107 | "\|".join([])=="" → findall("") 每位置匹配 | 运行验证 system_term_density: 1125.0 | 假阳性暂停 pipeline | 空列表返回 0 + 类型校验 | deep-read | verified |
| F606 | update_genre_config floor 只认 int：float/str 绕过下限（59.5 通过） | error | P2 | config/config_coherence.py:121-130 | 类型孔 | 运行验证 59.5 被接受 | 配置治理可绕过 | isinstance(int,float) 非 bool | deep-read | verified |
| F607 | 同包双 baseline 路径分裂：baseline.py 写 style/ vs linguistic_drift.py 读 context/；术语表也分裂 | error | P2 | baseline.py:78; linguistic_drift.py:278,296 | 平行实现互不消费 | grep 双路径确认 | 死数据 + 不一致 | 统一路径与术语源 | deep-read | verified |
| F608 | cjk.py 引号桶只数相邻字符对：真实引号文本恒计 0 | error | P2 | src/shenbi/text/cjk.py:54,67-70 | 桶 token 是相邻双字符串 | 运行验证 '「你好」' → 0 | 指标恒 0 失真 | 计开引号单字符 | deep-read | verified |
| F609 | replay 撕裂行/签名断链静默截断且无日志（改写文件不可追踪） | error | P2 | src/shenbi/trace/replay.py:40-48 | except Exception: break 无日志 | read 确认 | G7/排障不可见损坏原因 | 记 WARN（原因+行号） | deep-read | verified |
| F610 | recall_overdue_hooks 对缺 id hook 直接 KeyError，单条坏记录使整批崩溃 | error | P2 | skill_utils/foreshadowing_recall/recall.py:47 | 无 get 防御 | read 确认 | 确定性过滤可崩 | hook.get("id") 判空跳过 | deep-read | verified |
| F611 | config 治理规则 1 只拦 auditDimensions.<dim>:false，整键 auditDimensions 禁用可绕过 | error | P2 | config/config_coherence.py:109 | startswith 要求带点 | read 确认 | 关键审计维度治理可绕过 | 覆盖整键与更深子键 | deep-read | verified |
| F201 | chapter_planning/context_composing/volume_outlining 契约模型 dead-wire，g4 携带私有且**规则不同**的实现 | error | P1 | 见 Z2.a.md#F201 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F202 | contracts/registry.py REGISTRY + load_skill_contract 生产无消费者（仅测试用） | optimization | P2 | 见 Z2.a.md#F202 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F203 | schemas/deps.py DepsDoc + phase_of 未接线；sync_contracts 仍用 json.loads 解析 deps.json | optimization | P2 | 见 Z2.a.md#F203 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F204 | schemas/novel.py NovelConfig 声称 g6 consumer，g6 未 import | optimization | P2 | 见 Z2.a.md#F204 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F205 | schemas/scores.py ScoreReport 声称 g5 consumer，无生产 import | optimization | P2 | 见 Z2.a.md#F205 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F206 | schemas/state.py ProgressDoc/SummaryDoc 从未被加载验证（C3 修复无生效面） | optimization | P2 | 见 Z2.a.md#F206 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F207 | skills/_scoring_base.py ScoreReport + score_arc/stratum/volume 评分契约 dead-wire（M3 修复未接线） | optimization | P2 | 见 Z2.a.md#F207 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F208 | enums.py Severity/Verdict 无生产消费者；严重性字面量仍散落 4 处裸字符串 | error | P2 | 见 Z2.a.md#F208 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F209 | base.py GateOutcome.status 用裸 Literal 复制 status.py GateStatus 词表 | error | P2 | 见 Z2.a.md#F209 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F210 | hooks.py 的 SKILL.md 行号引用漂移（超出 ±5） | error | P2 | 见 Z2.a.md#F210 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F211 | executor.py SHENBI_G1_SKIP_READS 环境特性零测试覆盖 | optimization | P2 | 见 Z2.a.md#F211 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F212 | executor.py run_g1/run_g2 不检查 returncode，stdout 非 JSON 时裸 JSONDecodeError | error | P2 | 见 Z2.a.md#F212 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F213 | dispatcher/modes/codex.py 单次 codex exec、无重试/429/finish_reason/并行上限（仅 pipeline 路径有） | optimization | P2 | 见 Z2.a.md#F213 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F214 | codex.py _record_completion 不记录 current_scorer_agent；G3.4 fail-closed 与 pipeline 伪造 scorer 并存 | error | P1 | 见 Z2.a.md#F214 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F215 | codex.py 用 `\{[^{}]*\}` 提取首个"无嵌套花括号"JSON 片段 | error | P2 | 见 Z2.a.md#F215 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F216 | genre_config.py `_disabled_dimensions_have_rules` 在 customRules 为空时跳过检查 → G4 校验洞 | error | P1 | 见 Z2.a.md#F216 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F217 | pacing_design.py CONSTELLATION 区间三处不一致（docstring 20-30 / 代码 15-35 / SKILL.md 15-25） | error | P2 | 见 Z2.a.md#F217 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F218 | fields.py 部分匹配时未命中的已声明字段被静默丢弃（escape hatch 仅全缺触发），调用方丢弃 matched 标志 | error | P1 | 见 Z2.a.md#F218 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F219 | executor.py 对 ContractError 静默 fail-open：registry 缺失 → 空 inputs → G1 空集真空 PASS → 无上下文派发 | error | P2 | 见 Z2.a.md#F219 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F220 | ownership.py OWNERSHIP 矩阵仅 6 条参考条目（docstring 自述「支柱一续」），其余技能落 file-level 检查 | optimization | P2 | 见 Z2.a.md#F220 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F300 | dispatch_helper `"\u003c"` 转义是 no-op，文档声明的标签注入缓解未生效 | security | P1 | 见 Z3.a.md#F300 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F301 | 并行审计波使串行审计路径（run_audit_layer / 审计 BLOCKING 重审环 / resonance 解析与落盘 / boundary circle）在生产中不可达 | error | P1 | 见 Z3.a.md#F301 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F302 | TokenLedger 接线不全：genesis/closure/triggers/并行 post-draft/审计波调用 dispatch_skill 均未传 state，账本缺大部分调用；chapter 字段恒 0 | error | P0 | 见 Z3.a.md#F302 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F303 | 快照子系统生产未接线：create_differential_snapshot / restore_from_snapshot / _prune_old_snapshots / chapter_loop._snapshot_chapter_files 全部无生产调用方；step 15 "pre-revision-snapshot" 空转；last_snapshot 永不写入 | error | P1 | 见 Z3.a.md#F303 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F304 | RetryExhaustedError 在 crash-resume 预算耗尽路径未被捕获，CLI 裸崩而非 escalation checkpoint | error | P1 | 见 Z3.a.md#F304 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F305 | 审计严重度裸子串检测（"BLOCKING"/"FAIL"）产生误报 | error | P1 | 见 Z3.a.md#F305 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F306 | audit_context_cache 读错 volume_map 路径 + 章节号子串匹配缺陷 | error | P2 | 见 Z3.a.md#F306 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F307 | hook_planting 模块生产死线：plant_hooks_from_plan 只在不可达分支被调用，确定性伏笔种植从未运行 | error | P2 | 见 Z3.a.md#F307 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F308 | compact_pipeline_state / _archive_chapter_state 死代码（Plan 17 10d 未勾选 TODO 从未接线） | optimization | P2 | 见 Z3.a.md#F308 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F309 | _validate_state_consistency / _heal_current_step 死代码（注释声称 cli.py resume 调用，实际无调用方） | error | P2 | 见 Z3.a.md#F309 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F310 | volume_align.py 死模块（与 chapter_loop._check_volume_map_alignment 重复，无生产调用方） | optimization | P2 | 见 Z3.a.md#F310 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F311 | scr_extractor 缓存永不失效：revision 改写章节后 SCR 持续陈旧 | error | P2 | 见 Z3.a.md#F311 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F312 | truth_io.upsert_yaml 模式序列化丢弃 markdown body（潜在数据丢失；当前无生产调用方） | error | P2 | 见 Z3.a.md#F312 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F313 | closure step 6 G4 目标路径用卷号替换 N（应为章号）——closure 正常路径 G4 校验错误文件 | error | P1 | 见 Z3.a.md#F313 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F314 | bridge 激活窗口包含已激活桥（chapter >= activation - 3 未排除 past-activation） | optimization | P2 | 见 Z3.a.md#F314 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F315 | _merge_step_result / _apply_step_outputs 为 no-op 死线（"单写者合并"实际什么都不做） | optimization | P2 | 见 Z3.a.md#F315 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F316 | revision_router.collect_audit_issues 读原始 glob 无聚合去重（F10 先例未修复） | optimization | P2 | 见 Z3.a.md#F316 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F317 | error_handler 常量与配置耦合：MAX_DISPATCH_RETRIES/MAX_AUDIT_RETRIES 死常量；dispatch 重试上限绑定 max_revision_retries（配置放大隐患） | optimization | P2 | 见 Z3.a.md#F317 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F318 | 文档/注释漂移（M 级合并条目） | error | M | 见 Z3.a.md#F318 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F319 | cmd_review MODIFY 对 PER_CHAPTER 检查点无回滚语义，feedback 泄漏到下一章 | error | P2 | 见 Z3.a.md#F319 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F400 | G2.12 无 file_type 守卫 → JSON/清单文件误报"截断"WARN（D1-03 根因核实） | error | P2 | 见 Z4.a.md#F400 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F401 | G_RECONCILE GR.2 未剥离 -scores 后缀 → 生产命名下恒误报；测试刻意绕开（masking） | error | P1 | 见 Z4.a.md#F401 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F402 | g4_length_normalizing 用未解析路径计字数 → rd+相对路径崩溃 | error | P1 | 见 Z4.a.md#F402 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F403 | CLI G4 无 round_dir 时 ValueError 崩溃，破坏 JSON/退出码契约 | error | P2 | 见 Z4.a.md#F403 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F404 | DecisionsDoc P2.5 "REQUIRED" 被空字符串 rationale 绕过 | error | P1 | 见 Z4.a.md#F404 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F405 | G4_CHECKER_SKILLS 注册表过期：漏 9 个专用 checker | error | P2 | 见 Z4.a.md#F405 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F406 | G0.3/G0.6/G7.5 使用遗留目录名 skill-output（真实布局 novel-output / project-output） | error | P2 | 见 Z4.a.md#F406 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F407 | G0 无 seed 时早退 → 全部环境检查被跳过，gate 空转 PASS | error | P2 | 见 Z4.a.md#F407 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F408 | G3.4 fail-closed 被调用方伪造 scorer 证据击穿（跨区交互） | error | P1 | 见 Z4.a.md#F408 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F409 | G1 空输入 → PASS（G1.0 SKIP 空转） | error | P2 | 见 Z4.a.md#F409 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F410 | cli.py SHORT_MAP 缺 11 个技能的 shorthand | optimization | M | 见 Z4.a.md#F410 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F411 | g0.py G0.4 missing_dirs 死代码 + G0.12 注释 "20 skills" 过期 | optimization | M | 见 Z4.a.md#F411 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F412 | g3_independence.py docstring 行引用过期 | docs | M | 见 Z4.a.md#F412 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F413 | decisions_validator.py:175 注释 "shared.py:113" 错位 | docs | M | 见 Z4.a.md#F413 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F414 | g4_chapter_revision 返回 "HARD_FAIL" 状态值不在 GateStatus 词表 | error | M | 见 Z4.a.md#F414 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F415 | g4/chapter_drafting.py:73 引用 SKILL.md:125，实际规则在 140（漂移 15 行） | docs | P2 | 见 Z4.a.md#F415 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F416 | docs/framework/decisions-schema.md 严重度枚举缺 medium（代码与示例均有） | docs | M | 见 Z4.a.md#F416 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F417 | 覆盖率缺口处置汇总（对应 d1-06 本区 415 行） | — | — | 见 Z4.a.md#F417 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F418 | g0_config_coherence 的 threshold_mismatch / floor_too_low 检测在真实调用路径永不触发 | error | P2 | 见 Z4.a.md#F418 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F101 | safe_write 写入后目标文件权限一律 0600，仓库 0644 工件已被改写 | error | P2 | 见 Z1.a.md#F101 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F102 | error_guidance 6 条 doc_url 全指向不存在的文档路径/锚点；2 条 action 指向不存在的脚本 | error | P2 | 见 Z1.a.md#F102 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F103 | exceptions.py 22 类中 17 类在 src/ 无 raise 站点；error_guidance/recovery 目录引用的全部 6 类均不会被真实错误命中 | error | P2 | 见 Z1.a.md#F103 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F104 | scoring.py `--kill-switch` 无 scores.json 的死分支必然 REJECT，永远到不了 0 分 | error | P2 | 见 Z1.a.md#F104 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F105 | phase_runner main() 不强制 --project-dir，缺失时把字符串 "None" 传给 G5；assert 守卫在 python -O 下失效 | error | P2 | 见 Z1.a.md#F105 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F106 | scoring.py G3 gate 输出解析异常被 `except Exception: pass` 静默吞掉，无日志，评分继续 | error | P2 | 见 Z1.a.md#F106 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F107 | G_TRANSITION/G_DISPATCH/G_RECONCILE 未接入 phase_runner 状态机，仅 CLI 手动入口 + 各自单测 | optimization | P2 | 见 Z1.a.md#F107 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F108 | safe_write 两处并发缺陷：mkstemp 在锁获取后、try 块外 → mkstemp 失败锁泄漏；stale-takeover unlink 后 O_EXCL 竞态 FileExistsError 未捕获 | error | P2 | 见 Z1.a.md#F108 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F109 | sync_contracts.verify_bijection 用 assert 做一致性守卫，python -O 下整函数失效 | optimization | P2 | 见 Z1.a.md#F109 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F112 | RoundPaths.repo() 无任何调用方（死代码） | optimization | P2 | 见 Z1.a.md#F112 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F113 | phase_runner cmd_pre_skill 的 ContractError 静默吞错：契约损坏时无日志降级为空 reads/writes | error | P2 | 见 Z1.a.md#F113 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F612 | 3 层干预把 severity 阶梯全部门控在 `is_drift`：绝对阈值（>30/>50/>100）在 baseline 被污染时永不可达 | error | P1 | 见 Z6.review.md#F612 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F613 | compute_stats 破折号/省略号桶同样重复字符双计（F604 同根、不同桶，初审漏覆盖） | error | P2 | 见 Z6.review.md#F613 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F614 | update_genre_config 中途 ConfigError 留 audit-trail 幻影条目（config 未落盘但 trail 已追加） | error | P2 | 见 Z6.review.md#F614 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F615 | TraceWriter 对撕裂尾部 JSONDecodeError 裸崩溃（replay 自愈 vs writer 不自愈不对称） | error | P2 | 见 Z6.review.md#F615 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F616 | parser._parse_body 静默丢弃非 dict YAML 条目：权威记录视图缺行 → 潜在 drift 误报/漏报 | error | P2 | 见 Z6.review.md#F616 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F617 | linguistic_drift.py 两个告警函数无生产调用方：计划承诺的 >3σ second-tier 告警与内容循环检测未接线 | dead code | P2 | 见 Z6.review.md#F617 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F618 | compute_stats RHETORICAL 正则字典死代码（定义从未使用，且与 detect_rhetoric 实际实现重复且不一致） | dead code | P2 | 见 Z6.review.md#F618 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F619 | compute_stats CLI `--output` 缺参时 IndexError 裸崩溃 | error | P2 | 见 Z6.review.md#F619 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F419 | G1.2 / G2.4 对合法非对象 JSON 崩溃（jload ValueError 未捕获） | error | P2 | 见 Z4.review.md#F419 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F420 | G6 在 novel.json / genre-config.json 损坏时崩溃（无 try/except） | error | P2 | 见 Z4.review.md#F420 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F421 | G_RECONCILE / G_DISPATCH / G_TRANSITION 对非对象 progress.json 崩溃 | error | P2 | 见 Z4.review.md#F421 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F422 | cli.py G1 非 JSON 参数静默转空 → 零校验 PASS（丢失 gate 自身逗号拆分回退） | error | P2 | 见 Z4.review.md#F422 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F423 | G0.7 引用已迁移的 tests/scoring.py → 每次带 seed 的 G0 恒 WARN | error | P2 | 见 Z4.review.md#F423 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F424 | g4_chapter_drafting 用遗留目录名 "skill-output" 找 genre-config → 真实布局下疲劳词表恒用默认 | error | P2 | 见 Z4.review.md#F424 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F425 | G7.6 依赖遗留 skill-output → 真实布局恒 SKIP（pending truth 检测失效） | error | P2 | 见 Z4.review.md#F425 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F426 | g4_genre_config 未用 resolve_input_path → 相对路径+无 rd 静默 CWD 回退 | error | P2 | 见 Z4.review.md#F426 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F427 | g4_chapter_revision 未解析路径（raw Path(fp)）→ rd+相对路径误报 invalid_json | error | P2 | 见 Z4.review.md#F427 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F428 | G3.2 阈值分叉：total_score 直读路径用 acceptance.t1(94)，rubric/维度回退路径硬编码 90 | error | P2 | 见 Z4.review.md#F428 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F429 | G1.4 在 gate 内写 .bak（AGENTS.md 纯验证契约偏离） | contract | P2 | 见 Z4.review.md#F429 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F430 | g4_foreshadowing_track G4.ft.changes 判定过松：正文出现"操作"一词即 PASS | error | P2 | 见 Z4.review.md#F430 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F324 | 生产 volume_map 中文格式与全部解析器不匹配：卷边界系统、closure 转换、卷上下文、计划骨架全线静默失效 | error | **P0** | 见 Z3.review.md#F324 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F325 | step 16 revision 双重门控矛盾：`_any_audit_has_findings` 扫描旧式审计文件名，BLOCKING 路由后 revision 仍被跳过（审计 BLOCKING 永不修复） | error | P1 | 见 Z3.review.md#F325 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F326 | 并行 post-draft 违反 write_safety WRITE_SHARED 串行不变量：lifecycle 与 state-settling 并发写 truth/pending_hooks.md（lost-update 竞态） | error | P1 | 见 Z3.review.md#F326 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F327 | §6.3 决策树未接线：decide_revision 无生产调用；route_chapter_revision 忽略 blocking；resonance floor 仅 log 不决策 | error | P2 | 见 Z3.review.md#F327 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F328 | CONDITIONAL_STEPS 从未被迭代（intent-management/drift-guidance/snapshot-manage 每章门控死代码）+ 自适应触发死簇 | optimization | P2 | 见 Z3.review.md#F328 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F329 | shenbi-review-sensitivity 每章双发（core 波 + genre 波同一 skill，写同一文件） | optimization | P2 | 见 Z3.review.md#F329 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F330 | cmd_resume 忽略 `_verify_truth_integrity` 返回值——"fail fast"文档声称未兑现 | error | P2 | 见 Z3.review.md#F330 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F331 | 并行 post-draft 的 G4 失败只 log 不重试/不升级（与串行语义不一致），lifecycle G4 失败输出被静默接受 | error | P2 | 见 Z3.review.md#F331 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F332 | state.token_usage 不进 to_dict/from_dict——token 汇总跨进程/跨 save 丢失 | error | P2 | 见 Z3.review.md#F332 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F333 | genesis G4 auto 模式开关语义错位（per_chapter_review_enabled 兼任 genesis 严格度开关）+ 章数口径不一致 | error | P2 | 见 Z3.review.md#F333 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F334 | 初审报告编号空洞：声称 23 findings，实际编号仅 22 条（F320/F321 缺失） | error | M | 见 Z3.review.md#F334 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F114 | phase_runner.run_gate 不捕获 subprocess.TimeoutExpired：60s 门超时 → 状态机 traceback 崩溃而非 FAIL 降级 | error | P2 | 见 Z1.review.md#F114 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F115 | scoring 维度过滤对 38/82 实际 rubric 静默 no-op：worldbuilding 等 4 技能 bug-hunt/clean 评分含 N/A 豁免维度 | error | P1 | 见 Z1.review.md#F115 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F116 | phase_runner cmd_post_skill 对 G2 FAIL 不阻断（仅记录），与 dispatcher/executor G2 FAIL→return 1 及 command-to-give "G2 失败 = 输出不合格" 冲突 | error | P2 | 见 Z1.review.md#F116 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F117 | sync_contracts.load_all_contracts 静默跳过 ContractError 技能 → expected_outputs/DAG/index 静默缺失，verify_bijection 同源盲区无法发现 | error | P2 | 见 Z1.review.md#F117 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F118 | scoring `--phase` 参数被解析但从未使用（死参数）；`--tier` 仅 T1 分支有实际逻辑 | optimization | P2 | 见 Z1.review.md#F118 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F119 | safe_write stale-takeover 固定 1 秒退避后无条件 unlink，可破坏活跃锁互斥；flock 失败路径 fd 泄漏 | error | P2 | 见 Z1.review.md#F119 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F120 | scoring check_gate_markers 的 G4/G6 标记名用 test_type 后缀，gates/cli.py 只写 "-generative" 标记（G4 bug-hunt/clean 分支不写标记）→ 非 generative 评分 + --round-dir 必误报 MARKER_MISSING | error | P2 | 见 Z1.review.md#F120 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F121 | phase_runner cmd_post_skill rglob 回退 `[:20]` 静默截断 + 不过滤非输出 .md | error | P2 | 见 Z1.review.md#F121 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F122 | phase_runner cmd_pre_score 不追加 step，其余 5 个命令均记录 → phase-state 审计历史不完整 | error | P2 | 见 Z1.review.md#F122 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
| F221 | GenreConfig 缺 tropeInventory 字段且未编码 SKILL.md 规则 1「顶层字段数=8」；SKILL.md/fixture/OWNERSHIP 四源冲突 | 漏报（校验洞+文档漂移） | P2 | 见 Z2.review.md#F221 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F222 | SHENBI_G1_SKIP_READS 三处实现/消费语义分叉（executor/g1/dispatch_helper），executor 侧零测试 | 漏报（F211 增补） | P2 | 见 Z2.review.md#F222 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F223 | codex.py 协议边界 JSON 处理无防护：shenbi-score stdout 双解析 + final_score 缺省静默 0 + 损坏 progress.json 裸 JSONDecodeError | 漏报 | P2 | 见 Z2.review.md#F223 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F224 | G3.3「output files passed G2」全仓无生产者 → 永久 SKIP；codex.py _record_completion 写 progress["skills"][skill][test_type]={score,status} 无 output_files 键 | 漏报（门静默空转） | P2 | 见 Z2.review.md#F224 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F225 | 独立 dispatcher（codex 模式）不消费 contract read_fields：Layer B 字段过滤仅 pipeline 生效 | 漏报 | P2 | 见 Z2.review.md#F225 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F226 | cli.py usage 声明 prompt 可选，codex 模式硬要求非空 → 缺参时裸 SubAgentProtocolError | 漏报 | M | 见 Z2.review.md#F226 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
