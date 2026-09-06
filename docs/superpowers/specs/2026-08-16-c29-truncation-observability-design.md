> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-06 · SDD #43 阶段 3 设计审查修订：基线命令改被动式、新增 R2b、helper 改名、消费方接线) | **Severity:** 🟡 P2 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C29）| **依赖:** 无硬前置（标记协议与 C10 token 证据链、C28 冗余量化互为消费方）| **范围:** dispatch_helper._budgeted_truncate、共享审计上下文注入、g4/g5/g6 采样检查、cli 章号排序、trace/replay | **核心洞察:** 一切截断/采样/排序都静默进行——检测结果基于多少输入、丢了哪些输入，事后不可审计（唯一推理假设簇，T1615 有三规模实测旁证）

# C29 · 截断/采样/排序静默修复（truncation-observability）

## 元信息
- 簇：C29（截断/采样/排序静默：无标记无日志），8 条，最高严重度 P2，**证据等级=推理假设**（纯读码推导；T1615 有 T16 三规模实测旁证）——本簇修复前建议先做一次最小实证（见验收）
- 成员：F361（代表）、F235、F326、F330、F362、F459、F620、T1615
- 来源：Z2/Z3/Z4/Z6 初审与复核 + thread-reports/T16.md

## 背景与根因
框架在五个层面静默收缩输入或乱序处理，且不留任何痕迹：
1. **输入截断**：per-file 32K cap 静默无标记无日志，且截断标记本身可被 32K cap 切掉（F361）；`_budgeted_truncate` 预算不再分配——短文件余量不给被截断文件（F330）
2. **共享上下文截断**：pending_hooks 静默截断至 3000 字符，6 个核心审计中 5 个对该文件无契约读取，截断副本是其唯一视角（F362）
3. **检查面采样**：G6.8/G6.10/G6.9/G5.3 只读每文件前 3000-5000 字符，检测面系统性截窄且 PASS 不披露（F459）；g4_genre_config 诊断只报 errors[:5]（F235）
4. **排序错误**：章号字符串排序（1,10,11,2）贯穿 cmd_chapters/_get_audit_history 与 G6 检查（F326）
5. **trace 截断**：replay 撕裂行截断静默无日志（F620）；累积 truth 全文注入是唯一随 N 超线性增长的 token 项（T1615，N×2→×4）

根因：截断是"防御性降级"但被当作正常路径——没有"我丢了一部分输入"的披露协议，检测结果与完整性不可审计。

## 目标
1. 任何截断/采样必须留痕：注入产物带机器可读标记 + 日志一条 WARN（含文件、截取区间/丢弃量）
2. 章号全链路数值排序（显示、审计历史、G6 扫描顺序）
3. 检查面采样策略成文：哪些检查有意采样、采多少、为什么——其余改读全文

## 任务分解
### R1 · 截断标记协议（F361 + F330 + F362）
- `_budgeted_truncate` 返回 `(text, meta)`：meta 含 original_len/kept_len/offset；注入文本尾部追加 `[TRUNCATED x/y chars]` 标记，**标记在 per-file cap 切片之后追加**（不可被切掉，修复现行 dispatch_helper.py:333→:335 标记先加后切的缺陷）；structlog WARN 一条；顺带摘除 :314 处过时的 `# pyright: ignore[reportUnusedFunction]`
- 预算再分配：先扫描各文件长度，短文件未用完的余量按需回补给被截断文件（F330）；回补不得越过 `_INPUT_MAX_CHARS_PER_FILE` 上限（成本维度：回补天然增大 prompt，上限即护栏）
- 共享审计上下文注入的 pending_hooks 截断同样标记（F362；驳斥复核降级——声明读方经 raw_files/G6.7 已得全文，本项仅覆盖 fallback 路径）
- **可测试性重构前提**：`_budgeted_truncate` 须保持独立可导入的纯函数（现已是），prompt 装配段（dispatch_helper.py:713-759）截断相关逻辑经既有 trace/日志断言覆盖，不要求真实 dispatch
- **验收**：>32K fixture 驱动单元测试断言标记存在、置于 cap 外、WARN 已记录（structlog capture）；预算回补用例（1 短 1 长文件）长文件保留量增加

### R2 · 检查面采样披露（F459 + F235）
- G6.4/G6.8/G6.9/G6.10、G5.3 的 `[:3000]`/`[:5000]` 截取点统一收到一个 `clip_with_disclosure()` helper（**命名避开 g5.py:186 既有局部变量 `sample_text`**）：返回文本 + sampled 标志；检查结果 JSON 增加 `input_sampled: true/false` 字段（命名对齐既有先例 `chapters_sampled`，g6_checks.py:307），PASS 报告如实披露
- `input_sampled` 消费方（dead-wire 防护）：接真实读方——G7.13（重跑 gate_G6 的核对路径）透传 `sampling_disclosed` 进 check note；`write_gate_marker` 持久化 JSON 自带该字段（操作员可见）。plan review 修正：原案接 audit_layer 不可行（其只跑 G4，看不到 G5/G6 字段）
- g4_genre_config 诊断改为全量错误计数 + 首详例（`errors[:5]` + `+N more`）
- **验收**：长章 fixture 下检查结果含采样披露字段且 G7.13 重跑路径/marker JSON 可见 `sampling_disclosed`；gate 输出 schema 同步（C8 词表单源协同）

### R2b · 计数型采样披露与采样策略成文（F459 补全面）
- 文件计数/列表位置型采样同样披露：g5.py:147（outline `[:3]`）、:152（`[:8]`）、:187（char_dir `[:6]`）、:199（conflicts `[:10]`）、g6.py:223/233（chapters `[:15]`、catchphrases `[:3]`）、g6.py:294（constraints `[:10]`）——结果 JSON 加 `files_sampled: "3/12"` 类字段（仅输入文件型采样；conflicts/catchphrases 属**发现项封顶**而非输入采样，用 `findings_capped: "10/N"` 区分字段，避免误述）
- 采样策略成文（目标 3 的落地）：一页文档（`docs/framework/sampling-policy.md`）列出哪些检查有意采样、采多少、为什么——覆盖 R2 字符截取点（`[:3000]`/`[:5000]`）与 R2b 计数型采样点两类
- **验收**：>12 文件 fixture 下 G5 结果含 files_sampled；sampling-policy.md 存在且覆盖全部列出的采样点
- **fixture 出处（G0.9）**：>32K 输入 fixture 由 tests/fixtures 真实章节稿拼接生成；>12 文件 fixture 复用真实 outline 产物族；撕裂 trace 为真实 trace 副本 + 注入断行（健康运行不产撕裂行，以测试内生成器函数（upstream-generator）落 fixtures，注明生成方式）

### R3 · 数值排序（F326）
- 章号解析 helper（int 化 + 非数字尾缀稳定排序）应用于 cmd_chapters、_get_audit_history、G6 章节遍历
- **验收**：章 2-10 fixture（tests/fixtures/chapter-{2..10}-draft.md，9 章即覆盖 9→10 字典序边界）下 `shenbi-pipeline chapters`（cmd_chapters，cli.py:910）与审计历史按 2,3,…,10 顺序；G6 章节遍历同序（g6.py:68 / g6_checks.py:45-49 连续时间线比对依赖此序）

### R4 · trace 截断日志（F620）与 T1615 记录
- replay 撕裂行/签名断链截断时 WARN 记录行号范围与丢弃字节数
- T1615（累积 truth 注入超线性）不在本簇修——登记为 C10/C28 的量化输入，本 spec 只保证其可观测（注入量进 token 账本）
- **验收**：构造撕裂 trace fixture，replay 输出 WARN 且报告保留事件数

## 验收（簇级）
- **最小实证前置（被动式）**（本簇为推理假设级）：修复前对**既有已执行 round** 的日志/trace 做被动基线——grep 既有信号 `input_over_budget_applying_priority_truncation`（dispatch_helper.py:723）与 `[... truncated from`，量化哪些文件实际被截、被截多少。**不做新 dispatch**（核心原则 8：SDD 禁为验证触发付费且写状态的操作）。既有 round 无截断记录 = 影响面存疑，记 deviation 供用户裁决，不静默降级
- `just check` 全绿；C29 全部 8 条 merged-into F361 回写关闭

## 风险
- 标记文本进入 LLM prompt 可能被技能复制进产物——标记用固定 ASCII 哨兵格式并在产物 lint（C18 面）中列禁则。**C18 现无活跃 spec、无人承接**：泄漏风险在现行旧标记（`[... truncated from N chars]`，dispatch_helper.py:333 / audit_context_cache.py:119）上已存在；新哨兵与旧标记格式兼容，未来 C18 lint 可一并覆盖；本 spec 风险段即所有权记录。另注意标记进入 `.md` 产物会与 G2 字数/结构检查交互，C18 lint 落地前人工关注
- 采样披露字段改变 gate 输出 schema——与 C1（读方对账）联动：改键须同步全部消费者（当前唯一程序化读方 audit_layer.py:172 只读 status，加键向后兼容；R2 已为其接线新字段）

## 验证命令
- 截断基线实证（推理假设闸门，被动式）：`grep -rn "input_over_budget_applying_priority_truncation\|\[\.\.\. truncated from" <既有 round 目录>/ `（0 命中 = 既有 round 影响面为零，记 deviation 供裁决，不自动降级）
- 标记协议：`pytest tests/unit/pipeline/ -k truncate -q`（structlog capture + 纯函数断言，无 dispatch）
- 采样披露：>5000 字 fixture 跑 `shenbi-validate G6 <pipeline_name> <round_dir> <project_dir>`（G6 三参签名，gates/cli.py:170-176），输出 JSON 含 input_sampled 字段
- 排序：章 2-10 fixture 下 `shenbi-pipeline chapters` 与审计历史人工核对 2..10 顺序
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F361 <- F235, F326, F330, F362, F459, F620, T1615`
- 若最小实证推翻影响面假设：簇内 P2 条目降 M 处置，并在 phase4-clustering.md §证据等级注记（本簇为 37 簇中唯一推理假设簇）
