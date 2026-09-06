> **Date:** 2026-08-16 | **Status:** Done (PR #153, 2026-09-06;后续 flake 修复 PR #154) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C28）| **依赖:** C10（token 计量接线——已由 spec36/PR #137 落地，三条派发路径全落账）| **范围:** contracts/legacy.py registry 缓存、gates/cli 懒加载、truth_embed/context_assemble 模型单例、audit_context_cache 四处路径错配+读抑制、gate 侧 O(N²) 重读 | **核心洞察:** registry 每次重解析（8.5ms×每派发×每门禁子进程）、门禁子进程 96% import 开销（实测 368.6ms/spawn）、gate 侧 O(N²) 全量重读——性能债直接折算为 token 与墙钟成本
> **修订注记（2026-09-04 R2，设计审查第 2 轮收敛）**：T1607 已被 spec #26 路径 3（commit 66e7f69d/PR #105）移除差分子系统而消解；T1608（save_state 步级全量 dump）**让位** C30（#44 拥有 resume 游标锚定与 staging 生命周期语义）；R1 机制从「摘要字段注入」改为「原始字节表读抑制」（摘要字段注入会破坏字节等价——字段是截断值非文件原文）；F312 死键清单从 2 处扩至 **4 处路径错配**（builder 3 + 注入块 1 组）；volume_context 无审计波消费者移出 R1；F415 有两个跨轮同号条目（C35 已立案的编号碰撞）：08-15 轮 = gate 侧 O(N²) 重读放大（本 spec R3 承接 content_uniqueness 面），08-14 轮 = chapter_drafting.py 行号引用漂移（R4 顺手修正）

# C28 · 性能反模式修复（perf-antipatterns）

## 元信息
- 簇：C28（性能反模式：重复解析/O(N²)/import 开销/冗余注入），原 13 条；本轮裁定 11 条由本 spec 关闭（T1607 resolved-by-#26、T1608 transferred-to-#44），证据等级=实验佐证（T16 三规模实测，2026-09-04 驳斥复核 12/13 存活 + 协调者逐条 VERIFY + 设计审查 2 轮）
- 成员（本 spec 关闭）：T1601-I/O 面、T1603、T1604、T1606、T1609、T1610、T1613、T1614、F215、F328、F415（08-15 content_uniqueness 面 + 08-14 行号漂移）；成员（不由本 spec 关闭）：T1607（#26 移除）、T1608（让位 #44）、T1602（归 C30/#44）、T1605/T1612（归 C37/#51）、T1611（spec36/PR #137 已落）、T1615（观测面归 C29/#43）
- 来源：thread-reports/T16.md + Z2/Z3/Z4 对应行（注意 F 编号跨轮碰撞，见修订注记）

## 背景与根因
四类反模式各自独立成灾：(a) **重复 I/O**——审计波 6 技能契约逐个直读章节全文（实测每章被读 8 次，T1614；根因=F312 路径错配 + 注入机制后置于磁盘读且只覆盖 4 个截断字段）；(b) **重复解析/实例化**——registry 每次全量重解析 truth-files.yaml（F215，实测 8.5ms/次×每派发×每门禁子进程，T1613 量化）、74 技能模板扫描无短路（T1606，实测 654.9ms/次）、SentenceTransformer 每条目重载 + 不 close（F328）且 Route B 无失败负缓存（T1603，永久降级态每章 2×0.3-3.5s 停顿）；(c) **gate 侧 O(N²) 重读**——_load_previous_titles 全读前章全文（T1609）、content_uniqueness 每章重算全部前章指纹（F415-0815，300 章 ≈9 万次读）、integrity findings O(k²) 重写（T1610）；(d) **import 开销**——门禁子进程 96% 时间在 import（T1604：`import shenbi.gates.cli` 实测 368.6ms，jieba 105ms 顶层拖入 + 11 门急加载 + logging(structlog→rich)/cli_utils/gates.shared 链）。

根因：无性能回归防线（无 benchmark 基线，C17），每处局部"正确但浪费"的实现累积成全局税。

## 目标
1. 审计波 I/O 去重：同章多审计派发共享单一磁盘读取（读抑制 + checklist 路径），章节文件每章被读次数 9→1（6 契约直读 + 3 checklist 冷路径；含共享上下文构建的那一次）；**读抑制机制本身不改变 prompt 字节**（字节等价验收只锁开关对比）；F312 路径修复按修复意图改变注入内容（world_rules 从恒空变为真内容、幻影 style 重复项消失）——这是缺陷修复的预期效果，不在字节等价闸内
2. 热路径缓存化：registry/技能模板解析按 (path, mtime_ns, size) 进程内缓存；SentenceTransformer 进程级单例 + 失败 TTL 负缓存
3. gate 侧 O(N²) 重读消除（进程内路径）：标题有界前缀读取 + 指纹 mtime 缓存 + 真 append
4. 门禁 import 懒加载：`import shenbi.gates.cli` 顶层 <50ms（按 gate 名懒加载 11 个门禁模块；jieba 移入函数体；logging/cli_utils/gates.shared/status 延迟到 main()）

### 明确出账（Revised R2）
- **T1607**：差分快照已随 #26 路径 3 整体移除——resolved-by-#26，不由本 spec 关闭
- **T1608**：save_state 步级粒度与 C30/#44 的 resume 游标锚定、staging 生命周期正面交叠——transferred-to-#44（本 spec 不触碰 machine.py/cli.py 的 save_state 调用频率与格式）
- **R1 token 侧（原"29%→≤5%"目标）**：API 路径无文件工具、prompt 仍需内嵌全文，token 占比下降只有单派发多报告（与审计域分离/G5 结构冲突，MERGE-2 已止步 6 组）或前缀缓存重构（provider 特定、system 段 per-skill 无法共享前缀）两条路——均为 prompt 架构级产品决策，超出本 spec 权限。本 spec 交付 I/O 去重 + 路径修复（prompt 字节不变的确定性收益），token 架构决策记入回写供后续 spec 立项
- **volume_context / chapter_summary 字段**：volume_context 全仓零读者（grep 无任何消费点；context_assemble 的卷上下文是独立直读）且为提取形态非原始字节——移出 R1 读抑制表，仅修 builder 路径错配防未来误用；chapter_summary 从未被填充的死字段，注记归 C37/#51 清理
- **g5.5 逐对重跑去重**（F415-0815 的 g5.5 面）：同文件×前置重复对仅来自 glob 交叠，命中率近零且无可写验收——随门禁进程内化（见回写后续建议）才有意义，本 spec 不实施

## 任务分解
### R1 · 审计波共享读取（T1614/F312 + T1601-I/O 面，P1）
- **原始字节表（读抑制的数据源）**：`SharedAuditContext` 新增 `raw_files: dict[str, str]`——键 = `_input_key(path, project_dir)`，值 = **文件完整原文**（不截断、不摘要、不提取）。`build_shared_audit_context` 为 5 个文件填充：`chapters/chapter-{chapter}.md`、`world/rules.md`、`truth/character_matrix.md`、`style/style_profile.md`、`truth/pending_hooks.md`。既有摘要字段（world_rules/character_list/style_profile/pending_hooks）保留用于现状注入块（行为不变），**不得**作为读抑制数据源（截断值 ≠ 磁盘字节，会破坏字节等价）
- **F312 四处路径错配修复**（对照 docs/framework/truth-files.yaml 规范路径）：builder `:49` `chapters/chapter-{chapter:03d}.md` → `chapters/chapter-{chapter}.md`（对齐生产写方 chapter_loop/crash_recovery/confidence_calibration 的无填充形态）；builder `:53` `truth/world_rules.md` → `world/rules.md`（truth-files.yaml:15）；builder `:71` `truth/volume_map.md` → `outline/volume_map.md`（对齐 `_shared.py:42 VOLUME_MAP_PATH`）；注入块 `dispatch_helper.py:683/:691` 的 `truth/world_rules.md` → `world/rules.md`、`truth/style_profile.md` → `style/style_profile.md`（builder 实际读 style/ 下，注入键却指 truth/ 下——world_rules 键因 builder 死路径恒空注入，style 键注入的是真内容的截断重复项，修复后重复项消失）
- **读抑制机制**：`_build_skill_prompt` 的契约 reads 磁盘读循环先查 `raw_files`（同 `_input_key`）——命中则用缓存原文，未命中才 `read_text` 落盘；`filter_to_fields`（Layer B）与 `_strip_meta_for_non_drafting` 照常作用于命中后的字节（管线位置不变，仅数据源换）。**review_checklist 生成路径的章节读取同走缓存**（review_checklist.py:271/:354 直读两处 + :272 `word_count_md` 内部再读一次 = 冷缓存下每波 3 次全文读）——装配时将 `raw_files` 中的章节字节传入（word_count_md 用缓存内容变体），消灭 checklist 侧全部读取
- **语义不变约束**：读抑制开关（开 vs 关）不改变 prompt 字节——验收以字节等价测试锁定该开关对比；F312 路径修复带来的注入内容变化（见目标 1）不在此闸内
- **验收**（fixture 项目 = `tmp_path` 内以真实 fixture 文件组装：`tests/fixtures/multi-chapter-example/chapter-*.md` 复制入 `chapters/`、`tests/fixtures/snapshots/chapter-025/truth/{character_matrix,pending_hooks}.md`、`tests/fixtures/world-rules-example.md` → `world/rules.md`、`tests/fixtures/style-profile-example.md` → `style/style_profile.md` 按规范布局放置——G0.9 合规，全部源为真实产物，无手写内容）：
  1. 单元：`raw_files[key] == path.read_text()` 对 5 文件逐一成立（断言**完整原文**，即等于文件 read_text 结果，非截断摘要）
  2. I/O 计数：spy `Path.read_text`（monkeypatch 计数，含 builder 自身读取），装配 6 审计技能 prompt + checklist 全流程后章节文件 read_text 次数 == 1（当前 9：6 契约 + 3 checklist 冷路径）
  3. 字节等价：读抑制开/关两种构建路径产出的全部 prompt 字节完全一致（`uv run pytest tests/unit/pipeline/ -k "read_suppression" -q`）
  4. 路径修复：fixture 项目上 `raw_files` 含 world/rules.md 键（修复前 builder 读 truth/world_rules.md 恒空）

### R2 · 解析/模型缓存（F215 + T1606 + T1603 + F328 + T1613/T1614-解析面）
- `load_registry` 按 `(REGISTRY_PATH, mtime_ns, size)` 进程内缓存：命中返回缓存模型；文件变更（含同秒替换，mtime_ns 粒度）自动失效重解析——满足 `audit/snapshot.py:22-29` "跨轮词表可变"的刻意不缓存关切（mtime 键两全）；缓存实例**只读约定**：grep 全部调用方确认无 mutation 点（2026-09-04 复核已确认零 mutation 调用方），返回共享实例不复制
- `_init_truth_templates` 前置短路：目标 truth 模板文件全部存在时直接返回，不跑 74 技能全量扫描（T1606）；扫描结果同键缓存
- SentenceTransformer：模块级单例（`threading.Lock` 双检锁护初始化——现状模型构造点为 assemble_context→`_route_b`（context_assemble.py:158，单线程顺序）与 genesis `embed_and_store`（truth_embed.py:121），无并发构造路径；锁作为廉价防御保留）。**close 语义指 `EmbeddingStore` 的 sqlite 句柄**（SentenceTransformer 无 close API，模型对象随单例常驻即设计意图）：genesis `_update_route_b` 循环改用单例（消灭逐条目重载，F328）+ finally 关闭 EmbeddingStore 句柄（现状 genesis 也从不关句柄）。Route B 失败 TTL 负缓存（失败异常类型+时间戳，TTL 10min，到期重试）
- **验收**：单测断言 mtime 不变时 `load_registry` 底层 YAML 解析次数 == 1（touch 后 == 2）；模板齐全时 `_collect_declared_truth_fields` 不被调用（spy）；Route B 断网场景（mock HF 401）第二次装配无网络调用（负缓存命中）；单例并发初始化防御测试（两线程同时首调，模型构造次数 == 1——现状无并发构造路径，锁为防御性）

### R3 · gate 侧 O(N²) 重读消除（T1609 + T1610 + F415-0815 content_uniqueness 面）
- `_load_previous_titles`（chapter_loop.py:2142-2170，**进程内调用**——chapter_loop 是管线进程本体，收益落生产路径）：改每文件有界前缀读取（读首 4KB 或至首个 H1，取先到者）——消灭 N-1 个 ~24KB 全文读取。**顺带行为修正（审查 R2 轮发现，R3 轮扩大）**：现状两处提取都锚定位置 0——`_load_previous_titles` 的 `re.match(r"^#\s+", ch_text)` 与 `_extract_chapter_title`（chapter_loop.py:2138，`re.match` 带 `re.M` 仍只锚位置 0）对 meta-first 章（真实产物首块为 `## PRE_WRITE_CHECK`，H1 在 ~行 10，见 `tests/fixtures/chapter-7-example.md`）**双零提取——当前章与前章标题都为空，标题查重是全链路静默 no-op**；两处同改为前缀内 `re.search(r"^#\s+(.+)", prefix, re.MULTILINE)`（首 H1），恢复查重本意。`check_chapter_title` 期望真标题（复核：生产 H1 不含 ASCII 数字章号），修正不破坏其语义
- `content_uniqueness`（g4/chapter_drafting.py:279-309）：章节指纹 (path, mtime_ns, size) 进程内缓存，每章只算本章指纹，其余章查缓存（glob 覆盖全部其他章，含后置章）。**范围声明**：生产 G4 经 `run_gate_g4` 子进程逐派发（dispatch_helper.py:2694-2703），进程内缓存每 spawn 冷启动——本修复收益面 = 进程内多文件调用（g5.5 内嵌 gate_G4、tests、未来门禁进程内化后生产路径）；300 章 9 万次读 → 300 次的账只在进程内形态成立，回写如实注记
- `_append_integrity_findings`（dispatch_helper.py:1132-1152）：`locked_transact` 全量读+重写改真 append（`open("a")` 在既有 flock 临界区内），保持 jsonl 语义
- **验收**：(1) T1609：合成规模语料（真实 fixture 章按确定性变换扩展 N=56/112/224——变换 = 逐文件改写 H1 行为 `# 第{i}章 · {原标题}（变体 {i}）`、正文原样保留，变换脚本入 tests/，G0.9：源是真实产物复制变体）上，单章标题查重的文件读取字节数 ≤ 4096×N（当前 ~24KB×N）；meta-first 章（chapter-7-example.md 形态）**两处**标题提取（`_load_previous_titles` + `_extract_chapter_title`）均非空（现状双空——全链路 no-op 证据）；(2) content_uniqueness：N 章语料**同一进程内**全量跑两遍，第二遍总读取次数 == N（缓存命中 N-1）；(3) T1610：200 次 append 后文件内容与全量重写式逐字节一致 + 总写放大字节 O(k)（线性）；(4) `uv run pytest tests/ -m benchmark -q` 三条基线绿（registry 解析、门禁冷启动、标题有界读取字节）——基线用例入 `tests/benchmark/`（既有 pytest-benchmark + `-m benchmark` 标记基建）
- **合规注记**：指纹/标题缓存是进程内 memoization（无输出文件副作用、verdict 在 (path, mtime_ns, size) 键下幂等、pytest 间不复用）——满足 AGENTS.md「gate 检查器纯函数幂等无副作用」的字母与精神
- **协同注记**：本 R 不触碰 save_state 频率/格式（T1608 让位 #44）；写路径全部走既有 flock/safe_write 协议（C11 已 Done PR #140 落地版），无新并发面

### R4 · 门禁懒加载（T1604 + F415-0814）
- `gates/cli.py`：11 个门禁模块（g0-g7、g_dispatch、g_reconcile、g_transition）顶层 import 改按 gate 名懒加载（dispatch dict → loader 函数内 import）；`from shenbi.logging import ...`（含 `:30` 模块级 `log = get_logger(__name__)` 绑定——一并移入 main()/函数体）、`from shenbi.cli_utils import emit_json`、`from shenbi.gates.shared import ...`、`from shenbi.status import GateStatus` 延迟进 main()/handler 函数体
- `src/shenbi/text/cjk.py:10-11`：顶层 `import jieba`/`jieba.posseg` 移入首个使用函数体（仅 G6 需要）
- F415-0814 顺手修正：`g4/chapter_drafting.py:93` 引用 `(SKILL.md:125)` 改符号引用（引规则原文「章节标题不要包含章节号」，对齐 C23 行号锚点改符号引用方向；实际规则在 SKILL.md:140，漂移 15 行）
- **验收**：`uv run python -X importtime -c "from shenbi.gates import cli" 2>&1 | tail -3` 顶层累计 <50ms（当前实测 368.6ms）；11 门全跑一遍行为不变（`uv run pytest tests/gates/ -q` 绿 + `just check` 全绿）

## 验收（簇级）
- `just check` 全绿；`uv run pytest tests/ -m benchmark -q` 三条基线绿（registry 解析、门禁冷启动、标题有界读取）防回归
- 回写关闭 11 条（同下方回写节口径）：T1601（I/O 面，吸收 T1614/F312）、T1603、T1604（吸收 F415-0814）、T1606、T1609（含 `_extract_chapter_title` 全链路 no-op 行为修正）、T1610、T1613（吸收 F215）、T1614、F215、F328、F415-0815（content_uniqueness 面，进程内范围注记）；T1607 注 resolved-by-#26、T1608 注 transferred-to-#44

## 风险
- R1 读抑制：缓存键与 `_input_key` 不一致会把错字节注入 prompt——字节等价测试（开/关两路径对比）是硬闸；raw_files 必须存完整原文（摘要字段做数据源 = 字节等价破坏，已在机制层排除）
- R2 registry 缓存：跨轮词表变更依赖 mtime_ns 失效——同秒原地编辑且 size 不变的病理场景接受为已知残余风险（生产中 registry 只经 PR 变更，进程生命期内不变）
- R2 单例：~1.3GB 模型常驻进程——当前每次装配/每 genesis 条目重新构造（顺序执行，2×/章 + genesis 逐条目），单例化后全进程共享一份；EmbeddingStore 句柄由 genesis finally 关闭
- R3 标题行为修正：meta-first 章查重从 no-op 变为生效——若历史产物存在同题章，pipeline resume 场景可能新报重题（这是查重本意，非回归；记 deviation 观察）
- R3 真 append：现状 locked_transact 以原子替换收尾（不撕裂文件，最坏丢末条）；真 append 单调写崩溃时可撕裂**末行**——读取侧按行解析需容忍末行残缺（跳过不完整尾行）。为 O(k) 写放大收益接受此 delta，flock 临界区不变

## 验证命令
- import 开销：`uv run python -X importtime -c "from shenbi.gates import cli" 2>&1 | tail -3`（R4 验收 <50ms）
- registry 缓存：`uv run pytest tests/unit/contracts/ -k registry -q`（解析次数断言，新增）
- O(N²) 基线：`uv run pytest tests/ -m benchmark -q`（入 tests/benchmark/ 既有标记基建）
- 读抑制：`uv run pytest tests/unit/pipeline/ -k "read_suppression" -q`（新增）
- 回归：`just check` 全绿

## 回写
- 本 spec 关闭 11 条：T1601（I/O 面，吸收 T1614/F312）、T1603、T1604（吸收 F415-0814）、T1606、T1609（含 `_extract_chapter_title` 全链路 no-op 行为修正）、T1610、T1613（吸收 F215）、T1614、F215、F328、F415-0815（content_uniqueness 面，进程内范围注记）（phase4 §3 merged 关系按此修订执行）
- 出账注记：T1607 resolved-by-#26（66e7f69d/PR #105）；T1608 transferred-to-#44（save_state 粒度与 C30 resume 游标/staging 语义同域，防双 spec 冲突设计）；F415-0815 的 g5.5 面随门禁进程内化才有意义（见下）
- 后续立项建议（非本 spec 交付）：(1) 审计波 token 架构（单派发多报告 vs 前缀缓存重构）需产品裁决后另立 spec——本 spec 的确定性 prompt 重构基线（T16 方法）可作其输入；(2) 门禁进程内化（run_gate_g4/g3 子进程 → 进程内函数调用）——既消灭 0.29s×5-6/章 spawn 税，也使 R3 指纹缓存在生产路径生效；T1604 本 spec 只做 lazy import 过渡方案
- T1615（累积注入超线性）观测面归 C29/#43；T1612 死缓存删除、chapter_summary 死字段归 C37/#51
