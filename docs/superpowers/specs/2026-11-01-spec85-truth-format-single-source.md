# Spec #85 · 真相文件格式单源（truth-format-single-source）：把散布 9 文件的 5 种格式方言收敛为一

**日期**：2026-11-01（r2 修订 2026-11-02：cell 正则修正/误报清单义务/volume 收敛落点钉死）｜ **系列**：架构复审批次 A ｜ **状态**：Design（r2，未执行） ｜ **优先级**：🟥 P0
**动机证据**：architecture-review-20261101 #1 卡 + 协调者亲验（本文 §1 全部命令已实跑复现；fixtures 真实产物形态普查见 §1.3）

**触及的不变量维度**：承诺与债务（钩）（hook-id 检测语法直接决定 pending_hooks 对账/归档/检索三面可见集）

---

## 0. 背景与根因

「什么算一个钩 ID / 线索 ID / 卷标题 / 表格行 / frontmatter」是真相文件格式的**不变量**，却以 ≥5 种私有正则散布 9 个文件。probe15 事故后建了 `canon_hook_id` 规范器（truth_io.py:562-571），但**检测**语法从未收敛。pending_hooks.md 被 6 模块解析、thread_map 4 模块、volume_map 4 模块。

## 1. 事实基础

### 1.1 真实产物形态普查（tests/fixtures = G0.9 真实输出，形态即生产形态）

实跑 `find tests/fixtures -name "pending_hooks*.md" | xargs grep -hoE '(MH|CP|H|P)[-_]?[0-9]{1,4}(-[0-9]+)?' | sort | uniq -c`：

| 族 | 形态 | 频次（样本） | 备注 |
|---|---|---|---|
| MH | `MH01`–`MH14`（2 位、无连字符） | 249 | 主体族 |
| CP | `CP-004`–`CP-009`（连字符 + 3 位） | 45 | 全部带连字符 |
| P | `P0-4` / `P0-9` / `P0-14`（P+数字+连字符+数字） | 3（truth-pending_hooks-ch56.md:29-31） | 表格单元格内，`### P0-x` 标题形态在 fixtures 中**不存在** |

**结论**：`P\d*-\d+` 是真实生产形态且仅在**表格单元格**出现——M4 的缺口在 cell 正则（truth_io.py:414），不在 heading 正则（heading 家族缺 P 族属**覆盖前移**，非活缺陷）。

### 1.2 活误解析（协调者全部实跑复现；§4 红测照抄）

| # | 位置 | 输入 → 错误输出 | 后果（已核消费链） |
|---|------|----------------|------|
| M1 | `truth_index.py:32` `(?:[HM]\d+\|P\d*-\d+)` | `"MH01"` → `H01` | **全部 MH 族被改键**（fixtures MH 249 次）。消费链实证：`context_assemble.py:29` import `query_index` → `truth_index.py:243` body 扫描 `finditer`、`:362` plan 引用按 `index.hooks` 成员过滤——键形态不一致即**引用丢失** |
| M2 | 同上 | `"CP-001"` → `P-001` | CP 族（45 次）同样改键 |
| M3 | `truth_readers.py:50` `(?:MH\d+\|[HM]\d+\|P\d*-\d+)` | `"CP-001"` → `P-001` | 该函数自称 pending_hooks 单一解析者（SDD #21 R2）——CP 族对其不可见 |
| M4 | `truth_io.py:414` `_HOOK_ID_CELL_RE = (MH\|CP)-?(\d{1,4})` | `"\| P0-4 (quiet) \|"` → 不匹配 | :975-976 的 `canon_hook_id(f"{g1}{g2}")` 归一/匹配链对 P 族全失——**这是 P 族的真实断点**（heading 家族 :408 缺 P 同批覆盖，但无已知活输入） |
| M5 | `tools/lint_truth_pool.py:53` `([ABC]\d{1,3})` | `"D12"` → 不匹配 | truth_io.py:439 已修为 `[A-Za-z]+\d{1,3}` 并留档——lint 侧仍是修复前字符集，pool lint 静默跳过 D 级线索 |

g4/chapter_planning.py 另有 8 处严格 `MH\d+`（:248,:263,:374,:376,:408,:412,:514,:906）——第 6 方言：不见 CP、不见连字符形态，与 truth_io 接受集不同即漏检。

### 1.3 规范 HOOK_ID_RE（单源定义，兼容上表全族）

```
(?<![A-Za-z0-9-])(?:(?:MH|CP|H)-?\d{1,4}|P\d*-\d{1,4})(?![0-9A-Za-z])
```
- 前后界断言是 M1/M2 的**根因修复**（无界时 `[HM]\d+` 可从 `MH01` 的第二字符起匹配）；
- 替代顺序：`MH|CP|H` 族在前（长匹配优先），`P\d*-` 在后；
- `canon_hook_id` 语义不变（truth_io 迁出、重导出保兼容）。
- **误报清单义务（r2 新增，防新语法错吃散文）**：换源前跑「全 fixtures 匹配清单」——`grep -oP` 上面的正则在 tests/fixtures 全部 .md 上，人工过一遍清单（预期：仅 hook id 形态），清单入 plan 验收证据；凡误匹配（如英文缩写）进 plan 处置表。

## 2. 落地设计

### 2.1 叶模块 `src/shenbi/truth_format.py`（零 shenbi 依赖）

**为何新叶模块**：亲验 gates↔pipeline 已双向 import（`gates/g4/state_settling.py:16 → pipeline.truth_io`；`pipeline/chapter_loop → gates.g4.*`），现靠函数内惰性 import 缓解。g4 消费者不应新增 gates→pipeline 顶层依赖；叶模块两向皆可顶层 import。（备选：并入 `shenbi/text/`——否，text/ 是 CJK 文本运算，格式解析不同域。）

导出面（≤10 符号）：
- `HOOK_ID_RE`（§1.3 规范式）、`THREAD_ID_RE`（`[A-Za-z]+\d{1,3}` + 前后界）
- `canon_hook_id()`（自 truth_io 迁入；truth_io 重导出）
- `split_table_cells(row)` / `is_separator_row(line)`（合并 truth_io.py:1426/:1464 与 truth_readers.py:71/:81 两字节同体拷贝；`_row_entry_id`（ledger_archive.py:272，缺尾管守卫）与 read_extractors 内联拆分（:153,:264）改走带守卫版）
- `split_frontmatter(text)`（带 truth_io.py:1819-1824 的 `----` 主题性断线修复——truth_index.py:118-134 的拷贝缺此修复）
- `iter_h2_sections(text)`（`^##\s+\S` 边界遍历单源；蓝本 ledger_archive.py:176 参数化形态）

### 2.2 volume_map 收敛（落点已亲验：**_shared.py**）

依赖方向实证：`volume_budget.py:40` 已 `from shenbi.pipeline._shared import read_volume_boundaries`——即 volume_budget → _shared，故收敛家在 `_shared`（叶），**反向不成立**。
- `_shared` 增 `parse_volume_spans(text) -> list[VolumeSpan]`（VolumeSpan 自 volume_budget 迁入或 _shared 定义、volume_budget 重导出保其公共 API——chapter_loop:1330、dispatch_helper:2615/:2648 走 volume_budget 不动）；
- 三条 `_CN_VOL_*`（:59,:63,:71）与 volume_budget.py:48-51/:112-114/:217-221 收敛为**一个数字字符集**（含 千/百）+ **冒号可选**规则；`read_volume_boundaries` 由 `parse_volume_spans` 派生；
- truth_io.py:423 outline 键（第 5 份字符集）改 import；
- **红测**（采集自真实 seed 形态）：无冒号标题 `## 第一卷 标题（第 1-23 章）`、含「千」卷号、阿拉伯卷号三种形态各自解析一致。

### 2.3 消费者换源清单（grep 锚，换源后私有定义归零）

truth_io / truth_readers / truth_index / read_extractors / ledger_archive / review_checklist（活半边）/ g4-chapter_planning（8 处）/ g4-state_settling / tools/lint_truth_pool（M5）。scr_extractor 若按 #86 缩编则随之去重。

## 3. 分期

- **P1**：叶模块 + M1-M5 五红测转绿 + 全消费者换源 + volume 收敛 + 表格/frontmatter/节界单源 + 误报清单过审。
- **P2**：truth_index 重索引的 CP 族效果由运行项目侧 regen-accept 窗口验证（SDD 边界外，#80 先例）。

## 4. 验收

1. M1-M5 各一红测（输入/输出照 §1.2 表；M4 断言点 = cell 正则经 `canon_hook_id` 归一后与 `P0-4` 匹配）；
2. 误报清单落 plan 证据且零未处置误匹配；
3. `grep -rn "re.compile" src/shenbi tools/ | grep -E "MH|HOOK_ID|THREAD_ID" | grep -v truth_format | grep -v test` 零输出（方言定义唯一点；truth_io 重导出除外）；
4. `split_table_cells`/`is_separator_row`/`split_frontmatter`/`iter_h2_sections` 各唯一定义；
5. volume span 正则唯一定义；三种卷标题形态红测绿；
6. `just check` exit 0（G4/G2 判定面变化仅限 M1-M5 修复本体，characterization 记录变化集）。
7. **误报成本**：无新 FAIL 门——纯解析修复+收敛；越严越准，无 shadow 义务。
