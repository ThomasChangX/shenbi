# Spec #99 · settle 增量契约基底行保真（settle-base-row-fidelity）：引语类基底行改写族根治

**日期**：2026-11-08 ｜ **系列**：生产运行慢族根治批（束4-束7 三窗实锤；spec #98 束7 分叉落点件） ｜ **状态**：Active（**r4** 2026-11-08——轮 2 重审修复：C1 bundle 孪生块豁免扩展裁定+⑤配对前置；I1 铁律 0 own-block 排除条款；I2 锚点与边界扫描统一入 helper；I3 验收依据改写+T0 判别法[空格 own-block 下被丢行=H4 窗口误归因]；I4 写径归一入批强制。r3=轮 1 重定性；r2=价值门六修订；r1 立项同日） ｜ **优先级**：🟠 P1（生产税：每窗 1 接骨+手术风险——probe31 以来第三个实锤窗）
**依赖**：无硬依赖（与批次 A 文件域不冲突）；证据源=novel-xinghuo-vol1 运行工件（blob 验尸法）。
**动机证据**（r3 重定性+r4 补强）：①probe29-31：content_dropped 跨窗慢性 P1（pre-#23 时代）——**r4 判别法待 T0 裁**：其被丢行位于空格 own-block 标题下（H4 窗口误归因 H1）还是基底区（真 H1）——该判定直接控制①③存续合理性；②束4 裁决 #12：手工手术面（matcher 限度另案 #86）——归因待同判别法复核；③束7 裁决 #19——重定性为 **H4 假阳性死锁**（blob 实证：a1 prompt 自陈行 `@21872` 落 `## 第 47 章状态增量` 块 `@21504-21924` 内；a2 反馈 `content_dropped:1行（去重后 1）` 仅列该行；**三派 response 逐字全在场**（a2 blob=`8600f0fa…` 20665B sha256 自校验过——r4.2 勘误：r4.1（轮 3）引入的「缺失」声明系哈希转录错）且全部一致改写为更全章句——模型按 probe31 keyed-upsert 语义合法替换、**门错**）；④机械根因四表面（gate 严格形 state_settling.py:322/提取器容错形 read_extractors.py:916-918/写径精确匹配 truth_io.py:1585[失配→`_replace_section` None→EOF 追加重复块，链路 truth_io.py:1642-1662 实证]/教学示例空格形 chapter_loop.py:955=漂移源；第五邻接面 read_extractors.py:52 `_SECTION_UNIT_RE` 已容错——附记兼容不改）；**空格形系长期生产现象**（fixture spec95/00189-reads :92/:108 已有 `## 第 3 章状态增量` 形——「ch47/48 模型自撰」表述不成立，首派 00255 发空格双块只是延续）。

**触及的不变量维度**：无（truth 增量语义/prompt 契约面；④系恢复 probe31 已裁定语义+单源化，非改判据——见 T1 豁免声明）。

---

## 0. 根因假设（r4）

- **H4（主，束7 面）**：own-block 豁免正则空格不容→豁免静默失效→合法 keyed-upsert 重派被误判→矛盾指令死锁。束7 窗口整体由此解释（blob 实证）。**扩展面（r4/C1）**：`_current_settle_chapter` 只返 sidecar 首章（=47），bundle 重派时孪生块（48）重派发但不豁免——同型死锁对 follower 块敞开（束7 **a1 未重发 48 块；a2/a3 均重发**[00265/00266 response 实证，均与 live 逐字同稿故 48 面未触发]——follower 重发系观测行为 2/3 而非推测，⑤ 双章口径下 follower 块合法更新即暴露无豁免死锁）。
- **H1（降级：慢性族残余假设，待 T0 判别法裁）**：引语类**基底区**（非 own-block）行的「保真-准确」语义引力。活测试条件：改写发生于 own-block 之外。
- **H2**：反馈缺引语行专用锚形（双行正例）。
- **H3**：重派预注入已是现状；首派有通用锚（#23 注入）——残余=首派缺引语形正例/verbatim 数据锚。

## 1. 任务分解（r4）

- **T0 blob 验尸+表面盘点+判别法（半天，无实弹）**：束7 三派（dispatches 00264-266；**首派=00255**[2026-11-08T01:45:52]——seq 1214 系 trace 事件非 dispatch 文件，r4 勘误）逐字证据链（own-block 豁免失效逐派影响/**三派 response 逐字改写核**[三派 blob 全在场——a2=`8600f0fa…` r4.1（轮 3）「缺失」声明系哈希转录错，r4.2 勘误]/首派 00255 双空格块创建形/**a2/a3 follower 块重发形**[均与 live 逐字同稿——C1 实证基础]）+ **判别法**：probe29-31/束4 #12 的被丢行定位核验（空格 own-block 标题下=H4 误归因→①③缩窄为预防面；基底区=真 H1→①③ 为根治面）+ 标题语法四表面盘点（含 `_replace_section` 失配→EOF 追加链触发条件推演；第五邻接面 `_SECTION_UNIT_RE` 附记兼容不改）+ probe 族同源判定（旧 POC blob 磁盘可用性未核——不可用按 SKILL :98 内注+会话记忆并记 deviation）。
- **T1 修复面（branch+PR，同批强制①③④⑤，r4）**：
  ①SKILL.md：铁律 0 增 **own-block 排除条款**（:98「已有」=除本章（bundle 重派含孪生章 N+1）外的块——与④后语义对齐；:100「对应新 chapter 块」消歧）＋引语行双行正例（「原句保持原样；正文如有更全原句→新起一行『XX 补全（第N章原句）』」，**自行构造过离线三验**——三验=改后 G4 判定通过/与 live diff 仅新增行/append-only 语义保持）＋:248 legacy 行口径修（create_or_overwrite→append_dedup 口径）＋教学统一**无空格规范形**（SKILL.md 全文现系无空格形；真正的空格教学面=**chapter_loop.py:955 重试指引示例**——①显式纳入改无空格形，存在性 lint 范围同步覆盖 SKILL 面+该示例面）——**与④写径归一配对前置**（见④）＋一行存在性 lint（仿 lint_decisions_sources 模式，入 just check 面——防①教学漂移回退）；
  ②（现状声明）重派预注入已是现状；残余首派引语形锚并入①；
  ③G4.ss `_format_drops` 报文补引语行双行正例（引语判别可复用 quote_verbatim.py:25 NESTED_QUOTE_RE）；
  ④**单源化标题语法（r4 完整形）**：共享 helper 唯一定义容错正则+**锚点与边界扫描统一**（保留 `\s*$` 尾锚——防带后缀标题新入豁免域；边界扫描 `startswith("## ")` 一并入 helper 消 `##第47章` 形失配——锚点取舍在 plan 记理由）；**helper 落点约束**：pipeline 侧（truth_io/truth_format 域——state_settling.py:17 已模块级 import truth_io，不新增 import 边/方向）；消费方=gate `_strip_increment_section`+提取器 read_extractors+写径 `_replace_section` 预匹配（**预匹配仅对 `第N章状态增量` 语法族生效**——`_replace_section` 系全体 headed 分节通用原语，泛化=放宽全部分节替换语义；**r4 入批强制**：①教无空格规范形而 live ch47/48 系空格形——无写径归一则未来重派发无空格标题→精确匹配失配→EOF 追加重复块且 G4 不可见[两 span 均被容错豁免剥离]——①与写径归一互为前置）；**豁免扩展（C1 裁定）**：bundle 重派时豁免 N 与 N+1 两块——**信号源=同文件现成 `bundle_chapters`**（state_settling.py:245 已函数级 import；volume_map 派生不跨卷；sidecar 新字段方案会触发契约升级纪律三源同步，弃）——与⑤双章口径互为前置（另一案=⑤限 leader-only 会教模型漏发 follower 块、违 SKILL:92 双章规则，弃）；**豁免声明**：恢复 probe31 已裁定语义+消同语法多字面量漂移+bundle 孪生豁免缺口闭合，非改门检判定语义；**配对义务（强制+机械化·对称矩阵）**：④与①③⑤同批；容错正则在场⇒引语双行正例+铁律 0 排除条款在场；**孪生豁免在场⇔⑤注入双章口径条款在场**（对称断言——两互为前置对均 CI 可判定）；
  ⑤#23 注入双矛盾修正（dispatch_helper.py:1460-1470）：单章口径→双章批口径（**与④豁免扩展互为前置**）；「NEVER modify or extend any earlier `## 第N章状态增量` section」→明确 own-block（含 bundle 孪生）keyed-upsert 可替换性；补防回退断言（test_append_dedup_increment_injection.py:89 现仅查标题串）；
  **红线保持**：不改 content_dropped 判定语义与 append-only 铁律。
- **T2 离线回放验收（r4）**：**(a) 纯子函数直测红绿**——`_strip_increment_section`（含 bundle 孪生豁免）/`_dropped_content_lines`/`_replace_section` 归一化直测：改前红/改后绿；`_format_drops` 引语正例在场断言；④①配对机械化断言。**(b) blob 物化整链**——束7 blob **复制入 `tests/fixtures/spec99/`**（novel 目录 git 不跟踪直引破 CI；循 spec95/00189-reads 复制先例+哈希锁）后经 `_increment_units`+upsert 物化 staged/live/sidecar 兄弟过 `_check_matrix_structure(pf)`：改前 FAIL→改后 PASS（归因已定：绿由④单独产生）。**(c) 实弹疗效**归 T3。
- **T3 实弹验收（搭卷二续跑窗，双观测线）**：线 1（④ 主疗效）：settle 步 **0 接骨 0 手术**（含 bundle 重派 follower 块面）；线 2（①③ 预防面）：首派引语保真（仅 own-block 外改写可观测）；两线分记不得互读；**T3 条目 supersede 束7 裁决 #19 的归因记录**（vol1-ledger #19 现存「违 append-only 铁律」表述已被 r3 重定性取代——T3 台账条目声明取代关系）。

## 2. 验收（r4）

1. T0 验尸+判别法+表面盘点报告落 `docs/research/`（含 probe29-31/束4 #12 被丢行定位裁定）；
2. T1 PR 合并（CI 全绿+**无 gate 消费方断言翻转**[r4 依据改写——fixture 存空格形（spec95/00189-reads :92/:108）但其消费方仅提取器/重放面，逐消费方核断言不翻转]+①③④⑤同批+④①配对机械化断言+⑤防回退断言+①存在性 lint）；
3. T2(a)(b) 红绿记录（fixtures/spec99/ 复制件为源）；
4. T3 双观测线疗效落 vol1-ledger（束级条目+supersede #19 声明）。

## 3. 风险与回退（r4）

- 修复面均为 prompt/教学/正则/写径匹配面——回退=还原文本与正则，无运行态迁移；
- T0 判别法若裁 H1 假阳性（probe/束4 被丢行均在 own-block 下）→①③定位=首派预防面（保留）；若真 H1 在场→①③为根治面（证据更强）——两果均不缩批（①③④⑤同批不变）；
- ④豁免扩展（bundle 孪生）新增静默域=孪生块内引语改写不判——由①③教学+首派预防覆盖，与 leader 块同口径；
- 锚点统一若 plan 期裁定弃 `\s*$`（采纳提取器无锚形）→须记 deviation+补后缀标题不翻转断言；
- T1 触及的 src 文件均在 `tests/tiers/deps.json` `_tool_hashes` sha256 锁内——PR 须同步刷新哈希（R3 工序）；T3 依赖卷二续跑窗复机（现停机面 ch49-0 待令）——外部调度依赖，续跑令即 T3 启动条件。
