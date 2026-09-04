> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-04) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C28）| **依赖:** C10（token 计量接线——已由 spec36/PR #137 落地，三条派发路径全落账）| **范围:** contracts/legacy.py registry 缓存、gates/cli 懒加载、truth_embed/context_assemble 模型单例、audit_context_cache 死键修复、gate 侧重读去重 | **核心洞察:** registry 每次重解析（8.5ms×每派发×每门禁子进程）、门禁子进程 96% import 开销（实测 368.6ms/spawn）、gate 侧 O(N²) 全量重读——性能债直接折算为 token 与墙钟成本
> **修订注记（2026-09-04，价值门+设计审查 R1 轮）**：T1607 已被 spec #26 路径 3（commit 66e7f69d/PR #105）移除差分子系统而消解；T1608（save_state 步级全量 dump）**让位** C30（#44 拥有 resume 游标锚定与 staging 生命周期语义，本簇实施步级游标会与其正面冲突）——两者均不由本 spec 关闭；F415 有两个跨轮同号条目（C35 已立案的编号碰撞）：08-15 轮 = gate 侧 O(N²) 重读放大（本 spec R3 承接），08-14 轮 = chapter_drafting.py 行号引用漂移（本 spec R4 顺手修正）

# C28 · 性能反模式修复（perf-antipatterns）

## 元信息
- 簇：C28（性能反模式：重复解析/O(N²)/import 开销/冗余注入），原 13 条；本轮裁定 11 条由本 spec 关闭（T1607 resolved-by-#26、T1608 transferred-to-#44），证据等级=实验佐证（T16 三规模实测，2026-09-04 驳斥复核 12/13 存活 + 协调者逐条 VERIFY）
- 成员（本 spec 关闭）：T1601-I/O 面（见 R1 范围裁剪）、T1603、T1604、T1606、T1609、T1610、T1613、T1614、F215、F328、F415（08-15 gate 重读放大）；成员（不由本 spec 关闭）：T1607（#26 移除）、T1608（让位 #44）、T1602（归 C30/#44）、T1605/T1612（归 C37/#51）、T1611（spec36/PR #137 已落）、T1615（观测面归 C29/#43）
- 来源：thread-reports/T16.md + Z2/Z3/Z4 对应行（注意 F 编号跨轮碰撞，见修订注记）

## 背景与根因
四类反模式各自独立成灾：(a) **重复 I/O**——审计波 6 技能契约逐个直读章节全文（实测每章被读 8 次，T1614；根因=F312 双死键 + 注入机制后置于磁盘读）；(b) **重复解析/实例化**——registry 每次全量重解析 truth-files.yaml（F215，实测 8.5ms/次×每派发×每门禁子进程，T1613 量化）、74 技能模板扫描无短路（T1606，实测 654.9ms/次）、SentenceTransformer 每条目重载 + 不 close（F328）且 Route B 无失败负缓存（T1603，永久降级态每章 2×0.3-3.5s 停顿）；(c) **gate 侧 O(N²) 重读**——_load_previous_titles 全读前章（T1609）、content_uniqueness 每章重算全部前章指纹（F415-0815，300 章 ≈9 万次读）、g5.5 每文件×每前置逐跑 G4（F415-0815）、integrity findings O(k²) 重写（T1610）；(d) **import 开销**——门禁子进程 96% 时间在 import（T1604：`import shenbi.gates.cli` 实测 368.6ms，jieba 105ms 顶层拖入 + 12 门急加载 + logging/structlog/rich/contracts 链）。

根因：无性能回归防线（无 benchmark 基线，C17），每处局部"正确但浪费"的实现累积成全局税。

## 目标
1. 审计波 I/O 去重：同章多审计派发共享单一磁盘读取（读抑制），章节文件每章被读次数 8→1；prompt 字节内容完全不变（零语义风险）
2. 热路径缓存化：registry/技能模板解析按 (path, mtime_ns, size) 进程内缓存；SentenceTransformer 进程级单例 + 失败 TTL 负缓存
3. gate 侧 O(N²) 重读消除：标题/指纹 mtime 缓存 + 真 append
4. 门禁 import 懒加载：`import shenbi.gates.cli` 顶层 <50ms（按 gate 名懒加载门禁模块；jieba 移入函数体；logging/cli_utils/gates.shared 延迟到 main()）

### 明确出账（Revised）
- **T1607**：差分快照已随 #26 路径 3 整体移除（src 零残留，CHAPTER_STEPS 无快照步）——resolved-by-#26，不由本 spec 关闭
- **T1608**：save_state 步级粒度与 C30/#44 的 resume 游标锚定、staging 生命周期正面交叠——transferred-to-#44，不由本 spec 关闭（本 spec 不触碰 machine.py/cli.py 的 save_state 调用频率与格式）
- **R1 token 侧（原"29%→≤5%"目标）**：API 路径无文件工具、prompt 仍需内嵌全文，token 占比下降只有单派发多报告（与审计域分离/G5 结构冲突，MERGE-2 已止步 6 组）或前缀缓存重构（provider 特定、system 段 per-skill 无法共享前缀）两条路——均为 prompt 架构级产品决策，超出本 spec 权限。本 spec 交付 I/O 去重 + 死键修复（prompt 字节不变的确定性收益），token 架构决策记入回写供后续 spec 立项

## 任务分解
### R1 · 审计波共享读取（T1614/F312 + T1601-I/O 面，P1）
- **读抑制机制**：`build_shared_audit_context` 在磁盘读循环**之前**构建（含修复后字段）；`_build_skill_prompt` 的契约 reads 磁盘读循环先查共享上下文表——命中（同文件同 `_input_key`）则用缓存字节，未命中才落盘——同章 8 处读取收敛为 1 处
- **F312 双死键修复**：`audit_context_cache.py:49` `chapter-{chapter:03d}.md` → 与生产写方一致的无填充 `chapter-{chapter}.md`（写方：chapter_loop/crash_recovery/confidence_calibration）；`:71` `truth/volume_map.md` → `outline/volume_map.md`（对齐 `_shared.py:42 VOLUME_MAP_PATH` 与 truth-files.yaml）
- **共享上下文扩容**：chapter_text、volume_context 两字段纳入读抑制表（原有 world_rules/character_list/style_profile/pending_hooks 四字段同机制）
- **语义不变约束**：读抑制只改变读取来源，注入字节与原磁盘读字节必须完全一致——验收以字节等价测试锁定（见下）
- **验收**：(1) fixture 驱动单测：spy `Path.read_text`（monkeypatch 计数），装配 6 审计技能 prompt 时章节文件 read_text 次数 == 1（当前 8）；(2) 字节等价回归：同一 fixture 项目，读抑制开/关两种构建路径产出的 prompt 字节完全一致（`pytest tests/unit/pipeline/ -k "shared_read or read_suppression" -q`）；(3) 死键单测：真实 fixture 项目（`tests/fixtures/`）上 `SharedAuditContext.chapter_text` 非空、`volume_context` 非空

### R2 · 解析/模型缓存（F215 + T1606 + T1603 + F328 + T1613/T1614-解析面）
- `load_registry` 按 `(REGISTRY_PATH, mtime_ns, size)` 进程内缓存：命中返回缓存模型；文件变更（含同秒替换，mtime_ns 粒度）自动失效重解析——满足 `audit/snapshot.py:22-29` "跨轮词表可变"的刻意不缓存关切（mtime 键两全）；缓存实例**只读约定**：grep 全部调用方确认无 mutation 点，返回共享实例不复制
- `_init_truth_templates` 前置短路：目标 truth 模板文件全部存在时直接返回，不跑 74 技能全量扫描（T1606）；扫描结果同键缓存
- SentenceTransformer：模块级单例（`threading.Lock` 双检锁护初始化——审计波 6 线程并发首装不竞态）；Route B 失败 TTL 负缓存（失败异常类型+时间戳，TTL 10min，到期重试）；genesis `_update_route_b` 循环改用单例 + finally 显式 close（F328）
- **验收**：单测断言 mtime 不变时 `load_registry` 底层 YAML 解析次数 == 1（touch 后 == 2）；模板齐全时 `_collect_declared_truth_fields` 不被调用（spy）；Route B 断网场景（mock HF 401）第二次装配无网络调用（负缓存命中）；单例并发初始化测试（两线程同时首调，模型构造次数 == 1）

### R3 · gate 侧 O(N²) 重读消除（T1609 + T1610 + F415-0815）
- `_load_previous_titles`（chapter_loop.py:2142-2170）：改每文件只读头部（标题在文件首行 H1，读首 512B 即可），或标题索引逐章 append——消灭 N-1 个全文读取
- `content_uniqueness`（g4/chapter_drafting.py:261-278）：章节指纹 (path, mtime_ns, size) 缓存，每章只算本章指纹，前置章查缓存——消灭每章 O(N) 重算（300 章 9 万次读 → 300 次）
- g5.5（g5.py:264-298）：期望输出 glob × 前置 skill 的逐对 G4 重跑去重（同文件同前置的结果 mtime 缓存）
- `_append_integrity_findings`（dispatch_helper.py:1132-1152）：`locked_transact` 全量读+重写改真 append（`open("a")` 在既有 flock 临界区内），保持 jsonl 语义
- **验收**：(1) T1609：合成规模语料（真实 fixture 章 procedurally 扩展 N=56/112/224，G0.9——由真实产物复制变体，非手写）上，单章标题查重的文件读取字节数 ≤ 512B×N（当前 ~24KB×N）；(2) content_uniqueness：N 章语料全量跑一遍后第二遍总读取次数 == N（每章一次，缓存命中 N-1）；(3) T1610：200 次 append 后文件内容与全量重写式逐字节一致 + 总写放大字节 O(k)（线性）；(4) `pytest tests/ -m benchmark -q` 三条基线绿（registry 解析、门禁冷启动、标题/指纹读取）——基线用例入 `tests/benchmark/`（既有 pytest-benchmark + `-m benchmark` 标记基建）
- **协同注记**：本 R 不触碰 save_state 频率/格式（T1608 让位 #44）；写路径全部走既有 flock/safe_write 协议（C11 已 Done PR #140 落地版），无新并发面

### R4 · 门禁懒加载（T1604 + F415-0814）
- `gates/cli.py`：12 个门禁模块顶层 import 改按 gate 名懒加载（dispatch dict → loader 函数内 import）；`from shenbi.logging import ...`、`from shenbi.cli_utils import emit_json`、`from shenbi.gates.shared import ...`、`from shenbi.status import GateStatus` 延迟进 main()/handler 函数体
- `src/shenbi/text/cjk.py:10-11`：顶层 `import jieba`/`jieba.posseg` 移入首个使用函数体（仅 G6 需要）
- F415-0814 顺手修正：`g4/chapter_drafting.py:93` 引用 `(SKILL.md:125)` 改符号引用（引规则原文「章节标题不要包含章节号」，对齐 C23 行号锚点改符号引用方向）
- **验收**：`uv run python -X importtime -c "from shenbi.gates import cli" 2>&1 | tail -3` 顶层累计 <50ms（当前实测 368.6ms）；12 门全跑一遍行为不变（`uv run pytest tests/gates/ -q` 绿 + `just check` 全绿）

## 验收（簇级）
- `just check` 全绿；`uv run pytest tests/ -m benchmark -q` 三条基线绿（registry 解析、门禁冷启动、标题/指纹读取字节）防回归
- 回写关闭 11 条：T1601（I/O 面）、T1603、T1604、T1606、T1609、T1610、T1613、T1614、F215、F328、F415（两轮条目分注）；T1607 注 resolved-by-#26、T1608 注 transferred-to-#44

## 风险
- R1 读抑制：缓存键与 `_input_key` 不一致会把错字节注入 prompt——字节等价测试（开/关两路径对比）是硬闸
- R2 registry 缓存：跨轮词表变更依赖 mtime_ns 失效——同秒原地编辑且 size 不变的病理场景接受为已知残余风险（生产中 registry 只经 PR 变更，进程生命期内不变）
- R2 单例：~1.3GB 模型常驻进程——审计波 6 线程共享一实例（当前每线程各装一份更糟）；close 语义由 genesis finally 保证
- R3 真 append：jsonl 半行损坏风险与现状相同（全量重写同样不防中断），flock 临界区不变

## 验证命令
- import 开销：`uv run python -X importtime -c "from shenbi.gates import cli" 2>&1 | tail -3`（R4 验收 <50ms）
- registry 缓存：`uv run pytest tests/unit/contracts/ -k registry -q`（解析次数断言，新增）
- O(N²) 基线：`uv run pytest tests/ -m benchmark -q`（入 tests/benchmark/ 既有标记基建）
- 读抑制：`uv run pytest tests/unit/pipeline/ -k "shared_read or read_suppression" -q`（新增）
- 回归：`just check` 全绿

## 回写
- 本 spec 关闭：`T1601(I/O面) <- T1614, F312；T1603；T1604 <- F415-0814；T1606；T1609；T1610；T1613 <- F215；F328；F415-0815`（11 条，phase4 §3 merged 关系按此修订执行）
- 出账注记：T1607 resolved-by-#26（66e7f69d/PR #105）；T1608 transferred-to-#44（save_state 粒度与 C30 resume 游标/staging 语义同域，防双 spec 冲突设计）
- 后续立项建议（非本 spec 交付）：审计波 token 架构（单派发多报告 vs 前缀缓存重构）需产品裁决后另立 spec——本 spec 的确定性 prompt 重构基线（T16 方法）可作其输入
- T1615（累积注入超线性）观测面归 C29/#43；T1612 死缓存删除归 C37/#51
