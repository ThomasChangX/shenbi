# Spec #86 死面清扫批（dead-surface-purge）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 6 处零引用死面（src 净减 ~906 行），为 spec #87 god 文件拆分减重——纯删除批，零新机制、零新 FAIL 门、零付费 dispatch。

**Architecture:** 按 spec r3.4 的 T1-T6 分七个 task：scr_extractor 缩编（唯一新代码=~40 行单函数）、review_checklist 死半边、chapter_loop 死分支+manifest+孤儿 helper、trace 两模块删除、capability_fs 迁 tests、executor_config 死块+registry 死 kind，收尾生成物重同步+全验收跑。所有 task 均 infra（触 `pipeline/`/`contracts/`），协调者亲实现。

> **Plan r2（2026-11-10 审查轮 1 修订）**：C1/C2 补 Task 6 两钉死测试（test_executor_config discriminative 列表裁 5+docstring 9→5；test_registry kinds 删 short+名 16→15）· I3 Task 3 补删 :45 HookState/parse_hook_state 悬空 import · I4 `_write_chapter` META 改规范 `<!--META-BEGIN-->…<!--META-END-->` 形态且内置不在期望集的 location 字钉剥离序 · I5 steps_restructured/adaptive_triggers 两 patch 直测钉死整测删 · M6 删已 rm 文件的 pytest 参数+补 skipped 基线步 · M7 t4_scatter :129/:130 调用点 · M8 truth_readers:34 docstring · M9 world-freshness NOTE docstring 同步 · M10 STATIC/DYNAMIC 区间与笔误修正。验收 4 计数 16→**18**（spec r3.5 同步）。
>
> **Plan r3（2026-11-10 审查轮 2 修订）**：C1 `_read_events` docstring 去 `shenbi.trace.replay` 字面量（否则植入两测试文件后 T4 grep 永久非零）· I1 steps_restructured 区间改 :41-52+:76-102 删/**保 :55-73 两活测试**（r2 的 :41-76 夹活测试=静默覆盖损失；Files/Self-Review 陈旧措辞同步清）+test_chapter_loop 锚精（:337-375 整类/:545-568 整测）· I2 T4 判据 deps.json:292-293 陈旧键预期假红注记（Task 7 重生成后 canonical 全零）· M1 双剥离钉（标题内置「镇」）· M4 三锚修（:51-69/:551-558/:4812-4813 含 NOTE 段）· M5 spec 验收 4 同步 18（spec r3.5）。
>
> **Plan r4（2026-11-10 审查轮 3 修订）**：I1 test_chapter_loop 类区间锚精 `:334-376`（banner+整类；r3 终点 :375 差末行孤立断言语法红）· I2 test_adaptive_triggers Files 条目钉死整测删（「亲读后定」陈旧措辞清除——与 Step 3/Self-Review 一致）· M1 deps.json 预期命中改恰 :292（:293 不匹配判据模式）· M2 truth_readers.py 入 Task 3 Files（pathspec 防漏提交）· M3 review_checklist :547-549 孤儿 banner 同删。

**Tech Stack:** Python 3.11+ / pytest / just（CI 同构）/ uv run

## Global Constraints

- 行号为 2026-11-10 树快照（HEAD 145bb384）；**每 task 开工前按符号 re-anchor**（chapter_loop 在本批 Task 1/3 内会再漂移）
- 验收命令全部走 `just`/`uv run`（环境同构）；禁系统 python
- `src/shenbi/` 无 `print()`（structlog）；pathlib 文件 IO；gate/lint 检查器纯函数幂等
- **禁止 `git add -A`/`git add .`**——所有 commit 显式列路径
- 不触 SKILL.md reads/writes（全批已核零触及）；不触发任何 `shenbi-dispatch`/`pipeline` 子命令（核心原则 8）
- 死桩证据写入 Task 2 commit message（spec T2 留档要求）：`third_person_limited`/`multi_pov` 捏造、`truth/world_rules.md` 不存在（活半边读 `world/rules.md`）、`chapter-{ch:03d}` 零填充与全管线不一致、`sensitivity_flags: 0` int 冒充 list
- 每 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`（fresh-context 重审）；无 audit 不得进下一 task

---

### Task 1: scr_extractor 缩编 + chapter_loop 两调用点换源（spec T1）

**复杂度: infra** ｜ **test_kind: tdd_red_green**（新函数）+ regression_guard（删除面）

**Files:**
- Rewrite: `src/shenbi/pipeline/scr_extractor.py`（493 行 → ~40 行）
- Modify: `src/shenbi/pipeline/chapter_loop.py:2266-2282`（world freshness 换源）、`:2177-2190`（删 `_run_post_draft_extract`）、`:4492`（删调用行）、`:4491` 附近 import 无（函数内 import 随删）
- Test: `tests/pipeline/test_scr_extractor.py`（189 行重写为 ~70 行）
- Delete: `tests/pipeline/test_scr_cache_invalidation.py`（整文件，4 测试专测缓存）
- Modify: `tests/pipeline/test_bundle_stepping.py:322`（删 mock 行）

**Interfaces:**
- Produces: `recent_location_terms(project_dir: Path, chapter: int, lookback: int = 10) -> set[str]`（scr_extractor 新唯一公共面；Task 1 内 chapter_loop 换源消费）
- Deletes: `extract_scr` / `StructuredChapterRepresentation` / `extract_prose` / `_extract_world_references` / `_scan_fatigue_words` 及其余全部私有抽取器；`_run_post_draft_extract`

- [ ] **Step 1: 写新函数的红测**——重写 `tests/pipeline/test_scr_extractor.py` 全文件：

```python
"""recent_location_terms: the surviving world-freshness face of the old SCR.

spec #86 T1: the 17-field StructuredChapterRepresentation had exactly one
live consumer (world freshness reading world_refs[category=="location"]);
everything else was dead weight. This module now exposes a single function.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.pipeline.scr_extractor import recent_location_terms


def _write_chapter(project_dir: Path, n: int, body: str) -> None:
    # 双剥离钉（plan r3 审查 M1）：标题内置「镇」、META 块内置「林/谷」——三者
    # 均不在任何期望集：META 剥离失效→林/谷泄漏红；H1 剥离失效→镇泄漏红。
    chapters = project_dir / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    (chapters / f"chapter-{n}.md").write_text(
        f"# 第{n}章 镇志\n\n{body}\n\n"
        "<!--META-BEGIN-->林 # 非散文 META 行\n第二行谷<!--META-END-->\n",
        encoding="utf-8",
    )


def test_collects_location_terms_across_window(tmp_path: Path) -> None:
    _write_chapter(tmp_path, 3, "他走进山口，望见远处的城。")
    assert recent_location_terms(tmp_path, 4) == {"山", "城"}


def test_window_excludes_current_chapter(tmp_path: Path) -> None:
    _write_chapter(tmp_path, 3, "旧章的山")
    _write_chapter(tmp_path, 4, "本章的河")
    assert recent_location_terms(tmp_path, 4) == {"山"}


def test_lookback_bounds_at_chapter_one(tmp_path: Path) -> None:
    _write_chapter(tmp_path, 1, "第一章的林")
    assert recent_location_terms(tmp_path, 5) == {"林"}


def test_missing_chapter_tolerated(tmp_path: Path) -> None:
    _write_chapter(tmp_path, 2, "存在的海")  # chapter 1 absent
    assert recent_location_terms(tmp_path, 3) == {"海"}


def test_non_location_categories_ignored(tmp_path: Path) -> None:
    # 灵石=cultivation、金币=currency 必须被过滤；山/河=location 保留
    _write_chapter(tmp_path, 2, "他掏出灵石和金币，翻过山，渡过河。")
    assert recent_location_terms(tmp_path, 3) == {"山", "河"}


def test_empty_project_returns_empty(tmp_path: Path) -> None:
    assert recent_location_terms(tmp_path, 10) == set()
```

- [ ] **Step 2: 红跑确认**——`uv run pytest tests/pipeline/test_scr_extractor.py -q`（期望 FAIL: cannot import recent_location_terms）

- [ ] **Step 3: 重写 `src/shenbi/pipeline/scr_extractor.py` 全文件**：

```python
"""Recent location terms for the world-freshness check (spec #86 T1).

The old 17-field StructuredChapterRepresentation had one live consumer:
world freshness reading world_refs filtered to category=="location". The
per-chapter disk cache existed only to serve the full extraction; with the
single-function face there is nothing worth caching.
"""

from __future__ import annotations

import re
from pathlib import Path

from shenbi.gates.shared import META_BLOCK_RE

_LOCATION_RE = re.compile(r"(山|河|城|镇|村|谷|林|海|原)")


def recent_location_terms(project_dir: Path, chapter: int, lookback: int = 10) -> set[str]:
    """Location terms referenced in chapters ``[max(1, chapter-lookback), chapter)``.

    Mirrors the pre-#86 consumption shape verbatim: window excludes the
    current chapter; a missing/incomplete chapter is tolerated (its absence
    contributes nothing) — the old loop's per-chapter ``except: continue``.
    """
    terms: set[str] = set()
    for ch in range(max(1, chapter - lookback), chapter):
        path = project_dir / "chapters" / f"chapter-{ch}.md"
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        prose = META_BLOCK_RE.sub("", text)
        prose = re.sub(r"^(#\s+.+?\n\s*)+", "", prose)
        terms.update(_LOCATION_RE.findall(prose))
    return terms
```

（文件级验收 ≤60 行：此实现 ~40 行 ✓）

- [ ] **Step 4: chapter_loop 换源**——`src/shenbi/pipeline/chapter_loop.py`（行号按符号找）：
  1. world freshness 块（原 :2266-2282）：删 try-import 守卫（`try: from shenbi.pipeline.scr_extractor import extract_scr ... return` 五行）与整个 for 循环（`recent_locations: set[str] = set()` 到 `continue` 十行），替换为（**并同步改写函数头 :2252-2255 的 Plan 17 NOTE docstring——守卫删除后失败会传播而非静默降级，原注释失实**）：

```python
    from shenbi.pipeline.scr_extractor import recent_location_terms

    recent_locations = recent_location_terms(project_dir, chapter)
```

  2. 删 `_run_post_draft_extract` 整函数（原 :2177-2190）
  3. 删 :4492 调用行 `_run_post_draft_extract(state, n)`（step-5 scene-split 尾 bundle 循环内）

- [ ] **Step 5: 删测试文件 + 改 mock 点**——`git rm tests/pipeline/test_scr_cache_invalidation.py`；`tests/pipeline/test_bundle_stepping.py` 删 `:322` 行 `mp.setattr(cl, "_run_post_draft_extract", lambda *a, **kw: None)`

- [ ] **Step 6: 绿跑 + 零翻转面**——`uv run pytest tests/pipeline/test_scr_extractor.py tests/pipeline/test_bundle_stepping.py tests/unit/pipeline/test_chapter_loop.py -q`（bundle_stepping/全章环零翻转）；`uv run pytest tests/ -q -k "world_freshness or scene_split" ` 相关面；记录 `uv run pytest tests/ -q --collect-only 2>/dev/null | tail -2` 的用例总数与 skipped 基线（验收 4 比对用）

- [ ] **Step 7: 判据跑**——`grep -rn "StructuredChapterRepresentation\|extract_scr" src/ tools/ tests/ | grep -v scr_extractor.py` 期望零输出；`wc -l src/shenbi/pipeline/scr_extractor.py` 期望 ≤60

- [ ] **Step 8: Commit**（路径显式列出）+ audit-T1

---

### Task 2: review_checklist 死半边 + lint 白名单承诺锚（spec T2）

**复杂度: infra** ｜ **test_kind: regression_guard**

**Files:**
- Modify: `src/shenbi/pipeline/review_checklist.py`（删 8 死函数 :572-655 区段逐个删 + STATIC_FIELDS :551-558 + DYNAMIC_FIELDS :559-569 + **:547-549「Static/Dynamic Split」孤儿 banner 同删** + `__all__` 收缩至 4 公共名）
- Modify: `tools/lint_truth_format_single_source.py`（删 NAMED_WHITELIST 条目 :57 + 模块 docstring :18-19 两行）
- Delete: `tests/pipeline/test_review_checklist.py`（整文件 57 行——两测试全测死函数 get_checklist/generate_chapter_delta）

**Interfaces:**
- Keeps（唯一公共面，消费者 dispatch_helper.py:1580-1594）: `ReviewChecklist` / `ENDING_PATTERNS` / `generate_review_checklist` / `inject_checklist_into_prompt`
- Deletes: `generate_static_template` / `generate_chapter_delta` / `get_checklist` / `_extract_hooks_from_plan` / `_load_blacklist` / `_load_voice_constraints` / `_load_pov_mode` / `_load_world_rules_brief` / `STATIC_FIELDS` / `DYNAMIC_FIELDS`（`__all__` 中 5 死 `_` 名随之）

- [ ] **Step 1: 逐个删 8 死函数**（:572/:584/:594/:611/:634/:643/:647/:651——**逐个定位删除，禁止整段区间**；中间夹的活私有函数（`_get_recent_ending_types` 等 9 活 `_` 名对应的函数体在 :103-:550 区间）不动）
- [ ] **Step 2: 删 STATIC_FIELDS（:551-558）与 DYNAMIC_FIELDS（:559-569）两死常量**；`__all__` 改为恰四名：

```python
__all__ = [
    "ENDING_PATTERNS",
    "ReviewChecklist",
    "generate_review_checklist",
    "inject_checklist_into_prompt",
]
```

- [ ] **Step 3: lint 白名单兑现**——`tools/lint_truth_format_single_source.py` 删 :57 条目 `"src/shenbi/pipeline/review_checklist.py": "hook_pattern",` 与 :18-19 模块 docstring 中提及该白名单的两行（NAMED_WHITELIST 若因此为空 dict，保留空 dict+注释「spec #85 r8 承诺锚已随 #86 T2 兑现」）
- [ ] **Step 4: 删测试文件**——`git rm tests/pipeline/test_review_checklist.py`
- [ ] **Step 5: 验证**——`uv run pytest tests/ -q -k "review_checklist or precompute"`（tests/unit/pipeline/test_review_checklist*.py 两文件只 import 保留面，应零翻转）；`uv run python tools/lint_truth_format_single_source.py`（期望 exit 0——`hook_pattern` 死代码随之消失，白名单条目删除后无残留命中）；`uv run python tools/lint_key_reconciliation.py`（不触，应绿）
- [ ] **Step 6: 判据跑**——`grep -rn "generate_static_template\|generate_chapter_delta\|get_checklist\|_extract_hooks_from_plan\|_load_blacklist\|_load_voice_constraints\|_load_pov_mode\|_load_world_rules_brief\|STATIC_FIELDS\|DYNAMIC_FIELDS" src/ tools/ tests/` 期望零输出
- [ ] **Step 7: Commit（含死桩证据四条于 message）** + audit-T2

---

### Task 3: chapter_loop 死分支 ×4 + manifest 三函数 + 孤儿 helper（spec T3）

**复杂度: infra** ｜ **test_kind: regression_guard**

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py`（删 :3044-3048/:4810-4813/:4909-4910 死分支；_check_conditional_resolve :2814-：函数体含 :2832 dispatch_skill；_is_volume_boundary :2967；_drift_guidance_triggered :2977；_load_manifest :2924；_save_manifest :2937；_update_last_drift_manifest :2960——**三段不连续，:2944 _get_recent_resonance_scores 是活函数勿伤**）
- Modify: `src/shenbi/pipeline/truth_readers.py:34`（docstring「(chapter_loop conditional-resolve)」悬空指认改写——Step 3 顺手项入 Files 防 pathspec 漏提交）
- Modify: `tools/lint_key_reconciliation.py`（删两 ReadKey 锚 :132-138 `chapterloop/drift-guidance` 与 :139-145 `chapterloop/pending-hooks`——整 ReadKey 块）
- Modify: `tests/unit/pipeline/test_spec83_stale_declarations.py`（删 :87 参数化行 + **:105 canary `== 13` 改 `== 12`**）
- Modify: `tests/unit/pipeline/test_chapter_loop.py`（删 **:334-376「Conditional foreshadowing-resolve」banner+`class TestConditionalResolve` 整类**（类实止 :376——r4 锚精：r3 的 :337-375 差末行孤立断言语法红）与 **:545-568 `test_track_step_with_triggered_hooks_dispatches_resolve` 整测**）
- Modify: `tests/pipeline/test_chapter_steps_restructured.py`（**删 :41-52 `test_intent_management_boundary_only` + :76-102 `test_drift_guidance_triggered_by_alerts` 两死分支直测；保 :55-73 两活测试**（`test_non_conditional_steps_always_run`/`test_conditional_snapshot_manage_runs`——删分支后仍过、钉默认 fallthrough）；r3 钉死：改 patch 目标不可行——`_should_run_step` 删 :3044-3048 后 conditional 步落默认 `return True`，`is False` 断言无解）
- Modify: `tests/unit/pipeline/test_adaptive_triggers.py:34-56`（`test_intent_management_gated_by_volume_boundary` 整测删至文件尾——r4 钉死与 steps_restructured 同理：改 patch 目标不可行，`_should_run_step` 删分支后对 conditional 步恒 `return True`，`is False` 断言无解）
- Modify: `docs/framework/truth-files.yaml:102-104`（:102-103 注释历史化：「历史遗留：写方 `_update_last_drift_manifest` 已于 spec #86 删除；存量项目盘上文件容忍，无新写入」；:104 条目 `producer: pipeline` **保留原值**）
- Modify: `tools/regen_reset.py`（删 :149-156 `_clear_snapshots_key` 整函数 + :228 调用行 + :186 动作标签行）
- Modify: `src/shenbi/records/writer.py:6`（docstring「(via chapter_loop._check_conditional_resolve)」→「(via chapter_loop pending-hooks consumption)」）
- Modify: `docs/superpowers/plans/2026-10-26-spec79-regen-acceptance.md:12`（行尾加注记「（spec #86：`last_drift_chapter` 清理已随死面删除，regen-reset 不再触碰该键）」）

**Interfaces:**
- Deletes: `_check_conditional_resolve(state: PipelineState, project_dir: Path, chapter: int) -> None`、`_is_volume_boundary(project_dir: Path, chapter: int) -> bool`、`_drift_guidance_triggered(state: PipelineState) -> bool`、`_load_manifest(project_dir: Path) -> dict[str, Any]`、`_save_manifest(project_dir: Path, manifest: dict[str, Any]) -> None`、`_update_last_drift_manifest(project_dir: Path, chapter: int) -> None`
- Keeps: `shenbi.pipeline.triggers.is_volume_boundary(chapter: int, project_dir: Path | str) -> bool`（活函数 :318——**test_triggers.py:233 不动**）；`_get_recent_resonance_scores`（:2944 活）

- [ ] **Step 1: 先跑 canary 红证**——`uv run pytest tests/unit/pipeline/test_spec83_stale_declarations.py -q`（批前绿基线记录）；删 chapter_loop 死分支+三函数+孤儿 helper 后先跑一次看 canary `==13` 红 dispatch 计数（13→12 变动实锚）+ lint_key_reconciliation 红（reader anchor FAIL）——两红即「删对了地方」的证据，随后改 :105 与 lint 锚转绿
- [ ] **Step 2: chapter_loop 删除**——按符号定位（Task 1 已使行号漂移）：死分支①②（`if step.skill == "shenbi-intent-management":` / `elif`/`if step.skill == "shenbi-drift-guidance":` 含 return 两块 :3044-3048）、③（`if "foreshadowing-lifecycle" in step.skill: _check_conditional_resolve(...)` :4812-4813——**连同其上方 :4806-4811 NOTE 注释段一并删**，字面删 if/call 两行会留孤儿注释）、④（`if step.skill == "shenbi-drift-guidance": _update_last_drift_manifest(...)` :4909-4910）；manifest 三函数两段；孤儿 helper 三函数；**删 :45 行 `from shenbi.contracts.schemas.hooks import HookState, parse_hook_state`（全文件唯一消费点在 _check_conditional_resolve 体内 :2828——删前 grep 复核两符号零残余使用，否则 ruff F401 悬空）**
- [ ] **Step 3: 连带面逐项落**——lint 两 ReadKey 块删；spec83 :87 行删+:105 `13`→`12`；test_chapter_loop 整类+整测删；**steps_restructured 删 :41-52+:76-102（保 :55-73 两活测试）与 adaptive_triggers :34-56 两处 `_is_volume_boundary` patch 直测整测删**（r3 钉死：分支删除后 `_should_run_step` 对 conditional 步落默认 `return True`，`is False` 断言无论 patch 指向哪必失败——改 patch 目标不可行）；truth-files.yaml 注释；regen_reset 三处；writer.py docstring；spec79 plan 注记；truth_readers.py:34 docstring「(chapter_loop conditional-resolve)」悬空指认顺手改写
- [ ] **Step 4: 验证**——`uv run pytest tests/unit/pipeline/test_spec83_stale_declarations.py tests/pipeline/test_chapter_steps_restructured.py tests/unit/pipeline/test_adaptive_triggers.py tests/unit/pipeline/test_triggers.py tests/unit/pipeline/test_chapter_loop.py tests/unit/tools/test_regen_reset.py -q` 全绿；`uv run python tools/lint_key_reconciliation.py --strict` exit 0
- [ ] **Step 5: 判据跑**——T3 两条 grep（spec r3.4 文本）期望零输出
- [ ] **Step 6: Commit** + audit-T3

---

### Task 4: trace materialize/replay 删除 + 6 测试文件（spec T4）

**复杂度: infra** ｜ **test_kind: regression_guard**

**Files:**
- Delete: `src/shenbi/trace/materialize.py`（163 行）、`src/shenbi/trace/replay.py`（63 行）、`tests/unit/trace/test_materialize.py`、`tests/unit/trace/test_replay.py`（整文件）
- Modify: `src/shenbi/trace/__init__.py`（删 :5-6 两 import + `__all__` 中 `materialize_progress`/`replay` 两名）
- Modify: `tests/unit/trace/test_compaction.py`（:6 import 换本地 helper；:22/:44 `replay(tmp_path)` 换 `_read_events`）
- Modify: `tests/property/trace/test_chain_invariants.py`（:10 import；:22/:37 同换）
- Modify: `tests/unit/test_t4_scatter_guards.py:127-130`（:127 `from shenbi.trace.materialize import _round_field` → 本地 helper **换名 `round_field`**——沿用旧名会使验收 grep 非零；:129/:130 两处调用点同步换名）
- Modify: `tests/unit/pipeline/test_concurrency_regression.py`（:132-150 `test_f630_materialize_clobbers_foreign_keys` **整测删**——守护对象已删；:188-213 `test_record_audit_outcome_g7_no_false_tamper` 的 :192 import 与 `replay(tmp_path)` 换本地 helper；:268-274 `test_periodic_materialize_removed` 整测删）
- Modify: `docs/framework/status-vocab.md:20`（materialize/replay 提及行改写）、`docs/superpowers/full-project-audit-prompt.md:335`（`trace/replay.py` 引用改写）

**Interfaces:**
- Produces（测试本地 helper，两文件各一份同形）:

```python
def _read_events(round_dir: Path) -> list[TraceEvent]:
    """Pure reader: parse trace.jsonl, stop at first torn line / bad signature.

    The pre-#86 replay reader also truncated the file on torn lines; tests
    only consume the returned events, so the helper is read-only.
    """
    from shenbi.trace.event import GENESIS_PREV, TraceEvent, canonical_payload, sign

    path = Path(round_dir) / "trace.jsonl"
    if not path.exists():
        return []
    prev = GENESIS_PREV
    out: list[TraceEvent] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            event = TraceEvent.model_validate_json(ln)
        except Exception:
            break
        if sign(prev, canonical_payload(event), event.schema_version) != event.signature:
            break
        out.append(event)
        prev = event.signature
    return out
```

  test_t4_scatter_guards.py 本地 helper（F614 语义）:

```python
def round_field(round_dir: Path) -> str:
    """Derive round number from ``round-<N>`` dir name; else "unknown" (F614)."""
    name = Path(round_dir).name
    if "round-" in name:
        tail = name.split("-")[1]
        return tail if tail.isdigit() else "unknown"
    return "unknown"
```

- [ ] **Step 1: 删模块与两专测文件**——`git rm src/shenbi/trace/materialize.py src/shenbi/trace/replay.py tests/unit/trace/test_materialize.py tests/unit/trace/test_replay.py`
- [ ] **Step 2: `__init__.py` 收缩**——删两 import 行与 `__all__` 两名
- [ ] **Step 3: 四文件改写**——test_compaction/test_chain_invariants 植入 `_read_events` helper 换调用；t4_scatter_guards 植入 `round_field`；concurrency 删两整测+g7 测换 helper
- [ ] **Step 4: 文档两处改写**（status-vocab.md:20 行内提及；audit-prompt:335 trace/replay.py 引用——按上下文最小改写）
- [ ] **Step 5: 验证**——`uv run pytest tests/unit/trace/ tests/property/trace/ tests/unit/test_t4_scatter_guards.py tests/unit/pipeline/test_concurrency_regression.py -q` 全绿
- [ ] **Step 6: 判据跑**——两条 grep（含 `--exclude-dir=coverage` 与私有导入面）：**T4 时点预期命中 `tests/tiers/deps.json:292`（`trace/replay.py` 陈旧键——`.` 通配 `/`；:293 的 materialize 键同陈旧但两判据模式均不命中它，随重生成同灭）**；其余命中须为零。canonical 判据（全零）在 Task 7 Step 3 重生成后统一跑
- [ ] **Step 7: Commit** + audit-T4

---

### Task 5: capability_fs 迁 tests/support（spec T5）

**复杂度: infra** ｜ **test_kind: regression_guard**

**Files:**
- Move: `src/shenbi/capability_fs.py` → `tests/support/capability_fs.py`（内容原样，git mv）
- Create: `tests/support/__init__.py`（空文件）
- Modify: `tests/unit/test_capability_fs.py:7` 与 `tests/property/gates/test_capability_fs_properties.py:9`（`from shenbi.capability_fs import CapabilityFS` → `from tests.support.capability_fs import CapabilityFS`）
- Modify: `pyproject.toml:432`（`"src/shenbi/capability_fs.py" = [...]` → `"tests/support/capability_fs.py" = [...]` 键名迁移，豁免列表原样）
- Modify: `docs/superpowers/full-project-audit-prompt.md:336`（capability_fs 列为 T12 审计对象的行——改写为 tests/support 路径注记）

**Interfaces:**
- Keeps: `class CapabilityFS`（内容零改动，仅位置）

- [ ] **Step 1: git mv + __init__ + import 改写 + pyproject 键迁移**
- [ ] **Step 2: 验证**——`uv run pytest tests/unit/test_capability_fs.py tests/property/gates/test_capability_fs_properties.py -q` 全绿；`uvx ruff check tests/support/capability_fs.py`（pyproject 迁移键生效=零命中）
- [ ] **Step 3: 判据跑**——`test ! -e src/shenbi/capability_fs.py` 期望 exit 0
- [ ] **Step 4: Commit** + audit-T5

---

### Task 6: executor_config 六死块 + registry 死 kind（spec T6）

**复杂度: infra** ｜ **test_kind: regression_guard**

**Files:**
- Modify: `executor_config.toml`（**按键删 6 块**：`[overrides."shenbi-review-continuity"]` :120、`[overrides."shenbi-review-anti-ai"]` :124、`[overrides."shenbi-review-memo-compliance"]` :157、`[overrides."shenbi-review-world-rules"]` :161、`[overrides."shenbi-review-pov"]` :169、`[overrides."shenbi-review-dialogue"]` :189——**每块含其键值对至下一 `[` 前；禁按行区间整删**——区间夹 10 活块）
- Modify: `src/shenbi/contracts/schemas/registry.py`（:38 Literal 删 `"short"` 行；:9 docstring「16 kind values (the real yaml uses all 16)」→「15 kind values (the real yaml uses all 15)」）
- Modify: `tests/pipeline/test_executor_config.py:51-69`（`test_discriminative_review_queue_has_low_temperature` discriminative 列表 :55-65 含将删 4 键且断言 `skill in overrides`——**列表裁至存活 5 技能**（arc-payoff/era/fanfic/sensitivity/spinoff），docstring「9 discriminative」改「5」）
- Modify: `tests/unit/contracts/schemas/test_registry.py:49-70`（`test_kind_literal_all_16` kinds 列表 :63 钉死 `"short"`——删该元素；测试名与 docstring `16`→`15`）

**Interfaces:**
- Keeps: `RegistryKind` Literal 其余 15 值；executor_config 其余 29 活 override 块

- [ ] **Step 1: 按键删 6 块**（逐键定位 `[overrides."<key>"]` 起至下一节头）
- [ ] **Step 2: registry 删 "short" + docstring 16→15**；同步两测试：executor_config discriminative 列表裁至存活 5 技能+docstring 9→5；registry 测试 kinds 删 "short"+名与 docstring 16→15
- [ ] **Step 3: 验证**——`uv run pytest tests/pipeline/test_executor_config.py tests/unit/contracts/schemas/test_registry.py -q` 全绿；`uv run python -c "import tomllib; cfg=tomllib.loads(open('executor_config.toml').read()); assert len(cfg['overrides'])==29"`；`uv run python -c "from shenbi.contracts.schemas.registry import RegistryKind; assert 'short' not in RegistryKind.__args__"`
- [ ] **Step 4: 判据跑**——六键 grep executor_config.toml 零输出
- [ ] **Step 5: Commit** + audit-T6

---

### Task 7: 生成物重同步 + 全验收跑（spec T9 + §2 验收 1-4）

**复杂度: infra** ｜ **test_kind: regression_guard**

**Files:**
- Regenerate: `tests/tiers/deps.json`（`_tool_hashes` 面全变）、`docs/skills/`（如 generate 触及）
- Verify: spec §2 四条验收全跑

- [ ] **Step 1: `just generate`**（shenbi-sync-contracts 重生成 deps.json/docs/skills）→ `git add` 生成物（**流序：锁→生成→commit→check**——本批不动 pyproject 依赖，uv.lock 不需动）
- [ ] **Step 2: `just check`**——期望 EXIT=0（契约 lints 三件+repo 一致性+状态字面量+ruff+mypy+basedpyright+幂等 diff+两段 pytest）
- [ ] **Step 3: 验收 1 判据全跑**——T1/T2/T3/T4/T5/T6 六组 grep + 存在性断言全零输出，粘贴进 progress.md 验收证据
- [ ] **Step 4: 验收 2**——`git diff --stat origin/main...HEAD -- src/ | tail -1` 核 src 净减 ≥650（预期 ~906）；`wc -l src/shenbi/pipeline/scr_extractor.py` ≤60
- [ ] **Step 5: 验收 4**——skip 计数比对（批前基线在 Task 1 Step 6 记录；`uv run pytest tests/ -q 2>&1 | tail -3` 的 skipped 数不增）；18 文件改写后全绿已由各 task 证明（r2：T1 三+T2 一+T3 四+T4 六+T5 两+T6 两）
- [ ] **Step 6: Commit（生成物）** + audit-T7

---

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 每 T grep 判据零输出 | T1-T6 各 Step「判据跑」+ T7 Step 3 汇总 | 六组 grep（spec r3.4 全文判据段） |
| 2 src 净减 ≥650 + scr ≤60 行 | T7 Step 4 | `git diff --stat origin/main...HEAD -- src/` + `wc -l` |
| 3 just check exit 0 | T7 Step 2 | `just check`（前置：lint 两锚 T3/白名单 T2/pyproject 键 T5 均已落） |
| 4 skip 不增 + 18 文件改写后过 | 各 task Step 验证 + T7 Step 5 | pytest skipped 计数比对 |

## F947 合规

全批零 LLM dispatch 依赖；所有验收=离线 grep/pytest/just。G3.4 不适用（无生成物评分场景）。

## Self-Review 记录

- 覆盖：spec T1-T6+T7(不动面)+T8(更正已在 spec)+T9 ↔ Task 1-7 一一对应 ✓
- 占位符：无 TBD/「适当处理」类；steps_restructured/adaptive_triggers 两处 patch 直测的处置已在 r3 **钉死为整测删**（分支删除后 `_should_run_step` 对 conditional 步落默认 `return True`——改 patch 目标不可行；steps_restructured 保 :55-73 两活测试）✓
- 类型一致：`recent_location_terms` 签名 Task 1 Step 1/3/4 三处一致；`_read_events`/`round_field` helper 名与 T4 验收 grep 判据（`_round_field` 零输出）自洽 ✓
