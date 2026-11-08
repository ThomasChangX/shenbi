# Spec #99 · settle 增量契约基底行保真（settle-base-row-fidelity）：引语类基底行改写族根治

**日期**：2026-11-08 ｜ **系列**：生产运行慢族根治批（束4-束7 三窗实锤；spec #98 束7 分叉落点件） ｜ **状态**：Active（**r3** 2026-11-08——阶段 3 设计审查 Critical 落地：束7 窗口重定性为 H4 假阳性死锁[自陈行 own-block 内实证]→H4 升主/H1 降级慢性族残余；标题语法四表面单源化；T2(a) seam 修正为纯子函数；⑤ 扩展第二矛盾+入验收配对；INDEX 同步。r2 2026-11-08 价值门六修订；r1 立项同日） ｜ **优先级**：🟠 P1（生产税：每窗 1 接骨+手术风险——probe31 以来第三个实锤窗）
**依赖**：无硬依赖（与批次 A 文件域不冲突——主战场 skills/shenbi-state-settling SKILL.md+G4.ss 反馈文本+`_strip_increment_section`+dispatch_helper 注入面，不抢 chapter_loop 逻辑区）；证据源=novel-xinghuo-vol1 运行工件（blob 验尸法）。
**动机证据**（三窗实锤链；r3 重定性）：①probe29-31：matrix_structure content_dropped 为跨窗慢性 P1（pre-#23 时代「LLM 增量语义问题」——批 #23 注入终结表格行平台期）；②束4 裁决 #12：手工手术面（matcher 限度另案已记 #86）；③束7 裁决 #19——**r3 重定性（设计审查 Critical，blob 实证）**：该窗**整个 drop set 仅一行且系 own-block 内行**（a1 prompt blob：自陈行 `@21872` 落 `## 第 47 章状态增量` 块内 `@21504-21924`；a2 反馈 `content_dropped:1行（去重后 1）` 仅列该行）——按 probe31 keyed-upsert 语义（本章块=可整体替换单元），a1 的「改写」是**合法替换**、a2/a3 的拒绝复原是**契约正确**，**门错了**（H4 假阳性死锁）而非模型违 append-only 铁律；「verbatim 反馈在场仍复发」叙事系对反馈本身有误场面的误读。④机械根因（实证三层）：`_strip_increment_section` 正则（state_settling.py:322）不容数字两侧空格——live ch44-46 无空格形（:999/:1009/:1029）豁免生效、ch47/48 空格形（:1049/:1068，模型自撰+合并器按键名原样接受）豁免静默失效→own-block 被当基底比对→合法重派死锁。**标题语法漂移系四表面族**（r3 盘点）：gate 严格形（state_settling.py:322）vs 提取器容错形（read_extractors.py:916-918 `^##\s*第\s*{n}\s*章\s*状态增量`）vs 写径精确匹配（truth_io.py:1585 `line.strip() != heading`——重派标题形与 live 不一致时 `_replace_section` 失配→APPEND 重复块隐患）vs 教学示例空格形（chapter_loop.py:955 防回退令示例 `## 第 2 章状态增量`=漂移源）。

**触及的不变量维度**：无（truth 增量语义/prompt 契约面；④系恢复 probe31 已裁定语义的正则 bug 修复+四表面单源化，非改判据——见 T1 豁免声明）。

---

## 0. 根因假设（r3 重排序）

- **H4（主，束7 面）**：own-block 豁免正则空格不容→空格形标题使豁免静默失效→重派面把本章块当基底比对→合法 keyed-upsert 重派被误判 content_dropped→反馈指令与 upsert 契约矛盾→死锁至 3/3 熔断+手术。束7 窗口整体由本假设解释（drop set 仅 own-block 一行，blob 实证）。
- **H1（降级：pre-#23 时代慢性族残余假设）**：引语类基底行存在「保真-准确」语义引力——模型按本章正文原句「修正」**其他章块/基底区**的引语行。活测试条件：仅当改写发生在 own-block 之外才可观测（束7 无此证据；probe29-31 系 pre-#23 时代证据，族同源性 T0 核）。若 T0 判定族不同源→H1 面缩窄为「首派教学预防」，①③保留为预防面。
- **H2**：反馈指令的「原样保留」缺少引语行专用锚形（对表格行有正例 `| a | 1 |` 形，对引语行无「原句保持+新句另起」的双行正例）。
- **H3（r3 措辞校准）**：**重派面预注入已是现状**（`_format_drops` verbatim 清单+指令+正例）；首派指令区**有通用锚**（#23 注入「NEVER modify any existing row」，a1 prompt 实证在场）——残余缺口精确形=**首派缺引语形正例/verbatim 数据锚**。

## 1. 任务分解（r3）

- **T0 blob 验尸+表面盘点（半天，无实弹）**：束7 三派（dispatches 00264-00266——attempt 元数据均 1/feedback_ref null，**分派依据=prompt 反馈在场性**：「上次重派」计数 a1=0/a2=1/a3=2 已验）prompt/response 逐字——**确认性验尸**（束7=H4 死锁已由设计审查预判，T0 补齐逐派证据链：own-block 豁免失效的逐派影响/47 块行集与 drop 清单关系[已预判：仅差异行入清单，同序 verbatim 行被 _seq_drops 匹配]/a1 前首派[seq 1214]的块创建形与标题形）+ probe29-31 族同源判定（旧 POC 原始 blob 磁盘可用性未核——不可用则按 SKILL :98 内注+会话记忆判并记 deviation）+**标题语法四表面盘点核实**（gate/提取器/写径/教学示例四处的现行形与交叉 drift 面，含 `_replace_section` 失配→APPEND 重复块隐患的触发条件推演）。
- **T1 修复面（branch+PR，同批强制①③④⑤，r3）**：
  ①SKILL.md 增量契约补引语行双行正例（「原句保持原样；正文如有更全原句→新起一行『XX 补全（第N章原句）』」）——**正例须自行构造并过离线三验**（三验=束7 手术口径：改后 G4 判定通过/与 live diff 仅新增行/append-only 语义保持——r3 定义；束7 手术「两全形」现盘仅复原半[character_matrix.md:1066]不得引用为已实证形）；**同批并入**：SKILL.md :248 legacy 行（character_matrix 信息边界仍教 `create_or_overwrite（逐字复现 live 基底＋仅追加增量）`——与 append_dedup 契约矛盾且教基底重发反模式）改口径；正例与教学统一**无空格规范形** `## 第N章状态增量`；
  ②（现状声明，非新建）重派预注入已是现状（`_format_drops`+cli.py:367 g4_note）；残余=首派引语形锚，并入①教学面，不新建通道；
  ③G4.ss `_format_drops` 报文补引语行双行正例（现仅表格形 :209-210；引语判别可复用 quote_verbatim.py:25 NESTED_QUOTE_RE）；
  ④**单源化标题语法**（r3 升格）：新建共享 helper（容错正则 `^##\s*第\s*{N}\s*章\s*状态增量`，唯一定义——gate `_strip_increment_section` 与提取器 read_extractors 共用；**豁免声明：恢复 probe31 已裁定语义的正则 bug 修复+消除同语法双字面量漂移，非改门检判定语义**）；写径 `_replace_section` 匹配面以同 helper 归一（消重复块隐患）或经 T0 推演后声明不修理由；**配对义务（强制）**：④必须与①③同批（④解死锁后 own-block 内引语改写对 G4 静默——①③管豁免域保真+首派预防），⑤同批；
  ⑤（r3 扩展）#23 注入双矛盾修正（dispatch_helper.py:1460-1470）：单章口径「MUST be a **new** block **only**」→双章批口径；「NEVER modify or extend any existing row or **any earlier `## 第N章状态增量` section**」字面禁止同章块重发——修正为明确 own-block keyed-upsert 可替换性（probe31 语义）；**⑤ 入验收 #2 同批清单**（唯一固定该注入的测试 test_append_dedup_increment_injection.py:89 仅查标题串——⑤ 的双矛盾修正须补断言防回退）；
  **红线保持**：不改 content_dropped 判定语义与 append-only 铁律（④按豁免声明执行）。
- **T2 离线回放验收（r3 seam 修正）**：**(a) 纯子函数直测红绿**——`_strip_increment_section`/`_dropped_content_lines` 直测（真纯函数，无文件 IO）：改前（严格正则）own-block 行入 drop 清单红/改后（④容错+单源）豁免剥离绿；`_format_drops` 引语正例在场断言（③）；`_replace_section` 归一化断言（若修）；**配对机械化**：容错正则在场 ⇒ 引语双行正例必须在场（断言防④单发）。**(b) blob 物化回放（harness 声明）**——束7 blob 经 `_increment_units`+upsert 物化 staged/live/sidecar 兄弟（G0.9 允许的结构性构造）过 `_check_matrix_structure(pf)` 整链：改前 FAIL→改后 PASS——r3 注记：drop set=1 行 own-block 行，绿由④单独即可产生（③系反馈文本不影响判定）——红绿归因已定。**(c) 实弹疗效**归 T3。
- **T3 实弹验收（搭卷二续跑窗，不开新探针；r3 观测拆分）**：**观测线 1（④ 主疗效）**：后续束窗 settle 步 **0 接骨 0 手术**（重派合法替换不再误判）；**观测线 2（①③ 预防面疗效）**：首派引语保真——仅当改写发生于 own-block 之外才可观测（束7 无此类证据，本线系慢性族预防的活测试）；两线分记，④ 成功不得读作①③ 有效（反之亦然）。

## 2. 验收（r3）

1. T0 验尸+表面盘点报告（确认性证据链+族同源判定+四表面盘点）落 `docs/research/`；
2. T1 PR 合并（CI 全绿+G4 判定语义零漂移断言[既有夹具全无空格形，④不翻转既有断言]+**①③④⑤同批配对落地**+④配对机械化断言+⑤双矛盾修正带防回退断言）；
3. T2(a)(b) 红绿记录（纯子函数直测+blob 物化整链，改前 FAIL→改后 PASS）；
4. T3 实弹窗疗效记录落 vol1-ledger（束级条目，两观测线分记）。

## 3. 风险与回退（r3）

- 修复面均为 prompt/教学/正则面——回退=还原文本与正则，无运行态迁移；
- H1 若 T0 判族不同源（probe31 形≠束7 形已由重定性预设成立）→①③定位=慢性族预防面（束4 #12 手术面证据仍独立成立）；
- ④单发风险（豁免域保真失守）已由配对义务+机械化断言阻断；
- 写径归一化若经 T0 推演判定不做→声明重复块隐患的触发条件与现况评估（当前 live 无重复块）。
