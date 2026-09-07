# 承接清单 — 未关闭 verified/open 条目（全 severity，spec #49 R2）

D1-02 P2 verified pytest addopts 全局 `--cov` 使 `--collect-only` 触发 cov 插件：输出 16.08% 假 FAIL 报告并覆写 tests/coverage/
D1-03 P2 verified G2.12 对文件清单输入报 WARN "may be truncated"（Z8.files 2047 字节清单被截断校验？）
F0-03 P2 verified gate 文档漂移：overview.md:55 "八道门"、gates.md:3 "8 validation gates"、README "8 道" vs CLI 实际 11 gate（G0-G7+G_TRANSITION+G_DISPATCH+G_RECONCILE），活跃文档 0 引用额外 gate
F0-04 M verified 归档计数漂移：INDEX.md:4 "已归档 99"、:80 "97 个"，实际 specs/archive/ 91 项
F0-05 P2 verified command-to-give.md:48 引用已删除脚本 tests/dispatch-subagent.sh（0f68102 PR-22 删除 shim），执行者照做会失败
F0-06 P2 verified python 版本三元不一致：requires-python>=3.11 vs mypy python_version=3.12 vs basedpyright pythonVersion=3.11
F0-07 P2 verified SECURITY.md:20-21 声称 pip-audit "runs on every PR and weekly"，security.yml 无 schedule、nightly.yml 无 pip-audit job
F0-08 M verified coverage 注释漂移：pyproject:447-451 声称 >=90% line / >=80% branch、"89 (not 90)"，实际 fail_under=85
F502 P2 verified FileChange.status Literal 定义在 contracts/ownership.py:22 而非 enums.py（enums.py:1 明示"所有 Literal 必须从此处 import"）
F503 P2 verified write_audit._declared_patterns 宽 except Exception 吞错：derive_output_files 意外异常 → declared=[] → 未声明写入假阳性 GATE_FAIL
F504 P2 verified ledger.record() 对 usage 值裸 int() 强转，非 int 可强转值 ValueError 崩 hot path（违反"must never crash the pipeline"）
F506 P2 verified report._try_avg_g3_score 把任意 **/*score*.json 的任意顶层 0-100 数值当 G3 分求平均，CPQ 指标名实不符
F509 M verified compute_file_change 对 pre==post（含 None,None）报 status="modified" 幻影条目
F510 M verified report.main() 尾部 return 2 不可达（subparsers required 仅 report）；print() 在 CLI 入口（AGENTS.md No print 边缘）
F511 M verified 归档 spec 文档行号漂移（write_audit.py:31 lazy import 实际在 :22 等，历史态描述）
F603 P2 verified records drift 只检 md→YAML 方向：YAML 新增 hook 未同步派生表不报 drift
F607 P2 verified 同包双 baseline 路径分裂：baseline.py 写 style/ vs linguistic_drift.py 读 context/；术语表也分裂
F609 P2 verified replay 撕裂行/签名断链静默截断且无日志（改写文件不可追踪）
F610 P2 verified recall_overdue_hooks 对缺 id hook 直接 KeyError，单条坏记录使整批崩溃
F202 P2 verified contracts/registry.py REGISTRY + load_skill_contract 生产无消费者（仅测试用）
F203 P2 verified schemas/deps.py DepsDoc + phase_of 未接线；sync_contracts 仍用 json.loads 解析 deps.json
F204 P2 verified schemas/novel.py NovelConfig 声称 g6 consumer，g6 未 import
F205 P2 verified schemas/scores.py ScoreReport 声称 g5 consumer，无生产 import
F206 P2 verified schemas/state.py ProgressDoc/SummaryDoc 从未被加载验证（C3 修复无生效面）
F207 P2 verified skills/_scoring_base.py ScoreReport + score_arc/stratum/volume 评分契约 dead-wire（M3 修复未接线）
F208 P2 verified enums.py Severity/Verdict 无生产消费者；严重性字面量仍散落 4 处裸字符串
F209 P2 verified base.py GateOutcome.status 用裸 Literal 复制 status.py GateStatus 词表
F210 P2 verified hooks.py 的 SKILL.md 行号引用漂移（超出 ±5）
F211 P2 verified executor.py SHENBI_G1_SKIP_READS 环境特性零测试覆盖
F212 P2 verified executor.py run_g1/run_g2 不检查 returncode，stdout 非 JSON 时裸 JSONDecodeError
F213 P2 verified dispatcher/modes/codex.py 单次 codex exec、无重试/429/finish_reason/并行上限（仅 pipeline 路径有）
F215 P2 verified codex.py 用 `\{[^{}]*\}` 提取首个"无嵌套花括号"JSON 片段
F217 P2 verified pacing_design.py CONSTELLATION 区间三处不一致（docstring 20-30 / 代码 15-35 / SKILL.md 15-25）
F219 P2 verified executor.py 对 ContractError 静默 fail-open：registry 缺失 → 空 inputs → G1 空集真空 PASS → 无上下文派发
F220 P2 verified ownership.py OWNERSHIP 矩阵仅 6 条参考条目（docstring 自述「支柱一续」），其余技能落 file-level 检查
F305 P2 verified 审计严重度裸子串检测（"BLOCKING"/"FAIL"）产生误报
F306 P2 verified audit_context_cache 读错 volume_map 路径 + 章节号子串匹配缺陷
F307 P2 verified hook_planting 模块生产死线：plant_hooks_from_plan 只在不可达分支被调用，确定性伏笔种植从未运行
F308 P2 verified compact_pipeline_state / _archive_chapter_state 死代码（Plan 17 10d 未勾选 TODO 从未接线）
F309 P2 verified _validate_state_consistency / _heal_current_step 死代码（注释声称 cli.py resume 调用，实际无调用方）
F310 P2 verified volume_align.py 死模块（与 chapter_loop._check_volume_map_alignment 重复，无生产调用方）
F311 P2 verified scr_extractor 缓存永不失效：revision 改写章节后 SCR 持续陈旧
F314 P2 verified bridge 激活窗口包含已激活桥（chapter >= activation - 3 未排除 past-activation）
F315 P2 verified _merge_step_result / _apply_step_outputs 为 no-op 死线（"单写者合并"实际什么都不做）
F316 P2 verified revision_router.collect_audit_issues 读原始 glob 无聚合去重（F10 先例未修复）
F317 P2 verified error_handler 常量与配置耦合：MAX_DISPATCH_RETRIES/MAX_AUDIT_RETRIES 死常量；dispatch 重试上限绑定 max_revision_retries（配置放大隐患）
F318 M verified 文档/注释漂移（M 级合并条目）
F319 P2 verified cmd_review MODIFY 对 PER_CHAPTER 检查点无回滚语义，feedback 泄漏到下一章
F400 P2 verified G2.12 无 file_type 守卫 → JSON/清单文件误报"截断"WARN（D1-03 根因核实）
F403 P2 verified CLI G4 无 round_dir 时 ValueError 崩溃，破坏 JSON/退出码契约
F405 P2 verified G4_CHECKER_SKILLS 注册表过期：漏 9 个专用 checker
F406 P2 verified G0.3/G0.6/G7.5 使用遗留目录名 skill-output（真实布局 novel-output / project-output）
F407 P2 verified G0 无 seed 时早退 → 全部环境检查被跳过，gate 空转 PASS
F409 P2 verified G1 空输入 → PASS（G1.0 SKIP 空转）
F410 M verified cli.py SHORT_MAP 缺 11 个技能的 shorthand
F411 M verified g0.py G0.4 missing_dirs 死代码 + G0.12 注释 "20 skills" 过期
F412 M verified g3_independence.py docstring 行引用过期
F413 M verified decisions_validator.py:175 注释 "shared.py:113" 错位
F414 M verified g4_chapter_revision 返回 "HARD_FAIL" 状态值不在 GateStatus 词表
F415 P2 verified g4/chapter_drafting.py:73 引用 SKILL.md:125，实际规则在 140（漂移 15 行）
F416 M verified docs/framework/decisions-schema.md 严重度枚举缺 medium（代码与示例均有）
F417 — verified 覆盖率缺口处置汇总（对应 d1-06 本区 415 行）
F418 P2 verified g0_config_coherence 的 threshold_mismatch / floor_too_low 检测在真实调用路径永不触发
F101 P2 verified safe_write 写入后目标文件权限一律 0600，仓库 0644 工件已被改写
F102 P2 verified error_guidance 6 条 doc_url 全指向不存在的文档路径/锚点；2 条 action 指向不存在的脚本
F103 P2 verified exceptions.py 22 类中 17 类在 src/ 无 raise 站点；error_guidance/recovery 目录引用的全部 6 类均不会被真实错误命中
F104 P2 verified scoring.py `--kill-switch` 无 scores.json 的死分支必然 REJECT，永远到不了 0 分
F105 P2 verified phase_runner main() 不强制 --project-dir，缺失时把字符串 "None" 传给 G5；assert 守卫在 python -O 下失效
F106 P2 verified scoring.py G3 gate 输出解析异常被 `except Exception: pass` 静默吞掉，无日志，评分继续
F107 P2 verified G_TRANSITION/G_DISPATCH/G_RECONCILE 未接入 phase_runner 状态机，仅 CLI 手动入口 + 各自单测
F108 P2 verified safe_write 两处并发缺陷：mkstemp 在锁获取后、try 块外 → mkstemp 失败锁泄漏；stale-takeover unlink 后 O_EXCL 竞态 FileExistsError 未捕获
F109 P2 verified sync_contracts.verify_bijection 用 assert 做一致性守卫，python -O 下整函数失效
F110 M verified exceptions.py RegistryStaleError 消息 "1 source files changed" 语法错误（单数名词 + 复数 files，未区分单复数）；test_exceptions.py:64 断言同款文案
F111 M verified __init__.py docstring "forwarder until PR-19/PR-20" 过期：gates/cli.py、dispatcher/cli.py、executor.py 均为真实实现（PR-19/20 早已落地）
F112 P2 verified RoundPaths.repo() 无任何调用方（死代码）
F113 P2 verified phase_runner cmd_pre_skill 的 ContractError 静默吞错：契约损坏时无日志降级为空 reads/writes
F615 P2 verified TraceWriter 对撕裂尾部 JSONDecodeError 裸崩溃（replay 自愈 vs writer 不自愈不对称）
F616 P2 verified parser._parse_body 静默丢弃非 dict YAML 条目：权威记录视图缺行 → 潜在 drift 误报/漏报
F617 P2 verified linguistic_drift.py 两个告警函数无生产调用方：计划承诺的 >3σ second-tier 告警与内容循环检测未接线
F618 P2 verified compute_stats RHETORICAL 正则字典死代码（定义从未使用，且与 detect_rhetoric 实际实现重复且不一致）
F619 P2 verified compute_stats CLI `--output` 缺参时 IndexError 裸崩溃
F422 P2 verified cli.py G1 非 JSON 参数静默转空 → 零校验 PASS（丢失 gate 自身逗号拆分回退）
F423 P2 verified G0.7 引用已迁移的 tests/scoring.py → 每次带 seed 的 G0 恒 WARN
F426 P2 verified g4_genre_config 未用 resolve_input_path → 相对路径+无 rd 静默 CWD 回退
F427 P2 verified g4_chapter_revision 未解析路径（raw Path(fp)）→ rd+相对路径误报 invalid_json
F428 P2 verified G3.2 阈值分叉：total_score 直读路径用 acceptance.t1(94)，rubric/维度回退路径硬编码 90
F429 P2 verified G1.4 在 gate 内写 .bak（AGENTS.md 纯验证契约偏离）
F430 P2 verified g4_foreshadowing_track G4.ft.changes 判定过松：正文出现"操作"一词即 PASS
F327 P2 verified §6.3 决策树未接线：decide_revision 无生产调用；route_chapter_revision 忽略 blocking；resonance floor 仅 log 不决策
F328 P2 verified CONDITIONAL_STEPS 从未被迭代（intent-management/drift-guidance/snapshot-manage 每章门控死代码）+ 自适应触发死簇
F329 P2 verified shenbi-review-sensitivity 每章双发（core 波 + genre 波同一 skill，写同一文件）
F330 P2 verified cmd_resume 忽略 `_verify_truth_integrity` 返回值——"fail fast"文档声称未兑现
F331 P2 verified 并行 post-draft 的 G4 失败只 log 不重试/不升级（与串行语义不一致），lifecycle G4 失败输出被静默接受
F332 P2 verified state.token_usage 不进 to_dict/from_dict——token 汇总跨进程/跨 save 丢失
F333 P2 verified genesis G4 auto 模式开关语义错位（per_chapter_review_enabled 兼任 genesis 严格度开关）+ 章数口径不一致
F334 M verified 初审报告编号空洞：声称 23 findings，实际编号仅 22 条（F320/F321 缺失）
F114 P2 verified phase_runner.run_gate 不捕获 subprocess.TimeoutExpired：60s 门超时 → 状态机 traceback 崩溃而非 FAIL 降级
F116 P2 verified phase_runner cmd_post_skill 对 G2 FAIL 不阻断（仅记录），与 dispatcher/executor G2 FAIL→return 1 及 command-to-give "G2 失败 = 输出不合格" 冲突
F117 P2 verified sync_contracts.load_all_contracts 静默跳过 ContractError 技能 → expected_outputs/DAG/index 静默缺失，verify_bijection 同源盲区无法发现
F118 P2 verified scoring `--phase` 参数被解析但从未使用（死参数）；`--tier` 仅 T1 分支有实际逻辑
F119 P2 verified safe_write stale-takeover 固定 1 秒退避后无条件 unlink，可破坏活跃锁互斥；flock 失败路径 fd 泄漏
F120 P2 verified scoring check_gate_markers 的 G4/G6 标记名用 test_type 后缀，gates/cli.py 只写 "-generative" 标记（G4 bug-hunt/clean 分支不写标记）→ 非 generative 评分 + --round-dir 必误报 MARKER_MISSING
F121 P2 verified phase_runner cmd_post_skill rglob 回退 `[:20]` 静默截断 + 不过滤非输出 .md
F122 P2 verified phase_runner cmd_pre_score 不追加 step，其余 5 个命令均记录 → phase-state 审计历史不完整
F221 P2 verified GenreConfig 缺 tropeInventory 字段且未编码 SKILL.md 规则 1「顶层字段数=8」；SKILL.md/fixture/OWNERSHIP 四源冲突
F222 P2 verified SHENBI_G1_SKIP_READS 三处实现/消费语义分叉（executor/g1/dispatch_helper），executor 侧零测试
F223 P2 verified codex.py 协议边界 JSON 处理无防护：shenbi-score stdout 双解析 + final_score 缺省静默 0 + 损坏 progress.json 裸 JSONDecodeError
F224 P2 verified G3.3「output files passed G2」全仓无生产者 → 永久 SKIP；codex.py _record_completion 写 progress["skills"][skill][test_type]={score,status} 无 output_files 键
F225 P2 verified 独立 dispatcher（codex 模式）不消费 contract read_fields：Layer B 字段过滤仅 pipeline 生效
F226 M verified cli.py usage 声明 prompt 可选，codex 模式硬要求非空 → 缺参时裸 SubAgentProtocolError
F622 P2 verified recall_overdue_hooks 对 str 类型 last_reinforced/max_distance TypeError 崩溃（F610 之外的独立类型失败模式）
F623 P2 verified AI_MARKERS "不是…而是" 用单省略号字符字面量 → 真实文本"不是……而是"（双字符）恒不命中
F625 P2 verified versioning.migrate_to_current 缺迁移函数时 `_identity` 回退 → while 循环永不前进 → 无限循环挂死
F626 P2 verified check_linguistic_drift_trigger（第 4 漂移触发点）死导出：HARD/ESCALATE 从未接入 drift-guidance
F629 P2 verified revision_routing.verify_preservation 无生产调用方：§5.3 再生保留校验器实现+测试但未接线，保留保障仅靠 LLM prompt
F515 P2 verified `_matches_declared` 不匹配契约原生 glob 写模式（`truth/*.md`）→ 已声明写被误报"未声明写入"
F516 M verified 初审误判 snapshot.py:43-45 为"无 `*` 写入"死代码：契约实际存在 glob 写模式
F335 P2 verified audit_context_cache 用补零章节文件名（chapter-001.md），生产为不补零 → chapter_text 恒空
F336 P2 verified state.to_dict/from_dict 丢失 step_timings（F332 同根不同面）
F338 P2 verified 审计级联跳过（Spec 8 Fix 8）无数据源：并行波不写 per-skill audit_results → _should_skip_audit 恒 False
F339 P2 verified 并行波审计信号失真且无消费方：blocking_found 由 consolidate(stdout) 计算（API 路径恒 0）、audit_reports 记录不存在的 group-*.md、review-summary.md 恒报 0 问题
F342 P2 verified volume_snapshot_pending / add_audit_result / increment_retry / reset_retry 生产死代码
F431 P2 verified jload 的 ValueError（合法但非 dict 的 JSON）在 G1.6/G3.x/G5.1/G7.x/read_genre_config/gate_manifest 未捕获 → 多门崩溃（F419/F421 家族扩展）
F433 P2 verified g4_chapter_drafting 主角在场检查用坏掉的 project_root（skill-output 爬升）而非已传入的 project_dir → 生产布局恒用默认名 ["林烽","他"]，检查形同虚设或误报
F434 P2 verified g4_state_settling 参数 agent 名单用单字符子串匹配（"冷"/"光"）→ 真实 fixture 误报 FAIL
F435 P2 verified G0.12 exempt_skills 读取后从未使用 + 注释声称的 "no skill returns UNIMPLEMENTED" 校验未实现（G0.12 恒 PASS 空转）
F436 M verified G6.7 planted_chapters 死变量
F437 P2 verified G5.5 用 except Exception → WARN 吞掉 G4 重跑的一切异常（含 gate 崩溃）→ G4 回归检查 fail-open
F438 M verified chapter_drafting 转折词阈值 1/1000（≥5 兜底）vs SKILL.md 契约 1/3000（3 倍放宽，代码注释自认但 SKILL 未同步）
F439 P2 verified g4_style_polishing 字数比检查死路：其输入 .bak 只由 G1.4 为 BACKUP_SKILLS（truth updaters）创建，style-polishing 不在其中 → G4.sp.word_ratio 永不执行
F123 P2 verified capability_fs.CapabilityFS 无任何生产接线：支柱五"读 provenance 运行时兜底"仅测试消费，模块为生产死代码
F124 P2 verified phase_runner CLI 无位置参数校验：缺参 → IndexError traceback；flag 被解析为位置参数
F125 P2 verified command-to-give.md:48 引用不存在的 tests/dispatch-subagent.sh：PR-20 迁移后执行协议断链
F126 M verified scoring.py 批次评分 scored_by 误标 "interactive"：非交互文件评分且未传 --subagent 时审计元数据失真
F127 M verified status.py ScoringStatus.OK / ScoringStatus.UNIMPLEMENTED 死成员：单一定义词汇表中 2/5 成员无任何 emit/read 站点
F228 P2 verified derive_output_files/G2 不展开 writes/updates 中的 glob → 9 技能 G2.1 恒失败
F229 P2 verified derive_file_type 单一 file_type 批处理与异构输出不兼容：(a) chapter 型技能非散文输出误套章节规则；(b) decisions 型技能 .md 散文静默漏套 G2.6-2.10
F230 P2 verified fields.py `_filter_json` 不做规范化（裸 `k in fields`），与 `_filter_md` 的 canonical rule 不一致——复核轮"md 与 json 同构"断言为误
F231 P2 verified genre-config 消费侧引用 povMode/sensitivityFlags，但模型/fixture/SKILL.md 规则表/OWNERSHIP 全源无此键——review_checklist 恒空默认、review-group-character 字段过滤恒 escape hatch
F234 P2 verified 整文件删除 owned 文件零违规——check_write_ownership 忽略 FileChange.status
F630 P2 verified revision_router.DEFAULT_RESONANCE_FLOOR=50 与单源阈值 65 漂移（E11 缺陷类复活）
F632 P2 verified linguistic_drift severity 阶梯硬编码 30/50/100 与 thresholds.py 单源阈值重复且不一致风险（"single source of truth" 声明被违反）
F517 P2 verified `audit_writes` 将 pending_hooks 专属解析无差别应用于全部 watched .md：非 truth .md 含 `## 活跃伏笔` 表 → 假 drift GATE_FAIL；含 `## hooks` 节 → ValueError/YAMLError 崩审计链
F520 P2 verified tenacity 重试失败 attempt 的 token 消耗不记账：仅最终成功 attempt 的 usage 落账 → 429/5xx/timeout 重试成本被少计
F521 P2 verified `estimate_prompt_tokens` CJK 判定范围仅 0x4E00-0x9FFF：中文标点/全角/扩展 A 按 ASCII 4 chars/token 计 → 中文 prompt 系统性低估 token，上下文告警阈值提前量被侵蚀
F522 P2 verified resonance_trend.md 写侧（`_build_resonance_trend_row` 无 header 7 列行）与 `compute_drift.parse_trend`（要求 header 行含维度名）格式不兼容 → parse_trend 恒返回空，volume-decline 检测永不触发
F523 P2 verified `_diff_records` 对无 id 记录按 `str(None)` 键合并：id-less 记录的新增/删除在 record 级 diff 中静默掩盖
F346 P2 verified truth_index._HOOK_ID_RE 不匹配生产带连字符 hook id（MH-001/H-N01）→ master hooks 从 Route A 检索静默缺失
F347 P2 verified 生产 hook 数据格式与上下文"伏笔债务简报"解析全错位：简报恒"(无)"
F348 P2 verified SharedAuditContext 缓存注入与审计契约 reads 错位——缓存对预期目标近乎死线
F349 P2 verified MODIFY 派生的 truth re-dispatch 无重试预算/无升级：持续失败时每次 step 迭代重复重发
F350 M verified 每章无条件创建 chapter-N-pre-rev.md 备份（即使 route=no-revision 无 revision 发生）
F351 M verified API JSON 模式未传 response_format，依赖提示词合规 + 回退解析（非合规输出先失败一次再重试）
F352 M verified dispatch_skill 的 timeout 形参死代码（三条路径均用 _compute_dispatch_timeout）
F442 P2 verified g4_length_normalizing 未实现 SKILL.md 压缩双底线（≥25% 原始长度）→ 过度压缩静默通过
F443 P2 verified g1.check_fields_exist 死代码：仅测试引用，gate_G1 与生产均未接线（B.4 字段软检查未生效）
F445 M verified shared.unimplemented() 无调用方（死代码）
F639 P2 verified compute_drift CLI 对缺失趋势文件静默跳过并 exit 0（误判"无漂移"）；真实项目缺 arc_payoff/volume 趋势文件 → CLI 只跑半个检测；`--write-audit-drift` 向 drift-guidance 单一写者拥有的 audit_drift.md 追加无协调
F526 P2 verified `_changed_top_keys` 对 JSON 顶层类型变化（dict→list/str）返回空元组 → OWNERSHIP field 文件被整体替换为非 dict 时零违规
F528 P2 verified `record_audit_outcome` 账本写侧（mkdir/open/write）无 OSError 防御：写失败在 `dispatch_with_write_audit` 的 finally 中传播 → 审计结果丢失并掩盖 dispatch rc
F530 M verified `parse_resonance_scores` 的 `val > 0` 过滤丢弃合法 0 分（dead-wire 桥上下文，无现行生产影响）
F355 P2 verified 确定性策展层输出死线：context/chapter-N-curated.md 无任何 skill 读取（9 节分层编排生产无效）
F356 P2 verified curate_context P 分层渲染失效：章节 plan 与全部 route 条目落入 P7，P1/P3-P6 恒 "(未产出)"
F357 P2 verified SharedAuditContext 的 style_profile 以幽灵路径 truth/style_profile.md 注入（style 内容重复进入每个审计 prompt）
F358 P2 verified linguistic drift ESCALATE 被吞：DriftEscalationError 在 pipeline-linguistic-drift-check 的 except Exception 中仅 log；drift 指令文件无消费者
F359 P2 verified Route A 检索条目无实体内容（仅 "[category] id from file" 标签），entity 事实从不进入上下文
F360 P2 verified chapter_loop._maybe_rebuild_truth_index 只 build 不落盘（周期索引重建无效，日志误导）
F361 M verified _call_llm_streaming 的 early_stop_patterns 死参数（无调用方传值）
F363 M verified run_triggered_skills 中途失败后重试会重发已成功的触发步骤（无 per-skill 进度追踪）
F362 M verified cmd_backfill_context 使用 print() 违反框架约定（AGENTS.md：No print() in framework code）
F446 P2 verified count_transition_words 转折词计数双向偏离 SKILL 契约：然而→0、然后/显然→计入
F447 P2 verified G4.chapter-drafting 的 transition/fatigue 计数把 PRE/POST 元区块计入（与 G4.meta、word_count_md 剥离行为不一致）→ 真实章节近阈值/越阈值误报
F448 P2 verified check_chapter_title 只识别阿拉伯数字章节号，中文数字"第一章"漏检（SKILL.md 明示禁止）
F449 P2 verified G_RECONCILE 状态字面量 "DONE" 与全部生产 progress 形状不匹配 → GR.1 恒死；GR.2 在 F401 修复（剥离 -scores）后仍恒 FAIL
F450 P2 verified G6.7 hook 解析器与真实 pending_hooks.md 格式不匹配 → 真实项目恒 low_hook_density:0.0 FAIL，生命周期/超距检查死路
F451 P2 verified g6_checks check_pacing / check_style_consistency 元区块剥离正则缺 `# ` 与 `<!--META` 边界 → 正文被吞 → 章节误分类/风格指标失真
F452 P2 verified G4.cd.chapter_end_hook 评估的是文件末尾 POST_WRITE_SELF_CHECK 元文本而非叙事结尾
F453 P2 verified G2.7 重要章豁免（volume_map/plan 标注 → ceiling 10000）在全部自动化调用路径死路：project_dir 未接线 → >4500 字重要章恒误报 FAIL
F454 P2 verified G_TRANSITION GT.1/GT.3 对生产 progress 形状语义漂移：round-exec 形状恒真空 PASS、materialize 形状恒 FAIL
F455 M verified g4_generic_generative docstring 声称校验 frontmatter，代码未实现
F535 P2 verified `parse_markdown_table` 表头缺 id 列 → md_rows 恒空 → drift 检测静默放行（畸形派生表 = "一致"）
F536 P2 verified "未声明写入"检测在真实接线下不可达：快照面=声明写入面，技能写声明外文件（越权的基本形态）永不进入审计；test_write_audit.py:79-87 手工构造 post dict 掩盖该盲区
F134 P2 verified scoring validate_scores 对空 dimensions rubric 静默放行 → 不可解析 rubric 产出静默 0 分（FAIL）而非 REJECT
F135 P2 verified scoring validate_scores 对 NaN 分数放行：`{"1": NaN}` 通过 0-100 校验 → final_score NaN 静默
F136 M verified status.py CommandResult TypedDict 全仓无使用："Emit sites use enum members through typed result structures" 的静态类型保证未落实
F137 P2 verified phase_runner cmd_post_skill 经 derive_output_files/derive_file_type 静默吞 ContractError：契约损坏 → G2 SKIP + G4 空文件 vacuous PASS → 相位无校验推进、无日志
F138 M verified error_guidance.py / recovery.py 的 `log = get_logger(__name__)` 从未使用（死代码）
F139 M verified __init__.py docstring 子模块清单仅列 6/12：缺 capability_fs/cli_utils/error_guidance/paths/recovery/safe_write/status/sync_contracts，与初审"与实际结构一致"断言不符
F641 P2 verified records `_values_equal` 布尔比较孔：YAML 布尔 `true` 与 md 表 `"true"` 比较 → 假 drift（block ship）
F365 P2 verified STATE_SETTLE MODIFY 重跑不重设 checkpoint：重跑结果悬空不提交、重审门被静默跳过（`_advance` 的 STATE_SETTLE 分支本身即死代码）
F366 P2 verified 5 个 PipelineConfig 死旋钮零消费者：genesis_review_required / volume_boundary_review_required / style_learning_interval / context_budget_override / snapshot_retention_chapters
F367 M verified step 2 chapter-planning 的 context assembly 恒读不存在的当章 plan → 每章恒失败走 minimal fallback + 一次无效 curation
F368 M verified hook_planting._append_to_pending_hooks 以 frontmatter-only 覆写 pending_hooks.md——接线即破坏生产 body 表格格式
F369 M verified cmd_init 对缺失 seed 文件未捕获 FileNotFoundError → 裸 traceback 而非 emit_json ERROR
F370 M verified API 路径解析出的 SkillOutput.decisions 字段从不落盘（JSON 模式 decisions 侧车静默丢弃）
F236 P2 verified audit/write_audit.py `_matches_declared` 不 fnmatch 声明为 glob 的写入（`truth/*.md` 等 9 技能）→ glob 写入恒判"未声明写入"
F237 P2 verified compute_file_change 对 added JSON 文件返回空 changed_top_keys → field 级 OWNERSHIP 键集校验对新建文件整体旁路
F538 P2 verified `snapshot_tree` 对非 UTF-8 watched 文件抛 UnicodeDecodeError 崩审计链：pre-snapshot（executor.py:244）崩 → dispatch 未启动即中止；post-snapshot（:264）崩 → finally 异常替换 dispatch 结果
F140 P1 verified `shenbi-score` CLI 成功路径恒 exit 1：main() 返回 dict → 控制台脚本 `sys.exit(dict)` → 违反 command-to-give.md 文档化退出码契约（0=成功），且 codex 模式自动评分路径永远"失败"
F141 P2 verified scoring validate_scores 对 bool 分数放行：scores.json 中 `true`/`false` 静默按 1/0 计分（isinstance 把 bool 当 int）
F142 M verified scoring 过滤后评分在文档化 bug-hunt/clean 路径恒发 `weight_mismatch` 误报 warning；filter docstring 宣称 "renormalize weights" 但函数内未实现（重归一实际隐式发生在 compute_score），且输出 dimensions 权重和不等于 100
F143 M verified phase_runner cmd_post_skill 回退注释声称 "G2's decisions branch would json.loads() markdown → crash"，与 g2.py 实际行为（decisions 分支对非 .json 直接 continue，不会解析 markdown）不符
F372 P2 verified `_style_profile_is_stale` 章节计数被 pre-revision 备份文件污染：`chapter-*.md` glob 计入 `chapter-N-pre-rev.md` → style-learning 自愈触发提前/误触发
F238 P2 verified audit_writes 对 malformed `## hooks` YAML 裸抛 ScannerError/ValueError → dispatcher 审计链崩溃，"崩溃仍审计"保证失效
F239 P2 verified derive_file_type truth/decisions 分类 glob 盲区：精确字符串交集，`truth/*.md`/`snapshots/chapter-NNN/*` 写者被误归 "chapter"
F240 P2 verified extract_chapter 仅识别英文 "chapter N"：中文 prompt（框架主语言）→ chapter=None → N/NNN 输出全部丢弃 → standalone G2 整体静默跳过
F241 P2 verified genre_config 规则 1 approval.decision 缺失/空值时静默 PASS；禁用 非 list / 替换建议 非 dict 时对应规则静默跳过
F242 P2 verified OWNERSHIP 矩阵 2/6 条目指向 DEPRECATED 技能（plant/track），生产写者 foreshadowing-lifecycle 无条目 → pending_hooks.md 记录级写保护对生产路径空转
F243 P2 verified 独立 dispatcher 无独立评分者：PR-20 把原 shell 的"独立评分 subagent 派发（G3.4 wrapper）"改为"生成器自评"
F244 P2 verified G1.4 的 .bak 由 INPUTS 创建、G2.11 对 truth OUTPUTS diff → 输出非输入的 truth-updater G2.11 永不触发
F144 P2 verified phase_runner `load_state` 对 phase-state 文件无形状/类型校验：损坏或非 dict 的状态文件 → 未捕获 JSONDecodeError/KeyError/TypeError 裸 traceback，与其余命令的结构化错误信封不一致
F456 P2 verified G6 章节目录按字典序排序（chapter-10 < chapter-2）→ G6.4 时间线回归漏报、future_knowledge 语义错乱、G6.5 连续分类与 G6.8/G6.10 采样错章
F457 P2 verified G6.5/G6.10 对话占比用「对话段数 / 总字数」而非「对话字数 / 总字数」→ dialogue 分类死路、对白范围判定失真
F461 P2 verified g4_chapter_drafting protagonist_presence / scene_concreteness 未剥离 PRE/POST 元区块（F447 家族剩余消费方）→ 边缘章节主角在场/视觉场景误判
F374 P2 verified write_safety 将 shenbi-review-resonance 分类为 READ_ONLY_AUDIT，但其契约 updates 写 truth/audit_drift.md + truth/resonance_trend.md → 并行审计波在无串行保护下并发写 truth 文件（模块自述的 WRITE_SHARED 串行不变量被违反）
F375 P2 verified API 路径多文件输出部分缺失仍返回成功（missing 仅 log.error，DispatchResult 恒 True）→ state-settling 等 6 文件技能的残缺输出被静默接受
F376 M verified `pipeline-truth-embed update` 无 `--text` 时静默报 OK（不嵌入任何内容）
F377 M verified check_audit_completeness 的 VERDICT_MARKERS 含通用词 "通过"，no_verdict 检查几乎永不触发
F378 P2 verified context/volume-N-complete.json 全仓无写入方 → `_check_volume_completion` 恒 False → 软失败升级链恒触发 volume_objective_missed 信号；`last_trigger_failure` 写后无消费者
F145 M verified phase_runner `load_deps()` 无任何错误处理：deps.json 损坏/缺失 → cmd_pre_score / cmd_finalize 裸 traceback，而同一文件的两个兄弟消费者（g5.py / scoring.py）均有守卫
F146 M verified scoring.check_gate_markers t2 分支对 deps.json 仅 exists() 守卫：文件存在但损坏 → 未捕获 JSONDecodeError 裸 traceback（同族 F145 只覆盖了 phase_runner.load_deps，scoring 侧损坏场景漏掉）
F147 M verified sync_contracts.main() 的 deps.json 读取（:195）与 load_registry（:165）均无守卫：损坏/缺失 → 裸 traceback（本文件前七轮仅 F109/F117/F130 覆盖，加载边界未覆盖）
F381 P2 verified state_heal._heal_revision_counts 把未修订章节的 revision_count 抬到 ≥1：`_ensure_revision_decisions_exists` 对 NO_REVISION 路由也写回退文件，heal 误将其当作"发生过修订"
F382 P2 verified progress.json 物化层半接线：pipeline 从不写 trace 事件（safe_write 未传 round_dir/trace_action），每 5 步 materialize 把 progress.json 重建为"全 pending"视图，resume 时 staleness 检查空转
F383 P2 verified IDE 派发路径输出无 `### FILE:` 标记时，整段 stdout 被写入每一个输出文件（codex 已安装 → 当前环境 IDE 路径激活下的潜伏数据损坏点）
F248 P2 verified pacing_design.from_markdown 解析失真：chapter_sequence 恒空使「不连续 3 章同类型」规则在 g4 门路径死代码；scene_types 固定词表子串扫描致 g4 误拒/虚增
F249 P2 verified executor.run_g2 把 PROJECT_DIR（shenbi 仓库根）当 G2 project_dir 传入 → _is_important_chapter 恒 False → 重要章 4500-10000 字被 G2.7 误拒
F148 P2 verified phase_runner cmd_post_skill 对契约声明但磁盘缺失/为空的输出静默丢弃（无日志）：技能未产出任何文件时 G2 SKIP + G4 空文件 vacuous PASS + PASS marker → 相位以 OK 推进
F150 P2 verified phase_runner run_gate("G2") 不传 project_dir → G2.7 重要章节 ceiling 判定在相位机路径恒失效（executor 传 REPO_ROOT 亦错）
F151 M verified scoring.py:419 scores.json 非数字键静默丢弃且无 WARNING
F152 M verified load_rubric kill-switch 解析漏 "→ detection dimension = 0" 类条目 → 10+ 份 rubric kill_switches 元数据不完整
F153 M verified sync_contracts.render_body_view 的 skill 参数从未使用（死参数）
F644 P2 verified compute_ngrams 未剔除标点 → n-gram 风格指纹被标点对/标点串主导（真实 chapter-1 top bigram 为 `。他` 与 `——`）
F646 P2 verified AUDIT_SAFETY_MATRIX 维度集与真实 genre-config auditDimensions 漂移（6 vs 10 维）：motivation/foreshadowing/sensitivity/worldRules 可无 rationale 禁用且 G0 无信号
F462 P2 verified G3.2 评分提取键与 shenbi-score 规范输出形状不匹配（total_score/score vs final_score/dimensions）→ 规范形状报告 score=0 恒 FAIL；F428 的"直读 94 阈值"路径在生产形状下不可达
F463 P2 verified G3.2 全量扫描 t1-reports 不按 skill_name 过滤 + rubric 加权回退用 gate 技能 rubric 评估其它技能报告（跨技能互扰）
F464 P2 verified t1-reports 生产命名 `*-scores-subagent.json`（codex.py）与 gate 消费模式 `*-scores.json`/find_report 不匹配 → G5.1 兜底恒 no_report FAIL、G0.10 计数恒 0（F432 第二根因）、GR.1/GR.2 在 F401 修复后仍失败（-subagent 后缀）、G7.14/15 空转
F466 P2 verified G4.cd.content_uniqueness 在 G6.3 调用形状（rd=项目目录，g6.py:86-93）下静默跳过 —— Path(rd)/"project-output"/"chapters" 不存在 → T3 逐章 G4 中内容唯一性检查不执行且无 SKIP 记录
F467 P2 verified chapter_planning 节号分隔符不一致：sections 计数接受 `## 5、`/`## 5：`，s5/s7 提取正则仅认英文句点 `## 5\.` → 合法格式下 s5_choice 误 WARN、s7_hook_ops 误 FAIL
F250 P2 verified 独立 dispatcher codex 模式不注入技能定义：codex agent 仅有裸 prompt（无 SKILL.md/契约/rubric），无法产出契约一致输出
F384 P2 verified bge-large-zh SentenceTransformer 模型在每次 embed/检索调用中重复加载：genesis 每步全量重嵌（每 hook/rule 一次全新模型加载）+ 每章 context assembly 两次加载
F385 P2 verified dispatch_skill 第三路由（legacy `shenbi-dispatch` 子进程）为必失败死端：internal 模式硬拒 + uses_staging 被忽略
F386 P2 verified 软失败升级路径派发 escalation-review 但不设 ESCALATION checkpoint——升级从不暂停、escalation 报告成为孤儿
F387 P2 verified genre 波与 group 波文件级重复不止 sensitivity：worldRules/motivation/dialogue/texture 四维每章重复审计并覆盖 group 波产物（F329 的完整版）
F388 P2 verified `_audit_context_coverage` 死函数：docstring 声称"pipeline resume 初始化时调用"（spec §3.1 的 77% 上下文覆盖缺口检测），cli 从未接线
F390 M verified cmd_review `--feedback` 文件缺失时误报 "project not found"
F154 M verified safe_write flock 主路径与 O_EXCL 回退路径互不感知对方锁原语：flock 持有者与 lockfile 持有者可并发写同一目标（第四处并发缺陷站点，前九轮只覆盖原语内竞态）
F155 M verified scoring.check_scorer_agreement 对 NaN 分数误报 agreed=True；flag_score_collapse 对单维度误报 all_identical（两函数数值边界缺陷；函数当前 dead（Z5 F500），接线前必须先修）
F647 P2 verified records drift.py `by_id` 对重复 id / 缺失 id 静默塌缩：权威 YAML 中重复 hook id 只保留最后一条，派生表与"错误的那条"比较 → 漏报或误报 drift 且无任何告警
F468 P2 verified G3.2 的 `threshold = 90` 在循环内赋值泄漏到后续报告 → 同一报告因扫描顺序不同得到 PASS/FAIL 不同判定（F428 同根因的第二机制）
F469 P2 verified shenbi-chapter-revision 的 composite 把 g4_decisions 接进 "existing"（md）槽 → DecisionsDoc schema/P2.5 校验对该技能 decisions.json 永不执行，schema 违规静默 PASS
F472 P2 verified cli.py bughunt/clean 分支不转发 rd → 相对路径报告恒 resolve_input_path ValueError 崩溃（F403 家族独立实例）
F391 P2 verified API/IDE 派发路径完全跳过 G1 input-readiness 门禁：缺失契约 reads 静默丢弃、无失败语义——模块 docstring 声称的 "G1/G2 经 dispatcher 内部执行" 仅 legacy 子进程路径成立
F392 P2 verified decisions JSON 恢复失败的 ValueError 穿透 dispatch→CLI：API/IDE 路径裸 traceback、无 checkpoint、无 JSON 结果（F304 同族、异常源不同）
F393 P2 verified review_checklist._extract_hook_deliverables 仅读 frontmatter hooks：生产 hook 数据在 body 表格 → 注入每个审计 prompt 的 "hook_deliverables" 恒空（F347 同根、新消费面）
F394 M verified crash_recovery.reset_emergency_state 注释声称 "remove any atexit hooks registered by earlier tests" 但从未调用 atexit.unregister，且 register 无去重
F395 M verified _dispatch_via_api 对任意异常调用 _handle_timeout_gracefully：非超时错误也打 "dispatch_timeout ... resolution=saving_partial_output" 日志，而该函数不保存任何部分输出
F251 P2 verified 独立 dispatcher 评分产物与门消费契约三处不匹配：`-scores-subagent.json` 命名对 G0.10/find_report 不可见 + raw 维度 dict 无 final_score + progress 状态 "done" vs "DONE" → G0.10 恒 WARN、G5.1 恒 no_report FAIL、GR.2 恒 FAIL
F252 P2 verified standalone 编排不执行 G4、不写 gate marker → shenbi-score gate-marker 强制必 MISSING（exit 3）→ 任何走到评分阶段的独立派发 rc=3；且 exit 3 先于分数校验（F243 所述 REJECT exit 2 被前置拦截）
F156 P2 verified phase_runner/executor 双路径对混合输出施加单一 derive_file_type：file_type="decisions" 时 G2 decisions 分支整体跳过 .md → 主章 .md 仅过 G2.1-2.3（存在/非空/UTF-8），文档化 G2.4-G2.12 内容校验（字数 G2.6、重要章节 ceiling G2.7、格式 G2.8/2.9、frontmatter G2.5）在管线路径静默不执行
F157 M verified scoring 交互模式 `input()` 提示词写入 stdout 数据通道：stdout 整体为单行"提示词+JSON"混合、不可 JSON 解析，违反 cli_utils "stdout=数据通道/stderr=诊断" 契约
F649 P2 verified check_opening_similarity/check_window_redundancy 用 SequenceMatcher.ratio() 默认 autojunk → 相似度随参数顺序不对称（0.57 vs 0.637），近阈值分类不稳定；F642 跨三轮之争的根源
F650 P2 verified TraceWriter 信任尾部签名不做链校验：可解析但签名无效的尾部（篡改/坏写）静默链上新事件，下次 replay 把新合法事件与坏尾部一起截断删除——静默数据丢失（F615 的另一失败模式）
F651 P2 verified records parser yaml.safe_load 对重复键静默 last-wins（`state: A` + `state: B` → B，无错误无告警）→ 权威记录源静默损坏，drift 与错误值比较
F254 P2 verified executor.run_g1/run_g2 与 codex.dispatch_codex 的 shenbi-score 子进程均无 timeout（仅 codex exec 有 600s）→ standalone 路径门/评分子进程挂起时无限阻塞
F255 P2 verified derive_file_type 的 REPORT 分支先于 truth 交集返回 → kind=report 且写 truth 概念文件的技能被归 "report"，G2.11 truth 只增不删保护对其静默失效
F396 P2 verified check_genre_config_drift 的 _WARNING_RE 与两个生产写入方格式零交集：spec §6.6 genre-config 运行时更新触发恒 False，`config.genre_config_update_on_drift`（默认 True）全路径无功能效果
F473 P2 verified G6.11 卷边界检查在真实项目上恒发 7 条 must_fix：跨卷伏笔表格单元格被解析为"幽灵卷" + no_ending_hook 评估的是文件尾部元区块而非叙事结尾 + 规划中未写卷恒 FAIL
F474 P2 verified G6.4 时间线日期提取对单章内非时序日期引用（截止日/当前日混排）误报 timeline_regression——真实项目 2 条 FAIL
F475 P2 verified G0.3/G6.1 的 chapter_word.default 读取是死特性（GenreConfig 契约与真实配置均无此键）且 default=0 时 ZeroDivisionError 崩溃
F476 P2 verified G4.chapter-planning 仅实现 SKILL 声明 8 条"可自动检查"规则中的 2 条（段完整性/chapter_role），缺 6 条（段标题精确性/优先级来源声明/章尾改变数/hook 账列名/hook 操作有效性强制/沉默检测）
F478 M verified 12 个 UNIMPLEMENTED 子检查 stub（G0.5/G7.2/7.3/7.4/7.8/GR.3/GR.4/GT.2/GT.4/GT.5/GD.2/GD.3）→ 对应门声明的部分校验目标未实现而门仍 PASS
F479 M verified g4_worldbuilding story_bible 注释 "prose density < 5%" 与代码方向相反（代码检查 bullet_density > 5% FAIL，SKILL 要求散文）
F480 M verified g4_generic_bughunt/clean 的 `if not mf or all(not x.startswith(...))` 死条件（mf 只含本家族前缀条目，all(...) 恒假 → 条件退化为 `not mf`）
F481 M verified G2.meta_ratio 在 ratio>0.5 时输出两条同 id 的 WARN check（_check_meta_ratio 返回 WARN check + failures 字符串被重复追加）
F482 M verified check_chapter_title docstring 声称 "Thematic naming encouraged (1-4 Chinese characters)" 未实现
F483 P2 verified g4_chapter_drafting 主角名单硬编码阳性代词"他"且从不加"她" → 女性主角作品主角在场检查误报 FAIL
F159 M verified sync_contracts 从不调用 `configure_logging()`：全部日志输出到 stdout（违反 logging.py:8-9 "All output goes to stderr" 与 cli_utils stdout=数据通道 契约），且 `SHENBI_LOG_FORMAT` 环境变量对该工具静默失效
F654 P2 verified compute_drift `_try_float` docstring 承诺"非有限数值返回 None"，实际 nan/inf/1e999 透传 → 趋势表出现 nan 单元格时序列被静默污染（smooth 全 nan、σ 统计全 nan、单调 run 中断）
F655 P2 verified records `detect_cross_section_drift` 对"缺失键"无空值语义：`rec.get(key)` 返回 None 且 `_values_equal(None, '')` 恒 False → 派生表空单元格/多余列在 YAML 记录省略该字段时恒报假 drift
F484 P2 verified g3_independence 对畸形 agent_trace 静默 fail-open：agent_trace 非 dict 时同源评分检测被跳过 → G3.4 独立性保证在坏数据下失效（F408 家族之外的独立机制）
F486 M verified g4_plot_thread_weaver G4.pt.lines 检查语义缺口：6 标签 OR 匹配且 "## A" 为子串 → 仅单线（如只有 "## A"）即 PASS，A/B/C 三线缺失检测失效
F256 M verified g2.py G2.10/G2.12 注释声明 "chapter files only"，代码对全部 file_type 无条件生效——truth 文件占位符行误拒 + JSON 系统性假 WARN
F257 M verified executor.dispatch 的 `chapter` 关键字参数全仓零调用方（死参数）；dispatch_with_write_audit 另行独立二次 extract_chapter
F398 M verified `_verify_truth_integrity` 在每章边界误报：`plans/chapter-{current_chapter}-plan.md` 在章首本来就不存在（step 2 才创建），却被当作缺失关键文件告警——"fail fast"检查每章产生一次假阳性
F399 P2 verified `next` 命令在审批过渡型检查点后静默跳过相位转换/延迟动作：GENESIS_COMPLETE approve 后 `next` 恒报 OK 无进展；VOLUME_BOUNDARY approve 后 `next` 不派发延迟快照、不更新 total_chapters
F161 P2 verified RoundPaths.write() 无任何生产调用方（死代码）：F112 只覆盖了 repo()/backup()，write() 为同一家族第三个遗漏成员
F162 M verified phase_runner cmd_post_skill 冗余调用 configure_logging()：与 main() 重复配置，为六命令中唯一命令内再配置站点
F487 P2 verified g4_chapter_drafting `_load_protagonist_names` 主角名双重追加 → 主角在场计数翻倍（正常路径 fail-open）
F490 M verified g4_chapter_revision 返回的 `checks` 槽是字符串列表而非 dict 列表（GateResult 契约偏离，F414 同返回语句的第二个键）
F657 P2 verified compute_drift.main 卷级检测丢弃 human_overridden 排除标志：章节级排除、卷级不排除 → 被人工覆盖的卷降分仍触发 VOLUME_DECLINE
F658 P2 verified parse_markdown_table 派生表内重复 id 行 last-wins 静默塌缩：首行被吞且无告警（F647 的 md 侧镜像，独立函数独立行）
F258 M verified extract_chapter 首匹配语义：多章节引用英文 prompt 取**第一个** "chapter N"（引用章），非目标章 → standalone G1/G2/审计面全部解析到错误章节
F3A0 P2 verified `_build_skill_prompt` 的 "Files to create" 清单跳过全部通配输出路径，而 shenbi-character-design 的 G4 无条件要求 major/minor 子目录 ≥3/≥2 文件——genesis step 3 与卷边界 expand 触发步 G4 缺口
F3A1 M verified `dispatch_skill` 的 test_type/round_dir/skip_reads 形参在 API/IDE 路由被静默丢弃（仅 legacy 子进程路径生效）——测试隔离与 G1-skip 语义对主路由不成立
F164 M verified phase_runner.py:124 emit 信封 `"g5": "PASS"` 为裸 GateStatus 字面量：唯一裸状态字面量 emit 站点，逃逸 lint_status_strings 的键范围（仅查 status/state/classification），并证伪初审"status 字符串 emit 用枚举成员"的不变量声明
F3A3 M verified pipeline-state.json 损坏/版本不匹配时 machine.load_state 抛 JSONDecodeError/ValueError，cli 六个命令仅捕 FileNotFoundError → 裸 traceback（无 emit_json、无 checkpoint）
F259 M verified extract_chapter 接受 "chapter 0" → 0：零章节号与模型/门语义不一致（N/NNN 解析出 chapter-000/chapter-0 路径，G1 对不存在文件 loud FAIL）
F261 M verified decisions.py `VALID_BASIS`/`VALID_SEVERITY` 死常量；`Selection._p25` 错误优先级：routine+low 超长 rationale 报长度错误而非 FORBIDDEN
F491 P2 verified g4_worldbuilding 地点计数双重缺陷：`## 地点[：:]?` 可选冒号吞掉"## 地点构建汇总"汇总节 + numbered_loc 优先分支把任意 `## N.` 标题当地点数 → SKILL 模板合规输出误报 `G4.locations.count` FAIL
F492 M verified G0.5b rubric-SKILL 一致性检查 evidence 正则漏认"证据"列头形态 → 每次带 seed 的 `shenbi-validate G0` 恒发 3 条 rubric-SKILL mismatch WARN（score-arc/stratum/volume）
F165 M verified phase_runner/`__init__` docstring 宣称 "T2/T3 phase state machine" 与实现不符：G5 只认 t2-phases（t3 名恒 FAIL "unknown phase"），pre_score/finalize 只读 `deps["t2-phases"]`，command-to-give.md:126 明示 "T3 不使用 phase-runner.py" → phase_runner 实际 T2-only，"T2/T3" 承诺为假
F166 M verified phase_runner cmd_pre_skill 的 skill 参数未净化直接拼接路径：`PROJECT / "skills" / skill / "SKILL.md"` 与 load_contract 内部 `SKILLS / skill / "SKILL.md"` 均可穿越 skills/ 目录做任意路径存在性探测、并把技能目录外任意位置放置的 SKILL.md 解析为契约（F158 只覆盖了 phase 参数的写侧穿越，skill 参数读侧站点前十四轮完全未提及）
F660 P2 verified parse_markdown_table 无表头表静默整表丢行（首行分隔行被当表头 → 数据行无 id 全部丢弃，drift 检查空转）
F494 P2 verified G6.4 时间线检查只读每章前 5000 字符 → 章节后半段的时间线回归完全漏报（check_pacing 却读全文，采样口径不一致）
F495 M verified review_arc_payoff / review_resonance 的 file+line 证据正则被时间/比例/日期形态满足 → 无文件引用证据的报告 false PASS（fail-open 启发式）
F3A5 M verified `cmd_chapters` 按字符串键排序章节状态：`chapter_states.items()` 字典序使 "10" 排在 "2" 之前，chapters JSON 数组非数字序
F3A6 M verified 并行审计波读取 genre-config.json 用裸 `json.loads`（chapter_loop.py:2574），JSONDecodeError 无任何捕获 → 穿透 CLI 裸崩（F3A3/F392 同族、异常源第三处）
F3A7 M verified `cmd_resume` VOLUME_BOUNDARY approve 分支的延迟 snapshot-manage 派发结果被静默丢弃：无 success 检查、无 G4、无失败 checkpoint → 卷快照欠账无任何信号
F262 P2 verified read_fields 声明与生产者模板系统性漂移（7 文件/5 技能）——含 F218 部分丢弃实锤（book_strata/arc-N「未解决悬置」被静默丢弃）+ F231 同类全漏实例（0/N → 恒 escape hatch）
F662 P2 verified materialize `_as_float` 对 str 分数静默置 0.0（同模块 `_as_int` 却接受 str）——MARK_DONE score 为字符串时分数被静默抹零
F496 P2 verified G6.8 幽灵角色检测与口头禅匹配只读每章前 5000 字符 → 章节后半段角色/口头禅漏检漏报（F494 采样截断家族第二消费方）
F3A8 P2 verified `_check_content_size_guard` 新旧内容比混用"字符数 vs 字节数"：中文章节 revision 缩改（保留 <60% 原文）被误拦截 → 重试循环/静默不应用
F3A9 P2 verified `_build_hook_debt_briefing` 对 frontmatter hooks 中缺 `id` 键的条目直接 KeyError → 单条坏数据使整章 curated 文档（P1-P7+多样性+债务简报）不产出
F263 M verified `read_frontmatter_contract` 的 `split("---", 2)` 不以行首锚定：frontmatter 内出现 "---" 子串（描述/示例文本）时截断 → 静默字段截断或 loud 误报；g0_skill_contract 存在同款孪生
F264 M verified `extract_h2_sections` 重复 H2 标题折叠：同标题多段内容在字段过滤时静默丢首段（dict 键覆盖），与 F218 的"未匹配丢弃"机制不同
F265 M verified `_diff_records` 的 None 哨兵使 null 值新增键旁路 record_field 键集校验（F260 的 record 层孪生）：track/resolve/state-settling 对 null 值键写入零审计
F266 P2 verified write_semantics 校验面整体未接线：`mode` 值自由形式无词表校验（拼写错误静默通过）、`append_dedup`/`merge_prose` 声明无框架实现（dispatch_helper 显式 NOT branched、g4 无 checker）、且与 truth 模板 `update_mode:` 词表双轨并行
F3AA M verified cmd_status / cmd_chapters 的 ReadLock TimeoutError 未捕获（管线运行期间 30s 后裸 traceback；cmd_init 有先例却漏接）
F267 M verified cli.py 只取 argv[4] 作 prompt：未加引号的多词 prompt 静默截断（argv[5:] 丢弃）→ codex 收到残缺指令
F268 M verified G2/G4 文件列表逗号拼接协议：输出/校验路径含 `,` 时被门 CLI 拆分为两个错误路径（executor run_g2 拼接 vs gates/cli.py 拆分）
F498 P2 verified G5.3 数值一致性检测完全死路：num_pat 单捕获组 + `m.group(2)` IndexError 被 `except Exception: continue` 吞掉 → numeric 冲突永不报告；测试显式钉死惰性行为（"source bug"）
F499 P2 verified F494/F496 采样截断家族剩余 2 个消费方：G6.9 章节扫描（[:3000]）与 G5.3 术语一致性采样（[:3000]）只读每文件前 3000 字符 → 章节尾部规则违反/术语混用漏检
F664 P2 verified 审计链对 records.parser 的 yaml.YAMLError 无防护：坏 YAML 的 post .md 使 `dispatch_with_write_audit` 的 finally 块整次审计崩溃（写越权/drift 门禁被旁路、成功 dispatch 的 rc 被异常取代、无 write-audit.jsonl 记录）
F665 P2 verified drift-guidance skill §11.8 "卷级目标未达成"触发器在 compute_drift 未实现：SKILL.md 指示 LLM 读取 volume_score_trend.md 并从 drift_detection 获得卷级目标漂移信号，但 CLI 无该输入参数、无该 DriftKind、无 objective_achieved 解析
F3AB P2 verified `_extract_chapter_title` / `_load_previous_titles` 用 `re.match`（位置 0 锚定）提取标题，生产章节文件一律以 META 块开头 → 标题恒空、G4.cd.title 重复标题检测在正常路径完全失效
F3AC P2 verified 并行 post-draft 中 foreshadowing-lifecycle dispatch 失败被吞：仅 state-settling 失败升级，lifecycle 失败 log 后照常 `add_step_done`+推进，hook 更新静默丢失且不可重试
F3AD M verified ReadLock/WriteLock `__init__` 无条件 `mkdir(parents=True)` → 只读命令 `cmd_status`/`cmd_chapters` 对不存在的项目目录静默创建空目录（副作用）
F3AE M verified cmd_status / cmd_chapters 的 emit_json 无 `status` 信封键（其余全部命令都有），与 cli.py 模块 docstring "Result-envelope status values use the typed CommandStatus vocabulary" 矛盾
F4A0 P2 verified G6.9 数值规则合规检查约束侧失效：关键词↔约束错配（str(val) 命中共享上下文中更早的数字子串）+ 真实 rules.md 散文格式零约束 + 仅"人/个"单位 + 前 10 条上限 → 现实项目数值规则违反静默漏检
F3B0 M verified check_audit_line_refs 的 `_LINE_REF_RE` 仅匹配英文 `L(\d+)` 行号格式，生产 15/722 审计文件用「第N行」中文格式 → G4.av.stale_line_ref 对这些审计静默失效（格式契约断裂，F324/F396/F389 同族）
F3B1 M verified truth_embed main() 的 emit_json 用裸字面量 "degraded" 作 status 值（非 CommandStatus 成员），违反 spec D3 类型化信封约定（F3AE 同族、独立实例）
F270 M verified `record_audit_outcome` 的 write-audit.jsonl ledger 写入无防护：round_dir 只读/磁盘故障时 finally 块裸抛，掩盖 dispatch 异常且审计记录丢失（F238 的 record 层孪生，故障面=文件系统）
F271 M verified `extract_h2_sections` 不跳过围栏代码块：truth 文件内 ``` 围栏含 `## ` 行时产生伪 section，字段过滤输出携带悬空围栏标记（F264/F218/F262 均未覆盖代码围栏干扰面）
F4A1 M verified g4_worldbuilding truth 模板检查：缺 frontmatter 字段时同一文件同时输出 FAIL(must_fix) 与 PASS(check)（c.append(PASS) 无条件执行）
F4A2 M verified G6.8/G6.9/G6.11 子检查产生 must_fix 违规时仍无条件输出 "PASS" 汇总 check 条目 → G6 FAIL 输出的 checks 带自相矛盾 PASS（F481 同族新实例）
F4A3 P2 verified G1 glob 展开双重缺陷：相对 glob 按 CWD 解析忽略 round_dir（与 resolve_input_path rd 语义不一致）+ compute_backup_targets 在展开前计算 → in-place 技能 glob 输入下 .bak 永不创建且误标 "not in-place skill"
F4A4 M verified G6.8 口头禅提取 `ct[ct.index("voice_profile:") :]` 至 EOF 抓取全部引号串（正文 + 后续 frontmatter 字段）→ 口头禅列表污染、`[:3]` 检查语义漂移 → 真实口头禅在场仍误发 catchphrases_not_found WARN
F3B2 M verified genesis._update_route_b 打开 EmbeddingStore 从不 store.close()（SQLite 连接泄漏）——对照 context_assemble._route_b 有 close
F3B3 M verified GENESIS_COMPLETE MODIFY 的 modify_feedback 被存进 chapter_loop 字段但 genesis 从不消费——重跑不带人审反馈，残留反馈随后泄漏进 chapter-loop 首次 dispatch
F3B4 M verified cmd_backfill_context 无任何 ReadLock/WriteLock——与并发管线写 context 文件竞态（对照其余全部命令持锁）
T7-01 P1 verified resonance_trend.md 双写者键格式漂移（CN3 模式）：框架写者行键 `Ch{N}`（7 列）与 skill 写者行键 `{N}`（9 列）不一致 → 同章 upsert 不去重产生重复行 + 列数错位
T7-02 P1 verified pending_hooks.md 结构化 hooks 记录丢失 + 格式契约漂移：生产文件无 `hooks:` frontmatter（ch53 快照 22 条 → 当前 0 条），全部 frontmatter-hooks 读取器静默空读，G6.7 对无 `## hooks` 段文件垃圾解析
T7-03 P1 verified staging/truth 与 truth/ 活副本分叉 + G4 校验 staging 副本而下游读 committed + clear_staging 生产运行未生效
T7-04 P2 verified LLM 元叙述 + 未闭合代码栅栏泄漏进 truth 文件；后写完整性检查只覆盖章节/审计，truth 文件从不检查
T7-05 P2 verified `update_mode:` frontmatter 契约"写一次、读零次、生产全缺"
T7-06 P1 verified state-settling SKILL.md 内部契约自相矛盾：frontmatter 声明 current_state/particle_ledger/subplot_board 为 append_dedup（累积），正文声明为 replace（快照）——F397 修复必须先裁决权威语义，否则按 frontmatter 路由修复会破坏快照文件
T6-01 P2 verified record_gate_result 对 pipeline-manifest.json 的读-改-写锁是进程内 threading.Lock：phase_runner cmd_post_skill 在 pipeline WriteLock 之外写 manifest → 跨进程 lost-update（F253/F3A4 家族第 4 实例站点）
T6-02 P2 verified `_executor_config_cache` 惰性初始化 check-then-act 竞态：并行审计波首批 7-9 线程并发首调 → N 个重复缓存条目（沙箱复现 8 线程→8 条目）
T6-03 P2 verified write_safety 分类是名字启发式：26 个 shenbi-review-* 中 2 个契约有 updates（resonance + arc-payoff）→ `assert_parallelizable` 保证建立在错误谓词上（F374 现行实例，arc-payoff 潜伏扩展）
T6-04 P2 verified truth_io `_path_lock` 键未规范化（相对/绝对/symlink 拼写→不同锁）：同文件写者可并发绕过串行化（latent）
T6-05 M verified safe_write 两锁路径互斥粒度不对称：flock=目录级（同目录不同文件也串行，拖慢并行波）、O_EXCL 回退=文件级（正确性已由 F154 覆盖，性能/一致性观察）
T1001 P2 verified D1 行号订正在归档 spec 中再次漂移（4 处关键引用偏离实际代码 7-22 行）
T1002 M verified INDEX:91 "PR #20 torch-bump 处置（待 #3 follow-up）" 注记过期
T1-01 P1 verified pipeline 模式下 decisions.json 无任何门校验：G2 整门跳过 + G4 文件列表不含 .json → G4.dec 恒 SKIP "no files"，门恒 PASS
T1-02 P1 verified Producer 模板与 prompt 均不编码 decisions schema/P2.5 规则 → 真实产物枚举/结构大漂移
T1-03 P1 verified 写路径 schema 校验缺位：_validate_json_output 仅语法校验、clean 但违规 JSON 原样落盘；IDE/codex 直写完全绕过
T1-04 P2 verified context/chapter-N-context-decisions.json 悬空读：producer（context-composing）被确定性策展替换，consumer（chapter-drafting）仍声明该读，API 路径无 G1 → 静默丢失
T1-05 P2 verified plan-decisions.json / state-settling-decisions.json：registry 声明但零契约 producer，且 staging commit 只提交契约路径/仅 *.md → 55+1 文件滞留 staging，从未 commit/校验/读取
T1-06 P2 verified SkillOutput.decisions 死字段：定义+prompt 要求输出，但写路径从不消费
T1-07 P2 verified decisions-schema.md ↔ DecisionsDoc 双向往弱漂移：selections 标 REQUIRED 但 model 默认 []；produced_at 标 ISO 8601 但 model 仅 str；selections severity 含 medium 且 docs 未列
T1-08 M verified G2.dec.4 多对象检测按 `"$schema"` 原始计数：对 67 个真实 "Extra data" 拼接 0 命中（均不重复 $schema），反而对 rationale 字符串内出现 `"$schema"` 文本的合法文件有误报面
T301 P1 verified pipeline 字段级过滤为死代码：`_build_skill_prompt` 的 dict-form reads 分支永远不触发，`filter_to_fields` 唯一生产调用点恒传空 fields
T302 P1 verified `lint_contract_fields` 假阴性：基准 fixtures 与声明自洽，真实 run/生产者模板漂移全部漏检（exit 0）
T303 P2 verified 4 个 group skill 正文手写 `## Contract` 块与 frontmatter 双源漂移（含字段声明永不生效）
T304 P2 verified `check_fields_exist`（G1 字段漂移 WARN）为死代码：无生产调用，D21 播种机制为其服务的假设不成立
T305 P2 verified `filter_to_fields` 对非 md/json 扩展名静默跳过：不过滤、matched=True、无 WARN（latent）
T201 P1 verified B.5 字段漂移 lint（lint_contract_fields.py）未接入 CI/pre-push/pre-commit/测试：docstring 声称 "blocks PR" 在 CI 面不成立，契约 reads 漂移可静默合入
T202 P2 verified truth-files.yaml 死词表 6 项（short/*、chapter-revised、plan-decisions sidecar、snapshots glob D20 废弃未删）
T203 P2 verified dependency-dag.json 生成但零消费（唯一消费者是 CI idempotency git diff）
T204 P2 verified G0.16 只校验 write mode 存在性不校验值合法性（拼写错误 mode 过门禁被当默认处理）
T205 P2 verified sync derive_expected_outputs/verify_bijection 对契约加载失败的 phase 成员静默丢输出（双侧同空自检失效）
T1501 P2 verified 96MB 孤儿 blob（commit 对象 dump）无路径、unreachable；`.git` 膨胀 75MB
T1502 P2 verified gh-pages 分支 mkdocs 构建产物入库（search_index.json 6.9MB + bundle js.map 1MB）+ 5 个 6.5-6.9MB 孤儿 search_index 变体 + 4.1MB 文件清单 dump + 673KB uv.lock 孤儿
T1503 P2 verified 孤儿分支 `docs/token-efficiency-p2-spec`：P2 效率 spec + field-level 3.7 spec 从未合并 main 也未归档；Layer B 功能已实现（ea9575e）但文档悬空
T1504 P2 verified 远程分支残留：sdd/inference-control-audit（13 commits 已 squash 合入 #40 未删）、docs/archive-inference-control（已合入 #41 未删）、pre-commit-autoupdate 升级未合入（ruff/mypy/hooks 版本滞后）、10 个 dependabot 分支 NOT-IN-MAIN
T1505 P2 verified G5 numeric revert 闭环未完成：b74e9ae 修复 → dc6fc67 revert（pin inert）→ 承诺的 source PR 从未落地；`m.group(2)` 非捕获组 IndexError 被吞、numeric 检测死路被测试固化（F498 历史根因）
T1506 M verified dispatch_helper zcode 半迁移残留：auto-detect 已 revert 但 IDE CLI 路径仍列 zcode + "requires separate testing"/"future zcode usage-report" 注释
T1507 M verified `contracts/legacy.py` 命名残留：文件名 legacy 实为当前单源契约加载器（docstring 自述）
T1508 M verified 归档文档 broken links：2026-06-15-p-1.e-06-enterprise.md → 0001/0002/0009-ADR 链接失效；ci-optimization-design.md → `file.md`；eliminate-existing-warnings-plan.md → `../nonexistent-test-link.md`
T401 P2 verified usage 载荷形状/类型脆弱：缺 total_tokens / None 值 / dict 形状 → AttributeError/TypeError 崩计量热路径（API 成功后、输出写盘前）→ 丢 LLM 输出
T402 P2 verified shenbi-cost 报告零自动化消费：账本数据 write-only，成本观测纯人工 CLI
T403 P2 verified parallel 接线 state 的聚合非原子性 + F505 联动：F302 修复方向（Z5.review4 建议"全部调用方传 state"）在并行波上会激活共享 dict 竞态与跨实例 append 交错
T404 P2 verified iter_records/summarize 静默跳过损坏行，报告无跳过计数：成本报告把不完整账本当完整展示
T9-01 P1 verified lint_status_strings 对"词表外发明值"全盲：6+ 站点在 status/state 键上发射 `STATUS_STRING_LITERALS` 之外的状态值，CI/预提交门禁全绿
T9-02 P2 verified "s" 键通道 186 处裸 GateStatus 字面量完全绕 lint；同键双轨（g4 枚举成员 vs 其余裸串）
T9-03 P2 verified ChapterState.status 无类型字段 3 拼写漂移（pending/complete/settling_failed）；progress.json 同键承载第二套词表（pending/done/skip）
T9-04 P2 verified Severity 词表 5 套互斥值集并存；enums.py Severity 为死表且与 4 套活词表值集冲突（F208 扩展）
T9-05 P2 verified Verdict 词表 4 套互斥值集并存；enums.py Verdict 死表与活词表值集不相交（F208 扩展）
T9-06 P2 verified 16 处裸字符串 status/state 比较 + 6 处 require_state 裸列表替代枚举成员（lint 洞 H4）
T9-07 P2 verified HookState 枚举 + parse_hook_state 已存在，但 4 个使用点全部裸字面量绕过；g6.py 双大小写比较并把 ARCHIVED/EXPIRED 终态误计为 unresolved
T9-08 P2 verified lint 形态盲区：Call 关键字参数与属性赋值发射完全不可见（F209/F164 站点同时逃逸 lint）
T9-09 P2 verified ActorRole 发射端 2 处裸字面量绕过已定义枚举（safe_write.py:134、audit/record.py:46）
T9-10 P2 verified trace action 名称无词表（6+ 裸串）；MARK_DONE 生产零发射，与 chapter_loop.py:680 注释背离，materialize 重放路径事件源缺失
T9-11 P2 verified 双"单一信源"声明分裂：enums.py 与 status.py 各自声称全框架唯一词表，互不引用、词汇集不相交；enums.py 头注释「所有 Literal 必须从此处 import」已被 6+ 处违反
T12-01 P1 verified `<document name="{fname}">` 属性注入：LLM 可控制文件名（通配符写契约）含 `"` 字符 → 逃逸文档 wrapper 属性 → prompt 注入（与 F300 内容侧 no-op 同 wrapper 的另一条未修复向量）
T12-02 P1 verified 持久化 prompt 注入链端到端可达 + codex（workspace-write）路径可直改 project_dir 内状态/门禁/评分文件：pipeline-state.json、gate markers、progress/scores 完整性击穿，且该路径无写审计（F512）
T12-03 P2 verified run_pipeline.sh 与 tests/round-exec.sh 将目录参数插值进 `python3 -c "…"` 双引号 shell 串 → `'`/`"`/`$()`/反引号 均可注入任意命令（命令注入；Z10 区确认 + 新实例）
T12-04 P2 verified codex/zcode 子进程全量继承父环境：SHENBI_LLM_API_KEY（T1 路径）/CI token 等凭证可达 workspace-write 通用编码 agent；与 T12-02 注入链叠加构成凭证外泄路径
T12-05 P2 verified 写路径穿越防御脆弱隐式：`relative_to` 词法不归一化 `..`（拦截仅靠 wildcard 正则形态）；symlink 目录逃逸（声明目录为 symlink 时契约校验通过的写落盘到 link 目标）；safe_write 零规范化
T12-06 P2 verified 按名拼接的防御缺失：`skills/{skill}/SKILL.md` 与 `load_contract(skill)` 无 skill 名词法校验（当前调用方全为硬编码配置，未来不可信 skill 名 → 任意仓库文件读入 system prompt + 契约混淆）；plugins/generate.py `REPO_ROOT / config["output"]` 允许 `..`
T1301 P2 verified pytest-asyncio 声明于 dev group 但全仓零异步测试（休眠插件）
T1302 P2 verified pytest-ordering 声明但零使用，且 0.6（2019）无人维护
T1303 P2 verified numpy 为核心依赖但其全部引用点仅在 Route B 可选路径执行
T1304 P2 verified dev group 的 setuptools 无任何运行时消费者（冗余直接声明）
T1305 M verified plugins/master.json version=0.2.0 与 pyproject version=0.1.0 漂移，无同步机制
T1306 M verified pyproject.toml:11 pydantic 注释"P-1 不用；为 P0 schemas 准备"已过期
T501 P1 verified tenacity 重试层在生产路径为死代码：`_is_retryable` 只认裸 httpx 异常，openai SDK 异常永不命中（429/5xx/timeout 零重试 + 测试掩盖）
T502 P1 verified ESCALATION 解决不清零 durable 重试预算：升级后首个再失败确定性 raise 未捕获 RetryExhaustedError（F304 崩溃的第二触发源 + machine.py 契约假）
T503 P2 verified pipeline 级重试无退避、无失败分类：串行/closure 立即连发 ≤3 次全量 dispatch，429 风暴与 content_filter 等不可重试失败被同等放大
T504 P2 verified 写失败重试反馈 dead-wire：`build_retry_feedback`/RETRY_WRITE_CONFIRMATION 进 `DispatchResult.stderr`，无编排方读 stderr 注入重试 prompt → 写失败盲重试 ×3
T505 P2 verified finish_reason 处理仅 API 路径实现：IDE/legacy 无截断检测（cap-raise 保护缺失），finish_reason=None 时截断不可检测
T14-01 P1 verified 确定性助手"提示词级接线"零强制：5 个 skill_utils 助手只靠 SKILL.md 指令（"必须运行 / 禁止跳过"），无任何 G4/门校验助手是否执行——铁律 #2（prompt-only 守卫不够）系统性复发
T14-02 P2 verified hook_planting 死线补全（F307 新面）：TRIGGER_STEPS 卷边界仍 dispatch LLM 版 shenbi-foreshadowing-plant（活跃路径），与 foreshadowing-resolve 同块双写 pending_hooks.md
T14-03 P1 verified style-learning 全章 glob pass-through：chapters/*.md 全量注入（56 章 510KB → 截断后仍 ~128K chars ≈ 74.7K tokens/次），LLM 实际只需 compute_stats 的 JSON
T14-04 P1 verified state-settling"写半已落地"接线面证伪（F397 P0 的接线面补充）：truth_io.write_truth_file 唯一生产调用（resonance_trend，chapter_loop.py:3014）在 F301 串行路径不可达；accumulation 写路径从不分支 append_dedup
T14-05 P2 verified memory-distill 密度触发（60/15/20 阈值计数）声明未实现：确定性计数规则停留 SKILL.md，triggers.py 无密度检查
T14-06 P2 verified 双路由重复：review-resonance 的三路径分流（skill_utils.review_resonance.routing + calibration，SKILL 指令级）与 pipeline 侧 route_chapter_revision 是两套独立路由
T14-07 P2 verified 系统性模式：16 个确定性助手仅 ~5 个代码层接线——"确定性替换已 9 次实现"的说法是"实现 16 次、接线 ~5 次"；供 phase 4 聚类的母模式
T801 P1 verified **chapter-2..10-draft.md（9 文件）为伪造**：逐字节相同仅 H1 标题不同；PRE_WRITE_CHECK 全自述"第1章/N/A"；全仓零引用（死+假）。违反 G0.9"真实输出"声称
T802 P1 verified **chapter-7/8/9-example.md（3 文件）为伪造**：ch8==ch9 逐字节相同；ch7=ch2-draft 截断+改标题；却被 context-composing（ending diversity 输入）/ review-resonance / regenerate-baselines.sh（G2 基准）当作不同章节成稿
T803 P1 verified **snapshots/chapter-025 为伪造快照**：manifest 占位 checksum（abc123/xyz789）且 files 引用不存在的 chapters/；truth 5 文件与顶层第1章 fixture 逐字节相同（last_chapter:1）仅 current_state 改写；manifest 声称"第25章/125k 字"与内容矛盾。F516（snapshot glob 死代码）侧面证实该快照从未被生产消费
T804 P1 verified **calibration 27 锚点为手写 mock**：commit 自述 "human-curated … original prose"；锚点正文（老周/黑石饼）在 shipped 内容零命中（真实 canon=田国栋）；违反 calibration README 自身 schema 与 G0.9；且 G0.14 将手写锚点哈希锁进 deps.json 门禁（真实路径被假基准固化）
T805 P1 verified **arc/book-spine/book-strata/volume-summary-example.md（4 文件）自述非真实输出**（"format reference … Real outputs will replace it"），却是 lint_contract_fields 的 EXAMPLE_FIXTURES 基准 → 自洽闭环（T302）的基准本身就是 mock
T806 P1 verified **G0.9 只校验路径前缀，不校验存在性/真实性** → 19 个空目录（characters/、chapters/、source/、samples/reference-texts/、config/platform-rules/、story/volumes/、truth/、truth/character_profiles/、truth/source_material/、world/factions/、world/locations/、audits/、drafts/、import/canon/、import/packaging/、consolidation/volume-1/、skill-triggering-prompts/、snapshots/chapter-030/、snapshots/pre-chapter-25/）被 20+ scenario 引用，G0.9 全 PASS；generative 测试的 agent 读到空目录
T807 P1 verified **62 个 bug-hunt expected-output 中 60 个引用不存在的证据文件**（drafts/chapter-N.md、config/platform-rules/qidian-fatigue-list.json、snapshots/chapter-030/manifest.json、import/analysis/01_parse.md…08_state.md、characters/protagonist.md 等）→ 植错测试无法按剧本执行，测试掩盖/必然失败面
T808 P1 verified **scenario 植错前提与 fixture 内容不符**：chapter-drafting 声称"无 PRE_WRITE_CHECK + 然而×4"（实测有 PRE_WRITE_CHECK、然而×1）；review-sensitivity 声称 sensitive_words.txt 含傻逼/白痴/脑残且第6章第9段含"你这个白痴"（实测文件 3 词、chapter-draft-example 无白痴）
T809 P1 verified **review-arc-payoff bug-hunt scenario 引用 fixture 中不存在的内容**：hook-007/老周/黑石饼/arc_beats 均不在 outline-example.md、truth-pending_hooks.md（只有 hook-ch1-001..003）→ 剧本建立在锚点自创 lore 上，agent 无法在 fixture 中找到"证据"
T810 P2 verified **stop_words_zh.txt 格式违反自身 spec 且零消费者**：spec 规定"每行一个停用词"，文件为单行逗号分隔；chapter_loop.py/volume_align.py 各有硬编码停用词集，G6.7 文档声称的停用词过滤在 g6.py 中不存在（G6.7 是伏笔生命周期检查）
T811 P2 verified **sensitive_words.txt 仅 3 词**，G6.12 全文章节敏感扫描近乎空转；且 scenario 声称的敏感词与文件不符（并入 T808 影响面）
T812 P2 verified **28 个零引用死 fixture**：chapter-2..10-draft（9，并入 T801）、truth-emotional_arcs.md、truth-particle_ledger.md、market-data-example.md、multi-chapter-example.md、parent-canon-example.md、world-rules/locations/power-system/story-bible-example.md（4）、snapshots/chapter-025/manifest.md（并入 T803）、calibration 9 个 low 锚点（目录级引用外无单文件引用）
T813 P2 verified **truth fixture 命名断裂**：16 个 scenario 引用 `tests/fixtures/truth/`（空目录），仅 3 个引用实际存在的 `truth-*.md`（破折号形式）；`truth/` 下只有 character_profiles/、source_material/ 两个空子目录
T814 M verified **calibration README 过期**："No anchors are authored yet"与 27 个锚点现状矛盾；README schema 要求"Never invented or hand-crafted"，与锚点实际手写矛盾
T815 P2 verified **G0.14 双重实现漂移**：lock-tool-hashes.sh（无 CRLF 规范化、无 sort by relative path）vs g0.py check_calibration_integrity（有 CRLF 规范化、有 sort）vs test_g0_calibration_hash.py _compute_combined（镜像 gate）——Windows CRLF checkout 下重新 lock 会产生与 gate 不一致的哈希 → G0.14 假 FAIL
T816 P2 verified **chapter-draft-example.md 身份漂移**：同一文件被 139 处 scenario 引用为 chapter 5/6/7/8/10/15…（互相矛盾），audit-report-example.md 自述"第1章"；文件自身 H1 在第1章与第2章之间漂移（ch2-draft 标题"第2章"vs example 标题"毕业即失业与穿越即负债"）
T1101 P2 verified mutmut 按仓库配置结构性不可运行；基线文档归因错误
T1102 P2 verified mutation-score.txt 非基线；`just mutate-check`/compare_mutation_score.py 恒 exit 2 死工具
T1103 P2 verified 突变分数下界 59.6%（exceptions 41.1% / logging 58.6% / shared 63.3%），未达宣称 P-3 80%
T1104 M verified `[tool.mutmut] paths_to_mutate` 弃用（mutmut 3.6 应 `source_paths`）
T1105 P2 verified G0.8/G0.9/G0.9c 只扫 `scenario.md`，`scenario-pressure.md` 免疫——6 个压力场景 5 个含同款非 fixture 路径引用
T1106 M verified 压力场景计数错误（简报 7 个 vs 实际 6 个）+ 场景非自包含（需手工构造虚构项目）、无 runner、无自动化执行证据
T1107 P2 verified `tests/benchmark/` 空洞（仅 `__init__.py`）；唯一 benchmark 测试是 `1+1` 冒烟；`norecursedirs "tests/benchmarks"`（复数）指向不存在目录
T1108 P2 verified gate-outputs 差分基线陈旧（2026-06-15）且无 enforcement；G6/G7 基线因 round-001 目录消失而不可再生
T1109 P2 verified `tests/golden/` 空洞确认（README 声称 10-20 章，目录仅 README；P1.8 验收"≥10 章人工评分"未实现；0 消费方）
F1200 P2 verified lint_contract_graph.py 自称 "marquee CI mechanism / block PR"，实际未接入 ci.yml、pre-commit、pre-push-check.sh（T201 同类第二实例）
F1201 P2 verified lint_contract_fields.py（B.5 字段漂移 lint）未接入 CI/pre-commit/pre-push/测试（= 已知 T201，Z10 侧重新取证）
F1202 P2 verified ci.yml codegen-idempotency 对 `.codex-plugin/` 的 `git diff --exit-code` 检查空转（目录被 gitignore 且未入库，diff 恒空）
F1203 M verified ci.yml quality job 对 macOS 全 job `continue-on-error: true`，macOS 矩阵失败不阻断 CI
F1204 P2 verified run_pipeline.sh 将 `$PROJECT_DIR` 插值进 `python3 -c "…"` 双引号串 → `'`/`"`/`$()`/反引号命令注入（= 已知 T12-03，Z10 侧确认 + 精确定位）
F1206 P2 verified run_pipeline.sh 绕过 `pipeline review` CLI 直接改写 pipeline-state.json（step_index+1、retry_counts 清零）→ 状态机不变量由外部脚本篡改
F1207 P2 verified codeql.yml 无 pull_request 触发 → 根 SECURITY.md:21 "CodeQL static analysis runs on every PR and weekly" 的 "every PR" 声明不成立（F0-07 家族第二半）
F1208 P2 verified changelog 双机制漂移：release.yml 用 `git log` 平铺生成 release notes，cliff.toml + `just changelog`（git-cliff）未接入发布流程
F1209 M verified dependabot.yml:5 与 embeddings-smoke.yml:7 引用已移入 archive 的 spec 路径（`docs/superpowers/specs/…` 应为 `…/specs/archive/…`）
F1210 P2 verified lint_contract_graph 的 dag_key 无法连接目录读（`benchmarks/anchors/`）与文件写（`benchmarks/anchors/AC-*.md`）→ 真实消费关系被误报 DANGLING_WRITE；registry 对同一资产的 producer 分类矛盾
F1211 P2 verified 依赖锁定卫生：dev group 冗余/休眠依赖 + 版本漂移（= 已知 T1301–T1306，全部确认）
F1212 P1 verified deps.json 契约缺 5 skill 登记（foreshadowing-lifecycle + review-group-{character,craft,factual,plan}），executor_config 引用之；lint_repo_consistency 无 skill↔deps.json 完整性检查（= 已知 F0-02，Z10 侧确认）
F1213 P2 verified plugins/master.json skills 清单 59 vs skills/ 74（15 缺），generate.py 无任何 skills/ 交叉校验 → 新 skill 静默不发布（= 已知 F624，Z10 侧确认）
F1214 P1 verified lint_status_strings 对词表外发明值全盲：status/state/classification 键上 8 文件 10 站点发射 STATUS_STRING_LITERALS 之外的字面量，lint rc=0（= 已知 T9-01，Z10 侧重新取证）
F1215 P2 verified security.yml 无 schedule → 根 SECURITY.md:20 "pip-audit runs on every PR and weekly" 的 weekly 半句不成立（= 已知 F0-07，Z10 侧确认）
F1216 P2 verified tests/benchmark/ 空洞（仅 __init__.py）+ pyproject norecursedirs "tests/benchmarks"（复数）指向不存在目录 + 唯一 benchmark 测试为 1+1 冒烟（= 已知 T1107，Z10 侧确认）
F1217 P2 verified justfile `check` 与 ci.yml 双向漂移：just check 缺 N7/purity lint（CI 有），CI 缺 graph/fields lint（just 有）
F1218 P2 verified pytest addopts 全局 `--cov` 使 `--collect-only` 等非测试调用产生 16.08% 假 FAIL 并覆写 tests/coverage/；ci.yml "Run coverage threshold test" step 名与 `--no-cov` 行为错位（= 已知 D1-02，Z10 侧确认）
F1219 M verified executor_config.toml `shenbi-chapter-drafting` override 的 PRE-DEPLOYMENT 探测注释悬置（max_tokens=32768 是否被模型接受未确认/未清理）
F750 P1 verified 58/62 bug-hunt expected-output 的证据路径"既未植入也不存在"——植错测试无法按剧本执行
F751 P1 verified 12 个 bug-hunt scenario 的植错断言与 fixture 内容不符（T808 本区核实）
F752 P1 verified audit-report-example.md 单文件被 16 个不同审计技能的 bug-hunt/clean/generative scenario 当作"审计报告"证据
F753 P1 verified 18 个 fixture 目录有效为空却被 scenario 引用为存在的项目状态（T806 本区量化）
F754 P1 verified 8 个 rubric-only scaffold：无任何测试类型目录，其中 6 个是 T2 prerequisite → T2 分层契约不可达
F755 P1 verified F115 核实：38/82 rubric 维度过滤 no-op；4 份 per-dim-row rubric 的 N/A 豁免被 parser 静默吞掉
F756 P2 verified F0-02 核实：deps.json 缺 5 skill 登记（foreshadowing-lifecycle + review-group-*），契约 lint 无闭包检查
F757 P2 verified genesis phase roster 与 rubric/seed 不一致：deps.json 列 11 个 prereq，rubric Phase 行与 seed 只执行 6 个
F758 P2 verified deps.json _tool_hashes 陈旧：99 条中 63 条与当前文件哈希不符、3 条指向不存在文件，且无 gate 校验
F759 P2 verified 8 个 rubric-only skill 的 rubric 为模板化占位（通用维度/空 Standard 列），无 T1 测试价值
F760 P2 verified T1105 扩展：8 个压力场景 + 20 个变体场景免疫 G0.8/G0.9/G0.9c 纯度检查
F761 P2 verified using-shenbi bug-hunt scenario 引用空目录 skill-triggering-prompts/，声称"10 个 trigger prompts"
F762 P2 verified context-composing generative scenario 的"ending diversity"输入无多样性（chapter-8==9 逐字节相同）
F763 M verified acceptance.json 无 schema/版本字段，t3 阈值无 gate 消费
F764 M verified T2/T3 rubric 无 Dimension Applicability section（12/12），kill switch 单条且 parser 可解析
F765 M verified audit phase "All 18 review-* skills" 措辞与全量 review 技能数（24）不符
F850 P2 verified tests/skill-behavior + skill-triggering 全部 33 个 .md 是 tiers 场景的精确重复副本（38 对 diff IDENTICAL），非执行、无同步机制 → 双源漂移隐患
F851 P2 verified phase3-plant-track-resolve 内部算术自相矛盾（CP 债务 18 vs 12，公式支持 12）
F852 P2 verified revision-mode-routing 测试期望混合策略与 shenbi-chapter-revision SKILL.md"混合→rewrite"契约冲突
F853 M verified 铁律编号系统性漂移（测试引铁律1/2/3 vs SKILL.md 铁律2/4 错位；"培育超期=warning"无对应条款；plant_chapter vs planted_chapter 字段名不一致；跨技能铁律引用）
F854 M verified 快照"11 个 truth 文件"硬编码与真实数量漂移
F855 P2 verified using-shenbi 触发映射对"伏笔"类请求存在路由歧义（plant vs review/track）
F856 P2 verified test_word_count_md_always_non_negative 空转（策略字母表不含 CJK 字符 → word_count_md 恒 0）
F857 P2 verified test_excluding_all_decline_indices_suppresses_finding 空转（升序序列永不产生递减）
F858 M verified test_bootstrap_subset_of_yaml 伪属性（@given(st.data()) 未使用 _data）
F859 M verified 陈旧注释（docstring 声称 54==54 实际 70==70；"54→70"注释漂移）
F860 M verified .hypothesis 实际 11 个 0 字节文件 + 12 patch 共 17 个已发现失败（任务称 44 样本不符），17 个失败全部已修复
F861 P2 verified property 测试对 11 个 src 模块的增量覆盖缺口（空转/伪属性同根）
F800 P1 verified **chapter-2..10-draft.md（9 文件）为伪造章节草稿**：9 个文件 = chapter-draft-example 截断到 150 行 + 仅 H1 标题不同（"第N章：最新章节"占位标题）；PRE_WRITE_CHECK 全部自述"第一章"；与 outline 第2-10章内容不符；全库零引用（死+假）
F801 P1 verified **chapter-7/8/9-example.md（3 文件）逐字节相同**（T8 仅报 8==9）：`df81acba…` 三文件同一哈希；= chapter-draft-example 截断到 80 行 + 改 H1；被 context-composing generative 当"不同章节成稿"做结局多样性检查（三份相同文本无法检查）；**chapter-8-example 零引用**
F802 P1 verified **chapter-draft-example.md 身份漂移**：127 处 scenario 引用为 chapter 2/3/4-6/7/8-10/9/11/17/20…（互相矛盾；review-continuity bug-hunt 把同一文件同时充当 chapter 2 和 3）；audit-report-example 自述"第1章"、chapter-plan-example `chapter: 1`；文件自身 H1（毕业即失业与穿越即负债=outline 第1章标题）与"第2章"漂移
F803 P1 verified **review-resonance clean/bug-hunt scenario 与 fixture 断链**：声称 plan 声明 `chapter_role: 高潮/兑现`（实际 chapter-plan-example=推进/转折）；把与 calibration 锚点同款的自创 lore prose（老周脸/黑石饼/我替你还）**直接内嵌进 scenario 作为"被评估的成稿"**（该 prose 不在任何 fixture 章节中）；generative scenario 声称 chapter-7-example"with POST_WRITE_SELF_CHECK"（80 行截断版无）
F804 P1 verified **chapter-drafting / review-sensitivity bug-hunt 植错前提不成立**：声称"无 PRE_WRITE_CHECK"（有）、"然而×4/不过×3/与此同时×2"（实际正文 0/0/0）、"第6章第9段'你这个白痴'"（白痴 0 命中）、sensitive_words.txt 含傻逼/白痴/脑残（实际 3 词：台独/藏独/法轮功）
F805 P2 verified **review-sensitivity scenario 声称 novel-example.json 指定 `target_platform: "qidian"`**——JSON 无此字段（键：title/genre/language/status/core_concept/themes/target_word_count/ending_direction/mode）
F806 P1 verified **snapshots/chapter-025 为伪造快照**：manifest 占位 checksum（`sha256:abc123`/`xyz789`）、`files:` 引用不存在的 chapters/；truth 5 文件 4 个与顶层第1章 truth-*.md 逐字节相同（last_chapter:1），仅 current_state 改写；manifest 声称"第25章/~125,000 字/铁砧镇/田国栋第7章牺牲"与内容及 multi-chapter canon 矛盾；被 sequel-writing generative 当真实 25 章断点喂续写 agent（数据污染面）
F807 P1 verified **calibration 27 锚点全为手写 mock**：commit 14a672e/adbe2f8 自述 "Author 12 human-curated … original Chinese fiction prose excerpt"；锚点 lore（老周/黑石饼/锈泥巷/灵能催化剂/我替你还）在 shipped 语料零命中（真实 canon=田国栋/陈阿满）；违反 calibration README 自身 schema（"Never invented or hand-crafted"）；**G0.14 将手写锚点哈希锁进 deps.json**（本区按 g0.py 算法重算 `274e76d0…` 与锁值匹配=假基准固化进门禁）
F808 P2 verified **calibration 锚点 schema 违反之二**：arc-payoff 的 期待债务结算(3)/线索收束(3)/角色弧推进(3) 共 9 个锚点正文为**评论/概述体**（"本卷净偿还了读者期待…"）而非 README schema 要求的 prose excerpt（"the actual text under evaluation"）；伏笔兑现质量 3 个为叙述+评论混合体
F809 M verified **calibration README 过期自相矛盾**："No anchors are authored yet … contains only this README and `.gitkeep`"、"G0.14 locks the empty-set hash"——实际 27 个锚点存在且哈希被锁定
F810 P2 verified **calibration 锚点零单文件引用**：27 个锚点全部仅目录级/glob 引用（`calibration/resonance/`、`calibration/arc-payoff/`、`**/*.md`），无任何单文件路径引用；9 个 low 锚点无单文件引用
F811 P1 verified **arc/book-spine/book-strata/volume-summary-example（4 文件）自述非真实输出**（"G0.9 note: … not a hand-crafted mock … Real outputs will replace it"），却作为 scripts/lint_contract_fields.py `EXAMPLE_FIXTURES` 硬编码基准（T302 自洽闭环的基准本身是 mock）
F812 P2 verified **弧系列 fixture 章节范围互相矛盾**：arc-example `chapter_range: 1-12`、volume-summary-example `1-15`、book-strata-example `1-36`、book-spine `total_chapters: 15`——同为"第一大弧/第一卷"，章节数 12/15/36 三方冲突
F813 P2 verified **21 个零特定引用死 fixture**（全库活代码无引用）：chapter-2..10-draft（9，兼伪造 F800）、chapter-8-example、market-data-example.md、multi-chapter-example.md、parent-canon-example.md、truth-chapter_summaries/emotional_arcs/particle_ledger/character_matrix（4）、world-rules/locations/power-system/story-bible-example（4）。（T8 的 T812 计 28 个含 calibration 9 个 low 锚点——本区按"无任何特定引用"口径为 21；arc/book-spine/book-strata 仅归档 plan + lint 硬编码引用，另计 F811）
F814 P1 verified **19 个空目录（仅 .gitkeep）被 20+ scenario 引用**：truth/ 22、truth/character_profiles/ 6、characters/ 6、chapters/ 4、samples/reference-texts/ 3 等；G0.9 只校验路径前缀（g0_purity.py:33-38），不校验存在性/真实性 → generative agent 读到空目录
F815 P1 verified **import-analysis 链断**：import-analysis clean/bug-hunt scenario 声称 chapters/ 有 12 章源稿、import/analysis/ 产出 01_parse..08_state 8 文件——实际 chapters/ 空（仅 .gitkeep）、import/analysis/ 仅 03_world.md；03_world.md 声称"从第1-25章提取"并引用不存在章节的具体行号（第3章 L45-52 等）；bug-hunt expected-output 引用不存在的 02_characters.md/04_plot.md
F816 P2 verified **truth-* 与伪造快照双份逐字节重复**：truth-chapter_summaries/character_matrix/emotional_arcs/pending_hooks 与 snapshots/chapter-025/truth/ 对应文件 4 对逐字节相同（同一第1章数据两处存放，其中一处是伪造快照的一部分）
F817 M verified **chapter-draft-example 字数自述矛盾**：POST_WRITE_SELF_CHECK "~3100字"、chapter-summaries-example "~3100" vs audit-report-example "5403字" vs style-profile 第1章 "5444字"；audit 引文行号（行59）与正文实际行号（行68）偏移
F818 M verified **同 hook-ch1-001 内容双版本漂移**：pending-hooks-example "强制劳役或**灵能剥离**" vs truth-pending_hooks "强制劳役或**灵能僭越罪**"（同一钩子的罚则表述不一致）
F819 P1 verified **snapshot-manage bug-hunt scenario 植错前提与实际快照不符**：声称快照"contains only 8 of the 11 truth files"、manifest "claims 11 files archived"、缺失 3 个文件（pending-hooks-example/chapter-plan-example/author-intent-example）——实际快照有 5 个 truth 文件、manifest files 列 5 条、被指缺失的文件是顶层 example 而非快照文件；且 scenario 声称的"11 truth files in tests/fixtures/truth/"中多数路径重复且不属于该目录 → 植错测试无法按剧本执行
F820 P2 verified **genre-config-example.json 与真实输出结构漂移**：chapterTypes 键英文（battle/dialogue/exposition/transition/climax/politics）vs 真实（novel-output/xinghuo-ranqiong）中文（战斗/对话/谋略/人物/世界观/过渡）；示例多 tropeInventory 键；approval.reviewer 示例 human-partner vs 真实 pipeline-autonomous——示例非真实输出副本
F821 P2 verified **sensitive_words.txt 仅 3 词**（台独/藏独/法轮功），G6.12 全文章节敏感扫描近乎空转；scenario 声称的敏感词（傻逼/白痴/脑残）与文件不符（并入 F804 影响面）
F822 P2 verified **stop_words_zh.txt 格式违反自身 spec 且零消费者**：spec 要求"每行一个停用词"，文件为单行 47 词逗号分隔；src/tests/scripts 零引用（chapter_loop/volume_align 用硬编码停用词集）
F823 M verified **market-data/qidian-urban-fantasy-2026-06.md 声称真实榜单数据（弱证据）**：作品/作者为真实知名网文（我在东京当阴阳师/夜之命名术/诡秘之主 等），但阅读量/月票数字无快照源、无法仓库内独立核验
F824 P2 verified **market-data-example.md 自述"真实收集数据"但全库零引用（死 fixture）**；数据（月票 52,358 等）不可核验
F825 M verified **multi-chapter-example/ 5 章为弱证据"真实历史输出"**（正文互不相同、格式自洽、commit 6bab764 批量引入、round 已清理无 provenance）；索引 multi-chapter-example.md 死文件；字数声称（24,180）与实测 CJK 计数（4,851/5,329/5,042/4,953/5,583）偏差约 6% 但索引内自洽
F826 P2 verified **review-arc-payoff bug-hunt scenario 引用 fixture 中不存在的内容**：声称 outline-example.md "lists arc_beats"（outline 无 arc_beats）、truth-pending_hooks "mark hook-007 as resolved_this_arc"（实际只有 hook-ch1-001..003 全 PLANTED）、"hook-007 老周留下的半块黑石饼"（老周/黑石仅存在于手写锚点+scenario 闭环）→ 剧本与 fixture 断链
F827 M verified **parent-canon-example.md 死文件**：声称 chapters: 100 的 parent canon，仓库内无 100 章语料支撑；全库零引用（并入 F813 清单）
F700 P1 verified test_chapter_loop.py:457 G3-fail 测试用越界 step_index=16 构造恒真断言（无效测试）
F701 P1 verified test_parallel_steps.py 用 mock dispatch 验证"并发"，只断言调用次数，未验证并发性（已知 mock 掩盖站点）
F702 P1 verified test_g_reconcile.py 主动绕开已知 GR.2 解析 bug，测试与生产命名约定脱钩（masking）
F703 P1 verified test_scoring.py:510-546 单元测试直接改写仓库跟踪文件 tests/tiers/deps.json（xdist 竞态源）
F704 P2 verified tests/golden/ 空洞 + baselines/gate-outputs 陈旧且无 enforcement（T1108/T1109 同源确认）
F705 P2 verified lock-tool-hashes.sh 的 `_tool_hashes` 为死数据：96 键中 66 个已过期，且无任何 enforcement
F706 P2 verified test_g6.py:559-571 / test_g5.py:229-241 monkeypatch `jload` 触发 JSONDecodeError 测"不崩溃"，但断言仅 FAIL，未验证 JSON 合法
F707 P2 verified test_g4_escalation_review.py / test_g4_score_checkers.py 用字符串子串断言 JSON（`'"status": "PASS"' in result`），脆且测不到结构
F708 P2 verified test_retry.py 断言 `stop_reason is None` 于成功流，与实现语义可能不符（脆弱耦合）
F709 P2 verified test_docs_accuracy.py 四个 "File not yet created" skip 恒真恒跳（stale）
F710 P2 verified tests/unit/pipeline/test_context_assemble.py:163-169 / test_truth_embed.py:119-127 skip 为 masking（sentence_transformers 已装，降级路径永不可测）
F711 P2 verified test_chapter_loop.py / test_chapter_loop_full.py 大量 `# review-resonance`/步骤索引注释与真实表错位，索引文档漂移
F712 P2 verified test_state_machine_heal.py 对 MagicMock state 调 `_heal_current_step` 仅验证状态赋值，未覆盖真实状态对象序列化
F713 P2 verified test_docs_accuracy.py:82-104 三处 `if not doc_path.exists(): skip("File not yet created")` 已成死条件（文件存在），应删除
F714 P2 verified test_g4_signatures.py 断言 `"skill" in data or "status" in data`（or 短路弱断言）
F715 P2 verified tests/unit/gates/test_g7.py:178-204 test_g715 注释声称"audit_warnings 写回 summary.json"，但断言"summary.json 未被写"——注释与断言矛盾（G7 纯度变更未同步注释）
F716 P2 verified test_phase_runner.py 大量 `monkeypatch.setattr(phase_runner, "run_gate", ...)` 仅测状态机，G5/G2/G4 真子进程集成只靠 test_gate_cli.py（慢且部分跳过）
F717 P2 verified tests/unit/gates/g4/test_all_skills_parametrized.py 的 `test_returns_string_for_empty_file_list` 等 12 断言全部用空输入，只证明"不崩溃"，不证明业务规则
F718 P2 verified tests/unit/pipeline/test_e2e.py / test_cli.py 用 `_run` 直接调 `main(argv)`，未走真实 CLI 入口（argparse/exit 路径）
F719 P2 verified tests/unit/test_pytest_framework.py 的 `test_unit_marker_works`/`test_integration_marker_works` 为恒真冒烟（`assert True`）
F720 P2 verified tests/unit/skill_utils/test_calibration.py / test_confidence_routing_integration.py 只测 `calibrate_confidence` 单个 HitRate 组合，未覆盖 anchor 命中率驱动的真实校准数据来源
F900 P2 verified 2 个 skill 的 description 违反"只写触发条件"（foreshadowing-lifecycle / review-group-craft）
F901 P1 verified foreshadowing-lifecycle 正文声明产出 audits/chapter-N-foreshadowing.md，frontmatter 却声明 writes: []（未声明写入 + index 无此生产者）
F902 P2 verified foreshadowing-lifecycle 引用不存在的参考文件 lifecycle-states.md / hook-types.md
F903 P1 verified foreshadowing-resolve 的 Chase Power 公式/阈值三处不一致，且示例自相矛盾
F904 P2 verified review-anti-ai / review-motivation / review-pov 的 DEPRECATED 标注未传导：仍注册于 index/deps/executor_config/using-shenbi，正文仍自称活跃
F905 P1 verified review-sensitivity 双重调度：固定章节步骤 14 与 genre-circle 均调度同一 skill，真实配置下每章重复执行
F906 P1 verified genre-config.json 字段级 reads 漂移：prohibitions / climaxKeywords / prohibitedClimaxKeywords / povMode / maxClimaxPerChapter 被 4+ skill 读取但 schema 与真实文件均无
F907 P2 verified review skill 激活条件使用存档 spec 的数值维度 ID（维度 15/9/19/11/17/32），与运行时 named-key 机制脱节
F908 P2 verified character-design expand 模式读取 characters/**/*.md 未在 frontmatter 声明，且正文引用未注册文件 outline/chapter_outline.md、outline/three_act.md
F909 P2 verified market-radar 声明写 context/market-radar-decisions.json 但正文输出格式无任何 decisions 指令，且 index 显示零消费者
F910 P2 verified chapter-planning 实际产出未声明的 plans/chapter-N-plan-decisions.json（55 个中 38 个无效 JSON），index 无此条目
F911 P2 verified chapter-planning 字段级 reads 漂移：主角状态/当前世界局势/活跃线索/已完成章节/伏笔统计 在真实 truth 文件中不存在
F912 P2 verified sequel-writing 引用已废弃的 snapshots/chapter-NNN/ 目录概念（D20 已声明废弃，真实布局为平文件）
F913 P2 verified truth-sync 铁律 3"增量更新不重写整个文件"与 frontmatter updates mode: create_or_overwrite 矛盾
F914 M verified review-highpoint DOT 引用 maxClimaxPerChapter，正文检查项实际用 climaxKeywords/prohibitedClimaxKeywords（DOT 与正文不一致）
F916 M verified review-fanfic 激活/读取字段路径不一致：novel.json.mode vs novel.json.fanfic.mode
F917 M verified short-packaging 书名候选类型"情绪"不在 Step 1 类型表（直白/隐喻/钩子/系列）
F918 M verified genre-config 备份文件名不一致：铁律 4 用 .bak，输出格式用 .bak.YYYYMMDD
F919 M verified review-sensitivity 缺陷证据格式句残缺（"遵循  定义的四要素格式"缺主语/引用）
F920 M verified sensitive-words.md 引用已废弃 review-anti-ai 协作，且引用 genre-config.json.genre（不存在，实为 novel.json.genre）
F921 P2 verified using-shenbi 未传导 MERGE-2：4 个 group auditor 完全缺席触发表，仍路由到已废弃 skill；docs/specs 路径已失效
F923 M verified anchor-curate / escalation-review 缺少 anti-rationalization 表（其余 21 个 skill 均有）
F950 P1 verified DEPRECATED skill 仍登记在 deps.json 调度相位 + executor_config + 审计文件写所有权（deprecation 零 enforcement，"Do not dispatch" 无契约效力）
F951 P2 verified context-composing 写契约断链：主产物 context/chapter-N-context.md 无任何 skill 声明写，frontmatter 只声明 decisions.json；近章结尾检查所需 chapter-(N-3..N-1).md 未入 reads
F952 P2 verified style_profile.md 字段级 reads 漂移：4 个消费 skill 引用旧节号（11. 综合画像 / 6. 修辞模式 / 9. 对白占比），style-learning 现输出仅 8 节且无对白占比 → 每次 dispatch 触发 field_filter_no_match WARN + 全量 escape hatch
F953 P1 verified memory-distill 契约 vs 正文漂移：L4/L5 流程读 author_intent + book_spine + arcs/arc-N.md 均未声明 reads，且 book_spine 仅 updates（create_or_overwrite）无 reads → L5 滚动复核在 dispatcher 契约下拿不到书脊原文（盲写风险）
F954 P2 verified book_spine.md 双更新者 + updates 用 create_or_overwrite 模式错配（memory-distill 与 score-stratum 均整写同一 L5 声明文件，正文却声称"只更新数据字段"）
F955 P2 verified snapshot-manage 回滚写面未声明：回滚覆盖项目文件（truth/ + chapters/ + world/ 等）但契约 writes 仅声明 snapshots/chapter-NNN/*
F956 P2 verified foundation-review reads 缺 genre-config.json（评分程序 §六 tropeInventory 对照源）与 truth/book_spine.md（前置文件验证必需），且正文重复两个"## 输出格式"节
F957 P2 verified review-group-factual description 违反触发条件性契约（描述"做什么/机制"而非"何时用"，lint 盲区放行）
F958 P2 verified review-group-factual 正文 Contract YAML 与 frontmatter 矛盾（writes↔updates 互换），且正文引用陈旧代码行号 chapter_loop.py:1090-1168
F959 P2 verified volume-consolidation 写模式与正文矛盾（volume_summaries.md create_or_overwrite vs "追加"）+ 重复"## 输出格式"节 + 执行步骤编号重复
F960 P2 verified anti-detect 触发输入（anti-ai 审计报告）未入 reads，genre-config.json 声明读而正文零使用
F961 P2 verified short-drafting 字数下限依赖 novel.json.target_word_count 但 novel.json 未入 reads
F962 M verified 三个 review skill 的"缺陷证据格式"引用主体缺失（"遵循  定义的四要素格式"空白）
F963 M verified ngram-methodology.md 内部数值矛盾：示例 +15.9/+16.1/+17.9% 标注为满足 ">0.20" 阈值；6 字 n-gram 滑动窗口示例为 5 字窗口且串内容错误
F964 M verified spinoff-violations.md §7"所有违规统一为 error（无 warning）"与 SKILL.md 输出模板 WARNING 行矛盾；伏笔隔离要求 pending_hooks 每钩子有 scope 字段但种植模板无此字段
F965 M verified worldbuilding truth 文件数自相矛盾（"全部 11 个" vs 列出 12 个）+ 重复"## 铁律"节 + DOT "Read genre config" 对应文件未入 reads
F966 M verified description 含实现/执行注记（"runs in an independent agent"；score-stratum 中英混排）——description 纯度系统性瑕疵
F967 M verified style-learning 输出头"纯统计（零 LLM）"与正文"LLM 转散文"矛盾；style-polishing DOT "prohibitions" 未在 reads 字段声明
F968 M verified chapter-drafting 黄金三章规则依赖 novel.json.golden_opening_chapters 但 novel.json 未入 reads（anti-ai-reference.md 间接引用）；3 个 .gitkeep 零字节遗留
F969 M verified decisions.json 声明在 writes 但正文零指令（3 个 skill 均如此），dispatcher 只注入通用 schema 注记——decisions 内容契约悬空（Z11-01 无效 decisions 的 Z8 侧证据）
F1000 P2 verified shenbi-chapter-revision 修订模式词表三处矛盾（SKILL.md 3 模式 vs revision-modes.md 6 模式 vs 顶部 DOT rewrite/rework）
F1001 P1 verified shenbi-drift-guidance 契约声明写 truth/drift_guidance.md 但正文从未定义其内容；pipeline step output 指向该文件而真实项目从未产生；audit_drift.md append_dedup 与"合并重写为权威版本"语义冲突
F1002 P1 verified shenbi-state-settling 未声明 reads（character_matrix.md）与未声明写（characters/protagonist.md arc_log），Write-Protection 规则在 dispatcher 过滤下无法成立
F1003 P1 verified shenbi-state-settling 更新模式三处不一致：frontmatter append_dedup vs 更新规则表 replace vs Update Mode Rules 缺失 particle_ledger/subplot_board
F1004 P1 verified 7 个 DEPRECATED skill 全链接线未断："Do not dispatch" 无 enforcement；deps.json 前置契约与 pipeline 步骤表矛盾
F1005 P2 verified shenbi-review-resonance reads 字段 style_profile.md [11. 综合画像 / 6. 修辞模式] 与真实 style_profile.md 章节号不符（实际 8. 综合画像 / 5. 修辞模式）
F1006 P2 verified 激活条件与真实 genre-config schema 漂移：数字维度号 / eraResearch / eraConstraints 均不存在于真实 auditDimensions
F1007 P2 verified 4 个 builder/planner skill 的"append 语义"正文与 frontmatter create_or_overwrite 模式冲突
F1008 P2 verified shenbi-faction-builder 正文输出 world/faction-relations.md（文件 2），契约仅声明 updates world/factions.md —— 未声明写
F1009 P1 verified review-group-character / review-group-plan 的 description 描述实现而非纯触发条件（含 "in one call"、"dispatches via parallel_dispatch.py"），且无 "Use when" 触发条件
F1010 P2 verified review-group-character / review-group-plan 正文内嵌 "Contract" YAML 块与 frontmatter 契约 writes/updates 互换（writes: [] + updates: 4 文件 vs frontmatter writes: 4 文件 + updates: []）
F1011 P1 verified shenbi-book-spine-init 正文使用 characters/protagonist.md + world/rules.md 但契约 reads 未声明
F1012 P2 verified shenbi-chapter-pattern 熵评级阈值内部矛盾 + 13 模式与 genre-config chapterTypes 词表不匹配
F1013 P2 verified shenbi-pacing-design 内部矛盾：四拍范围 / CONSTELLATION 多套范围 / 场景类型 6-8 vs 恰好 8 / 单调性阈值统一 vs 分类型
F1014 P2 verified shenbi-volume-outlining 内部矛盾：铺垫段占比 10-20% vs 15-25%；跨卷钩子 ≥1（铁律/核心设计）vs ≥3（输出/检查/汇总）
F1015 P2 verified shenbi-foreshadowing-track 内部矛盾：字段分工（last_reinforced/subtlety 归 state-settling）vs DOT "Update last_reinforced / subtlety"；Cross-Volume Bridge Tracking 引用不存在文件 foreshadowing_ledger.md
F1016 P2 verified foreshadowing-track / foreshadowing-recall 的 dict-form reads 字段与真实 truth 文件结构不符（活跃伏笔/伏笔时间线/已完成章节 不存在）
F1017 P2 verified 缺陷证据格式引用缺失/死引用：review-character 空白引用；review-pacing 引用不存在的 skills/_shared/REVIEW_EVIDENCE.md
F1018 P2 verified 多处 "spec §X.Y" 引用无命名文档，唯一可匹配文档为归档 plan（positive-quality-gates）
F1022 P2 verified shenbi-state-settling/truth-files-reference.md 文件清单过期不完整（遗漏 9 个契约中 truth 文件）且"增量更新"原则与 replace-mode 冲突
F1019 M verified shenbi-score-volume 铁律 3 "从 book_spine.md (L5) 读 themes/master hooks" 行号引用过期：L5 是 frontmatter 结束符，themes 实际在 ~L17-21、master hooks 在 ~L31-42
F1020 M verified shenbi-chapter-pattern 熵计算输出模板 "第A-Ⓣ章" 全角符号误用（Ⓣ 应为半角 T）
F1021 M verified shenbi-book-spine-init HARD-GATE 语句重复（"（worldbuilding + character + story-architecture + volume-outlining）完成后、逐章循环开始前执行。"同一分句重复两次）
F1100 P2 verified D2 漂移：deterministic spec :18 引用 `2026-06-22-positive-quality-gates.md:7`，实际文件为 `...-gates-design.md`（缺 `-design` 后缀），且 :7 非分层表（分层表在 :63）
F1101 P2 verified D2 漂移：deterministic spec :102 引用 `dispatch_helper.py:1030-1037` 为 append_dedup caller-责任文档，实际该注释在 :1059-1065
F1102 M verified output-side spec :52 声称 "genre circle 加 review-character"，但 GENRE_ACTIVATION_MATRIX（audit_layer.py:44-53）无 character 键（character 属 core-circle）
F1103 M verified output-side spec :36 常量名笔误 "MAX_DISPATCH_DETRIES"（实际 `MAX_DISPATCH_RETRIES`）
F1104 P2 verified basedpyright-overrides.md:7,58 描述 `src/shenbi/skill_utils` executionEnvironment + "mirrors mypy ignore_errors = true for skill_utils"——实际 pyproject basedpyright 仅有 tests env，mypy overrides 无 skill_utils 条目
F1105 M verified specs/INDEX.md:4 "活跃 spec 数：14" vs 磁盘 15 个活跃 spec；总纲 catalog `2026-08-14-full-project-audit-design.md` 未登记进 INDEX（F0-04 家族）
F1106 M verified plans/INDEX.md:4 "已归档 65"、:23 "63 个已完成的 plan" vs 实际 plans/archive 67 个文件（F0-04 家族，但 F0-04 只覆盖 specs INDEX）
F1107 M verified overview.md:141,176 与 concepts.md:29,31 声称 "15 种 kind 值"，truth-files.yaml 实际 16 种（多 benchmark）
F1108 M verified CHANGELOG.md:18 "7-gate validation system (G0-G7)"——G0–G7 是 8 道门（off-by-one）
F1109 M verified CHANGELOG [Unreleased] 仅列 P-1.E——PR #19-26、novel pipeline、gates、contract 单信源、decisions-sidecar、CI 优化等全部未记录
F1110 M verified CODE_OF_CONDUCT.md:39 遗留占位符 `[INSERT CONTACT METHOD]`
F1111 M verified CONTRIBUTING.md:44 声称 mypy overrides "removed by Plan 1 and Plan 4"——pyproject.toml 仍有 4 个 overrides（含 numpy ignore_errors=true）
F1112 M verified CONTRIBUTING.md:80 声称 "an ungenerated change fails the plugin-manifest-freshness job"——.codex-plugin/ 已在 b73edd0 移出 git 并 gitignore，`git diff --exit-code -- .codex-plugin/` 恒空（guard 失效）
F1113 P2 verified README.md:45 `just pipeline-init outline-example.md ./my-novel --auto` 不可执行——justfile pipeline-init recipe 不接受/不转发 `--auto`，just 报错
F1114 M verified outline-example.md:7 目标字数 100000（10 万）vs goal-prompt.md:3,71 / concepts.md:39 "20 万字"（20 万）——同星火燃穹字量不一致
F1115 M verified specs/INDEX.md:80 "97 个已完成 spec" vs 实际 98 个 spec .md 文件（90 顶层 + 8 子目录）；:4 "已归档 99" vs 100 总文件/91 顶层条目（F0-04 精确化）
F1116 M verified command-to-give.md:1 引用 `docs/superpowers/plans/2026-06-11-test-framework.md`，该 plan 已归档至 `plans/archive/`（路径断链，F0-05 同族）
F1301 P1 verified 章节头契约零符合：56/56 无 `# Chapter N:` 头
F1302 P1 verified 6 章无 META 块 + ch40 用 `## META` YAML 替代 `<!--META-BEGIN-->`
F1303 P1 verified DEBUG_USE_MANUAL_CREATE.md 暴露手动创建路径：decisions.json 的"Extra data"来源
F1304 P1 verified Z11-01 根因确认：83/145 decisions.json 无效，成因=写路径绕过 + G4 从未收到 .json
F1305 P1 verified 57/145 可解析但 schema 违反：producer 模板零 schema 编码
F1306 P2 verified revision-decisions 触发 34/56 但 `_ensure_revision_decisions_exists` 兜底写入的"minimal"文件仍违反 schema
F1307 P1 verified 根 `truth/`（bridge_tracker.md + character_matrix.md）与 truth-files.yaml 三源分裂
F1308 P2 verified staging truth 与正式 truth 内容不一致（pending_hooks 9886 vs 4171）
F1309 P1 verified progress.json 内容空壳：仅 scorer 字段，无任何进度
F1310 P1 verified pipeline 永不完成状态实证：closure=pending、closure_step=0、total_chapters 缺位
F1311 P2 verified audit_reports 状态记录与磁盘 117 个审计文件脱节（resonance+review-summary 全缺）
F1312 P2 verified 双 resonance gate-marker：`G4-review-resonance-generative.json` 为验证运行写入的污染 marker
F1313 P1 verified token ledger 缺席：cost/token-ledger.jsonl 不存在，F302 死接线预测验证
F1314 P2 verified audits 722 无内容重复，但 texture 维度配置=true 而磁盘 0 文件 + sensitivity 双发（F329 实证）
F1315 P2 verified ch56 审计不完整：6/13 维缺失（dialogue/motivation/resonance/review-summary/sensitivity/world-rules）+ ch56 无 audit_reports 记录
F1316 P2 verified config-change-log.jsonl 单条无操作条目（old=true/new=true）且时间戳晚于运行结束
F1317 P2 verified write-audit/trace.jsonl 记录与 GATE_FAIL 语义一致但 root truth 残留仍落盘
F1318 M verified .hypothesis "Examples ARE committed" 声明失效：43 个 example 全未跟踪（F861 复验+计数漂移）
F1320 M verified DEBUG_USE_MANUAL_CREATE.md 计数漂移（1226 vs 1229；marker 21 vs 22；snapshots 52 vs 51）
F1321 P2 verified plan-decisions 全部滞留 staging（55 个），plans/ 零 decisions；ch54 缺 plan-decisions
