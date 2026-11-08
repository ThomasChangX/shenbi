# Spec #100 POST 自检虚报反馈补充 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「POST 自检申报 X 而实测 Y」的当场反驳句并入既有 `word_band` 重派反馈（仅「声明在带 ∧ 实测<下限」触发），并补 SKILL 两句禁照抄教学——零新 id、零新解析面、零新增派发轮次。

**Architecture:** 单一解析面落 `gates/g4/post_declarations.py`（`parse_post_wordcount_declarations -> list[int]`，规则 `_POST_WORDCOUNT_DECL_RE` 不迁出）；`check_post_wordcount_precision` 重构消费它（行为零变）；`pipeline/scene_splitter.validate_split` 在既有 `word_band` 报文尾部追加 precision 子句。无新 issue 行/无新契约字段。

**Tech Stack:** Python 3.11+/pytest；无新依赖。

**Spec:** `docs/superpowers/specs/2026-11-08-spec100-drafting-band-first-pass.md`（r7）

## Global Constraints

- **零新 id / 零新 issue 行 / 零新增派发轮次**（spec 最小性裁定）——precision 子句只并入既有 word_band 报文
- **触发仅「declared ∈ 带 ∧ actual < 下限」**；纯声明漂移（actual 在带）不进 rewind；over-band false claim 不在本批域
- **`check_post_wordcount_precision` 行为零变**（多声明行各发一条 issue——故助手返回 `list[int]` 而非 last-wins 单值）；G4 侧仍 WARN、id 不变
- **不硬编码 3200**：SKILL 只写 `chapter_word.default`（符号引用）
- **`_POST_WORDCOUNT_DECL_RE` 不迁出 post_declarations**（避免 shared↔g4 第二解析面）
- 与 #96 共用 drafting SKILL → plan 首步 re-anchor；不改 frontmatter reads/writes（无需契约再生成，但改 SKILL 后仍须 `just check` 生成物 diff 为空）
- T1 触及 src 文件在 `tests/tiers/deps.json` 哈希锁内 → commit 前最后一步 `bash tests/lock-tool-hashes.sh`
- T3（实弹三线）**批外**：束8 续跑窗台账
- G0.9：fixture=真实首派 blob 解包件；G0.11 不适用（运行工件）
- Conventional commits；gate 检查器纯函数幂等；无 print

## 实际签名（源码复制；执行首步 re-anchor）

```python
# src/shenbi/gates/g4/post_declarations.py:97-101（规则现状）
_POST_WORDCOUNT_DECL_RE = re.compile(
    r"^\s*-\s*\[[xX ]\]\s*正文字数（逐段计数合计）[^\n]*?总计\s*[≈约]?\s*(\d+)", re.M
)


# src/shenbi/gates/g4/post_declarations.py:118
def check_post_wordcount_precision(content: str, actual_chars: int) -> list[str]: ...


# src/shenbi/pipeline/scene_splitter.py:211
def validate_split(ch: SplitChapter, band: tuple[int, int]) -> list[str]: ...


# :217 total = total_chars_md_text(ch.body)
# :225-229 word_band issue 首 append

# src/shenbi/pipeline/chapter_loop.py:1557
issues.extend(validate_split(ch, band))
```

---

### Task 0: Re-anchor（leaf）

- [ ] **Step 1:** `grep -n "def validate_split\|_POST_WORDCOUNT_DECL_RE\|def check_post_wordcount_precision\|issues.extend(validate_split" src/shenbi/ -r` — 漂移 ±3 外更新本 plan 签名节
- [ ] **Step 2:** 基线 `uv run pytest tests/unit/pipeline/test_scene_splitter.py tests/unit/pipeline/test_length_feedback_scenes.py tests/unit/gates/g4/test_spec83_transition_cross.py -q --no-cov` → 记 progress.md

### Task 1: 单源助手 + 原函数重构（infra · tdd_red_green；协调者亲自）

**Files:** Modify `src/shenbi/gates/g4/post_declarations.py`；Test `tests/unit/gates/g4/test_post_wordcount_declarations.py`（新建）

**Interfaces（Produces）:**
```python
def parse_post_wordcount_declarations(content: str) -> list[int]:
    """All declared 字数总计 values in POST_WRITE_SELF_CHECK order (shared
    single parse surface for check_post_wordcount_precision and the settle/
    scene-split band feedback; the regex stays in this module)."""
```

- [ ] **Step 1:** 红测：多声明行 → `[3358, 3100]`；无声明 → `[]`；声明 0 过滤（与原函数 `declared <= 0: continue` 对齐）
- [ ] **Step 2:** 实现助手；`check_post_wordcount_precision` 重构为 `for declared in parse_post_wordcount_declarations(content):`（逐条同样加 issue，**零行为变**）
- [ ] **Step 3:** 既有 `test_spec83_transition_cross.py` 零翻转 + 新测绿
- [ ] **Step 4:** `bash tests/lock-tool-hashes.sh` → Commit `feat: spec #100 单源助手 parse_post_wordcount_declarations（原函数零行为变重构）`

### Task 2: validate_split precision 子句（infra · tdd_red_green；协调者亲自）

**Files:** Modify `src/shenbi/pipeline/scene_splitter.py`（validate_split `:211-234`）；Test `tests/unit/pipeline/test_spec100_post_decl_feedback.py`（新建）+ `tests/fixtures/spec100/ch47-48-first-pass-bundle.md`（解包件）

**Interfaces:**
- Consumes: `parse_post_wordcount_declarations`（Task 1）；`total_chars_md_text`（既有）
- Produces: `validate_split` 在 `actual < band[0] ∧ declared_last ∈ band` 时，word_band issue 尾部追加：`；POST自检申报 {d}（在带内）而实测 {actual}<{band[0]}——自检虚报，须逐段真实点数补足缺口，禁照抄计划/PRE 预算`

- [ ] **Step 1:** fixture：解包 seq248 response blob `files[0].content`（bundle，含 ch47/48）→ `tests/fixtures/spec100/ch47-48-first-pass-bundle.md` + SHA256SUMS 裸形（G0.9）
- [ ] **Step 2:** 红测 3 条：①ch47 首派（声明 3210/实测 2288<2800）→ word_band 报文含「POST自检申报 3210」+「实测 2288」+「补足缺口」，**不含**「改声明一行」；②in-band（final ch48 声明 3006/实测 3093）→ issues **无**「POST自检申报」且 G4 WARN 仍产出（`check_post_wordcount_precision` 直测）；③over-band 构造（declared 3200/actual 4100）→ issues 无「POST自检申报」
- [ ] **Step 3:** 实现（`validate_split` 内 `declared = parse_...(...)` 取 `[-1]`；条件 `band[0] <= d <= band[1] and total < band[0]`）
- [ ] **Step 4:** 三绿 + 全量 `tests/unit/pipeline/ tests/unit/gates/g4/` 零翻转
- [ ] **Step 5:** 锁哈希 → Commit `feat: spec #100 validate_split 并入 POST 自检虚报反驳句（仅声明在带∧实测<下限）`

### Task 3: SKILL 净新增两句（infra · regression_guard；协调者亲自）

**Files:** Modify `skills/shenbi-chapter-drafting/SKILL.md:110`（篇幅契约段）；Test 并入 Task 2 文件或 `tests/unit/tools/`（存在性断言）

- [ ] **Step 1:** 在 :110 段末追加（不改既有句）：「**不得以 PRE 自检行或计划场景预算的总计充作 POST 总计**，POST 必须重新点数（实测六章虚报 16-97%）；目标值=`chapter_word.default`（带下限只是硬底线，不得按底线思维铺量）」
- [ ] **Step 2:** 测试：断言两句在场 + `coverage`（`chapter_word.default` 出现）；断言不含硬编码「≥3200」
- [ ] **Step 3:** `just check` 生成物 diff 为空（SKILL 变更检查）→ 锁哈希 → Commit `docs: spec #100 草写 SKILL 禁照抄 POST 总计教学（净新增两句）`

### Task 4: 收口（leaf）

- [ ] **Step 1:** plans/INDEX 登记；specs/INDEX #100 状态→执行中 T0-T2 完成/T3 批外
- [ ] **Step 2:** progress.md 验收覆盖表：验收 1→Task 0-2 证据；验收 2→PR/CI；验收 3→批外（T3 三线）
- [ ] **Step 3:** Commit `docs: spec #100 收口登记`

---

## 验收覆盖表

| Spec 验收 | Task | 验证 |
|---|---|---|
| 1. T0 三证核报告落 docs/research/ | Task 0/2 | 三证数据：manifest 34/13（T0 报告）+ rewind issues 零 precision + 被拒首派未跑 G4.cd（blob 回放证明） |
| 2. T1 PR 合并（CI 全绿+① 离线红绿+② 在场+零翻转） | Task 1-3 | Task 2 Step 2 红→Step 4 绿；`just check`；PR CI |
| 3. T3 三线记录 | **批外** | 束8 续跑窗台账 |

## G3.4 / F947

- 无生成型输出评分面 → G3.4 不适用。
- F947：T3 实弹依赖已拆为 T2 离线（本 plan）+ 批外观测——执行期零现场 dispatch。

## 复杂度路由

Task 0/4=leaf；**Task 1/2/3=infra**（gates/g4 + pipeline/ 跨模块+哈希锁），协调者亲自实现。
