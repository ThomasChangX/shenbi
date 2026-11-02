# Spec #85 · 真相文件格式单源（truth-format-single-source）：把散布 9 文件的 5 种格式方言收敛为一

**日期**：2026-11-01（r2 修订 2026-11-02：cell 正则修正/误报清单义务/volume 收敛落点钉死；**r2.2 2026-11-02 全量对抗式审计修订**——P 标题形改判活缺陷/频次表重采/补 M6 第二副本/验收改 AST 判定/iter_sections 精确层级语义）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2.2，未执行） ｜ **优先级**：🟥 P0
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
| P | `P0-4` / `P0-9` / `P0-14`（P+数字+连字符+数字） | 单元格形样本 3（truth-pending_hooks-ch56.md:29-31；全 fixtures P 族 token 数百）＋**标题形 2**（两文件各 :65，`### P0-4 TRIGGER 证据`，provenance: upstream-copy） | **r2.2 改判：标题形是真实生产形态**——heading 正则缺 P 族是**活缺陷**，不是「覆盖前移」 |

**结论（r2.2 勘误）**：`P\d*-\d+` 在**表格单元格与 `###` 标题**两形态均有真实样本——M4（cell 正则）与 heading 家族（chapter_planning/ledger_archive 蓝本）**都必须补 P 族**；红测须钉住 `truth-pending_hooks-ch56.md:65`（heading）与 `:29-31`（cell）两处。

### 1.2 活误解析（协调者全部实跑复现；§4 红测照抄）

| # | 位置 | 输入 → 错误输出 | 后果（已核消费链） |
|---|------|----------------|------|
| M1 | `truth_index.py:32` `(?:[HM]\d+\|P\d*-\d+)` | `"MH01"` → `H01` | **全部 MH 族被改键**（fixtures MH 246 次）。消费链实证：`context_assemble.py:29` import `query_index`；truth_index 内部 body 扫描（:243）与 plan 引用过滤（:362）**同用这一坏正则**、彼此自洽——真实失效是与 `truth_readers`（保留 `MH01`）产生**重复条目**（`MH01` 与 `H01` 并存），plan 命中无字段副本（r2.2 勘误：原「引用丢失」归因不准） |
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
- **边界负例（r2.2 新增，必测固定集）**：`H2O`/`P53`/`CPR12`/`MP3` 不得匹配；已知误吃面：`第H2节`→`H2`、`H-1 项`→`H-1`（CJK 非 ASCII 边界）——规范式须加 CJK 侧排除或把这两形登记为受控误报。`P14`（无连字符）无生产证据，不纳入。

## 2. 落地设计

### 2.1 叶模块 `src/shenbi/truth_format.py`（零 shenbi 依赖）

**为何新叶模块**：亲验 gates↔pipeline 已双向 import（`gates/g4/state_settling.py:16 → pipeline.truth_io`；`pipeline/chapter_loop → gates.g4.*`），现靠函数内惰性 import 缓解。g4 消费者不应新增 gates→pipeline 顶层依赖；叶模块两向皆可顶层 import。（备选：并入 `shenbi/text/`——否，text/ 是 CJK 文本运算，格式解析不同域。）

导出面（≤10 符号）：
- `HOOK_ID_RE`（§1.3 规范式）、`THREAD_ID_RE`（`[A-Za-z]+\d{1,3}` + 前后界）
- `canon_hook_id()`（自 truth_io 迁入；truth_io 重导出）
- `split_table_cells(row)` / `is_separator_row(line)`（合并 truth_io.py:1426/:1464 与 truth_readers.py:**60/:68** 两字节同体拷贝——**r2.2 勘误：原 :71/:81 是 `_hook_id`/`_norm_state`**；实际导出名统一：truth_io 侧 `_is_separator_row` 私有、truth_readers 侧 `_cells`/`_is_separator` 命名不一——统一导出为公共名；`_row_entry_id`（ledger_archive.py:272，缺尾管守卫）与 read_extractors 内联拆分（:153,:264）改走带守卫版）
- `split_frontmatter(text)`（带 truth_io.py:1819-1824 的 `----` 主题性断线修复；**r2.2 补全拷贝清单**：truth_index.py:118-134、truth_readers.py:94-96、truth_io.py:280/:360/:382、records/writer.py:57、**gates/shared.py:337 的 `strip_narrative_body` 首段（#89 T4 显式移交，r2.2 审计补）**——单源前全部枚举，验收 4 覆盖这些副本）
- `iter_sections(text, level=2)`（**精确层级**；实现形 `re.compile(rf"^#{{{level}}}\s+\S", re.M)`——`level` 是**构造正则时的插值参数**，不是正则量词；level=2 只取 H2、level=3 只取 H3——r2.2 修正语义：原 `^#{2,level}` 写法既非可执行正则、语义在 level=3 时也会把 H2 祖先一起返回，T3 还要二次过滤；蓝本=`ledger_archive.py:88` 的级域组提取＋`:176-190` 的节尾切分逻辑【r2.1 锚勘误：原「:176 参数化形态」系粗锚；r2.2 补：:88 只做 ID 过滤，节域切分在 :176-190】；**level 参数必须保留**：#95 T3 settle 分窗切 pending_hooks H3 钩详情节为同款需求——实测 113,741 字节/14 个 `### MHnn（…）` 详情节，2026-11-02 grep 亲验）
- **复合形态辅助（r2.2 新增）**：`HOOK_HEADING_RE`（`^#{2,6}\s+(<id>)` 标题形）与 `find_hook_ids(text) -> list[str]`（body 扫描）——`truth_io.py:408/411/443/447/451/588`、`g4/state_settling.py:383`、`read_extractors.py:43/46/394` 都是带锚点/组号的复合形态，单条无组 ID 正则嵌不进去；缺此两辅助则换源时组号/锚点丢失，验收 4 必红。

### 2.2 volume_map 收敛（落点已亲验：**_shared.py**）

依赖方向实证：`volume_budget.py:40` 已 `from shenbi.pipeline._shared import read_volume_boundaries`——即 volume_budget → _shared，故收敛家在 `_shared`（叶），**反向不成立**。
- `_shared` 增 `parse_volume_spans(text) -> list[VolumeSpan]`（VolumeSpan 自 volume_budget 迁入或 _shared 定义、volume_budget 重导出保其公共 API——chapter_loop:1330、dispatch_helper:**2618/:2651** 走 volume_budget 不动【#275 后 +3 行漂移，r2.2 重钉】）；
- 三条 `_CN_VOL_*`（**`_shared.py`:59/:63/:71**——r2.2 补文件名：原锚点误挂 volume_budget）与 volume_budget.py:48-51/:112-114/:217-221 收敛为**一个数字字符集**（含 千/百）+ **冒号可选**规则；`read_volume_boundaries` 由 `parse_volume_spans` 派生；
- truth_io.py:423 outline 键（第 5 份字符集）改 import；
- **红测**（采集自真实 seed 形态）：无冒号标题 `## 第一卷 标题（第 1-23 章）`、含「千」卷号、阿拉伯卷号三种形态各自解析一致。

### 2.3 消费者换源清单（grep 锚，换源后私有定义归零）

truth_io / truth_readers / truth_index / **records/writer（M6，r2.2 补）** / read_extractors / ledger_archive / g4-chapter_planning（8 处）/ g4-state_settling / **tools/lint_truth_pool.py（M5）**。**review_checklist（r2.2 更正）**：活半边 `_extract_hook_deliverables:424` 只读 frontmatter hooks 列表、无 ID 方言；唯一 ID 方言在死函数 `_extract_hooks_from_plan:619`，随 #86 T2 删除——不列入换源面。scr_extractor 若按 #86 缩编则随之去重（其 `([A-Z]{2,4}-\d+)`:237 是第 7 种形态，删除即消）。

**前瞻第三消费方（r2.1 注记，2026-11-02）：#95 T3 settle 分窗组装**——总览表行（split_table_cells）/active 钩 ID（HOOK_ID_RE）/触及钩 H3 详情节（iter_sections level=3）三面切片一律 import 本模块；#95 T3 禁自带临时正则（否则即 M6 第六方言——本 spec 立项病因复发）。

## 3. 分期

- **P1**：叶模块 + M1-M6 六红测转绿 + 全消费者换源 + volume 收敛 + 表格/frontmatter/节界单源 + 误报差集清单过审。
- **P2**：truth_index 重索引的 CP 族效果由运行项目侧 regen-accept 窗口验证（SDD 边界外，#80 先例）。

## 4. 验收

1. M1-M6 各一红测（输入/输出照 §1.2 表；M4 断言点 = cell 正则经 `canon_hook_id` 归一后与 `P0-4` 匹配；heading 红测钉 `truth-pending_hooks-ch56.md:65`）；
2. 误报差集清单落 plan 证据且零未处置误匹配；边界负例四件套（`H2O`/`P53`/`CPR12`/`MP3`）固定为测试用例；
3. **AST lint（r2.2 替换原 grep 判据——原命令既漏 `re.match/finditer/findall` 8 处与裸常量 `_THREAD_ID_TOKEN`，又会误判组合行）**：`tools/lint_truth_format_single_source.py` 扫描 `src/shenbi tools/` 全部 regex 字符串字面量，含 `MH|CP|P\d*-` 形态者除 `truth_format.py` 与该文件白名单组合点外零命中；进 `just check`；
4. `split_table_cells`/`is_separator_row`/`split_frontmatter`/`iter_sections`（level=2/3 两档红测）各唯一定义；
5. volume span 正则唯一定义；三种卷标题形态红测绿；
6. `just check` exit 0（G4/G2 判定面变化仅限 M1-M6 修复本体，characterization 记录变化集）。
7. **误报成本**：无新 FAIL 门——纯解析修复+收敛；越严越准，无 shadow 义务。
