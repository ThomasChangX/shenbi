# Phase 1: Pipeline 阻塞性缺陷根因修复 Spec

> **日期:** 2026-07-06
> **状态:** 设计中
> **前置:** `docs/superpowers/specs/2026-07-02-novel-pipeline-root-cause-fixes-design.md` (根因分析), `docs/superpowers/specs/2026-07-01-novel-pipeline-design.md` (原始 spec)
> **目的:** 以最小改动修复 8 个 Category A 阻塞性缺陷，使 Pipeline 能端到端跑通 20 万字种子，为 Phase 2 架构升级建立稳定基线

## 1. 背景

Pipeline 首次实施 (Wave 1-5) 完成后，2026-07-02 的根因分析发现了 55 个缺陷，其中 8 个 Category A 缺陷会阻塞管线完成端到端小说生成。

两个 PR (#13, #14) 修复了部分可靠性问题（escalation loop、folder stability、`--auto` mode），但 8 个 Category A 缺陷的核心逻辑未被修复：

- **A3**: genre-config 审计矩阵键名不匹配 — 0 个审计维度激活
- **A8**: 审计层 TODO(W3T4) 未接线 — 题材圈/边界圈审计代码写了但从未运行
- **A7**: state-settling G4 验证空操作 — 最关键步骤的结构验证被跳过
- **A5**: error_handler 三个函数未接线 — 错误处理代码写了但从未调用
- **A4**: escalation-review dispatch 未接线 — 升级决策没有分析报告支撑
- **A2**: resonance 评分解析器缺失 — 评分永远为 None，阈值检查空转
- **A1**: total_chapters 动态重算缺失 — 卷边界扩展后章节总数未更新
- **A6**: MODIFY 决策 = APPROVE — 人工反馈被静默丢弃

## 2. 总体策略

### 2.1 实施原则

**每次只改一个缺陷，改完立即验证，验证通过才进入下一个。**

这是 Toyota Kata 的持续改进方法和 Continuous Delivery 的增量部署原则——不在设计阶段规划所有细节，在每个修复步骤获得真实反馈后调整下一步。

### 2.2 依赖链

```
Step 1: A3 (审计矩阵)
    ↓ 必须先对齐，否则 A8 空跑
Step 2: A8 (审计层接线)
    ↓ 审计必须先工作，否则 A5 的审计错误处理路径无意义
Step 3: A7 (state-settling G4)
    ↓ 独立，但受益于 A8 的审计层验证 state-settling 输出
Step 4: A5 (错误处理接线)
    ↓ 独立
Step 5: A4 (escalation-review)
    ↓ 依赖 A5 的错误处理路径就位
Step 6: A2 (resonance 解析器)
    ↓ 独立
Step 7: A1 (total_chapters 重算)
    ↓ 独立
Step 8: A6 (MODIFY 决策)
    ↓ 独立
Step 9: 金丝雀验证 (3章→10章→20万字)
```

### 2.3 每个 Step 的验证标准

```
改 1 个缺陷 → 跑该模块的单元测试 → 跑全量单元测试 → 跑 3 章金丝雀
```

任一阶段失败即停止，不允许带着已知失败进入下一步。

## 3. 详细设计

### Step 1: A3 — genre-config 审计矩阵对齐

**文件:** `src/shenbi/pipeline/audit_layer.py`

**问题:** `GENRE_ACTIVATION_MATRIX` 使用 snake_case 键名，读取 `audit_dimensions` (snake_case)，但与真实 `genre-config.json` fixture 的 `auditDimensions` (camelCase) + 不同键名集不匹配。结果：`get_active_genre_audits()` 在任何真实运行中返回 `[]`。

**修复:**

```python
# 1. 矩阵键名改为 camelCase，对齐真实 fixture
GENRE_ACTIVATION_MATRIX: dict[str, str] = {
    "sensitivity": "shenbi-review-sensitivity",
    "worldRules": "shenbi-review-world-rules",
    "motivation": "shenbi-review-motivation",
    "dialogue": "shenbi-review-dialogue",
    "texture": "shenbi-review-texture",
    "era": "shenbi-review-era",
    "fanfic": "shenbi-review-fanfic",
    "readerPull": "shenbi-review-reader-pull",
    "highpoint": "shenbi-review-highpoint",
}

# 2. 读取正确的顶层键名，保留 snake_case fallback
def get_active_genre_audits(genre_config: Mapping[str, object]) -> list[str]:
    audit_dims = genre_config.get("auditDimensions")  # camelCase 优先
    if audit_dims is None:
        audit_dims = genre_config.get("audit_dimensions", {})  # 兼容
    if not isinstance(audit_dims, dict):
        return []

    # 3. 过滤核心圈键名（它们由 chapter_loop 固定步骤处理）
    CORE_CIRCLE_KEYS = {"antiAi", "character", "pacing", "continuity",
                        "foreshadowing", "memoCompliance", "pov"}

    return sorted(
        skill
        for dim_key, skill in GENRE_ACTIVATION_MATRIX.items()
        if dim_key not in CORE_CIRCLE_KEYS and audit_dims.get(dim_key, False)
    )
```

**验证:** 用 `tests/fixtures/genre-config-example.json` 直接测试，确认返回非空 skill 列表。

**验收:**
- [ ] `get_active_genre_audits(真实 fixture)` 返回非空列表
- [ ] 核心圈键名不被题材圈激活
- [ ] snake_case `audit_dimensions` 向后兼容
- [ ] 所有现有测试通过

---

### Step 2: A8 — 审计层接线 + BLOCKING 修订闭环

**文件:** `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/state.py`

**前置:** Step 1 完成

**问题:** `chapter_loop.py:653-661` — 核心圈审计完成后，`TODO(W3T4)` 注释掉 `run_audit_layer()` 调用。题材圈和边界圈审计从未运行。BLOCKING 发现不停止章节。

**修复:**

**2a. ChapterState 加 `audit_retry_count` (state.py):**

```python
@dataclass
class ChapterState:
    steps_done: list[str] = field(default_factory=list)
    status: str = "pending"
    resonance_score: int | None = None
    audit_results: dict[str, Any] = field(default_factory=dict)
    revision_count: int = 0
    audit_retry_count: int = 0  # NEW

# 同步更新 ChapterLoopStateData.to_dict() / from_dict() 序列化 audit_retry_count
```

**2b. 替换 TODO(W3T4) 为审计修订闭环 (chapter_loop.py:653-661):**

```python
if step.is_audit and step_idx == _LAST_AUDIT_IDX:
    import json
    from shenbi.pipeline.audit_layer import run_audit_layer

    gc_path = project_dir / "genre-config.json"
    gc = json.loads(gc_path.read_text(encoding="utf-8")) if gc_path.exists() else {}

    cs = _get_chapter_state(state, chapter)
    while True:
        audit_result = run_audit_layer(project_dir, chapter, gc)
        cs.audit_results["blocking_found"] = audit_result.blocking_found
        cs.audit_results["issues"] = audit_result.issues
        cs.audit_results["audit_reports"] = audit_result.audit_reports

        if not audit_result.blocking_found:
            break

        cs.audit_retry_count += 1
        if cs.audit_retry_count > state.config.max_revision_retries:
            set_checkpoint(state, CheckpointType.ESCALATION, chapter=chapter,
                context=f"Audit BLOCKING persists after {cs.audit_retry_count} revision attempts")
            return True

        rev = dispatch_skill("shenbi-chapter-revision", project_dir,
            f"Revise chapter {chapter} to fix audit BLOCKING issues.")
        if not rev.success:
            return _handle_failure(state, step, chapter, "audit-revision")

        log.info("audit_blocking_revision", chapter=chapter,
                 retry=cs.audit_retry_count)
```

**验收:**
- [ ] 核心圈审计完成后 `run_audit_layer()` 被调用
- [ ] BLOCKING 发现触发修订闭环（最多 3 次）
- [ ] 3 次后仍 BLOCKING → ESCALATION checkpoint
- [ ] 通过后继续步骤 17 (review-resonance)
- [ ] `audit_retry_count` 在 `pipeline-state.json` 持久化

---

### Step 3: A7 — state-settling G4 验证修复

**文件:** `src/shenbi/pipeline/chapter_loop.py`

**问题:** state-settling 步骤的 `output_path=""`，`_resolve_g4_path()` 返回 `""`，G4 收到 `[]` → 直接 SKIP。state-settling 写入的 `staging/truth/*.md` 格式错误不被拦截。

**修复:**

新增 `_resolve_g4_files()` 函数，替换 `run_chapter_step()` 中的单文件 G4 路径解析：

```python
def _resolve_g4_files(
    project_dir: Path, step: ChapterStep, chapter: int
) -> list[str]:
    """Return list of file paths for G4 validation."""
    single = _resolve_g4_path(project_dir, step, chapter)
    if single:
        return [single]

    # State-settling: writes multiple truth files to staging/
    if step.uses_staging and "state-settling" in step.skill:
        staging_truth = project_dir / STAGING_DIR / "truth"
        if staging_truth.exists():
            return sorted(
                f"{STAGING_DIR}/truth/{p.name}"
                for p in staging_truth.glob("*.md")
            )

    return []
```

`run_chapter_step()` 第 625-626 行改为：

```python
# 修改前:
g4_file = _resolve_g4_path(project_dir, step, chapter)
g4 = run_gate_g4(step.skill, [g4_file] if g4_file else [], project_dir)

# 修改后:
g4_files = _resolve_g4_files(project_dir, step, chapter)
g4 = run_gate_g4(step.skill, g4_files, project_dir)
```

**验收:**
- [ ] `_resolve_g4_files(state_settling_step)` 返回 `staging/truth/` 下所有 `.md` 文件
- [ ] 非 state-settling 步骤行为不变
- [ ] staging/truth/ 不存在时不崩溃

---

### Step 4: A5 — 错误处理函数接线

**文件:** `src/shenbi/pipeline/chapter_loop.py`

**问题:** `error_handler.py` 中 `handle_scoring_failure` 和 `handle_state_settle_failure` 已实现但从未从 orchestrator 调用。`handle_audit_blocking` 在 Step 2 中已通过审计修订闭环间接使用。

**修复:**

**4a. state-settling 失败接线 (chapter_loop.py:614-622 之后):**

在 dispatch 失败检查处，对 state-settling 步骤使用专用处理：

```python
# 在 run_chapter_step() 中, dispatch_skill 之后:
if not result.success:
    # State-settling 失败 → 标记 settling_failed + 暂停
    if "state-settling" in step.skill:
        from shenbi.pipeline.error_handler import handle_state_settle_failure
        handle_state_settle_failure(state, chapter)
        return True  # checkpoint 已设置，暂停等人工

    log.error("chapter_dispatch_failed", ...)
    return _handle_failure(state, step, chapter, "dispatch")
```

**4b. scoring 失败接线 (chapter_loop.py: dispatch 结果检查处):**

在 review-resonance 的 dispatch 之后、通用成功检查之前：

```python
result = dispatch_skill(step.skill, project_dir, prompt)

# Scoring skills: exit code 2/3 需要特殊分流（在通用失败检查之前）
if "review-resonance" in step.skill:
    if not result.success or result.returncode in (2, 3):
        from shenbi.pipeline.error_handler import handle_scoring_failure
        if handle_scoring_failure(state, result.returncode):
            # exit 2: 重新 dispatch + G3; exit 3: 先 G4 再 dispatch
            return False  # 不推进 step_index，下次调用重试
        return _handle_failure(state, step, chapter, "scoring")

# 通用失败检查（state-settling 已在 4a 处理）
if not result.success:
    # ...
```

注：`result.returncode` 来自 `DispatchResult`，是 dispatcher 子进程的实际退出码。

**验收:**
- [ ] state-settling dispatch 失败 → `settling_failed` + ESCALATION checkpoint
- [ ] scoring exit code 2 → 重新 dispatch
- [ ] scoring exit code 3 → 先跑 G4 再重新 dispatch
- [ ] 其他 exit code → 走现有 `_handle_failure` 路径

---

### Step 5: A4 — escalation-review dispatch 接线

**文件:** `src/shenbi/pipeline/chapter_loop.py`, `src/shenbi/pipeline/genesis.py`, `src/shenbi/pipeline/closure.py`

**问题:** 重试耗尽后直接 `set_checkpoint(ESCALATION)`，没有先 dispatch `shenbi-escalation-review` 生成分析报告。

**修复:**

在 `_handle_failure` 返回 False（重试耗尽）后，先 dispatch escalation-review 再设 checkpoint：

```python
# chapter_loop.py _handle_failure() — 重试耗尽路径:
if handle_dispatch_failure(state, step.skill, count):
    # ... 现有重试逻辑 ...
    return False

# 新增: 重试耗尽 → 先 dispatch escalation-review
from shenbi.pipeline.revision_router import dispatch_escalation
# dispatch_escalation(project_dir, chapter, context="") → bool
dispatch_escalation(project_dir, chapter,
    context=f"Step {step.step_num} ({step.skill}) failed after {count} attempts")

log.error("chapter_step_escalation", ...)
set_checkpoint(state, CheckpointType.ESCALATION, ...)
return True
```

同样修改 `genesis.py` 和 `closure.py` 中对应的 `_handle_failure` 函数，使用相同的模式。

**验收:**
- [ ] 重试耗尽后 `shenbi-escalation-review` 被 dispatch
- [ ] `audits/escalation-N-report.md` 在 checkpoint 之前生成
- [ ] genesis 和 closure 的 escalation 路径同样接线

---

### Step 6: A2 — resonance 评分解析器

**文件:** `src/shenbi/pipeline/chapter_loop.py`

**问题:** `cs.resonance_score` 始终为 `None`，因为 `audits/chapter-N-resonance.md` 中的分数从未被提取。

**修复:**

新增解析函数，在 review-resonance dispatch 成功后提取分数：

```python
def _parse_resonance_score(report_path: Path) -> int | None:
    """Extract resonance score from a review-resonance audit report.

    Expected format in the report: ``**Resonance Score**: 87`` or
    YAML frontmatter ``resonance_score: 87``.
    """
    if not report_path.exists():
        return None
    text = report_path.read_text(encoding="utf-8")

    # Pattern 1: YAML frontmatter
    if text.startswith("---"):
        import yaml
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                score = fm.get("resonance_score")
                if isinstance(score, int):
                    return score
            except Exception:
                pass

    # Pattern 2: Markdown bold label
    import re
    m = re.search(r'\*\*Resonance\s*Score\*\*:\s*(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Pattern 3: Plain "Score: N"
    m = re.search(r'(?:Score|resonance_score)\s*:\s*(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None
```

在 `run_chapter_step()` 中 review-resonance 成功后的位置调用：

```python
if "review-resonance" in step.skill:
    cs = _get_chapter_state(state, chapter)
    report_path = project_dir / _substitute_chapter("audits/chapter-N-resonance.md", chapter)
    cs.resonance_score = _parse_resonance_score(report_path)
    log.info("resonance_score_parsed", chapter=chapter, score=cs.resonance_score)

    _route_revision_after_resonance(state, project_dir, chapter)  # 现有
```

**验收:**
- [ ] `cs.resonance_score` 在 review-resonance 后不再为 `None`
- [ ] `check_resonance()` 使用真实分数进行地板判断
- [ ] 报告缺失时不崩溃，保持 `None`

---

### Step 7: A1 — total_chapters 动态重算

**文件:** `src/shenbi/pipeline/triggers.py`

**问题:** volume-outlining (genesis step 6) 一次性写入 `total_chapters` 到 `novel.json`。卷边界扩展后从未重新计算。导致 chapter-loop 可能在错误的总章节数处终止。

**修复:**

卷边界扩展完成后，重新解析 `volume_map.md` 并更新 `novel.json`：

```python
def _count_total_chapters(project_dir: Path) -> int:
    """Parse volume_map.md and sum all volume chapter counts."""
    vmap = project_dir / "truth" / "volume_map.md"
    if not vmap.exists():
        return 0
    text = vmap.read_text(encoding="utf-8")

    total = 0
    # Match patterns like "章节数: 12" or "Chapters: 12"
    for m in re.finditer(r'(?:章节数|Chapters?)\s*:\s*(\d+)', text):
        total += int(m.group(1))
    return total if total > 0 else 0


def _update_total_chapters(state: PipelineState) -> None:
    """Recompute novel.json.total_chapters from volume_map.md after volume expansion."""
    project_dir = Path(state.project_dir)
    new_total = _count_total_chapters(project_dir)
    if new_total < 1:
        return

    novel_json = project_dir / "novel.json"
    if not novel_json.exists():
        return

    data = json.loads(novel_json.read_text(encoding="utf-8"))
    old_total = data.get("total_chapters", 0)
    if new_total != old_total:
        data["total_chapters"] = new_total
        novel_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("total_chapters_updated", old=old_total, new=new_total)
```

在 `run_triggered_skills()` 的卷边界扩展完成后调用 `_update_total_chapters(state)`。

**验收:**
- [ ] 卷边界扩展后 `novel.json.total_chapters` 被重算
- [ ] 重算值与 `volume_map.md` 中各卷章节数之和一致
- [ ] `volume_map.md` 不存在时不崩溃

---

### Step 8: A6 — MODIFY 决策行为修正

**文件:** `src/shenbi/pipeline/cli.py`

**问题:** `cmd_review` 对 `MODIFY` 执行与 `APPROVE` 完全相同的 staging commit。Feedback 被记录但从未用于重新 dispatch 技能。

**修复:**

在 `clear_checkpoint` 后，MODIFY 决策需要重置步骤游标，使管线在 resume 时重新执行该步骤：

```python
# cli.py cmd_review() — 在 clear_checkpoint 之后:
if decision == ReviewDecision.MODIFY:
    # 1. 记录 feedback 到 checkpoint history（现有）
    # 2. 重置步骤游标到产生该 checkpoint 的步骤
    #    这样 resume 时会重新 dispatch 该技能，带上 feedback
    cp = state.pending_checkpoint  # 保存引用（clear_checkpoint 会清掉）
    clear_checkpoint(state, decision)

    # 回退步骤游标
    if cp.type == CheckpointType.CHAPTER_MEMO:
        state.chapter_loop.step_index = 1  # 章节规划是 CHAPTER_STEPS[1]
    elif cp.type == CheckpointType.STATE_SETTLE:
        state.chapter_loop.step_index = 6  # state-settling 是 CHAPTER_STEPS[6]
    elif cp.type == CheckpointType.GENESIS_COMPLETE:
        state.genesis.current_step = 0  # 回到 genesis 起点

    # 3. 将 feedback 存入 state（通过 ChapterLoopStateData 持久化）
    state.chapter_loop.modify_feedback = feedback

    # 4. 不清除 staging — 技能会用 feedback 重新写入

    save_state(state, project_dir)
    return 0
```

**8a. ChapterLoopStateData 加 `modify_feedback` (state.py):**

```python
@dataclass
class ChapterLoopStateData:
    current_chapter: int = 0
    current_step: str = ""
    step_index: int = 0
    chapter_states: dict[str, ChapterState] = field(default_factory=dict)
    per_chapter_review_enabled: bool = True
    retry_counts: dict[str, int] = field(default_factory=dict)
    modify_feedback: str | None = None  # NEW

# 同步更新 PipelineState.to_dict() / from_dict() 序列化 modify_feedback
```

**8b.** 修改 `run_chapter_step()` 和 `run_genesis_step()`，在构建 dispatch prompt 时注入 `modify_feedback`：

```python
prompt = f"Execute {step.skill} for chapter {chapter}. Project dir: {project_dir}"
# genesis 使用 state.genesis.modify_feedback（如有需要同理添加字段）
if state.chapter_loop.modify_feedback:
    prompt += f"\n\nHuman review feedback: {state.chapter_loop.modify_feedback}"
    state.chapter_loop.modify_feedback = None  # 一次性消费，消费后置 None
```

**验收:**
- [ ] MODIFY 后 resume，步骤游标回退到产生 checkpoint 的步骤
- [ ] Feedback 被注入到重新 dispatch 的 prompt 中
- [ ] APPROVE 行为不变
- [ ] REJECT 行为不变

---

### Step 9: 金丝雀验证

**目标:** 用真实种子跑通完整管线，逐级验证。

**种子文件:**
- `tests/fixtures/canary-3-chapter-seed.md` — 3 章短篇（L2 金丝雀，每次 PR 运行）
- `tests/fixtures/canary-10-chapter-seed.md` — 10 章中篇（L3 集成，每日运行）
- `outline-example.md` — 20 万字长篇（L4 全量回归，里程碑验证）

**验证流程:**

```
Step 9a: 3 章金丝雀
  ├── pipeline init canary-3-chapter-seed.md /tmp/canary-3 --auto
  ├── pipeline next /tmp/canary-3（运行到下一个 checkpoint）
  ├── 重复 pipeline next 直到管线完成或需要 review
  ├── 验证: 3 章全部生成, 无 ESCALATION, 无错误
  └── 失败 → 回到对应 Step 修复

Step 9b: 10 章金丝雀
  ├── pipeline init canary-10-chapter-seed.md /tmp/canary-10 --auto
  ├── pipeline next /tmp/canary-10（重复直到完成）
  ├── 验证: 10 章全部生成, resonance 分数可解析
  └── 失败 → 回到对应 Step 修复

Step 9c: 20 万字全量
  ├── pipeline init outline-example.md /tmp/canary-full --auto
  ├── pipeline next /tmp/canary-full（重复直到完成）
  ├── 验证: 全章节生成, closure 完成
  └── 失败 → 回到对应 Step 修复
```

**验收:**
- [ ] 3 章种子通过端到端
- [ ] 10 章种子通过端到端
- [ ] 20 万字种子通过端到端

---

## 4. 文件改动总览

```
修改文件:
  src/shenbi/pipeline/audit_layer.py        — Step 1 (~15行)
  src/shenbi/pipeline/state.py              — Step 2 (~5行)
  src/shenbi/pipeline/chapter_loop.py       — Step 2,3,4,5,6 (~100行)
  src/shenbi/pipeline/genesis.py            — Step 5 (~10行)
  src/shenbi/pipeline/closure.py            — Step 5 (~10行)
  src/shenbi/pipeline/triggers.py           — Step 7 (~30行)
  src/shenbi/pipeline/cli.py                — Step 8 (~20行)

新增文件:
  tests/fixtures/canary-3-chapter-seed.md   — Step 9
  tests/fixtures/canary-10-chapter-seed.md  — Step 9

新增测试:
  tests/unit/pipeline/test_audit_layer.py   — Step 1 补充
  tests/unit/pipeline/test_chapter_loop.py  — Step 2,3,4,6 补充
  tests/unit/pipeline/test_cli.py           — Step 8 补充
  tests/unit/pipeline/test_triggers.py      — Step 7 补充
```

## 5. 不变式

以下现有行为在整个 Phase 1 中不被修改：

- **三层架构** (Driver/Orchestrator/Skills) — 不动
- **PipelineState cursor 模型** — 不动（Phase 2 中替换为事件溯源）
- **G0-G7 gate 体系** — 不动
- **Dispatcher 的 dispatch_with_write_audit** — 不动
- **67 个 skill 的 SKILL.md** — 不动
- **现有 510+ 单元测试** — 全部保持通过

## 6. 验收标准

Phase 1 完成的定义：

- [ ] 8 个 Category A 缺陷全部修复，每个有单元测试覆盖
- [ ] 3 章金丝雀种子端到端通过
- [ ] 10 章金丝雀种子端到端通过
- [ ] 20 万字 `outline-example.md` 端到端通过
- [ ] 全量 510+ 单元测试无回归
- [ ] pre-commit hooks 全部绿色 (ruff, mypy, basedpyright strict, contract checks)
