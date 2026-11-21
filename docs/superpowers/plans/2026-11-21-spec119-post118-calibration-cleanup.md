# Spec #119 post118-calibration-cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** content_uniqueness 门比对池纯形化（谓词单源 replay↔门同引）＋review 转折预算从 `TRANSITION_CAP_PER_1000` 单源派生——修 #118 后两件标定收尾（测量面=执法面）。

**Architecture:** T1 在 `gates/shared.py` 落白名单谓词 `is_pure_chapter`（`chapter-NN` 数字精确形），G4.cd 比对池与 tools 回放改同引；T2 把 `pipeline/review_checklist.py` 的退役公式 `max(5, wc//1000)` 换成常量派生 `ceil(CAP×max(wc,1)/1000)`（函数级 import，无循环依赖——g4→pipeline 传递闭包零模块级引用已实测）。两 task 均为 **infra**（触 `gates/g4/`+`pipeline/` 模块）→ **协调者亲自实现＋TDD**（§Profile leaf/infra 分流；模型分档 OFF 单血统）。

**Tech Stack:** Python 3.11+ / pathlib / pytest / structlog / just（验证走 `uv run` 与 CI 同构）。

## Global Constraints（spec r1.1 逐字块——每 task 审查派发时注入）

- **40% 阈与指纹口径不动**（T1）；
- 比较语义钉死：**转折计数 ≥ 预算即 ERROR（预算=首个失败计数）**——非整千 wc 与门 FAIL 精确对齐、整千 wc 严一词（保守向：门 FAIL 章必不漏过 review）；
- `max(wc, 1)` 镜像门侧 `chapter_drafting.py:998` 护栏（wc=0 退化态不产「零转折也 ERROR」假阳）；
- 测量面=执法面同谓词：`is_pure_chapter` 单源（shared.py），replay 与门同引；
- G0.9：fixture 只用真实产物；结构性输入（tmp_path 组装）允许；
- 域约束：真实 LLM dispatch（shenbi-dispatch/pipeline init|resume|review）**付费且写状态——全流程禁为验证目的触发**（本件零 dispatch，全离线）；
- F947：验收全离线可复验（回放报告＋结构断言，无 LLM 依赖）；
- SKIP 两分支（目录缺席/基数≤1）基数口径随池口径同变（结构单点：`:1149` 消费同一池变量）；
- 基线注记已随立项 PR #372 预落——T1 后只核期望列（FAIL 32→0），不重写注记。

## AC 覆盖表

| spec 验收 | task | test/证据 |
|---|---|---|
| 1. T1-T2 判据全绿（红测双向＋50 章重跑＋baseline 核对） | T1/T2 | T1 三测＋replay 报告 uniqueness 行；T2 两 re-pin 测 |
| 2. diff 面止于清单（验收 2） | T1/T2 | 阶段 7 `git diff --stat` 核对（本 plan Files 清单=清单） |
| 3. `just check` 全绿 | — | 阶段 7 门禁 |

---

### Task 1: uniqueness 纯章形池过滤＋谓词单源

**复杂度: infra**（触 `gates/g4/chapter_drafting.py`）· **test_kind: tdd_red_green** · 测试层级 T1 · 协调者亲自实现。

**Files:**
- Modify: `src/shenbi/gates/shared.py`（`chapter_no_raw` 后、`load_facts_oracle` 前新增谓词）
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:19-43`（shared import 列表加 `is_pure_chapter`）＋ `:1148`（池过滤，一函数内一处）
- Modify: `tools/gate_power_replay.py`（删 :162-163 本地 `_pure_chapter`，改引 shared，改 :171/:254 两调用点）
- Test: `tests/unit/gates/g4/test_gate_power_negatives.py`（改写 :224 测＋新增场景①测）
- Test: `tests/unit/gates/test_shared_is_pure_chapter.py`（新建，谓词直测）
- 产出工件: `reports/2026-11-22-gate-power-vol1-post119.md`（回放重跑）＋ `docs/framework/gate-power-baseline.md`（整表重指＋uniqueness 行数字）

**Interfaces:**
- Consumes: `CHAPTER_NUM_RE`（shared.py 既有单源章号正则，fullmatch 语义）；`CheckContext`/`ctx.rd`/`ctx.pf`（:1126 既有）
- Produces: `def is_pure_chapter(stem: str) -> bool`（`src/shenbi/gates/shared.py`；语义=现 replay `_pure_chapter` 逐字——`re.fullmatch(r"chapter-\d+", stem) is not None`；T2 与后续回放共用此单源）

- [ ] **Step 1: 谓词失败测试（红）**

新建 `tests/unit/gates/test_shared_is_pure_chapter.py`：

```python
"""spec #119 T1: 纯章形白名单谓词单源（chapter-NN 数字精确形）."""

import pytest

from shenbi.gates.shared import is_pure_chapter


@pytest.mark.parametrize(
    ("stem", "want"),
    [
        ("chapter-1", True),
        ("chapter-50", True),
        ("chapter-030", True),  # 零填充同纯形（B5 跨书注记——命名碰撞面由管道控制）
        ("chapter-1-pre-rev", False),  # 管道修订备份=历史层，白名单外
        ("chapter-1-duplicated", False),
        ("chapter-1-decisions", False),
        ("chapter", False),
        ("chapter-", False),
        ("prologue", False),
    ],
)
def test_is_pure_chapter_whitelist_form(stem: str, want: bool) -> None:
    assert is_pure_chapter(stem) is want
```

Run: `uv run pytest tests/unit/gates/test_shared_is_pure_chapter.py -q`
Expected: FAIL with `ImportError: cannot import name 'is_pure_chapter'`

- [ ] **Step 2: 场景①失败测试（红）——pre-rev 不入池**

`tests/unit/gates/g4/test_gate_power_negatives.py` 新增（放在 `test_content_duplicated_fails_content_overlap_gate` 改写体旁）：

```python
def test_content_uniqueness_excludes_pre_rev_from_pool(tmp_path: Path) -> None:
    """spec #119 T1: pre-rev 备份不入比对池——近全同稿不触发 FAIL（比对真跑非 SKIP）."""
    import json as _json

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    base = next(sorted(Path("tests/fixtures").glob("chapter-*-draft.md"))).read_text(
        encoding="utf-8"
    )
    ch3 = (FIX_DIR / "chapters" / "chapter-3.md").read_text(encoding="utf-8")
    d = tmp_path / "proj"
    (d / "chapters").mkdir(parents=True)
    (d / "chapters" / "chapter-1.md").write_text(base, encoding="utf-8")
    # pre-rev 备份=修订前原稿的逐字拷贝（chapter_loop 写入，重叠 1.0）
    (d / "chapters" / "chapter-1-pre-rev.md").write_text(base, encoding="utf-8")
    # 第二纯形章（真实产物、内容互异）——池基数 ≥2 使比对真跑
    (d / "chapters" / "chapter-3.md").write_text(ch3, encoding="utf-8")
    res = _json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-1.md")], str(d), str(d), repo_root=None)
    )
    mf = res.get("must_fix", [])
    assert not any(m.startswith("G4.cd.content_overlap:") for m in mf), mf[:3]
    rows = [c for c in res["checks"] if c["id"] == "G4.cd.content_uniqueness"]
    assert rows and rows[0]["s"] != "FAIL", rows
```

Run: `uv run pytest "tests/unit/gates/g4/test_gate_power_negatives.py::test_content_uniqueness_excludes_pre_rev_from_pool" -q`
Expected: FAIL —— 过滤前池含 `chapter-1-pre-rev.md`，重叠 1.0 > 0.40 → must_fix 含 `G4.cd.content_overlap:`（断言 `not any` 失败＝红）

- [ ] **Step 3: 场景②改写（红性保持——纯形双侧仍红的回归哨）**

改写 `test_content_duplicated_fails_content_overlap_gate`（:224-229）：fixture 文件名形态不复用（其池过滤后塌缩→SKIP），tmp_path 组装纯形双侧（内容=真实产物，语义=「13 段 append」构造法）：

```python
def test_content_duplicated_fails_content_overlap_gate(tmp_path: Path) -> None:
    """纯形双侧仍红（spec #119 T1 哨兵）：duplicated 章对 chapter-3 复制 13 段 append → 指纹占比 >40%."""
    import json as _json

    from shenbi.gates.g4.chapter_drafting import g4_chapter_drafting

    dup = (FIX_DIR / "chapters" / "chapter-1-duplicated.md").read_text(encoding="utf-8")
    ch3 = (FIX_DIR / "chapters" / "chapter-3.md").read_text(encoding="utf-8")
    d = tmp_path / "proj"
    (d / "chapters").mkdir(parents=True)
    (d / "chapters" / "chapter-1.md").write_text(dup, encoding="utf-8")
    (d / "chapters" / "chapter-3.md").write_text(ch3, encoding="utf-8")
    res = _json.loads(
        g4_chapter_drafting([str(d / "chapters" / "chapter-1.md")], str(d), str(d), repo_root=None)
    )
    mf = res.get("must_fix", [])
    assert any(m.startswith("G4.cd.content_overlap:") for m in mf), mf[:3]
```

Run: `uv run pytest "tests/unit/gates/g4/test_gate_power_negatives.py::test_content_duplicated_fails_content_overlap_gate" -q`
Expected: PASS（双侧纯形在过滤前后都在池内——本测是防过度过滤的回归哨：将来有人把过滤器拧过头（池被清空/塌缩→门判定变绿 SKIP）时，本测因 FAIL 不再发射而变红报警；注意原 `_g4` fixture 直读形态被本改写替换，docstring 语义不变）

- [ ] **Step 4: 实现——谓词单源＋池过滤＋replay 改引**

`src/shenbi/gates/shared.py`（`chapter_no_raw` 函数后、`load_facts_oracle` 前插入）：

```python
def is_pure_chapter(stem: str) -> bool:
    """True for the canonical live-chapter stem ``chapter-NN`` (digits-exact).

    Whitelist form (spec #119 T1): historical-layer variants (``-pre-rev``
    backups, future suffixes) fall outside the pool by shape, not by
    enumeration. Single source for both the measurement face (replay) and
    the enforcement face (G4.cd) — spec #116 C3. Reuses CHAPTER_NUM_RE under
    fullmatch (capture group does not affect the boolean) — chapter-number
    regex single-source discipline (z11 F1301 / lint_chapter_num_single_source).
    """
    return CHAPTER_NUM_RE.fullmatch(stem) is not None
```

（不新建 `PURE_CHAPTER_RE`——plan 审查 I-3：第二份章号正则以字形差绕过 `lint_chapter_num_single_source` 单源执法；`CHAPTER_NUM_RE.fullmatch` 与 replay 旧 `_pure_chapter` 对所有输入逐位等价。）

`src/shenbi/gates/g4/chapter_drafting.py`：
- `:19-43` 既有 `from shenbi.gates.shared import (...)` 列表加一行 `is_pure_chapter,`（`chapter_word_floor,` 之后）；
- `:1148` `other_chapters = list(chapters_dir.glob("chapter-*.md"))` → `other_chapters = [p for p in chapters_dir.glob("chapter-*.md") if is_pure_chapter(p.stem)]`（`:1149` 基数 SKIP 消费同一变量，口径自动同变——不另改）

`tools/gate_power_replay.py`：
- 删 `:162-163` `def _pure_chapter(...)` 及其前后多余空行（净删后保持标准 2 空行分隔——残留 4 连空行会被 `ruff format --check` 打红）；
- `:24-30` 既有 `from shenbi.gates.shared import (...)` 括号列表插入 `is_pure_chapter,`（`count_transition_words,` 之后——**不另起 import 行**，同模块双 from-import 触发 I001）；
- `:171`/`:254` 两处 `if _pure_chapter(p.stem)` → `if is_pure_chapter(p.stem)`（全调用方 grep 已清：仅此两处＋tests 无私有名 import）

- [ ] **Step 5: 红转绿**

Run: `uv run pytest tests/unit/gates/test_shared_is_pure_chapter.py "tests/unit/gates/g4/test_gate_power_negatives.py::test_content_uniqueness_excludes_pre_rev_from_pool" "tests/unit/gates/g4/test_gate_power_negatives.py::test_content_duplicated_fails_content_overlap_gate" "tests/unit/gates/g4/test_gate_power_negatives.py::test_content_uniqueness_skip_rows_explicit" tests/unit/tools/test_gate_power_replay.py -q`
Expected: 全 PASS（含 SKIP 双分支既有测＋replay collect 跳非纯形既有行为测——谓词换源行为不变）

- [ ] **Step 6: 邻域回归**

Run: `uv run pytest tests/unit/gates/ tests/unit/tools/ -q`
Expected: 全 PASS（gates 树＋tools 树零连带红）

- [ ] **Step 7: 50 章重跑（批级一次）＋报告核对**

Run: `uv run python tools/gate_power_replay.py novel-xinghuo-vol1 --out reports/2026-11-22-gate-power-vol1-post119.md`
Expected: 报告生成；`G4.cd.content_uniqueness` 行 = `50 | 0 | 0 | 0 | 0.00`（现语料纯池零跨章重复——audit-T8 预证 0/50）；**其余行与 `reports/2026-11-20-gate-power-vol1-post118.md` 逐行一致**（报告为确定性渲染无时间戳——diff 应恰好只有 uniqueness 一行含 firing 列变化；T1 不触其他门）

- [ ] **Step 8: baseline 整表重指＋uniqueness 行更新**

`docs/framework/gate-power-baseline.md`：
- 33 处 `reports/2026-11-20-gate-power-vol1-post118.md` → `reports/2026-11-22-gate-power-vol1-post119.md`（sed 整表替换；`＝#118 后权威态` 标签改 `＝#119 后权威态`）；
- `:40` 登记表头注「权威回放」句追加：`2026-11-22 spec #119 落地后权威回放=reports/2026-11-22-gate-power-vol1-post119.md（uniqueness 纯形池过滤——FAIL 32→0，聋门修复）`；
- `:59` uniqueness 行**最近回放数列**（`50 章 @ …`）改 `50 章 @ 2026-11-22（post119 报告＝#119 后权威态）`、依据列追加 `**spec #119 T1 已执行**：纯形白名单池（is_pure_chapter 单源）——重放 50 PASS/0 FAIL（firing 0.00＝纯池零跨章重复，audit-T8 预证兑现）`。

Run: `uv run python tools/lint_gate_power_baseline.py`（justfile :36 同构）
Expected: PASS（baseline 表结构 lint 绿）

- [ ] **Step 9: Commit**

```bash
git add src/shenbi/gates/shared.py src/shenbi/gates/g4/chapter_drafting.py tools/gate_power_replay.py tests/unit/gates/test_shared_is_pure_chapter.py tests/unit/gates/g4/test_gate_power_negatives.py reports/2026-11-22-gate-power-vol1-post119.md docs/framework/gate-power-baseline.md
git commit -m "feat: spec #119 T1 uniqueness 纯形池过滤＋is_pure_chapter 谓词单源（replay↔门同引，FAIL 32→0）"
```

---

### Task 2: review 预算单源派生＋SKILL 措辞清偿

**复杂度: infra**（触 `pipeline/review_checklist.py`）· **test_kind: tdd_red_green** · 测试层级 T1 · 协调者亲自实现。

**Files:**
- Modify: `src/shenbi/pipeline/review_checklist.py`（:59-63 顶层加 `import math`；:361-366 函数级 import 块加 `from shenbi.gates.g4.chapter_drafting import TRANSITION_CAP_PER_1000`；:386 公式一行）
- Modify: `skills/shenbi-review-group-craft/SKILL.md:237`（措辞一行）
- Modify: `skills/shenbi-chapter-drafting/anti-ai-reference.md:22`（措辞一行）
- Test: `tests/unit/pipeline/test_review_checklist_precompute.py`（:25-29 re-pin＋:71-83 整测改写）

**Interfaces:**
- Consumes: `TRANSITION_CAP_PER_1000 = 1.0`（`src/shenbi/gates/g4/chapter_drafting.py:969`，T1 同文件已 import shared——函数级 import 无环：g4 chapter_drafting 模块闭包零 pipeline 引用）
- Produces: `transition_budget: int`（`ReviewChecklist` dataclass 既有字段——语义改为「首个失败计数」：转折计数 ≥ 预算即 ERROR；注入面 `"transition_budget"` dict 键不变，SKILL 消费方措辞同步）

- [ ] **Step 1: re-pin :25-29 失败（红）——分母测改派生锁**

```python
def test_transition_budget_uses_word_count_md_denominator(tmp_path: Path) -> None:
    _project(tmp_path)
    cl = generate_review_checklist(tmp_path, 2)
    wc = word_count_md(tmp_path / "chapters" / "chapter-2.md")
    from shenbi.gates.g4.chapter_drafting import TRANSITION_CAP_PER_1000

    expected = math.ceil(TRANSITION_CAP_PER_1000 * max(wc, 1) / 1000)
    assert cl.transition_budget == expected
```

（文件顶部测试既有 import 处补 `import math`；`word_count_md` 已 import。）
Run: `uv run pytest "tests/unit/pipeline/test_review_checklist_precompute.py::test_transition_budget_uses_word_count_md_denominator" -q`
Expected: FAIL —— fixture 章 wc≈3354：旧公式 5 vs 派生 ceil(3.354)=4

- [ ] **Step 2: re-pin :71-83 失败（红）——边界测改硬编码逐例**

整测替换（测名＋docstring 同步改派生口径）：

```python
def test_transition_budget_derived_from_cap_constant(tmp_path: Path) -> None:
    """spec #119 T2: budget = ceil(CAP×max(wc,1)/1000)，首个失败计数语义.

    派生自 TRANSITION_CAP_PER_1000 单源（G4 chapter_drafting）——旧绝对阈
    max(5, wc//1000) 退役（#118 T4 后口径失同步）。整千边界保守一格注记：
    wc=6000 预算 6，tc=6 → review ERROR 而 G4 PASS（密度恰=1.0 不越
    `>`）——保守向：门 FAIL 章必不漏过 review。
    """
    chapters = tmp_path / "chapters"
    chapters.mkdir(exist_ok=True)

    for n, chars in [(1, 999), (2, 1000), (3, 4999), (4, 6000), (5, 9000)]:
        (chapters / f"chapter-{n}.md").write_text("字" * chars, encoding="utf-8")
    for n, budget in [(1, 1), (2, 1), (3, 5), (4, 6), (5, 9)]:
        cl = generate_review_checklist(tmp_path, n)
        assert cl.transition_budget == budget
```

Run: `uv run pytest "tests/unit/pipeline/test_review_checklist_precompute.py::test_transition_budget_derived_from_cap_constant" -q`
Expected: FAIL —— 旧公式 wc=999/1000 得 5（max 下限）vs 新期望 1（`:82`/`:83` 断言形态已被本改写替换，红来自公式本身）

- [ ] **Step 3: 实现——公式派生**

`src/shenbi/pipeline/review_checklist.py`：
- `:59` `import json` 后插 `import math`（顶层，json/math/re 字母序）；
- `:361-366` 函数级 import 块（`from shenbi.gates.shared import (...)` 之后）加：

```python
    from shenbi.gates.g4.chapter_drafting import TRANSITION_CAP_PER_1000
```

- `:386` `transition_budget = max(5, wc // 1000)` →

```python
    transition_budget = math.ceil(TRANSITION_CAP_PER_1000 * max(wc, 1) / 1000)
```

（`max(wc, 1)` 镜像门侧 `chapter_drafting.py:998` `tc / max(ctx.wc, 1) * 1000` 护栏。）

- [ ] **Step 4: 红转绿＋文件级回归**

Run: `uv run pytest tests/unit/pipeline/test_review_checklist_precompute.py tests/unit/pipeline/test_review_checklist.py -q`
Expected: 全 PASS（`test_review_checklist.py` 的 :105/:117/:123/:143 为注入值构造测不触公式；:339 `> 0` 断言在新公式 wc=0 时 ceil(1×1/1000)=1 仍过）

- [ ] **Step 5: SKILL 措辞清偿（两处）**

`skills/shenbi-review-group-craft/SKILL.md:237` 整行替换：

```
4. 转折词密度 — 读注入 `transition_count`，对照 `transition_budget`（= G4 `TRANSITION_CAP_PER_1000` 派生：`ceil(CAP×max(wc,1)/1000)`；计数 ≥ 预算即 ERROR——预算为首个失败计数；单一阈值来源，spec #119 T2）
```

`skills/shenbi-chapter-drafting/anti-ai-reference.md:22` 整行替换：

```
转折词预算与 G4 同源（spec #119 T2 派生口径）：`ceil(TRANSITION_CAP_PER_1000 × max(章字数, 1) / 1000)`（word_count_md 计数；常量自 G4 单源派生，预算=首个失败计数），以下词合计 ≥ 预算即 ERROR，合法区为 < 预算：
```

- [ ] **Step 6: 契约面核验（纯散文预期零变更）**

Run: `uv run just lint-contracts`
Expected: PASS——两处改动均纯散文（无 reads/writes/decisions 变更；若报契约变更则回查——spec §3 风险预答面）

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/pipeline/review_checklist.py skills/shenbi-review-group-craft/SKILL.md skills/shenbi-chapter-drafting/anti-ai-reference.md tests/unit/pipeline/test_review_checklist_precompute.py
git commit -m "feat: spec #119 T2 review 转折预算单源派生（TRANSITION_CAP_PER_1000）＋SKILL/anti-ai-reference 措辞清偿"
```

---

## Self-Review 记录（writing-plans 步骤 3）

1. **Spec coverage**：T1 判据三面（①Step 2 ②Step 3 ③Step 3 改写体）＋50 章重跑（Step 7）＋baseline 核对（Step 8）；T2 re-pin 双测（:25-29 Step 1/:71-83 Step 2）＋SKILL/anti-ai 措辞（Step 5）＋lint-contracts（Step 6）；验收 2 diff 面=两 task Files 清单；验收 3 落阶段 7。无缺口。
2. **Placeholder scan**：无 TBD/「适当处理」类；所有代码步骤含真实代码与期望输出。
3. **Type consistency**：`is_pure_chapter(stem: str) -> bool` 三处一致（定义/T1 消费/replay 改引）；`TRANSITION_CAP_PER_1000` 常量名四处一致（定义 :969/T2 import/两 SKILL 措辞）；`transition_budget: int` 类型不变。
