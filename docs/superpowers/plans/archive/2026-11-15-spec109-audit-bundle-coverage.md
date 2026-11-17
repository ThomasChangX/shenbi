# Spec #109 audit-bundle-coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复双章批（bundle）审计的 follower 章系统性饿死——契约 reads 对称化、派发组装双章化、收口/路由 per-n 消费面、占位/失败判定 invalid 第三态、resume invalid 感知补跑。

**Architecture:** 五个生产面改造全部走「升格既有」路线：预检（`missing_audit_reads`）学 offset 解析＋wave 条件语义；shared context/checklist 以 bundle 参数化（drafting 侧 per-n 先例）；wave 收口复活 serial per-n 环的等价物并换装单源传感器；invalid 第三态仿 `resonance_pending` entry 先例、词族常量落 src 单源（工具反向 import）；resume 闭合存在性过滤与 done 面的 invalid 盲区。

**Tech Stack:** Python 3.11+ / pathlib / re / structlog；测试 pytest（tmp_path 构造结构性 fixture——G0.9 豁免：结构性输入非冒充真实产物）；门禁 `just check`。

## Global Constraints（spec 项目级约束逐字）

- **域约束**：真实 LLM dispatch（`shenbi-dispatch` / `pipeline init|resume|review`）付费且写状态——SDD 全流程禁为「验证」目的触发（`shenbi-validate G0` 允许：无副作用）。
- **F947**：验收若依赖真实 LLM dispatch 或手写 mock，plan 期必须改写为可离线复验形式（fixtures 回放/结构断言）——不改写即该 task BLOCKED。**适用裁定**：spec 验收 5（T2 生成测试 ≥94，G3.4 独立评分）依赖付费实弹 → **随用户令挂账**（#106 AC4 先例），本 plan 以离线结构断言替代交付（Task 2/Task 7）。
- **deps.json 等生成物禁手改**：改契约源头（SKILL.md）+ `just generate`（幂等 diff 会打回）。
- **src/shenbi/ 禁 `print()`**（ruff T20 零豁免）：用户可见文本走 `shenbi.cli_utils.echo`，机器可读走 `sys.stdout.write`，日志走 structlog。
- **gate 检查函数幂等**：纯验证无输出文件副作用。
- **G0.9**：scenario 输入只能引用 `tests/fixtures/` 真实产物；结构性输入（本文全部 tmp_path 构造）可 inline。
- **词族/锚定单源**（spec 附录 A）：常量家=`src/shenbi/pipeline/audit_starve_family.py`（Task 4 建），`tools/audit_starve_baseline.py` import 自 src（tools→src 方向；值不变 manifest 不变），**禁散文词表/禁 src→tools import**。双锚定：基线/回放=首锚定行、生产门=全部判定行值段，共用同一 `VERDICT_LINE_RE`。
- **offset reads wave 条件语义**（spec C1）：`{N+1}` 类 offset reads 当且仅当 n+1 ∈ wave_chapters 时必需；singleton 波合法缺席。
- **测试层级声明**：本 plan 全部 task 为 T1 层（per-skill/unit+integration）；无 T2/T3 实弹（付费面挂账）。
- **commit pathspec 纪律**：所有 commit 显式列文件路径，禁 `git add -A`。

---

### Task 1: 契约 reads 对称化 + 预检 offset/wave 条件语义（spec T1，infra）

**Files:**
- Modify: `src/shenbi/pipeline/audit_layer.py:299-354`（`missing_audit_reads`）
- Modify: `src/shenbi/pipeline/chapter_loop.py:4114`（预检调用点传 `bundle=wave_chapters`——I4 归属本 task）
- Modify: `skills/shenbi-review-group-craft/SKILL.md:7-11`、`skills/shenbi-review-group-plan/SKILL.md`、`skills/shenbi-review-group-factual/SKILL.md`、`skills/shenbi-review-group-character/SKILL.md`、`skills/shenbi-review-resonance/SKILL.md`、`skills/shenbi-review-sensitivity/SKILL.md`（contract reads 区）
- Test: `tests/unit/pipeline/test_audit_readiness.py`（扩展）
- Test: `tests/pipeline/test_audit_cluster.py`（契约断言扩展）

**Interfaces:**
- Consumes: `shenbi.contracts.loader.load_contract(skill) -> dict`；`shenbi.contracts.paths.resolve_chapter_path(path: str, chapter: int | None) -> str`（`_offset_sub` 解析 `{N+1}`）。
- Produces: `missing_audit_reads(project_dir: Path | str, skill: str, chapter: int | None, *, bundle: list[int] | None = None) -> list[str]`（新增仅限关键字参数 `bundle`；Task 3 的 wave 调用点将传入）。六技能契约 reads 含 `chapters/chapter-{N+1}.md`（group-craft/-plan/resonance 另含 `plans/chapter-{N+1}-plan.md`）。

- [ ] **Step 1: 写失败测试——offset 解析与 wave 条件语义**

在 `tests/unit/pipeline/test_audit_readiness.py` 追加。**契约注入用该文件既有手法**（`:26-31` 先例）：`monkeypatch.setattr(loader, "load_contract", lambda skill: {...})` 直接喂 dict 契约——**不写物理 SKILL.md**（loader 无 `SKILLS_DIR` 常量，物理文件路线死码）：

```python
def _offset_contract() -> dict:
    return {
        "kind": "report",
        "reads": ["chapters/chapter-N.md", "chapters/chapter-{N+1}.md"],
        "writes": [],
        "updates": [],
    }


def test_missing_audit_reads_resolves_offset_braces(tmp_path, monkeypatch):
    """a1: literal ``chapter-{N+1}`` reads resolve to the follower chapter."""
    import shenbi.contracts.loader as loader
    from shenbi.pipeline.audit_layer import missing_audit_reads

    monkeypatch.setattr(loader, "load_contract", lambda skill: _offset_contract())
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-25.md").write_text("正文25", encoding="utf-8")
    (tmp_path / "chapters" / "chapter-26.md").write_text("正文26", encoding="utf-8")
    # bundle 双章：follower 在波内且在盘 → 零缺失（r1 事故形态：字面花括号 probe 必缺失）
    assert missing_audit_reads(tmp_path, "fake-skill", 25, bundle=[25, 26]) == []


def test_missing_audit_reads_offset_required_only_inside_bundle(tmp_path, monkeypatch):
    """C1: singleton 波（无 volume_map/卷尾）offset reads 合法缺席，不停摆。"""
    import shenbi.contracts.loader as loader
    from shenbi.pipeline.audit_layer import missing_audit_reads

    monkeypatch.setattr(loader, "load_contract", lambda skill: _offset_contract())
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "chapter-49.md").write_text("正文49", encoding="utf-8")
    # singleton 波：50 ∉ [49] → offset read 不探测（下一章未起草是常态）
    assert missing_audit_reads(tmp_path, "fake-skill", 49, bundle=[49]) == []
    # bundle=[49,50] 且 50 缺盘 → 报缺失（follower 在波内必须真实在盘）
    assert missing_audit_reads(tmp_path, "fake-skill", 49, bundle=[49, 50]) == [
        "chapters/chapter-50.md"
    ]
```

另加 **wave 级红测**（I4——`:4114` 预检调用面，非单元直调）：

```python
def test_wave_precheck_escalates_on_bundle_follower_missing(tmp_path, monkeypatch):
    """bundle 波 follower 正文缺盘 → 预检 ESCALATION（M2 预检硬门主场景）。"""
    # 构造 tmp 项目：chapters/chapter-25.md 在盘、chapter-26.md 缺、volume_map 跨 25-26
    # 直调 _run_audit_wave_step 的预检段（或以 monkeypatch 截 dispatch 层断言不派发、
    # state 进 ESCALATION checkpoint）——实现形态以该文件既有 wave 预检测试为准沿用
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_audit_readiness.py -k "offset or bundle_follower" -v`
Expected: FAIL——`missing_audit_reads() got an unexpected keyword argument 'bundle'`（TypeError 先于断言：现行签名无 `bundle`）；wave 级用例失败于预检不报缺失（现行 `_resolve` 不识别 offset，字面花括号 probe 反而误报——两条合证语义缺口）。

- [ ] **Step 3: 实现 `_resolve` offset 解析 + `bundle` 条件语义**

`audit_layer.py` `missing_audit_reads` 改造（保留其余分支不动）：

```python
def missing_audit_reads(
    project_dir: Path | str,
    skill: str,
    chapter: int | None,
    *,
    bundle: list[int] | None = None,
) -> list[str]:
    """Required contract reads that do not exist for an audit dispatch (spec #105 T3).

    spec #109 a1/C1: ``chapter-{N+1}`` offset reads resolve via
    ``resolve_chapter_path`` (the naive ``str.replace`` never matched the
    brace form — the probe fell on a literal path that never exists, so every
    bundle wave would ESCALATION). Offset reads are REQUIRED only when the
    resolved chapter is inside ``bundle`` (singleton waves legally lack the
    follower: no volume_map / span end / uncovered span).
    """
```

内联 `_resolve` 替换为（**None 分支保留旧语义**——`resolve_chapter_path(path, None)` 对占位路径 raise `UnresolvedPathError`，会炸既有 `test_chapter_none_keeps_literal_placeholder`（test_audit_readiness.py:211-221 断言 `["chapters/N.md"]`）——I1）：

```python
    def _resolve(rel: object) -> str:
        raw = str(_entry_file(rel) if isinstance(rel, dict) else rel)
        if chapter is None:
            return raw.replace("chapter-N", "N")
        from shenbi.contracts.paths import resolve_chapter_path

        return resolve_chapter_path(raw, chapter)
```

（dict-entry 归一沿用 `_entry_file`；`produces` 集合同样受益。）循环内、`probe.exists()` 判定之前加 wave 条件语义：

```python
    offset_ch = _resolved_offset_chapter(rel, chapter)  # {N+1} → n+1；非 offset 形 → None
    if offset_ch is not None and (bundle is None or offset_ch not in bundle):
        continue  # spec #109 C1: offset read 在波外（singleton/卷尾）不探测
```

`_resolved_offset_chapter` 为模块级小助手：`_OFFSET_READ_RE = re.compile(r"chapter-\{N\+(\d+)\}")`，命中时返回 `chapter + int(m.group(1))`，否则 `None`（对 `chapter-N` 平文返回 `chapter` 会使语义退化——平文 read 永远必需，不进条件分支；`{N-k}` 负偏移今日零声明者，暂不展开——理论项记录在案）。

**同批接线 `:4114` 预检调用点**（I4——Task 1 自己产的门自己开，不留 Task 1→3 合入窗口的 fail-open）：`chapter_loop.py` 预检循环改 `_gaps = {gap for n in wave_chapters for gap in missing_audit_reads(project_dir, _skill, n, bundle=wave_chapters)}`。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/pipeline/test_audit_readiness.py -v`
Expected: PASS（新旧全绿——旧 #105 用例不受影响：它们不含 offset reads）。

- [ ] **Step 5: 写失败测试——六技能契约 reads 断言（load_contract 形态，非裸 grep）**

`tests/pipeline/test_audit_cluster.py` 追加：

```python
def test_audit_skills_declare_next_chapter_reads() -> None:
    """spec #109 T1: bundle auditors must DECLARE the follower chapter read."""
    from shenbi.contracts.loader import load_contract

    six = [
        "shenbi-review-group-craft",
        "shenbi-review-group-plan",
        "shenbi-review-group-factual",
        "shenbi-review-group-character",
        "shenbi-review-resonance",
        "shenbi-review-sensitivity",
    ]
    for s in six:
        reads = load_contract(s).get("reads", [])
        assert any(str(r).endswith("chapter-{N+1}.md") for r in reads), s
    for s in ("shenbi-review-group-craft", "shenbi-review-group-plan", "shenbi-review-resonance"):
        reads = load_contract(s).get("reads", [])
        assert any(str(r).endswith("chapter-{N+1}-plan.md") for r in reads), s
```

Run: `uv run pytest tests/pipeline/test_audit_cluster.py::test_audit_skills_declare_next_chapter_reads -v`
Expected: FAIL（六技能 reads 现均单章）。

- [ ] **Step 6: 编辑六技能契约 reads（plain-path 全文形，禁 dict-form fields）**

每个 SKILL.md 的 frontmatter `reads:` 列表、`chapters/chapter-N.md` 行后加 `- chapters/chapter-{N+1}.md`；group-craft/-plan/resonance 在 `plans/chapter-N-plan.md` 行后加 `- plans/chapter-{N+1}-plan.md`（factual/character/sensitivity 不加 plans——spec：按真实消费面，不虚增）。auto-generated「数据契约」块不动（`just generate` 再生）。

Run: `uv run pytest tests/pipeline/test_audit_cluster.py::test_audit_skills_declare_next_chapter_reads -v`
Expected: PASS。

- [ ] **Step 7: 生成物再生 + 契约对账门禁**

Run: `just generate && just check`
Expected: 全绿（deps.json 幂等 diff 吸收契约改动；lint_registry_reconcile/lint_decisions_sources/lint-contracts 自动纳入六技能新 reads）。

- [ ] **Step 8: Commit**

```bash
git add src/shenbi/pipeline/audit_layer.py skills/shenbi-review-group-craft/SKILL.md skills/shenbi-review-group-plan/SKILL.md skills/shenbi-review-group-factual/SKILL.md skills/shenbi-review-group-character/SKILL.md skills/shenbi-review-resonance/SKILL.md skills/shenbi-review-sensitivity/SKILL.md tests/unit/pipeline/test_audit_readiness.py tests/pipeline/test_audit_cluster.py <just generate 触发的生成物文件——按 `git status` 实列>
git commit -m "feat: spec #109 T1 契约 reads 对称化+预检 offset/wave 条件语义"
```

---

### Task 2: 派发组装双章化——bundle shared context + 双章 checklist（spec T2，infra）

**Files:**
- Modify: `src/shenbi/pipeline/audit_context_cache.py:60-138`（`build_shared_audit_context` 参数化）
- Modify: `src/shenbi/pipeline/chapter_loop.py:4067`（wave 调用点传 bundle）
- Modify: `src/shenbi/pipeline/review_checklist.py`（`generate_review_checklist` bundle 形 + `inject_checklist_into_prompt` 多块）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1347-1367`（checklist 注入点 bundle 化）
- Test: `tests/unit/pipeline/test_review_checklist.py`（扩展）
- Test: `tests/unit/pipeline/test_audit_context_cache.py`（新建或扩展——以现有该文件名为准，`ls tests/unit/pipeline/ | grep context` 先查）

**Interfaces:**
- Consumes: Task 1 的契约改动（reads 含 `{N+1}`）——`build_skill_prompt` 的 reads 循环（`dispatch_helper.py:857-868` `resolve_or_skip_ctx` 原生解析 `{N+1}`）自动把 follower 正文载入 prompt 与 reads manifest。
- Produces:
  - `build_bundle_audit_context(project_dir: Path, chapters: list[int]) -> SharedAuditContext`（raw_files 键=各章 `chapters/chapter-<n>.md` 项目相对 POSIX 路径；`chapter_text`=首章；ending_history 合并去重）；`build_shared_audit_context(project_dir, chapter)` 变为 `build_bundle_audit_context(project_dir, [chapter])` 的薄包装（签名不变，既有调用方零改动）。
  - `generate_bundle_checklist(project_dir: Path | str, chapters: list[int]) -> list[ReviewChecklist]`
  - `inject_checklist_into_prompt(prompt: str, checklists: ReviewChecklist | list[ReviewChecklist]) -> str`（单复数兼容；每章一块「## 审查参考数据」）。

- [ ] **Step 1: 写失败测试——bundle context 与双章 checklist**

```python
def test_bundle_audit_context_covers_follower_raw_files(tmp_path):
    from shenbi.pipeline.audit_context_cache import build_bundle_audit_context

    ch = tmp_path / "chapters"
    ch.mkdir()
    (ch / "chapter-25.md").write_text("锚章正文", encoding="utf-8")
    (ch / "chapter-26.md").write_text("随章正文", encoding="utf-8")
    ctx = build_bundle_audit_context(tmp_path, [25, 26])
    assert ctx.raw_files["chapters/chapter-25.md"] == "锚章正文"
    assert ctx.raw_files["chapters/chapter-26.md"] == "随章正文"


def test_inject_checklist_two_blocks(tmp_path):
    from shenbi.pipeline.review_checklist import ReviewChecklist, inject_checklist_into_prompt

    c25 = ReviewChecklist(chapter=25)  # 其余字段取默认——以 dataclass 实际必填字段为准补齐
    c26 = ReviewChecklist(chapter=26)
    out = inject_checklist_into_prompt("## Input Files\n- x", [c25, c26])
    assert out.count("## 审查参考数据") == 2
    assert '"chapter": 25' in out and '"chapter": 26' in out
```

（`ReviewChecklist` 必填字段以 `review_checklist.py` dataclass 实际定义为准——写 step 时打开补齐，禁凭空猜签名。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/ -k "bundle_audit_context or inject_checklist_two" -v`
Expected: FAIL — `build_bundle_audit_context` 不存在（ImportError）；`inject_checklist_into_prompt` 只接受单个 checklist（TypeError/单块）。

- [ ] **Step 3: 实现两函数**

`audit_context_cache.py`：新增 `build_bundle_audit_context(project_dir, chapters)`——现函数体整体移入、per-chapter 段（chapter_file 读取）改循环 `for n in chapters`，`chapter_text` 取 `chapters[0]`；world/character/style/hooks 各取一次（项目级）；`volume_context` 经 `_extract_volume_chapter(raw, chapters[0])` 取锚章节点（该提取是章参数化的——M5 定性修正；volume_context 零消费者，行为保持）；`ending_history` 循环范围 `min(chapters)-9 … max(chapters)`，其中 `k == chapter: text = ctx.chapter_text` 快捷分支改 `k == chapters[0]`（bundle 形下 chapter 变量已不存在——M7）。原 `build_shared_audit_context` 改为 `return build_bundle_audit_context(project_dir, [chapter])`。

`review_checklist.py`：`generate_review_checklist(project_dir, chapter, chapter_content=None)` 保持（单章缓存路径复用）；新增 `generate_bundle_checklist(project_dir, chapters)` = `[generate_review_checklist(project_dir, n) for n in chapters]`（各自走缓存）；`inject_checklist_into_prompt(prompt, checklists)` 归一 `checklists = [checklists] if isinstance(checklists, ReviewChecklist) else list(checklists)`，逐块在 `## Input Files` 前插入（多块时按章序连续插入，块序=chapters 序）。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/pipeline/ -k "bundle_audit_context or inject_checklist_two or review_checklist" -v`
Expected: PASS（新旧全绿）。

- [ ] **Step 5: 写失败测试——prompt 级 blob 断言（主防线）**

并入 `tests/pipeline/`（既有 build_skill_prompt 测试所在层——`grep -rl "build_skill_prompt" tests/pipeline/ | head` 先查，M4 防碎片化）：

```python
def test_wave_prompt_contains_follower_text_and_dual_checklist(tmp_path, monkeypatch):
    """spec #109 T2 判据：prompt 内 follower 正文与两章预计算块均在（blob 级）。"""
    # 构造 tmp 项目：genre-config.json + chapters/25+26 + plans/25+26 + truth/ 基本件
    # + outline/volume_map.md（bundle 跨 25-26）；随章正文含中文唯一锚串「随章正文独有锚串」
    ...
    from shenbi.pipeline.dispatch_helper import build_skill_prompt

    built = build_skill_prompt(
        "shenbi-review-group-craft", tmp_path, "Execute for chapters 25,26", chapter=25
    )
    manifest_paths = [r["path"] for r in built.reads_manifest]
    assert "chapters/chapter-26.md" in manifest_paths
    assert "随章正文独有锚串" in built.user  # follower 正文 blob 进 prompt（I2：字段名=user）
    assert built.user.count("## 审查参考数据") == 2  # 双章预计算块
```

（fixture 细节——`truth/pending_hooks.md` 空文件、`style/`、`world/rules.md` 按需补齐使组装不告警；正文串用中文唯一锚防撞。）

- [ ] **Step 6: 实现注入点与调用点改造**

`dispatch_helper.py:1347-1367`：`if is_review_skill(skill) and chapter is not None:` 内改 `checklists = generate_bundle_checklist(project_dir, bundle_chapters(project_dir, chapter))`（`from shenbi.pipeline.chapter_loop import bundle_chapters` 置函数内防环——以现有 import 风格为准，若已有既有局部导入先例则循它）；`chapter_content` 优化路径按 `raw_files.get(f"chapters/chapter-{n}.md")` 逐章传入（`generate_review_checklist` 支持则传，不支持则 None——不为本任务扩签名）。`inject_checklist_into_prompt(user_prompt, checklists)`。

`chapter_loop.py:4067`：`shared_ctx = build_bundle_audit_context(project_dir, wave_chapters)`（`wave_chapters` 已在 `:4092` 定义——把 shared_ctx 构造移到其后，或先算 `wave_chapters = bundle_chapters(project_dir, chapter)` 再构造）。

Run: `uv run pytest tests/pipeline/ -k "wave_prompt or built_prompt" -v && uv run pytest tests/pipeline/test_audit_cluster.py -v`
Expected: PASS。

- [ ] **Step 7: just check + Commit**

Run: `just check` → 全绿。

```bash
git add src/shenbi/pipeline/audit_context_cache.py src/shenbi/pipeline/review_checklist.py src/shenbi/pipeline/dispatch_helper.py src/shenbi/pipeline/chapter_loop.py tests/
git commit -m "feat: spec #109 T2 派发组装双章化——bundle shared context+双章 checklist+manifest 主防线断言"
```

---

### Task 3: 收口/路由 per-n 消费面 + 传感器换装（spec T3，infra）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:4216-4330`（wave 收口段——抽 `_wave_close_for_n`；**保留清单**：`_reset_retries` :4323、`_advance` :4324-4330、step_index 推进 :4254-4255、`_charge_wave_retries` :4282、`_failed_audit_skills`/step-done 环 :4241-4252——leader 位块原位保留，只替换 consolidation/summary/blocking_found/audit_reports/route 单章块为 per-n 循环；`_parse_and_persist_resonance` 移入循环 per-n 跑）
- Test: `tests/pipeline/test_audit_cluster.py`（扩展）

**Interfaces:**
- Consumes: `build_consolidator_sensors() -> tuple[re.Pattern, re.Pattern]`（parallel_dispatch.py:305）；`consolidate_review_results(results, chapter, skills, project_dir, cascade_skipped)`；`route_revision_after_resonance(state, project_dir, chapter)`（chapter_loop.py:3167）。
- Produces: `_wave_close_for_n(state: PipelineState, project_dir: Path, n: int, results: list[DispatchResult], skills: list[str], cascade_skipped: list[str]) -> None`——per-n summary 写盘（`audits/chapter-{n}-review-summary.md`）、`cs_n.audit_results["blocking_found"]` 用传感器扫 `chapter-{n}-*.md`（排除 review-summary 自身）判定、`route_revision_after_resonance(state, project_dir, n)` 调用。Task 5 在本函数产出的 `blocking_found` 基础上叠加 invalid 面。

- [ ] **Step 1: 写失败测试——follower BLOCKING 触发路由与状态写入**

```python
import shenbi.pipeline.chapter_loop as cl  # 模块顶部（M9）


@pytest.mark.integration
def test_wave_close_routes_follower_blocking(tmp_path, monkeypatch):
    """spec #109 T3 判据：follower 章 BLOCKING → 该 n blocking_found=True 且路由触发。"""
    # tmp 项目：chapters/25+26、volume_map bundle、audits/chapter-26-texture.md
    # 内容含 '**BLOCKING** 未核实：随章正文缺位' 维度报告锚定形
    routed: list[int] = []
    monkeypatch.setattr(cl, "route_revision_after_resonance", lambda s, p, n: routed.append(n))
    state = PipelineState.default(str(tmp_path))
    cl._wave_close_for_n(
        state, tmp_path, 26, results=[], skills=["shenbi-review-group-craft"], cascade_skipped=[]
    )
    cs26 = state.chapter_loop.chapter_states["26"]
    assert cs26.audit_results["blocking_found"] is True
    assert 26 in routed
    assert (tmp_path / "audits" / "chapter-26-review-summary.md").exists()
```

（`results=[]` 合法——空派发集时 summary 走文件扫描面。M8 行为变更注记：per-n `audit_reports` 从「声明全集」变为「在盘 glob 集」——唯一消费面 `collect_audit_issues` 自行 glob 不读该键，无回归面。）

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_audit_cluster.py::test_wave_close_routes_follower_blocking -v`
Expected: FAIL — `_wave_close_for_n` 未定义（ImportError/AttributeError）。

- [ ] **Step 3: 实现 `_wave_close_for_n` 并改 wave 收口段**

`chapter_loop.py` 在 `_run_audit_wave_step` 内（或其旁）新增：

```python
def _wave_close_for_n(state, project_dir, n, results, skills, cascade_skipped) -> None:
    """Per-n audit close for the wave path (spec #109 T3).

    The serial loop's ``_run_audit_close_for_chapter`` is unreachable under
    the wave interception (:3995-3996); this is its wave equivalent minus the
    genre re-dispatch (run_audit_layer would re-dispatch wave-2 skills —
    d1/d2: reuse the wave task surface instead).
    """
    from shenbi.pipeline.parallel_dispatch import (
        build_consolidator_sensors,
        consolidate_review_results,
    )

    consolidated = consolidate_review_results(
        results,
        n,
        skills=skills,
        project_dir=project_dir,
        cascade_skipped=sorted(set(cascade_skipped)) or None,
    )
    safe_write(project_dir / "audits" / f"chapter-{n}-review-summary.md", consolidated)
    blocking_re, _critical_re = build_consolidator_sensors()
    reports = [
        p
        for p in sorted((project_dir / "audits").glob(f"chapter-{n}-*.md"))
        if "review-summary" not in p.name
    ]
    cs = _get_chapter_state(state, n)
    cs.audit_results["blocking_found"] = ("## BLOCKING Issues" in consolidated) or any(
        blocking_re.search(p.read_text(encoding="utf-8")) for p in reports if p.is_file()
    )
    cs.audit_results["audit_reports"] = [f"audits/{p.name}" for p in reports]
    route_revision_after_resonance(state, project_dir, n)
```

wave 收口段（现 `:4216-4274`）改为：leader 侧 G3 记录与 `_wave_audit_entry` 循环保留；consolidation/summary/`blocking_found`/`audit_reports`/`_parse_and_persist_resonance`/`route` 原单章块替换为 `for n in wave_chapters: _wave_close_for_n(...)`（`_parse_and_persist_resonance(state, project_dir, n, source="parallel_wave")` 移入循环内 per-n 跑——resonance 报告两章各有，trend 行 per-n）。`:4266-4271` 字面 H2 传感器块整删（传感器换装 f 项）。

- [ ] **Step 4: 跑测试确认通过 + 既有 wave 测试回归**

Run: `uv run pytest tests/pipeline/test_audit_cluster.py tests/unit/pipeline/test_chapter_loop.py -v`
Expected: PASS 全绿（既有 anchor 收口行为迁移为 per-n 后，anchor 章结果不变）。

- [ ] **Step 5: anchor 等价性回归测试**

```python
def test_wave_close_anchor_equivalence(tmp_path, monkeypatch):
    """per-n 化后 anchor 章收口行为不变（blocking/路由/summary 仍写）。"""
    # 同上 fixture，BLOCKING 写在 chapter-25-texture.md；断言 25 路由、26 不路由
```

- [ ] **Step 6: just check + Commit**

Run: `just check` → 全绿。

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/pipeline/test_audit_cluster.py
git commit -m "feat: spec #109 T3 收口/路由 per-n 消费面+传感器换装（wave 等价物复活 serial per-n 环）"
```

---

### Task 4: 词族家=src + starve_verdict 校验器 + 写路径接线（spec T4a，infra）

**Files:**
- Create: `src/shenbi/pipeline/audit_starve_family.py`
- Modify: `tools/audit_starve_baseline.py`（常量改 import 自 src）
- Modify: `src/shenbi/pipeline/llm_output_integrity.py`（新增 `check_audit_starve_verdict`）
- Modify: `src/shenbi/pipeline/dispatch_helper.py:2982-2992`（写路径 `if is_audit:` 块加第五查器）
- Modify: `src/shenbi/gates/g4/generic.py:257`（`_revalidate_finding` 加 `G4.av.starve_verdict → check_audit_starve_verdict(target)` 复验路由——**不改 `_POST_WRITE_FAIL_PREFIXES`**：`"G4.av."` 广前缀已覆盖 FAIL 分类（generic.py:205-210），追加条目是 no-op（I3）；路由分支消除未识别 `G4.av.*` 的保守放行 WARN 噪音，#105 dispatch_integrity 路由先例 ：257 同位）
- Test: `tests/unit/pipeline/test_llm_output_integrity.py`（扩展）
- Test: `tests/unit/tools/test_audit_starve_baseline.py`（常量单源断言——M3：删 manifest 骨架测试，真 manifest 证=Step 5 实弹复验）

**Interfaces:**
- Consumes: `check_audit_dispatch_integrity(path) -> list[str]` 的发射格式（`f"G4.av.dispatch_integrity:{path.name} — L{ln}:…"`）与写路径接线先例；`_revalidate_finding` 的 per-id 复验路由（generic.py:257，#105 dispatch_integrity 路由先例同位——**不动 `_POST_WRITE_FAIL_PREFIXES`**，`"G4.av."` 广前缀已覆盖 FAIL 分类）。
- Produces:
  - `audit_starve_family.NARROW6: tuple[str, ...]` / `WIDE12: tuple[str, ...]` / `T4_VARIANTS: tuple[str, ...]` / `PRODUCTION_FAMILY: tuple[str, ...]`（= NARROW6+T4_VARIANTS）/ `VERDICT_LINE_RE: re.Pattern[str]`（`^\s*(?:[-*>|#]+\s*)?\*\*判定\*\*\s*[：:]\s*(.*)$`，MULTILINE）
  - `check_audit_starve_verdict(path: Path) -> list[str]`——**全部判定行值段**锚定（`VERDICT_LINE_RE.finditer`，非首行——生产门语义；基线/回放的首行语义由工具侧消费形态区分）×`PRODUCTION_FAMILY`；finding 形如 `f"G4.av.starve_verdict:{path.name} — L{ln}:判定行饿死形态「{token}」（输入缺口——不得出具判定）——按输入缺口重派"`（M2：以 Step 3 代码版为准，本行与代码逐字一致）。
  - 工具侧：`tools/audit_starve_baseline.py` 删本地 NARROW6/WIDE12/T4_VARIANTS/VERDICT_LINE 定义，改 `sys.path.insert(0, str(REPO / "src"))` + `from shenbi.pipeline.audit_starve_family import ...`（lint_decisions_sources.py 先例）；**manifest 值不变**（Task 7 以 `--verify-manifest d9a1b5f0…f5c2` 复验）。

- [ ] **Step 1: 写失败测试——常量单源 + 校验器三形态**

```python
# tests/unit/pipeline/test_llm_output_integrity.py
def test_starve_verdict_catches_placeholder_pass(tmp_path):
    p = tmp_path / "chapter-48-memo-compliance.md"
    p.write_text("# 审\n\n**判定**: 通过（附条件）\n", encoding="utf-8")
    issues = check_audit_starve_verdict(p)
    assert any("starve_verdict" in i and "附条件" in i for i in issues)


def test_starve_verdict_catches_section_starvation_not_first_line(tmp_path):
    """ch45 形：首判定行通过、第 N 判定行饿死——全判定行锚定必须检出（I1）。"""
    p = tmp_path / "chapter-45-reader-pull.md"
    p.write_text(
        "# 审\n\n**判定**: 通过\n\n## 节\n\n- **判定**: 无法评估（数据未注入），不判缺陷。\n",
        encoding="utf-8",
    )
    assert any("starve_verdict" in i for i in check_audit_starve_verdict(p))


def test_starve_verdict_clean_pass_and_prose_mention_untouched(tmp_path):
    """6 假阳类：值段干净 + 散文提及豁免。"""
    p = tmp_path / "chapter-1-pacing.md"
    p.write_text(
        "# 审\n\n**判定**: 通过（有 MINOR 瑕疵，不阻断）\n\n散文：本条规则不适用（单章，多章窗口）。\n",
        encoding="utf-8",
    )
    assert check_audit_starve_verdict(p) == []


# tests/unit/tools/test_audit_starve_baseline.py
def test_tool_families_single_source_with_src():
    import tools.audit_starve_baseline as tool
    from shenbi.pipeline.audit_starve_family import NARROW6, T4_VARIANTS, VERDICT_LINE_RE

    assert tool.NARROW6 == NARROW6
    assert tool.T4_VARIANTS == T4_VARIANTS
    assert tool.VERDICT_LINE.pattern == VERDICT_LINE_RE.pattern


def test_tool_family_regexes_built_from_imported_constants():
    """FAMILY 正则由 import 常量构造（防工具侧再起词表双源）。"""
    import tools.audit_starve_baseline as tool
    from shenbi.pipeline.audit_starve_family import NARROW6, WIDE12

    assert tool.FAMILY["narrow6"].pattern == "|".join(NARROW6)
    assert tool.FAMILY["wide12"].pattern == "|".join(WIDE12)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_llm_output_integrity.py -k starve -v && uv run pytest tests/unit/tools/test_audit_starve_baseline.py -v`
Expected: FAIL — 模块/函数不存在（ImportError）。

- [ ] **Step 3: 实现 `audit_starve_family.py` + 校验器 + 接线**

`audit_starve_family.py`（常量逐字从现 `tools/audit_starve_baseline.py` 搬移——值即单源）：

```python
"""Starvation-marker word families and the verdict-line anchor (spec #109).

Single source for the T4 production gate and the replay/baseline tool —
the spec's prose is a gloss, never authoritative (spec appendix A; erratum).
"""

from __future__ import annotations

import re

NARROW6: tuple[str, ...] = ("待补", "不适用", "无法核对", "附条件", "待正文核验", "正文未提供")
WIDE12: tuple[str, ...] = (
    *NARROW6,
    "待核验",
    "无法验证",
    "无法评估",
    "正文缺失",
    "未能提供",
    "未提供正文",
)
T4_VARIANTS: tuple[str, ...] = ("待核", "暂记", "留待后续核验", "建议复核", "数据未注入")
PRODUCTION_FAMILY: tuple[str, ...] = (*NARROW6, *T4_VARIANTS)
VERDICT_LINE_RE: re.Pattern[str] = re.compile(
    r"^\s*(?:[-*>|#]+\s*)?\*\*判定\*\*\s*[：:]\s*(.*)$", re.MULTILINE
)
```

`llm_output_integrity.py` 加：

```python
def check_audit_starve_verdict(path: Path) -> list[str]:
    """Invalidate reports whose verdict lines carry starvation markers (spec #109 T4).

    Production anchor = ALL verdict lines' value segments (spec I1: ch45-form
    markers sit on the 8th verdict line — a first-line anchor never sees
    them). Prose mentions never count (ch9 form); baseline/replay's
    first-line semantics are the TOOL's consumption mode, same regex.
    """
    from shenbi.pipeline.audit_starve_family import PRODUCTION_FAMILY, VERDICT_LINE_RE

    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    for m in VERDICT_LINE_RE.finditer(text):
        value = m.group(1)
        for token in PRODUCTION_FAMILY:
            if token in value:
                ln = text.count("\n", 0, m.start()) + 1
                issues.append(
                    f"G4.av.starve_verdict:{path.name} — L{ln}:判定行饿死形态「{token}」"
                    "（输入缺口——不得出具判定）——按输入缺口重派"
                )
                break
    return issues
```

`dispatch_helper.py` `if is_audit:` 块（`check_audit_dispatch_integrity` 行后）加 `issues += check_audit_starve_verdict(full_path)`（import 随该块现有局部 import 风格）。`generic.py` `_revalidate_finding` 加路由分支 `G4.av.starve_verdict → check_audit_starve_verdict(target)`（:257 #105 dispatch_integrity 路由同位——消除未识别 `G4.av.*` 的保守放行 WARN 噪音；**FAIL 分类零改动**：`"G4.av."` 广前缀天然覆盖）。工具侧迁移（Interfaces 所述）。

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/pipeline/test_llm_output_integrity.py tests/unit/tools/test_audit_starve_baseline.py -v`
Expected: PASS。

- [ ] **Step 5: manifest 复验（I2 迁移值不变的实弹证）**

Run: `uv run python tools/audit_starve_baseline.py novel-xinghuo-vol1/audits --verify-manifest d9a1b5f011127306bd38d2cdfe17c4571fc09c9fb402d1a7056f6ef9ae20f5c2`
Expected: exit 0（报告打印，无 mismatch 报错）。

- [ ] **Step 6: just check + Commit**

Run: `just check` → 全绿。

```bash
git add src/shenbi/pipeline/audit_starve_family.py src/shenbi/pipeline/llm_output_integrity.py src/shenbi/pipeline/dispatch_helper.py src/shenbi/gates/g4/generic.py tools/audit_starve_baseline.py tests/
git commit -m "feat: spec #109 T4a 词族家=src 单源+starve_verdict 校验器（全判定行锚定）+写路径接线+G4 复验路由"
```

---

### Task 5: invalid 第三态消费——wave entry valid 维度/cascade/done 面/summary 披露（spec T4b，infra）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:3075-3091`（`_wave_audit_entry`）、`:4241-4252`（done 面）、`:691-749`（`should_skip_audit`）、`:765-790`（`_get_audit_history` 写入侧形状）
- Modify: `src/shenbi/pipeline/parallel_dispatch.py:336-459`（`consolidate_review_results` 披露行）
- Test: `tests/unit/pipeline/test_chapter_loop.py`（扩展——`should_skip_audit` invalid 断言）
- Test: `tests/pipeline/test_audit_cluster.py`（扩展——entry valid/summary 披露）

**Interfaces:**
- Consumes: Task 4 的期刊 finding 前缀 `G4.av.starve_verdict`（+ 既有 `G4.av.dispatch_integrity`）；`.integrity-findings-{n}.jsonl` 行形 `{"file": rel, "finding": str}`——**期刊按被写文件自身章号分卷**（`_append_integrity_findings` :1955-1976，grouped 技能的 follower finding 落 `.integrity-findings-26.jsonl` 而非 leader 卷）；FAIL 分类单源复用 `gates/g4/generic.py` 的 `_POST_WRITE_FAIL_PREFIXES`（含 `fence_imbalance` WARN 例外——`G4.av.*` 全 FAIL 类）；`_wave_savepoint` 形状（不动——write-only 取证）。
- Produces:
  - `_wave_audit_entry(task_success: bool, hard: int, report_paths: list[str], project_dir: Path) -> dict`——返回 dict 增键 `"valid": bool`（默认 True；**对 report_paths 中每个文件按其自身章号查对应期刊卷**（C1：首路径提取只读 leader 卷，follower invalid 恒漏），任一文件命中 FAIL 类 finding → False）与既有 `passed`（语义=派发成功∧hard==0，**不含** valid——三态正交）。
  - `should_skip_audit(...)`——streak 判定加第五关：`recent` 任一 `r.get("valid") is False` → `return False`（invalid 不进 streak）。
  - wave done 面：`_failed_audit_skills` 旁增 `_invalid_audit_skills`（`cs.audit_results[short].get("valid") is False` 的技能集）；`:4250-4252` 排除条件改为 `not in _failed_audit_skills and not in _invalid_audit_skills`。
  - `consolidate_review_results(..., invalid_reports: list[str] | None = None)`——`failed_count > 0 or invalid_reports` 时禁净结论句，改渲染披露行：`- **输入缺口（invalid 产物）**: {len(invalid_reports)} 份（{names}）——不计通过、不构成净结论`；净结论句条件改 `if not blocking_lines and not critical_lines and failed_count == 0 and not invalid_reports`。

- [ ] **Step 1: 写失败测试（spec T4 判据三条）**

```python
# test_chapter_loop.py
def test_should_skip_audit_rejects_invalid_streak():
    """invalid 不进 cascade streak——含 invalid 的三连胜不跳。"""
    from shenbi.pipeline.chapter_loop import should_skip_audit

    hist_ok = [
        {"skill": "texture", "chapter": c, "passed": True, "hard_failures": 0, "valid": True}
        for c in (1, 2, 3)
    ]
    assert should_skip_audit("texture", hist_ok, current_chapter=4) is True
    hist_bad = [dict(r, valid=False) for r in hist_ok]
    assert should_skip_audit("texture", hist_bad, current_chapter=4) is False


# test_audit_cluster.py
def test_wave_audit_entry_invalid_from_journal(tmp_path):
    (tmp_path / "audits").mkdir()
    rep = tmp_path / "audits" / "chapter-26-texture.md"
    rep.write_text("**判定**: 待补（正文未提供）\n", encoding="utf-8")
    (tmp_path / "audits" / ".integrity-findings-26.jsonl").write_text(
        json.dumps(
            {"file": "audits/chapter-26-texture.md", "finding": "G4.av.starve_verdict:…"},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    entry = cl._wave_audit_entry(True, 0, ["audits/chapter-26-texture.md"], tmp_path)
    assert entry["passed"] is True and entry["valid"] is False  # 三态正交


def test_wave_audit_entry_grouped_follower_journal(tmp_path):
    """C1：grouped 技能产物集跨 25/26 两章——follower 卷的 FAIL 必须命中 valid=False。"""
    (tmp_path / "audits").mkdir()
    paths = ["audits/chapter-25-texture.md", "audits/chapter-26-texture.md"]
    for rel in paths:
        (tmp_path / rel).write_text("**判定**: 通过\n", encoding="utf-8")
    (tmp_path / "audits" / ".integrity-findings-26.jsonl").write_text(
        json.dumps(
            {"file": "audits/chapter-26-texture.md", "finding": "G4.av.starve_verdict:…"},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    entry = cl._wave_audit_entry(True, 0, paths, tmp_path)
    assert entry["valid"] is False  # 首路径=25 卷无 finding——按文件逐卷查才不漏


def test_consolidate_disclosure_when_failed_or_invalid():
    from shenbi.pipeline.parallel_dispatch import consolidate_review_results

    out = consolidate_review_results([], 26, invalid_reports=["chapter-26-texture.md"])
    assert "No BLOCKING or CRITICAL issues found" not in out
    assert "输入缺口" in out and "chapter-26-texture.md" in out


def test_done_face_excludes_invalid_skill(tmp_path, monkeypatch):
    """re-review 轮 2 Minor#1：当波 invalid 技能不当 done（done 面在 entry 循环前——
    _invalid_audit_skills 必须与 _failed_audit_skills 同段内联计算，不依赖 entry 循环产物）。"""
    # tmp 项目 + wave 预检/派发桩（沿用该文件既有 wave 桩手法）；构造 group-craft
    # 全部产物在盘、chapter-26-texture.md 饿死形 + 期刊 FAIL 记录；
    # 跑 _run_audit_wave_step 后断言 state 中 anchor/follower 的 audit step-done
    # 不含 shenbi-review-group-craft（invalid 排除），而 cascade 其它面照常。
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py -k invalid_streak -v && uv run pytest tests/pipeline/test_audit_cluster.py -k "invalid_from_journal or grouped_follower or disclosure or done_face" -v`
Expected: FAIL（`valid` 键不存在/streak 不看 valid/披露行不存在/done 面 invalid 排除无断言——四红）。

- [ ] **Step 3: 实现四处**

`_wave_audit_entry` valid 判定（C1 逐文件逐卷查期刊——期刊即时计算路线，I7 落码；**返回命中 rel-path 列表**而非 bool——re-review 新破坏#1：按 `audit_suffix` 重构的名字对 grouped 技能是 phantom 路径，披露行必须点名真实产物文件）：

```python
def _fail_findings_for_reports(report_paths: list[str], project_dir: Path) -> list[str]:
    """Report files carrying FAIL-class post-write findings (spec #109 T4b).

    Returns the offending project-relative report paths (deduped, in input
    order). The journal is VOLUMED BY THE WRITTEN FILE'S OWN CHAPTER
    (_append_integrity_findings) — a grouped skill's follower findings live in
    ``.integrity-findings-26.jsonl`` while the first report path is 25: the
    lookup must walk EVERY report path against ITS OWN volume (C1). FAIL
    classification reuses the G4 single source (prefixes + the single WARN
    exception).
    """
    import json as _json

    from shenbi.gates.g4.generic import _POST_WRITE_FAIL_PREFIXES  # pyright: ignore[reportPrivateUsage]

    hits: list[str] = []
    for rel in report_paths:
        m = re.search(r"chapter-(\d+)", rel)
        if m is None:
            continue
        journal = project_dir / "audits" / f".integrity-findings-{m.group(1)}.jsonl"
        if not journal.is_file():
            continue
        for line in journal.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = _json.loads(line)
            except _json.JSONDecodeError:
                continue  # torn tail (crash) — same tolerance as the G4 reader
            if str(entry.get("file", "")) != rel:
                continue
            finding = str(entry.get("finding", ""))
            if finding.startswith("G4.pi.fence_imbalance"):
                continue  # the single WARN class
            if any(finding.startswith(p) for p in _POST_WRITE_FAIL_PREFIXES):
                if rel not in hits:
                    hits.append(rel)
                break
    return hits
```

（pyright 私有 import 注记沿用 `src/shenbi/facts/settle_ops.py:39` 先例——re-review 注记#4。）

`_wave_audit_entry` 内、返回前加 `entry["valid"] = not _fail_findings_for_reports(report_paths, project_dir)`。`_wave_close_for_n`（Task 3）调 consolidate 处**内联计算**（消解顺序依赖——entry 循环在 consolidation 之后，不从 entry 产物取）：`invalid_reports=[p for p in _fail_findings_for_reports([f"audits/{f.name}" for f in reports], project_dir)]`——`reports` 即该 n 的在盘 glob 集，命中名全为真实产物文件。done 面改造（re-review 轮 2 Minor#1：done 面在 entry 循环**之前**，`_invalid_audit_skills` 不得依赖 entry 产物）：与 `_failed_audit_skills` 同段（`:4241-4249` zip 循环处）内联计算 `_invalid_audit_skills = {task.skill for task in core_wave + core_serial + genre_wave + genre_serial if _fail_findings_for_reports(list(task.all_output_paths()), project_dir)}`；`:4250-4252` 排除条件 `not in _failed_audit_skills and not in _invalid_audit_skills`。`_get_audit_history` 提取侧加 `"valid": audit_result.get("valid", True)`。

- [ ] **Step 4: 跑测试确认通过 + 回归**

Run: `uv run pytest tests/unit/pipeline/test_chapter_loop.py tests/pipeline/test_audit_cluster.py tests/unit/pipeline/test_parallel_dispatch*.py -v`（parallel_dispatch 测试文件名以 `ls tests/unit/pipeline/ | grep parallel` 实列为准）
Expected: PASS 全绿。

- [ ] **Step 5: just check + Commit**

Run: `just check` → 全绿。

```bash
git add src/shenbi/pipeline/chapter_loop.py src/shenbi/pipeline/parallel_dispatch.py tests/
git commit -m "feat: spec #109 T4b invalid 第三态消费——wave entry valid/cascade streak/done 面/summary 缺口披露"
```

---

### Task 6: resume invalid 感知补跑（spec T5，infra）

**Files:**
- Modify: `src/shenbi/pipeline/chapter_loop.py:393-399`（`_filter_completed_audit_tasks`）
- Test: `tests/pipeline/test_audit_cluster.py`（crash-replay 集成测试）

**Interfaces:**
- Consumes: Task 4 `check_audit_starve_verdict` + 期刊（双源判定：期刊有 FAIL finding **或** 现盘文件重查器命中 → invalid——期刊为准、重查兜底，两者取或）。
- Produces: `_filter_completed_audit_tasks(tasks: list[ReviewTask], project_dir: Path) -> list[ReviewTask]`——签名加 `project_dir`（调用点 `:4162/:4201` 同步传）；完成判据=全部产物在盘 **且** 无 invalid 产物。

- [ ] **Step 1: 写失败测试——crash-replay（spec T5 判据）**

```python
@pytest.mark.integration
def test_resume_redispatches_invalid_follower_report(tmp_path):
    """mid-wave crash 重放：invalid 产物 → 该技能任务不视为完成 → 重派且带全输入。"""
    # tmp 项目 bundle 25-26；audit_report_paths(25, group-craft) 全部 6 条产物在盘
    # （25/26 × texture/reader-pull/anti-ai——I5：必须全部在盘，否则存在性分支先命中、
    # 红测因错误理由通过）；仅 audits/chapter-26-texture.md 内容为饿死形
    # （**判定**: 待补（正文未提供））；期刊无记录（crash 前写路径钩子未跑——重查器兜底路径）
    task = ReviewTask(
        skill="shenbi-review-group-craft",
        project_dir=tmp_path,
        prompt="cluster",
        output_path="audits/chapter-25-texture.md",
        output_paths=audit_report_paths(25, "shenbi-review-group-craft"),
    )
    remaining = cl._filter_completed_audit_tasks([task], tmp_path)
    assert [t.skill for t in remaining] == ["shenbi-review-group-craft"]  # invalid → 不算完成
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/pipeline/test_audit_cluster.py::test_resume_redispatches_invalid_follower_report -v`
Expected: FAIL——现行纯存在性过滤把该任务视为完成（remaining 为空）。

- [ ] **Step 3: 实现 invalid 感知过滤**

```python
def _filter_completed_audit_tasks(tasks: list[ReviewTask], project_dir: Path) -> list[ReviewTask]:
    """C30 F377 + spec #109 T5: drop audit tasks whose outputs all exist AND are valid.

    Existence alone marks starved/invalid follower products complete — the
    resume path never re-dispatches them. Validity = no FAIL-class journal
    finding on any output OR (fallback) a fresh starve-verdict re-check of
    the on-disk file (journal may be absent/torn after a crash).
    """
    from shenbi.pipeline.llm_output_integrity import check_audit_starve_verdict

    out: list[ReviewTask] = []
    for t in tasks:
        paths = [t.project_dir / p for p in t.all_output_paths()]
        if not all(p.exists() for p in paths):
            out.append(t)
            continue
        if any(check_audit_starve_verdict(p) for p in paths):
            out.append(t)  # invalid product → re-dispatch with full inputs
    return out
```

（期刊检查并入：命中 `.integrity-findings-{n}.jsonl` 的 FAIL 行同判 invalid——实现时以最短路径合并两源，保持纯读幂等。）

- [ ] **Step 4: 跑测试确认通过 + 回归（C30 既有 resume 测试）**

Run: `uv run pytest tests/pipeline/test_audit_cluster.py -v && uv run pytest tests/ -k "filter_completed or resume" -v`
Expected: PASS 全绿。

- [ ] **Step 5: just check + Commit**

Run: `just check` → 全绿。

```bash
git add src/shenbi/pipeline/chapter_loop.py tests/pipeline/test_audit_cluster.py
git commit -m "feat: spec #109 T5 resume invalid 感知补跑——存在性过滤升级双源 validity"
```

---

### Task 7: 差分回放离线仲裁 + AC 证据汇总（spec 验收#2/#3/#4，执行面）

**Files:**
- 无 src 改动；产出：`.superpowers/sdd/2026-11-15-spec109-audit-bundle-coverage/replay-report.md`（工作态，不入库）

**Interfaces:**
- Consumes: `tools/audit_starve_baseline.py`（manifest+基线）、Task 4 `check_audit_starve_verdict`。
- Produces: 回放仲裁报告（验收#2 证据）+ progress.md 验收证据段。

- [ ] **Step 1: 基线复现（语料冻结证）**

Run: `uv run python tools/audit_starve_baseline.py novel-xinghuo-vol1/audits --verify-manifest d9a1b5f011127306bd38d2cdfe17c4571fc09c9fb402d1a7056f6ef9ae20f5c2`
Expected: exit 0；判定行口径 47@窄6/85@扩12（全偶零奇）、文件级 114/157、verdict_pass 偶位 23/24——与 spec 快照逐位一致。

- [ ] **Step 2: 生产校验器全量回放（离线，只读）**

```bash
uv run python -I -c "
from pathlib import Path
from shenbi.pipeline.audit_starve_family import VERDICT_LINE_RE, NARROW6, WIDE12
from shenbi.pipeline.llm_output_integrity import check_audit_starve_verdict
# 1) 生产口径 invalid 清单（全判定行 × PRODUCTION_FAMILY）——只报告不设阈值（M1）
# 2) 一致性子集断言：基线窄6首行 47 文件集 ⊆ 生产 invalid 集；扩12 85 文件集 ⊆ 生产 invalid 集
#    （首行饿死 ⊂ 全行饿死 ∧ 窄词族 ⊂ 生产词族——必然子集，若不成立=锚定实现错）
"
```

Expected: 子集断言全过；生产计数入 replay-report.md（报告面：全偶分布、词族分布、ch45/ch49 形命中清单）。

- [ ] **Step 3: 验收#3/#4 证据核对**

- #3：Task 4 三红测（占位/编造通过/节段饿死判定行形）+ Task 2 blob 断言（第四形态输入断言）+ ch49 形=T2 预防单侧（spec 显式声明）——测试名清单入 replay-report。
- #4：双章 fixture dry-run 全链（Task 2 Step 5 测试 + Task 3 集成测试 + Task 6 crash-replay）——产物 valid 断言在 Task 5/6 测试内。

- [ ] **Step 4: 验收 5 挂账声明（F947）**

progress.md 记：验收 5（T2 生成测试 ≥94，G3.4 独立评分）依赖付费实弹——**随用户令挂账**（#106 AC4 先例），离线结构断言（Task 2 blob 级）为替代交付。

- [ ] **Step 5: 汇总写入 progress.md `## 验收证据`（命令+输出逐条粘贴）**

---

## Self-Review 结论（含阶段 5 审查修复轮 2026-11-18）

1. **Spec 覆盖**：T1→Task 1；T2→Task 2；T3→Task 3；T4→Task 4+5；T5→Task 6；验收#1（判据全绿）=各 task 测试+Task 7；#2=Task 7 Step 1-2；#3=Task 4/2 红测+Task 7 Step 3；#4=Task 2/3/6 集成测试；#5=Task 7 Step 4 挂账（F947）。无缺口。
2. **占位符扫描**：Task 2 Step 1 的 `ReviewChecklist(chapter=25)` 现即合法（仅 chapter 必填——阶段 5 审查亲验）；其余步骤均含真码/真命令/期望输出。
3. **类型一致性**：`_wave_close_for_n`（Task 3 产、Task 5 消费 invalid_reports 参数——名单来源=per-skill entry valid 面）；`check_audit_starve_verdict`（Task 4 产、Task 6 消费）；`bundle=` 参数（Task 1 产、**Task 1 自己接线 `:4114`**——无跨 task 隐式依赖窗口）。
4. **阶段 5 审查修复轮**（两轮 re-review 后终态）：C1（`_fail_findings_for_reports` 期刊按文件逐卷查——grouped follower 盲视修复+grouped 红测+**返回真名列表**供披露行点名真实产物——re-review 轮 2 新破坏#1）；I1（`_resolve` None 分支保留旧语义）；I2（`built.user`）；I3（generic.py 改 `_revalidate_finding` 路由、Step 3/Interfaces/commit message 三处旧「FAIL 前缀追加」指令全清——re-review 轮 2 I3 残留补清）；I4（`:4114` 归属 Task 1+wave 级红测）；I5（Task 6 fixture 全 6 产物在盘）；I6（monkeypatch loader 手法+删物理 SKILL.md 死码）；I7（落码+FAIL 分类单源 import+私有 import pyright 注记）；M1-M9 全落（保留清单/文案统一/骨架测试删/测试并入 tests/pipeline/**volume 章参数化定性**/**ending_history `k==chapters[0]` 快捷分支适配**/audit_reports 语义注记/cl import——M5/M7 正文实落，re-review 轮 2 指认的虚报已补齐）；顺序依赖消解（invalid_reports 内联计算，不走 entry 产物）。
