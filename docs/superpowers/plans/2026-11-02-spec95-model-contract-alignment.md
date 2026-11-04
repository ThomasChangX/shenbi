# Spec #95 模型契约对齐与上下文预算 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 spec #95 r1.6 六任务 T1-T6——gate 词表⇄prompt 单源、卷期热协议参数下沉、settle 读面升格分窗+预算、失败反馈改操作路径、草写长度锚定+束级早检、修订 diff 化+检查点所有权对称。

**Architecture:** 全部为既有机制升格/接线（extractor 体系、shadow 通道、TARGETED-EDIT 通道、append_dedup 特判），新建仅四件：枚举常量单源、matrix 定向提取器、settle 专属总预算、场景级 patch applier。**全部 infra**——`pipeline/`、`gates/g4/`、`contracts/` 域，按 leaf/infra 分流规则**协调者亲自实现**，逐 task TDD + fresh-context audit。

**Tech Stack:** Python 3.11+ / pathlib / re.MULTILINE 锚定 / structlog / pytest（just test 同构 CI）。

**Spec:** `docs/superpowers/specs/2026-11-02-spec95-model-contract-alignment.md`（r1.6，commit 90a7e615）

## Global Constraints

- 每task 首步 **re-anchor**：spec 行号为 2026-11-04 快照，执行时以符号名重定位（INDEX 行号锚纪律）；漂移记 progress.md。
- gate 检查器纯函数幂等、无副作用；`src/shenbi/` 无 `print()`（structlog）；状态字面量唯一定义 `contracts/enums.py`。
- fixtures 只能是真实产物副本（G0.9）：00189 blob 固化件带源 sha256 注释头，禁手造。
- 契约 reads/writes 变更后跑 `just generate`（deps.json/docs/skills 三源同步，diff 须空）。
- 环境同构：验证一律 `just`/`uv run`；禁真实 dispatch（核心原则 8）。
- **F947 声明**：验收 3/4 的束4 实弹重跑=**合并后生产验收窗**（#84 Task 10 解冻条件，用户令下执行）；本 plan 的 SDD PR 交付 T1-T6 实现+离线测试面（验收 1/2/5）。**G3.4 声明**：PR 内无 LLM 产物评分验收，不涉独立评分子 agent；束4 窗内评分按现行 G3.4 协议另起。

**test_kind 总表**：Task 1/2/3/4/5/7/8/9/10/11/12/14 = `tdd_red_green`；Task 6 = fixture 固化（哈希+快照断言，`regression_guard`）；Task 13 = `tdd_red_green`（applier）+ `characterization`（append_dedup 既有行为先钉）。

---

### Task 0: Re-anchor 基线（无代码）

**Files:** 无（只读核对，产出记 `.superpowers/sdd/progress.md`）

- [ ] **Step 1**: 对 spec 全部行号锚跑符号级重定位（`grep -n` 符号名），漂移表记 progress.md「阶段 6 · Task 0」。重点：chapter_planning.py:749/:125、context_assemble.py:39-44/:110-113/:255、cli.py:676/:718、dispatch_helper.py:316/:398-400/:447/:903/:1082/:1458、state_settling.py:182-187、shadow.py:28-58、read_extractors.py:92/:352、chapter_loop.py:804-836/:1164/:1178-1232/:1625-1632/:1753-1760、enums.py:43、ownership.py:41、SKILL.md:158/:223（planning）/:149-151（drafting）/:107-109（resonance）。
- [ ] **Step 2**: `just check` 基线全绿（截图输出进 progress.md）。

---

### Task 1: 枚举常量单源（T1 前置 · 修 R1 词表源头）

**Files:**
- Modify: `src/shenbi/contracts/enums.py`（WriteMode Literal :43 邻近新增节）
- Test: `tests/unit/contracts/test_enums_spec95.py`（新建）

**Interfaces:**
- Produces: `CHAPTER_ROLE_VALUES: tuple[str, ...] = ("高潮","兑现","推进","转折","过渡","铺垫")`；`GOLDEN_LINE_VALUES: tuple[str, ...] = ("燃","静")`；`CHECK_ENUM_REGISTRY: dict[str, tuple[str, str]]`——check_id → (常量名, SKILL 仓库相对路径 str)，Task 4 lint 与 Task 2 gate 共读（lint 自 repo root 运行）。后续 task 以 `from shenbi.contracts.enums import CHAPTER_ROLE_VALUES` 消费。
- 复杂度: **infra**（contracts 域，跨 4 消费方）· test_kind: tdd_red_green · 层级: T1 单测

- [ ] **Step 1: 红测**

```python
# tests/unit/contracts/test_enums_spec95.py
"""spec #95 T1: 枚举常量单源——gate/lint/context_assemble 共读（R1 斜杠病根）。"""
from shenbi.contracts.enums import CHAPTER_ROLE_VALUES, GOLDEN_LINE_VALUES, CHECK_ENUM_REGISTRY

def test_chapter_role_values_single_only():
    assert CHAPTER_ROLE_VALUES == ("高潮", "兑现", "推进", "转折", "过渡", "铺垫")
    assert all("/" not in v for v in CHAPTER_ROLE_VALUES)  # 单值铁律（禁斜杠分组形）

def test_golden_line_values_cover_current_regex_domain():
    # 现 chapter_planning.py:125 只编码 燃；GOLDEN_LINE_VALUES 至少含 燃/静（R3 冷三连用 静）
    assert set(("燃", "静")).issubset(set(GOLDEN_LINE_VALUES))

def test_check_enum_registry_covers_chapter_role():
    assert "cp.chapter_role" in CHECK_ENUM_REGISTRY
    const_name, skill_rel = CHECK_ENUM_REGISTRY["cp.chapter_role"]
    assert const_name == "CHAPTER_ROLE_VALUES"
    assert skill_rel.endswith("chapter-planning/SKILL.md")
```

- [ ] **Step 2**: `uv run pytest tests/unit/contracts/test_enums_spec95.py -v` → FAIL（ImportError）。
- [ ] **Step 3**: enums.py 新增（实际代码）：

```python
# --- spec #95 T1: gate 词表 ⇄ prompt 单源（R1：SKILL 斜杠分组形教错模型） ---
# 值域只收单值；斜杠/多值形由 gate 锚尾判定拒（G4.cp.invalid_chapter_role）。
CHAPTER_ROLE_VALUES: tuple[str, ...] = ("高潮", "兑现", "推进", "转折", "过渡", "铺垫")
GOLDEN_LINE_VALUES: tuple[str, ...] = ("燃", "静")

# 有枚举判定的检查 → (常量名, SKILL 相对路径)；lint_gate_prompt_contract 从此派生，
# 禁手列函数清单（r1.5：手列即计数腐化源）。
CHECK_ENUM_REGISTRY: dict[str, tuple[str, str]] = {
    "cp.chapter_role": ("CHAPTER_ROLE_VALUES", "skills/shenbi-chapter-planning/SKILL.md"),
}
```

- [ ] **Step 4**: 跑测 PASS → `just lint-contracts` 绿。
- [ ] **Step 5**: Commit `feat: spec95 T1 enum constants single source (CHAPTER_ROLE_VALUES/GOLDEN_LINE_VALUES/CHECK_ENUM_REGISTRY)` + audit-T1.md。

---

### Task 2: gate 锚尾判定 + 独立 must_fix id（T1 · 修 R1 拦截面）

**Files:**
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（:749 内联 regex 替换）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（G4_CHECK_MAP :804-836 注册新 id）
- Test: `tests/unit/gates/g4/test_chapter_planning_role.py`（:133-142 翻转+新增）
- Test/fixture 更新: `tests/fixtures/chapter-plan-example.md:18`、`tests/fixtures/spec82/plans/chapter-2-plan.md:7`、`chapter-36-plan.md:7`、`tests/fixtures/spec83/plans/chapter-1-plan.md:7`、`chapter-28-plan.md:7`（斜杠→单值）；`tests/unit/gates/g4/test_chapter_planning.py:132` 构造行同步

**Interfaces:**
- Consumes: Task 1 `CHAPTER_ROLE_VALUES`。
- Produces: `G4.cp.invalid_chapter_role`（**一切非规范在场值**：斜杠/空格多值/`无效` 等一律此 id）；`missing_chapter_role` 语义收窄为「键不存在」。gate 内新正则模块级常量 `_ROLE_LINE_RE`。**判定语义（plan 审查 C1 修正）**：`finditer` 全量收集在场值行——零行→missing；任一行值∉CHAPTER_ROLE_VALUES→invalid（**混合行不豁免**：示例正例行+斜杠行并存仍 FAIL）；全规范→PASS。
- 复杂度: **infra** · tdd_red_green · T1

- [ ] **Step 1: 红测**（新增+翻转；按 test 文件既有 `_run`/`_valid_plan_raw_role_line` 帮手形态接线）

```python
def test_slash_form_rejected_not_passed():
    # 构造 plan：chapter_role: 推进/转折 → must_fix 含 invalid_chapter_role（现前缀匹配放行=红）

def test_mixed_canonical_and_slash_still_fails():  # C1 混合行（示例正则被抄进 plan 的 R1 失败类）
    # plan 同时含 `chapter_role: 推进`（示例行）与 `chapter_role: 推进/转折`（实声明行）→ FAIL invalid

def test_space_separated_multi_value_fails_invalid():  # C1 次生：空格多值不得塌缩 missing
    # `chapter_role: 推进 转折` → invalid_chapter_role（非 missing）

def test_fullwidth_colon_single_value_passes():  # 全角变体（先例 :71-74 语义并入锚尾）

def test_invalid_present_value_gets_invalid_id_not_missing():  # 翻转 :133-142（无效→invalid 非 missing）
```

- [ ] **Step 2**: 跑测 FAIL（现前缀匹配放行斜杠）。
- [ ] **Step 3**: 实现（chapter_planning.py 替换 :749 块）：

```python
from shenbi.contracts.enums import CHAPTER_ROLE_VALUES
# spec #95 T1: 锚尾单值判定——前缀匹配曾放行 `推进/转折`（R1 加重发现，协调者复现）。
# finditer 全量收行：混合行（示例+斜杠）不豁免（plan 审查 C1）。
_ROLE_LINE_RE = re.compile(r"^chapter_role\s*[:：]\s*(?P<val>.+?)\s*$", re.MULTILINE)

# in checker:
_vals = [m.group("val").strip() for m in _ROLE_LINE_RE.finditer(content)]
_canon = set(CHAPTER_ROLE_VALUES)
if not _vals:
    mf.append(f"G4.cp.missing_chapter_role:{fp}")  # 键不存在
elif any(v not in _canon for v in _vals):
    bad = next(v for v in _vals if v not in _canon)
    mf.append(f"G4.cp.invalid_chapter_role:{fp}:{bad!r}")  # 在场非规范（斜杠/空格多值/无效）
else:
    c.append({"id": "G4.cp.chapter_role", "file": fp, "s": GateStatus.PASS})
```

chapter_loop `G4_CHECK_MAP` 增 `"invalid_chapter_role": G4Severity.HARD`（G4Severity 为 StrEnum：HARD/SOFT/WARN，chapter_loop.py:788±；**不入** GATE_TO_SHADOW_KEY——未列即保 HARD fail-safe，正确）。
- [ ] **Step 4**: 5 fixtures 斜杠→单值（保语义：`高潮/兑现`→取该章实际档位单值——spec82 ch2/ch36 为高潮档→`高潮`；`推进/转折`→`推进`；`过渡/铺垫`→`过渡`）；test_chapter_planning.py:132 构造行同改；全测 PASS。
- [ ] **Step 5**: Commit `feat: spec95 T1 anchored-tail chapter_role gate + invalid_chapter_role id`——**commit message 附契约升级 no-impact 声明**（现役 42 plan 中 35 斜杠：G4 只检 staged 派发产物、ch1-36 盘面不重检；live-plan 预算面由 Task 3 别名覆盖）+ audit-T2.md。

---

### Task 3: BUDGET_BY_ROLE 换键 + 别名 + 三面对齐（T1 · 修 live wire）

**Files:**
- Modify: `src/shenbi/pipeline/context_assemble.py:39-44`（BUDGET_BY_ROLE）+ `:255`（get 链不变）
- Modify: `skills/shenbi-chapter-drafting/SKILL.md:149-151`、`skills/shenbi-review-resonance/SKILL.md:107-109`（表单值化）
- Modify: `tests/tiers/t1-skill/shenbi-review-resonance/rubric.md:17`、`generative/input/scenario.md:9,:19,:24`（tier 面同批对齐）
- Test: `tests/unit/pipeline/test_context_assemble.py:51-54/:129-141`（改写+新增）

**Interfaces:**
- Consumes: `CHAPTER_ROLE_VALUES`（经 `_BUDGET_BY_GROUP` 档位映射派生）。
- Produces: `BUDGET_BY_ROLE` 键=单值+3 旧斜杠兼容别名（束4 后可清）；`DEFAULT_BUDGET=12000` 不变。
- 复杂度: **infra** · tdd_red_green · T1

- [ ] **Step 1: 红测**

```python
def test_single_value_plan_gets_tier_budget():
    plan = "...chapter_role: 高潮\n..."  # 单值（Task 2 后的正向形态）
    assert _parse_chapter_role→BUDGET_BY_ROLE 链产出 18000  # 现状: .get("高潮") miss→12000 红

def test_legacy_slash_alias_compatibility():
    assert BUDGET_BY_ROLE["推进/转折"] == 12000  # r1.6 兼容别名（中断/回工窗口读旧 live plan）
```

- [ ] **Step 2**: FAIL（现状单值 miss）。
- [ ] **Step 3**: 实现：

```python
from shenbi.contracts.enums import CHAPTER_ROLE_VALUES
# spec #95 T1: 从 CHAPTER_ROLE_VALUES 单源派生；旧斜杠键保留为兼容别名
# （预算消费方读已提交 live plan——升级时点中断续跑/回工窗口携旧斜杠 plan 重入 step 3；束4 后可清）。
_BUDGET_BY_GROUP: tuple[tuple[tuple[str, ...], int], ...] = (
    (("高潮", "兑现"), 18000),
    (("推进", "转折"), 12000),
    (("过渡", "铺垫"), 8000),
)
BUDGET_BY_ROLE: dict[str, int] = {
    role: budget for group, budget in _BUDGET_BY_GROUP for role in group
}
BUDGET_BY_ROLE.update({"/".join(group): budget for group, budget in _BUDGET_BY_GROUP})
assert all(v in BUDGET_BY_ROLE for v in CHAPTER_ROLE_VALUES)  # 单源对账（import 时校验）
```

- [ ] **Step 4**: test_context_assemble :51-54 改单值断言+保留一条斜杠别名断言；:129-141 路径改单值入参；两 SKILL 表/rubric/scenario 对齐（`高潮/兑现` 行改 `高潮`/`兑现` 两行或注明单值）。
- [ ] **Step 5**: `just generate`（SKILL 改动）diff 空；Commit `feat: spec95 T1 BUDGET_BY_ROLE single-value rekey + legacy aliases` + audit-T3.md。

---

### Task 4: lint_gate_prompt_contract + SKILL 模板块重写（T1 · 修 R1/R2 常驻注入）

**Files:**
- Create: `tools/lint_gate_prompt_contract.py`
- Modify: `skills/shenbi-chapter-planning/SKILL.md:158/:223`（斜杠形改逐行清单+锚模板+正例）
- Modify: `justfile` check 面（lint 注册）
- Test: `tests/unit/tools/test_lint_gate_prompt_contract.py`

**Interfaces:**
- Consumes: `CHECK_ENUM_REGISTRY`（Task 1）。
- Produces: lint 校验每个注册检查的 SKILL 含 **verbatim 模板块**——合法值逐行列出+「只许单值」+最小正例（chapter_role 额外要求 defer 锚**数据形正例**：`→ defer 至第2卷·KR3`）。
- 复杂度: **infra**（tools+just check 面）· tdd_red_green · T1

- [ ] **Step 1: 红测**

```python
def test_current_planning_skill_fails_slash_grouping(tmp_repo_with_skills):
    findings = lint_gate_prompt_contract()  # 对现行 SKILL.md
    assert any("slash" in f or "verbatim" in f for f in findings)  # 斜杠形+锚缺失→FAIL

def test_passing_template_block_shape():
    # 合法块 = 每值一行 + 只许单值明示 + defer 锚数据形正例行
    ...
```

- [ ] **Step 2**: FAIL。
- [ ] **Step 3**: 实现 lint（骨架）：遍历 `CHECK_ENUM_REGISTRY` → 定位 SKILL → 校验块存在（逐值行 `^高潮$` 形、`只许单值`、正例行）；`main()` 输出 findings、非零退出；justfile check 面注册 `uv run python tools/lint_gate_prompt_contract.py`。
- [ ] **Step 4**: SKILL.md :158/:223 重写：

```markdown
- 首行必须声明 `chapter_role`，**只许单值**，合法值逐行如下（禁斜杠/组合形）：
  - `高潮`
  - `兑现`
  - `推进`
  - `转折`
  - `过渡`
  - `铺垫`
  - 正例：`chapter_role: 推进`
- defer 行锚模板：`至第N卷·KRn（N=卷号, n=KR 号，须在 volume_map 在盘）`；**数据形正例**：
  - `→ defer 至第2卷·KR3`（完整 defer 行实值形——照此形态写）
- 场景钩声明⊆末行逐字（谓则说明保留现行语义）
```

- [ ] **Step 5**: lint 对修后 SKILL PASS；`just check` 全绿；Commit `feat: spec95 T1 gate-prompt contract lint + verbatim template blocks` + audit-T4.md。

---

### Task 5: 卷期热协议参数下沉（T2 · 修 R3）

**Files:**
- Modify: `src/shenbi/contracts/skills/genre_config.py`（market_params 子键 schema 校验 `_market_params_structure` 增 `volume_opening_protocol` 扁平标量键）
- Modify: `skills/shenbi-chapter-planning/SKILL.md`、`skills/shenbi-chapter-drafting/SKILL.md`（reads 增 genre-config 投影——子键走 read extractor 面）
- Modify: `src/shenbi/pipeline/read_extractors.py`（新增 `extract_volume_opening_protocol`：从 genre-config.json `market_params.volume_opening_protocol` 投影为注入块）
- Modify: `src/shenbi/gates/g4/chapter_planning.py`（冷三连 WARN：`emotion_tone∈{平}`∧`金句位∈{静}`∧章尾张力拍=微/温 同现 → WARN `cp.cold_opening_triple`；#82 `cold_chapter`（text/recall_weight.py:205）更严子集）
- Modify: `src/shenbi/gates/g4/shadow.py`（`GATE_TO_SHADOW_KEY` 增 `"cp.cold_opening_triple": ("market_params", "volume_opening_protocol")`）
- Modify: `docs/framework/invariants.md`（维度 8 门检列登记）、`docs/regen-vol2-driver-prompt.md:19`（同批改写「唯一执法」条款）
- Test: `tests/unit/gates/g4/test_cold_opening_triple.py`、`tests/unit/contracts/test_genre_config_spec95.py`

**Interfaces:**
- Consumes（audit-T1 补）: `GOLDEN_LINE_VALUES`——冷三连谓词的 `金句位∈{静}` 分支从常量派生（`"静" in GOLDEN_LINE_VALUES` 语义），禁内联字面 `静`（词表多源病）；Task 2 顺手把 chapter_planning.py:125 `golden_hot` 正则的 `燃` 字面换为常量派生 alternation。
- Produces: `extract_volume_opening_protocol(project_dir: Path, chapter: int | None, content: str) -> str`（""→全文+WARN 降级语义同既有 extractor）；WARN id `cp.cold_opening_triple`。
- 复杂度: **infra** · tdd_red_green · T1；不变量维度=情绪节奏（仅 WARN）
- 顶层 12 键红线：**不动 GENRE_KEYS**；子键值=扁平标量（`dict[str, int|float|str|None]`）

- [ ] **Step 1: 红测**：冷三连同现→WARN 且 shadow 表命中；genre-config 带未知子键不拒+带新子键过结构校验；reads 过滤子键路径生效（extractor 出块含 `热开篇` 协议文字）。
- [ ] **Step 2**: FAIL → **Step 3**: 实现（按上述 Files 逐点；WARN 走 shadow 通道语义：表内且 config 键在→WARN，未列→HARD fail-safe 不变）。
- [ ] **Step 4**: `just generate` diff 空；invariants.md 登记；驱动 prompt 改写（「T2 已落门级 WARN，驱动侧条款降为补充」措辞，消双源）。
- [ ] **Step 5**: Commit `feat: spec95 T2 volume_opening_protocol subkey + cold-triple shadow WARN` + audit-T5.md。

---

### Task 6: 00189 blob 回放 fixture 固化（T3 前置 · G0.9）

**Files:**
- Create: `tests/fixtures/spec95/00189-reads/`（15 个 read 的 blob 副本，文件头 `<!-- src: sha256:<ref> observability/dispatches/00189 -->`）+ `manifest.json`（path→blob sha→期望 chars）+ `expected_assembly.json`（**数字以 Step 2 回放重录为准**——Files 列所引 119,928/43,795/59,329/哨兵×2/配比 0.80 为 00189 时点实测，若组装代码已漂移则以重录值覆盖并注记）
- Test: `tests/unit/pipeline/test_settle_budget_replay.py`

**Interfaces:**
- Produces: fixture 集（Task 9 预算断言回放源）；`TOKEN_RATIO = 0.80`（估算规则钉死：chars×0.80≈tokens，01/02 实测 95,835/119,928）。
- 复杂度: infra · regression_guard · T1
- 禁 live 路径（staging 已清）；副本=真实产物逐字节（G0.11 哈希一致）

- [ ] **Step 1**: 从 `novel-xinghuo-vol1/observability/blobs/<ref>` 逐字节复制 15 项+user_prompt_blob；manifest 记 sha256/chars。
- [ ] **Step 2**: 测试断言 fixture 哈希与 manifest 一致（防漂改）；组装回放（调 Task 9 前的现行组装函数）记录基线数字进 expected_assembly.json。
- [ ] **Step 3**: Commit `test: spec95 T3 freeze 00189 blob replay fixtures` + audit-T6.md。

---

### Task 7: character_matrix 定向提取器（T3 · 真新增①）

**Files:**
- Modify: `src/shenbi/pipeline/read_extractors.py`（新增 `extract_matrix_scoped`）
- Modify: `skills/shenbi-state-settling/SKILL.md`（reads `truth/character_matrix.md` 增 `extractor: matrix_scoped`）
- Test: `tests/unit/pipeline/test_extract_matrix_scoped.py`（fixture=Task 6 的 matrix blob 副本）

**Interfaces:**
- Consumes: `truth_format.split_table_cells`（:66）；grounding 面=`truth/chapter_summaries.md`「出场角色」列（truth_io 表头在盘）。
- Produces: `extract_matrix_scoped(project_dir: Path, chapter: int | None, content: str) -> str`——键结构样例（表头+首行）+本章出场角色行；""→全文+WARN（既有降级语义）；替代通用 head+tail 中段盲截（169,169B 原档→定向小窗）。
- 复杂度: infra · tdd_red_green · T1
- **回放数字随动（plan 审查 I1）**：本 task 起 expected_assembly.json 的 matrix 字段同步更新——T7 matrix 窗/T8 hooks 窗/T9 总预算三步数字先后变动，**每 task 落地各自更新，保持 `just test` 全绿**（禁跨 task 红窗）。

- [ ] **Step 1: 红测**：ch41 fixture→输出含本章出场角色行、省略行有哨兵 `> [extractor:matrix_scoped]`；chapter=None→""。
- [ ] **Step 2**: FAIL → **Step 3**: 实现（读 chapter_summaries 出场角色列→过滤 matrix 行；import 禁自带临时正则切表——一律 split_table_cells）。
- [ ] **Step 4**: SKILL reads 变更+`just generate` diff 空；测 PASS；**expected_assembly.json matrix 字段更新**。
- [ ] **Step 5**: Commit `feat: spec95 T3 matrix_scoped extractor` + audit-T7.md。

---

### Task 8: hooks 窗语义强化（T3 · 真新增②）

**Files:**
- Modify: `src/shenbi/pipeline/read_extractors.py`（`extract_hooks_audit_scoped` :92-138 升级）
- Test: `tests/unit/pipeline/test_extract_hooks_audit_scoped.py`（含 ch41 全点名回归用例）

**Interfaces:**
- Consumes: `truth_format.HOOK_ID_RE`/`canon_hook_id`；**ch41 全点名回归 fixture=Task 6 固化的 hooks blob 副本**。
- Produces: 保留集=「点名 ∪ active（总览表『当前生命周期』列非 RESOLVED/已收束）」，详情节超预算时按钩优先级截并披露；治理 ch41 失效模式（点名全部 14 钩→零裁剪→43.8k 撞 32K 帽）。
- 复杂度: infra · tdd_red_green · T1

- [ ] **Step 1: 红测**：全点名 fixture 下 active-only 过滤仍生效（非 active 的点名节可省略披露）；active 判定从总览列读（`当前生命周期`）。
- [ ] **Step 2**: FAIL → **Step 3**: 实现保留集逻辑+哨兵格式扩展（`保留 X 段[点名 a+active b]，省略 Y 段`）。
- [ ] **Step 4**: 测 PASS + 00189 回放快照更新（Task 6 expected 相应字段）。
- [ ] **Step 5**: Commit `feat: spec95 T3 hooks window active∪named semantics` + audit-T8.md。

---

### Task 9: settle 专属总预算 + 顶部截断汇总块 + 降级路径预算（T3 · 真新增③④⑤）

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py`（:1458 user_prompt 组装出口；per-file 哨兵 :398-400/:447）
- Test: `tests/unit/pipeline/test_settle_budget_replay.py`（Task 6 fixture 驱动）

**Interfaces:**
- Produces: `SKILL_TOTAL_CHAR_BUDGET: dict[str, int] = {"shenbi-state-settling": 72_000}`（r1.4 配比 0.80×60k tokens 留 ~4% 余量）；**落位（plan 审查 I3）：预算执行+披露块+断言置于组装函数 return 前**（:1516 helper 注入之后——今日该块对 settle 为 no-op，但不给未来接线留绕过面；:1487/:1508/:1538 同理已被核为非 settle 面）；**72k 含披露块自身字符**；超预算→按钩优先级降级（复用 `_budgeted_truncate` :404 机括）→仍超=披露式截断+WARN（`settle_budget_degraded` 事件）→仅 <40k 硬地板 raise；**组装内断言**=预算执行路径+披露块必然出现（非断言永不超）；顶部 `【截断告知】以下文件数据不完整（截断清单+缺多少）` 汇总块（per-file 哨兵保留，不双口径）。
- 降级路径（extractor_failed_fulltext 回全文）同受总预算约束。
- **余量声明（I3）**：`chapter_loop._append_feedback_injections`（:3619/:4385）在组装外追加 corrective feedback（ch41 R5/R6 重试场景）——最终派发 prompt 可超 72k 一个反馈块；由 ~4% 余量覆盖（72k×0.80=57.6k tokens vs 60k 目标≈3k chars≈Task 10 反馈 1-2KB）——**声明的设计决定，非事故**。
- 复杂度: **infra**（最热文件 dispatch_helper）· tdd_red_green · T1

- [ ] **Step 1: 红测**：Task 6 回放——现行组装 119,928 chars；断言新预算后 ≤72,000 且顶部披露块在、钩行截断披露；硬地板用例（构造 <40k 输入损坏面→raise）；降级路径用例（extractor 抛错→全文仍受限）。
- [ ] **Step 2**: FAIL → **Step 3**: 实现（预算映射+降级序+汇总块+断言；structlog WARN）。
- [ ] **Step 4**: 回放测 PASS（expected_assembly.json 更新为新数字）+ 全量 `just test`。
- [ ] **Step 5**: Commit `feat: spec95 T3 settle total budget 72k + disclosure block + degrade-path budget` + audit-T9.md。

---

### Task 10: settle 反馈三段式（T4 前半 · 修 R6）

**Files:**
- Modify: `src/shenbi/gates/g4/state_settling.py`（`_format_drops` :182-187 纯函数面）
- Modify: `src/shenbi/pipeline/chapter_loop.py`（`_append_feedback_injections` :1164 注入层——窗口优先排序在此，gate 不进 dispatch-frame 状态）
- Test: `tests/unit/gates/g4/test_state_settling_feedback.py`

**Interfaces:**
- Produces: `_format_drops(missing, samples, *, cap=20)` → 三段式：①verbatim 行清单（去重、≤20 行、每行全文；**保留 `content_dropped:` 前缀 token**——消费方 sweep 已核：retry_routing._LENGTH_TOKENS 不以其为键，无分类破坏；#88 finding 契约衔接面在此声明）②指令「以上行原样保留于输出（作为基底行），仅在其后追加本章新键行」③最小正例（live 两行+新一行）；gate 只发纯清单（live vs staged 磁盘对比幂等），窗口感知排序（优先未在截断窗内的行）由注入层参数完成。
- 复杂度: infra · tdd_red_green · T1

- [ ] **Step 1: 红测**：反馈含 verbatim 全行+指令+正例三段；>20 行截断；窗口集参数改变排序。
- [ ] **Step 2**: FAIL → **Step 3**: 实现 → **Step 4**: PASS → **Step 5**: Commit `feat: spec95 T4 three-part content_dropped feedback` + audit-T10.md。

---

### Task 11: drafting 字数反馈并入 TARGETED-EDIT（T4 后半）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:1178-1232`（长度族反馈分支——在其上改写报文）
- Test: `tests/unit/pipeline/test_length_feedback_scenes.py`

**Interfaces:**
- Produces: 长度族反馈报文升级为「场景 i 差 N 字（现 X/需 ≥Y）+ 建议扩拍位（对白/动作/感官各一）」——**复用既有前稿全文+扩不重写指令与打摆切换**，不新建第二套反馈模板。
- 复杂度: infra · tdd_red_green · T1

- [ ] **Step 1: 红测**：字数缺口反馈含场景级差值与扩拍位建议（现只有总额）。
- [ ] **Step 2**: FAIL → **Step 3**: 实现（split_bundle 场景计数→逐场景差值格式化）→ **Step 4**: PASS → **Step 5**: Commit `feat: spec95 T4 scene-level length feedback via TARGETED-EDIT` + audit-T11.md。

---

### Task 12: 范例章注入 + 束级早检（T5 · 修 R4）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（drafting 派发组装处注入范例章；bundle 解析后早检——挂点 :1354-1363 域，Task 0 re-anchor 符号定位）
- Test: `tests/unit/pipeline/test_exemplar_and_bundle_earlycheck.py`

**Interfaces:**
- Produces: ①范例章=user prompt 注入「上一通过章全文」——**解析规则（plan 审查 I2 钉死）**：`chapters/chapter-{N-1}.md` 在盘即注入（step-5 G4.cd 晋升=「已通过」代理判据）；不在盘（真首章）→**跳过注入**（无范例不造范例）；**fixture 章（chapter-8-example.md / z11/chapter-40-no-meta.md）仅单测用**（测试显式传路径注入），生产代码禁依赖 tests/ 路径；②束级早检：dispatch 输出解析后即 split_bundle+逐章 total_chars，低于带→按章定向反馈（Task 11 报文）+整束重派；**单章重试属 Phase 2 不做**。**早检挂点（M8）**：bundle 输出解析实际执行点≈chapter_loop :1354-1363（split_bundle 消费/step-5 前域，非 :179-189 声明点）——Task 0 re-anchor 时以符号定位并记入漂移表。
- 成本声明：+3.5k tokens/次（成本可忽略）。
- 复杂度: infra · tdd_red_green · T1

- [ ] **Step 1: 红测**：组装含范例章块（fixture 驱动）；双章 bundle 一章欠重→早检捕获+反馈含该章差值；两章全绿→无早检事件。
- [ ] **Step 2**: FAIL → **Step 3**: 实现 → **Step 4**: PASS → **Step 5**: Commit `feat: spec95 T5 exemplar injection + bundle-level early check` + audit-T12.md。

---

### Task 13: merge_prose applier + patch schema（T6 前半 · 修 R7）

**Files:**
- Modify: `src/shenbi/contracts/enums.py:43` 邻域（WriteMode 语义注释+patch 载体 schema 常量）
- Create: `src/shenbi/pipeline/prose_patch.py`（applier：`apply_scene_replacements(chapter_text: str, patches: list[ScenePatch]) -> str`——未列场景不动；PRE/POST/场景钩随替换重生成）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1289-1389`（write-mode 特判增 merge_prose 分支——**先 characterization 钉死 append_dedup 既有行为**）
- Modify: `skills/shenbi-chapter-revision/SKILL.md`（输出契约改「场景级替换清单」+正例）
- Test: `tests/unit/pipeline/test_prose_patch.py`、`tests/unit/pipeline/test_write_mode_merge_prose.py`

**Interfaces:**
- Produces: `ScenePatch = tuple[str, str]`（场景定位键, 全文）；applier 纯函数幂等；G2 字数/G4.cd 全章复核在 applier 后（顺序写死在 chapter_loop 修订步）。
- 复杂度: **infra** · tdd_red_green + characterization · T1/T2
- SKILL 契约先落再改 prompt；`just generate` diff 空。

- [ ] **Step 1: characterization**——append_dedup 特判现有行为钉死（既有测试补齐缺口面）。
- [ ] **Step 2: 红测**——applier：替换单场景其余不动；PRE/POST 重生成；场景钩保留；未匹配场景键→FAIL finding（不静默）；merge_prose 派发输出走 applier。
- [ ] **Step 3**: 实现 applier+特判分支+SKILL 契约（`场景n: <全文>` 清单+正例）→ **Step 4**: PASS → **Step 5**: Commit `feat: spec95 T6 scene-level merge_prose applier + patch schema` + audit-T13.md。

---

### Task 14: reject 作用域对称（T6 后半 · 修 R8 真缺口）

**Files:**
- Modify: `src/shenbi/pipeline/cli.py:676-700`（`_checkpoint_staging_targets` CHAPTER_MEMO 分支镜像 commit 的 follower 循环）
- Test: `tests/unit/pipeline/test_checkpoint_scope_symmetry.py`

**Interfaces:**
- Produces: reject 清单=leader plan+sidecars+`bundle_chapters(project_dir, chapter)[1:]` 各 follower plan+sidecars；检查点 artifact/context 明列两章（`_checkpoint_staging_targets` 与 `_commit_staging_for_checkpoint` :734-745 单一语义对——修对称后 docstring「single map can never diverge」复为真）。
- **不新增第二检查点**；覆写路径（重派写盘）不在本 spec（§3 划出）。
- 复杂度: infra · tdd_red_green · T1

- [ ] **Step 1: 红测**：CHAPTER_MEMO 检查点 reject→follower staged plan+sidecar 均在清理清单（现只 leader）。
- [ ] **Step 2**: FAIL → **Step 3**: 实现（镜像 :743-745 循环）→ **Step 4**: PASS + commit 对称性断言（两函数 CHAPTER_MEMO targets 相等——防再漂移）→ **Step 5**: Commit `feat: spec95 T6 reject scope symmetry with commit (follower mirrors)` + audit-T14.md。

---

## 验收覆盖表（spec §2 → task → 验证命令）

| spec 验收 | task | 验证（SDD PR 内可离线执行） |
|---|---|---|
| 1. just check 含契约 lint 且现行 SKILL 全 PASS | T4 | `just check`（lint 注册后全绿输出） |
| 2. 00189 回放 ≤60k tokens 组装内断言+截断汇总块单测 | T6+T9 | `uv run pytest tests/unit/pipeline/test_settle_budget_replay.py -v` |
| 3. 束4 ≤1 接骨 | （生产验收窗） | 合并后 #84 解冻重跑——ledger 双列重数+覆写类单列记账（r1.4 条款）；PR 内不触发真实 dispatch（F947） |
| 4. 束级早检捕获≥1 字数失败或全绿 | T12（实现）+（生产窗观测） | 实现面：bundle 早检单测；实弹面：束4 窗 |
| 5. 单测面八项 | T1/T2/T3/T4/T5/T7/T8/T9/T10/T11/T13/T14（T12 实现面在 row 4） | `just test` 全绿+各 task 测试文件 |

## Self-Review 结论

- 覆盖：T1-T6 全部落到 Task 1-14；R1-R8↔任务映射：R1→T1/T2/T3/T4、R2→T4、R3→T5、R4→T12（②处置§3）、R5→T6-T9、R6→T10/T11、R7→T13、R8→T14。无缺口。
- 类型一致：`CHAPTER_ROLE_VALUES`/`CHECK_ENUM_REGISTRY`（Task 1 产出）被 Task 2/3/4 消费；`extract_matrix_scoped`/`SKILL_TOTAL_CHAR_BUDGET` 命名跨 task 一致。
- 无占位符；执行时首步 re-anchor（Task 0）。
