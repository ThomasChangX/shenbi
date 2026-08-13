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
| F305 | 审计严重度裸子串检测（"BLOCKING"/"FAIL"）产生误报 | error | P2 | 见 Z3.a.md#F305 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | open |
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
| F324 | 生产 volume_map 中文格式与全部解析器不匹配：卷边界系统、closure 转换、卷上下文、计划骨架全线静默失效 | error | P0 | 见 Z3.review.md#F324 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F325 | step 16 revision 双重门控矛盾：`_any_audit_has_findings` 扫描旧式审计文件名，BLOCKING 路由后 revision 仍被跳过（审计 BLOCKING 永不修复） | error | P1 | 见 Z3.review2.md（误报，已撤销）| 复核发现：group contract writes 声明旧式路径、磁盘 722 旧式审计文件、BLOCKING 必命中 | 实证 | 误报撤销 | — | deep-read | false-positive |
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
| F620 | `_check_linguistic_drift` 唯一调用点用宽泛 `except Exception` 吞掉 DriftEscalationError → "ESCALATE 暂停 pipeline" 契约在任何路径下永不生效 | error | P1 | 见 Z6.review2.md#F620 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F621 | compute_pattern 熵对词表外 pattern 只算分母不算分子 → 互异章节被评"严重单调" | error | P2 | 见 Z6.review2.md#F621 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F622 | recall_overdue_hooks 对 str 类型 last_reinforced/max_distance TypeError 崩溃（F610 之外的独立类型失败模式） | error | P2 | 见 Z6.review2.md#F622 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F623 | AI_MARKERS "不是…而是" 用单省略号字符字面量 → 真实文本"不是……而是"（双字符）恒不命中 | error | P2 | 见 Z6.review2.md#F623 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F624 | plugins/master.json skills 清单与 skills/ 目录漂移（59 vs 74，15 个 skill 未列）+ generate.py 无任何 skills 校验 → 静默不发布 | doc drift | P2 | 见 Z6.review2.md#F624 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F625 | versioning.migrate_to_current 缺迁移函数时 `_identity` 回退 → while 循环永不前进 → 无限循环挂死 | error | P2 | 见 Z6.review2.md#F625 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F626 | check_linguistic_drift_trigger（第 4 漂移触发点）死导出：HARD/ESCALATE 从未接入 drift-guidance | dead code | P2 | 见 Z6.review2.md#F626 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F628 | segment_sentences 与 segment_paragraphs 句数口径不一致（"；" 只计入段落句数）→ 同一报告自相矛盾 | error | P2 | 见 Z6.review2.md#F628 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F629 | revision_routing.verify_preservation 无生产调用方：§5.3 再生保留校验器实现+测试但未接线，保留保障仅靠 LLM prompt | dead code | P2 | 见 Z6.review2.md#F629 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F513 | 写审计快照根错位：`dispatch_with_write_audit` 快照 `PROJECT_DIR`（框架仓库根）而非 `round_dir` | 接线错误 | P1 | 见 Z5.review.md#F513 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F514 | d1-06 重生成声明与工件矛盾：on-disk d1-06 仍为污染版（32.89%/cost=0%），F508 的"已重生成 85.16% 版本"不实 | 审计工件质量 | P2 | 见 Z5.review.md#F514 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F515 | `_matches_declared` 不匹配契约原生 glob 写模式（`truth/*.md`）→ 已声明写被误报"未声明写入" | 审计正确性 | P2 | 见 Z5.review.md#F515 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F516 | 初审误判 snapshot.py:43-45 为"无 `*` 写入"死代码：契约实际存在 glob 写模式 | 初审覆盖处置错误 | M | 见 Z5.review.md#F516 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F335 | audit_context_cache 用补零章节文件名（chapter-001.md），生产为不补零 → chapter_text 恒空 | error | P2 | 见 Z3.review2.md#F335 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F336 | state.to_dict/from_dict 丢失 step_timings（F332 同根不同面） | error | P2 | 见 Z3.review2.md#F336 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F337 | check_triggers 在 total_chapters=0 时 book_closure 恒 True（chapter >= 0），仅被调用方守卫掩盖 | error | P2 | 见 Z3.review2.md#F337 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F338 | 审计级联跳过（Spec 8 Fix 8）无数据源：并行波不写 per-skill audit_results → _should_skip_audit 恒 False | optimization | P2 | 见 Z3.review2.md#F338 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F339 | 并行波审计信号失真且无消费方：blocking_found 由 consolidate(stdout) 计算（API 路径恒 0）、audit_reports 记录不存在的 group-*.md、review-summary.md 恒报 0 问题 | error | P2 | 见 Z3.review2.md#F339 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F340 | cmd_review 的 REJECT 未实现 spec §2.7 重做/回退语义（全类型缺失）；genesis-complete reject 后 pipeline 卡死 | error | P1 | 见 Z3.review2.md#F340 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F341 | --auto 模式下并行 post-draft 仍每章无条件设 STATE_SETTLE checkpoint（state_settle_review_required 未检查）→ 自动化运行每章必停 | error | P1 | 见 Z3.review2.md#F341 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F342 | volume_snapshot_pending / add_audit_result / increment_retry / reset_retry 生产死代码 | optimization | P2 | 见 Z3.review2.md#F342 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F431 | jload 的 ValueError（合法但非 dict 的 JSON）在 G1.6/G3.x/G5.1/G7.x/read_genre_config/gate_manifest 未捕获 → 多门崩溃（F419/F421 家族扩展） | error | P2 | 见 Z4.review2.md#F431 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F432 | G7.1b 反向覆盖以 ALL_SKILLS(74) 为全集，5 个无 T1 scaffold 的 group/lifecycle 技能永不可达 → 完整 round 的 G7 恒 FAIL；G0.10/G_DISPATCH 同根因 | error | P1 | 见 Z4.review2.md#F432 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F433 | g4_chapter_drafting 主角在场检查用坏掉的 project_root（skill-output 爬升）而非已传入的 project_dir → 生产布局恒用默认名 ["林烽","他"]，检查形同虚设或误报 | error | P2 | 见 Z4.review2.md#F433 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F434 | g4_state_settling 参数 agent 名单用单字符子串匹配（"冷"/"光"）→ 真实 fixture 误报 FAIL | error | P2 | 见 Z4.review2.md#F434 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F435 | G0.12 exempt_skills 读取后从未使用 + 注释声称的 "no skill returns UNIMPLEMENTED" 校验未实现（G0.12 恒 PASS 空转） | error | P2 | 见 Z4.review2.md#F435 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F436 | G6.7 planted_chapters 死变量 | optimization | M | 见 Z4.review2.md#F436 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F437 | G5.5 用 except Exception → WARN 吞掉 G4 重跑的一切异常（含 gate 崩溃）→ G4 回归检查 fail-open | error | P2 | 见 Z4.review2.md#F437 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F438 | chapter_drafting 转折词阈值 1/1000（≥5 兜底）vs SKILL.md 契约 1/3000（3 倍放宽，代码注释自认但 SKILL 未同步） | docs | M | 见 Z4.review2.md#F438 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F439 | g4_style_polishing 字数比检查死路：其输入 .bak 只由 G1.4 为 BACKUP_SKILLS（truth updaters）创建，style-polishing 不在其中 → G4.sp.word_ratio 永不执行 | error | P2 | 见 Z4.review2.md#F439 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F123 | capability_fs.CapabilityFS 无任何生产接线：支柱五"读 provenance 运行时兜底"仅测试消费，模块为生产死代码 | dead-wire/未接线 | P2 | 见 Z1.review2.md#F123 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F124 | phase_runner CLI 无位置参数校验：缺参 → IndexError traceback；flag 被解析为位置参数 | error | P2 | 见 Z1.review2.md#F124 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F125 | command-to-give.md:48 引用不存在的 tests/dispatch-subagent.sh：PR-20 迁移后执行协议断链 | doc↔code drift | P2 | 见 Z1.review2.md#F125 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F126 | scoring.py 批次评分 scored_by 误标 "interactive"：非交互文件评分且未传 --subagent 时审计元数据失真 | error | M | src/shenbi/scoring.py（见 Z1.review2.md#F126） | 文档化命令不带 --subagent 时默认标 interactive | read 确认 | 审计元数据失真 | 按调用方式标注 | deep-read | verified |
| F127 | status.py ScoringStatus.OK / ScoringStatus.UNIMPLEMENTED 死成员：单一定义词汇表中 2/5 成员无任何 emit/read 站点 | error | M | src/shenbi/status.py（见 Z1.review2.md#F127） | 词表扩展后未清理 | grep 无消费 | 词汇表死成员 | 删除或接线 | deep-read | verified |
| F227 | executor.dispatch G1/G2 在技能执行前校验尚不存在的输出——PR-20 翻译门序回归，文档化 first-novel 流程第一步即失败 | 漏报（功能错误/回归） | P1 | 见 Z2.review2.md#F227 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F228 | derive_output_files/G2 不展开 writes/updates 中的 glob → 9 技能 G2.1 恒失败 | 漏报 | P2 | 见 Z2.review2.md#F228 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F229 | derive_file_type 单一 file_type 批处理与异构输出不兼容：(a) chapter 型技能非散文输出误套章节规则；(b) decisions 型技能 .md 散文静默漏套 G2.6-2.10 | 漏报（校验洞+误拒） | P2 | 见 Z2.review2.md#F229 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F230 | fields.py `_filter_json` 不做规范化（裸 `k in fields`），与 `_filter_md` 的 canonical rule 不一致——复核轮"md 与 json 同构"断言为误 | 漏报（一致性缺陷） | P2 | 见 Z2.review2.md#F230 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F231 | genre-config 消费侧引用 povMode/sensitivityFlags，但模型/fixture/SKILL.md 规则表/OWNERSHIP 全源无此键——review_checklist 恒空默认、review-group-character 字段过滤恒 escape hatch | 漏报（契约-消费漂移） | P2 | 见 Z2.review2.md#F231 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F232 | decisions.py P2.5 rationale 空串/纯空白绕过 REQUIRED 规则 | 漏报（校验洞） | P2 | 见 Z2.review2.md#F232 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F233 | ownership.py record_create 的 write_keys 从不校验新增记录键集——plant 可写任意键，_HOOK_KEYS_NEW_RECORD 声明 dead | 漏报（审计盲区） | P2 | 见 Z2.review2.md#F233 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F234 | 整文件删除 owned 文件零违规——check_write_ownership 忽略 FileChange.status | 漏报（审计盲区） | P2 | 见 Z2.review2.md#F234 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F630 | revision_router.DEFAULT_RESONANCE_FLOOR=50 与单源阈值 65 漂移（E11 缺陷类复活） | 跨文件状态一致性 | P2 | 见 Z6.review3.md#F630 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F631 | config 治理规则 1 与 G0 均用 `is False` 严格相等：`0`/`null`/`""` 等 falsy 值绕过 rationale 与 G0 检查且实际禁用审计 | 治理绕过 | P2 | 见 Z6.review3.md#F631 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F632 | linguistic_drift severity 阶梯硬编码 30/50/100 与 thresholds.py 单源阈值重复且不一致风险（"single source of truth" 声明被违反） | 跨文件状态一致性 | P2 | 见 Z6.review3.md#F632 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F633 | segment_paragraphs docstring 声称支持单换行分段，实现只按空行分割 → 单换行章节被当作 1 个巨段落且换行被计为句末 | 文档↔代码漂移 | P2 | 见 Z6.review3.md#F633 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F634 | compute_linguistic_metrics / compute_stats 把 pipeline 自产的 META 指令块当章节正文统计 → 密度稀释 + 指令文本进计数 | 统计口径 | P2 | 见 Z6.review3.md#F634 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F635 | 整个 config 治理层（update_genre_config）零生产调用：docstring "Every change flows through" 为假，genre-config 由 skill 直写，audit trail 仅一次人工修复产物 | 死代码/未接线 | P2 | 见 Z6.review3.md#F635 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F636 | detect_drift 把任意指标 0→正值映射为 6.0x 偏差 → 基线为 0 的指标首次出现即触发 is_drift=True（severity≥WARN） | 边界触发语义 | P2 | 见 Z6.review3.md#F636 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F517 | `audit_writes` 将 pending_hooks 专属解析无差别应用于全部 watched .md：非 truth .md 含 `## 活跃伏笔` 表 → 假 drift GATE_FAIL；含 `## hooks` 节 → ValueError/YAMLError 崩审计链 | 审计健壮性/正确性 | P2 | 见 Z5.review2.md#F517 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F518 | OWNERSHIP 文件 `added` 状态零拦截（F507 的 added 孪生）：首次创建 OWNERSHIP 文件携带未授权键静默过审 | 审计完整性 | P2 | 见 Z5.review2.md#F518 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F519 | `TokenLedger.record` 写侧（mkdir/open/f.write）无 OSError 防御：文件系统错误崩 API dispatch hot path（API 成功后、输出写入前）→ 丢 LLM 输出并失败该步 | 错误处理 | P2 | 见 Z5.review2.md#F519 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F520 | tenacity 重试失败 attempt 的 token 消耗不记账：仅最终成功 attempt 的 usage 落账 → 429/5xx/timeout 重试成本被少计 | 计量缺口 | P2 | 见 Z5.review2.md#F520 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F521 | `estimate_prompt_tokens` CJK 判定范围仅 0x4E00-0x9FFF：中文标点/全角/扩展 A 按 ASCII 4 chars/token 计 → 中文 prompt 系统性低估 token，上下文告警阈值提前量被侵蚀 | 估算精度/边界 | P2 | 见 Z5.review2.md#F521 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F522 | resonance_trend.md 写侧（`_build_resonance_trend_row` 无 header 7 列行）与 `compute_drift.parse_trend`（要求 header 行含维度名）格式不兼容 → parse_trend 恒返回空，volume-decline 检测永不触发 | 格式兼容性（跨区：Z6/skill_utils） | P2 | 见 Z5.review2.md#F522 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F523 | `_diff_records` 对无 id 记录按 `str(None)` 键合并：id-less 记录的新增/删除在 record 级 diff 中静默掩盖 | 边界/错误处理 | P2 | 见 Z5.review2.md#F523 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F524 | `audit_writes` 内部 `_declared_patterns` 不带 chapter 调 `derive_output_files` → 全部 chapter-parametric 写模式被 genesis 过滤（resolve_or_skip→None）→ declared=[] → 所有章节文件判"未声明写入"假阳性 GATE_FAIL（确定性，非边角） | 审计正确性 | P1 | 见 Z5.review2.md#F524 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F345 | 并行审计波完全绕过 G3（scoring independence）——6 个 audit skill 均 requires_independent=True | 契约违反 | P1 | 见 Z3.review3.md#F345 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F346 | truth_index._HOOK_ID_RE 不匹配生产带连字符 hook id（MH-001/H-N01）→ master hooks 从 Route A 检索静默缺失 | error | P2 | 见 Z3.review3.md#F346 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F347 | 生产 hook 数据格式与上下文"伏笔债务简报"解析全错位：简报恒"(无)" | error | P2 | 见 Z3.review3.md#F347 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F348 | SharedAuditContext 缓存注入与审计契约 reads 错位——缓存对预期目标近乎死线 | optimization | P2 | 见 Z3.review3.md#F348 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F349 | MODIFY 派生的 truth re-dispatch 无重试预算/无升级：持续失败时每次 step 迭代重复重发 | error | P2 | 见 Z3.review3.md#F349 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F350 | 每章无条件创建 chapter-N-pre-rev.md 备份（即使 route=no-revision 无 revision 发生） | optimization | M | 见 Z3.review3.md#F350 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F351 | API JSON 模式未传 response_format，依赖提示词合规 + 回退解析（非合规输出先失败一次再重试） | error | M | 见 Z3.review3.md#F351 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F352 | dispatch_skill 的 timeout 形参死代码（三条路径均用 _compute_dispatch_timeout） | optimization | M | 见 Z3.review3.md#F352 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F440 | g0.py G0.3/G0.12 的 jload ValueError 未捕获 → gate_G0 崩溃（F431 家族在 g0.py 的 2 处漏网） | error | P2 | 见 Z4.review3.md#F440 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F441 | G0.14 deps.json 为合法非 dict JSON → AttributeError 崩溃（json.loads 直读后未校验即 .get） | error | P2 | 见 Z4.review3.md#F441 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F442 | g4_length_normalizing 未实现 SKILL.md 压缩双底线（≥25% 原始长度）→ 过度压缩静默通过 | error | P2 | 见 Z4.review3.md#F442 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F443 | g1.check_fields_exist 死代码：仅测试引用，gate_G1 与生产均未接线（B.4 字段软检查未生效） | dead-wire | P2 | 见 Z4.review3.md#F443 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F444 | G3.3 output_files 读取层级与 progress.json 实际结构不匹配 → G3.3 恒 SKIP，G2 复查死路（测试用非生产形状掩盖） | error | P1 | 见 Z4.review3.md#F444 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F445 | shared.unimplemented() 无调用方（死代码） | dead-wire | M | 见 Z4.review3.md#F445 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F637 | records 判据 12 漂移检查在真实 pending_hooks.md 上恒为空操作：真实文件无 `## hooks` YAML 与 `## 活跃伏笔` 表，ch-025 快照有 → 格式在 ch25→ch56 间分叉，drift/block-ship 安全网静默失效且单测全部掩盖 | 真实数据验证 | P1 | 见 Z6.review4.md#F637 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F638 | 治理链 auditDimensions 键形分叉：audit_layer 支持 snake_case 回退，config_coherence Rule 1 与 G0 只认 camelCase → snake_case 配置禁用关键审计维度时绕过写侧 rationale 与读侧 G0，审计却照常被禁用 | 跨文件状态一致性 | P2 | 见 Z6.review4.md#F638 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F639 | compute_drift CLI 对缺失趋势文件静默跳过并 exit 0（误判"无漂移"）；真实项目缺 arc_payoff/volume 趋势文件 → CLI 只跑半个检测；`--write-audit-drift` 向 drift-guidance 单一写者拥有的 audit_drift.md 追加无协调 | 边界/CLI | P2 | 见 Z6.review4.md#F639 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F525 | `TokenLedger.summarize`/`iter_records` 对"可构造但字段类型错误"的记录不跳过 → TypeError 崩报告 CLI，违反模块"corrupt line 绝不崩"契约 | 错误处理/边界 | P2 | 见 Z5.review3.md#F525 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F526 | `_changed_top_keys` 对 JSON 顶层类型变化（dict→list/str）返回空元组 → OWNERSHIP field 文件被整体替换为非 dict 时零违规 | 审计正确性 | P2 | 见 Z5.review3.md#F526 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F527 | `check_write_ownership` record_create 分支不校验新记录的键集：`_HOOK_KEYS_NEW_RECORD`（16 键白名单）为死配置，plant 新增记录可携带任意未授权键 | 审计完整性/死配置 | P2 | 见 Z5.review3.md#F527 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F528 | `record_audit_outcome` 账本写侧（mkdir/open/write）无 OSError 防御：写失败在 `dispatch_with_write_audit` 的 finally 中传播 → 审计结果丢失并掩盖 dispatch rc | 错误处理 | P2 | 见 Z5.review3.md#F528 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F530 | `parse_resonance_scores` 的 `val > 0` 过滤丢弃合法 0 分（dead-wire 桥上下文，无现行生产影响） | 边界/语义 | M | 见 Z5.review3.md#F530 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F353 | novel.json.total_chapters 无任何正常流写入点（自锁死循环）——F324 修复后 pipeline 仍永不完成 | error | P1 | 见 Z3.review4.md#F353 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F354 | 并行审计波静默吞掉 dispatch 失败：全部审计失败仍标记完成并推进（对照串行 _handle_failure 重试/升级） | error | P1 | 见 Z3.review4.md#F354 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F355 | 确定性策展层输出死线：context/chapter-N-curated.md 无任何 skill 读取（9 节分层编排生产无效） | error | P2 | 见 Z3.review4.md#F355 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F356 | curate_context P 分层渲染失效：章节 plan 与全部 route 条目落入 P7，P1/P3-P6 恒 "(未产出)" | error | P2 | 见 Z3.review4.md#F356 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F357 | SharedAuditContext 的 style_profile 以幽灵路径 truth/style_profile.md 注入（style 内容重复进入每个审计 prompt） | error | P2 | 见 Z3.review4.md#F357 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F358 | linguistic drift ESCALATE 被吞：DriftEscalationError 在 pipeline-linguistic-drift-check 的 except Exception 中仅 log；drift 指令文件无消费者 | error | P2 | 见 Z3.review4.md#F358 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F359 | Route A 检索条目无实体内容（仅 "[category] id from file" 标签），entity 事实从不进入上下文 | error | P2 | 见 Z3.review4.md#F359 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F360 | chapter_loop._maybe_rebuild_truth_index 只 build 不落盘（周期索引重建无效，日志误导） | optimization | P2 | 见 Z3.review4.md#F360 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F361 | _call_llm_streaming 的 early_stop_patterns 死参数（无调用方传值） | optimization | M | 见 Z3.review4.md#F361 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F363 | run_triggered_skills 中途失败后重试会重发已成功的触发步骤（无 per-skill 进度追踪） | optimization | M | 见 Z3.review4.md#F363 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F362 | cmd_backfill_context 使用 print() 违反框架约定（AGENTS.md：No print() in framework code） | error | M | 见 Z3.review4.md#F362 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F446 | count_transition_words 转折词计数双向偏离 SKILL 契约：然而→0、然后/显然→计入 | error | P2 | 见 Z4.review4.md#F446 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F447 | G4.chapter-drafting 的 transition/fatigue 计数把 PRE/POST 元区块计入（与 G4.meta、word_count_md 剥离行为不一致）→ 真实章节近阈值/越阈值误报 | error | P2 | 见 Z4.review4.md#F447 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F448 | check_chapter_title 只识别阿拉伯数字章节号，中文数字"第一章"漏检（SKILL.md 明示禁止） | error | P2 | 见 Z4.review4.md#F448 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F449 | G_RECONCILE 状态字面量 "DONE" 与全部生产 progress 形状不匹配 → GR.1 恒死；GR.2 在 F401 修复（剥离 -scores）后仍恒 FAIL | error | P2 | 见 Z4.review4.md#F449 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F450 | G6.7 hook 解析器与真实 pending_hooks.md 格式不匹配 → 真实项目恒 low_hook_density:0.0 FAIL，生命周期/超距检查死路 | error | P2 | 见 Z4.review4.md#F450 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F451 | g6_checks check_pacing / check_style_consistency 元区块剥离正则缺 `# ` 与 `<!--META` 边界 → 正文被吞 → 章节误分类/风格指标失真 | error | P2 | 见 Z4.review4.md#F451 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F452 | G4.cd.chapter_end_hook 评估的是文件末尾 POST_WRITE_SELF_CHECK 元文本而非叙事结尾 | error | P2 | 见 Z4.review4.md#F452 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F453 | G2.7 重要章豁免（volume_map/plan 标注 → ceiling 10000）在全部自动化调用路径死路：project_dir 未接线 → >4500 字重要章恒误报 FAIL | error | P2 | 见 Z4.review4.md#F453 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F454 | G_TRANSITION GT.1/GT.3 对生产 progress 形状语义漂移：round-exec 形状恒真空 PASS、materialize 形状恒 FAIL | error | P2 | 见 Z4.review4.md#F454 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F455 | g4_generic_generative docstring 声称校验 frontmatter，代码未实现 | docs | M | 见 Z4.review4.md#F455 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F531 | 无 state 的 dispatch 调用路径（genesis/closure/triggers/audit_layer/parallel/CLI）TokenLedger 零落账：`_record_token_usage` 以 `if state:` 为闸门，project_dir 可用也不写 → 大部分 pipeline API 成本系统性缺失 | 计量缺口 | P2 | 见 Z5.review4.md#F531 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F532 | `TokenLedger.record` 的 chapter 字段恒为 0：`getattr(state, "chapter", 0)` 在 PipelineState（无 .chapter 属性，真实字段是 chapter_loop.current_chapter）上恒返回 0 → summarize by_chapter 全部坍缩到 "0" 桶 → report "Per-chapter average cost" 恒等于总成本 | 展示指标失真 | P2 | 见 Z5.review4.md#F532 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F533 | `TokenLedger.iter_records` 对无效 UTF-8 账本行抛 UnicodeDecodeError 崩 `shenbi-cost report`：read_text 无防护，违反模块"corrupt line is skipped, never crashing the report"契约 | 错误处理/契约违反 | P2 | 见 Z5.review4.md#F533 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F534 | `_changed_top_keys` 对 JSONDecodeError 静默返回 ()：OWNERSHIP JSON 文件被写成无效 JSON（数据损坏形态）→ field 级审计零违规 | 审计正确性 | P2 | 见 Z5.review4.md#F534 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F535 | `parse_markdown_table` 表头缺 id 列 → md_rows 恒空 → drift 检测静默放行（畸形派生表 = "一致"） | 审计健壮性 | P2 | 见 Z5.review4.md#F535 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F536 | "未声明写入"检测在真实接线下不可达：快照面=声明写入面，技能写声明外文件（越权的基本形态）永不进入审计；test_write_audit.py:79-87 手工构造 post dict 掩盖该盲区 | 审计完整性/接线 | P2 | 见 Z5.review4.md#F536 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F134 | scoring validate_scores 对空 dimensions rubric 静默放行 → 不可解析 rubric 产出静默 0 分（FAIL）而非 REJECT | error | P2 | 见 Z1.review4.md#F134 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F135 | scoring validate_scores 对 NaN 分数放行：`{"1": NaN}` 通过 0-100 校验 → final_score NaN 静默 | error | P2 | 见 Z1.review4.md#F135 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F136 | status.py CommandResult TypedDict 全仓无使用："Emit sites use enum members through typed result structures" 的静态类型保证未落实 | dead-wire | M | 见 Z1.review4.md#F136 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F137 | phase_runner cmd_post_skill 经 derive_output_files/derive_file_type 静默吞 ContractError：契约损坏 → G2 SKIP + G4 空文件 vacuous PASS → 相位无校验推进、无日志 | error | P2 | 见 Z1.review4.md#F137 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F138 | error_guidance.py / recovery.py 的 `log = get_logger(__name__)` 从未使用（死代码） | dead-wire | M | 见 Z1.review4.md#F138 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F139 | __init__.py docstring 子模块清单仅列 6/12：缺 capability_fs/cli_utils/error_guidance/paths/recovery/safe_write/status/sync_contracts，与初审"与实际结构一致"断言不符 | doc↔code drift | M | 见 Z1.review4.md#F139 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F640 | materialize_progress 的输入契约（INIT/MARK_DONE 事件）在生产中零生产者 → 任何调用都静默用"全 pending"视图覆盖真实 progress.json（数据丢失 + 错误结果） | dead-wire + 数据损坏 | P1 | 见 Z6.review5.md#F640 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F641 | records `_values_equal` 布尔比较孔：YAML 布尔 `true` 与 md 表 `"true"` 比较 → 假 drift（block ship） | 边界/比较缺陷 | P2 | 见 Z6.review5.md#F641 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F642 | check_opening_similarity 比较的是 META 指令块而非正文开头：真实章节对 (45,46) 相似度 0.627 > 0.6 阈值 → F602 一旦接线即假阳性触发 opening-variation 指令 | 统计口径（F634 同根第三消费方） | P2 | 见 Z6.review5.md#F642 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F364 | atexit 紧急清理在每次正常进程退出时无条件清空 staging/——人审通过的 plan/truth 永不被提交，pipeline 卡死于 chapter-planning 循环 | error | P1 | 见 Z3.review5.md#F364 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F365 | STATE_SETTLE MODIFY 重跑不重设 checkpoint：重跑结果悬空不提交、重审门被静默跳过（`_advance` 的 STATE_SETTLE 分支本身即死代码） | error | P2 | 见 Z3.review5.md#F365 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F366 | 5 个 PipelineConfig 死旋钮零消费者：genesis_review_required / volume_boundary_review_required / style_learning_interval / context_budget_override / snapshot_retention_chapters | optimization | P2 | 见 Z3.review5.md#F366 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F367 | step 2 chapter-planning 的 context assembly 恒读不存在的当章 plan → 每章恒失败走 minimal fallback + 一次无效 curation | error | M | 见 Z3.review5.md#F367 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F368 | hook_planting._append_to_pending_hooks 以 frontmatter-only 覆写 pending_hooks.md——接线即破坏生产 body 表格格式 | error | M | 见 Z3.review5.md#F368 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F369 | cmd_init 对缺失 seed 文件未捕获 FileNotFoundError → 裸 traceback 而非 emit_json ERROR | error | M | 见 Z3.review5.md#F369 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F370 | API 路径解析出的 SkillOutput.decisions 字段从不落盘（JSON 模式 decisions 侧车静默丢弃） | error | M | 见 Z3.review5.md#F370 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F235 | dispatch_with_write_audit 审计面错位：快照 PROJECT_DIR（shenbi 仓库根）而非 round_dir/project_dir —— 成功派发返回 rc=2 GATE_FAIL + 写越权审计对真实写入盲区 | 漏报（功能错误/审计失效） | P1 | 见 Z2.review3.md#F235 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F236 | audit/write_audit.py `_matches_declared` 不 fnmatch 声明为 glob 的写入（`truth/*.md` 等 9 技能）→ glob 写入恒判"未声明写入" | 漏报（跨区：audit/ 被 executor 审计链消费） | P2 | 见 Z2.review3.md#F236 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F237 | compute_file_change 对 added JSON 文件返回空 changed_top_keys → field 级 OWNERSHIP 键集校验对新建文件整体旁路 | 漏报（审计盲区，F233 field 级孪生） | P2 | 见 Z2.review3.md#F237 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F537 | `_changed_top_keys` 的 `.get()` 把"缺失键"与"null 值键"归并为同一信号：OWNERSHIP field 文件新增 null 值键 / 删除 null 值键 → 键集变化零检测 → field 级审计静默放行 | 审计正确性 | P2 | 见 Z5.review5.md#F537 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F538 | `snapshot_tree` 对非 UTF-8 watched 文件抛 UnicodeDecodeError 崩审计链：pre-snapshot（executor.py:244）崩 → dispatch 未启动即中止；post-snapshot（:264）崩 → finally 异常替换 dispatch 结果 | 错误处理/健壮性 | P2 | 见 Z5.review5.md#F538 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F643 | 治理链对"键缺失"的默认语义自相矛盾：G0 视缺失为启用（`get(dim, True)`）、audit_layer 视缺失为禁用（`get(dim_key, False)`）→ 从 auditDimensions 移除关键维度（或置空对象）静默停用审计且两道治理同时失明 | 治理绕过（F611/F631/F638 同族第四向量） | P2 | 见 Z6.review6.md#F643 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F140 | `shenbi-score` CLI 成功路径恒 exit 1：main() 返回 dict → 控制台脚本 `sys.exit(dict)` → 违反 command-to-give.md 文档化退出码契约（0=成功），且 codex 模式自动评分路径永远"失败" | error | **P1** | 见 Z1.review5.md#F140 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F141 | scoring validate_scores 对 bool 分数放行：scores.json 中 `true`/`false` 静默按 1/0 计分（isinstance 把 bool 当 int） | error | P2 | 见 Z1.review5.md#F141 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F142 | scoring 过滤后评分在文档化 bug-hunt/clean 路径恒发 `weight_mismatch` 误报 warning；filter docstring 宣称 "renormalize weights" 但函数内未实现（重归一实际隐式发生在 compute_score），且输出 dimensions 权重和不等于 100 | doc↔code drift | M | 见 Z1.review5.md#F142 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F143 | phase_runner cmd_post_skill 回退注释声称 "G2's decisions branch would json.loads() markdown → crash"，与 g2.py 实际行为（decisions 分支对非 .json 直接 continue，不会解析 markdown）不符 | doc↔code drift | M | 见 Z1.review5.md#F143 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F371 | closure step 10（shenbi-snapshot-manage）G4 校验恒失败：目录路径 `final-snapshot/` 被 generic G4 判 read_error/not_found → 重试×3 后 escalation → pipeline 永不 COMPLETED | error | P1 | 见 Z3.review6.md#F371 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F372 | `_style_profile_is_stale` 章节计数被 pre-revision 备份文件污染：`chapter-*.md` glob 计入 `chapter-N-pre-rev.md` → style-learning 自愈触发提前/误触发 | error | P2 | 见 Z3.review6.md#F372 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F238 | audit_writes 对 malformed `## hooks` YAML 裸抛 ScannerError/ValueError → dispatcher 审计链崩溃，"崩溃仍审计"保证失效 | 漏报（错误处理缺陷） | P2 | 见 Z2.review4.md#F238 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F239 | derive_file_type truth/decisions 分类 glob 盲区：精确字符串交集，`truth/*.md`/`snapshots/chapter-NNN/*` 写者被误归 "chapter" | 漏报（校验错位+文档自相矛盾） | P2 | 见 Z2.review4.md#F239 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F240 | extract_chapter 仅识别英文 "chapter N"：中文 prompt（框架主语言）→ chapter=None → N/NNN 输出全部丢弃 → standalone G2 整体静默跳过 | 漏报（校验空洞） | P2 | 见 Z2.review4.md#F240 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F241 | genre_config 规则 1 approval.decision 缺失/空值时静默 PASS；禁用 非 list / 替换建议 非 dict 时对应规则静默跳过 | 漏报（校验洞，F216 同类） | P2 | 见 Z2.review4.md#F241 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F242 | OWNERSHIP 矩阵 2/6 条目指向 DEPRECATED 技能（plant/track），生产写者 foreshadowing-lifecycle 无条目 → pending_hooks.md 记录级写保护对生产路径空转 | 漏报（死线/未接线） | P2 | 见 Z2.review4.md#F242 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F243 | 独立 dispatcher 无独立评分者：PR-20 把原 shell 的"独立评分 subagent 派发（G3.4 wrapper）"改为"生成器自评" | 漏报（G3.4 结构性违反，F214 互补） | P2 | 见 Z2.review4.md#F243 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F244 | G1.4 的 .bak 由 INPUTS 创建、G2.11 对 truth OUTPUTS diff → 输出非输入的 truth-updater G2.11 永不触发 | 漏报（保护静默失效，跨区） | P2 | 见 Z2.review4.md#F244 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F144 | phase_runner `load_state` 对 phase-state 文件无形状/类型校验：损坏或非 dict 的状态文件 → 未捕获 JSONDecodeError/KeyError/TypeError 裸 traceback，与其余命令的结构化错误信封不一致 | error | P2 | 见 Z1.review6.md#F144 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F456 | G6 章节目录按字典序排序（chapter-10 < chapter-2）→ G6.4 时间线回归漏报、future_knowledge 语义错乱、G6.5 连续分类与 G6.8/G6.10 采样错章 | error | P2 | 见 Z4.review5.md#F456 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F457 | G6.5/G6.10 对话占比用「对话段数 / 总字数」而非「对话字数 / 总字数」→ dialogue 分类死路、对白范围判定失真 | error | P2 | 见 Z4.review5.md#F457 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F458 | DecisionsDoc Adjustment.rationale 空串绕过 P2.5 REQUIRED（F404 家族第二实例） | error | P1 | 见 Z4.review5.md#F458 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F459 | g4_worldbuilding novel.json / genre-config.json 的 jload ValueError 未捕获 → 合法非 dict JSON 崩溃（F431 家族漏网 2 处） | error | P2 | 见 Z4.review5.md#F459 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F460 | json.loads/jload 后内层形状未校验 → AttributeError 崩溃（G0.3 chapter_word / G0.cc auditDimensions / G5.1 t1_scores 条目 / G4 _check_adjacent_budget 相邻文件） | error | P2 | 见 Z4.review5.md#F460 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F461 | g4_chapter_drafting protagonist_presence / scene_concreteness 未剥离 PRE/POST 元区块（F447 家族剩余消费方）→ 边缘章节主角在场/视觉场景误判 | error | P2 | 见 Z4.review5.md#F461 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F373 | run_triggered_skills 的 G4 校验用未解析 N 占位路径（dispatch 写盘为解析后章号路径）→ 5 个 N 型触发步骤 G4 恒 not_found，周期/卷边界触发必进 ESCALATION | error | P1 | 见 Z3.review7.md#F373 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F374 | write_safety 将 shenbi-review-resonance 分类为 READ_ONLY_AUDIT，但其契约 updates 写 truth/audit_drift.md + truth/resonance_trend.md → 并行审计波在无串行保护下并发写 truth 文件（模块自述的 WRITE_SHARED 串行不变量被违反） | error | P2 | 见 Z3.review7.md#F374 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F375 | API 路径多文件输出部分缺失仍返回成功（missing 仅 log.error，DispatchResult 恒 True）→ state-settling 等 6 文件技能的残缺输出被静默接受 | error | P2 | 见 Z3.review7.md#F375 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F376 | `pipeline-truth-embed update` 无 `--text` 时静默报 OK（不嵌入任何内容） | error | M | 见 Z3.review7.md#F376 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F377 | check_audit_completeness 的 VERDICT_MARKERS 含通用词 "通过"，no_verdict 检查几乎永不触发 | error | M | 见 Z3.review7.md#F377 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F378 | context/volume-N-complete.json 全仓无写入方 → `_check_volume_completion` 恒 False → 软失败升级链恒触发 volume_objective_missed 信号；`last_trigger_failure` 写后无消费者 | error | P2 | 见 Z3.review7.md#F378 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F245 | contracts/paths.py N 占位符语义碰撞：arc-N/volume-N/stratum-N/escalation-N/AC-NNN 一律按章节号解析或丢弃；resolve_volume_path 除 closure 外零消费 → pipeline 卷/弧技能 dispatch 崩 UnresolvedPathError | 漏报（正常路径功能错误，跨区） | P2 | 见 Z2.review5.md#F245 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F246 | dispatch_skill legacy 回退默认路由到 shenbi-dispatch → pipeline 默认路径继承 standalone 全部缺陷（F227 门序 + F235 审计 rc=2）→ pipeline genesis 在无 API key/无 codex 环境无法完成 | 漏报（接线缺陷，跨区放大） | P2 | 见 Z2.review5.md#F246 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F145 | phase_runner `load_deps()` 无任何错误处理：deps.json 损坏/缺失 → cmd_pre_score / cmd_finalize 裸 traceback，而同一文件的两个兄弟消费者（g5.py / scoring.py）均有守卫 | error | **M** | 见 Z1.review7.md#F145 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F146 | scoring.check_gate_markers t2 分支对 deps.json 仅 exists() 守卫：文件存在但损坏 → 未捕获 JSONDecodeError 裸 traceback（同族 F145 只覆盖了 phase_runner.load_deps，scoring 侧损坏场景漏掉） | error | **M** | 见 Z1.review8.md#F146 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F147 | sync_contracts.main() 的 deps.json 读取（:195）与 load_registry（:165）均无守卫：损坏/缺失 → 裸 traceback（本文件前七轮仅 F109/F117/F130 覆盖，加载边界未覆盖） | error | **M** | 见 Z1.review8.md#F147 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F379 | closure 步骤 2/4/5/6/10 在 API/IDE 派发路径下 prompt 构建即失败（UnresolvedPathError）：10 步中 5 步永不派发——比 F313/F371 更根本的 CLOSURE 阻塞 | error | P1 | 见 Z3.review8.md#F379 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F380 | genesis step 16（shenbi-anchor-curate，optional）在 API/IDE 路径永远被当作 optional 跳过：anchors 永不产出（AC-NNN.md 契约占位符在 chapter=None 时抛 UnresolvedPathError） | error | P2 | 见 Z3.review8.md#F380 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F381 | state_heal._heal_revision_counts 把未修订章节的 revision_count 抬到 ≥1：`_ensure_revision_decisions_exists` 对 NO_REVISION 路由也写回退文件，heal 误将其当作"发生过修订" | error | P2 | 见 Z3.review8.md#F381 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F382 | progress.json 物化层半接线：pipeline 从不写 trace 事件（safe_write 未传 round_dir/trace_action），每 5 步 materialize 把 progress.json 重建为"全 pending"视图，resume 时 staleness 检查空转 | optimization | P2 | 见 Z3.review8.md#F382 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F383 | IDE 派发路径输出无 `### FILE:` 标记时，整段 stdout 被写入每一个输出文件（codex 已安装 → 当前环境 IDE 路径激活下的潜伏数据损坏点） | error | P2 | 见 Z3.review8.md#F383 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F247 | 审计链 N 占位符解析不一致：watch 面解析 N 而 declared 面不解析 → 40 个 N 写技能成功派发恒被判「未声明写入」rc=2 GATE_FAIL | 漏报（正常路径功能错误/审计失效） | P1 | 见 Z2.review6.md#F247 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F248 | pacing_design.from_markdown 解析失真：chapter_sequence 恒空使「不连续 3 章同类型」规则在 g4 门路径死代码；scene_types 固定词表子串扫描致 g4 误拒/虚增 | 漏报（校验洞+误拒） | P2 | 见 Z2.review6.md#F248 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F249 | executor.run_g2 把 PROJECT_DIR（shenbi 仓库根）当 G2 project_dir 传入 → _is_important_chapter 恒 False → 重要章 4500-10000 字被 G2.7 误拒 | 漏报（正常路径误拒，跨区接线） | P2 | 见 Z2.review6.md#F249 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F148 | phase_runner cmd_post_skill 对契约声明但磁盘缺失/为空的输出静默丢弃（无日志）：技能未产出任何文件时 G2 SKIP + G4 空文件 vacuous PASS + PASS marker → 相位以 OK 推进 | error | **P2** | 见 Z1.review9.md#F148 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F149 | scoring filter_dimensions_by_test_type 对"无维度数字"的排除 scope 静默 no-op：规范 _template rubric 自身的 `Prose/narrative quality \ | No` 行无效（排除机制第三失效模式，R2 备查 #5 "44 个未触发" 与事实不符） | error | 见 Z1.review9.md#F149 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F150 | phase_runner run_gate("G2") 不传 project_dir → G2.7 重要章节 ceiling 判定在相位机路径恒失效（executor 传 REPO_ROOT 亦错） | error | M | src/shenbi/phase_runner.py（见 Z1.review9.md#F150） | 两路径均未传真实项目目录 | read 确认 | G2.7 相位机路径失效 | 传真实 project_dir | deep-read | verified |
| F151 | scoring.py:419 scores.json 非数字键静默丢弃且无 WARNING | error | M | src/shenbi/scoring.py:419（见 Z1.review9.md#F151） | extra-key WARNING 只对数字键生效 | read 确认 | 静默丢键 | 补 WARNING | deep-read | verified |
| F152 | load_rubric kill-switch 解析漏 "→ detection dimension = 0" 类条目 → 10+ 份 rubric kill_switches 元数据不完整 | error | M | src/shenbi/scoring.py（见 Z1.review9.md#F152） | 解析只认 total/phase/pipeline = 0 | read 确认 | 元数据缺项 | 扩展解析 | deep-read | verified |
| F153 | sync_contracts.render_body_view 的 skill 参数从未使用（死参数） | error | M | src/shenbi/sync_contracts.py（见 Z1.review9.md#F153） | 死参数 | read 确认 | 死代码 | 删除参数 | deep-read | verified |
| F644 | compute_ngrams 未剔除标点 → n-gram 风格指纹被标点对/标点串主导（真实 chapter-1 top bigram 为 `。他` 与 `——`） | 统计口径 | P2 | 见 Z6.review7.md#F644 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F645 | compute_ttr 排除串缺 `“”`/`"`/`‘’` 引号（只排 ASCII 直单引号 `''`）→ 对话文本引号字符计入 TTR token | 统计口径 | P2 | 见 Z6.review7.md#F645 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F646 | AUDIT_SAFETY_MATRIX 维度集与真实 genre-config auditDimensions 漂移（6 vs 10 维）：motivation/foreshadowing/sensitivity/worldRules 可无 rationale 禁用且 G0 无信号 | 跨文件状态一致性 | P2 | 见 Z6.review7.md#F646 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F462 | G3.2 评分提取键与 shenbi-score 规范输出形状不匹配（total_score/score vs final_score/dimensions）→ 规范形状报告 score=0 恒 FAIL；F428 的"直读 94 阈值"路径在生产形状下不可达 | error | P2 | 见 Z4.review6.md#F462 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F463 | G3.2 全量扫描 t1-reports 不按 skill_name 过滤 + rubric 加权回退用 gate 技能 rubric 评估其它技能报告（跨技能互扰） | error | P2 | 见 Z4.review6.md#F463 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F464 | t1-reports 生产命名 `*-scores-subagent.json`（codex.py）与 gate 消费模式 `*-scores.json`/find_report 不匹配 → G5.1 兜底恒 no_report FAIL、G0.10 计数恒 0（F432 第二根因）、GR.1/GR.2 在 F401 修复后仍失败（-subagent 后缀）、G7.14/15 空转 | error | P2 | 见 Z4.review6.md#F464 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F465 | F460 家族新增 4 实例：内层形状未校验 → AttributeError 崩溃（G7.1/G7.1b t1_scores、G_RECONCILE skills、character_design archetype_sources 元素、foreshadowing_plant hooks 元素） | error | P2 | 见 Z4.review6.md#F465 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F466 | G4.cd.content_uniqueness 在 G6.3 调用形状（rd=项目目录，g6.py:86-93）下静默跳过 —— Path(rd)/"project-output"/"chapters" 不存在 → T3 逐章 G4 中内容唯一性检查不执行且无 SKIP 记录 | error | P2 | 见 Z4.review6.md#F466 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F467 | chapter_planning 节号分隔符不一致：sections 计数接受 `## 5、`/`## 5：`，s5/s7 提取正则仅认英文句点 `## 5\.` → 合法格式下 s5_choice 误 WARN、s7_hook_ops 误 FAIL | error | P2 | 见 Z4.review6.md#F467 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F250 | 独立 dispatcher codex 模式不注入技能定义：codex agent 仅有裸 prompt（无 SKILL.md/契约/rubric），无法产出契约一致输出 | 漏报（正常路径功能缺陷，F227 掩盖） | P2 | 见 Z2.review7.md#F250 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F384 | bge-large-zh SentenceTransformer 模型在每次 embed/检索调用中重复加载：genesis 每步全量重嵌（每 hook/rule 一次全新模型加载）+ 每章 context assembly 两次加载 | optimization | P2 | 见 Z3.review9.md#F384 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F385 | dispatch_skill 第三路由（legacy `shenbi-dispatch` 子进程）为必失败死端：internal 模式硬拒 + uses_staging 被忽略 | error | P2 | 见 Z3.review9.md#F385 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F386 | 软失败升级路径派发 escalation-review 但不设 ESCALATION checkpoint——升级从不暂停、escalation 报告成为孤儿 | error | P2 | 见 Z3.review9.md#F386 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F387 | genre 波与 group 波文件级重复不止 sensitivity：worldRules/motivation/dialogue/texture 四维每章重复审计并覆盖 group 波产物（F329 的完整版） | optimization | P2 | 见 Z3.review9.md#F387 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F388 | `_audit_context_coverage` 死函数：docstring 声称"pipeline resume 初始化时调用"（spec §3.1 的 77% 上下文覆盖缺口检测），cli 从未接线 | error | P2 | 见 Z3.review9.md#F388 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F389 | linguistic drift 数据源侧全链路 inert：`style/linguistic_baseline.json` 唯一写入方 `establish_baseline` 全仓 0 调用方 → 每章 drift 检查恒 "no baseline" 返回 None → spec §3.4 三级干预（WARN/HARD/ESCALATE）与 DriftEscalationError 生产不可达 | error | P2 | 见 Z3.review9.md#F389 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F390 | cmd_review `--feedback` 文件缺失时误报 "project not found" | error | M | 见 Z3.review9.md#F390 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F154 | safe_write flock 主路径与 O_EXCL 回退路径互不感知对方锁原语：flock 持有者与 lockfile 持有者可并发写同一目标（第四处并发缺陷站点，前九轮只覆盖原语内竞态） | error | **M** | 见 Z1.review10.md#F154 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
| F155 | scoring.check_scorer_agreement 对 NaN 分数误报 agreed=True；flag_score_collapse 对单维度误报 all_identical（两函数数值边界缺陷；函数当前 dead（Z5 F500），接线前必须先修） | error | **M** | 见 Z1.review10.md#F155 | 见报告 | 见报告 | 见报告 | 见报告 | deep-read | verified |
