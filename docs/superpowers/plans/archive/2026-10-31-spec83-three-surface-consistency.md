# Spec #83 三面一致性之网 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 正文/声明/truth/大纲四面之间补上对账器、联动器与回灌路径——7 类门/工具（POST 引句 verbatim、修订联动、canon 回灌 lint、打摆切换、follower 完成语义、数字锚、验收口径清偿）全部按 shadow 纪律落地。

**Architecture:** 门侧扩既有 G4.cd/G4.ss 执法面与 #82 共基（quote_verbatim.py / shadow.py 路由），管线侧升格既有回调（_revalidate_revised_chapter / _complete_chapter / _append_feedback_injections），工具侧新建 lint_outline_truth_drift 驱动侧对账族。全部新 FAIL 支路走 §10 shadow checklist（GATE_TO_SHADOW_KEY 登记 + id-first 发射 + 消费点接线），状态字面量走 §11 落点表。

**Tech Stack:** Python 3.11+ / pathlib / structlog / pytest（uv run --frozen 同构）；本 spec 无前端、无新依赖。

**Spec:** `docs/superpowers/specs/2026-10-30-spec83-three-surface-consistency.md`（r5.3，main 5c7563dc）

## Global Constraints

- 铁律 L-C：对账器只对结构化可判定子集动手（引句逐字/数值锚/清单枚举），语义级留评审，不造 NLP 假象。
- 铁律 L-D：全部新 FAIL 门带 shadow 配置位（`GATE_TO_SHADOW_KEY` 登记；键缺席=默认 shadow:true → demote——`shadow.py:61-64` 语义），卷二首束（ch37-38）WARN 试运行零误伤后升 FAIL。
- 发射形态铁律 id-first：所有新 must_fix 串一律 `G4.<id>:<path>:<detail>` 形（`check_id()` shadow.py:43-46 按串首 `G4\.([a-z_.]+)` 提取）。
- **锚点回放纪律（审查轮 1 C1/C2 教训）**：每个新正则锚点（执法行/句式/声明形态）**写入 plan/代码前必须先对语料回放**——`grep -n` 真实行形、粘贴命中行作锚证据，再定稿正则。已实证形态锚：转折词声明行=`- [ ] 转折词密度: 0 / 3625字 = 0 (≤ 1/3000)`（ch1:229/ch28:237）；余额句=`纸包里剩一百零三文`（ch26:26，裸「剩」）/`剩下的一百零三文`（ch26:177）；字数声明行=`- [ ] 正文字数（逐段计数合计）: …；总计 3625`（ch1:233）/`总计 1029+1098+1060=3187`（ch28:241）。
- 状态字面量单一落点（§11）：`declarations_stale`/`bundle_merged`/`streak_monitor_rewinds`/`provenance` 只出现在 §11 钉死的落点，禁止散布。
- G0.9：fixtures 只能是真实 skill 输出的拷贝（源=`novel-xinghuo-vol1/`，gitignored 磁盘真项目）；结构测试可 tmp_path 构造，但 scenario 输入引用真实产物。
- 核心原则 8：SDD 全流程禁为「验证」触发真实 dispatch/pipeline；一切验收用 fixtures 驱动测试表达。
- 框架纯度：`src/shenbi/` 无 `print()`、gate 检查器纯函数幂等、pathlib、structlog。
- commit 纪律：Conventional Commits；**显式列文件路径，禁止 `git add -A`/`git add .`**（worktree 常有用户未提交改动）。
- 验证命令一律 `just`/`uv run`（与 CI `uv run --frozen` 同构）。
- 测试 fixture 路径约定（**轮 3 I5 按目录深度分表**）：`tests/unit/gates/g4/`→`parents[3]`（对齐 test_quote_verbatim.py:16 先例）；`tests/unit/pipeline/`、`tests/unit/tools/`→`parents[2]`（先例 test_check_severity_vocab.py:13）；`tests/integration/`→`parents[1]`。目标一律 `…/fixtures/spec83/`——按测试文件所在深度取 parents 层级，勿跨目录套用。测试 sketch 中的 `FIX` 均指该根（每文件自行定义，轮 4 N7a）。

## 验收覆盖表（spec §9 → task → 可执行验证）

| spec 验收 | task | 验证命令（fixtures 驱动/只读） |
|---|---|---|
| §9.1 全部新门/工具红测→绿 + shadow 位默认 | T1-T13 各自 | `uv run pytest tests/unit/gates/g4/test_spec83_*.py tests/unit/pipeline/test_spec83_*.py tests/unit/tools/test_spec83_*.py -v`（红→绿在各 task 步骤内）；`ls` 核对 shadow 登记断言（test_shadow_demotion.py 扩展） |
| §9.1 `just check` exit 0 | 阶段 7 | `just check` |
| §9.2 卷二首束实弹（settle 反馈定向/status 全 complete/POST 门零 FAIL/T2 零 stale） | T2/T4/T5/T6/T7/T8 | F947 离线改写：各机制单测/集成测试即验收面；**卷二实弹归 #84 驱动侧运行窗口**（本 plan 在 T13 收尾记 deviation 注记，不在本批伪造运行证据） |
| §9.3 束前 lint_outline_truth_drift 零悬空 | T12 | `uv run pytest tests/unit/tools/test_spec83_outline_drift.py -v`（卷一四实证夹具） |
| §9.4 余额/计数零漂移（WARN 面人工裁决） | T9/T10 | `uv run pytest tests/unit/gates/g4/test_spec83_counter_anchor.py tests/unit/gates/g4/test_spec83_balance_anchor.py -v` |
| §9.5 regen-accept 判据 5 转绿 | T13 | `uv run pytest tests/unit/tools/test_spec83_regen_accept_voice.py -v`（声口 token 族单测；卷一语料整卷 PASS 归运行窗口——工具面替换的口径单测） |

**评分场景声明**：本 plan 无评分场景（全部验收为 fixtures 驱动测试 + 只读 CLI），不涉及 G3.4 独立评分调度。
**F947 合规**：spec §9.2 运行侧判据全部改写为离线测试（上表）；无 task 依赖真实 dispatch。

## 任务总览与依赖

| Plan task | Spec 映射 | 复杂度 | test_kind | 依赖 |
|---|---|---|---|---|
| T0 | fixtures 基建 | infra | —（拷贝+存在性断言） | — |
| T1 | spec T1 前置（嵌套提取） | infra | tdd_red_green + characterization | T0 |
| T2 | spec T1 门（cd.post_quote_verbatim） | infra | tdd_red_green | T1 |
| T3 | spec T1 交叉门（transition 修正+cd.post_transition_cross+字数行 WARN） | infra | tdd_red_green | T2（改 T2 建的 post_declarations.py） |
| T4 | spec T2 主修法（rev.prop_purged） | infra | tdd_red_green | T0 |
| T5 | spec T2 次级（stale 状态链） | infra | tdd_red_green + characterization | T4（同函数面） |
| T6 | spec T4 计数器+切换 | infra | tdd_red_green + characterization | T0 |
| T7 | spec T4 分族路由 | infra | tdd_red_green | T6 |
| T8 | spec T5 follower 完成语义 | infra | tdd_red_green + characterization | T6（_complete_chapter 共改点，串行） |
| T9 | spec T6 计数锚扩族 | infra | tdd_red_green + characterization | T0 |
| T10 | spec T6 余额锚 | infra | tdd_red_green | T2+T9（post_declarations.py 追加＋同 G4.cd 面串行） |
| T11 | spec T6 来历锚 | infra | tdd_red_green | T2（post_declarations.py 追加） |
| T12 | spec T3 工具 | leaf（tools/ 新文件+just/docs 登记，无 src/shenbi infra 改动） | tdd_red_green | T0 |
| T13 | spec T7 口径清偿 | infra | tdd_red_green + characterization | T12（--declarations 同文件） |

排序依据（rubric 维度 8）：T1 共基提取器先于 T2 门（门的地基）；T3 内修复先于门发射（同 task 内步序）；T9 门先于 T10（同文件面串行防冲突）。全部 infra task 协调者亲自实现（v7 leaf/infra 分流）；T12 可分派 implementer 子 agent（仍须 task 后 fresh-context 重审）。

---

### Task 0: fixtures 基建（spec83 语料包）

**Files:**
- Create: `tests/fixtures/spec83/README.md`（来源清单+拷贝日期+源目录说明）
- Create: `tests/fixtures/spec83/chapters/chapter-{1,2,6,13,16,17,19,23,25,26,28,30,31,33,35}.md`（自 `novel-xinghuo-vol1/chapters/` 精确拷贝；35=来历锚「渡口那夜」实证；19=尾注引句实证（审查轮 1 I8）；**23=余额锚深位首现绿测**（轮 4 N1：:300 付后 143 vs 付前 183 健康章，first_scene_span/META 位置排除双面设计的回归钉））
- Create: `tests/fixtures/spec83/characters/`（**递归**拷贝 `novel-xinghuo-vol1/characters/{major,minor}/*.md + protagonist.md`——布局非扁平；**≥5 张带卡面标记卡**（审查轮 1 I4：`check_blind_recognition` 在 `len(cards) < 5` 硬 FAIL，2-3 张无法走真实入口；relationships.md 不拷——`_load_cards` 跳过之）
- Create: `tests/fixtures/spec83/genesis-context/chapter_outline.md`（精确拷贝——**欠账进度表实锚在 :370「三大打卡装置/还账进度表（私账打卡）」节**（审查轮 1 I3：outline/volume_map.md:123/:430 仅引用不带表），T12 第四对账面数据源）
- Create: `tests/fixtures/spec83/plans/chapter-28-plan.md`、`chapter-1-plan.md`（精确拷贝）
- Create: `tests/fixtures/spec83/truth/particle_ledger.md`、`prop_registry.md`、`facts/counters.json`、`facts/props.json`（精确拷贝）
- Create: `tests/fixtures/spec83/outline/volume_map.md`（精确拷贝）
- Test: `tests/unit/gates/g4/test_spec83_fixtures.py`

**Interfaces:**
- Produces: 后续全部 task 的 fixture 根路径 `tests/fixtures/spec83/`（各测试文件按 Global Constraints 的 `parents[3]` 约定取用——深度随测试目录层级调整，禁止 parents[2] 型错指）。

- [ ] **Step 1: 拷贝清单执行**

```bash
SRC=novel-xinghuo-vol1; DST=tests/fixtures/spec83
mkdir -p $DST/chapters $DST/plans $DST/truth/facts $DST/outline $DST/characters $DST/genesis-context
for n in 1 2 6 13 16 17 19 23 25 26 28 30 31 33 35; do cp $SRC/chapters/chapter-$n.md $DST/chapters/; done
cp $SRC/plans/chapter-28-plan.md $SRC/plans/chapter-1-plan.md $DST/plans/
cp $SRC/truth/particle_ledger.md $SRC/truth/prop_registry.md $DST/truth/
cp $SRC/truth/facts/counters.json $SRC/truth/facts/props.json $DST/truth/facts/
cp $SRC/outline/volume_map.md $DST/outline/
cp $SRC/genesis-context/chapter_outline.md $DST/genesis-context/
cp -R $SRC/characters/major $SRC/characters/minor $DST/characters/ && cp $SRC/characters/protagonist.md $DST/characters/ 2>/dev/null; ls $DST/characters/major | wc -l  # ≥5 张卡面核验（不足则全量拷，relationships 不拷）
```

G0.9：全部为真实 skill 输出/运行工件精确拷贝（chapter= drafting 产物、plan= planning 产物、truth=facts 体系运行态、volume_map= 大纲面）。chapters/chapter-N-pre-rev.md 修订对**不入包**（T4 红测以真实章为基底 tmp_path 构造修订后版本——结构测试豁免面）。

- [ ] **Step 2: 写存在性/形态断言测试**

```python
# tests/unit/gates/g4/test_spec83_fixtures.py
"""spec #83 fixture 包存在性与关键锚断言（G0.9 拷贝证明）。"""
from pathlib import Path

FIX = Path(__file__).resolve().parents[3] / "fixtures" / "spec83"  # parents[3]——tests/unit/gates/g4/ 深四层

def test_chapter_anchors_present():
    # spec 钦定实证锚：ch1:231 嵌套实证句 / ch6 截断金句 / ch28 双声明
    ch1 = (FIX / "chapters" / "chapter-1.md").read_text(encoding="utf-8")
    assert "却不知道明天城就破了" in ch1
    ch28p = (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")
    assert "计数: 鉴录名数 4+0" in ch28p and "计数: 鉴录名数 4 +1" in ch28p

def test_truth_faces_present():
    assert (FIX / "truth" / "particle_ledger.md").is_file()
    assert (FIX / "truth" / "facts" / "counters.json").is_file()
    import json
    counters = json.loads((FIX / "truth" / "facts" / "counters.json").read_text(encoding="utf-8"))
    assert counters["facts"]["鉴录名数"]["value"] == 4  # 实文件嵌套在 "facts" 键下（审查轮 2 M5：裸 ["鉴录名数"] KeyError）；r5.1：终态 4；ch9 时序绿测须另行构造 facts=3
```

- [ ] **Step 3: 运行测试确认通过**

Run: `uv run pytest tests/unit/gates/g4/test_spec83_fixtures.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/spec83 tests/unit/gates/g4/test_spec83_fixtures.py
git commit -m "test: add spec83 real-corpus fixture pack (G0.9 exact copies)"
```

---

### Task 1: #82 共基提取器嵌套感知修复＋位置法排尾注

**Files:**
- Modify: `src/shenbi/gates/g4/quote_verbatim.py:21`（`_QUOTE_RE`）、`:64-77`（`extract_meta_quotes`）
- Test: `tests/unit/gates/g4/test_quote_verbatim.py`（扩展）

**Interfaces:**
- Consumes: 无（现基线：`_QUOTE_RE = re.compile('[「『“"]([^「」『』“”"]+)[」』”"]')`）
- Produces: `extract_meta_quotes(chapter_text: str, *, min_len: int = 6) -> list[str]`（签名不变；嵌套「」感知＋尾注括号区间排除；新 kwarg `regions_only: str = "META"` 不加——保持签名冻结）。嵌套正则常量 `_NESTED_QUOTE_RE = re.compile("「((?:[^「」]|「[^「」]*」)*)」")`（r4b 探针实测形）。

**复杂度: infra**（gates/g4 核心正则，#82/#83 共基；3+ 消费面）· **test_kind: tdd_red_green + characterization**（#82 面回放）

**测试层级: T1（unit）** · fixtures: `tests/fixtures/spec83/chapters/chapter-1.md`（嵌套实证句）、`chapter-19.md`（尾注排除——审查轮 1 I8）、全 15 章包（#82 面回放）

- [ ] **Step 1: 写红测**

```python
# tests/unit/gates/g4/test_quote_verbatim.py 追加
NESTED_SENTENCE = "心里记下这笔「听不懂的账」——却不知道明天城就破了"  # ch1:231 外层「」内嵌「」

def test_nested_quote_extracted_from_meta():
    ch1 = (FIX / "chapters" / "chapter-1.md").read_text(encoding="utf-8")
    quotes = extract_meta_quotes(ch1, min_len=6)
    assert any("听不懂的账" in q and "城就破了" in q for q in quotes)  # r4 实测：现行零命中 → 红

def test_paren_span_quotes_excluded():
    # 审查轮 1 I8：ch19 实证 3 条尾注形（（从备忘段6「章尾张力拍」行）/（把「遗物：无。灯一盏」的「无」轻轻划掉…）/（收束钩：「粥凉了，不算折耗。」…））
    # 轮 3 M10：测试内自备复算 helper——按 match 位置（非引句串）判括号归属
    from shenbi.gates.g4.quote_verbatim import _NESTED_QUOTE_RE, _QUOTE_RE, _meta_regions, _PAREN_SPAN_RE
    ch19 = (FIX / "chapters" / "chapter-19.md").read_text(encoding="utf-8")
    quotes = extract_meta_quotes(ch19, min_len=6)
    raw_n = 0
    for region, _rs, _re_ in _meta_regions(ch19):
        spans = [m.span() for m in _PAREN_SPAN_RE.finditer(region)]
        raw_n += sum(
            1
            for rx in (_NESTED_QUOTE_RE, _QUOTE_RE)
            for m in rx.finditer(region)
            if len(m.group(1)) >= 6 and not any(ps <= m.start() < pe for ps, pe in spans)
        )
    assert raw_n == len(quotes)  # 复算（未排除面-位置法）与提取器一致
    assert any("粥凉了" in q for q in (  # 尾注内引句「粥凉了，不算折耗。」确被位置法弃置
        m.group(1) for region, *_ in _meta_regions(ch19) for m in _NESTED_QUOTE_RE.finditer(region)
    )) and "粥凉了，不算折耗。" not in quotes

def test_spec82_anchor_extraction_unchanged():
    # #82 面回归（r5.3 注记）：extract_anchor_quotes 用独立『』行正则，不受 _QUOTE_RE 影响
    # 全 15 章 fixture 回放：anchor 面逐字守恒（『』锚不含「」）；plan 在包内的章（ch1/ch28）
    # 走完整 extract_anchor_quotes(plan_text) 路径
    plan1 = (FIX / "plans" / "chapter-1-plan.md").read_text(encoding="utf-8")
    for _tier, q in extract_anchor_quotes(plan1):
        assert q and "「" not in q  # 『』锚面不含「」
    for p in sorted((FIX / "chapters").glob("chapter-*.md")):
        text = p.read_text(encoding="utf-8")
        assert extract_meta_quotes(text, min_len=1) is not None  # 全包 15 章提取不崩（守恒面在 T2 基线测试承载）
```

- [ ] **Step 2: 运行确认红**

Run: `uv run pytest tests/unit/gates/g4/test_quote_verbatim.py -v -k nested`
Expected: FAIL（嵌套实证句零命中）

- [ ] **Step 3: 最小实现**

```python
# quote_verbatim.py
# r4 钉死嵌套感知式（一轮实测 ch1 实证句可提取）；不用最长匹配——按行 greedy 会把
# 双引句行（ch1:234/235、ch6:298「场景1「…」／场景2「…」」形）合并成跨 / 假引句。
_NESTED_QUOTE_RE = re.compile("「((?:[^「」]|「[^「」]*」)*)」")
_QUOTE_RE = re.compile('[『“"]([^『“”"]+)[』”"]')  # 单层族保留（『』“”不嵌套于语料）
_PAREN_SPAN_RE = re.compile(r"（[^（）]*）")

def _meta_regions(chapter_text: str) -> list[tuple[str, int, int]]:
    """(region_text, start, end) —— 位置法排尾注需要 match 绝对位置。"""
    regions: list[tuple[str, int, int]] = []
    for m in _META_BLOCK_RE.finditer(chapter_text):
        regions.append((m.group(0), m.start(), m.end()))
    for m in _META_SECTION_RE.finditer(chapter_text):
        regions.append((m.group(0), m.start(), m.end()))
    return regions

def extract_meta_quotes(chapter_text: str, *, min_len: int = 6) -> list[str]:
    """（docstring 保留 #83 seam 说明，追加：嵌套「」感知＋全角括号尾注区间位置法排除。）"""
    out: list[str] = []
    for region, _rs, _re in _meta_regions(chapter_text):
        paren_spans = [m.span() for m in _PAREN_SPAN_RE.finditer(region)]
        nested_spans: list[tuple[int, int]] = []
        for m in _NESTED_QUOTE_RE.finditer(region):
            nested_spans.append(m.span())
            if len(m.group(1)) < min_len:
                continue
            if any(ps <= m.start() < pe for ps, pe in paren_spans):  # 位置法，非文本剥除
                continue
            out.append(m.group(1))
        for m in _QUOTE_RE.finditer(region):
            if any(ns <= m.start() < ne for ns, ne in nested_spans):  # M16 去重：单层命中落嵌套 span 内弃
                continue
            if len(m.group(1)) < min_len:
                continue
            if any(ps <= m.start() < pe for ps, pe in paren_spans):
                continue
            out.append(m.group(1))
    return out
```

注意：min_len 语义保持（≥6 默认）；T2 门调用方对执法两行传 `min_len=1`（1 字引句逃逸面已知注记，逐字臂平凡命中即绿——spec r5.1）。**嵌套去重（审查轮 1 M16 钉死，实现见上 sketch 的 `nested_spans` 块）**：语料存在 `「…『制度』『私放』『借』…」` 形（ch31 章尾行，「」内嵌『』）——单层 `_QUOTE_RE` 命中落在嵌套 span 内则弃（span 级去重，非字符串比较）。

- [ ] **Step 4: 运行确认绿 + #82 面回放**

Run: `uv run pytest tests/unit/gates/g4/test_quote_verbatim.py -v`
Expected: 全 PASS（含 #82 面守恒）
Run: `uv run pytest tests/unit/gates/g4/ tests/gates/ -q`
Expected: 既有 #82 门测试零回归

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/quote_verbatim.py tests/unit/gates/g4/test_quote_verbatim.py
git commit -m "feat: nested-aware meta quote extraction + paren tail-note position exclusion (spec #83 T1 prerequisite)"
```

---

### Task 2: `cd.post_quote_verbatim` 两臂门（声明↔正文）

**Files:**
- Create: `src/shenbi/gates/g4/post_declarations.py`（判定器模块：两执法行正则＋两臂判定——chapter_drafting.py 已 950+ 行，判定器独立成文件保持聚焦）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（主循环接线：PRE/POST 检查段 :630-640 后）
- Modify: `src/shenbi/gates/g4/shadow.py:28-40`（GATE_TO_SHADOW_KEY 登记）
- Test: `tests/unit/gates/g4/test_spec83_post_quote.py`

**Interfaces:**
- Consumes: `extract_meta_quotes(chapter_text, *, min_len)`（T1 产出）、`quote_in_chapter(quote, chapter_text)`（quote_verbatim.py:34 现有）、`strip_narrative_body`（gates/shared.py:337 现有）
- Produces:
  - `POST_GOLDEN_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*金句位\s*[：:]", re.M)`
  - `POST_TAIL_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*章尾张力（G4\.cd 口径）\s*[：:]", re.M)`（r4b 探针实测形态；ch25 变体行 `- [x] 章尾张力:` 无口径标签**不命中**＝设计内）
  - `_CLAUSE_SPLIT_RE = re.compile(r"[。！？；，、：·—–…「」『』“”\"'（）()\[\]【】《》〈〉？！!?:;,./｜|＝=＋+＊*～\s]+")`（r4b `_PUNCT` 全标点族——切分与归一同源一次完成）
  - `check_post_quote_verbatim(content: str) -> tuple[list[str], list[str]]` → `(fail_items, warn_items)`；fail 项形 `cd.post_quote_verbatim:『<q[:24]>…』<detail>`
  - shadow 键 `("market_params", "post_quote_verbatim")`

**复杂度: infra** · **test_kind: tdd_red_green** · **测试层级: T1** · fixtures: spec83/chapters/{1,2,6,13,16,19,25,26,28,30,31,33}.md

- [ ] **Step 1: 写红测（5 FAIL 全集 + 7 WARN 形态 + 三负例；尾注排除行为测在 T1/ch19 承载，本 task 不重复）**

```python
# tests/unit/gates/g4/test_spec83_post_quote.py
"""spec #83 T1: cd.post_quote_verbatim 两臂判定——r5 全语料回放钉死基线。
红测 5 例（ch1/ch6/ch2/ch31/ch33 声明失真）；WARN（ch13/16/19/26 标点/复合变体）；
负例：ch28 微粒钩不入面 / ch25 变体标签行不入面 / ch30 尾注弃。"""
from shenbi.gates.g4.post_declarations import check_post_quote_verbatim

def _fails(ch: int) -> list[str]:
    text = (FIX / "chapters" / f"chapter-{ch}.md").read_text(encoding="utf-8")
    fails, warns = check_post_quote_verbatim(text)
    return fails

def test_five_distortion_fails():  # r5 回放 5 FAIL 全集逐章断言
    assert any("城就破了" in f for f in _fails(1))      # 正文无此句
    assert any("册子认得" in f for f in _fails(6))      # 正文=册子认得人（截断漂移，子句等值不豁免）
    assert any("账上" in f for f in _fails(2))          # 归并缩写（添「账上」）
    assert any("私账" in f or "头一行" in f for f in _fails(31))
    assert any("旗会换" in f or "价会变" in f for f in _fails(33))

def test_punct_variants_warn_not_fail():  # ch13/16/19/26 逐字缺席但子句全在 → WARN 不 FAIL
    for ch in (13, 16, 19, 26):
        fails, warns = check_post_quote_verbatim(
            (FIX / "chapters" / f"chapter-{ch}.md").read_text(encoding="utf-8"))
        assert fails == [], f"ch{ch} 应零 FAIL（回放基线）"

def test_negative_faces():  # 微粒钩移出执法面/变体行不入面（行为级断言——审查轮 2 M8）
    fails28, _ = check_post_quote_verbatim((FIX / "chapters" / "chapter-28.md").read_text(encoding="utf-8"))
    assert not any("王朝的命" in f for f in fails28)   # 跨段转述微粒钩 → G3.4 兜底
    text25 = (FIX / "chapters" / "chapter-25.md").read_text(encoding="utf-8")
    fails25, _ = check_post_quote_verbatim(text25)     # ch25 变体行 `- [x] 章尾张力:`（无口径标签）不入执法面
    tail_variant = [l for l in text25.splitlines() if "章尾张力" in l and "[x]" in l and "G4.cd" not in l]
    if tail_variant:  # 变体行存在时：其行内引句不产生 FAIL（正则不收行）
        assert not any("章尾张力" in f for f in fails25)
```

- [ ] **Step 2: 运行确认红**

Run: `uv run pytest tests/unit/gates/g4/test_spec83_post_quote.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现判定器 + 接线 + shadow 登记**

```python
# src/shenbi/gates/g4/post_declarations.py（新文件，框架纯度：无 print、纯函数）
"""spec #83 T1: POST 声明引句 verbatim 门判定器（声明↔正文对账）。

执法面＝POST「金句位」＋「章尾张力（G4.cd 口径）」两行（r5 全语料回放 36 章 68 行）。
两臂判定（r5 定稿）：逐字臂缺席 → 子句臂（标点归一子句等值，切分与归一同源）：
任一子句缺席 → FAIL；子句全在 → WARN（交 G3.4 评审）。微粒钩/PRE 面/无引号裸句
张力声明不入执法面（spec §1 裁定）。"""
from __future__ import annotations
import re

from shenbi.gates.g4.quote_verbatim import (  # 轮 4 N7b：仅引所用（_meta_regions 不用）
    _NESTED_QUOTE_RE,
    _PAREN_SPAN_RE,
    _QUOTE_RE,
    quote_in_chapter,
)
from shenbi.gates.shared import strip_narrative_body

POST_GOLDEN_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*金句位\s*[：:](.*)$", re.M)
POST_TAIL_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*章尾张力（G4\.cd 口径）\s*[：:](.*)$", re.M)
_CLAUSE_SPLIT_RE = re.compile(
    r"[。！？；，、：·—–…「」『』“”\"'（）()\[\]【】《》〈〉？！!?:;,./｜|＝=＋+＊*～\s]+"
)

def _line_quotes(line_text: str) -> list[str]:
    out: list[str] = []
    paren_spans = [m.span() for m in _PAREN_SPAN_RE.finditer(line_text)]
    for m in (*_NESTED_QUOTE_RE.finditer(line_text), *_QUOTE_RE.finditer(line_text)):
        if any(ps <= m.start() < pe for ps, pe in paren_spans):
            continue  # 尾注位置法
        out.append(m.group(1))
    return out

def _clauses(text: str, min_len: int = 2) -> set[str]:
    return {c for c in _CLAUSE_SPLIT_RE.split(text) if len(c) >= min_len}

def check_post_quote_verbatim(content: str) -> tuple[list[str], list[str]]:
    fails: list[str] = []
    warns: list[str] = []
    prose_clauses: set[str] | None = None
    for line_re in (POST_GOLDEN_LINE_RE, POST_TAIL_LINE_RE):
        for m in line_re.finditer(content):
            for q in _line_quotes(m.group(1)):
                if quote_in_chapter(q, content):
                    continue  # 逐字臂绿
                if prose_clauses is None:
                    prose_clauses = _clauses(strip_narrative_body(content))
                missing = [c for c in _clauses(q) if c not in prose_clauses]
                if missing:
                    fails.append(
                        f"cd.post_quote_verbatim:『{q[:24]}…』声明子句缺席「{'、'.join(missing[:3])}」"
                        "——POST 自检引句须逐字/子句取自正文（修复者: drafting 改声明一行）"
                    )
                else:
                    warns.append(f"cd.post_quote_verbatim:『{q[:24]}…』逐字缺席但子句全在（标点/复合变体，交评审）")
    return fails, warns
```

chapter_drafting.py 接线（PRE/POST 块存在性检查 :636-640 之后、transition 计数前）：

```python
        # spec #83 T1: POST 声明引句两臂门（执法两行；WARN 臂进 c 列表交评审）
        from shenbi.gates.g4.post_declarations import check_post_quote_verbatim
        _pq_fails, _pq_warns = check_post_quote_verbatim(content)
        for _f in _pq_fails:
            mf.append(f"G4.{_f.split(':', 1)[0]}:{fp}:{_f.split(':', 1)[1]}")  # id-first 铁律
        for _w in _pq_warns:
            c.append({"id": "cd.post_quote_verbatim", "file": fp, "s": GateStatus.WARN, "r": _w})
```

shadow.py 登记（`GATE_TO_SHADOW_KEY` dict 追加）：

```python
    # spec #83 §10 checklist（行 1）：POST 引句两臂 FAIL 臂（勿与 #82 G4.cd.quote_verbatim 混同）
    "cd.post_quote_verbatim": ("market_params", "post_quote_verbatim"),
```

消费点：mf 项经 `run_gate_g4` → chapter_loop `_shadow_route_g4`（:4333/:4016/:1387）自然 demote——无需额外接线（§10 r5.3 前提满足：经既有路径）。

- [ ] **Step 4: 运行确认绿 + shadow 断言**

Run: `uv run pytest tests/unit/gates/g4/test_spec83_post_quote.py tests/unit/gates/g4/test_shadow_demotion.py -v`
Expected: PASS；`test_shadow_demotion.py` 追加断言 `GATE_TO_SHADOW_KEY["cd.post_quote_verbatim"] == ("market_params", "post_quote_verbatim")`（同步骤内补）
Run: `uv run pytest tests/unit/gates/g4/ -q`
Expected: 既有面零回归

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/post_declarations.py src/shenbi/gates/g4/chapter_drafting.py src/shenbi/gates/g4/shadow.py tests/unit/gates/g4/test_spec83_post_quote.py tests/unit/gates/g4/test_shadow_demotion.py
git commit -m "feat: cd.post_quote_verbatim two-arm POST quote gate (spec #83 T1, shadow per L-D)"
```

---

### Task 3: count_transition_words 子串修正＋`cd.post_transition_cross` 交叉门＋字数行精度 WARN

**Files:**
- Modify: `src/shenbi/gates/shared.py:854-871`（`count_transition_words`）
- Modify: `src/shenbi/gates/g4/post_declarations.py`（交叉门判定器追加）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（:642-649 transition 段接线交叉门）
- Modify: `src/shenbi/gates/g4/shadow.py`（行 2 登记）
- Test: `tests/unit/gates/g4/test_spec83_transition_cross.py`（独立文件——commit pathspec 已按此钉）

**Interfaces:**
- Consumes: `count_transition_words(content) -> int`（shared.py:854）；`TRANSITION_SPECIFIC = ["不过", "此时", "突然", "终于", "于是"]`（shared.py:851）
- Produces:
  - `check_post_transition_cross(content: str) -> list[str]`（POST 报转折词 0 而剥后正文 `count_transition_words ≥1` → issue 串 `cd.post_transition_cross:...`）；shadow 键 `("market_params", "post_transition_cross")`
  - `check_post_wordcount_precision(content: str, actual_chars: int) -> list[str]`（**审查轮 1 I9 补：spec §1 字数行虚假精度 WARN——复用 G2 口径助手复算**）：POST 字数行声明总计 vs 实测差 >2% → WARN（spec r2：判据保留、实例泛化不指定）；形态锚=ch1:233 `- [ ] 正文字数（逐段计数合计）: …；总计 3625`／ch28:241 `总计 1029+1098+1060=3187`（总计值=行末裸数或 `=` 后数）
- **锚点回放（Global Constraints 纪律——审查轮 1 C1 教训）**：POST 转折词声明行实测形态=`- [ ] 转折词密度: 0 / 3625字 = 0 (≤ 1/3000)`（ch1:229）/`- [ ] 转折词密度: 0 / 3187 字 = 0（≤ 1/3000）`（ch28:237）——标签是**转折词密度**、值非行尾裸 0；正则必须先对此形回放命中再定稿
- 修法（最小面，ch17 两实例钉死）：`不过` 计数排除补语潜在形——`tc -= content.count("不过来") + content.count("不过去")`（算**不过**来的账/看**不过**去 形态；「不过来/去」的「不过」非转折用法）。

**复杂度: infra** · **test_kind: tdd_red_green**（修 shared 计数器=行为变更）· **测试层级: T1** · fixtures: spec83/chapters/chapter-17.md（:79/:186 两实例）+ chapter-1.md（交叉门/字数行真实声明行回放）

- [ ] **Step 1: 写红测**

```python
def test_transition_substring_noise_fixed():
    from shenbi.gates.shared import count_transition_words
    assert count_transition_words("算不过来的账，忽然说了一句") == 0  # ch17:79 补语形（:186 忽然=非计数例——轮 7 M3 勘误）
    assert count_transition_words("不过他还是走了") == 1  # 真转折不减

def test_post_transition_cross_fires_on_real_decl_form():
    # 红测用真实声明行形（审查轮 1 C1：ch1:229 实测 `- [ ] 转折词密度: 0 / 3625字 = 0 (≤ 1/3000)`）
    from shenbi.gates.g4.post_declarations import check_post_transition_cross
    real_decl = "- [ ] 转折词密度: 0 / 3625字 = 0 (≤ 1/3000)"
    content = f"## POST_WRITE_SELF_CHECK\n{real_decl}\n\n正文不过如此，他终于明白了。\n"
    assert check_post_transition_cross(content) != []
    # 负例：非 0 声明不触发
    ok = "## POST_WRITE_SELF_CHECK\n- [ ] 转折词密度: 1 / 3187 字 = 1\n\n正文。\n"
    assert check_post_transition_cross(ok) == []

def test_post_wordcount_precision_warn():
    # spec §1 字数行虚假精度（审查轮 1 I9 补）：声明 3625 vs 实测差 >2% → WARN
    from shenbi.gates.g4.post_declarations import check_post_wordcount_precision
    decl = "- [ ] 正文字数（逐段计数合计）: 场景1: 8+72=80；总计 80"
    warns = check_post_wordcount_precision(f"## POST_WRITE_SELF_CHECK\n{decl}\n", actual_chars=70)  # 差 12.5%
    assert warns != []
    assert check_post_wordcount_precision(f"## POST_WRITE_SELF_CHECK\n{decl}\n", actual_chars=79) == []  # 1.2% 带内
```

- [ ] **Step 2: 确认红** — Run: `uv run pytest ... -k "transition or wordcount_precision"` Expected: FAIL

- [ ] **Step 3: 实现**

shared.py 修（:868-870 后追加）：

```python
    # spec #83 T1 前置：补语潜在形（V+不过+来/去）非转折用法——ch17:79「算不过来的账」
    # 实弹误计 1 次；不修则 cd.post_transition_cross 反向误伤无过错正文
    tc -= content.count("不过来")
    tc -= content.count("不过去")
```

post_declarations.py 追加：

```python
# 形态锚：ch1:229 `- [ ] 转折词密度: 0 / 3625字 = 0 (≤ 1/3000)`（值后带 / N字 = N 尾巴，非行尾裸 0）
_POST_TRANSITION_DECL_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*转折词密度\s*[：:]\s*0\s*(?:/|（)", re.M)  # 轮 8 M2：兼收 ch23 变体形 `0（正文零显式转折词）`（1/36；漏检无害——shadow 起步欠检测面）
# 形态锚：ch1:233 `…；总计 3625` / ch28:241 `总计 1029+1098+1060=3187`（裸数或 = 后数）
_POST_WORDCOUNT_DECL_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*正文字数（逐段计数合计）\s*[：:].*?总计\s*(?:[\d+]+\s*=\s*)?(\d+)\s*$", re.M)

def check_post_transition_cross(content: str) -> list[str]:
    """POST 报「转折词密度 0」而剥后正文词法计数 ≥1 → FAIL（声明↔门计数交叉对账）。"""
    from shenbi.gates.shared import count_transition_words
    if not _POST_TRANSITION_DECL_RE.search(content):
        return []
    if count_transition_words(strip_narrative_body(content)) >= 1:
        return ["cd.post_transition_cross:POST 报「转折词密度 0」但正文词法计数 ≥1"
                "——自检声明与词法门计数互斥（修复者: drafting 改声明一行）"]
    return []

def check_post_wordcount_precision(content: str, actual_chars: int) -> list[str]:
    """spec §1 字数行虚假精度：声明总计 vs 实测差 >2% → WARN（复用 G2 口径助手复算精神）。"""
    issues: list[str] = []
    for m in _POST_WORDCOUNT_DECL_RE.finditer(content):
        declared = int(m.group(1))
        if declared <= 0:
            continue
        drift = abs(declared - actual_chars) / declared
        if drift > 0.02:
            issues.append(f"cd.post_wordcount_precision:声明总计 {declared} vs 实测 {actual_chars}"
                          f"（差 {drift:.1%} >2%）——虚假精度（修复者: drafting 改声明一行）")
    return issues
```

chapter_drafting.py :647-649 接线（transition 计数段内）：在既有 `tc > max_t` FAIL 后追加交叉门消费 `check_post_transition_cross(content)` → mf（id-first 同 T2 形）＋ `check_post_wordcount_precision(content, total_chars_md_text(content))` → `c.append WARN`（**审查轮 2 I2：实测口径必须 `total_chars_md_text`——`wc`（:570 `word_count_md`）是 CJK 计数，与 POST 逐段全字符总计系统性差 13-19%（ch1 声明 3625 vs CJK 3147），接 `wc` 会每章误 WARN**；`total_chars_md_text` 与修订复验字数带 :1494 同口径且内部走 strip_narrative_body）；字数行=评审面非 FAIL，不入 §10。**语料校准锚（轮 3 M8）**：ch28 0.5% 带内、ch1 5.5%/ch26 3.5% 为**真阳 WARN**（写手自计数偏差——虚假精度检测本意），characterization 断言钉此三例期望集，防后人误读「I2 修复=语料零 WARN」。shadow.py 登记 `"cd.post_transition_cross": ("market_params", "post_transition_cross")`。

- [ ] **Step 4: 确认绿 + 既有 transition 门回归**

Run: `uv run pytest tests/unit/gates/g4/ -q && uv run pytest tests/unit -k "transition" -q`
Expected: 全 PASS（含 G4.cd 转折密度门既有测试——`max(5, wc // 1000)` 阈值面不变，仅计数降噪）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/shared.py src/shenbi/gates/g4/post_declarations.py src/shenbi/gates/g4/chapter_drafting.py src/shenbi/gates/g4/shadow.py tests/unit/gates/g4/test_spec83_transition_cross.py
git commit -m "fix: transition-word complement-form dedup + cd.post_transition_cross gate + wordcount precision WARN (spec #83 T1)"
```

---

### Task 4: `rev.prop_purged` 修订联动复验扩面（spec T2 主修法）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:1416-1497`（`_revalidate_revised_chapter` 扩面）＋ `:4487-4493`（消费点 demote 接线）
- Test: `tests/unit/pipeline/test_spec83_rev_prop_purged.py`

**Interfaces:**
- Consumes: `entity_in_text(entity, text) -> bool`（chapter_drafting.py:66 现有 F16 三形匹配器——升格既有）、`strip_narrative_body`、pre-rev 备份 `chapters/chapter-N-pre-rev.md`（`_create_pre_revision_backup` chapter_loop.py:2771 现有写入、:1437 现有读取）
- Produces:
  - `parse_prop_lines(plan_text: str) -> list[str]`（入场行：`- {entity}@hold: {holder}` 与 `- 物象: {entity}|{holder}` 两形态——ch28-plan.md:86/:99 实测形（轮 7 M2 勘误：:98 是 事件 行）；`@lose`/`@mention`/`@none` 与 PRE 散文行不入场）
  - `check_prop_purge_on_revision(before_text: str, after_text: str, plan_text: str, *, chapter: int) -> list[str]`（相对谓词：`entity_in_text(名, strip(before)) ∧ ¬entity_in_text(名, strip(after))` → issue `rev.prop_purged:chapters/chapter-{chapter}.md:『名』…`——**chapter 必传**（审查轮 1 I5a：无参硬编码 chapter-N 字面量会污染重试反馈与 trace）；两侧同口径 strip_narrative_body——raw 面 PRE/POST 声明块自含物象名会使 pre 侧恒真）
  - shadow 键 `("market_params", "prop_purge_guard")`

**复杂度: infra**（chapter_loop 派发与状态机）· **test_kind: tdd_red_green** · **测试层级: T1 单测 + T2 集成（tests/integration/ 束链路径）** · fixtures: spec83/chapters/chapter-28.md + plans/chapter-28-plan.md（44 行清点基线）；红测修订后版本=tmp_path 构造（真实章为基底删物象段）

- [ ] **Step 1: 写红测**

```python
# tests/unit/pipeline/test_spec83_rev_prop_purged.py
"""spec #83 T2: 修订删物象相对谓词——r5 回放基线（44 行零修订全绿 / 7 例合法缺席修订其他段仍绿 / 删尽红）。"""
from shenbi.pipeline.chapter_loop import check_prop_purge_on_revision, parse_prop_lines

def test_zero_revision_corpus_all_green():  # r5 回放：全语料零删改现状全绿
    text = (FIX / "chapters" / "chapter-28.md").read_text(encoding="utf-8")
    plan = (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")
    assert parse_prop_lines(plan)  # @hold + 物象: 行非空（ch28 实测形态）
    assert check_prop_purge_on_revision(text, text, plan, chapter=28) == []  # chapter 必传（轮 3 M6）

def test_purge_detected(tmp_path):  # 修订删尽红：真实章基底构造 post（结构测试豁免面）
    text = (FIX / "chapters" / "chapter-28.md").read_text(encoding="utf-8")
    plan = (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")
    purged = text.replace("骨哨", "口哨")  # 物象名整段消失形（pre 命中 post 不命中）
    fails = check_prop_purge_on_revision(text, purged, plan, chapter=28)
    assert any("骨哨" in f and "rev.prop_purged:chapters/chapter-28.md" in f for f in fails)  # id-first 含真章号

def test_legal_absence_stays_green():  # ch4/6/27 类合法缺席：持有物象当章正文零提及为合法态
    # 零提及 → pre 侧不命中 → 谓词左元 false → 不红（相对口径核心）
    plan = "- 物象: 灰底采买旗|那罕\n"
    assert check_prop_purge_on_revision("别的正文", "改后的别的正文", plan, chapter=33) == []
```

- [ ] **Step 2: 确认红** — Run: `uv run pytest tests/unit/pipeline/test_spec83_rev_prop_purged.py -v` Expected: FAIL（ImportError）

- [ ] **Step 3: 实现（chapter_loop.py）**

```python
# _revalidate_revised_chapter 内，backup 读取块 :1437-1443 之后追加：
    # spec #83 T2: 物象/POST 声明引句并入复验谓词（升格既有 #72 R3-C1 复验面）——
    # 相对口径（r5 定稿）：entity_in_text(修订前) ∧ ¬(修订后) → FAIL；绝对在场口径
    # 在全语料证伪（28 例/14 章零删改即红）。两侧同口径 strip_narrative_body。
    _plan_pr = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    if _plan_pr.is_file():
        issues.extend(
            check_prop_purge_on_revision(
                backup.read_text(encoding="utf-8") if backup.is_file() else text,
                text,
                _plan_pr.read_text(encoding="utf-8"),
                chapter=chapter,
            )
        )
```

新函数（chapter_loop.py 模块级，`_revalidate_revised_chapter` 前）：

```python
_PROP_HOLD_RE = re.compile(r"^\s*[-*]\s*(\S+?)@hold\s*[：:]\s*\S+", re.M)
_PROP_COLON_RE = re.compile(r"^\s*[-*]\s*物象\s*[：:]\s*([^|｜]+)[|｜]\s*\S+", re.M)

def parse_prop_lines(plan_text: str) -> list[str]:
    """入场行＝@hold＋物象: X|Y 结构化行（r4 用户裁定；r5 清点 44 行）。
    @lose/@mention/@none 与 PRE 散文物象行不入场（丢失/纯提及不在场是预期态）。
    去重保序（审查轮 2 M9：ch28 同一实体双声明形——@hold 与物象: 并存——
    不去重则删尽时双发同一 FAIL）。"""
    seen: dict[str, None] = {}
    for m in (*_PROP_HOLD_RE.finditer(plan_text), *_PROP_COLON_RE.finditer(plan_text)):
        seen.setdefault(m.group(1).strip(), None)
    return list(seen)

def check_prop_purge_on_revision(
    before_text: str, after_text: str, plan_text: str, *, chapter: int
) -> list[str]:
    from shenbi.gates.g4.chapter_drafting import entity_in_text
    from shenbi.gates.shared import strip_narrative_body
    before = strip_narrative_body(before_text)
    after = strip_narrative_body(after_text)
    issues: list[str] = []
    for name in parse_prop_lines(plan_text):
        if entity_in_text(name, before) and not entity_in_text(name, after):
            issues.append(
                f"G4.rev.prop_purged:chapters/chapter-{chapter}.md:『{name}』修订前在场、修订后被删尽"
                "——物象删除须有 @lose/事件声明，不许静默蒸发（修复者: revision 补回或补声明）"
            )
    return issues
```

POST 引句复验（spec：POST 引句走 T1 判定器执法两行）：`_revalidate_revised_chapter` 内追加对修订后 text 跑 `check_post_quote_verbatim(text)` 的 fails——**审查轮 1 I5b：判定器返回串自带 `cd.post_quote_verbatim:` 前缀而无 `G4.`，消费点按 `startswith("G4.")` 分流会漏 demote**——追加处显式加前缀：

```python
    from shenbi.gates.g4.post_declarations import check_post_quote_verbatim as _cpq
    issues.extend(f"G4.{f}" for f in _cpq(text)[0])  # 判定器串无 G4. 前缀，此处补齐进 id 分流
```

消费点接线 :4487-4493（r5.3 §10 强制项——行 3 支路）：

```python
        rev_issues = _revalidate_revised_chapter(project_dir, chapter)
        if rev_issues:
            # spec #83 §10 行 3：id-first 项过 shadow demote（rev_issues 混合既有无 id 串——
            # 只对 G4. 前缀项 demote，其余保持既有路由）
            _id_items = [i for i in rev_issues if i.startswith("G4.")]
            _plain = [i for i in rev_issues if not i.startswith("G4.")]
            _demoted, _hard = demote_must_fix(project_dir, _id_items)
            for _dw in _demoted:
                log.warning("shadow_gate_demoted", chapter=chapter, skill=step.skill, item=_dw)
                emit_shadow_warn_trace(project_dir, chapter, _dw)
            if _plain or _hard:  # 轮 3 M7：all-demoted 不得写空反馈头——shadow 契约要求
                # 复刻 retry_feedback 清理（PASS-with-warnings），非注入 vacuous 模板
                state.chapter_loop.retry_feedback[retry_key] = _enrich_g4_feedback(
                    [f"修订重验: {i}" for i in (_plain + _hard)]
                )
                return _handle_failure(state, step, chapter, "g4", project_dir)
            else:
                state.chapter_loop.retry_feedback.pop(retry_key, None)  # 全 demoted → 清理旧反馈
```

（全部 demoted 且无 plain → 不走 failure——PASS-with-warnings，对齐 shadow.py 路由契约。）shadow.py 登记 `"rev.prop_purged": ("market_params", "prop_purge_guard")`。

- [ ] **Step 4: 确认绿 + 集成**

Run: `uv run pytest tests/unit/pipeline/test_spec83_rev_prop_purged.py tests/unit/pipeline/test_chapter_loop.py -q`
Expected: PASS（既有修订复验测试零回归）
集成（T2 束链）：`tests/integration/` 已有束链路径补一例「修订删物象 → 复验 FAIL → 反馈定向」——本 task 先落单测，集成面在 Task 5 完成状态链后一并补（见 Task 5 Step 4）。

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/gates/g4/shadow.py tests/unit/pipeline/test_spec83_rev_prop_purged.py
git commit -m "feat: rev.prop_purged revision revalidation extension (spec #83 T2, shadow wiring at consumption site)"
```

---

### Task 5: `declarations_stale` 状态链＋`ss.stale_declarations` settle 派发前执法（spec T2 次级）

**Files:**
- Modify: `src/shenbi/pipeline/state.py:143-154`（ChapterState 字段）、`:323-334`（to_dict）、`:386-396`（from_dict）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（写入者 :4482 修订完成分支；清除点两处摄取步 :2022＋:2371＋复验绿复同步处；执法点＝**settle 真实派发路径三站点**（审查轮 3 C1 定稿）：①`run_parallel_post_draft_steps`（:3450，settling 派发 :3480-3498）②③见 Step 3——**正常 per-chapter settle 不走 run_chapter_step 通用路径**（:3954 `_FORESHADOWING_LIFECYCLE_IDX` 分支拦截进并行块），修订后重派 settle 走 **cli.py `_execute_pending_re_dispatches`（:260，:479 消费）**，STATE_SETTLE checkpoint REJECT/MODIFY redo（cli.py:1082-1090/:1296-1308 重置 step_index）落串行通用派发 :4253）
- Modify: `src/shenbi/pipeline/cli.py`（执法点第二处：`_execute_pending_re_dispatches` :260 内派发 `shenbi-state-settling` entry 前过同一 stale 检查 helper——**修订后重派 settle 是 stale 门的主战场**（:4505 排队、PASS-with-warnings 流程下 stale 保持 True）；cli.py:247 已有第 4 个 `_shadow_route_g4` 消费点先例）
- Modify: `src/shenbi/gates/g4/shadow.py`（行 4 登记）
- Test: `tests/unit/pipeline/test_spec83_stale_declarations.py`（含机械穷尽性 grep 测试）、`tests/integration/test_spec83_stale_chain.py`（**三路径都驱动**：①并行块 settle 派发前拒收 ②修订→pending 队列→cli `_execute_pending_re_dispatches` 重派拒收（PASS-with-warnings leg——真实可达主战场）③STATE_SETTLE checkpoint REJECT redo→串行通用路径拒收；快乐链（置位→复验 FAIL→补回→绿→清除→不再拒收）作 characterization）

**Interfaces:**
- Consumes: `ChapterState`（state.py:143 dataclass）、`ChapterStatus`（state.py:102——**不动**：declarations_stale 是 bool 字段非枚举值，一章可 complete 且 stale）、`retry_key(chapter, skill) -> str`（state.py:157）
- Produces: `ChapterState.declarations_stale: bool = False`；shadow 键 `("market_params", "stale_declarations")`；finding id `ss.stale_declarations`
- 落点纪律（§11）：字段唯一落点 ChapterState；序列化 to_dict/from_dict **两处显式清单同步改**（r5.3 注：漏改则不持久化）

**复杂度: infra**（state 序列化+状态机+派发执法）· **test_kind: tdd_red_green + characterization**（既有序列化面不回退）· **测试层级: T1 + T2** · fixtures: 无需新 fixture（tmp_path 构造 PipelineState 单元）

**执法可达窗口（审查轮 1 I7a 释明，实现照此设计）**：复验绿即清除（同块 :4482→:4487）意味着**快乐路径上 settle 派发前检查看不到 stale=True**——这是设计内语义而非缺陷：`ss.stale_declarations` 是**兜底门**（spec §2「覆盖复验谓词漏网形态」），可见窗口=①复验 FAIL 后的升级/续跑路径（stale 保持 True 直到下次修订复验转绿或人工介入）②**PASS-with-warnings 流程**（修订后复验面全 demoted → 不走 failure → :4505 排队重派 settle 而 stale 未经绿复验清除——站点②主战场）③STATE_SETTLE checkpoint 人审 REJECT/MODIFY redo（摄取未完成、stale 跨检查点存续——站点③）④崩溃恢复（stale=True 落盘后 crash）。快乐路径清除是 spec §11 双清除点明文（防「拒收→摄取永不发生→清除不可达」死锁），本 plan 照钉。

- [ ] **Step 1: 写红测**

```python
# tests/unit/pipeline/test_spec83_stale_declarations.py
def test_stale_field_persists_roundtrip(tmp_path):
    st = PipelineState(project_dir=str(tmp_path))
    st.chapter_loop.chapter_states["26"] = ChapterState(status=ChapterStatus.COMPLETE, declarations_stale=True)
    rt = PipelineState.from_json(st.to_json())
    assert rt.chapter_loop.chapter_states["26"].declarations_stale is True  # 现基线 AttributeError → 红

def test_stale_set_on_revision_clear_on_green(tmp_path):
    # 置位：修订完成（:4482 块内联写入，非独立 helper——审查轮 1 M13：测试经真实代码路径
    # run_chapter_step 修订分支或直接构造后调内联语义）；清除点 1：复验谓词全绿复同步处
    ...  # mini project（tmp_path: plans/ + chapters/ 真实 fixture 拷贝）驱动修订成功路径
    ...  # 断言置位 stale=True → 复验绿后 stale=False（快乐路径清除）

def test_settle_rejects_stale(tmp_path):
    # 执法点：state-settling 派发前 stale=True → must_fix ss.stale_declarations（shadow demote 后 WARN 继续）
    ...
```

- [ ] **Step 2: 确认红** — Run: `uv run pytest tests/unit/pipeline/test_spec83_stale_declarations.py -v` Expected: FAIL

- [ ] **Step 3: 实现**

state.py 三处：

```python
# ChapterState 字段（:154 declared 之后追加）
    # spec #83 T2: 修订完成→true；清除点两处（§11：settle 摄取成功后＋复验绿复同步处）。
    # 非 ChapterStatus 枚举值——章生命周期与声明新鲜度正交（可 complete 且 stale）。
    declarations_stale: bool = False
# to_dict :331 "declared": v.declared, 之后追加
                        "declarations_stale": v.declarations_stale,
# from_dict :395 declared=v.get("declared", {}), 之后追加
                declarations_stale=bool(v.get("declarations_stale", False)),
```

chapter_loop.py：
1. 写入者（:4482 `if "chapter-revision" in step.skill:` 块首，内联）：`_get_chapter_state(state, chapter).declarations_stale = True`（修订完成——无条件置位）
2. 清除点 1（复验绿复同步处——:4487 `rev_issues` 为空分支内）：`cs.declarations_stale = False`
3. 清除点 2（settle 摄取步成功后——**两个摄取点全覆盖**（审查轮 1 I7c）：:2022 `apply_settle_facts_ops` 并行/重派路径 **＋ :2371 串行 settle 自动提交路径**，两处成功返回后对该 chapter 清除）：`_get_chapter_state(state, chapter).declarations_stale = False`
4. 执法点（settle 派发前检查——**审查轮 3 C1 定稿：集中式 guard＋三站点接线＋机械穷尽性测试**）：

```python
def _pre_settle_guard(
    state: PipelineState, project_dir: Path | str, chapter: int
) -> tuple[list[str], list[str]]:
    """spec #83 §10 行 4 纯谓词：stale 拒收。返回 (demoted_warn_texts, hard_items)，
    路由归调用站点（并行块/串行/.cli 队列三站点各自镜像既有失败路由先例）。"""
    if not _get_chapter_state(state, chapter).declarations_stale:
        return [], []
    items = [f"G4.ss.stale_declarations:chapters/chapter-{chapter}.md:"
             "修订后声明面未同步（declarations_stale）——先重跑 hook_match/补声明同步再 settle"]
    demoted, hard = demote_must_fix(Path(project_dir), items)
    for dw in demoted:  # 轮 4 N5：对齐 _shadow_route_g4 :2081-2082 双通道（log + trace）
        log.warning("shadow_gate_demoted", chapter=chapter, skill="shenbi-state-settling", item=dw)
        emit_shadow_warn_trace(project_dir, chapter, dw)
    return demoted, hard
```

**三接线站点**（审查轮 2 C1＋轮 3 C1 合并定稿——settle 派发共三条真实路径）：
- **站点 ① 并行块**：`run_parallel_post_draft_steps`（:3450）内 settling_step 派发（:3480-3498）前调 `_pre_settle_guard(state, project_dir, chapter)`——作用域内是 `settling_step` 非 `step`、键用 `_retry_key(chapter, settling_step.skill)`（:3970/:4022 先例）；hard 路由（**轮 4 N6 钉＋轮 5 M4**）：合成失败的 settling DispatchResult（returncode≠0 **且 stderr 载 guard 报文**——调用侧 :3961-3978 的 feedback 写入以 `getattr(settling_result, "stderr", "")` 为闸，空 stderr 则定向反馈到不了重派模型）＋retry_feedback 写 `_retry_key(chapter, settling_step.skill)`——由调用侧 :3961-3978 既有失败分支自然路由（**审查轮 3 I2：不得裸 `return _handle_failure(...)` 布尔值破坏 `tuple[Any, Any]` 契约与 :3958 解包**；同函数 :3515-3519 settle 失败即此形态先例）
- **站点 ② cli 队列**：`cli.py _execute_pending_re_dispatches`（:260）派发 settle entry（:328 dispatch_skill）前——hard 路由镜像同函数 **G4 失败 entry 分支（:331-350）**：entry 写 feedback＋保持排队重试
- **站点 ③ 串行通用路径**：`_run_chapter_step_impl`（:3633，**轮 5 I2 勘误**：`run_chapter_step` :3600 为计时 wrapper）通用串行派发（:4253 dispatch 前、`step.skill == "shenbi-state-settling"` 时）——**审查轮 3 C1 新发现第三路径**：STATE_SETTLE checkpoint 人审 REJECT/MODIFY（cli.py:1082-1090/:1296-1308）直接把 `step_index` 重置到 settling 步 → :3954 拦截不触发（step_idx ≠ LIFECYCLE_IDX）→ 落通用串行派发；hard 路由 `_handle_failure(state, step, chapter, "g4", project_dir)`（该路径既有语义）
- **机械穷尽性测试（根治此类「穷尽性声明被证伪」循环——轮 2 C1/轮 3 C1 同类；轮 4 N3 钉机制）**：**勿按 `grep "shenbi-state-settling"` 提取站点**（skill 经变量传递——三站点函数体内无该字面量，~30 处引用多为非派发面，字面量 grep 命中 0/3 站点）；改按 **`dispatch_skill(` 调用点枚举**（**轮 6 I1 勘误：实为 13 个调用点/14 行原始 grep 命中——含 dispatch_helper.py:4234 的 def 行，解析器须滤除**）：characterization 测试解析 `grep -rn "dispatch_skill(" src/shenbi/` 全调用点 → 对 **钉死的 (file, function) 分类 allowlist** 逐点断言（settle-capable 站点＝chapter_loop.run_parallel_post_draft_steps / cli._execute_pending_re_dispatches / **chapter_loop._run_chapter_step_impl**〔**轮 5 I2 勘误**：:4253 派发点在 `_run_chapter_step_impl`（:3633）内——`run_chapter_step`（:3600）是计时 wrapper（:3621 委托），按行→外层函数映射永远落 impl，allowlist 写 wrapper 名则测试落地即红〕三对；**断言粒度=外层函数级**（run_parallel_post_draft_steps 含 lifecycle+settling 两个派发点、仅 settling 侧过 guard——函数级「上下文含 `_pre_settle_guard`」判定即可）；非 settle 站点**预分类清单（轮 6 I1）**=triggers.py:625（TRIGGER_STEPS 固定表无 settle）/parallel_dispatch.py:125（审计波）/audit_layer.py:237/genesis.py:610/closure.py:300（CLOSURE_STEPS）/revision_router.py:326/chapter_loop.py:432（re-audit revision）/:2528（_check_conditional_resolve）/cli.py:1576（卷界快照）——9 点 rest）；**任何新增调用点不在 allowlist → 红测报「classify before wiring」**——未来新派发面强制分类过 guard

shadow.py 登记 `"ss.stale_declarations": ("market_params", "stale_declarations")`。

- [ ] **Step 4: 集成测试（T2 束链）**

```python
# tests/integration/test_spec83_stale_chain.py：修订改文 → stale 置位 → 复验 FAIL（Task 4 谓词）
# → 反馈定向 → 修订补回 → 复验绿 → stale 清除 → settle 派发不再拒收。
```
（以 mini project 驱动 `run_chapter_step` 修订分支路径，fixtures=spec28 章+计划拷贝；不触发真实 dispatch——直接调 `_revalidate_revised_chapter` 与置位/清除回调。）

- [ ] **Step 5: 运行确认绿**

Run: `uv run pytest tests/unit/pipeline/test_spec83_stale_declarations.py tests/integration/test_spec83_stale_chain.py tests/unit/pipeline/test_state_heal.py tests/unit/pipeline/test_chapter_loop.py -q`
Expected: PASS（含既有 state 序列化/回愈面零回归）

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/state.py src/shenbi/pipeline/chapter_loop.py src/shenbi/gates/g4/shadow.py tests/unit/pipeline/test_spec83_stale_declarations.py tests/integration/test_spec83_stale_chain.py
git commit -m "feat: declarations_stale state chain + ss.stale_declarations settle gate (spec #83 T2)"
```

---

### Task 6: `streak_monitor_rewinds` 打摆计数器＋定点扩写切换（spec T4）

**Files:**
- Modify: `src/shenbi/pipeline/state.py:204-221`（ChapterLoopStateData 字段+序列化 to_dict/from_dict）
- Modify: `src/shenbi/pipeline/chapter_loop.py:4161-4175`（monitor_rewind 增点）、`:4384-4393`（g4_hard 增点）、`:2162-2176`（_complete_chapter bundle 循环=复位点）、`_append_feedback_injections`（:1153-1228 切换消费）
- Test: `tests/unit/pipeline/test_spec83_streak_switch.py`

**Interfaces:**
- Consumes: `retry_key(chapter, skill)`（state.py:157，键型 `ch{N}-{skill}`）；`retry_budget_consumed` 持久化纪律（state.py:211-214 不被 `_reset_retries` 清除——streak 同款纪律；**禁用 retry_counts**：:4170-4175 注释实证「成功重派即清零、rewind loop 会永远打转」）
- Produces: `ChapterLoopStateData.streak_monitor_rewinds: dict[str, int]`（per retry_key）；切换阈值常量 `_STREAK_TARGETED_MODE_THRESHOLD = 4`；复位=**仅章推进**（升级/熔断/成功重派均不复位——跨熔断持久连击正是打摆病理本体，ch25 两轮熔断间 14 连实证）

**复杂度: infra** · **test_kind: tdd_red_green + characterization**（_complete_chapter 既有面）· **测试层级: T1** · fixtures: 无新 fixture（trace 回放断言可用 r5 探针数值做注释基线；单测构造 state）

- [ ] **Step 1: 写红测（口径a 全属性）**

```python
# tests/unit/pipeline/test_spec83_streak_switch.py
"""spec #83 T4: 打摆计数口径a（r5 回放定稿）——同 key 连击不分族（monitor_rewind 与
g4_hard 同计）；DISPATCH 交织不断链；loop_id 不作计数器；planning key 计数但不触发
切换；复位=仅章推进。回放基线：ch25×14/ch31×5/ch27/29/33/35×4 全 ≥4 触发零假触发。"""

def test_streak_counts_retries_and_dispatch_does_not_break():
    # 口径a 不分族：_record_retry(state, chapter, skill) 无 kind 参数（monitor_rewind/g4_hard
    # 两站点同 helper）；RETRY→DISPATCH→RETRY 是重派循环本体（ch25 seq 505-546 流形）——
    # DISPATCH 不清零（计数器只由 _record_retry 增、_complete_chapter 章推进清）
    st = PipelineState()
    rk = retry_key(25, "shenbi-chapter-drafting")
    _record_retry(st, 25, "shenbi-chapter-drafting")  # 新 helper（Step 3 定义）
    _record_retry(st, 25, "shenbi-chapter-drafting")
    assert st.chapter_loop.streak_monitor_rewinds[rk] == 2  # 现基线 AttributeError → 红

def test_switch_fires_at_4_with_loop_id_reset_midway():
    # ch25 型：loop_id 序列 [1,2,3,4,1,...] 中途重置仍切换（loop_id 不可作计数器）
    ...

def test_reset_only_on_chapter_advance():
    # 成功重派不复位（对齐 retry_budget_consumed 纪律）；_complete_chapter(bundle) 推进后复位
    ...

def test_planning_key_counts_but_never_switches():
    # planning key 计数存在；切换消费面只读 drafting key
    ...
```

- [ ] **Step 2: 确认红** — Run: `uv run pytest tests/unit/pipeline/test_spec83_streak_switch.py -v` Expected: FAIL

- [ ] **Step 3: 实现**

state.py：`ChapterLoopStateData` 增 `streak_monitor_rewinds: dict[str, int] = field(default_factory=dict)` ＋ to_dict（:337 retry_budget_consumed 行后）`"streak_monitor_rewinds": ...` ＋ from_dict 对应读取。**不进 `_reset_retries` 清除面**。

chapter_loop.py：
1. 模块级 helper：

```python
_STREAK_TARGETED_MODE_THRESHOLD = 4  # 卷一战术「打摆>5 轮切手工」代码化，4 留自动裕量（spec T4）

def _record_retry(state: PipelineState, chapter: int, skill: str) -> None:
    """spec #83 T4 口径a：每条 RETRY（reason.kind 不分族）连击 +1。
    断链锚定=章循环状态机（r5.1：trace 无终态 action）——复位仅章推进，
    升级/熔断/成功重派均不复位（retry_counts :4170-4175 陷阱——禁用）。"""
    rk = _retry_key(chapter, skill)
    state.chapter_loop.streak_monitor_rewinds[rk] = (
        state.chapter_loop.streak_monitor_rewinds.get(rk, 0) + 1
    )
```

2. 两增点：monitor_rewind 站点（:4164 `_emit_retry_event` 前）与 g4_hard 站点（:4384 `_emit_retry_event` 前）各插 `_record_retry(state, chapter, step.skill)`（monitor_rewind 站点 skill=`drafting_step.skill`）。
3. 复位点（`_complete_chapter` :2174 F368 清扫块旁）：

```python
    # spec #83 T4：打摆连击复位=仅章推进（bundle 全员各自复位；升级/熔断/成功重派不复位）
    for member in bundle_chapters(project_dir, chapter):
        for k in [k for k in state.chapter_loop.streak_monitor_rewinds if k.startswith(f"ch{member}-")]:
            state.chapter_loop.streak_monitor_rewinds.pop(k, None)
```

4. 切换消费（`_append_feedback_injections` :1183 prev_g4_feedback 块内、_length_family 注入前）：

```python
        # spec #83 T4：打摆切换——同 key 连击 ≥4 → 反馈模板切「定点扩写」模式，
        # 不再发整档约束重述（ch25 型混合族连续全档重写病理）
        _streak = state.chapter_loop.streak_monitor_rewinds.get(_retry_key(chapter, skill), 0)
        if skill == "shenbi-chapter-drafting" and _streak >= _STREAK_TARGETED_MODE_THRESHOLD:
            prompt += (
                f"\n\n## TARGETED-EDIT MODE（连击 {_streak} 次打摆切换）\n"
                "前稿逐字保留，**只在反馈点名的问题处做定点修改/扩写**：\n"
                "- 每条失败项给段落锚（场景号/首句引用），只改该段；\n"
                "- 字数缺口按反馈实测值补足，不重掷全章；\n"
                "- 未被点名的段落 token 级不变。禁止整章重写、禁止场景重组。\n"
            )
```

- [ ] **Step 4: 确认绿 + observe 回放注释**

Run: `uv run pytest tests/unit/pipeline/test_spec83_streak_switch.py tests/unit/pipeline/test_chapter_loop.py tests/unit/pipeline/test_snapshot_declared.py -q`
Expected: PASS（_complete_chapter 既有面零回归）
Run: `uv run python tools/observe_report.py novel-xinghuo-vol1 2>/dev/null | head -5`
Expected: 现有 loop depth 表仍可跑（观测面不动——trace `seq` 聚合仅观测/测试回放面）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/state.py src/shenbi/pipeline/chapter_loop.py tests/unit/pipeline/test_spec83_streak_switch.py
git commit -m "feat: streak_monitor_rewinds durable counter + targeted-edit mode switch (spec #83 T4, reset on chapter advance only)"
```

---

### Task 7: RETRY 分族路由反馈定向＋diff 面积 WARN（spec T4 路由面）

**Files:**
- Create: `src/shenbi/pipeline/retry_routing.py`（分族器：纯函数）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（`_append_feedback_injections` 路由注入——分族从 retry_feedback 文本前缀反查；RETRY reason 载荷仅 trace/observe 观测面不持久化，**不进路由**〔审查轮 1 M12 单述定稿：spec r3「不从反馈文本判读」禁的是打摆**触发判定**（已由 T6 计数器承载），路由定向读的是反馈文本内**已结构化的 issue 前缀串**（monitor_rewind issues 原样进 retry_feedback），非自由文本判读——两纪律不相悖〕）
- Modify: `src/shenbi/gates/g4/state_settling.py:247-287`（`_check_matrix_structure` 返回形态扩 `tuple[list[str], list[str]]`＝(fails, warns)——**审查轮 1 M11：现返回 `list[str]` 直灌 :986 mf 无 WARN 通道**；diff 面积 >50% 进 warns；调用点 :986 同步拆包，warns → c.append WARN 观测行）
- Modify: `skills/shenbi-state-settling/SKILL.md:94-103`（铁律 0 段附一行指路「定点编辑反馈见 incremental 通道」——**审查轮 1 M18：spec §4 明文子项，此前无 task 承载**；prose 指引行不触契约三源面）
- Test: `tests/unit/pipeline/test_spec83_retry_routing.py`

**Interfaces:**
- Consumes: retry_feedback 文本内 issue 前缀（monitor_rewind `reason.issues` 前缀 7 族回放数值：scene_domain×61/word_band×19/chapter_band×19/G4.cd×31〔前缀含章号 token〕/composition×9/CH×4/XC×4；g4_hard `reason.check_ids` 兜底剥可选 `G4.` 前缀归一——`cp.prop_decl:…` 实例）；`_length_family` 既有注入（chapter_loop.py:1198-1214）
- Produces:
  - `classify_retry_family(feedback_text: str) -> str` → `"length" | "structure" | "content" | "other"`（长度族=word_band/chapter_band/G4.word_count；结构族=scene_domain/composition/CH；内容族=G4.cd/XC——**输入为反馈文本**，按前缀 token 匹配；**混合串优先级 length > structure > content**〔轮 5 M5 入 Interfaces——最重约束先路由，ch25 全混族主形态〕）
  - `targeted_feedback_addendum(family: str, prev_feedback: str) -> str`（各族定向指令块）
  - 分族表**重定位为反馈路由面**（非门控面——「长度/结构族才计入」门控在全语料证伪）

**复杂度: infra** · **test_kind: tdd_red_green** · **测试层级: T1** · fixtures: 无新（分族单测内联 147 条全表抽样实例——结构输入豁免面；`cp.prop_decl` 无前缀归一实例）

- [ ] **Step 1: 写红测**

```python
def test_family_classification_seven_prefixes():
    # 输入=retry_feedback 文本（monitor_rewind issues 原样进反馈；前缀即结构化 token）
    assert classify_retry_family("- word_band: ch25 短 380\n- G4.word_count: 差 500") == "length"
    assert classify_retry_family("- G4.cd ch25:quote 缺锚") == "content"
    assert classify_retry_family("- scene_domain: 4场景\n- composition: 拆") == "structure"
    assert classify_retry_family("- XC: 单位词根\n- CH:12 缺段") == "structure"  # 轮 4 N4 勘误：混合串按 Interfaces 钉死优先级 length>structure>content 归 structure（最重约束先路由——ch25 全混族主形态）

def test_g4_hard_check_id_prefix_normalization():
    # g4_hard 兜底：剥可选 G4. 前缀归一（r5 实测 1 条 cp.prop_decl 无前缀）——check_ids 进反馈文本后同前缀通道
    assert classify_retry_family("- cp.prop_decl:staging/plans/x.md") == "other"  # planning 族→other（drafting 切换面不读）
    assert classify_retry_family("- G4.cd.post_quote_verbatim:x") == "content"

def test_routing_addendum_shapes():
    assert "扩写" in targeted_feedback_addendum("length", "...")       # → _length_family 定向同款
    assert "场景结构" in targeted_feedback_addendum("structure", "...")
    assert "引句/数字锚" in targeted_feedback_addendum("content", "...")

def test_matrix_structure_warn_channel():
    # 审查轮 1 M11：_check_matrix_structure 返回 (fails, warns)——diff 面积 >50% 走 warns（观测非 FAIL）
    fails, warns = _check_matrix_structure(Path("matrix 重写 >50% 的夹具"))
    assert not fails and warns  # 重写型走 WARN 量化面
```

- [ ] **Step 2: 确认红** → **Step 3: 实现 retry_routing.py + 接线**

分族器（纯函数，输入=反馈文本，前缀 token 匹配；前缀表注释内附 147 条全表回放数值——审计锚）；`_append_feedback_injections` 在 TARGETED-EDIT 块后按 `classify_retry_family(prev_g4_feedback)` 注入 `targeted_feedback_addendum` 定向块；`_check_matrix_structure` 返回形态扩 `tuple[list[str], list[str]]`，content_dropped 分支计算 diff 面积比 >50% 进 warns（调用点 :986 拆包，warns → c.append WARN——shadow 量化面，观测记录不 FAIL）；SKILL.md 铁律 0 段尾附指路行。

- [ ] **Step 4: 确认绿**

Run: `uv run pytest tests/unit/pipeline/test_spec83_retry_routing.py tests/unit/gates/g4 -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/retry_routing.py src/shenbi/pipeline/chapter_loop.py src/shenbi/gates/g4/state_settling.py skills/shenbi-state-settling/SKILL.md tests/unit/pipeline/test_spec83_retry_routing.py
git commit -m "feat: retry family routing feedback + matrix diff-area WARN + iron-law-0 pointer (spec #83 T4)"
```

---

### Task 8: follower 完成语义＋指标面补全（spec T5）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:2162-2169`（`_complete_chapter` bundle 循环补 status）
- Modify: `tools/report_longitudinal.py:200-237`（`chapter_verdicts` bundle_merged 读取侧）、`:427-433`（per_chapter 生成侧）、新增 `--emit-ledger-rows N M`
- Test: `tests/unit/pipeline/test_spec83_follower_completion.py`、`tests/unit/tools/test_spec83_longitudinal.py`

**Interfaces:**
- Consumes: `bundle_chapters(project_dir, chapter)`（既有）；`#82 T0 declared 快照循环`（:2162-2169 注释明示 "#83 T5 routes its batch status write through the same per-chapter function"——接口已预留）
- Produces: bundle 循环内 `mcs.status = ChapterStatus.COMPLETE`（修 18/18 假 pending）；longitudinal per_chapter 行新 `bundle_merged: bool` 字段（生成侧：follower 判定=该章 ∈ 某 leader bundle 的非首成员；resonance 取束级值=leader 行值）＋读取侧 fail-closed（`bundle_merged=True` 行跳过单章 resonance 断言，束级断言替代：束内两章 resonance 均值 ≥ floor）；`--emit-ledger-rows N M` 从 trace/cost 生成台账缺行草稿（stdout，工具只报不写）

**复杂度: infra** · **test_kind: tdd_red_green + characterization** · **测试层级: T1** · fixtures: spec33 truth/facts + mini project（tmp_path 双章束）；台账行格式锚=vol1-ledger.md 纵向采集表 11 列（`| 章 | 实测字数 | 超发率 | cost | 一次过/retry | 新闸拦截 | emotion_tone | payoff 拍 | 章尾钩型 | resonance | 三 WARN |`——gitignored 运行工件，格式以注释锚定）

- [ ] **Step 1: 写红测**

```python
def test_bundle_completion_writes_all_member_status(tmp_path):
    # 双章束（ch2 leader, ch3 follower 惯例由 bundle_chapters 读 project 配置）——
    # mini project 构造后调 _complete_chapter(state, 2)：两章 status 均 complete（现基线 follower 恒 pending → 红）
    ...

def test_bundle_merged_field_and_bundle_level_assertion():
    # 生成侧：follower 行 bundle_merged=True + resonance=束级值；读取侧：单章断言跳过、束级断言替代
    ...

def test_emit_ledger_rows_shape(capsys):
    # --emit-ledger-rows 5 10：从 trace/cost 产出 ch5-10 草稿行（11 列头+可推导列，不可推导列=「待补」）
    ...
```

- [ ] **Step 2: 确认红** → **Step 3: 实现**

`_complete_chapter` bundle 循环改（:2165-2169）：

```python
    for member in bundle_chapters(project_dir, chapter):
        mkey = str(member)
        mcs = state.chapter_loop.chapter_states.setdefault(mkey, ChapterState())
        if not mcs.declared:
            mcs.declared = _snapshot_declared(project_dir, member)
        # spec #83 T5: batch status write（#82 T0 预留接口）——修 18/18 假 pending；
        # status 写点原本仅 leader 一处（:2160），游标 :2195 跳过 follower
        mcs.status = ChapterStatus.COMPLETE
```

report_longitudinal.py：`chapter_verdicts` 增 `bundle_merged` 参数面（verdict dataclass 增字段）；生成侧 `_is_bundle_follower(project_dir, ch)`（`bundle_chapters` 反查）填字段、resonance 取 leader 行值；fail-closed 分支：`if verdict.bundle_merged: 跳过 resonance-missing 理由；束级断言在 quality_conditions 聚合处成对校验`。`--emit-ledger-rows`：读 trace.jsonl RETRY/DISPATCH 计数与 cost 报告产出行草稿。

- [ ] **Step 4: 确认绿**

Run: `uv run pytest tests/unit/pipeline/test_spec83_follower_completion.py tests/unit/tools/test_spec83_longitudinal.py tests/unit/pipeline/test_chapter_loop.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tools/report_longitudinal.py tests/unit/pipeline/test_spec83_follower_completion.py tests/unit/tools/test_spec83_longitudinal.py
git commit -m "feat: bundle follower completion semantics + bundle_merged longitudinal face + ledger row drafts (spec #83 T5)"
```

---

### Task 9: 计数锚扩族——N+M 解析＋三 FAIL 支路＋锚词注册＋id-first（spec T6 计数）

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:166`（`_COUNTER_DECL_RE`）、`:182-194`（`parse_counter_declarations` 签名扩）、`:197-259`（`check_counter_reconciliation` 三支路重写）、`:218-220`（`_WORD_FAMILY` 扩锚词注册）、`:627-628`（发射 id-first）
- Modify: `src/shenbi/gates/g4/shadow.py`（行 5/6/7 登记）
- Test: `tests/unit/gates/g4/test_spec83_counter_anchor.py`、扩展 `tests/unit/gates/g4/test_f17_counters.py`

**Interfaces:**
- Consumes: `cn_amount`（cross_chapter 既有中文数字化）、`load_facts(FactsDim.COUNTERS)`（:536-538 check 时点现值接线——③口径的时序语义：drafting 时=增量落地前现值）、`_SENTENCE_SPLIT_RE`（:91，[。！？；]）
- Produces:
  - `parse_counter_declarations(memo_text: str) -> list[tuple[str, int, int]]`（**(name, base, delta)** 三元——签名变更，调用方 :222/:610 + test_f17_counters 同步）
  - `check_counter_reconciliation(text: str, memo_text: str, counters: dict, *, fp: str = "") -> list[str]`（**fp keyword-only 带默认**——审查轮 1 M15：三位置参调用不破，生产调用点 :627 传 `fp=fp` 进 detail；issue 串自带 `cd.counter.<sub>:` 前缀）
  - `_COUNTER_DECL_RE = re.compile(r"^[-*]\s*计数[：:]\s*(\S+)\s+(\d+)\s*\+\s*(\d+)\s*$", re.M)`（N+M 全形态含空格变体；r5 回放：全语料 9 条声明现仅捕 2 条）
  - `_WORD_FAMILY`（函数内局部 dict :218-220——阶段 2 注记：扩族改局部 dict）重构为 `_ANCHORED_COUNTERS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]]`＝`{counter: (词族, 锚词集)}`，`鉴录名数: (("名字",), ("《鉴录》", "鉴录"))`
  - 三支路 issue id：`cd.counter.plan_conflict`（②同 counter 多声明 finals 互斥）/`cd.counter.base_mismatch`（③每条声明 base ≠ facts 现值）/`cd.counter.prose_mismatch`（④同句锚定总数/序数 ∉ 允许集）；**旧判据 (2) `declared_val != facts_val + 1` 删除**（r5 证伪：+0 六章全误红——由③替代）
  - shadow 键：三支路共用 `("market_params", "counter_anchor")`（#82 hook 族多 id 一键先例）

**复杂度: infra** · **test_kind: tdd_red_green + characterization**（F17 既有正例不回退：+1 单声明绿路径、序数判定保留）· **测试层级: T1** · fixtures: spec83/plans/chapter-28-plan.md（双声明红）、truth/facts/counters.json（facts=4 终态）、ch30（锚定负例）、ch25/26/27/29/30/36 +0 六章绿（chapters 包内含 25/26/28/30——27/29/36 的 plan 声明行以 fixtures 内联引用真实拷贝段落）

- [ ] **Step 1: 写红测**

```python
def test_plan_conflict_ch28_dual_declaration():
    # ch28 :88 4+0（final 4）vs :100 4 +1（final 5）→ finals {4,5} 互斥稳红（r4/r5 双轮回放）
    plan = (FIX / "plans" / "chapter-28-plan.md").read_text(encoding="utf-8")
    text = (FIX / "chapters" / "chapter-28.md").read_text(encoding="utf-8")
    issues = check_counter_reconciliation(text, plan, {"鉴录名数": {"value": 4}})
    assert any("plan_conflict" in i for i in issues)

def test_base_mismatch_and_plus_zero_green():
    # +0 六章 base4==facts4 全绿（r5 回放）；base≠facts 红
    plan = "- 计数: 鉴录名数 5+0\n"
    issues = check_counter_reconciliation("正文", plan, {"鉴录名数": {"value": 4}})
    assert any("base_mismatch" in i for i in issues)
    issues0 = check_counter_reconciliation("正文", "- 计数: 鉴录名数 4+0\n", {"鉴录名数": {"value": 4}})
    assert not any("base_mismatch" in i for i in issues0)

def test_ch9_temporal_green_with_constructed_facts():
    # r5.1：ch9 3+1 在 check 时点 facts=3 时序绿（照抄终态 4 会得红测）——夹具构造 facts=3
    issues = check_counter_reconciliation("正文", "- 计数: 鉴录名数 3+1\n", {"鉴录名数": {"value": 3}})
    assert not any("base_mismatch" in i for i in issues)

def test_prose_anchor_same_sentence():
    # ch30 回放：:154「《鉴录》上四个名字」真命中；:58 船单「七个名字」无锚词排除；
    # :176 修辞「一个名字」排除；:186 POST 行剥 META 排除
    ch30 = (FIX / "chapters" / "chapter-30.md").read_text(encoding="utf-8")
    issues = check_counter_reconciliation(ch30, "- 计数: 鉴录名数 4+0\n", {"鉴录名数": {"value": 4}})
    assert not any("prose_mismatch" in i for i in issues)  # 双误红全消（r5 基线）

def test_ordinal_face_kept():  # characterization：F17 序数判定保留
    issues = check_counter_reconciliation("第五个名字", "- 计数: 鉴录名数 4+1\n", {"鉴录名数": {"value": 4}})
    assert issues == []  # final 5 == 序数 5
```

- [ ] **Step 2: 确认红** → **Step 3: 实现三支路 + id-first**

`check_counter_reconciliation` 重写要点：`declared = {}` 收集 `name -> list[(base, delta)]`；②对 len>1 的 name 计算 finals 集合互斥 → `cd.counter.plan_conflict:{fp}:…`（**issue 串内带完整 id 前缀**）；③逐条 base != facts → `cd.counter.base_mismatch:…`；④prose 面：`text = strip_narrative_body(text)`（剥后——排自身 POST 行）、`_re_total`/`_re_ordinal` 命中句 `_SENTENCE_SPLIT_RE.split` 定位同句、同句须含锚词集任一词、数值 ∉ {facts} ∪ finals → `cd.counter.prose_mismatch:…`。调用点 :627-628 改 id-first（生产传 `fp=fp`，测试省略）：

```python
                for issue in check_counter_reconciliation(content, _memo or "", _counters_facts):
                    mf.append(f"G4.{issue}")  # id-first 铁律（r5.3）：issue 串自带 "cd.counter.xxx:" 前缀；
                    # 现行 f"{fp}:{issue}" path-first 形态会使 check_id() 提取失效 → shadow 静默失灵
```

（issue 串内 detail 已含 fp——函数签名增 `fp: str` 参数或在 detail 拼装；实施取增参 `fp`。）`:623-626` unknown 计数器发射同步改 `G4.cd.counter:{fp}:…` id-first。**两调用方同步（审查轮 2 M6 点名崩溃机制；轮 3 行号勘误：解包处在 :621，:610 是 parse 调用）**：:222 `dict(parse_counter_declarations(...))` 对三元列表直接 `dict()` 崩（dict 要 2 元组）——重写为显式收集循环；:621 `{n for n, _v in _memo_decls}` 对三元解包 `ValueError`（2 元组解包改 3 元 `_n, _b, _d`）。shadow.py 三条登记（**每条登记行带 `# spec #83 §10 行 5/6/7` 标注注释**——阶段 7 核验 #4 计数对齐）。

- [ ] **Step 4: 确认绿 + 既有 F17 面回归**

Run: `uv run pytest tests/unit/gates/g4/test_spec83_counter_anchor.py tests/unit/gates/g4/test_f17_counters.py tests/gates/test_invariant_mutants.py -q`
Expected: PASS（F17 既有正例零回退）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py src/shenbi/gates/g4/shadow.py tests/unit/gates/g4/test_spec83_counter_anchor.py tests/unit/gates/g4/test_f17_counters.py
git commit -m "feat: counter anchor N+M parsing + plan-conflict/base-mismatch/anchored-prose gates, id-first emission (spec #83 T6)"
```

---

### Task 10: 余额锚 `cd.balance_value_drift`（WARN/FAIL 臂＋束级升格）

**Files:**
- Modify: `src/shenbi/gates/g4/post_declarations.py`（余额判定器追加）或独立 `balance_anchor.py`（若 post_declarations 超 ~200 行）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py`（主循环接线：needs project_dir 的 ledger 现值读取）
- Modify: `src/shenbi/gates/g4/state_settling.py`（束级升格：manifest 聚合面）
- Modify: `src/shenbi/gates/g4/shadow.py`（行 8/9 登记）
- Test: `tests/unit/gates/g4/test_spec83_balance_anchor.py`

**Interfaces:**
- Consumes: `cn_amount`（中文数字化）；`truth/particle_ledger.md` 现值行（「余 N 文」最新行——check 时点现值单一信源，**不扫前章正文**：正文回扫会引入与声明面同款噪声面）
- Produces:
  - `parse_ledger_current_value(ledger_text: str) -> int | None`（**轮 5 C1 重钉取数锚**：真实 ledger 现值行形态=`| 第 N 章 | 余额一百零三文 | 未动 | …`（余额前缀+中文数字，:143-:156 实锚）——**「余 N 文」锚与实表不符**（裸「余」形存在于 ch1 :13 `余 17 文`/:109/:118/:124 等多处——**轮 6 M2 勘误：非唯一**；末命中行规则下终值恒 103，但锚证据如实记）；正则钉 `余[额]?\s*[零一二两三四五六七八九十百千\d]+\s*文`、跳「无/未动」非钱行、取**最后一个命中行**（表尾存在乱序追加行）；**Step 1 必含对 fixture 拷贝的解析单测**（断言 ==103——红测直传 ledger_value=113 会绕过解析器，无单测则 TDD 不设防））
  - `parse_spend_events(memo_text: str) -> list[int]`（**轮 4 N2 补＋轮 5 M3 变体面**：plan `- 事件: 支出|N文|…` 支解析；变体覆盖——`支出|无|`/`支出|零文` 跳过（0 不入集）、ch4 复合行 `- 事件: 收入|八文|…｜支出|六文|…` 的**行中部支出段**（行锚正则漏行中段→伪 WARN，须行内 `支出\|` 全扫非仅行首锚）；ch23-plan:43 `- 事件: 支出|四十文|…` 实锚；调用侧 :610 `_memo` 已在作用域）
  - `check_balance_value_drift(content: str, ledger_value: int | None, *, spend_events: list[int] | None = None) -> tuple[list[str], list[str]]` → `(fail_items, warn_items)`：
    - **双面设计（轮 4 N1 定稿——M9 与 I4 的矛盾解）**：判定器输入=**raw content**；`_BALANCE_RE` 在 raw 上匹配、**META/POST 区间位置排除**（复用 quote_verbatim `_meta_regions` 的区间法——ch23:351 POST 行 `- [ ] 余额口径: …` 自述值不入场，M9 目标达成）；**不得以 `strip_narrative_body` 为输入面——其尾部 `strip_scene_markers`（shared.py:366）会剥掉 `<!--SCENE-->` 标记，`first_scene_span` 将恒走无标记退化、FAIL 臂回退全章首现（ch23 误红复活，正是 I4 要杀的病理）**；场景跨度与余额匹配共用 raw 坐标系
    - 强锚句式 `_BALANCE_RE = re.compile(r"(一共|还剩|只剩|剩下|剩|袋底|余额)[^。]{0,6}?([一二两三四五六七八九十百千\d]+)文")`（**审查轮 1 C2：前缀族含裸「剩」与「剩下」**——ch26:26 实测 `纸包里剩一百零三文`（裸剩）、ch26:177 `剩下的一百零三文`；alternation 长形在前防短形吞并；价格句「灯油四文」不命中——前缀限定）
    - **锚点回放义务（Global Constraints 纪律）**：定稿前对 36 章全语料 `grep -nE "(一共|还剩|只剩|剩下?|袋底|余额)[^。]{0,6}[一二两三四五六七八九十百千0-9]+文"` 回放——粘贴命中行清单进 task 记录，**逐章裁定 FAIL 臂判词**（对照该章 check 时点 ledger 值——审查轮 2 I4 教训：ch23:300 `袋底剩一百四十三文`（付后 143 vs 付前 183）是**健康章**——首现深居章尾非章首；裁定不能只分句类，须按首现位置+ledger 时序双维判），发现新形态（如「摸出」「数出」类）扩族再定稿
    - FAIL 臂：**首场景内首现**余额句数值 ≠ ledger 现值 → `cd.balance_value_drift:…`（ch26:L26 类：章首〔场景 1〕103 vs 现值 113）。**「章首」作用域（审查轮 3 I4 机械化定稿）＝`first_scene_span(content) -> tuple[int, int] | None` 新 helper**：行级重扫 `is_scene_marker_line`（shared.py:45），首标记 → 次标记/尾随 META 边界（对齐 `split_scenes` 的 trailing_meta 语义——**勿直接用 `split_scenes`：其返回 `list[tuple[int, str]]`（size, last_line）非场景文本/跨度，且无标记返 `[]`**）；**无标记 fallback=整个叙事体算首场景**（退化为全章首现——FAIL 臂本意；ch23 型误伤仅在有标记语料出现，无标记退化面记 deviation）——本章支出结算发生在后位场景，首场景出现付后值=时序泄漏（ch26 病理：标记 :23/:94/:183，余额行 :26 在场景 1）；深位首现（ch23:300 付后值、标记 :26/:107/:228 共 3 标记 → 场景 3〔轮 5 M1 终勘：轮 4「场景 4」计数误〕）不触发 FAIL（值对时序对），走 WARN 臂裁定
    - WARN 臂（**轮 5 I3 定稿——消解 r3-I3 与 r4 行文的范围矛盾**）：**FAIL 臂评估对象之外的全部余额命中**（含深位首现——ch23 型、含首场景内多时点——ch1 型），值 ≠ ledger 且**带符号值差 `ledger − occurrence` ∉ spend_events**（支出为正：ch23 183−143=+40 ∈ {40} 豁免 ✓；收入形负差不豁免）→ WARN 项（spend_events 由 `parse_spend_events(memo)` 供参，None=不豁免——轮 4 N2 定稿）。**「非本章首现」（轮 3 I3 定稿——含首场景内多时点推进）**：ch1 形态=场景 1 内 :37 一共十七文→:39 剩五十二文→:55 我剩十七文（标记 :26/:113，三行全在场景 1 但 :39/:55 非章首现）→ WARN 面用例（`ledger_value=17`，期望 WARN ≥1）；绿路径测试用 tmp_path 结构用例（干净正文+一致 ledger 值）；**深位首现绿测（轮 4 N1 补）＋META 排除钉（轮 6 M3）**：ch23 入 fixture 包，断言其付后深位首现（143 vs 183）零 FAIL；**另断言（轮 7 I1 重钉——None 态下 :300 深位命中〔值 143〕合法 WARN，与 :351 POST 命中同值不可按值消歧）**：spend_events=None 时 `fails == []` ∧ `not any("一百八十三文" in w for w in warns)`（:351 付前值 183 的 POST 命中被 META 排除的直接行为证）∧ `len([w for w in warns if "一百四十三文" in w]) == 1`（**恰一条** 143-WARN=:300 的合法深位漂移——0 条=深位 WARN 面被错误关闭，>1 条=META 排除失效）
  - 束级升格（§10 行 9）：`cd.balance_value_drift.bundle`——落点 **G4.ss 扩面**（state_settling 束 settle 时从 manifest G4.cd WARN 记录聚合：同锚 WARN 束内 ≥2 章复发或同章 ≥2 次 → must_fix；经 :4016 消费点自然 demote）
  - shadow 键：FAIL 臂与 bundle 臂 `("market_params", "balance_anchor")`（**登记行带 `# spec #83 §10 行 8/9` 标注注释**——阶段 7 核验 #4 计数对齐）

**复杂度: infra** · **test_kind: tdd_red_green** · **测试层级: T1** · fixtures: spec83/chapters/chapter-26.md（章首 103 红）+ chapter-23.md（深位首现绿测+None 态钉测）+ truth/particle_ledger.md（现值行解析==103）+ **ch1=WARN 面用例**（多时点余额叙事，非绿路径——审查轮 2 I3）；绿路径=tmp_path 结构用例

- [ ] **Step 0: 锚点全语料回放（C2/I4 教训——写正则与 FAIL 判词前先回放）**

Run: `grep -nE "(一共|还剩|只剩|剩下?|袋底|余额)[^。]{0,6}[一二两三四五六七八九十百千0-9]+文" novel-xinghuo-vol1/chapters/chapter-*.md`
Expected: 命中行清单粘贴进 task 记录；**双维裁定**：①句类（余额句入锚 vs 价格句不入）②逐章 FAIL 臂判词（首场景内首现值 vs 该章 check 时点 ledger 值——ch26 红/ch23 绿〔付后值深位首现〕/ch1 WARN 面〔多时点〕三类标杆核对）；发现新前缀形态（摸出/数出类）→ 扩族后再定稿 `_BALANCE_RE` 与首场景作用域

- [ ] **Step 1: 写红测**

```python
def test_ch26_opening_balance_mismatch_fails():
    ch26 = (FIX / "chapters" / "chapter-26.md").read_text(encoding="utf-8")
    # ch26:26 实测「纸包里剩一百零三文」（裸「剩」——C2 勘误后前缀族命中）
    fails, _ = check_balance_value_drift(ch26, ledger_value=113)  # ch26 check 时点前章末值 113（付前）
    assert any("balance_value_drift" in f for f in fails)  # 章首 103 ≠ 113 → FAIL 臂红

def test_spend_exemption_arithmetic():  # 轮 6 I2：豁免算术钉测——带符号 ledger−occurrence，符号翻转实现即红
    from shenbi.gates.g4.post_declarations import check_balance_value_drift
    ch23 = (FIX / "chapters" / "chapter-23.md").read_text(encoding="utf-8")
    fails, warns = check_balance_value_drift(ch23, 183, spend_events=[40])  # 183−143=+40 ∈ {40} 豁免
    assert fails == [] and all("一百四十三文" not in w for w in warns)  # :300 零信号

def test_price_sentence_not_anchored():
    _, warns = check_balance_value_drift("灯油四文一斤，他买了。", ledger_value=103)
    assert warns == []  # 价格句不命中强锚

def test_bundle_escalation_from_manifest_warns():
    # 束 settle 聚合：束内两章各 1 WARN → cd.balance_value_drift.bundle must_fix（经 :4016 可 demote）
    ...
```

- [ ] **Step 2: 确认红** → **Step 3: 实现**（判定器 + g4_chapter_drafting 接线 [ledger 读取：`project_dir/truth/particle_ledger.md` 缺席→ WARN 可见 skip，对齐 F16/F17 facts 缺席三律] + state_settling 束级聚合 + shadow 两条登记）

- [ ] **Step 4: 确认绿**

Run: `uv run pytest tests/unit/gates/g4/test_spec83_balance_anchor.py tests/unit/gates/g4 -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/ src/shenbi/gates/g4/shadow.py tests/unit/gates/g4/test_spec83_balance_anchor.py
git commit -m "feat: balance_value_drift anchor with WARN arm + bundle escalation (spec #83 T6)"
```

---

### Task 11: 来历锚 WARN（provenance 读侧＋settle 写侧指引）

**Files:**
- Modify: `src/shenbi/gates/g4/post_declarations.py`（来历判定器追加）
- Modify: `skills/shenbi-state-settling/SKILL.md`（产出指引一行——经手事件新行附 `地点·chN`；**prose 指引不触 reads/writes/decisions 契约面**，lint-contracts 不受影响；表头扩列归 #84 T0 回灌批——本 task 不动表头）
- Test: `tests/unit/gates/g4/test_spec83_provenance_anchor.py`

**Interfaces:**
- Consumes: `truth/prop_registry.md` 三列表（实体名/当前owner/经手事件；provenance 为未来第 4 列——**存量行缺列 → 跳过该实体**，不回填不恒 WARN）
- Produces: `check_provenance_anchor(content: str, registry_text: str) -> list[str]`（WARN-only）：
  - registry 行解析：`| 实体 | owner | 事件 | [地点·chN] |`——第 4 段存在才入场
  - 正文来历句：`(得|授|给|塞)` + 实体名 + `那夜|那天` 同句（_SENTENCE_SPLIT_RE 切句）
  - 词级重叠（T3 同款最粗粒度，不造分词假象）：provenance 地点串的全部 2-gram 与来历句零重叠 → WARN（渡口 vs 门洞类）；有任一共享 → pass
  - 挂 G4.cd 主循环 `c.append WARN`（**非 FAIL 门不入 §10**——人工裁决面）

**复杂度: infra** · **test_kind: tdd_red_green** · **测试层级: T1** · fixtures: spec83/truth/prop_registry.md（三列现状=存量缺列跳过路径）+ spec83/chapters/chapter-35.md（Task 0 已含——35/36 章骨哨「渡口那夜」来历句实证）

- [ ] **Step 1: 写红测**（渡口/门洞零重叠 WARN；同词共享 pass；存量缺列跳过=全语料现状零 WARN）→ **Step 2: 确认红** → **Step 3: 实现判定器+接线+SKILL.md 指引行** → **Step 4: 确认绿**（`uv run pytest tests/unit/gates/g4/test_spec83_provenance_anchor.py tests/unit/gates/g4 -q`）→ **Step 5: Commit**（`feat: provenance anchor WARN face + settle write-side guidance (spec #83 T6)`；SKILL.md 与代码同 commit——pathspec 列全）。

---

### Task 12: `tools/lint_outline_truth_drift.py` canon 回灌对账工具（spec T3）

**Files:**
- Create: `tools/lint_outline_truth_drift.py`
- Modify: `justfile`（`outline-drift *args:` 配方，对齐 audit-lint/pool-lint 形态）
- Modify: `AGENTS.md`（Key Commands 节登记 `just outline-drift <dir> [--volume N]`——r5.3 补的本仓文档惯例）
- Modify: `command-to-give.md`（**执行协议节内新条目**——审查轮 1 M17：该文件现无「束节奏」节，节构为 可靠性边界/执行协议/阈值 三节；在「执行协议」节束推进相关步骤处加运行义务：每 6 章束 settle 后＋卷界前必跑 `just outline-drift`；finding → 人工裁定「改大纲 or `※canon-vN` 引注」双择一不许悬空）
- Test: `tests/unit/tools/test_spec83_outline_drift.py`

**Interfaces:**
- Produces: CLI `python tools/lint_outline_truth_drift.py <dir> [--volume N] [--declarations]`（exit 0=零悬空 finding / 1=有 finding；工具只报不写）
  - 四对账（默认面）：
    1. 物象清单对账：卷纲节点行「四件：红纸包、骨哨、《鉴录》、私账」形道具集合 vs `truth/facts/props.json` 持有集——持有物缺席节点清单 → finding
    2. 来历短语对账：prop_registry 事件行 vs 卷纲描述——双方 2+ 字词集交集为空 → finding（`--strict` 收紧；默认最粗粒度）
    3. 承诺件对账：卷纲「金句出场点/卷末彩蛋/梗位」标签项 grep 全卷正文缺件 → finding
    4. 欠账对账：正文「欠」「还之日」句式行 vs 种子还账进度表——**实锚（审查轮 1 I3）：`genesis-context/chapter_outline.md:370`「三大打卡装置/还账进度表（私账打卡）」节（首批六行清单在此；outline/volume_map.md:123/:430 仅引用不带表）**——运行期新账不在排期 → finding；该文件缺失 → 此对账面 SKIP 报告（不硬崩）
  - `--declarations` 子命令面（T7 声明面漂移清单，Task 13 实装）：scene_hook 11 行 + voice_density + 无 META 块——**本 task 预留参数骨架**（argparse 注册+「子命令未实装」明确报错），实装在 Task 13
- Consumes: `scene_hook_mismatches`/`parse_scene_declarations`（gates/shared.py:114/:69——Task 13 用）

**复杂度: leaf**（tools/ 新文件＋just/docs 登记；无 src/shenbi infra 模块改动、无契约面）· **test_kind: tdd_red_green** · **测试层级: T1** · fixtures: spec83/outline/volume_map.md + truth/（卷一四实证：四件清单一把哨/临终 vs ch2 授哨/渡鸦局档案卡/五欠账不在首批六行）

- [ ] **Step 1: 写红测（卷一四实证夹具单测——真项目片段拷贝）**

```python
# tests/unit/tools/test_spec83_outline_drift.py
"""spec #83 T3: canon 回灌对账——卷一四实证作夹具（P1-2 根因链）。"""
def test_second_whistle_missing_from_node_list():  # 双哨 canon：truth 持有、节点清单只一把
    findings = run_lint(FIX)  # volume_map:88 四件清单 vs props.json（两把哨）
    assert any("骨哨" in f.detail and "节点清单" in f.detail for f in findings)

def test_provenance_phrase_mismatch():  # 「临终塞给他」vs 实际 ch2 存续授哨——词集交集空
    ...

def test_promise_item_missing():  # 渡鸦局档案卡（卷纲 L21 承诺件）正文缺件
    ...

def test_new_debt_not_scheduled():  # 五条欠账（ch36 运行期立账）不在还账进度表首批六行
    ...
```

- [ ] **Step 2: 确认红** → **Step 3: 实现工具 + just 配方 + AGENTS.md/command-to-give.md 登记**

```python
# tools/lint_outline_truth_drift.py 骨架（finding dataclass + 四对账函数 + argparse main；
# 中文词集提取=re.findall(r"[一-龥]{2,}", …) 最粗粒度——不造分词假象；输出人读表+exit code）
```

```makefile
# justfile（audit-lint 惯例位）
# Outline↔truth canon drift reconciliation: 只报不写（spec #83 T3）
outline-drift *args:
    uv run python tools/lint_outline_truth_drift.py "$@"
```

- [ ] **Step 4: 确认绿 + 只读性验证**

Run: `uv run pytest tests/unit/tools/test_spec83_outline_drift.py -q && uv run python tools/lint_outline_truth_drift.py tests/fixtures/spec83; echo "exit=$?"`
Expected: 测试 PASS；真实 fixture 目录跑出四实证 finding、exit=1；运行后 `git status tests/fixtures/spec83` 无改动（工具只报不写）

- [ ] **Step 5: Commit**

```bash
git add tools/lint_outline_truth_drift.py justfile AGENTS.md command-to-give.md tests/unit/tools/test_spec83_outline_drift.py
git commit -m "feat: lint_outline_truth_drift canon reconciliation tool + just/AGENTS wiring (spec #83 T3)"
```

---

### Task 13: 验收口径清偿（spec T7：判据 5 声口 token 族＋#80 回放口径＋--declarations 子命令）

**Files:**
- Modify: `tools/regen_accept.py:315-359`（`check_blind_recognition` 声口 token 族替换）＋判据 2b 读法注释（:177 段）
- Create: `docs/framework/gates.md` #80 节（manifest 门行对已生成章不回放口径——文档化）
- Modify: `tools/lint_outline_truth_drift.py`（`--declarations` 实装：scene_hook 全卷对账[复用 `scene_hook_mismatches`] + voice_density 声明 vs 正文 + 无 META 块清单）
- Test: `tests/unit/tools/test_spec83_regen_accept_voice.py`、`tests/unit/tools/test_spec83_outline_drift.py`（--declarations 用例追加）

**Interfaces:**
- Consumes: `ACCOUNTING_VERBS`（text/voice_lexicon.py:16）、`catchphrases_from_card`（voice_lexicon——现 markers 面）、`_BLIND_MIN_RATIO = 4/5`（regen_accept.py:54）、`scene_hook_mismatches(decls, scenes)`（gates/shared.py:114）
- Produces: `voice_token_buckets(cards) -> dict[str, tuple[str, ...]]`（per-角色声口 token 桶 = 卡面 catchphrase ∪ 账房动词族归属（主角侧 ACCOUNTING_VERBS 计入其桶）∪ 自嘲句尾正则族（角色卡自嘲标记）——分桶逻辑独立可直测）；`check_blind_recognition` 换消费 `voice_token_buckets`（argmax 归属口径不变 `best.name == owner.name`）。判据 2b 读法注释：G4.cd.* 门行对已生成章（卷一 10-29）不回放——manifest latest-wins 面已剥离历史，卷二按新口径执行。

**复杂度: infra**（验收判据机件+docs 门禁文档）· **test_kind: tdd_red_green + characterization**（判据 2b/6 既有面）· **测试层级: T1** · fixtures: spec83/chapters/（15 章声口样本）+ spec83/characters/（Task 0 递归拷贝 **≥5 张带卡面标记卡**——审查轮 1 I4：`check_blind_recognition` 在 `len(cards) < 5` 硬 FAIL（regen_accept.py:318-321），2-3 张走不通真实入口）

**测法（I4 对齐）**：①桶归属逻辑**直测**（新分桶函数 `voice_token_buckets(cards) -> dict[str, tuple[str, ...]]` 单测——账房动词入主角桶/自嘲尾入对应桶/卡面 catchphrase 保留）；②判据 5 端到端 PASS 正例用 **≥5 张真实卡 + fixtures 章**驱动（真实入口可达）；③无卡夹具走 `len(cards) < 5` FAIL 分支 characterization。

- [ ] **Step 1: 写红测**（token 族归属单测：账房动词句归属主角桶；自嘲句尾归属；4/5 阈值可达性——fixtures 章截段上判据 5 判 PASS 的正例）→ **Step 2: 确认红** → **Step 3: 实现**（regen_accept 替换 + gates.md #80 节 + --declarations 实装）→ **Step 4: 确认绿**

Run: `uv run pytest tests/unit/tools/test_spec83_regen_accept_voice.py tests/unit/tools/test_spec83_outline_drift.py tests/unit/tools -q && uv run python tools/regen_accept.py --help`
Expected: PASS；`--declarations` 面：`uv run python tools/lint_outline_truth_drift.py tests/fixtures/spec83 --declarations` 输出 scene_hook 漂移清单（工具只报不写）

- [ ] **Step 5: spec-deviations 记 §9.2 运行侧验收归属**（卷二首束实弹=T2/T4/T5/T6/T7 机制的 regen 运行窗口验收，归 #84 驱动侧执行；本批离线测试面已全覆盖——验收覆盖表 §9.2 行同此口径）

- [ ] **Step 6: Commit**

```bash
git add tools/regen_accept.py tools/lint_outline_truth_drift.py docs/framework/gates.md tests/unit/tools/test_spec83_regen_accept_voice.py tests/unit/tools/test_spec83_outline_drift.py
git commit -m "feat: voice-token criterion 5 + #80 replay-scope doc + --declarations face (spec #83 T7)"
```

---

## Post-task 全局核验（阶段 7-8 输入）

1. `ls .superpowers/sdd/audit-T*.md | wc -l` == 14（T0-T13）
2. `just check` exit 0（两段 pytest + lints 三件 + 幂等 diff）
3. `uv run python tools/lint_outline_truth_drift.py tests/fixtures/spec83` exit=1 四实证 finding 齐（只读复验）
4. §10 checklist 逐行核验：9 支路 × (GATE_TO_SHADOW_KEY 条目 + id-first 发射 + 消费点路径) —— `grep -n "spec #83" src/shenbi/gates/g4/shadow.py` 9 条
5. §11 落点表逐行核验：四字面量 grep 唯一落点（`grep -rn "declarations_stale\|bundle_merged\|streak_monitor_rewinds" src/shenbi/ | grep -v test`；`provenance` 单独核——**轮 3 M11：scoring.py 既有 `_provenance`（:376/:380/:469/:561）与 capability_fs.py 属无关同名词**，grep 收窄为 prop_registry 表列形态 `provenance` 裸词在 gates/g4 与 skills/shenbi-state-settling 面）

## Self-Review 记录（含审查轮 1 清偿）

- **Spec coverage**：T1 门+两前置（plan T1/T2/T3）；T2 主+次（T4/T5）；T3（T12）；T4 计数器+路由+降格面（T6/T7——`incremental_only` 降格=不建 FAIL 门、WARN 量化挂 matrix_structure、反馈定向挂 _length_family 先例，均落 T7）；T5（T8）；T6 三锚（T9/T10/T11）；T7（T13）；§10 九支路分散落各门 task 且每 task 步骤含 shadow 登记；§11 四落点落 T5/T6/T8/T11。**审查轮 1 补漏**：§1 字数行虚假精度 WARN（落 T3）；§4 铁律 0 指路行（落 T7）。§8 非目标不产生 task（正确）；spec §2 尾注「timeline 行归 T5 工具顺带对账」与 §8「timeline 随 #84 T0 手工清、不造通用 linter」相抵——**按 §8 非目标执行**（timeline 不入 T8 工具面，记 deviation 备查〔轮 5 M8〕）。
- **Placeholder scan**：T10/T11/T13 的 Step 1-5 以压缩形态书写（同 skill 模板步序完整、代码在关键面）——执行时按展开步序走；无 TBD/「适当处理」类空指引。
- **Type consistency**：`parse_counter_declarations` 三元返回在 T9 内两调用方+测试同步；`check_post_quote_verbatim` 签名 T2/T3/T4 三处消费一致（T4 消费处显式补 `G4.` 前缀）；`check_prop_purge_on_revision` 带 `chapter` kwarg（T4 红测断言真章号）；`check_counter_reconciliation` fp keyword-only 带默认（三参调用不破）；`streak_monitor_rewinds` T6 定义/T8 复位点互指一致；`_record_retry(state, chapter, skill)` 无 kind 参；fixture 路径按 Global Constraints 深度分表（g4→3 / pipeline+tools→2 / integration→1——轮 7 M5 勘误，前稿「一律 parents[3]」作废）。
- **审查轮 1 清偿对照**（2C+8I+9M 全处理）：C1 转折词密度真实形态（T3 正则+红测重钉）；C2 余额前缀族扩剩/剩下+回放 Step 0（T10）；I3 欠账表锚 genesis-context/chapter_outline.md:370（T12+T0）；I4 角色卡 ≥5 张递归+桶逻辑直测（T13+T0）；I5 chapter kwarg+POST 复验 G4. 前缀（T4）；I6 依赖表 T3→T2、T10/T11→T2；I7 执法可达窗口释明+双摄取清除点（T5——**接线锚经轮 2 C1 再修**）；I8 尾注测试换 ch19（T1）；I9 字数行 WARN 补（T3）；I10 parents[3] 全局约束；M11 matrix WARN 返回形态（T7）；M12 路由单述反馈文本通道（T7）；M13 红测对齐内联写入者（T5）；M14 _record_retry 签名（T6）；M15 fp kw-only（T9）；M16 『』嵌套去重义务（T1）；M17 command-to-give 挂执行协议节（T12）；M18 铁律 0 指路行（T7）；M19 characters 递归拷贝（T0）。
- **审查轮 2 清偿对照**（1C+3I+5M 全处理，协调者亲验 5/5 载重项成立）：**C1** T5 执法接线改两处真实派发路径（run_parallel_post_draft_steps :3450＋cli.py _execute_pending_re_dispatches :260——正常 settle 走并行块 :3954 拦截、修订后重派 settle 走 cli 队列完全绕过 chapter_loop 通用路径；cli.py 入 T5 Files；集成测试两路径都驱动）——**「两处」穷尽性声明经轮 3 C1 证伪，终态三站点见下**；I2 字数 WARN 口径换 total_chars_md_text（wc=CJK 计数系统差 13-19%）；I3 ch1 绿路径前提撤（多时点余额叙事→WARN 面用例，绿路径=tmp 结构用例）；I4 FAIL 臂钉「首场景内首现」作用域（ch23 付后值深位首现=健康，ch26 章首=病理；Step 0 回放升双维裁定）；M5 counters.json facts 嵌套；M6 :222 dict()/:610 解包双崩溃机制点名；M7 14 章+回归 sketch 变量定义；M8 ch25 负例行为级断言；M9 parse_prop_lines 去重保序。
- **审查轮 3 清偿对照**（1C+4I+7M 全处理，协调者亲验 4/4 载重项成立——cli.py:1082/:1296 redo 路径、split_scenes 返回 (size,last_line) 且无标记返 []、ch1 余额行全在场景 1、并行块作用域无 step/retry_key）：**C1** T5 第三派发路径（STATE_SETTLE checkpoint REJECT/MODIFY redo → 串行通用 :4253）——终态设计改**集中式 `_pre_settle_guard` 纯谓词 + 三站点接线（并行块/cli 队列/串行通用）+ 机械穷尽性 grep 测试**（把「穷尽性声明」变成受测不变量，根治轮 2-3 同类证伪循环）；I2 helper 适配三站点作用域（settling_step/entry dict/step）+ 各站路由钉既有失败分支先例（并行块不得裸 return bool 破 tuple 契约；cli 镜像 :331-350；串行 _handle_failure）；I3 WARN 臂改「非本章首现」（含首场景内多时点推进——ch1 :39/:55 入面，ledger=17 期望 ≥1 WARN）；I4 first_scene_span 新 helper（行级 is_scene_marker_line 重扫；勿用 split_scenes——返回 (size,last_line) 非跨度；无标记 fallback=全叙事体）+ T10 取数面 strip_narrative_body（M9：POST 自述值不入场）；I5 parents 深度分表（g4→3/pipeline+tools→2/integration→1）；M6 chapter=28；M7 all-demoted 反馈清理契约；M8 语料校准锚（ch1 5.5%/ch26 3.5% 真阳）；M10 位置法复算 helper 自备+span 级去重进 sketch；M11 provenance grep 收窄；M12 集成测试三路径+PASS-with-warnings leg 具名。
