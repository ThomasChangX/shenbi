# Spec #99 settle 基底行保真（settle-base-row-fidelity）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根治 settle 增量契约 own-block 豁免的空格形静默失效（H4 假阳性死锁）并单源化 `## 第N章状态增量` 标题语法（gate/提取器/写径/教学四表面），同批落地引语行保真教学（①③）与 #23 注入双矛盾修正（⑤）。

**Architecture:** 共享 helper 落 `pipeline/truth_io.py`（容忍空格的标题语法单源，双锚点模式：gate 用 `\s*$` 尾锚严格形、提取器用无尾锚前缀形——语法字面量唯一定义）；gate `_strip_increment_section` 改 bundle-aware 委托（`bundle_chapters` 信号源，孪生块 N+1 同豁免）；写径 `_replace_section` 增量族预匹配归一；SKILL/#23 注入/G4 报文三教学面同批。红侧先以束7 blob 物化 harness 固化（characterization red），④实现后转绿。

**Tech Stack:** Python 3.11+/pytest（T1 单测层）/无新依赖。

**Spec:** `docs/superpowers/specs/2026-11-08-spec99-settle-base-row-fidelity.md`（**r4.2**，audit_loop 五轮收敛版）

## Global Constraints

- **禁改 content_dropped 判定语义与 append-only 铁律**（spec T1 红线）——④系「恢复 probe31 已裁定语义的正则 bug 修复+单源化」，spec 豁免声明在案
- **①③④⑤ 同批配对**（spec T1 强制）：④不单发；配对机械化断言+对称断言必须落地（Task 4）
- **无 gate 消费方断言翻转**（spec 验收 2 r4 依据）：Task 3 结束时 G4 全量测试零翻转
- **写径预匹配仅对 `第N章状态增量` 语法族生效**（`_replace_section` 系全体 headed 分节通用原语，禁泛化）
- **教学统一无空格规范形** `## 第N章状态增量`（含 chapter_loop.py:955 示例）
- **deps.json 哈希工序**：T1 触及 src 文件全部在 `tests/tiers/deps.json` `_tool_hashes` 锁内——commit 前最后一步 `bash tests/lock-tool-hashes.sh`（ruff-format 在后会再改文件——先 format 后锁）
- **G0.9**：fixture 只能是真实产物复制（tests/fixtures/spec99/ = dispatch JSON+blob 复制件+SHA256SUMS 清单，G0.11 哈希一致）
- **T3（实弹疗效）批外**：依赖卷二续跑窗复机（现停机面 ch49-0 待令）——本 plan 边界止于 T2 完结+PR 合并；T3 双观测线归束8 窗台账
- Conventional commits；框架代码无 print（structlog）；gate 检查器纯函数幂等

## 实际签名（源码复制，plan 唯一权威——执行首步 re-anchor）

```python
# src/shenbi/pipeline/truth_io.py:1570
def _replace_section(existing: str, section: str) -> str | None:
    """Replace the same-heading section in *existing* with *section*. …
    Returns None when no matching heading exists (caller falls back to append)."""

# src/shenbi/pipeline/chapter_loop.py:1502
def bundle_chapters(project_dir: Path, chapter: int) -> list[int]:
    """[chapter, chapter + 1] unless chapter+1 crosses the current volume's
    boundary (or no volume_map span covers it) — then a singleton [chapter]."""

# src/shenbi/gates/g4/state_settling.py:316
def _strip_increment_section(live_text: str, chapter: int) -> str: …

# src/shenbi/gates/g4/state_settling.py:295
def _current_settle_chapter(pf: Path) -> int | None: …

# src/shenbi/gates/g4/state_settling.py:336
def _check_matrix_structure(pf: Path) -> tuple[list[str], list[str]]: …

# src/shenbi/gates/g4/state_settling.py:182
def _format_drops(missing: list[str], samples: int, *, cap: int = 20) -> list[str]: …

# src/shenbi/pipeline/read_extractors.py:916-918（现行提取器容错形——无尾锚）
chapter_block_res = [
    _re.compile(rf"^##\s*第\s*{n}\s*章\s*状态增量") for n in (chapter, chapter + 1)
]
```

---

### Task 0: Re-anchor 与基线（leaf · characterization）

**Files:** 无代码改动（只读核+progress 记账）

**Interfaces:** Produces: 行号再锚定表（写入 progress.md）；基线绿证据。

- [ ] **Step 1:** 按符号 re-anchor 上节签名（`grep -n "def _strip_increment_section\|def _replace_section\|def bundle_chapters\|def _format_drops\|def _current_settle_chapter\|def _check_matrix_structure" src/shenbi/ -r`）——漂移记 progress.md，±3 外更新本 plan 签名节
- [ ] **Step 2:** 基线：`uv run pytest tests/unit/gates/g4/test_state_settling*.py tests/unit/pipeline/test_append_dedup_increment_injection.py -q --no-cov` → 全绿基线计数粘贴 progress.md
- [ ] **Step 3:** `ls .superpowers/sdd/audit-T0.md` 不存在（本 task 完成后创建——见执行纪律）

### Task 1: T0 blob 验尸+判别法+表面盘点（leaf · research；=spec T0）

**Files:**
- Create: `docs/research/2026-11-08-spec99-t0-autopsy.md`
- Read-only 源：`novel-xinghuo-vol1/observability/dispatches/00255/00264/00265/00266-shenbi-state-settling-ch047-a1.json` + 各引 blob

**Interfaces:** Produces: 判别法裁定（H1 真阳性 vs H4 误归因——决定①③ T3 定位措辞）；四表面盘点核实表；写入 docs/research 的报告（spec 验收 1）。

- [ ] **Step 1:** 报告骨架五节：§1 三派证据链（a1/a2/a3 response 逐字改写核——三 blob 全在场[00265=`8600f0fa…` 20665B sha256 自校验]+own-block 豁免失效逐派影响+a2/a3 follower 块重发形[与 live 逐字同稿]）/§2 首派 00255 双空格块创建形/§3 **判别法**：probe29-31+束4 #12 被丢行定位（空格 own-block 标题下=H4 误归因；基底区=真 H1——逐窗列被丢行原文+所在块标题形）/§4 四表面盘点核实（gate:322 严格/提取器:916-918 容错/写径:1585 精确+EOF 追加链:1642-1662/教学:955 空格；第五邻接面 read_extractors.py:52 `_SECTION_UNIT_RE` 附记兼容不改）/§5 族同源判定+deviation（旧 POC blob 可用性；束4 #12 blob 若不在盘按 SKILL :98 内注+ledger 判）
- [ ] **Step 2:** 逐节填充（所有引文贴原文+偏移；判别法结论必须含每窗被丢行的块归属证据）
- [ ] **Step 3:** 提交 `docs: spec #99 T0 验尸报告——三派证据链+判别法裁定+四表面盘点`；验收 1 证据粘贴 progress.md

### Task 2: 红侧固化——fixtures/spec99 复制+blob 物化 harness+红断言（infra · characterization-red；协调者亲自）

**Files:**
- Create: `tests/fixtures/spec99/`（复制件：4 dispatch JSON+其 user_prompt/response blob，命名 `<hash>.txt`+`SHA256SUMS`）
- Create: `tests/unit/gates/g4/test_spec99_h4_redgreen.py`
- Test: 同文件

**Interfaces:**
- Consumes: `_current_settle_chapter`/`_strip_increment_section`/`_check_matrix_structure`（现行）；`_increment_units`（dispatch_helper.py:2219——物化用）
- Produces: `materialize_shu7(tmp_path, fixtures_dir) -> Path`（物化 staging/truth/character_matrix.md+live 兄弟+state-settling-decisions.json sidecar[chapter=47]——供 Task 3 转绿与回归复用）；断言测试名固定（Task 3 转绿复用）：`test_spaced_own_block_exempt`/`test_materialized_chain_no_drop`/`test_write_path_increment_heading_normalized`/`test_bundle_twin_block_exempt`（名表期望行为——红/绿由时点定）

- [ ] **Step 1:** 复制工件：00255/00264/00265/00266 dispatch JSON + 各自 user_prompt_blob+response_blob（prompt：00264=`29053cec…`、00265=`aa91eee…`、00266=`ee3d214…`；response：00255=`c7e9d718…`、00264=`e0cf960…`、00265=`8600f0fa…`、00266=`fa7b451f…`）至 `tests/fixtures/spec99/`；生成 SHA256SUMS 清单（G0.9 真实复制件溯源——spec95/00189-reads 的 manifest+内联 `<!-- src: sha256:… -->` 溯源先例，此处采 SHA256SUMS 等价形）
- [ ] **Step 2:** 物化 harness：live=00264 的 user_prompt_blob 中 `<untrusted-source>` 的 character_matrix 段提取（含 `## 第 47 章状态增量` 空格形块）；staged=00264 response 的 matrix 输出经 `_increment_units`+upsert 物化；sidecar `{"chapter": 47}`——写入 tmp_path 结构 `staging/truth/character_matrix.md`+live 兄弟；**孪生用例**（I-2）：另一 tmp 结构补 `outline/volume_map.md`（span 覆盖 47-48）+staged 重写 live 孪生 48 块行
- [ ] **Step 3:** 红断言四处（**断言期望行为**——Task 2 时红、Task 3 后绿；证据链=改前红/改后绿与 spec T2(a) 一致）：①`_strip_increment_section(live, 47)` 输出**不含**自陈行（现行严格正则下红）；②`_check_matrix_structure(staged_pf)` **无** content_dropped（现行豁免失效下红）；③heading 形不一致的增量族 `_replace_section` 调用返回**非 None**且含替换文本（现行精确匹配下红）；④**孪生豁免行为测**（I-2）：sidecar 47+volume_map 覆盖 47-48+staged 重写 48 块行→断言无 content_dropped（现行只豁免 47 下红）
- [ ] **Step 4:** `uv run pytest tests/unit/gates/g4/test_spec99_h4_redgreen.py -q --no-cov` → **四红**（红即预期——粘贴 progress.md 验收 3 红侧证据）
- [ ] **Step 5:** Commit `test: spec #99 红侧固化——束7 blob 物化 harness+H4 四红（豁免失效/整链/写径归一/孪生豁免）`（**Task 2/3/4 同分支同 PR 一次性 push——中间 commit 红/④暂无①③⑤ 属分支内态，CI 管 push head**）

### Task 3: ④ 标题语法单源化+bundle 孪生豁免+三消费方接线（infra · tdd_red_green；协调者亲自）

**Files:**
- Modify: `src/shenbi/pipeline/truth_io.py`（新 helper 区，~:1570 前插入）
- Modify: `src/shenbi/gates/g4/state_settling.py`（:295-326 区）
- Modify: `src/shenbi/pipeline/read_extractors.py`（:916-918 区）
- Test: `tests/unit/gates/g4/test_spec99_h4_redgreen.py`（Task 2 文件转绿）+`tests/unit/pipeline/test_truth_io_increment_heading.py`（新建）

**Interfaces:**
- Produces（truth_io，后续消费方唯一来源）:
```python
def increment_heading_re(chapter: int, *, anchored: bool = True) -> re.Pattern[str]:
    """单源标题语法：容忍数字两侧空白（\s* 含 U+3000）。anchored=True 带
    \\s*$ 尾锚（gate 豁免严格形——带后缀标题不入豁免域）；False 为前缀形
    （提取器块检测，兼容尾注标题）。语法字面量唯一定义，禁另立副本。"""


def strip_increment_blocks(text: str, chapters: list[int]) -> str:
    """剥离给定章（bundle 含孪生章）的 `## 第N章状态增量` span。标题判定=
    increment_heading_re(chapter).match(line.strip())；span 边界=下一行
    line.lstrip().startswith('#')（不依赖 '## ' 前缀——消 ##第47章 形失配）。"""
```
- Consumes: `bundle_chapters(project_dir, chapter)`（gate 侧信号源——state_settling 已有 :245 函数级 import 先例）

- [ ] **Step 1:** truth_io 实现 helper（含 docstring 语法声明）；新建 `test_truth_io_increment_heading.py`：锚点双形/空格容错（半角+U+3000）/`##第47章` 形 strip 生效/尾缀标题 anchored 不中+unanchored 中/多章 bundle 剥离/非目标章保留——红→绿
- [ ] **Step 2:** gate 接线：`_strip_increment_section` 改委托 `strip_increment_blocks(live_text, [chapter])`；`_check_matrix_structure` 签名扩参 `project_dir: str | None = None`（**显式传参优于从 pf 推导**——g4_state_settling:1055 已有 project_dir 参数且 :1106 调用点作用域内在场，同 :234 `_balance_bundle_escalation(project_dir,…)` 先例；缺省 None→`[chapter]` 单例保持现行为零破坏）——豁免章集=`bundle_chapters(Path(project_dir), chapter)`（无 volume_map 退 singleton）；保留 `_strip_increment_section` 函数名（内部委托，调用方零改）
- [ ] **Step 3:** 提取器接线：read_extractors:916-918 的内联正则改 `increment_heading_re(n, anchored=False)`（行为等价——语法单源化）
- [ ] **Step 4:** 写径预匹配：`_replace_section` 增量族专用前置——section 首行命中 `increment_heading_re(N, anchored=False)`（任意 N——用 `第\s*\d+\s*章\s*状态增量` 泛化形）时，逐行标题比对改 `line.strip()` 经同正则规范化键比对（`第47章`≡`第 47 章`），**仅增量族生效**（其余 headed 分节维持精确匹配——加注释红线）；`test_truth_io_increment_heading.py` 补：空格/无空格互替成功+非增量族标题不归一
- [ ] **Step 5:** Task 2 四红转绿：`uv run pytest tests/unit/gates/g4/test_spec99_h4_redgreen.py -q --no-cov` → 四绿（**红绿证据齐**=spec 验收 3）
- [ ] **Step 6:** 零翻转：`uv run pytest tests/unit/gates/g4/ -q --no-cov` 全绿（gate 消费方断言零翻转=验收 2 前半）
- [ ] **Step 7:** `bash tests/lock-tool-hashes.sh`（**最后一步**——三个 src 文件均哈希锁定）→ Commit `fix: spec #99 ④——标题语法单源化（truth_io helper 双锚点）+bundle 孪生豁免+gate/提取器/写径三消费方接线`

### Task 4: ①③⑤ 教学面+配对/防回退断言（infra · 混合：Steps 1-4 改文+绿侧防回退断言/regression_guard，Steps 5-6 tdd_red_green；协调者亲自）

**Files:**
- Modify: `skills/shenbi-state-settling/SKILL.md`（:98-103 铁律 0 区/:248/:92 不动）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（:955 示例区——仅改示例字符串）
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（:1460-1470 #23 注入区）
- Modify: `src/shenbi/gates/g4/state_settling.py`（`_format_drops` :208-211 正例区）
- Create: `tools/lint_increment_teaching.py` + justfile check 面接线
- Test: `tests/unit/pipeline/test_append_dedup_increment_injection.py`（扩展）/`tests/unit/gates/g4/test_state_settling_feedback_spec95.py`（扩展）/`tests/unit/tools/test_lint_increment_teaching.py`（新建）

**Interfaces:**
- Consumes: Task 3 的 `increment_heading_re`（对称断言用真实现而非字面量——容错正则在场判定调 helper）
- Produces: ①③④⑤ 四面同批在分支上的终态；机械化配对断言两条

- [ ] **Step 1:** SKILL ①：铁律 0 增排除条款（:98 后插：「排除：本章自身（bundle 重派含孪生章 N+1）的 `## 第N章状态增量` 块是 keyed-upsert 可替换单元——重派整块替换该块**合法**，不属『已有行』」）+:100 消歧+引语双行正例（铁律 0 区正例小节：「live 已有 `- 自陈: 「…」` 引语行时：原句行原样保持；正文如有更全原句→新起一行 `- 自陈补全（第N章原句）: 「…」`——两行并存，禁改写原句行」）+:248 行 `create_or_overwrite（基底保全：逐字复现 live 基底＋仅追加增量／原键位更新行）` → `append_dedup（键合并：现有行由合并层保全——模型只发本章增量块，禁重发现有行）`
- [ ] **Step 2:** chapter_loop.py:955 示例 `## 第 2 章状态增量` → `## 第2章状态增量`（无空格规范形）
- [ ] **Step 3:** dispatch_helper ⑤：注入文本两处修正——"MUST be a new `## 第N章状态增量` block only" → "MUST be the chapter's own `## 第N章状态增量` block(s) only（bundle 双章=leader 与 follower 各一块）"；"NEVER modify or extend any existing row or any earlier `## 第N章状态增量` section" → "NEVER modify any existing row or any **other chapter's** increment section（本章自身的增量块是 keyed-upsert 可替换单元——重派时整块重发合法）"；扩展 `test_append_dedup_increment_injection.py`（:89 后）：断言注入含 "other chapter's" 排除措辞+含 "两块/each" 双章口径（防回退断言）
- [ ] **Step 4:** G4 报文 ③：`_format_drops` 正例区扩引语形（表格正例后追加引语双行正例——文案与 SKILL ① 正例一致）；扩展 `test_state_settling_feedback_spec95.py`：断言 `_format_drops([...])` 输出含「自陈补全」双行正例（防回退）
- [ ] **Step 5:** 配对断言×2（新建 `tests/unit/gates/g4/test_spec99_pairing_guards.py`）：(a) `increment_heading_re(47, anchored=True).pattern` 含 `\s*`（容错在场）⇒ `_format_drops` 输出含引语正例 且 SKILL 铁律 0 区含排除条款（读 SKILL.md 文件断言）；(b) 对称：`_check_matrix_structure` bundle 豁免在场（grep 源文件 `bundle_chapters` 调用）⇒ dispatch_helper 注入含双章口径（读源断言）——红→绿
- [ ] **Step 6:** 存在性 lint：`tools/lint_increment_teaching.py`（检查 SKILL.md 铁律 0 区含「排除」+引语正例、chapter_loop 示例无空格形、dispatch_helper 注入含双章口径——三文件 grep 面；exit 1 带行号报告）；justfile check 面接线（仿既有 lint 工具行）+`test_lint_increment_teaching.py`（绿面+tamper 红）
- [ ] **Step 7:** `bash tests/lock-tool-hashes.sh` → Commit `feat: spec #99 ①③⑤——铁律 0 own-block 排除+引语双行正例+#23 注入双矛盾修正+配对/防回退断言+存在性 lint`
- [ ] **Step 8:** 验收 2 后半核对：`just check` 全绿（lint 入面后）——输出粘贴 progress.md

### Task 5: 收口与登记（leaf）

**Files:**
- Modify: `docs/superpowers/plans/INDEX.md`（本 plan 状态 ✅ ready→executed）
- Modify: `docs/superpowers/specs/INDEX.md`（#99 状态：执行中 T0-T2 完成+T3 待续跑令）

**Interfaces:** Consumes: Task 1-4 产出。

- [ ] **Step 1:** plans/INDEX 登记；specs/INDEX #99 状态行更新
- [ ] **Step 2:** progress.md 验收覆盖表核对（spec 验收 1→Task 1/2→Task 3+4/3→Task 2+3/4→批外 T3 声明）；deviations 归档（T0 判别法结论若裁 H1 真阳性在场→记①③定位升级）
- [ ] **Step 3:** Commit `docs: spec #99 收口登记——T0-T2 完结+T3 批外待续跑令`

---

## 验收覆盖表

| Spec 验收 | Task | 可执行验证 |
|---|---|---|
| 1. T0 报告落 docs/research/ | Task 1 | `docs/research/2026-11-08-spec99-t0-autopsy.md` 在盘五节齐 |
| 2. PR 合并（CI 全绿+零翻转+①③④⑤同批+配对机械化+⑤防回退+①lint） | Task 3+4 | Task 3 Step 6 零翻转输出+Task 4 Step 8 `just check`+PR CI |
| 3. T2 红绿记录 | Task 2+3 | Task 2 Step 4 三红 → Task 3 Step 5 三绿 |
| 4. T3 实弹窗疗效（双观测线+supersede #19） | **批外**（束8 续跑窗台账） | vol1-ledger 束8 条目（续跑令=T3 启动条件） |

## G3.4 / F947 声明

- 本 plan 无生成型输出评分面——G3.4 独立评分**不适用**（无 LLM 产物验收）。
- F947：spec T3 实弹依赖已在 r2 拆解为 T2 离线红绿（本 plan Task 2/3）+T3 观测记录（批外台账）——**执行期零现场 dispatch 取证**。

## 复杂度与路由

Task 0/1/5=leaf（可分派）；**Task 2/3/4=infra（协调者亲自**——pipeline/truth_io+gates/g4+契约教学面跨模块+哈希锁工序）。
