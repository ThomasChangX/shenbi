# Spec #88 gate-finding-contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 must_fix finding 的「id 产生」收进单一契约——`G4.<id>` id-first 恒不变、分类改精确 id 匹配、check_id 单源、id 清单化防漂。

**Architecture:** 四类发射拓扑改写（(a) 分层契约不动/(b) 裸家族→id-first/(c) 纯中文→新 id/(d) 变量前缀→合法形态）由新 AST lint（首跑红清单=权威枚举）驱动收敛；`finding()` 发射器落 `gates/shared.py`；`_extract_check_id` 删除归一 `shadow.check_id`（含 tools 第三副本）；G4_CHECK_MAP 24 HARD 键+3 checks-only 键删除、匹配改点边界精确 id；inventory fixture+生成器双向防漂；floor 两发射面静态引用标注。

**Tech Stack:** Python 3.11+ / ast（lint）/ pytest + hypothesis（property）/ just（check 接线）。

**Spec:** `docs/superpowers/specs/2026-11-01-spec88-gate-finding-contract.md`（r2.8，七轮设计审查收敛终态——本 plan 直接消费其锚点，全部锚经轮 1-7 亲验）

## Global Constraints

- AGENTS.md：gate 检查器纯函数幂等；`src/shenbi/` 无 `print()`（structlog）；pathlib；Conventional Commits；pathspec commit（禁 `git add -A`）。
- G0.9：fixtures 只能是真实 skill 输出或构造的结构输入（`g4-id-inventory.json` 系生成器产物=inventory 类构造输入；对抗串 inline 合法）。
- 验证走 `just`/`uv run`（与 CI `uv run --frozen` 同构）。
- **lint 语法（spec §2 T1）**：合法形态 = `finding(...)` 调用 ｜ `"G4."` 开头 str 常量 ｜ JoinedStr 首常量段以 `"G4."` 开头；BinOp/`str.format`/`%` 不可判（登记残余）；跨函数间接登记残余（T5 运行时断言兜底）。
- **id charset 契约**：`[a-z0-9_][a-z0-9_.]*`（新代码必须满足）；shadow 提取器正则本批改 `[a-z0-9_.]+`（宽松于契约，无害）。**XC 大写豁免（plan 审查轮1 I2）**：`XC` 系历史大写家族前缀（G4_CHECK_MAP/GATE_TO_SHADOW_KEY 既有键即大写）——charset 谓词对家族段首 `XC` 豁免（其后缀段仍须 `[a-z0-9_.]+`）；提取走 split-colon fallback（正则不匹配大写→fallback 取首冒号段，产出正确）；spec-deviations 记录该豁免。
- **残余形态（本批不改写，登记挂账）**：genre_config `G4.gc.{文件名}`、character_design `G4.cd.archetype.{中文}[{i}]`（**经 `local_failures` 中转非 mf 直发——扫描域外**而非语法过）、volume_outlining `G4.vo.*[{中文卷头}]`、pacing_design `G4.pd.{loc}`；保守代理谓词：id 槽（首个 `:` 前）含非常量插值 **且非 (a)/(d) 已知合法变量形态** → 残余候选（代理会误扫 chapter_drafting :718-719/:757/:791/:814 等运行时合法变量 id 站点——登记时人工剔除，M4 口径）。
- **F947**：spec 全部验收离线可复验（结构断言/fixtures 回放/property），零真实 dispatch——无改写需求。
- **G3.4**：本 spec 无评分场景——不适用（声明）。
- 消息语义变更面（纯中文新 id、path-first 改写）＝模型可见 prompt 变化——spec §4 已声明排批次 A 殿后（已满足：束4 已验收）。

## 执行纪律（v7）

- 全部 task **infra** 级（gates/g4 域+pipeline 域+lint 基建）——**协调者亲自实现**，不分派 implementer。
- 每 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 全量重审）；无 audit-T<N> 不得开始 T<N+1>。
- 每 task commit 当轮更新 `spec-deviations.md` 的 `### T<N>` 段。
- 中间 commit 不 push；批末一次 push 走 PR。

---

### Task 1: `finding()` 发射器（gates/shared.py）

**Files:**
- Modify: `src/shenbi/gates/shared.py`（:583 `def fail(` 前——gate 级 helper 旁新增 item 级 helper）
- Test: `tests/unit/gates/test_g4_finding.py`（新建独立文件——M1 定死，不追加 test_shared.py）

**Interfaces:**
- Produces: `finding(check_id: str, detail: str = "", file: str = "") -> str`——恒产 `G4.<check_id>` 前缀串；slot 拼装 `G4.{check_id}:{file}:{detail}`（空槽收缩：file 空则 `G4.{check_id}:{detail}`；全空则 `G4.{check_id}`）。Task 3/4/5 的改写点消费它。

**复杂度:** infra ｜ **test_kind:** tdd_red_green ｜ **测试层级:** T1

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/gates/test_g4_finding.py
"""finding() emitter contract tests (spec #88 T1)."""

from shenbi.gates.shared import finding


class TestFindingEmitter:
    def test_id_only(self):
        assert finding("cd.no_hook") == "G4.cd.no_hook"

    def test_id_and_file(self):
        assert finding("cd.no_hook", file="chapters/ch001.md") == "G4.cd.no_hook:chapters/ch001.md"

    def test_full(self):
        assert finding("ss.facts_ops", detail="非法 op", file="truth/facts.md") == (
            "G4.ss.facts_ops:truth/facts.md:非法 op"
        )

    def test_id_and_detail_no_file(self):
        assert finding("cd.counter", detail="缺锚") == "G4.cd.counter:缺锚"

    def test_prefix_never_doubled(self):
        # 防 helper 无脑加前缀造 G4.G4.——传入已带前缀时先剥
        assert finding("G4.cd.title") == "G4.cd.title"
```

- [ ] **Step 2: 跑测确认红**

Run: `uv run pytest tests/unit/gates/test_g4_finding.py -v`
Expected: FAIL `ImportError: cannot import name 'finding'`

- [ ] **Step 3: 最小实现**（shared.py `fail` 定义之前插入）

```python
def finding(check_id: str, detail: str = "", file: str = "") -> str:
    """Emit a must_fix item string with the canonical ``G4.<id>`` prefix.

    spec #88 T1 single emission point: callers pass the BARE check id
    (``cd.no_hook``); a pre-prefixed input is stripped, never doubled.
    Slot layout ``G4.<id>:<file>:<detail>`` with empty slots collapsed.
    """
    if check_id.startswith("G4."):
        check_id = check_id[len("G4.") :]
    parts = [f"G4.{check_id}"]
    if file:
        parts.append(file)
    if detail:
        parts.append(detail)
    return ":".join(parts)
```

- [ ] **Step 4: 跑测确认绿**

Run: `uv run pytest tests/unit/gates/test_g4_finding.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/shared.py tests/unit/gates/test_g4_finding.py
git commit -m "feat: finding() must_fix emitter in gates/shared (spec #88 T1)"
```

---

### Task 2: AST 输出契约 lint 工具 + 首跑红清单落盘 + just 接线

**Files:**
- Create: `tools/lint_mustfix_emission.py`（样板=`tools/lint_truth_format_single_source.py` 头部结构）
- Modify: `justfile`（check 块 lint 面追加一行）
- 落盘: `.superpowers/sdd/lint-redlist-baseline.txt`（首跑红清单——(b)(c)(d) 权威枚举，工作态非交付物）

**Interfaces:**
- Produces: lint 工具 exit 0（0 违规）/ exit 1（违规清单到 stderr）；`--list` 模式打印红清单供对账。
- 扫描位：`src/shenbi/gates/g4/*.py` 中 `.append(...)`/`.extend(...)` 调用，当其**接收者名**为 `mf`（must_fix 列表惯例名——spec 全域 213 处实证）时的参数形态。
- 判定（spec 语法）：合法 = `finding(...)` Call ｜ Str 常量 `"G4."` 开头 ｜ JoinedStr 且首常量段 `"G4."` 开头 ｜ GeneratorExp（`mf.extend(f"..." for ...)`——element 同语法判定）。
- 豁免（AST 形态，无行锚）：`warns.append`/`c.append`（非 mf 接收者天然不扫）；残余形态家族不出红（genre_config/volume_outlining JoinedStr 首段已 "G4." 语法过；character_design 经 `local_failures` 中转在扫描域外——M4 口径）；**盲区登记进模块 docstring**：跨函数间接（mf.extend(变量)——变量来自 helper，state_settling ss. 批改写后仍属此盲区形态）与 BinOp/format/% 拼接不判定（与 lint_truth_format 同款登记惯例）。

**复杂度:** infra ｜ **test_kind:** tdd_red_green ｜ **测试层级:** T1

- [ ] **Step 1: 写失败测试**（工具存在性+判定表）

```python
# tests/unit/tools/test_lint_mustfix_emission.py
"""lint_mustfix_emission grammar unit tests (spec #88 T1)."""

import ast
from pathlib import Path

from tools.lint_mustfix_emission import is_legal_argument, REPO_ROOT


def _arg(src: str) -> ast.expr:
    # plan 审查轮1 I3：返回 Call 的**首实参**（is_legal_argument 保持纯表达式谓词）
    call = ast.parse(src.strip(), mode="eval").body
    assert isinstance(call, ast.Call)
    return call.args[0]


class TestGrammar:
    def test_finding_call_legal(self):
        assert is_legal_argument(_arg('mf.append(finding("cd.no_hook", file=fp))'))

    def test_g4_constant_legal(self):
        assert is_legal_argument(_arg('mf.append("G4.file_not_found:x")'))

    def test_joinedstr_g4_first_legal(self):
        assert is_legal_argument(_arg('mf.append(f"G4.{issue}")'))

    def test_joinedstr_path_first_illegal(self):
        assert not is_legal_argument(_arg('mf.append(f"{fp}:{issue}")'))

    def test_joinedstr_bare_family_illegal(self):
        assert not is_legal_argument(_arg('mf.append(f"cp.prop_decl:{fp}:x")'))

    def test_variable_prefix_illegal(self):
        assert not is_legal_argument(_arg('mf.append(f"{code_prefix}.not_found:{fp}")'))

    def test_generator_element_judged(self):
        assert is_legal_argument(_arg('mf.extend(f"G4.XC.x:{n}:{i}" for n, i in pairs)'))

    def test_binop_not_judged_registered_blind(self):
        # BinOp 形态不判（登记盲区）——返回 True（不报）但 docstring 登记
        assert is_legal_argument(_arg('mf.append("G4.a" + var)'))
```

- [ ] **Step 2: 跑测确认红**（工具不存在）

Run: `uv run pytest tests/unit/tools/test_lint_mustfix_emission.py -v`
Expected: FAIL ModuleNotFoundError

- [ ] **Step 3: 实现工具**（头部按 lint_truth_format 惯例：r-docstring 写扫描位/豁免/盲区登记；主体 ast.walk 找 Attribute `.append/.extend` on Name `mf`；`is_legal_argument` 按上表；`main()` 聚合违规输出 `file:line` + exit 码；`--list` 打印全集）

- [ ] **Step 4: 跑测确认绿**

Run: `uv run pytest tests/unit/tools/test_lint_mustfix_emission.py -v`
Expected: 8 passed

- [ ] **Step 5: 首跑红清单落盘 + 与 spec 站点表对账**

Run: `uv run python tools/lint_mustfix_emission.py --list > .superpowers/sdd/lint-redlist-baseline.txt; cat .superpowers/sdd/lint-redlist-baseline.txt`
Expected 红清单（AST 真值 10 站点）：chapter_drafting:683、chapter_planning:752、chapter_planning:758、cross_chapter:949、cross_chapter:982、scoring_sections:40、scoring_sections:45、scoring_sections:47、decisions_validator:106、decisions_validator:118。
**对账断言**：红清单 == spec (b)(cd:683/cp:752/cp:758/xc:949) + (c)(xc:982) + (d)(ss:40/:45/:47/dv:106/dv:118) 站点表——diff 为空。任何多出站点 = spec 枚举缺口 → 记 spec-deviations 并回补 spec 后继续。

- [ ] **Step 6: just check 接线**

justfile check 块（`lint_truth_format_single_source.py` 行后）追加：
```
    uv run python tools/lint_mustfix_emission.py
```
（本 task 时点该 lint 红——**不跑全套 just check**；批末 Task 8 后全绿。commit message 注明。）

- [ ] **Step 7: Commit**

```bash
git add tools/lint_mustfix_emission.py tests/unit/tools/test_lint_mustfix_emission.py justfile
git commit -m "feat: AST must_fix emission-contract lint + red-list baseline (spec #88 T1; red until T3-T5 land)"
```

---

### Task 3: (d) 变量前缀家族 5 站点改写 + scoring_sections 连带

**Files:**
- Modify: `src/shenbi/gates/g4/scoring_sections.py:40/:45/:47`（发射）+ `:49`（SKIP checks id 拼回）+ 模块头 `code_prefix` 实参语义注释
- Modify: `src/shenbi/gates/g4/decisions_validator.py:106/:117-119`
- Test: `tests/unit/gates/test_g4_score_checkers.py:18/:22/:26`（实参同步）+ `tests/unit/gates/g4/test_decisions_validator.py`（若无则追加到该域合适文件）

**Interfaces:**
- Consumes: Task 1 `finding()`。
- Produces: 改写后 must_fix 串**与改写前逐字节相同**（运行时零 delta——等价性由 characterization 测试钉死）；`G4_FORMAT_EXAMPLES` `G4.dec.*` 键（chapter_loop.py:939/:982/:987/:994/:1003）继续命中（id 文本逐字保留）。

**复杂度:** infra ｜ **test_kind:** characterization（改写前后输出逐字节等价）+ tdd_red_green（lint 面转绿）｜ **测试层级:** T1

- [ ] **Step 1: characterization 钉死改写前输出**（scoring_sections 三 prefix×not_found/no_route_c/no_route_a + decisions_validator 两 parse/pydantic 形态——对每形态断言完整串，如 `assert "G4.arc.not_found:ch1.md" in mf`）

- [ ] **Step 2: 跑测确认绿（改写前基线）**

- [ ] **Step 3: 改写**——
scoring_sections（`code_prefix` 实参从 `"G4.arc"` 族改 `"arc"` 族）：
```python
mf.append(f"G4.{code_prefix}.not_found:{fp}")
mf.append(f"G4.{code_prefix}.no_route_c:must have Route C section")
mf.append(f"G4.{code_prefix}.no_route_a:must have Route A anchor section")
...
c.append({"id": f"G4.{code_prefix}", "s": GateStatus.SKIP, "r": "no files"})
```
decisions_validator（id 逐字保留，走 finding 剥前缀语义）：
```python
mf.extend(finding(f["id"], file=fp, detail=f["r"]) for f in parse_failures)
mf.extend(
    finding(f["id"], file=fp, detail=f["r"]) for f in pydantic_err_to_gate_failures(e, fp, "G4.dec")
)
```
测试实参 :18/:22/:26 `"G4.arc"`/`"G4.vol"`/`"G4.str"` → `"arc"`/`"vol"`/`"str"`。

- [ ] **Step 4: 跑 characterization（仍绿=逐字节等价）+ lint 对应 5 红转绿**

Run: `uv run pytest tests/unit/gates/test_g4_score_checkers.py tests/unit/gates/g4/test_decisions_validator.py -v && uv run python tools/lint_mustfix_emission.py --list`
Expected: 测试全绿；红清单剩 5（cd:683/cp:752/cp:758/xc:949/xc:982——Task 4/5 对象）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/scoring_sections.py src/shenbi/gates/g4/decisions_validator.py tests/unit/gates/test_g4_score_checkers.py
git commit -m "refactor: (d)-family variable-prefix emissions to legal form, byte-identical output (spec #88 T1)"
```

---

### Task 4: (b) 裸家族改写 + retry_routing token + 有意修正记录

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:683`（path-first→分层契约形态）
- Modify: `src/shenbi/gates/g4/chapter_planning.py:752/:758`
- Modify: `src/shenbi/gates/g4/cross_chapter.py:949`
- Modify: `src/shenbi/gates/g4/state_settling.py`（**ss. 裸家族批——plan 审查轮1 C1 补**：helper 内 13 处 `f"ss.…"` → `f"G4.ss.…"（:838/:841/:878/:889/:904/:908/:921/:940/:961/:971/:996/:1000/:1013/:1019）；:434 warns 面不动；:1134 matrix_issues 形态实读核（非 ss. 前缀不改）——lint 盲区（跨函数间接）故红清单不含，以 `grep -n 'f"ss\.' state_settling.py` 双清单对账）
- Modify: `src/shenbi/pipeline/retry_routing.py:24`（token 增补）
- Test: `tests/unit/pipeline/test_spec83_retry_routing.py:24`（legacy 输入镜像更新）+ `tests/unit/pipeline/test_retry_routing_xc.py`（新建：XC 新形态 content 路由 + cd.prop_handoff 路由）+ 既有 ss. 断言测试同步（`grep -rln 'f\?"ss\.\|in i.*ss\.' tests/unit/gates/g4/` 命中面——实施时逐文件改期望串为 `G4.ss.` 前缀形态）

**Interfaces:**
- Produces: path-first 消灭——`G4.cd.prop_handoff` 项的 check_id 提取从 `"chapters/ch025.md"`（路径）修正为 `"cd.prop_handoff"`；`_CONTENT_TOKENS = ("G4.cd", "XC:", "G4.XC")`。
- 行为变化（**有意修正**，记入 spec-deviations 与测试断言）：①cd.prop_handoff 项新获 `"G4.cd"` content 路由（旧=other）；②lint 4 红转绿。

**复杂度:** infra ｜ **test_kind:** tdd_red_green ｜ **测试层级:** T1

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/pipeline/test_retry_routing_xc.py
"""retry_routing coupling for spec #88 emission-contract rewrites."""

from shenbi.pipeline.retry_routing import classify_retry_family


def test_prop_handoff_gains_content_routing():
    # 有意修正：path-first 消灭后按 G4.cd 前缀路由
    assert classify_retry_family("G4.cd.prop_handoff:chapters/ch025.md:「灯」交接语境") == "content"


def test_xc_new_form_routes_content():
    assert classify_retry_family("G4.XC.pronoun_mismatch:ch1.md:代词违例") == "content"


def test_legacy_xc_colon_form_still_routes_content():
    # legacy 字面保留（历史反馈 blob 兼容）
    assert classify_retry_family("XC:chapter-1.md:角色「X」…") == "content"


def test_check_id_extracts_family_not_path():
    from shenbi.gates.g4.shadow import check_id

    assert check_id("G4.cd.prop_handoff:「灯」交接语境") == "cd.prop_handoff"
```

- [ ] **Step 2: 跑测确认红**（`test_prop_handoff_gains_content_routing` 红——现产出 other；`test_check_id_extracts_family_not_path` 红——现 :683 产 path-first 串）

- [ ] **Step 3: 改写**——
chapter_drafting:683：`mf.append(f"{fp}:{issue}")` → `mf.append(f"G4.{issue}")`（与 :718-719 counter 族同构——helper 已返回 `cd.prop_handoff:…` 家族前缀串，调用点拼 G4. 即 id-first；fp 不入串，spec §1 file 槽不强制）。
chapter_planning:752/:758：`f"cp.prop_decl:{fp}:…"` → `f"G4.cp.prop_decl:{fp}:…"`。
cross_chapter:949：`f"XC.not_found:{fp}"` → `f"G4.XC.not_found:{fp}"`。
state_settling ss. 批（C1 补）：helper 内 13 处 `f"ss.…"` → `f"G4.ss.…"`（逐点机械替换；warns 面 :434 除外）。
retry_routing:24：`_CONTENT_TOKENS = ("G4.cd", "XC:", "G4.XC")`。
test_spec83_retry_routing:24 legacy `cp.prop_decl` 输入更新为新形态镜像（`G4.cp.prop_decl:…`，路由期望仍 "other"——非 cd 前缀）。

- [ ] **Step 4: 跑测确认绿 + lint 转绿核对 + ss. 对账**

Run: `uv run pytest tests/unit/pipeline/test_retry_routing_xc.py tests/unit/pipeline/test_spec83_retry_routing.py tests/unit/gates/g4/ -v && uv run python tools/lint_mustfix_emission.py --list && grep -c 'f"ss\.' src/shenbi/gates/g4/state_settling.py`
Expected: 测试全绿（g4 域含 ss. 期望串同步面）；红清单剩 1（xc:982）；grep `f"ss.` 计数仅剩 warns 面 1 处（:434）

- [ ] **Step 5: 更新既有断言**（grep `chapters/ch025.md:cd.prop_handoff` / `"{fp}:{issue}"` 于 tests/——若既有测试钉死 path-first 串，同批改为新形态；grep 自证零残留）

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py src/shenbi/gates/g4/chapter_planning.py src/shenbi/gates/g4/cross_chapter.py src/shenbi/gates/g4/state_settling.py src/shenbi/pipeline/retry_routing.py tests/unit/pipeline/test_retry_routing_xc.py tests/unit/pipeline/test_spec83_retry_routing.py
git commit -m "fix: (b)-family bare emissions to id-first (incl. ss. batch) + retry_routing G4.XC token; prop_handoff content-routing intentional (spec #88 T1)"
```

---

### Task 5: (c) 纯中文项新 id 全批 + 嵌套升格 + deviation 记录

**Files:**
- Modify: `src/shenbi/gates/g4/cross_chapter.py`（issues 构造点 :625/:672/:684/:695/:705/:706/:714/:759/:790/:808/:825/:849/:860 + 包装点 :982）
- Test: `tests/unit/gates/g4/test_cross_chapter_ids.py`（新建）
- Test（连带——plan 审查轮1 C2 补）：`tests/unit/gates/g4/test_xc_pov_name.py`、`test_xc_prop_card.py`、`test_xc_assets.py`、`test_xc_timeline.py`、`test_xc_regression.py`、`test_cross_chapter_skeleton.py`、`test_f15_narration_name.py`、`tests/gates/test_invariant_mutants.py`（tuple/新 id 形态断言同步——`"substring" in i` 对 tuple 是成员判定非子串，~25 断言改写）

**Interfaces:**
- Produces: cross_chapter issues 元素从裸中文串改为 `(id, detail)` 二元组；包装点产 `G4.XC.{id}:{ch_path.name}:{detail}`。新 id 清单（spec §1.1 r2.7 定稿）：`pronoun_mismatch`(:672)/`title_violation`(:705)/`org_drift`(:684)/`residence_drift`(:695)/`reserved_name_hijack`(:706 经 reserved_name_hijack_hits——其返回形态按实际核)/`prop_chain_origin`(:759)/`prop_undeclared`(:790)/`pov_break`(:808)/`timeline_rollback`(:825)/`balance_jump`(:849/:860 双臂合一 id)＋嵌套 `narration_name`(:625——detail 剥内层前缀)。
- 语义变更（deviation 记录）：must_fix 文本模型可见面变化（`XC:ch1.md:中文` → `G4.XC.<id>:ch1.md:中文`）。

**复杂度:** infra ｜ **test_kind:** tdd_red_green ｜ **测试层级:** T1

- [ ] **Step 1: 写失败测试**（对 11 个 check 各一构造输入断言 `G4.XC.<id>:` 前缀完整形态；嵌套项断言 `G4.XC.narration_name:ch1.md:叙述段出现别名…` 且 detail 无内层前缀残留；`reserved_name_hijack_hits` 返回形态按实读代码定断言）

- [ ] **Step 2: 跑测确认红**

- [ ] **Step 3: 改写**——issues.append 改二元组 `("pronoun_mismatch", f"角色「{name}」正文用「她」而卡为男性代词（修复者: 卡修/settling）")` 形态；:625 `("narration_name", f"叙述段出现别名「{alias}」…")`（剥内层 `XC.narration_name:` 前缀）；:982 `mf.extend(f"G4.XC.{cid}:{ch_path.name}:{det}" for cid, det in issues)`。**实施中逐点核形态**：若某点现构造非裸中文（如 :714 extend 别的形态），按实读改并记 deviation。

- [ ] **Step 4: 跑测确认绿 + lint 全绿 + 连带族回归**

Run: `uv run pytest tests/unit/gates/g4/test_cross_chapter_ids.py tests/unit/gates/g4/test_xc_pov_name.py tests/unit/gates/g4/test_xc_prop_card.py tests/unit/gates/g4/test_xc_assets.py tests/unit/gates/g4/test_xc_timeline.py tests/unit/gates/g4/test_xc_regression.py tests/unit/gates/g4/test_cross_chapter_skeleton.py tests/unit/gates/g4/test_f15_narration_name.py tests/gates/test_invariant_mutants.py -v && uv run python tools/lint_mustfix_emission.py`
Expected: 全绿（C2 连带族同步后）；lint exit 0（10/10 红点清零——(b)(c)(d) 全消化）

- [ ] **Step 5: spec-deviations 记 `### T5`（新 id 全清单+文本变更声明）**

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/gates/g4/cross_chapter.py tests/unit/gates/g4/test_cross_chapter_ids.py tests/unit/gates/g4/test_xc_pov_name.py tests/unit/gates/g4/test_xc_prop_card.py tests/unit/gates/g4/test_xc_assets.py tests/unit/gates/g4/test_xc_timeline.py tests/unit/gates/g4/test_xc_regression.py tests/unit/gates/g4/test_cross_chapter_skeleton.py tests/unit/gates/g4/test_f15_narration_name.py tests/gates/test_invariant_mutants.py
git commit -m "feat: machine ids for all pure-Chinese XC findings + nested promotion; xc test family synced (spec #88 T1c, model-visible text change recorded)"
```

---

### Task 6: check_id 单源（删 `_extract_check_id` + tools 第三副本换源 + 正则含数字 + stale 注释清偿）

**Files:**
- Modify: `src/shenbi/gates/g4/shadow.py:64`（正则 `[a-z0-9_.]+`）+ `:24-25`（stale 注释改写）
- Modify: `src/shenbi/pipeline/chapter_loop.py:873-876`（删除）+ `:4702`（改 `from shenbi.gates.g4.shadow import check_id` 后调用）+ `:1206`（docstring 引用改写）
- Modify: `tools/lint_shadow_promotion.py:74`（换源：先剥 `[shadow] `/`[shadow]` 前缀再 `check_id(item)`——M5：旧 pattern 的无括号 `shadow?` 容忍度随删，唯一产者 shadow.py:84 恒产带括号形，安全；`gate_id.split(".")[-1] in mf` 相邻启发**不动**仅注释）
- Test: `tests/unit/gates/g4/test_shadow_demotion.py:46-48`（数字 id 断言追加）

**Interfaces:**
- Produces: 全仓唯一 `G4\.` id 提取正则 owner = `shadow.check_id`（`[a-z0-9_.]+`）；数字 id 完整提取（`G4.cc.p1p2_empty` → `cc.p1p2_empty`）。

**复杂度:** infra ｜ **test_kind:** tdd_red_green ｜ **测试层级:** T1

- [ ] **Step 1: 写失败测试**（追加进 test_shadow_demotion.py）：

```python
def test_check_id_digit_ids_not_truncated() -> None:
    assert check_id("G4.cc.p1p2_empty:ctx.md") == "cc.p1p2_empty"
    assert check_id("G4.cp.s7_hook_ops:plan.md") == "cp.s7_hook_ops"


def test_extract_check_id_gone_single_owner() -> None:
    import shenbi.pipeline.chapter_loop as cl

    assert not hasattr(cl, "_extract_check_id")
```

（soft-tracker 行为等价由既有 test_g4_classification/test_soft_fail_tracker 族守护——:4702 换源后跑全量相关。）

- [ ] **Step 2: 跑测确认红**（数字断言红——现截成 `cc.p`/`cp.s`）

- [ ] **Step 3: 改写**——shadow.py:64 `re.match(r"G4\.([a-z0-9_.]+)", item)`；:24-25 注释「the `_extract_check_id` shape」改「the must_fix `G4.<id>:…` shape」；chapter_loop 删 :873-876、:4702 `tracker_key = check_id(s)`（文件头或函数内 import——按 chapter_loop import 惯例就地 `from shenbi.gates.g4.shadow import check_id`）；:1206 docstring 改指 shadow.check_id；lint_shadow_promotion:74 区域改 `item` 先 `re.sub(r"^\[shadow\]\s*", "", item)` 再 `check_id(stripped)`（双 pattern 副本删除）。

- [ ] **Step 4: 跑测确认绿 + 全仓唯一性 grep**

Run: `uv run pytest tests/unit/gates/g4/test_shadow_demotion.py tests/unit/pipeline/test_g4_classification.py -v && grep -rn 'G4\\.(\[' src/ tools/ | grep -v shadow.py`
Expected: 测试绿；grep 仅 shadow.py:64 一处（唯一 owner 证据）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/shadow.py src/shenbi/pipeline/chapter_loop.py tools/lint_shadow_promotion.py tests/unit/gates/g4/test_shadow_demotion.py
git commit -m "refactor: check_id single owner in shadow (digit-safe regex); drop _extract_check_id + tools copy (spec #88 T2)"
```

---

### Task 7: 分类精确 id 匹配 + 键删除 + inventory fixture/生成器/三断言 + property test + 连带测试

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:812-848`（G4_CHECK_MAP 瘦身至 2 活键）+ `:851-870`（_classify_g4_failures 精确匹配）
- Create: `tools/gen_g4_id_inventory.py`（生成器：AST 枚举 mf 发射面 id → `tests/fixtures/g4-id-inventory.json`）
- Create: `tests/fixtures/g4-id-inventory.json`（生成器产物——inventory 类构造输入，G0.9 合规）
- Test: `tests/property/gates/test_g4_id_inventory.py`（新建：三断言 + hypothesis property）+ `tests/unit/pipeline/test_g4_classification.py`（:22-26/:28-29/:39-50 改写）

**Interfaces:**
- Consumes: Task 6 `check_id`（含数字）。
- Produces: `G4_CHECK_MAP` 仅 2 活键 `{"transition": SOFT, "fatigue": SOFT}`；`_classify_g4_failures` 匹配 `cid == key or cid.startswith(key + ".")`；inventory JSON `{"ids": [...], "generated_at": "<iso>", "generator": "tools/gen_g4_id_inventory.py"}`。
- 有意修正（记 deviation+测试钉死）：`cd.post_transition_cross` 从 SOFT 误判改 HARD（promoted 项从 soft-tracker 3-in-window 改立即 HARD 重试）。

**复杂度:** infra ｜ **test_kind:** tdd_red_green + regression_guard（行为不回归表）｜ **测试层级:** T1 + property

- [ ] **Step 1: 写失败测试**——
unit（test_g4_classification 改写）：
```python
def test_only_two_active_keys():
    assert set(G4_CHECK_MAP) == {"transition", "fatigue"}


def test_exact_match_not_substring():
    hard, soft, warn = _classify_g4_failures(["G4.cd.post_transition_cross:p:t"])
    assert len(hard) == 1 and not soft  # 有意修正：旧子串误判 SOFT


def test_dot_boundary_prefix():
    _, soft, _ = _classify_g4_failures(["G4.transition.density:p:8>7"])
    assert len(soft) == 1  # 真前缀族仍 SOFT


def test_unknown_defaults_hard():
    hard, soft, warn = _classify_g4_failures(["G4.future.check:p:x"])
    assert len(hard) == 1
```
property（三断言+不变量）：
```python
# tests/property/gates/test_g4_id_inventory.py
INV = json.loads(Path("tests/fixtures/g4-id-inventory.json").read_text())
IDS = set(INV["ids"])


def test_retained_keys_in_inventory():
    from shenbi.pipeline.chapter_loop import G4_CHECK_MAP

    assert set(G4_CHECK_MAP) <= IDS


def test_inventory_subset_of_ast_enumeration():
    # 反向防漂：生成器重跑产出 ⊆ 现树枚举（stale id 即红）
    from tools.gen_g4_id_inventory import enumerate_ids

    assert IDS <= set(enumerate_ids())


@given(st.sampled_from(sorted(IDS)))
def test_any_id_extractable_roundtrip(cid):
    from shenbi.gates.g4.shadow import check_id

    assert check_id(f"G4.{cid}:f:d") == cid


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_.", min_size=1, max_size=16))
def test_softwarn_implies_covered(seed):
    # property 主不变量：任何被判 SOFT/WARN 的 item，其 extracted id ∈ 覆盖键集
    # （alphabet 全集含 t/u 与点——hypothesis 可生成 "transition"/"fatigue"/"transition.x"
    #   命中 SOFT 臂，断言循环体非平凡执行；plan 审查轮1 I1 修正空测）
    from shenbi.pipeline.chapter_loop import _classify_g4_failures

    item = f"G4.{seed}:f:d"
    _, soft, warn = _classify_g4_failures([item])
    for out in (soft, warn):
        for it in out:
            fam = it.split(":", 1)[0][len("G4.") :]
            assert (
                fam == "transition"
                or fam == "fatigue"
                or fam.startswith(("transition.", "fatigue."))
            )
```

- [ ] **Step 2: 跑测确认红**（现 29 键/子串匹配全红）

- [ ] **Step 3: 改写**——G4_CHECK_MAP 收缩为 2 键（删 24 HARD+3 checks-only，删除处注释「severity 由发射点 checks[].s 携带（chapter_drafting:1093、chapter_planning:909/:1000/:1007）；未匹配默认 HARD（:868-869）与显式 HARD 等价」）；`_classify_g4_failures` 内层改 `cid = check_id(item)` + `if cid == key or cid.startswith(key + "."):`；写 `tools/gen_g4_id_inventory.py`——**enumerate_ids() 单函数三源（M2）**：①AST 枚举 mf 发射面常量 id 段 ②xc 二元组 `(cid, det)` 形态（Task 5 后的新形态）③变量前缀/分层契约补遗清单（`cd.post_transition_cross`/`cd.balance_value_drift`/counter 族等 AST 不可见 id——显式列表进生成器源码，注释来源锚）；`--write` 落 fixture，测试侧 import 同一函数（生成器只读不写）；生成并提交 `g4-id-inventory.json`。Task 8 豁免基线 = 该 fixture（补遗含变量形态活 id——防 `cd.post_transition_cross` 类被机械误判死 id，r2.7 missing_chapter_role 教训）。

- [ ] **Step 4: 跑测确认绿 + cold_opening 不破确认**

Run: `uv run pytest tests/unit/pipeline/test_g4_classification.py tests/property/gates/test_g4_id_inventory.py tests/unit/gates/g4/test_cold_opening_triple.py -v`
Expected: 全绿（cold_opening `not in G4_CHECK_MAP` 断言恒真不破）

- [ ] **Step 5: spec-deviations 记 `### T7`（post_transition_cross 有意修正+运行时 delta）**

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/pipeline/chapter_loop.py tools/gen_g4_id_inventory.py tests/fixtures/g4-id-inventory.json tests/property/gates/test_g4_id_inventory.py tests/unit/pipeline/test_g4_classification.py
git commit -m "feat: exact-id severity matching, 24+3 dead keys deleted, id inventory + bidirectional property invariants (spec #88 T3)"
```

---

### Task 8: T4 floor 两处静态引用标注 + dedup 断言 + T5 全 checker 参数化 + 批末终验

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_drafting.py:887`（word_count 消息加 floor 来源）
- Modify: `src/shenbi/gates/g4/length_normalizing.py:53`（below_floor 同）
- Test: `tests/unit/gates/g4/test_word_floor_citation.py`（新建红测）+ `tests/property/gates/test_shadow_all_checkers.py`（T5 参数化）

**Interfaces:**
- Produces: 两处消息 detail 含 `chapter_word_floor` 静态函数引用（名+当前值，如 `（floor 来源: chapter_word_floor=3200）`）；T5 参数化语料=per-checker 单测构造输出聚合 + fixture 真实 must_fix（bracketed-list-only 解析）+ 死 id 豁免集机械推导（fixture 语料 id − AST inventory；已知真死：`G4.fp.no_hooks`、`G4.rr.*` 族、`G4.rules.count`、`G4.protag.yaml_error`、`G4.ss.no_hook_state` 等按推导结果定——豁免项仅走「等于期望 id」分支）。

**复杂度:** infra ｜ **test_kind:** tdd_red_green（floor 引用红测）+ regression_guard（T5 参数化套件 born-green——Tasks 3-7 已落地，M3 口径）｜ **测试层级:** T1 + property

- [ ] **Step 1: 写失败测试**——floor 引用红测：
```python
def test_word_count_message_cites_floor_source(...):
    # 构造 under-floor 章节文件 → 跑 g4_chapter_drafting → 断言 must_fix 项含 "chapter_word_floor"
def test_ln_below_floor_cites_floor_source(...):
    # length_normalizing 同构断言
```
T5 参数化（test_shadow_all_checkers.py）：parametrize over「per-checker 单测构造输出聚合 + fixture 语料」，断言 `check_id(item) == expected or check_id(item) ∈ inventory`；豁免集在文件头由机械推导表达式生成（fixture 解析函数只取 `G4 ... check failed: [...]` 方括号段）。

- [ ] **Step 2: 跑测确认红**

- [ ] **Step 3: 改写**——两处消息 `f"G4.word_count:{fp}:{total}<{floor}（floor 来源: chapter_word_floor={floor}）"` / `f"G4.ln.below_floor:{fp}:{wc}<{floor}（floor 来源: chapter_word_floor={floor}）"`；:2230/volume_budget/chapter_loop:1779 **不动**（spec 排除面）。

- [ ] **Step 4: 跑测确认绿 + dedup diff 断言 + 批末终验**

Run:
```
uv run pytest tests/unit/gates/g4/test_word_floor_citation.py tests/property/gates/test_shadow_all_checkers.py -v
git diff main -- src/shenbi/gates/ | grep -c "dedup"   # expect 0（零新增 dedup 逻辑）
uv run python tools/lint_mustfix_emission.py            # exit 0
just check                                              # exit 0（全套）
```
Expected: 全绿（just check 完整输出粘 progress.md）

- [ ] **Step 5: Commit**

```bash
git add src/shenbi/gates/g4/chapter_drafting.py src/shenbi/gates/g4/length_normalizing.py tests/unit/gates/g4/test_word_floor_citation.py tests/property/gates/test_shadow_all_checkers.py
git commit -m "feat: floor-source citations + all-checker check_id parameterization (spec #88 T4+T5)"
```

---

## 验收覆盖表（spec §3 → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1. lint 绿（AST 面 0 违规）；纯中文新 id 已记 deviation | T2 接线+T3/T4/T5 消化 | `uv run python tools/lint_mustfix_emission.py` exit 0；spec-deviations `### T5` |
| 2. _extract_check_id 唯一定义（shadow；lint 工具换源）；数字正则红测；T5 参数化（213 面 checker 全集+死 id 豁免机械推导）；retry 锚 :1372 | T6+T8 | test_shadow_demotion 数字断言绿；grep 唯一 owner；test_shadow_all_checkers 参数化计数=checker 全集 |
| 3. 恰 2 活键+3 checks-only 删除；inventory 三断言；post_transition_cross 有意修正（含运行时 delta） | T7 | test_only_two_active_keys+property 三断言+deviation `### T7` |
| 4. property test 绿；两处 floor 静态引用红测；dedup diff 级断言；G4.XC token+用例；test_spec83:24 镜像 | T4+T7+T8 | pytest 全绿；`git diff main -- src/shenbi/gates/ \| grep -c dedup`=0 |
| 5. just check exit 0 | T8 批末 | `just check` 完整输出 |

## Self-Review 记录

- Spec 覆盖：T1(a)(不动)+T1(b)(T4——**含 state_settling ss. 批**，plan 审查轮1 C1 补)+T1(c)(T5)+T1(d)(T3)+lint(T2)+finding(T1)｜T2 全(T6)｜T3 全(T7)｜T4 全(T8 前半)｜T5 全(T8 后半)——§3 五条全覆盖 ✓
- 类型一致：`finding(check_id, detail, file)` 全 plan 统一；`check_id(item) -> str` 与 shadow 现签名一致 ✓
- 占位扫描：无 TBD/「适当处理」类残留；(c) 家族 :714/:706 形态标注「按实读核」——实施中逐点核（spec 已授权 plan 期机械枚举定稿）✓
- **Plan 审查轮 1 修订记录**（2🔴3🟡5🟢 全吸收）：C1 ss. 批并入 Task 4（spec T1(b) prose vs r2.8 红清单矛盾——采纳改写路线非 deviation）；C2 Task 5 连带测试族 8 文件扩入 Files/Step 4/commit；I1 property alphabet 修空测；I2 XC 大写豁免句；I3 `_arg` 返 `.args[0]`；M1-M5 全吸收（test 文件定死/enumerate_ids 三源/test_kind 拆分/残余描述口径/[shadow] 注释）
