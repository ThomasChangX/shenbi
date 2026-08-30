> **Date:** 2026-08-14 | **Status:** Rejected (2026-08-30 · 与活跃 spec 重复：master #40 裁决 supersede → C33/C7/C2/C34；R1b/R1 大半已在 main 修复，存活面全部有承接，残留 F1207/T203/T204 补登 #63/#60/#34) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 7/7） | **依赖:** gate-effectiveness | **范围:** 工具/门禁链（lint 接线、词表、重试、助手接线、CLI 契约）| **核心洞察:** 工具正确性洞（lint 未接线/发明值盲区/重试死码/助手半接线）使 CI 与门禁对真实缺陷零效力

# 工具与门禁链补完（补齐 G）

## R1 · lint 接线与发明值盲区（T201/T302/T9-01/F1212/F1214, P1）
- 证据：lint_contract_fields/graph 游离于 CI/pre-push/pre-commit（T201/T302）；lint_status_strings 白名单谓词放行词表外值（T9-01/F1214）；deps.json 缺 5 skill 无完整性 lint（F1212）
- 修复：B.5/graph lint 接入 CI+pre-push；词表校验改黑名单或枚举闭包；deps.json↔skills 闭包 lint；**验收：新词表外值/缺登记 → CI FAIL**

## R1b · pipeline 字段级过滤接线（T301, P1）
- 证据：_build_skill_prompt 的 dict-form reads 分支永远不触发（legacy.load_contract 拍平 reads 后 isinstance(dict) 恒 False）→ filter_to_fields 唯一生产调用点从不带非空 fields 执行；AGENTS.md:84-86 承诺三路径均未实现
- 修复：load_contract 保留 read_fields 结构供过滤分支消费；修复后补部分匹配 WARN 回归（F218 影响面激活）
- **验收：真实 dispatch 中 fields 非空且过滤生效**

## R2 · CLI 契约修复（F140, P1）
- 证据：shenbi-score 成功路径恒 exit 1（sys.exit(dict)），codex 自动评分永远"失败"
- 修复：main 返回 int 退出码（0=成功）；**验收：成功评分 exit 0**

## R3 · 并行波与重试链修复（F301/F354/T501/T502, P1）
- 证据：并行波触发后串行块不可达（F301）；审计波 dispatch 失败零检查仍推进（F354）；tenacity 只认裸 httpx 死码（T501）；升级后 durable 预算不清零（T502）
- 修复：F301 并行/串行切换显式化；F354 加 result.success 检查 + 重试；T501 _is_retryable 认 SDK 异常；T502 升级时清零 retry_budget_consumed；**验收：并行波失败不推进；429/5xx 实际重试**

## R4 · 确定性助手接线（T14-01/T14-03/T14-04, P1）
- 证据：16 助手仅 3 个代码接线（T14-01）；style-learning 全章 pass-through 530-675K tokens/书（T14-03）；state-settling 写半未落地（T14-04）
- 修复：助手接线矩阵验收标准（生产调用点 + 经真实 dispatch 路径测试）；style-learning 接 compute_stats；F397 修复落 dispatch 写路径
- **验收：16 助手接线矩阵 100% 或显式废弃**

## P2 清单
- **F1200（P2）** lint_contract_graph.py 自称 "marquee CI mechanism / block PR"，实际未接入 ci.yml、pre-commit、pre-push-check.sh（T201 同类第二实例）
- **F1201（P2）** lint_contract_fields.py（B.5 字段漂移 lint）未接入 CI/pre-commit/pre-push/测试（= 已知 T201，Z10 侧重新取证）
- **F1202（P2）** ci.yml codegen-idempotency 对 `.codex-plugin/` 的 `git diff --exit-code` 检查空转（目录被 gitignore 且未入库，diff 恒空）
- **F1204（P2）** run_pipeline.sh 将 `$PROJECT_DIR` 插值进 `python3 -c "…"` 双引号串 → `'`/`"`/`$()`/反引号命令注入（= 已知 T12-03，Z10 侧确认 + 精确定位）
- **F1205（P2）** run_pipeline.sh 错误自动放行启发式 `grep -q "escalation\
- **F1206（P2）** run_pipeline.sh 绕过 `pipeline review` CLI 直接改写 pipeline-state.json（step_index+1、retry_counts 清零）→ 状态机不变量由外部脚本篡改
- **F1207（P2）** codeql.yml 无 pull_request 触发 → 根 SECURITY.md:21 "CodeQL static analysis runs on every PR and weekly" 的 "every PR" 声明不成立（F0-07 家族第二半）
- **F1208（P2）** changelog 双机制漂移：release.yml 用 `git log` 平铺生成 release notes，cliff.toml + `just changelog`（git-cliff）未接入发布流程
- **F1210（P2）** lint_contract_graph 的 dag_key 无法连接目录读（`benchmarks/anchors/`）与文件写（`benchmarks/anchors/AC-*.md`）→ 真实消费关系被误报 DANGLING_WRITE；registry 对同一资产的 producer 分类矛盾
- **F1211（P2）** 依赖锁定卫生：dev group 冗余/休眠依赖 + 版本漂移（= 已知 T1301–T1306，全部确认）
- **F1213（P2）** plugins/master.json skills 清单 59 vs skills/ 74（15 缺），generate.py 无任何 skills/ 交叉校验 → 新 skill 静默不发布（= 已知 F624，Z10 侧确认）
- **F1215（P2）** security.yml 无 schedule → 根 SECURITY.md:20 "pip-audit runs on every PR and weekly" 的 weekly 半句不成立（= 已知 F0-07，Z10 侧确认）
- **F1216（P2）** tests/benchmark/ 空洞（仅 __init__.py）+ pyproject norecursedirs "tests/benchmarks"（复数）指向不存在目录 + 唯一 benchmark 测试为 1+1 冒烟（= 已知 T1107，Z10 侧确认）
- **F1217（P2）** justfile `check` 与 ci.yml 双向漂移：just check 缺 N7/purity lint（CI 有），CI 缺 graph/fields lint（just 有）
- **F1218（P2）** pytest addopts 全局 `--cov` 使 `--collect-only` 等非测试调用产生 16.08% 假 FAIL 并覆写 tests/coverage/；ci.yml "Run coverage threshold test" step 名与 `--no-cov` 行为错位（= 已知 D1-02，Z10 侧确认）
- **T14-02（P2）** hook_planting 死线补全（F307 新面）：TRIGGER_STEPS 卷边界仍 dispatch LLM 版 shenbi-foreshadowing-plant（活跃路径），与 foreshadowing-resolve 同块双写 pending_hooks.md
- **T14-05（P2）** memory-distill 密度触发（60/15/20 阈值计数）声明未实现：确定性计数规则停留 SKILL.md，triggers.py 无密度检查
- **T14-06（P2）** 双路由重复：review-resonance 的三路径分流（skill_utils.review_resonance.routing + calibration，SKILL 指令级）与 pipeline 侧 route_chapter_revision 是两套独立路由
- **T14-07（P2）** 系统性模式：16 个确定性助手仅 ~5 个代码层接线——"确定性替换已 9 次实现"的说法是"实现 16 次、接线 ~5 次"；供 phase 4 聚类的母模式
- **T202（P2）** truth-files.yaml 死词表 6 项（short/*、chapter-revised、plan-decisions sidecar、snapshots glob D20 废弃未删）
- **T203（P2）** dependency-dag.json 生成但零消费（唯一消费者是 CI idempotency git diff）
- **T204（P2）** G0.16 只校验 write mode 存在性不校验值合法性（拼写错误 mode 过门禁被当默认处理）
- **T205（P2）** sync derive_expected_outputs/verify_bijection 对契约加载失败的 phase 成员静默丢输出（双侧同空自检失效）
- **T503（P2）** pipeline 级重试无退避、无失败分类：串行/closure 立即连发 ≤3 次全量 dispatch，429 风暴与 content_filter 等不可重试失败被同等放大
- **T504（P2）** 写失败重试反馈 dead-wire：`build_retry_feedback`/RETRY_WRITE_CONFIRMATION 进 `DispatchResult.stderr`，无编排方读 stderr 注入重试 prompt → 写失败盲重试 ×3
- **T505（P2）** finish_reason 处理仅 API 路径实现：IDE/legacy 无截断检测（cap-raise 保护缺失），finish_reason=None 时截断不可检测
- **T9-02（P2）** "s" 键通道 186 处裸 GateStatus 字面量完全绕 lint；同键双轨（g4 枚举成员 vs 其余裸串）
- **T9-03（P2）** ChapterState.status 无类型字段 3 拼写漂移（pending/complete/settling_failed）；progress.json 同键承载第二套词表（pending/done/skip）
- **T9-04（P2）** Severity 词表 5 套互斥值集并存；enums.py Severity 为死表且与 4 套活词表值集冲突（F208 扩展）
- **T9-05（P2）** Verdict 词表 4 套互斥值集并存；enums.py Verdict 死表与活词表值集不相交（F208 扩展）
- **T9-06（P2）** 16 处裸字符串 status/state 比较 + 6 处 require_state 裸列表替代枚举成员（lint 洞 H4）
- **T9-07（P2）** HookState 枚举 + parse_hook_state 已存在，但 4 个使用点全部裸字面量绕过；g6.py 双大小写比较并把 ARCHIVED/EXPIRED 终态误计为 unresolved
- **T9-08（P2）** lint 形态盲区：Call 关键字参数与属性赋值发射完全不可见（F209/F164 站点同时逃逸 lint）
- **T9-09（P2）** ActorRole 发射端 2 处裸字面量绕过已定义枚举（safe_write.py:134、audit/record.py:46）
- **T9-10（P2）** trace action 名称无词表（6+ 裸串）；MARK_DONE 生产零发射，与 chapter_loop.py:680 注释背离，materialize 重放路径事件源缺失
- **T9-11（P2）** 双"单一信源"声明分裂：enums.py 与 status.py 各自声称全框架唯一词表，互不引用、词汇集不相交；enums.py 头注释「所有 Literal 必须从此处 import」已被 6+ 处违反

## M 清单（并入 M 批量 spec）
- **F1203（M）** ci.yml quality job 对 macOS 全 job `continue-on-error: true`，macOS 矩阵失败不阻断 CI
- **F1209（M）** dependabot.yml:5 与 embeddings-smoke.yml:7 引用已移入 archive 的 spec 路径（`docs/superpowers/specs/…` 应为 `…/specs/archive/…`）
- **F1219（M）** executor_config.toml `shenbi-chapter-drafting` override 的 PRE-DEPLOYMENT 探测注释悬置（max_tokens=32768 是否被模型接受未确认/未清理）
