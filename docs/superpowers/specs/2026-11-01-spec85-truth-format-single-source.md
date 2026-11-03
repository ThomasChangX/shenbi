# Spec #85 · 真相文件格式单源（truth-format-single-source）：把散布 9 文件的 5 种格式方言收敛为一

**日期**：2026-11-01（r2 修订 2026-11-02：cell 正则修正/误报清单义务/volume 收敛落点钉死；**r2.2 2026-11-02 全量对抗式审计修订**——P 标题形改判活缺陷/频次表重采/补 M6 第二副本/验收改 AST 判定/iter_sections 精确层级语义；**r3 2026-11-02 价值门驳斥修订**——§2.3 换源分层策略[chapter_planning 判定域保持]/§2.1 M4 整串 canon 迁移方案+find_hook_ids 家族过滤/§2.2 字符集 6 处精确化/勘误[#79 先例/:624 锚/cell 样本 8 行/代码体措辞/内联副本口径]/验收 6 改写+绿测钉死判据；**r4 2026-11-02 二轮驳斥修订**——§2.3.1 A/B 重划[:263/:374 hook_age FAIL 链入 B 层、A 层仅 :248]/hook_family_source 源串辅助[带组形态第二载体，导出面恰 10 符号]/find_hook_ids canon 归一契约/验收 3 豁免形态改写/验收 8 扩双判据[新增 hook_age 域钉死测试]/M4 m.group(0) 措辞；**r5 2026-11-02 三轮驳斥修订[用户授权]**——B 层五组合点组(1) **保留原始匹配串**[canon 归一在 :391-396 内插面对 MH01-09 漏检/MH1x 前缀误抑制/:382 键形失配，亲验；归一仅落 :514/:906 双侧对称]/A 层 :248 原形对齐/验收 6 五点勘误/验收 8⑵ 相注记/:910 报错串展示注记）；**r6 2026-11-03 设计审查修订[阶段 3 轮 1：0C+6I+8M 全清偿]**——C 层扩 per-site P-可见性表[:383 换源机制钉死 probe32 陷阱/lint_truth_pool:43,:80/ledger_archive:88,:90/read_extractors:43,:46/truth_io:588]/frontmatter 拷贝清单补 4 处[review_checklist:443 活链/state_settling:632/chapter_drafting:437/checkpoint:76]/split_frontmatter 契约钉死[(fm_text,body) 边界切分]/§2.2 派生式精确化[thread 族执法+THREAD_ID_RE.pattern 载体/lint 判据补 thread 形态/白名单钦定 AST 形态判据/P1 显式列 lint/锚回 :619/cell 样本 7 行/CP-RELEVANT 措辞降级/残余风险显式登记]）；**r7 2026-11-03 设计审查二轮精化[0C+4I+4M 清偿]**——split_frontmatter 围栏钦定[fm_text 含围栏原字节块/内芯类自剥]/§2.2 派生式改顺序回退+卷内 range-line 优先[并集误述实证推翻]+disagree 红测/truth_io:426 thread 内联收编/HOOK_HEADING_RE 两群组契约[group(2)=id 对齐 LedgerSpec]/多族源串契约/锚勘误[:89/:394]/「12 处 9 文件」/验收 7 限定语/.format() 入盲区口径）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r7，未执行） ｜ **优先级**：🟥 P0
**动机证据**：architecture-review-20261101 #1 卡 + 协调者亲验（本文 §1 全部命令已实跑复现；fixtures 真实产物形态普查见 §1.3）

**触及的不变量维度**：承诺与债务（钩）（hook-id 检测语法直接决定 pending_hooks 对账/归档/检索三面可见集）

---

## 0. 背景与根因

「什么算一个钩 ID / 线索 ID / 卷标题 / 表格行 / frontmatter」是真相文件格式的**不变量**，却以 ≥5 种私有正则散布 9 个文件。probe15 事故后建了 `canon_hook_id` 规范器（truth_io.py:562-571），但**检测**语法从未收敛。pending_hooks.md 被 6 模块解析、thread_map 4 模块、volume_map 4 模块。

## 1. 事实基础

### 1.1 真实产物形态普查（tests/fixtures = G0.9 真实输出，形态即生产形态）

复跑命令（r2.2 亲验；r1-r2 的 249/45 无可复现口径，按当前树实测重采）：

```bash
find tests/fixtures -name '*pending_hooks*.md' \
  | xargs grep -hoE '\b(MH|CP)-?[0-9]{1,4}\b' | cut -c1-2 | sort | uniq -c
# → 246 MH / 37 CP
grep -rnE '^#{2,6}\s+P[0-9]*-[0-9]+' tests/fixtures
# → 2 命中，分属两文件：truth-pending_hooks-ch56.md:65 / consolidation/volume-1/unresolved-hooks.md:65（同文副本）
```

| 族 | 形态 | 频次（样本） | 备注 |
|---|---|---|---|
| MH | `MH01`–`MH14`（2 位、无连字符） | 246 | 主体族（r2 记 249 无复现口径） |
| CP | `CP-004`–`CP-009`（连字符 + 3 位） | 37 | 全部带连字符（r2 记 45 同上） |
| P | `P0-4` / `P0-9` / `P0-14`（P+数字+连字符+数字） | 单元格形样本 **7 行 7 个 distinct id**（r6 终勘：truth-pending_hooks-ch56.md:29-35——P0-4/9/14/15/19/20/22；r3 记 3 低估、r3 批注 8 行又过冲）＋**标题形 2**（两文件各 :65，`### P0-4 TRIGGER 证据`，provenance: upstream-copy） | **r2.2 改判：标题形是真实生产形态**——heading 正则缺 P 族是**活缺陷**，不是「覆盖前移」 |

**结论（r2.2 勘误）**：`P\d*-\d+` 在**表格单元格与 `###` 标题**两形态均有真实样本——M4（cell 正则）与 heading 家族（chapter_planning/ledger_archive 蓝本）**都必须补 P 族**；红测须钉住 `truth-pending_hooks-ch56.md:65`（heading）与 `:29-31`（cell）两处。

### 1.2 活误解析（协调者全部实跑复现；§4 红测照抄）

| # | 位置 | 输入 → 错误输出 | 后果（已核消费链） |
|---|------|----------------|------|
| M1 | `truth_index.py:32` `(?:[HM]\d+\|P\d*-\d+)` | `"MH01"` → `H01` | **全部 MH 族被改键**（fixtures MH 246 次）。消费链实证：`context_assemble.py:30-33` import 块含 `query_index`（r6 重锚：原 :29 漂 1-4 行）；truth_index 内部 body 扫描（:243）与 plan 引用过滤（:362）**同用这一坏正则**、彼此自洽——真实失效是与 `truth_readers`（保留 `MH01`）产生**重复条目**（`MH01` 与 `H01` 并存），plan 命中无字段副本（r2.2 勘误：原「引用丢失」归因不准） |
| M2 | 同上 | `"CP-001"` → `P-001` | CP 族（37 次）同样改键 |
| M3 | `truth_readers.py:50` `(?:MH\d+\|[HM]\d+\|P\d*-\d+)` | `"CP-001"` → `P-001` | 该函数自称 pending_hooks 单一解析者（SDD #21 R2）——CP 族对其不可见 |
| M4 | `truth_io.py:414` `_HOOK_ID_CELL_RE = (MH\|CP)-?(\d{1,4})` | `"\| P0-4 (quiet) \|"` → 不匹配 | :975-976 的 `canon_hook_id(f"{g1}{g2}")` 归一/匹配链对 P 族全失——**cell 面的真实断点**；heading 家族 :408 缺 P 同为活缺陷（fixture `truth-pending_hooks-ch56.md:65` 实证），两处同批覆盖 |
| M5 | `tools/lint_truth_pool.py:53` `([ABC]\d{1,3})` | `"D12"` → 不匹配 | truth_io.py:439 已修为 `[A-Za-z]+\d{1,3}` 并留档——lint 侧仍是修复前字符集，pool lint 静默跳过 D 级线索（D 级样本只见 truth_io:433-438 的 rebudget-drill 注释，fixtures 无活证据——按假设形态处理） |
| **M6（r2.2 新增）** | `src/shenbi/records/writer.py:34` `(?:[HM]\d+\|P\d*-\d+)`（注释自认 “Same pattern as pipeline/truth_index.py”） | `"MH01"` → `H01` | **第二副本**：:103 `findall(body)` 产出的 free_ids 与 truth_index 同款改键。修 M1/M2 不修它 → §2.3「换源后私有定义归零」不成立、records 面继续产重复键 |

g4/chapter_planning.py 另有 8 处严格 `MH\d+`（:248,:263,:374,:376,:408,:412,:514,:906）——第 6 方言：不见 CP、不见连字符形态，与 truth_io 接受集不同即漏检。

### 1.3 规范 HOOK_ID_RE（单源定义，兼容上表全族）

```
(?<![A-Za-z0-9-])(?:(?:MH|CP|H)-?\d{1,4}|P\d*-\d{1,4})(?![0-9A-Za-z])
```
- 前后界断言是 M1/M2 的**根因修复**（无界时 `[HM]\d+` 可从 `MH01` 的第二字符起匹配）；
- 替代顺序：`MH|CP|H` 族在前（长匹配优先），`P\d*-` 在后；
- `canon_hook_id` 语义不变（truth_io 迁出、重导出保兼容）。
- **误报清单义务（r2 新增，r2.2 缩小规模）**：不做「全 fixtures 人工过一遍」（实测 2,500+ MH/200+ CP/数百 P token，不可执行）——改为**差集审查**：旧正则匹配集 vs 新正则匹配集，只审新增/消失项，范围限 truth-bearing 文件（pending_hooks/thread_map/plan/settling 输入），清单入 plan 验收证据；凡误匹配（如英文缩写）进 plan 处置表。
- **边界负例（r2.2 新增，必测固定集）**：`H2O`/`P53`/`CPR12`/`MP3` 不得匹配；已知误吃面：`第H2节`→`H2`、`H-1 项`→`H-1`（CJK 非 ASCII 边界）＋**r6 补：MH/CP+CJK 直连形 `MH02编年`→`MH02`**（state_settling.py:381-382 注释证明有真实数据面）——规范式须加 CJK 侧排除或登记为受控误报；`MH02编年` 形另有 §2.3.1 C 层 :383 换源机制条款防其进判定。`P14`（无连字符）无生产证据，不纳入。

## 2. 落地设计

### 2.1 叶模块 `src/shenbi/truth_format.py`（零 shenbi 依赖）

**为何新叶模块**：亲验 gates↔pipeline 已双向 import（`gates/g4/state_settling.py:16 → pipeline.truth_io`；`pipeline/chapter_loop → gates.g4.*`），现靠函数内惰性 import 缓解。g4 消费者不应新增 gates→pipeline 顶层依赖；叶模块两向皆可顶层 import。（备选：并入 `shenbi/text/`——否，text/ 是 CJK 文本运算，格式解析不同域。**r3 补落点域分离论证**：与 §2.2 的 volume 收敛落 `_shared` 并不矛盾——`_shared.py` 的 `__all__`/docstring 全是 volume-map 域语义，本模块管 hook/thread/表格/节界/frontmatter 族，两落点=**域分界**（volume 族归 _shared、真相文件格式族归 truth_format），非设计不一致。）

导出面（≤10 符号）：
- `HOOK_ID_RE`（§1.3 规范式）、`THREAD_ID_RE`（`[A-Za-z]+\d{1,3}` + 前后界；**r6 载体钦定、r7 收编 :426**：thread 组合点[truth_io.py:426（`_OUTLINE_SECTION_KEY_RE` thread_map 分支内联 `[A-Za-z]+\d+`——r7 收编，否则 §2.3「归零」对 thread 族不成立且复发 rebudget-drill 同病理）/:443/:447/:451、ledger_archive.py:107/:109、read_extractors.py:394、lint_truth_pool.py:53]的 token 源串经 **`THREAD_ID_RE.pattern` 内插**——不新增导出符号，禁自带 `[A-Za-z]+\d` 类私有 token 定义）；**`HOOK_HEADING_RE` r7 组契约钦定**：`^(#{2,6})\s+(<id>)` **两群组**（group(1)=层级、group(2)=id）——与 LedgerSpec group(2) 契约（ledger_archive.py:40-42 docstring）对齐；lint_truth_pool:80/read_extractors:46 换源点适配取 group(2)；**read_extractors:46 保 `^###` 锚只换 id 段**（层级域不放宽——现仅 H3，换 `#{2,6}` 超出修复本体）；两分组消费点（lint_truth_pool:109-111、read_extractors:156-158/:267-269 的 `canon_hook_id(f"{g1}{g2}")`）**同 M4 整串化改造**（ledger_archive:276 `m.group(0)` 直接兼容）；**`hook_family_source` r7 多族契约**：`hook_family_source(families)` 返回按族过滤的**联合源串**（长匹配优先序 `MH|CP|H` 在前、`P\d*-` 在后、连字符位 `-?` 按族保留——C 层 :383/:588 即 `(MH|CP|H|P)` 多族混用消费点）
- `canon_hook_id()`（自 truth_io 迁入；truth_io 重导出）
- `split_table_cells(row)` / `is_separator_row(line)`（合并 truth_io.py:1426/:1464 与 truth_readers.py:**60/:68** 两份同体拷贝——**r2.2 勘误：原 :71/:81 是 `_hook_id`/`_norm_state`**；r3 措辞精化：程序化比对确认**代码体 4 行一字不差**、docstring 有别（原「两字节同体拷贝」过强）；实际导出名统一：truth_io 侧 `_is_separator_row` 私有、truth_readers 侧 `_cells`/`_is_separator` 命名不一——统一导出为公共名；`_row_entry_id`（ledger_archive.py:272，缺尾管守卫）与 read_extractors 内联拆分（:153,:264）改走带守卫版；**r3 补同文件第三处：truth_io.py:675 内联拆分同批收敛**（r4 注记：:675 在 base_is_shell 内、无首尾管守卫——换走带守卫版后无尾管数据行的分类行为会变，列入 characterization 义务）。**r3 口径明示（驳斥复核缺位主张）**：g0.py:280/:288、contracts/skills/pacing_design.py:101/:112、confidence_calibration.py:69、helper_injection.py:150、records/drift.py:59 亦各有一行式 `split("|")` 内联拆分——属**非真相文件域**（G0 权重表/节奏设计表/置信校准/注入清单/漂移记录），不属真相文件格式族，**明示列范围外**（lint_truth_pool.py:70 的 `_cells` 弱守卫版例外：该文件本在 M5 换源清单内，随文件收敛））
- `split_frontmatter(text) -> tuple[str, str]`（**r6 契约钉死、r7 围栏钦定**：只管**边界切分**返回 `(fm_text, body)`——**fm_text 含 `---` 围栏原字节块**（`---\n…\n---` 完整段，字节回程保真；truth_io:382-383 `body[:close+4]` 与 checkpoint.py:76-79 `live_text[:fm_end+4]` 两处拼接类消费零适配）；**内芯类消费者**（truth_index/truth_readers/writer/review_checklist:443/state_settling:632 等 yaml/取值面）于 `fm_text` 上自行剥围栏首尾两行（适配行入 plan 行为变化表）；无 frontmatter 返回 `("", text)`；带 truth_io.py:1819-1824 的 `----` 主题性断线修复；**yaml 解析留在各消费者**（truth_readers docstring 明言「no yaml dependency for one scalar」），既不沿用 truth_io:1806-1837 的 raise TruthFileParseError、也不沿用 records/writer:57-65 的吞 YAMLError 返原文——边界函数无错误模式）；**拷贝清单（r6 补全、r7 计数勘误：12 处拷贝分布于 9 文件）**：truth_index.py:118-134、truth_readers.py:94-96、truth_io.py:280/:360/:382、records/writer.py:57、gates/shared.py:337（#89 T4 显式移交）**＋review_checklist.py:443-446（活链：dispatch_helper:1522→ReviewChecklist builder :228 读 truth/pending_hooks.md frontmatter——#86 只删死半边 :610-630 不覆盖此）＋state_settling.py:632-636（在 9 文件换源面内、character_matrix 域）＋chapter_drafting.py:437-448（truth/characters/protagonist.md）＋checkpoint.py:76-79（拼接变体，含围栏契约的零适配受益者）**——验收 4 覆盖全部副本；**frontmatter 族 range-out（r7 补，对照 split("\|") 的逐点纪律）**：chapter_loop:2674（报告面）、gates/shared:261（yload 泛面）、voice_lexicon:64（卡面）、regen_accept:289、contracts/loader:232/:324、g0_skill_contract:91——非真相文件格式族，明示域外
- `iter_sections(text, level=2)`（**精确层级**；实现形 `re.compile(rf"^#{{{level}}}\s+\S", re.M)`——`level` 是**构造正则时的插值参数**，不是正则量词；level=2 只取 H2、level=3 只取 H3——r2.2 修正语义：原 `^#{2,level}` 写法既非可执行正则、语义在 level=3 时也会把 H2 祖先一起返回，T3 还要二次过滤；蓝本=`ledger_archive.py:88` 的级域组提取＋`:176-190` 的节尾切分逻辑【r2.1 锚勘误：原「:176 参数化形态」系粗锚；r2.2 补：:88 只做 ID 过滤，节域切分在 :176-190】；**level 参数必须保留**：#95 T3 settle 分窗切 pending_hooks H3 钩详情节为同款需求——实测 113,741 字节/14 个 `### MHnn（…）` 详情节，2026-11-02 grep 亲验）
- **复合形态辅助（r2.2 新增）**：`HOOK_HEADING_RE`（`^#{2,6}\s+(<id>)` 标题形）与 `find_hook_ids(text, families=None) -> list[str]`（body 扫描；**r3 加 `families` 过滤参数、r4 定契约：返回值为 canon_hook_id 归一形态**——`MH-01`/`MH01` 同归 `MH1`，保证 `:514/:906` 两侧字符串一致不产新 unknown FAIL；`families=("MH",)` 只返 MH 族，支撑 §2.3.1 `:514/:906` 判定域保持换源）——`truth_io.py:408/411/443/447/451/588`、`g4/state_settling.py:383`、`read_extractors.py:43/46/394` 都是带锚点/组号的复合形态，单条无组 ID 正则嵌不进去；缺此两辅助则换源时组号/锚点丢失，验收 4 必红。**r4 新增**：`hook_family_source(families) -> str`（返回族正则**源串**如 `"MH\d{1,4}"`，供 §2.3.1 B 层带组/尾注组合点以 f-string 内嵌保留组结构——`find_hook_ids` 无法替换 `(id, tail)` 形态的第二条执法载体）。导出面合计 **10 符号恰达上限**。
- **M4 cell 组抽取迁移方案（r3 补，r4 措辞精化）**：`truth_io.py:414` `_HOOK_ID_CELL_RE` 是**两分组形态** `(MH|CP)-?(\d{1,4})`，`:975-976` 以 `f"{g1}{g2}"` 拼接后过 `canon_hook_id` 归一。P 族 `P0-4` 的连字符在**数字中间**——即使扩 alternation 至 `(MH|CP|P)`，`-?` 匹配不了中位连字符，只捕到 `P0`（协调者亲验：`(?!\d)` 后视在 `-` 处通过=部分匹配假阳性）。修法：cell 面改**整串匹配**——用 `HOOK_ID_RE`（无组整串）搜 cell 首格、命中后 `canon_hook_id(m.group(0))` 归一（**r4 明示=命中 id 整串而非 cell 全文**，`canon("MH01（钩子名）")` 会 pass-through 全文致永不相等；`canon_hook_id("P0-4")` pass-through 恒等、全角 `（` 在后视断言外复合首格可命中——均实测）；`:975-976` 拼接链随整串化消亡。

### 2.2 volume_map 收敛（落点已亲验：**_shared.py**）

依赖方向实证：`volume_budget.py:40` 已 `from shenbi.pipeline._shared import read_volume_boundaries`——即 volume_budget → _shared，故收敛家在 `_shared`（叶），**反向不成立**。
- `_shared` 增 `parse_volume_spans(text) -> list[VolumeSpan]`（VolumeSpan 自 volume_budget 迁入或 _shared 定义、volume_budget 重导出保其公共 API——chapter_loop:1330、dispatch_helper:**2618/:2651** 走 volume_budget 不动【#275 后 +3 行漂移，r2.2 重钉】）；
- 三条 `_CN_VOL_*` 中**含卷号字符集的两条**（`_shared.py:59 _CN_VOL_HEAD_RE` 与 `:71 _CN_VOL_HEAD_SPAN_RE`——r3 精确化：`:63 _CN_VOL_RANGE_LINE_RE` 是章节范围行正则、**不含卷号数字字符集**，不属本收敛对象）与 volume_budget.py:48-51/:112-114/:217-221、truth_io.py:423——**卷号字符集独立定义点共 6 处**（r3 勘误：原「三条 _CN_VOL_*」与「第 5 份字符集」计数不确）——收敛为**一个数字字符集**（含 千/百）+ **冒号可选**规则；`read_volume_boundaries` 的**r7 语义精确化（r6「三路径并集」误述，纯 re 实证推翻）**：现语义=**顺序回退（英文 End → 英文 range → 中文域）＋卷内 range-line 优先压过 paren-span**（_shared.py:92-100 `continue` 跳过 span 检查——range-line(止 20)+heading span(止 23) 并存时现行取 {20}、字面并集会取 {20,23} 产出现行不产出的边界）——派生实现**逐字保留该语义**，禁改并集；volume_budget:217-221 现纯阿拉伯 `第\d+卷` 归一到含千/百字符集=**放宽**，入 characterization；
- truth_io.py:423 outline 键（6 处之第 6）改 import；
- **红测**（采集自真实 seed 形态）：无冒号标题 `## 第一卷 标题（第 1-23 章）`、含「千」卷号、阿拉伯卷号三种形态各自解析一致。

### 2.3 消费者换源清单（grep 锚，换源后私有定义归零）

truth_io / truth_readers / truth_index / **records/writer（M6，r2.2 补）** / read_extractors / ledger_archive / g4-chapter_planning（8 处，按 §2.3.1 分层）/ g4-state_settling / **tools/lint_truth_pool.py（M5）**。**review_checklist（r2.2 更正）**：活半边 `_extract_hook_deliverables:424` 只读 frontmatter hooks 列表、无 ID 方言；唯一 ID 方言在死函数 `_extract_hooks_from_plan`（def 在 :610、方言正则 `hook_pattern` 在 **:619**——r6 终勘回改：r3 曾误改为 :624，协调者 grep 亲验实在 :619；生产零调用已核，仅 tests+`__all__` 引用），随 #86 T2 删除——不列入换源面。scr_extractor 若按 #86 缩编则随之去重（其 `([A-Z]{2,4}-\d+)`:237 是第 7 种形态，删除即消）。

### 2.3.1 消费者换源分层策略（r3 新增，r4 重划——两轮驳斥实证）

驳斥复核证实：`g4/chapter_planning.py` 的 8 处 `MH\d+` **不全是漏检方言**——`:514`（`registered_hooks = set(re.findall(r"MH\d+", ...))` 注册表构造）与 `:906`（refs 提取）是**对称的 MH-only 判定域**：`:911-912` 报错文案明示「新钩属 genesis/lifecycle 职权，memo 不得自造 MH 号；确需新钩请走 CP-NNN」——CP 族**有意**不在 hook_refs 对账域；绿测 `tests/unit/gates/g4/test_chapter_planning.py:208-221`（`test_cp_namespace_hooks_are_not_gated`，输入含 `| CP-001 | open |`、断言零 hook_refs must_fix）钉死此语义。**r4 重划（第二轮驳斥实证）**：`:263`（parse_relevant_hooks）是 hook_age FAIL 循环（`:381`→`:398-402` `mf.append(G4.cp.hook_age)`）的直接输入，且 CP-RELEVANT 总览行与生产形态同构（r6 措辞降级：chapter-118 fixture CP-001~009 行实测全为 RESOLVED/PARTIAL、无 RELEVANT 现症样本——「同构」成立、「有生产样本」不成立；生命周期 PLANTED→RELEVANT 为常态系推理而非实证）——机械换 canonical 产生确定性新 must_fix；`:374` 同链路（plant anchor 缺省 1 更易超龄）；`:408/:412`（defer_forms）是 **(id, tail) 带组复合正则**，tail 送 `:414-418` 清偿锚校验——`find_hook_ids`（返回 id 列表）不可无损替换。故换源分三层：

- **A 层（检测面换源，无判定后果——限键成员面）**：仅 `:248`（last-reinforced dict——CP/P 键无人查询；**r5：group(1) 保留文档原形**，与 B 层原形策略对齐消除 A/B 键形接缝：`:382 last.get(hook)` 的 hook 为 B 层 `:263` 组(1) 原形 `MH03`，两侧同形命中）。其余消费者的非判定方言正则同 A 层处理；行为=接受集变宽但不进任何判定，characterization 记录变化集。
- **B 层（判定域保持=组合点白名单+原形保留）**：`:263/:374/:376/:408/:412` 五处**保留组合正则结构**（行锚/组号/尾注组不动），id 族字面量片段改由 truth_format 导出的 `hook_family_source(families)` 源串内嵌（f-string 组合，`families=("MH",)` 保持 MH-only 判定域）；**r5 核心改写：五处组(1) 保留原始匹配串，不过 canon 归一**——三轮驳斥亲验：canon 归一形（`MH03`→`MH3`）在文档文本中从不出现，`:391-396` 的 `rf"{hook}…"` 内插检测会漏检主体生产形态 MH01-09（确定性假 FAIL）、`MH1` 对 `MH12` 前缀误抑制（静默漏报）、`:382` anchor 键形失配致 age 虚增——「归一+全串边界内插」数学不可行，**原形保留是唯一可行策略**。r4 的归一动机（`MH-01` 挂起行与 `MH01` 键串不等）系零生产证据假想形态（§1.1：246 次全 2 位无连字符；同文档混写两种拼写本身是数据 bug，不匹配反而合理）——降级为 characterization 注记（**r5.1 两分支明示**：连字符形进入 `:514/:906` 视野后——对应号已注册→可见且命中（无新 FAIL，宽容方向）；未注册→由不可见转为 must_fix（与规范形引用未注册钩同判定=probe23 立规语义，**堵盲区非误报**，验收时不得误判为回归））。`:514/:906` 两处纯 findall→set 无组依赖，换 `find_hook_ids(text, families=("MH",))`——**返回值即 canon 归一形态**（`find_hook_ids` 契约明示），两侧对称归一字符串一致（**注记**：`:910` must_fix 文案的 `'、'.join(unknown)` 将展示归一形如 `MH1` 而 memo 原文为 `MH01`——实施时于报错文案旁附原文形态或明示 canon 展示，防定位误导）。lint 白名单组合点=`:263/:374/:376/:408/:412`（验收 3 豁免形态）。
- **C 层（守卫增强=M4 修复本体的直接后果；r6 扩 per-site P-可见性表——设计审查实证「P 族入检测集」改变四个判定型消费者行为，不止 :383 一处）**：

| 点位 | 换源机制（r6 钦定） | 变化面 | characterization 义务 |
|---|---|---|---|
| `state_settling.py:383` `_HOOK_ROW_KEY_RE` | **B 层式族源串内嵌：保留 `^\|\s*` 行锚与正向前视终止符 `(?=[\s（(｜\|]|$)`，只把 id 段换 `hook_family_source` 源串**——**禁止整串换 HOOK_ID_RE**（probe32 回归陷阱，协调者亲验：`| MH02编年 |` 旧正则 False、整串换后 True 命中 MH02——正向前视终止符静默消失） | P 族行进入行键视野=守卫更强（M4 同款病灶） | 记录变化集；新告警面按实单独裁定 |
| `tools/lint_truth_pool.py:43`（`_HOOK_ID_RE`）/`:80`（标题正则） | 换 HOOK_ID_RE / HOOK_HEADING_RE | pool lint 对 P 族钩当前整体失明（总览行+详情节双侧）→ 进 findings 面 | 记录 P 族新增 findings 样例 |
| `ledger_archive.py:88/:89`（POOL_SPEC `section_heading_re`/`row_id_re`——r7 锚勘误：row_id_re 在 :89 非 :90） | 换 HOOK_HEADING_RE（两群组，id=group(2)） / HOOK_ID_RE | P 族钩详情节当前永不可归档 → `just ledger-archive` 开始动 P 族节 | **归档决策变化**——首次运行前人工过 diff |
| `read_extractors.py:43/:46`（`_GROUNDING_ID_RE`/`_DETAIL_HEADING_RE`） | 换 HOOK_ID_RE / HOOK_HEADING_RE | keep/omit 切片变化=**dispatch payload 内容变化（token 面）** | 记录 payload 变化集；验收 7「无 token 面放大」口径=变化仅限 P 族可见性修复本体 |
| `truth_io.py:588` `_HOOK_ROW_IN_TABLE_RE` | B 层式族源串内嵌（保留行锚+前视终止符，同 :383 款） | `base_has_hook_content` 守卫面扩 P 族 | 记录变化集 |

**前瞻第三消费方（r2.1 注记，2026-11-02）：#95 T3 settle 分窗组装**——总览表行（split_table_cells）/active 钩 ID（HOOK_ID_RE）/触及钩 H3 详情节（iter_sections level=3）三面切片一律 import 本模块；#95 T3 禁自带临时正则（否则即 M6 第六方言——本 spec 立项病因复发）。

## 3. 分期

- **P1**：叶模块 + M1-M6 六红测转绿 + 全消费者换源（含 §2.3.1 C 层表五点位与 frontmatter 12 文件面）+ volume 收敛 + 表格/frontmatter/节界单源 + 误报差集清单过审 + **AST lint 建成并挂 just check（r6 显式列任务）**。
- **P2**：truth_index 重索引的 CP 族效果由运行项目侧 regen-accept 窗口验证（SDD 边界外，#79 先例——r3 勘误：regen-accept 协议系 spec #79[2026-10-25-spec79-regen-acceptance.md]，原引 #80[invariant-net] 编号错误）。

**残余风险登记（r6 新增——对抗回放已测试路径中两条仍通，显式接受非沉默）**：① 通用字符集泛式逃逸（如 `[A-Z]{2,4}-\d+` 替代族字面量，scr_extractor:237 删除前开放）——lint 以精确换召回的原理性盲区；② skills 教学文案引入新 ID 族 → 泛式 thread 检测器静默错类（无 SKILL 散文 lint）。缓解义务：**新族落地须同步 truth_format 家表 + lint 判据**（写入 using-shenbi 规程由 plan 落实）；③ BinOp/`str.format()`/`%` 运行时拼接=r3 已声明盲区（当前树零方言实例——`_shared.py:277/:300` 的 `.format()` 模板现存但不载方言；r7 明写 `.format()/%` 一并入盲区口径）。

## 4. 验收

1. M1-M6 各一红测（输入/输出照 §1.2 表；M4 断言点 = cell 面**整串匹配**经 `canon_hook_id` 归一后与 `P0-4` 匹配[§2.1 r3 迁移方案]，且两分组旧式对 `P0-4` 的部分匹配假阳性（捕 `P0`）有负测钉死；heading 红测钉 `truth-pending_hooks-ch56.md:65`）；
2. 误报差集清单落 plan 证据且零未处置误匹配；边界负例四件套（`H2O`/`P53`/`CPR12`/`MP3`）固定为测试用例；
3. **AST lint（r2.2 替换原 grep 判据——原命令既漏 `re.match/finditer/findall` 8 处与裸常量 `_THREAD_ID_TOKEN`，又会误判组合行）**：`tools/lint_truth_format_single_source.py` 扫描 `src/shenbi tools/` 全部 regex 字符串字面量，含 **hook 族形态（`MH|CP|P\d*-`）或 thread 族形态（`[ABC]\d` 历史病灶形/`[A-Za-z]+\d{1,3}`）**者除 `truth_format.py` 与白名单组合点外零命中（**r6 补 thread 族判据**——否则 M5 同族复发无门禁）；进 `just check`（**r3 注记**：BinOp 拼接[常量+字面量]不在字面量判据内——当前树零方言实例，lint 覆盖面以此口径为限；tests/ 面的断言正则不属解析器方言，范围外）；**r4 豁免形态+r6 钉死实现口径**：白名单判据=**AST 形态**（JoinedStr/f-string 含 `hook_family_source(...)` 调用或 `THREAD_ID_RE.pattern` 引用**且常量段零方言字面量**）——**禁行号锚**（随编辑漂移产假阳/假阴）；B 层组合点 `:263/:374/:376/:408/:412`+C 层 `:383/:588` 走源串内嵌豁免，`:514/:906` 走 `find_hook_ids(families=...)` 调用豁免；
4. `split_table_cells`/`is_separator_row`/`split_frontmatter`/`iter_sections`（level=2/3 两档红测）各唯一定义（**含 truth_io.py:675 第三处与 lint_truth_pool.py:70 弱守卫版同批收敛**）；
5. volume span 正则唯一定义（卷号字符集 6 处归一）；三种卷标题形态红测绿；**r7 补 disagree 相红测**：range-line 与 heading span 不一致的卷（range 止 20/span 止 23）→ 断言边界取 {20}（卷内 range-line 优先语义钉死，防派生实现改成并集）；
6. `just check` exit 0（r3 改写、r5 计数勘误、r6 扩面：判定面变化限定=「M1-M6 修复本体 + 检测语法换源**不改变各消费者判定域**」——B 层**五点**判定域不变由验收 8 钉死；A/C 层接受集变宽的变化集以 characterization 记录，**C 层=§2.3.1 per-site 表五点位**（:383/:43+80/:88+90/:43+46/:588），如实证产生新告警面按表内义务单独裁定）；
7. **误报成本**：无新 FAIL **门**——纯解析修复+收敛+判定域保持；越严越准，无 shadow 义务（**r7 限定语**：C 层五点位表内注记的收紧/放宽项——read_extractors:43 尾字母形收紧（`MH02x` 旧匹配/新拒）、volume_budget:218 放宽——**不属于「无变化」承诺**，各归 characterization 义务；表内新告警面按单点裁定）。
8. **判定域保持钉死（r3 新增，r4 扩双判据，r5 加相注记）**：⑴ 绿测 `test_cp_namespace_hooks_are_not_gated`（tests/unit/gates/g4/test_chapter_planning.py:208-221，hook_refs 面）换源后**零改动保持绿**；⑵ **新增 hook_age 域钉死测试（r4——第二轮驳斥 N6 实证缺口：现 tests 无任何测试钉住 CP 排除于 hook_age 域）**：构造含 `| CP-NNN（名） | RELEVANT | 数字 |` 总览行且 memo 未触达的输入 → 断言零 `G4.cp.hook_age` must_fix（B 层 `:263` MH-only 判定域不变的执行判据；**r5 注记：green-before/green-after 相**——换源前 `:263` 不捕 CP 即绿、换源后 B 层 families 仍不捕 CP 亦绿，其防退化相=幼稚 canonical 全族换源[该相下测试转红]，不得误期红相）。两判据都过方算验收 8 过。
