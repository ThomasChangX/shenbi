# Spec #85 真相文件格式单源（truth-format-single-source）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把散布 10 文件的 8 种真相文件格式私有正则方言（钩 ID/线索 ID/卷标题/表格行/frontmatter/节边界六族）收敛为零依赖叶模块 `src/shenbi/truth_format.py` 单源，修复 M1-M6 六处活误解析，配 AST lint 防复发。

**Architecture:** 新建零依赖叶模块（gates↔pipeline 双向 import 下的唯一无环落点，两向可顶层 import）承载 10 个导出符号；消费者按 A/B/C 三层分层换源（A=检测面、B=判定域保持[组(1) 原形+hook_family_source 源串内嵌]、C=守卫增强[per-site 表六点位]）；volume 收敛落 `_shared`；AST lint 扫三扫描位进 `just check`。

**Tech Stack:** Python 3.11+ / pathlib / re / pytest（T1 单测层）/ tools 下 AST lint（ast 模块）。

## Global Constraints

- spec：`docs/superpowers/specs/2026-11-01-spec85-truth-format-single-source.md`（**r12 冻结版**——plan 与 spec 冲突时以 spec 为准并停步上报）
- 执行分支：`fix/spec85-truth-format-single-source`（已建）；**全部 task 为 infra 类**（pipeline/gates/tools）→ 协调者亲自实现，不分派 implementer
- 每 task commit 后**必须**产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 子 agent 全量重审）——无 audit-T<N>.md 不得开始 T<N+1>
- 规范式：`(?<![A-Za-z0-9-])(?:(?:MH|CP|H)-?\d{1,4}|P\d*-\d{1,4})(?![0-9A-Za-z])`
- 导出面恰 10 符号：`HOOK_ID_RE`/`THREAD_ID_RE`/`canon_hook_id`/`split_table_cells`/`is_separator_row`/`split_frontmatter`/`iter_sections`/`HOOK_HEADING_RE`/`find_hook_ids`/`hook_family_source`
- `find_hook_ids` 返回 **canon_hook_id 归一形态**；`hook_family_source` 源串**不含界断言**
- **禁**：真实 dispatch/pipeline 子命令（核心原则 8）；手改 deps.json 等生成物；gate 检查器副作用；`src/shenbi/` 内 `print()`
- 验证一律 `uv run pytest`/`just`（与 CI 同构）
- commit 用 conventional commits（`feat:`/`fix:`/`test:`/`chore:`）

---

### Task 0: Re-anchor 与基线采集

**Files:**
- Read-only: spec 全文锚点涉及的全部源文件
- Create: `.superpowers/sdd/reanchor-T0.md`（工作态，不提交）

**Interfaces:**
- Produces: 全部行号锚的当前树重锚表 + 旧正则匹配集基线（差集审查的「旧集」侧）——后续 task 的取证基准

- [ ] **Step 1: 按符号 re-anchor**——spec 行号为 r12 时点快照，逐符号重锚（`grep -n` 符号名）：truth_index.py `_HOOK_ID_RE`/`_parse_frontmatter`/`_split_frontmatter`、truth_readers.py `_HOOK_ID_RE`/`_cells`、truth_io.py `_HOOK_ID_CELL_RE`/`_HOOK_HEADING_RE`/`_HOOK_ROW_KEY_RE`(state_settling)/`_THREAD_ID_TOKEN`/`_OUTLINE_SECTION_KEY_RE`/`_HOOK_ROW_IN_TABLE_RE`/`split_table_cells`/`_is_separator_row`/`canon_hook_id`、writer.py `_HOOK_ID_RE`、chapter_planning.py 8 处 `MH\d+`、chapter_drafting.py `check_hook_fulfillment`、lint_truth_pool.py `_HOOK_ID_RE`/`_section_map`/`_thread_section_map`、read_extractors.py `_GROUNDING_ID_RE`/`_DETAIL_HEADING_RE`、ledger_archive.py `POOL_SPEC`、_shared.py 三条 `_CN_VOL_*`、volume_budget.py 三处字符集。漂移超 ±3 记 deviation（施工时以符号为准）
- [ ] **Step 2: 旧集基线采集**——对 truth-bearing fixtures 跑三个旧正则的匹配集并落盘基线：①truth_index/writer 旧式 `(?:[HM]\d+|P\d*-\d+)` ②truth_readers 旧式 ③truth_io cell 旧式 `(MH|CP)-?(\d{1,4})`；命令与输出存 reanchor-T0.md（Task 10 差集审查的旧集侧）
- [ ] **Step 3: 基线绿**——`just test` 起点全绿（记录输出摘要）

### Task 1: 叶模块 `src/shenbi/truth_format.py`（TDD）

**Files:**
- Create: `src/shenbi/truth_format.py`
- Test: `tests/unit/test_truth_format.py`
- Modify: `src/shenbi/pipeline/truth_io.py`（canon_hook_id 迁出+重导出）

**Interfaces:**
- Consumes: `canon_hook_id(raw: str) -> str`（自 truth_io.py:562 迁入，语义逐字不变——`re.fullmatch(r"([A-Za-z]+)-?0*(\d+)", raw.strip())`，无 match 则 `raw.strip().upper()` pass-through）；`split_table_cells(line: str) -> list[str] | None`（truth_io.py:1426 现行实现整体迁入）；`_is_separator_row(cells: list[str]) -> bool`（truth_io.py:1464）
- Produces（10 符号，后续全部 task 消费）:
  - `HOOK_ID_RE: re.Pattern[str]`（§1.3 规范式）
  - `THREAD_ID_RE: re.Pattern[str]`（`[A-Za-z]+\d{1,3}` + 前后界）
  - `canon_hook_id(raw: str) -> str`
  - `split_table_cells(line: str) -> list[str] | None`
  - `is_separator_row(cells: list[str]) -> bool`
  - `split_frontmatter(text: str) -> tuple[str, str]`（fm_text **含围栏原字节块**；无 fm 返 `("", text)`；带 truth_io.py:1819-1824 `----` 首行严格修复；无错误模式）
  - `iter_sections(text: str, level: int = 2) -> Iterator[tuple[str, str]]`（精确层级 `re.compile(rf"^#{{{level}}}\s+\S", re.M)`，level 是构造参数非量词；蓝本 ledger_archive.py:176-190 节尾切分）
  - `HOOK_HEADING_RE: re.Pattern[str]`（`^(#{2,6})\s+(<id>)` 两群组，group(1)=层级 group(2)=id；**块扫描位（truth_io:411/_HOOK_HEADING_BLOCK_RE、ledger_archive POOL_SPEC）以 `re.compile(HOOK_HEADING_RE.pattern, re.MULTILINE)` 派生**——不新增符号零字面量 lint 安全，禁直接丢 re.M）
  - `find_hook_ids(text: str, families: tuple[str, ...] | None = None) -> list[str]`（返回 canon 归一形态）
  - `hook_family_source(families: tuple[str, ...]) -> str`（联合源串按族过滤、长匹配优先、**不含界断言**；**返回串是单一可内嵌单元——顶层 alternation 自带 `(?:...)` 包裹**，如 `hook_family_source(("MH",)) == r"(?:MH-?\d{1,4})"`、多族 `r"(?:(?:MH|CP|H)-?\d{1,4}|P\d*-\d{1,4})"`——非捕获内嵌位直接拼接不拆散消费正则）

- [ ] **Step 1: 写红测**——`tests/unit/test_truth_format.py`，覆盖：边界负例四件套（`H2O`/`P53`/`CPR12`/`MP3` 全不匹配）＋受控误报三形（`第H2节`→`H2`、`H-1 项`→`H-1`、`MH02编年`→`MH02`）＋全族命中（`MH01`/`CP-004`/`H01`/`P0-4`）＋canon 语义（`MH-001`≡`MH01`≡`mh1`；`canon("P0-4")=="P0-4"` 恒等）＋split_frontmatter 围栏契约（fm_text 含 `---` 围栏原字节；`----` 首行→`("", text)`；中段 `---` 不切）＋iter_sections level=2 只取 H2/level=3 只取 H3（构造 H2>H3 嵌套样本断言互不混入）＋HOOK_HEADING_RE 两群组（`### P0-4 TRIGGER 证据`→group(2)=="P0-4"）＋find_hook_ids families 过滤（`families=("MH",)` 对 `CP-001` 不可见）与 canon 归一（`MH-01`→`MH1`）＋hook_family_source 联合串（单族 `== r"(?:MH-?\d{1,4})"`；多族 `MH|CP|H` 前 `P\d*-` 后且整体 `(?:...)` 包裹；**多族嵌入回归**：`re.match(rf"^\|\s*{hook_family_source(('MH','CP','H','P'))}(?=[\s（(｜|]|$)", "| MH01（名） | x |")` 命中——**注意 `re.match` 非 fullmatch**[模式只消费行首 id 段+零宽前瞻]、**单反斜杠**[代码 span 内 Markdown 转义不生效，双反斜杠=匹配字面反斜杠必假阴]）＋split_table_cells 尾管守卫（无 `|` 返 None）＋is_separator_row
- [ ] **Step 2: 跑红**——`uv run pytest tests/unit/test_truth_format.py -q` → ModuleNotFoundError/fail 预期
- [ ] **Step 3: 实现模块**——纯函数零依赖（仅 re/typing/collections）；模块 docstring 注明「§2.1 落点域分离：volume 族归 pipeline._shared，本模块管真相文件格式族」＋「iter_sections 为前瞻导出：#95 T3 settle 分窗是其首个消费者（spec §2.1 r2.1 注记）——T10 跑 just check 时若死代码 lint 触发则于 allowlist 登记 #95 前瞻锚」
- [ ] **Step 4: canon_hook_id 迁移**——truth_io.py 改 `from shenbi.truth_format import canon_hook_id`（import 即绑名，外部调用方零改动）；truth_io 原实现删除
- [ ] **Step 5: 跑绿**——`uv run pytest tests/unit/test_truth_format.py -q` 全绿 + `uv run pytest tests/unit/pipeline/ -q` 无回归（truth_io 重导出兼容）
- [ ] **Step 6: Commit**——`feat: add truth_format leaf module (spec #85 T1) — 10-symbol single source + canon_hook_id migration`

### Task 2: M1/M2/M6 换源——truth_index + records/writer（tdd_red_green）

**Files:**
- Modify: `src/shenbi/pipeline/truth_index.py`（:32 `_HOOK_ID_RE`、body 扫描、plan 引用过滤）、`src/shenbi/records/writer.py`（:34 `_HOOK_ID_RE`、:103 free_ids）
- Test: `tests/unit/pipeline/test_truth_index.py`（既有文件追加）

**Interfaces:**
- Consumes: `truth_format.HOOK_ID_RE`, `truth_format.find_hook_ids`, `truth_format.canon_hook_id`
- Produces: truth_index 键=MH01 原键（M1 修复后 `findall` 返整匹配 `MH01` 非 `H01`）；writer free_ids 同

- [ ] **Step 1: 红测 M1/M2/M6**——`tests/unit/pipeline/test_truth_index.py` 追加 `test_m1_mh01_key_not_mangled`（构造含 `MH01 与 CP-004` 的 body，断言索引钩键含 `"MH01"` 且**不含** `"H01"`——键归一策略按 :243-246 现行 `group(0)` 整串进键）与 `test_m2_cp_key`（`CP-001` 键非 `"P-001"`）；`tests/unit/records/test_writer.py` 追加 **`test_m6_writer_free_ids_not_mangled`**（含 `MH01` 的 body → free_ids 含 `"MH01"` 不含 `"H01"`——M6 红测落点）
- [ ] **Step 2: 跑红 → 换源**——两文件 `_HOOK_ID_RE = HOOK_ID_RE`（import），writer 注释「Same pattern as pipeline/truth_index.py」删除（M6 副本消亡）
- [ ] **Step 3: 跑绿 + 回归**——红测转绿；`uv run pytest tests/unit/pipeline/test_truth_index.py tests/unit/records/ -q`
- [ ] **Step 4: Commit**——`fix: M1/M2/M6 truth_index+writer dialect swap to HOOK_ID_RE (spec #85 T2)`

### Task 3: M3/M4 换源——truth_readers + truth_io hook 面（tdd_red_green + characterization）

**Files:**
- Modify: `src/shenbi/pipeline/truth_readers.py`（:50、:60/:68 `_cells`/`_is_separator` 统一公共名）、`src/shenbi/pipeline/truth_io.py`（:408/:411 heading 族、:414 cell 面整串化+:975-976 组链改造、:588 `_HOOK_ROW_IN_TABLE_RE` 族源串内嵌）
- Test: `tests/unit/pipeline/test_truth_readers.py`、`tests/unit/pipeline/test_truth_io_hooks.py`（新建）

**Interfaces:**
- Consumes: `HOOK_ID_RE`/`HOOK_HEADING_RE`/`split_table_cells`/`is_separator_row`/`canon_hook_id`/`hook_family_source`
- Produces: `pending_hooks` 单一解析者对 CP 族可见（M3）；cell 面 `P0-4` 命中且 canon 恒等（M4）；truth_io 内 `split_table_cells`/`is_separator_row` 转重导出（`:1426/:1464` 私有定义删除——truth_io 内 `_is_separator_row` 调用点**共 11 处**（:977/:1154/:1241/:1395/:1400/:1498/:1525/:1531/:1551/:1572/:1797）与 :1895 既有公共别名 `is_separator_row = _is_separator_row`——**施工时保留一行私有别名**（改名分支 11 处全改易漏，别名为零行为差）、`:675` 内联拆分与 `:972` 调用统一走单源）

- [ ] **Step 1: 红测 M3/M4（钉名）**——`tests/unit/pipeline/test_truth_readers.py` 追加 **`test_m3_cp_visible_to_pending_hooks_reader`**（`CP-001` 行经 read_pending_hooks 可见）；`tests/unit/pipeline/test_truth_io_hooks.py` 新建 **`test_m4_p_family_cell_and_heading`**（fixture `tests/fixtures/truth-pending_hooks-ch56.md` 读入，断言 `P0-4` 行[:29-35 cell]与 `### P0-4 TRIGGER 证据`[:65 heading]均被识别）；**负测**：两分组旧式对 `P0-4` 只捕 `P0` 的假阳性形（构造 `(MH|CP|P)-?(\d{1,4})` 推演断言 `P0` 不作为合法捕获出现——用新整串实现断言 `m.group(0)=="P0-4"`）
- [ ] **Step 2: 换源**——truth_readers :50 换 `HOOK_ID_RE`；truth_io :408/:411 换 `HOOK_HEADING_RE`（组消费点适配 group(2)）；:414 cell 面改 `HOOK_ID_RE.search(cell)` + `canon_hook_id(m.group(0))`（整串化，:975-976 `f"{g1}{g2}"` 拼接链删除）；:588 保行锚+前视终止符、id 段换 `hook_family_source(("MH","CP","H","P"))`；`_cells`/`_is_separator` 换公共名调用
- [ ] **Step 3: characterization**——跑 fixture 驱动对比测试（ch56/ch118/probe19 三 fixture 的钩可见集 before/after，变化集=P 族新增**加已登记松动/收紧轴项**——:408/:411 标题终止符 CJK/下划线受控松动[spec 验收 7 轴②]、:414 cell 面尾字母收紧[`MH02x` 旧入键/新拒，与 read_extractors:43 同款]、**:675 无尾管数据行分类变化[base_is_shell 换带守卫版，spec §2.1 r4 注记]**）落 `.superpowers/sdd/char-T3.md`
- [ ] **Step 4: 跑绿 + 回归**——`uv run pytest tests/unit/pipeline/ -q`
- [ ] **Step 5: Commit**——`fix: M3/M4 readers+truth_io hook-face swap, cell regex integral-string rework (spec #85 T3)`

### Task 4: chapter_planning A/B 层换源 + 验收 8 双判据（characterization + 新增钉死测试）

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（:248 A 层；:263/:374/:376/:408/:412 B 层源串内嵌；:514/:906 find_hook_ids）
- Test: `tests/unit/gates/g4/test_chapter_planning.py`（**既有绿测零改动**）、`tests/unit/gates/g4/test_hook_age.py`（追加钉死测试）

**Interfaces:**
- Consumes: `find_hook_ids(text, families=("MH",))`（返回 canon 归一）、`hook_family_source(("MH",))`（源串 `MH-?\d{1,4}`，无界断言）
- Produces: B 层判定域不变（组(1) 原形 MH03 保留、不过 canon）；`:514/:906` 双侧 canon 对账

- [ ] **Step 1: 新增 hook_age 钉死测试（先写）**——`test_cp_relevant_rows_not_in_hook_age`：_mk harness 构造 `| CP-005（码头那顿换来的饭） | RELEVANT | 26 |` 总览行 + memo 未触达 → 断言零 `G4.cp.hook_age` must_fix（green-before 相——换源前 `:263` 不捕 CP 即绿；防退化相=幼稚 canonical 全族换源）
- [ ] **Step 2: 跑基线确认双绿**——两测试文件全绿（含既有 `test_cp_namespace_hooks_are_not_gated`）
- [ ] **Step 3: A/B 换源**——:248 换 `hook_family_source(("MH",))` 内嵌（group(1) 原形）；五 B 层点同款内嵌（组结构/行锚/尾注组不动）；:514 `set(find_hook_ids(text, families=("MH",)))`、:906 `list(dict.fromkeys(find_hook_ids(s7_text, families=("MH",))))`；`:910` 文案注记 canon 展示（`'、'.join(unknown)` 旁附原文形态或明示 canon——按 spec §2.3.1 注记实施）
- [ ] **Step 4: 跑绿（双判据）**——既有绿测**零改动**保持绿 + 新增钉死测试绿；`uv run pytest tests/unit/gates/g4/ -q`
- [ ] **Step 5: characterization**——连字符形两分支验证（`MH-01` 已注册→命中无 FAIL；未注册→must_fix=堵盲区）＋轴⑤（:514/:906 位数收窄）与轴⑥（B 层 ≥5 位收窄/截断二分）实测登记，落 char-T4.md
- [ ] **Step 6: Commit**——`fix: chapter_planning A/B-layer swap, judgment domains pinned by dual tests (spec #85 T4)`

### Task 5: C 层表六点位换源（characterization 先行）

**Files:**
- Modify: `src/shenbi/gates/g4/state_settling.py`（:383 族源串内嵌保前视终止符；:632-636 frontmatter 位归 Task 6 一并）、`tools/lint_truth_pool.py`（:43/:80/:109-111/:181 **+ :70 弱守卫 `_cells` 换 split_table_cells**）、`src/shenbi/pipeline/ledger_archive.py`（:88/:89 换源；**:274 `_row_entry_id` 缺尾管守卫改走 split_table_cells**；:107 归 T8；:261 不动仅登记）、`src/shenbi/pipeline/read_extractors.py`（:43/:46 保 `^###` 锚 families 含 P/:156-158/:267-269 整串化/**:153/:264 内联拆分改走带守卫版**）、`src/shenbi/gates/g4/chapter_drafting.py`（:309/:311 对称 find_hook_ids+canon）
- Test: 上述各模块既有测试文件追加 C 层点位断言

**Interfaces:**
- Consumes: Task 1 全部符号（含 split_table_cells 带守卫版）
- Produces: C 层六点位行为变化集（char-T5.md 逐点位——P 族新增 findings 样例/归档 diff 前后/payload 变化/BR-01+AC-001 收紧样例/misses 前后差）；**验收 4 的弱守卫同批收敛**（lint_truth_pool:70/ledger_archive:274/read_extractors:153+264 四处——spec 验收 4 落点）

- [ ] **Step 1: characterization 先行**——对六点位各写 before 断言测试（现行行为快照）：lint_truth_pool 对 P 族失明快照、ledger_archive P 族节不可归档快照、chapter_drafting 对 `MH01` 形盲区快照（fixtures 5 个 plan 均 no-op 已证——用构造输入）
- [ ] **Step 1b: 弱守卫收敛**——lint_truth_pool:70 `_cells` 删除改调 `split_table_cells`（None 早退守卫统一）；ledger_archive `_row_entry_id`（:274）与 read_extractors:153/:264 内联 `strip("|").split("|")` 改走 `split_table_cells` 带守卫版（无尾管数据行返 None 跳过=行为变化记 char）
- [ ] **Step 2: 换源**——:383 与 :588[Task 3 已做]均为**族源串内嵌（保留行锚+前视终止符，禁整串换 HOOK_ID_RE——probe32 陷阱）**；:43/:80 换 `HOOK_ID_RE`/`HOOK_HEADING_RE`（:80 适配 group(2)；ledger_archive:88 的 POOL_SPEC 以 `re.compile(HOOK_HEADING_RE.pattern, re.MULTILINE)` 派生）；:109-111 与 read_extractors:156-158/:267-269 两分组 `canon(f"{g1}{g2}")` 链整串化 `canon(m.group(0))`；read_extractors:46 保 `^###` 锚只换 id 段（families 含 P）；:309/:311 双侧 `set(find_hook_ids(...))`（无 families=全族）——`missing = plan_hooks - chapter_hooks` 语义不变
- [ ] **Step 3: after 断言 + 差集**——char-T5.md **六点位变化集＋Step 1b 弱守卫四处行为变化**（含 BR-01/AC-001 退出 fulfillment 域样例）
- [ ] **Step 4: 跑绿 + 回归**——`uv run pytest tests/unit/ -q`
- [ ] **Step 5: Commit**——`fix: C-layer per-site swap (six sites, spec #85 §2.3.1 table) with characterization sets`

### Task 6: frontmatter 12 处切分拷贝收敛 + 跳过/剥离位登记

**Files:**
- Modify: `src/shenbi/pipeline/truth_index.py`（:118-134/:136-148）、`src/shenbi/pipeline/truth_readers.py`（:94-96）、`src/shenbi/pipeline/truth_io.py`（:382/:546/:1825）、`src/shenbi/records/writer.py`（:57）、`src/shenbi/gates/shared.py`（:337 strip_narrative_body 首段——#89 T4 移交）、`src/shenbi/pipeline/review_checklist.py`（:443-446）、`src/shenbi/gates/g4/state_settling.py`（:632-636）、`src/shenbi/gates/g4/chapter_drafting.py`（:437-448）、`src/shenbi/pipeline/checkpoint.py`（:76-79）、`src/shenbi/pipeline/dispatch_helper.py`（:2292/:2403 presence 判定）
- 注释回指（不换源）：`src/shenbi/gates/g6_checks.py:133-142`、`src/shenbi/pipeline/genesis.py:151-156`、`src/shenbi/pipeline/truth_io.py:641-652`、`src/shenbi/gates/g4/state_settling.py:30-55`、`tools/regen_accept.py:367`
- Test: `tests/unit/test_truth_format.py` 追加消费者适配测试

**Interfaces:**
- Consumes: `split_frontmatter`（fm_text 含围栏）
- Produces: 12 处私有切分定义归零；内芯类消费者剥围栏两行的适配行；行为变化表（7 处宽松形 `----` 翻转 + shared:348/truth_io:546 反向轴 + state_settling:633 中段差异 + presence 四点两轴）落 char-T6.md；**:261 残差说明行**（本轮不迁移故无时序行为变化；spec 反向轴措辞系「若未来对齐严格形」的条件差异登记——plan 裁定现状保留 `startswith("---\n")`）

- [ ] **Step 1: 红测**——`test_split_frontmatter_replaces_all_copies`：对 12 处所在模块的代表性入口各一测（如 truth_index `_parse_frontmatter(text)` 与 `_split_frontmatter(text)` 返回值在新旧实现下对 `----` 首行/CRLF/`--- ` 变体的行为差异按 spec 行为变化表断言）
- [ ] **Step 2: 逐处换源**——内芯类（yaml/取值面）调 `fm_text, body = split_frontmatter(text)` 后剥围栏首尾两行；拼接类（truth_io:382/checkpoint:76）直接用 fm_text（含围栏零适配）；truth_io:546 regex 切分换调用；**presence 位四点（truth_io:280/:360、dispatch_helper:2292/:2403）改走 `split_frontmatter(text)[0] != ""` 判定**——`----` 首行从「有 fm」翻转为「无 fm」（spec r8 登记的修复方向：ensure_truth_frontmatter 将为此类文件补块）＋**前置空行轴**（`"\n---\n…"` 首行文件今日 lstrip 判有 fm→迁移后判无 fm——零生产证据同登记），两轴均入行为变化表（显式迁移非沉默跳过）
- [ ] **Step 3: 跳过/剥离位注释回指**——5 处各加一行注释 `# frontmatter boundary semantics: see shenbi.truth_format.split_frontmatter`（不强换源）
- [ ] **Step 4: characterization**——char-T6.md 行为变化表（逐站点方向）
- [ ] **Step 5: 跑绿 + 回归**——`uv run pytest tests/unit/ -q`
- [ ] **Step 6: Commit**——`refactor: consolidate 12 frontmatter split copies to split_frontmatter (spec #85 T6)`

### Task 7: volume 收敛落 _shared（tdd_red_green + characterization）

**Files:**
- Modify: `src/shenbi/pipeline/_shared.py`（增 `parse_volume_spans(text) -> list[VolumeSpan]`；VolumeSpan 自 volume_budget 迁入或 _shared 定义+volume_budget 重导出；`_CN_VOL_HEAD_RE`/`_CN_VOL_HEAD_SPAN_RE` 字符集归一含千）、`volume_budget.py`（:48-51/:112-114/:217-221 三处字符集改 import；:217-221 纯阿拉伯→含千=放宽入 characterization）、`truth_io.py`（:423 outline 键字符集改 import）
- Test: `tests/unit/pipeline/test_volume_spans.py`（新建或追加）

**Interfaces:**
- Consumes: 无新依赖
- Produces: `parse_volume_spans(text: str) -> list[VolumeSpan]`（paren-span 形建模）；`read_volume_boundaries(project_dir: Path | str) -> set[int]` 签名不变、语义=顺序回退+卷内 range-line 优先逐字保留

- [ ] **Step 1: 红测（三种卷标题形态 + disagree 钉死测试）**——无冒号 `## 第一卷 标题（第 1-23 章）`、含千卷号、阿拉伯卷号各自解析一致；**disagree 钉死测试（green-before 相**——现行 _shared:92-100 已 range-line 优先，换源前即绿；**防退化相=派生实现改成并集**[该相下取 {20,23} 转红]**）**：range-line 止 20 + heading span 止 23 并存 → `read_volume_boundaries` 取 `{20}` 不取 `{20,23}`
- [ ] **Step 2: 实现**——单一数字字符集常量（含千/百）+ 冒号可选；`read_volume_boundaries` 三路径逐字保留重构为派生式
- [ ] **Step 3: characterization**——`:217-221` 放宽（`第一千卷` 新可匹配）与 _shared 增宽入 char-T7.md
- [ ] **Step 4: 跑绿 + 回归**——`uv run pytest tests/unit/pipeline/ -q`（volume_budget/chapter_loop 调用方无回归）
- [ ] **Step 5: Commit**——`refactor: volume numeral charset single-source in _shared + parse_volume_spans (spec #85 T7)`

### Task 8: thread 侧换源（:426/:439 删/:443/:447/:451 + 组合点）

**Files:**
- Modify: `src/shenbi/pipeline/truth_io.py`（:426 `_OUTLINE_SECTION_KEY_RE` thread 分支内插 `THREAD_ID_RE.pattern`；:439 `_THREAD_ID_TOKEN` **删除**；:443/:447/:451 f-string 改 `THREAD_ID_RE.pattern` 引用）、`ledger_archive.py:107`、`read_extractors.py:394`、`tools/lint_truth_pool.py:53/:181`
- Test: `tests/unit/test_truth_format.py` 追加 + 既有 thread 测试回归

**Interfaces:**
- Consumes: `THREAD_ID_RE.pattern`（源串载体钦定）
- Produces: thread 族私有 token 定义归零；`:426` `\d+`→`\d{1,3}` 收窄入 characterization

- [ ] **Step 1: characterization 先行 + M5 红测**——`### A1234: x` 旧匹配/新不匹配断言（收窄登记）；`_thread_section_map` D 级节可见性 before 快照；**红测 M5（验收 1 落点）**：lint 的 **thread 行图 `_THREAD_ID_RE`（:53）与节图 `_thread_section_map`（:181）**对 `| D12 |` 行与 `### D12:` 节——现行不可见（`[ABC]\d` 失明）、换源后两图可见（`test_m5_d12_visible_in_both_maps`，tests/unit/tools/ 下 lint 级测试或直接调 lint 内函数；注意 D12 管辖在 thread 图非 hook 图——`_HOOK_ID_RE`(:43) 换源后对 D12 仍不可见属正确）
- [ ] **Step 2: 换源**——五文件组合点 f-string 内插（truth_io:426/:443/:447/:451、ledger_archive:107、read_extractors:394、lint_truth_pool:53/:181）；`:439` 常量删除（ledger_archive/read_extractors 惰性 import 同步改）
- [ ] **Step 3: 跑绿 + 回归**——`uv run pytest tests/unit/ -q`
- [ ] **Step 4: Commit**——`refactor: thread-id token single-source via THREAD_ID_RE.pattern (spec #85 T8)`

### Task 9: AST lint 工具 + just check 挂载（tdd_red_green）

**Files:**
- Create: `tools/lint_truth_format_single_source.py`
- Modify: `justfile`（check 面挂 lint）
- Test: `tests/unit/tools/test_lint_truth_format_single_source.py`

**Interfaces:**
- Consumes: ast 模块（AST 形态判据）
- Produces: exit 0/非 0 CLI；三扫描位（re 调用实参 + `_*RE = re.compile(...)` 赋值位 + 模块级字符串常量赋值位[值含形态判据]）；白名单=AST 形态豁免（JoinedStr 含 `hook_family_source(...)`/`THREAD_ID_RE.pattern` 引用且常量段零方言字面量）+ 具名条目 `review_checklist.py:619`（注记 #86 T2 删除承诺锚）；`truth_format.py` 整文件豁免

- [ ] **Step 1: 红测**——用 tmp_path 构造三种违规样本（裸 `MH\d+` 字面量 re.compile 位/模块级 `X = r"MH\d+"` 裸常量位/组合点常量段夹带方言）与四种合法样本（truth_format 形态/f-string 引用/`'CPZone'` 枚举/`'MH-'` 词表——值无数字形态不命中）
- [ ] **Step 2: 实现工具**——ast.walk 扫三扫描位；hook 形态（`MH|CP|P\d*-`）与 thread 形态（`[ABC]\d`/`[A-Za-z]+\d{1,3}`）判据；输出违规清单 file:lineno
- [ ] **Step 3: 全树干跑**——`uv run python tools/lint_truth_format_single_source.py` 对当前树（换源完成后）零命中；若命中=换源遗留，回对应 task 修
- [ ] **Step 4: 挂 just check**——justfile check recipe 追加（对齐 lint_decisions_sources 模式）
- [ ] **Step 5: 跑绿**——`just check` exit 0
- [ ] **Step 6: Commit**——`feat: AST lint for truth-format single source + just check wiring (spec #85 T9)`

### Task 10: 终验收批（验收 1-8 全跑 + 差集清单 + 变化集归档）

**Files:**
- Create: `.superpowers/sdd/acceptance-T10.md`（验收证据落盘，gitignored 工作态）
- Modify: 仅在验收发现缺陷时回修对应模块

**Interfaces:**
- Consumes: Task 0 基线 + Task 1-9 全部产出
- Produces: spec §4 验收 1-8 逐条执行证据

- [ ] **Step 1: 验收 1**——M1-M6 红测全绿确认（`uv run pytest tests/unit/test_truth_format.py tests/unit/pipeline/test_truth_index.py ... -q` 输出粘贴）
- [ ] **Step 2: 验收 2**——差集审查：旧集基线（T0）vs 新集（**以 HOOK_ID_RE 源串重跑 T0 同命令采集**），只审新增/消失项，限 truth-bearing 文件（ch56/ch118/probe19 fixtures）；清单+处置表落 acceptance-T10.md；边界负例四件套在 T1 测试中
- [ ] **Step 3: 验收 3**——lint 全树零命中 + `just check` 含 lint
- [ ] **Step 4: 验收 4**——`grep -rn 'def split_table_cells\|def is_separator_row\|def split_frontmatter\|def iter_sections' src/ tools/` 各唯一定义（truth_format.py）；12 处拷贝归零核验；**内联/弱守卫残留核验**：`grep -rn 'strip("|").split' src/ tools/` 逐点勾核（expect：truth_format.py 定义外零未登记命中——域外点须在 spec range-out 清单内）
- [ ] **Step 5: 验收 5**——volume 三形态红测 + disagree 相红测绿；卷号字符集 6 处归一 grep 核验
- [ ] **Step 6: 验收 6/7**——`just check` exit 0；C 层六点位变化集（char-T3/T4/T5/T6/T7/T8 汇总）与验收 7 五轴登记对照
- [ ] **Step 7: 验收 8**——双判据：`git diff --stat tests/unit/gates/g4/test_chapter_planning.py`（绿测零改动——如因 import 无关行被动改动须记录说明）+ 新增 hook_age 钉死测试在位且绿
- [ ] **Step 8: Commit**——`test: acceptance evidence batch for spec #85 (all 8 criteria)`

---

## 验收覆盖表（spec §4 → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1 M1-M6 红测+M4 整串+heading 钉 fixture | T2（M1/M2/**M6**）/T3（M3/M4）/**T8（M5）** | `uv run pytest tests/unit/ -q -k 'm1 or m2 or m3 or m4 or m5 or m6 or cp_relevant or hook'` |
| 2 差集清单+负例四件套 | T0+T10（T1 埋负例） | acceptance-T10.md 差集表（旧集 T0/新集 T10 重跑同命令） |
| 3 AST lint 三扫描位+白名单 | T9 | `just check` 含 lint 且零命中 |
| 4 四函数各唯一定义+12 处收敛+弱守卫同批 | T5（弱守卫）/T6/T10 | grep 唯一定义+内联残留核验 |
| 5 volume 唯一定义+三形态+disagree | T7 | `uv run pytest tests/unit/pipeline/test_volume_spans.py -q` |
| 6 just check exit 0+判定域不变 | T4/T9/T10 | `just check` + 双判据 |
| 7 无新 FAIL 门+五轴登记 | T5/T6/T7/T8 | char 汇总对照 |
| 8 判定域钉死双判据 | T4 | 绿测零改动+新增钉死测试绿 |

## 执行说明

- 全部 task infra 类 → 协调者亲自 TDD 实现（subagent-driven-development 的 implementer 分派对本 plan 不适用；task 后 fresh-context 重审义务不变——audit-T<N>.md）
- 串行执行 T0→T10；T2/T3 可换序但 T1 必须最先（T0 除外）；T9 必须在全部换源 task 之后（否则 lint 自身红）
- 每 task 完成当轮更新 `spec-deviations.md` 的 `### T<N>` 段
