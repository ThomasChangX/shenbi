> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟡 P2 | **方法:** systematic-debugging 四阶段
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
- `_budgeted_truncate` 返回 `(text, meta)`：meta 含 original_len/kept_len/offset；注入文本尾部追加 `[TRUNCATED x/y chars]` 标记，且标记置于 cap 预算之外（不可被切掉）；structlog WARN 一条
- 预算再分配：先扫描各文件长度，短文件未用完的余量按需回补给被截断文件（F330）
- 共享审计上下文注入的 pending_hooks 截断同样标记（F362）
- **验收**：构造 >32K fixture，派发 prompt 与 trace 中可见标记与 WARN；预算回补用例（1 短 1 长文件）长文件保留量增加

### R2 · 检查面采样披露（F459 + F235）
- G6.4/G6.8/G6.9/G6.10、G5.3 的 `[:3000]`/`[:5000]` 截取点统一收到一个 `sample_text()` helper：返回文本 + sampled 标志；检查结果 JSON 增加 `input_sampled: true/false` 字段，PASS 报告如实披露
- g4_genre_config 诊断改为全量错误计数 + 首详例（`errors[:5]` + `+N more`）
- **验收**：长章 fixture 下检查结果含采样披露字段；gate 输出 schema 同步（C8 词表单源协同）

### R3 · 数值排序（F326）
- 章号解析 helper（int 化 + 非数字尾缀稳定排序）应用于 cmd_chapters、_get_audit_history、G6 章节遍历
- **验收**：10+ 章 fixture 下 `shenbi-pipeline status` 与审计历史按 1,2,…,10 顺序

### R4 · trace 截断日志（F620）与 T1615 记录
- replay 撕裂行/签名断链截断时 WARN 记录行号范围与丢弃字节数
- T1615（累积 truth 注入超线性）不在本簇修——登记为 C10/C28 的量化输入，本 spec 只保证其可观测（注入量进 token 账本）
- **验收**：构造撕裂 trace fixture，replay 输出 WARN 且报告保留事件数

## 验收（簇级）
- **最小实证前置**（本簇为推理假设级）：修复前先在真实 round 上抓一次截断日志基线（哪些文件实际被截、被截多少），确认影响面后再合入
- `just check` 全绿；C29 全部 8 条 merged-into F361 回写关闭

## 风险
- 标记文本进入 LLM prompt 可能被技能复制进产物——标记用固定 ASCII 哨兵格式并在产物 lint（C18 面）中列禁则
- 采样披露字段改变 gate 输出 schema——与 C1（读方对账）联动：改键须同步全部消费者

## 验证命令
- 截断基线实证（推理假设闸门）：对真实 round 跑一次派发 + `grep -r "TRUNCATED" <round_dir>/trace/ | wc -l`（0 = 影响面为零，簇降级回写 phase4）
- 标记协议：`pytest tests/unit/pipeline/ -k truncate -q`
- 采样披露：构造 >5000 字 fixture 跑 `just gate G6 <files> generative`，输出 JSON 含 input_sampled 字段
- 排序：`shenbi-pipeline status`（10+ 章 round，人工核对 1..10 顺序）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`F361 <- F235, F326, F330, F362, F459, F620, T1615`
- 若最小实证推翻影响面假设：簇内 P2 条目降 M 处置，并在 phase4-clustering.md §证据等级注记（本簇为 37 簇中唯一推理假设簇）
