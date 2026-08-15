> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C28）| **依赖:** C10（token 计量接线——冗余 token 的量化收益以 TokenLedger 落账为准）| **范围:** contracts/legacy.py、gates/cli 懒加载、snapshot/save_state 增量化、审计波共享上下文、truth_embed 模型缓存 | **核心洞察:** 审计波每派发重复注入全章文本（29% 冗余，56 章已付 ~1.74M token），叠加 O(N²) 状态保存与 96% import 开销的门禁子进程——性能债直接折算为 token 与墙钟成本

# C28 · 性能反模式修复（perf-antipatterns）

## 元信息
- 簇：C28（性能反模式：重复解析/O(N²)/import 开销/冗余注入），13 条，最高严重度 P1，证据等级=实验佐证（T16 三规模实测 + T1601/T1602 协调者核验 verified）
- 成员：T1601（代表）、T1603、T1604、T1606-T1610、T1613、T1614、F215、F328、F415
- 来源：thread-reports/T16.md + Z2/Z3/Z4 对应行

## 背景与根因
四类反模式各自独立成灾：(a) **冗余注入**——审计波 8/10 派发各自内嵌全章文本，章节文本占每章 prompt 体量 29%（T1601，56 章已付 ~1.74M 冗余输入 token）；(b) **重复解析/实例化**——registry 每次全量重解析 truth-files.yaml（F215，8.5ms/次×≥3 次/派发，T1613 量化）、69 技能模板扫描无短路（T1606，578ms/次）、SentenceTransformer 每条目重载 + 不 close（F328）且 Route B 无失败负缓存（T1603，永久降级态每章 2×0.3-3.5s 停顿）；(c) **O(N²)**——差分快照全量重哈希（T1607）、save_state 全量 dump（T1608，132KB×16/章）、_load_previous_titles 全读前章（T1609，三规模线性实测）、integrity findings O(k²) 重写（T1610）；(d) **import 开销**——门禁子进程 96% 时间在 import（T1604：gates.cli 255ms，jieba 107.6ms 顶层拖入 + 12 门急加载）。

根因：无性能回归防线（无 benchmark 基线，C17），每处局部"正确但浪费"的实现累积成全局税。

## 目标
1. 审计波冗余注入消除：同章多审计派发共享单一章节文本注入点，冗余输入 token 占比从 29% 降至 ≤5%
2. 热路径缓存化：registry/genre-config/技能模板解析每进程一次；SentenceTransformer 进程级单例 + 失败负缓存
3. O(N²) 消除：快照/save_state/titles 增量化，56 章规模下状态保存耗时不随章数平方增长
4. 门禁 import 懒加载：gates.cli 冷启动 <50ms（按需 import jieba 与各门实现）

## 任务分解
### R1 · 审计波共享上下文（T1601，P1，收益最大）
- 审计波派发改为共享章节文本注入：每章装配一次，8-10 个审计派发引用同一份（文件引用或共享 context id），prompt 内不再各自内嵌全文
- 与 C10 协同：注入量变化前后用 TokenLedger 落账对比（56 章规模 ~1.74M token 为基线）
- **验收**：三规模（N=8/16/32）实测每章输入 token 线性；审计结论不因共享注入而退化（fixture 回归）

### R2 · 解析/模型缓存（F215 + T1606 + T1603 + F328 + T1613/T1614）
- `load_registry` 结果进程内缓存（mtime 失效）；`_build_skill_prompt` 短路已扫描模板；genre-config 缓存修正（见 C37 T1612——死缓存删除而非修复）
- SentenceTransformer：模块级单例 + EmbeddingStore close 语义 + Route B 失败负缓存（TTL 化，避免每章重试 HF 下载）
- **验收**：单测断言解析函数每进程调用 ≤1 次；Route B 断网场景第二次装配无网络等待

### R3 · O(N²) 增量化（T1607/T1608/T1609/T1610）
- save_state 增量写（脏字段/脏步骤标记）；差分快照只哈希变更文件；_load_previous_titles 缓存标题列表增量追加；integrity findings 改构建后单次写
- 与 C19（快照接线 spec #26）协同：若 #26 裁决"移除"，T1607 直接消解
- **验收**：N=16 vs N=32 章状态保存耗时比值 ≤2.5×（当前平方）；benchmark 用例入 `tests/`（C17 基线）

### R4 · 门禁懒加载（T1604）
- gates.cli 改懒 import：按 gate 名注入对应模块，jieba 等重依赖移入首个使用函数
- **验收**：`python -X importtime -c "from shenbi.gates import cli"` 顶层 <50ms；12 门全跑一遍行为不变（`just test` 绿）

## 验收（簇级）
- `just check` 全绿；新增 benchmark 基线三条（状态保存、registry 解析、门禁冷启动）防回归
- C28 全部 13 条 merged-into T1601 回写关闭

## 风险
- R1 共享注入改变审计 prompt 形状——需 fixture 级 A/B 对比审计结论一致性，防止"省 token 丢检出"
- R3 增量写与 C11（并发/durability）的 WriteLock/fsync 协议交叠——增量实现不得绕过锁协议，两 spec 联合验收

## 验证命令
- import 开销：`python -X importtime -c "from shenbi.gates import cli" 2>&1 | tail -5`（R4 验收 <50ms）
- registry 缓存：`pytest tests/unit/contracts/ -k registry -q`（解析次数断言）
- O(N²) 基线：`pytest tests/ -k "benchmark and (save_state or snapshot or titles)" -q`（入 C17 基线集）
- 冗余注入收益：C10 合入后 `shenbi-cost report` 前后对比（56 章 ~1.74M 冗余输入 token 基线，T1601）
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`T1601 <- F215, F328, F415, T1603-T1604, T1606-T1610, T1613-T1614`
- 依赖注记：T1612（死缓存）不修而删，归 C37 R2；T1615（累积注入超线性）由 C10/C28 联合量化，观测面归 C29
