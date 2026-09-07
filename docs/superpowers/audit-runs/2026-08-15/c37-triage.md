# C37 分桶裁决表（R0 · 2026-09-07 按当前 main 现判）

> 硬闸：T2-T6 逐行执行；表外删除禁止合入。行首锚定 `| F###`/`| T###`（行数验收用）。
> 桶：wire=接线/移交 · delete=本 spec 删除 · defer=显式延期 · already-fixed=已由其他 spec 修复/主张失效
> 执行者 T2-T6 对应 plan `docs/superpowers/plans/2026-09-07-c37-dead-code-enforcement.md`

| Finding | 形态摘要 | file:line（当前 main） | 桶 | 执行者 | 备注 |
| F108 | error_guidance 模块零消费者、doc_url/脚本引用不存在 | src/shenbi/error_guidance.py:24-35 | delete | T2 | 与 F109 整删 |
| F109 | recovery 模块零运行时消费者 | src/shenbi/recovery.py 全文 | delete | T2 | 仅 error_guidance 字符串键引用 |
| F110 | 7 异常类从未 raise/except | src/shenbi/exceptions.py（ScoringError/ScoringRejectError/MigrationError/DefectApplicationError/RegistryCorruptError/ConfigurationError/SubAgentUnavailableError） | delete | T2 | 仅死模块字符串键提及 |
| F118 | scoring._phase 死参（--phase 赋值从不使用） | src/shenbi/scoring.py:433,443 | delete | T4 | |
| F226 | no_op_behavior: skip_write 零消费 + skip_paths 参数从未被喂养 | src/shenbi/pipeline/dispatch_helper.py:1428+ 及 skills frontmatter | delete | T3 | 契约面同步 `just generate` |
| F230 | from_markdown 不填 chapter_sequence，3-window 校验不可达 | src/shenbi/contracts/skills/pacing_design.py:67-72,82,131 | delete | T2 | 删不可达校验与透传；G4 no_beat_data 留空表 skip 路径 |
| F243 | OutputKind.EPHEMERAL 死值 | src/shenbi/dispatcher/executor.py:87 | already-fixed | — | 已接线（#33 时代），注释在 :75 |
| F313 | build_index 返回值即弃（仅 log） | src/shenbi/pipeline/chapter_loop.py:1174 | delete | T3 | 已删 _maybe_rebuild_truth_index 整函数+调用（audit-T3 I-1：留空壳即假防线）；build_index 本体有读者保留 |
| F314 | volume_align 整模块死 | src/shenbi/pipeline/volume_align.py:52 | delete | T3 | 直测随删 |
| F315 | CONDITIONAL_STEPS 死表（零消费；_get_last_drift_chapter 级联随删） | src/shenbi/pipeline/chapter_loop.py:439 | delete | T3 | |
| F316 | _archive_chapter_state + compact_pipeline_state 零调用 | src/shenbi/pipeline/state.py:435,459 | delete | T3 | |
| F319 | review_checklist split 段死面 | src/shenbi/pipeline/review_checklist.py:426 | already-fixed | — | 重构后为活 frontmatter 解析，原主张形态不复存在 |
| F321 | 串行审计分支不可达 | src/shenbi/pipeline/chapter_loop.py:2891+ | already-fixed | — | MERGE-2 重构后串行路径是 C32 WRITE_SHARED 真实路径，主张失效 |
| F325 | _verify_truth_integrity 返回值被忽略 | src/shenbi/pipeline/cli.py:755,856 | wire | T4 | 接线 fail-fast：非空即非零退出 |
| F343 | genre-config 死路径 config/genre-config.json + 仅测试调用 | src/shenbi/pipeline/dispatch_helper.py:228 | delete | T3 | 与 T1612 同函数一并删 |
| F345 | dispatch_skill timeout 形参从不使用 | src/shenbi/pipeline/dispatch_helper.py:2707,2807 | delete | T4 | 删形参；体内用 _compute_dispatch_timeout |
| F346 | snapshot_retention 死配置旋钮 | tests/unit/pipeline/test_state.py:130 | already-fixed | — | 随 #26 移除，测试已断言不存在 |
| F356 | SharedAuditContext.chapter_summary 零填充零读取 | src/shenbi/pipeline/audit_context_cache.py:21,39 | delete | T3 | 模块本体已接线，仅删死字段 |
| F366 | %5 物化节拍永不触发 | src/shenbi/pipeline/chapter_loop.py:1050-1053 | already-fixed | — | #37 F630 裁决 b 移除 |
| F368 | retry_feedback 永不清理（清理逻辑在死 compact 内） | src/shenbi/pipeline/chapter_loop.py:3154,3269 | defer | T6 注记 | C33 已落全局预算语义；清理时机需产品裁决，复活条件=C33 后续复审 |
| F378 | _validate_state_consistency 死线+注释谎称 cli.py 调用 | src/shenbi/pipeline/state.py:521 | delete | T2 | 直测随删 |
| F427 | 三个复制粘贴 checker | src/shenbi/gates/g4/score_arc.py + score_stratum.py + score_volume.py | delete | T4 | 合一 g4_scoring_sections（原 3 文件删除） |
| F471 | ProgressDoc/SummaryDoc 零使用 | src/shenbi/contracts/schemas/state.py:19,25 | delete | T3 | |
| F512 | 不可达 return 2 | src/shenbi/cost/report.py:137 | already-fixed | — | 目录守卫后已可达 |
| F611 | RHETORICAL 死正则 | （全仓零命中） | already-fixed | — | #33 dead-face cleanup 已删 |
| F622 | escalation/foreshadowing_recall CLI 零引用（escalation 半面已接线） | skill_utils/foreshadowing_recall（零生产引用） | delete | T3 | 删 foreshadowing_recall helper；escalation 保留 |
| F631 | trace compact() 零生产调用 | src/shenbi/trace/compact.py（仅测试） | delete | T3 | 触发引擎已由 #33 接线，此死线删 |
| F632 | migrate_from_progress 零调用 | src/shenbi/trace/__init__.py:6 导出、零调用 | delete | T3 | |
| F633 | drift 触发器组零调用（原主张） | triggers.py:234,297 | already-fixed | — | #33 已接线 check_triggers/run_triggered_skills |
| F634 | escalation 触发器组零调用（原主张） | cli.py:227,231,255 | already-fixed | — | #33 已接线 |
| F635 | drift 接线面（原主张） | src/shenbi/pipeline/chapter_loop.py:89 等 | already-fixed | — | #33 已接线 |
| F636 | escalation 接线面（原主张） | src/shenbi/pipeline/cli.py:300 | already-fixed | — | #33 已接线 |
| F641 | records 半数导出零消费（执行修正：serialize_records 有生产消费 writer.py:187/parser 内部——保留；仅 is_idempotent 零消费） | src/shenbi/records/parser.py:76 | delete | T3 | 仅删 is_idempotent 及导出 |
| F642 | text 半数导出零消费（PUNCTUATION_TOKENS 除外——count_punctuation 消费 .items()；Token/_get_tokenizers 随 tokenize 级联删） | src/shenbi/text（count_words/tokenize/Token） | delete | T3 | 保 count_punctuation + PUNCTUATION_TOKENS + find_terms |
| F706 | g4/conftest 两死 fixture | tests/unit/gates/g4/conftest.py:13,27 | delete | T4 | grep 确认零引用后删 |
| F793 | 死函数被直测模式（_should_run_recall 已删、_should_run_drift 仍在） | src/shenbi/pipeline/chapter_loop.py:1774 + tests/unit/pipeline/test_adaptive_triggers.py:16 | delete | T3 | 模式治理整体移交 C14（R4/T6） |
| F886 | genesis-context/*.md 写后零消费 | src/shenbi/pipeline/cli.py:497-500 | defer | T2 注记 | 种子断流是产品缺陷非卫生问题；写点注释如实标注，内容恢复待产品裁决/后续 spec |
| F903 | G0.13 工具哈希承诺静默失效 | src/shenbi/gates/g0.py:188-226 | already-fixed | — | #54/C16 以 G0.14 落地执法 |
| F1027 | lint_status_strings 死参/CWD 面 | tools/lint_status_strings.py:165,168 | already-fixed | — | #34 已修复 |
| T301 | check_fields_exist 零生产调用仅直测 | src/shenbi/gates/g1.py:106 + tests/unit/gates/test_g1_fields.py | delete | T4 | |
| T1506 | legacy.py 命名 + re-export shim 残留 | src/shenbi/contracts/legacy.py + contracts/__init__.py:49 | delete | T4 | 改名 + 删 shim，全仓 32 引用点（7 src/23 tests/2 tools）+ import 变体 |
| T1605 | truth-index 重建即弃/零读者（读者半面已修） | src/shenbi/pipeline/chapter_loop.py:1174 | delete | T3 | 与 F313 同动作：删即弃调用；CLI rebuild + query_index 读者保留 |
| T1612 | _genre_config_cache 死缓存（每章仅一击、仅测试调用） | src/shenbi/pipeline/dispatch_helper.py:220-226 | delete | T3 | 与 F343 同点一并删 |

## 桶计数（核对）
already-fixed 13（F243/F319/F321/F346/F366/F512/F611/F633/F634/F635/F636/F903/F1027——F633-636 计 4 行）+ delete 27 + wire 1（F325）+ defer 2（F368/F886）= 43 ✓
（执行中改行须同步本表与 spec-deviations；commit 9bbc862b 消息中 "12 already-fixed" 为笔误，实为 13）
