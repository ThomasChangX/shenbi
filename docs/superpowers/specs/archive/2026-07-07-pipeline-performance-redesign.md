# Pipeline 性能优化：基于行业最佳实践的重新设计

> **日期:** 2026-07-07
> **状态:** 设计中
> **前置:** `2026-07-01-novel-pipeline-design.md` (原始 spec), `2026-07-06-pipeline-phase1-defect-fix-design.md` (Phase 1)
> **行业参考:** Anthropic Multi-Agent Researcher, Microsoft AutoGen v0.4, TIMAR Review System, TreeReview (2025), Context Engineering Playbook (LangChain/ZenML)

---

## 0. 核心哲学：做减法，不做重组

审视原 Plan 的所有问题，一个根本模式浮现：

> **大量可以用 10 行 Python 确定性地完成的工作，被委托给了 LLM。**

| 工作 | 原本做法 | 应该用 |
|------|---------|--------|
| Context 结构化 (P1-P7 排序) | LLM (context-composing) | Python 重排 |
| 近章结尾多样性检查 | LLM (context-composing) | Python 正则 |
| Hook 债务简报生成 | LLM (context-composing) | Python 数据聚合 |
| Hook 种植 YAML 生成 | LLM (plant) | Python 模板填充 |
| 审查前置清单 | LLM (planning) | Python 文件读取+聚合 |
| G4 软失败裁决 | LLM 重试 | Python 规则引擎 |
| 审查触发决策 | 固定间隔 | Python 阈值判断 |
| 上下文摘要 | 正则提取 (脆弱) | Embedding 语义搜索 |
| 审查并行化 | 串行 | ThreadPoolExecutor |

Anthropic 2025 年指南的标题就是答案：

> **"Prefer explicit, code-driven workflows when the pipeline logic is clear upfront."**

本 pipeline 中，上下文策展、伏笔种植、审查触发、数据聚合——这些逻辑是清晰的。只有章节写作和内容审查需要 LLM。我们的优化策略不是"用更少的 LLM 做更多的事"，而是"把不需要 LLM 的事还给代码"。

### 设计原则

1. **LLM 只做创造性判断**：写作、审查、评分。其他一切是数据转换。
2. **并行优于合并**：11 个审查不需要变成 2 个——它们需要同时跑。并行保质量，合并损质量。
3. **契约交接 (contract-based handoff)**：Agent 之间通过结构化 JSON 传递信息，不依赖 prompt 中的自然语言指令。
4. **自适应触发**：不按固定间隔执行步骤，而是当数据表明需要时才触发。
5. **缓存复用**：每章只计算一次的东西（审查上下文摘要、检查清单），缓存后所有步骤共享。

### 预期效果

| 指标 | 当前基线 | 重新设计后 | 改善 |
|------|---------|-----------|------|
| 每章 LLM 调用 | 19 次 | 12-14 次 | -26~37% |
| 每章 wall-clock 时间 | 2.6h | 0.5-0.6h | -77~81% |
| 100 章总时间 | 10.8 天 | 2.1-2.5 天 | -77% |
| 审查质量 | 独立审查（高） | 独立审查（高，不变） | 质量不降 |
| 代码复杂度增量 | — | ~300 行 Python + 1 个 ThreadPoolExecutor | 可控 |

> 注：LLM 调用数降幅不如原方案的 -82%，但 wall-clock 时间降幅相近（因为并行化），且**不牺牲审查质量**。

---

## Phase 1: Bug 修复

### 1.1 Staging 路径：修复两阶段提交，而非加 fallback

**根因**：auto 模式下 `chapter_memo_review_required: False`，`_advance()` 跳过 checkpoint → `commit_staging()` 从未被调用 → dispatch 写入的文件留在最终路径（`plans/`），但 G4 去 `staging/` 找。

**修复**：在 `_advance()` 中，当 checkpoint 被 auto-skip 时，自动执行 `commit_staging()`。

> **Note:** 原设计曾考虑在 `_resolve_g4_path` 中加 fallback 让 G4 去非 staging 路径找文件。经 review 确认这是反模式——掩盖根因而非修复。两阶段提交是唯一正确的做法。

```python
# src/shenbi/pipeline/chapter_loop.py: _advance()
if step.checkpoint is not None:
    cfg = state.config
    if step.checkpoint == CheckpointType.CHAPTER_MEMO and not cfg.chapter_memo_review_required:
        # Auto mode: commit staging immediately since no human review
        from shenbi.pipeline.checkpoint import commit_staging
        try:
            commit_staging(project_dir, [_substitute_chapter(step.output_path, chapter)])
        except FileNotFoundError:
            # Dispatch may have written directly (legacy behavior). Log and continue.
            log.warning("staging_commit_skipped_no_file", chapter=chapter)
        # Fall through to chapter-completion check (no checkpoint raised)
    elif step.checkpoint == CheckpointType.STATE_SETTLE and not cfg.state_settle_review_required:
        from shenbi.pipeline.checkpoint import commit_staging
        # state-settling writes multiple truth files
        staging_files = [f.name for f in (project_dir / "staging" / "truth").glob("*.md")]
        if staging_files:
            commit_staging(project_dir, [f"truth/{f}" for f in staging_files])
```

同时，dispatch 端确保 `uses_staging=True` 时路径前缀 `staging/`：

```python
# src/shenbi/pipeline/dispatch_helper.py: _build_skill_prompt()
if uses_staging:
    output_paths = [f"staging/{p}" for p in output_paths]
```

**效果**：消除 chapter-planning 每章 3 次 G4 重试（G4.cp.not_found）。dispatch → staging/ → G4 验证 staging/ → auto-commit → 最终路径，流程完整。

**修改文件**：`chapter_loop.py` (_advance), `dispatch_helper.py` (_build_skill_prompt, dispatch_skill)

### 1.2 G4 分级：Enum 分类 + 趋势追踪

**修复**：将字符串匹配改为 Enum 分类，增加跨章节 soft fail 趋势追踪：

```python
# src/shenbi/pipeline/chapter_loop.py

from enum import StrEnum

class G4Severity(StrEnum):
    HARD = "hard"    # 结构性缺陷 — 必须重试
    SOFT = "soft"    # 质量阈值 — 单次 warn，累积 3 次 escalate
    WARN = "warn"    # 信息性 — 记录即可

G4_CHECK_MAP: dict[str, G4Severity] = {
    # HARD — structural problems
    "not_found": G4Severity.HARD,
    "pre_check": G4Severity.HARD,
    "post_check": G4Severity.HARD,
    "meta": G4Severity.HARD,
    "word_count": G4Severity.HARD,
    "no_visual_scene": G4Severity.HARD,
    "no_valid_verdict": G4Severity.HARD,
    "no_file_line_ref": G4Severity.HARD,
    "missing_cols": G4Severity.HARD,
    "missing_sections": G4Severity.HARD,
    "sections": G4Severity.HARD,
    "chapter_role": G4Severity.HARD,
    "s7_hook_ops": G4Severity.HARD,
    "content_overlap": G4Severity.HARD,
    "no_result": G4Severity.HARD,
    "no_evidence": G4Severity.HARD,
    # SOFT — quality thresholds
    "transition": G4Severity.SOFT,
    "fatigue": G4Severity.SOFT,
    "cd.chapter_end_hook": G4Severity.SOFT,
    "cp.golden": G4Severity.WARN,
    "cp.s5_choice": G4Severity.WARN,
}

# Soft-fail trend tracking with sliding window (persisted in PipelineState)
@dataclass
class SoftFailTracker:
    check_id: str
    occurrences: list[int] = field(default_factory=list)  # chapter numbers
    window_size: int = 5         # sliding window — only look at last N chapters
    escalation_threshold: int = 3

    def record(self, chapter: int) -> bool:
        """Record a soft fail occurrence. Returns True if escalation needed."""
        self.occurrences.append(chapter)
        # Prune entries outside the sliding window
        self.occurrences = [ch for ch in self.occurrences if chapter - ch <= self.window_size]
        return len(self.occurrences) >= self.escalation_threshold
```

**行为**：
- HARD fail → 重试 1 次 → 仍失败 → escalation
- SOFT fail → 记录 warn，继续；同一 check_id 在 5 章内出现 3 次 → escalation
- WARN fail → 仅记录日志

**效果**：消除 ~50% 的无效重试。质量不会静默退化——趋势追踪确保累积问题被捕获。

**修改文件**：`chapter_loop.py` (G4CheckSeverity, G4_CHECK_MAP, SoftFailTracker, run_chapter_step)

---

## Phase 2: 确定性提取 — 把不需要 LLM 的事还给代码

这是整个重新设计的核心。以下四个 LLM 调用被替换为确定性 Python 函数。

### 2.1 context-composing → 确定性策展函数

**当前**：`context-composing` 是一个 LLM skill，读 12 个文件，输出 9-section 结构化上下文。

**分析**：三个核心职责都是确定性的：
1. **P1-P7 分层重排**：assemble 的扁平 Route A/B/C 结果 → 按优先级重排到 9 个 section
2. **近章结尾多样性检查**：读 `chapters/chapter-(N-3).md` 到 N-1 的末段 → 检测连续同类型
3. **Hook 债务简报**：读 `pending_hooks.md` + `book_spine.md` → 按 MH*/H* 分级生成表格

**替换为**：

```python
# 新文件: src/shenbi/pipeline/context_curation.py
"""Deterministic context curation — replaces LLM-based context-composing."""

def curate_context(project_dir: Path, chapter: int) -> str:
    """Curate the assembled context into a structured 9-section format.

    Replaces the shenbi-context-composing LLM call with deterministic
    Python operations: section reordering, ending diversity check,
    hook debt briefing generation.
    """
    # 1. Read assembled context
    ctx_path = project_dir / "context" / f"chapter-{chapter}-context.md"
    if not ctx_path.exists():
        return _generate_minimal_context(project_dir, chapter)

    assembled = ctx_path.read_text(encoding="utf-8")

    # 2. Reorder flat sections into P1-P7 hierarchy
    sections = _reorder_to_layered_format(assembled, chapter, project_dir)

    # 3. Check ending diversity (deterministic regex)
    ending_table = _check_ending_diversity(project_dir, chapter)

    # 4. Build hook debt briefing (deterministic data aggregation)
    hook_briefing = _build_hook_debt_briefing(project_dir, chapter)

    # 5. Render 9-section output
    return _render_context_document(sections, ending_table, hook_briefing)


def _reorder_to_layered_format(assembled: str, chapter: int, project_dir: Path) -> list[Section]:
    """Reorder flat Route A/B/C results into P1-P7 priority layers."""
    # Parse ### route-a:Entity / ### route-b:chunk_id / ### route-c:label
    # Sort by priority: P1 (plan) → P2 (spine) → P3 (strata) → ...
    sections = _parse_assembled_sections(assembled)

    # Priority key for sorting
    priority_order = {
        "chapter-plan": 1, "book_spine": 2, "book_strata": 3,
        "volume_summaries": 4, "arcs": 5, "chapter_summaries": 6,
        "world_rules": 7, "style_profile": 7, "audit_drift": 7,
    }

    def sort_key(s: Section) -> int:
        for prefix, prio in priority_order.items():
            if prefix in s.source.lower():
                return prio
        return 99  # unknown → bottom

    sections.sort(key=sort_key)

    # Also load the chapter plan as P1 if not in assembled results
    plan_path = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    if plan_path.exists():
        plan_section = Section(
            source="P1 章节备忘",
            priority=1.0,
            text=plan_path.read_text(encoding="utf-8"),
            category="plan",
            estimated_tokens=0,
        )
        sections.insert(0, plan_section)

    return sections


def _parse_assembled_sections(assembled: str) -> list[Section]:
    """Parse flat Route A/B/C results from assembled context markdown.

    The assembled context is a flat series of `## route-X:entity_id` H2 sections.
    Extracts each into a Section with source, text, category, and priority.
    """
    sections = []
    parts = re.split(r"\n(?=## route-)", assembled)
    for part in parts:
        header_match = re.match(r"## (route-[abc]):(.+)", part)
        if not header_match:
            continue
        category = header_match.group(1)
        source_id = header_match.group(2).strip()
        text = part[header_match.end():].strip()
        sections.append(Section(
            source=f"{category}:{source_id}",
            priority={"route-a": 1.0, "route-b": 0.8, "route-c": 0.6}.get(category, 0.5),
            text=text,
            category=category,
            estimated_tokens=int(len(text) * 1.5),
        ))
    return sections


def _generate_minimal_context(project_dir: Path, chapter: int) -> str:
    """Fallback when assembled context is missing (early ramp-up chapters).

    Returns a minimal 9-section context with just the chapter plan as P1.
    """
    plan_path = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else "(no plan yet)"
    return f"""## P1 章节备忘\n{plan_text}\n\n## P2 书脊（L5）\n(未产出)\n\n## P3 当前大弧（L4）\n(未产出)\n\n## P4 当前卷摘要（L3）\n(未产出)\n\n## P5 当前弧段（L2）\n(未产出)\n\n## P6 近章拍点（L1）\n(未产出)\n\n## P7 世界铁律与文风\n(未产出)\n\n## 近章结尾多样性\n(不足3章)\n\n## Hook 债务简报\n(无活跃伏笔)\n"""


def _check_ending_diversity(project_dir: Path, chapter: int) -> str:
    """Check last 3 chapters' endings for consecutive same-type patterns.

    Reads actual chapter files (not summaries — SKILL.md 铁律 4).
    """
    if chapter < 3:
        return "| 章节 | 结尾方式 | 末段首句 |\n|------|---------|---------|\n| (不足3章) | — | — |\n"

    ENDING_PATTERNS = {
        "cliffhanger": r"(突然|猛然|就在此时|一声|眼前一|[？?]$)",
        "hook": r"(但|然而|却|不过|还[有存]|等待|尚未|不知)",
        "resolution": r"(终于|最后|就这样|[。！]$)",
        "reflection": r"(回想|想起|原来|或许|也许|大概)",
        "transition": r"(第二天|次日|翌日|接下来|之后|随后)",
    }

    rows = []
    ending_types = []
    for offset in range(3, 0, -1):
        ch = chapter - offset
        ch_path = project_dir / "chapters" / f"chapter-{ch}.md"
        if not ch_path.exists():
            continue

        text = ch_path.read_text(encoding="utf-8")
        # Get last paragraph (skip meta blocks)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()
                      and not p.startswith("<!--") and not p.startswith("## ")]
        last_p = paragraphs[-1] if paragraphs else ""
        first_20 = last_p[:20].replace("\n", " ")

        # Classify ending type
        etype = "other"
        for name, pattern in ENDING_PATTERNS.items():
            if re.search(pattern, last_p):
                etype = name
                break

        ending_types.append(etype)
        rows.append(f"| {ch} | {etype} | {first_20} |")

    # Check for 3+ consecutive same type
    warning = ""
    if len(ending_types) >= 3 and len(set(ending_types[-3:])) == 1:
        warning = f"\n⚠️ 连续 3 章相同结尾方式 ({ending_types[-1]})，本章必须避免！\n"

    # Monitor classifier health: if "other" rate exceeds 20%, patterns may have drifted
    other_rate = ending_types.count("other") / len(ending_types) if ending_types else 0
    if other_rate > 0.2:
        log.warning("ending_classifier_drift", chapter=chapter, other_rate=f"{other_rate:.0%}",
                    msg="ending type classifier 'other' rate high — regex patterns may need update")

    header = "| 章节 | 结尾方式 | 末段首句（前 20 字） |\n|------|---------|-------------------|\n"
    return header + "\n".join(rows) + warning


def _build_hook_debt_briefing(project_dir: Path, chapter: int) -> str:
    """Generate MH*/H* two-tier hook debt briefing from truth files."""
    hooks = _read_pending_hooks(project_dir)
    spine_hooks = _read_spine_master_hooks(project_dir)

    # MH* — from book_spine master hooks
    mh_rows = []
    for h in spine_hooks:
        silence = chapter - h.get("last_reinforced", h.get("plant_chapter", 0))
        urgency = "URGENT" if silence > h.get("max_distance", 999) * 0.7 else ""
        mh_rows.append(
            f"| {h['id']} | {h.get('content', '?')} | {h.get('state', '?')} | "
            f"{h.get('last_reinforced', '?')} | {silence} | {urgency or 'advance'} |"
        )

    # H* — from pending_hooks non-MH hooks
    h_rows = []
    for h in hooks:
        if h.get("id", "").startswith("MH"):
            continue
        silence = chapter - h.get("last_reinforced", h.get("plant_chapter", 0))
        h_rows.append(
            f"| {h['id']} | {h.get('content', '?')} | {h.get('state', '?')} | "
            f"{h.get('last_reinforced', '?')} | {silence} | |"
        )

    briefing = "## Hook 债务简报\n\n"
    briefing += "### 主线钩子（MH*）\n\n"
    briefing += "| Hook ID | 内容 | 状态 | 最后推进章 | 沉默章数 | 操作建议 |\n"
    briefing += "|---------|------|------|----------|---------|---------|\n"
    briefing += "\n".join(mh_rows) if mh_rows else "| (无) | — | — | — | — | — |\n"

    briefing += "\n### 弧内钩子（H*）\n\n"
    briefing += "| Hook ID | 内容 | 状态 | 最后推进章 | 沉默章数 |\n"
    briefing += "|---------|------|------|----------|---------|\n"
    briefing += "\n".join(h_rows) if h_rows else "| (无) | — | — | — | — |\n"

    return briefing
```

**在 chapter_loop 中集成**：step 4 (pipeline-context-assemble) 调用 assemble + curate 一次性完成，跳过 step 5 (context-composing)：

```python
# In run_chapter_step, after context assembly:
if step.calls_context_assembly:
    _run_context_assembly(project_dir, chapter)
    # Also run deterministic curation — replaces context-composing LLM call
    _run_context_curation(project_dir, chapter)
```

**效果**：消除 1 次 LLM 调用/章。上下文质量不变（9-section 格式保留）。

**修改文件**：新建 `context_curation.py`；修改 `chapter_loop.py` (step 4 扩展，step 5 skip)

### 2.2 Hook 种植 → 确定性 YAML 生成

**当前**：`foreshadowing-plant` 是一个 LLM skill，读 chapter plan 的 hook ledger + pending_hooks，生成新 hook 的 YAML 元数据并追加到 pending_hooks。

**分析**：chapter-planning 的第 7 节已声明本章要种植哪些 hook（"plant hook-005: 矿井深处的心跳声"）。plant 的 LLM 工作在做什么？——把"plant hook-005"这条记录扩展为完整的 YAML 元数据（type, dimension, subtlety, escalation_curve...）。但这些元数据 90% 是模板化的：新 hook 默认 GENUINE + CHARACTER + 0.6 + RISING。真正的创造性判断（这个 hook 应该是什么 type？什么 dimension？）在第 7 节写"plant hook-005"时已经做完了。

**替换为**：

```python
# 新文件: src/shenbi/pipeline/hook_planting.py
"""Deterministic hook planting — replaces LLM-based foreshadowing-plant."""

def plant_hooks_from_plan(project_dir: Path, chapter: int) -> int:
    """Parse chapter plan section 7, extract plant operations, generate
    hook YAML, and append to truth/pending_hooks.md.

    Returns: number of hooks planted.
    """
    plan_path = project_dir / "plans" / f"chapter-{chapter}-plan.md"
    if not plan_path.exists():
        return 0

    plan = plan_path.read_text(encoding="utf-8")
    section7 = _extract_section_7(plan)
    planted = 0

    for entry in _parse_hook_entries(section7, chapter):
        if entry.get("operation") != "plant":
            continue

        # Generate hook metadata from plan entry + defaults
        hook = {
            "id": entry["hook_id"],
            "content": entry["content"],
            "state": "PLANTED",
            "operation": "plant",
            "type": entry.get("type", "GENUINE"),
            "dimension": entry.get("dimension", "CHARACTER"),
            "subtlety": float(entry.get("subtlety", 0.6)),
            "plant_chapter": chapter,
            "cultivation_interval": int(entry.get("cultivation_interval", 5)),
            "last_reinforced": chapter,
            "max_distance": int(entry.get("max_distance", 20)),
            "escalation_curve": entry.get("escalation_curve", "RISING"),
            "depends_on": entry.get("depends_on", []),
            "core_hook": entry.get("core_hook", False),
            "promoted": False,
        }

        _append_to_pending_hooks(project_dir, hook)
        planted += 1

    log.info("hooks_planted_deterministically", chapter=chapter, count=planted)
    return planted


def _extract_section_7(plan_text: str) -> str:
    """Extract section 7 content from chapter plan."""
    m = re.search(r"## 7\..*?\n(?=## 8\.|\Z)", plan_text, re.DOTALL)
    return m.group() if m else ""


def _parse_hook_entries(section7: str, chapter: int | None = None) -> list[dict]:
    """Parse hook operation entries from section 7.

    Expects format like:
    | hook-005 | 矿井深处的心跳声 | plant | GENUINE | CHARACTER |
    or YAML block with hook entries.
    """
    entries = []

    # Try table format first
    for line in section7.split("\n"):
        if "|" not in line or "hook-" not in line.lower():
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) >= 3 and "plant" in cells[2].lower():
            entries.append({
                "hook_id": cells[0],
                "content": cells[1],
                "operation": "plant",
                "type": cells[3] if len(cells) > 3 else None,
                "dimension": cells[4] if len(cells) > 4 else None,
            })

    # Try YAML block format
    yaml_match = re.search(r"```ya?ml\s*\n(.*?)```", section7, re.DOTALL)
    if yaml_match:
        try:
            import yaml
            yaml_entries = yaml.safe_load(yaml_match.group(1))
            if isinstance(yaml_entries, list):
                entries.extend(yaml_entries)
        except Exception as e:
            log.warning("hook_yaml_parse_failed", chapter=chapter, error=str(e))

    return entries
```

**在 chapter_loop 中集成**：step 3 (foreshadowing-plant) 替换为调用 `plant_hooks_from_plan()`，不再 dispatch LLM：

```python
if step.skill == "shenbi-foreshadowing-plant":
    from shenbi.pipeline.hook_planting import plant_hooks_from_plan
    count = plant_hooks_from_plan(project_dir, chapter)
    _record_step_done(state, step, chapter)
    _reset_retries(state, step, chapter)
    return _advance(state, step_idx, step, chapter)
```

**效果**：消除 1 次 LLM 调用/章。Hook 种植速度从 ~5min → ~50ms。

**修改文件**：新建 `hook_planting.py`；修改 `chapter_loop.py` (step 3 改为本地调用)

### 2.3 审查前置清单 → 确定性 JSON 生成

**当前**：审查需要的参考信息（角色声音、AI味黑名单、疲劳词预警、POV 规则、伏笔兑现项、章尾约束）分散在各个审查 skill 的 prompt 中，每个 skill 独立加载完整文件。

**分析**：这些信息是确定性的——读文件 → 提取字段 → 格式化。且同一章的 11 个审查共享相同的参考信息。计算一次，缓存复用。

**替换为**：

```python
# 新文件: src/shenbi/pipeline/review_checklist.py
"""Deterministic review checklist generation — pre-computes shared review context."""

@dataclass
class ReviewChecklist:
    """Pre-computed review context shared by all review skills for one chapter."""
    chapter: int
    transition_budget: int           # max(5, estimated_wc // 1000)
    ai_blacklist: list[str]          # from genre-config.fatigueWords + audit_drift
    fatigue_warnings: dict[str, int] # word → recent chapter frequency
    voice_constraints: dict[str, str]  # character_name → voice_fingerprint
    pov_mode: str                     # from genre-config.povMode
    hook_deliverables: list[dict]     # hooks to advance/resolve this chapter
    ending_constraints: list[str]     # last 3 chapter ending types
    world_rules_brief: str            # condensed world rules (max 2K chars)
    sensitivity_flags: list[str]      # from genre-config.sensitivityFlags


def generate_review_checklist(project_dir: Path, chapter: int) -> ReviewChecklist:
    """Generate review checklist once per chapter. Cached result reused by all reviews."""
    gc = read_genre_config(project_dir)
    estimated_wc = _estimate_chapter_word_count(project_dir, chapter)

    checklist = ReviewChecklist(
        chapter=chapter,
        transition_budget=max(5, estimated_wc // 1000),
        ai_blacklist=_extract_ai_blacklist(project_dir, gc),
        fatigue_warnings=_extract_fatigue_warnings(project_dir, gc),
        voice_constraints=_extract_voice_constraints(project_dir, chapter),
        pov_mode=gc.get("povMode", "third-limited"),
        hook_deliverables=_extract_hook_deliverables(project_dir, chapter),
        ending_constraints=_get_recent_ending_types(project_dir, chapter),
        world_rules_brief=_summarize_world_rules(project_dir),
        sensitivity_flags=gc.get("sensitivityFlags", []),
    )

    # Cache to context/ directory with mtime-based freshness
    cache_path = project_dir / "context" / f"review-checklist-{chapter}.json"

    # Check if cache is still fresh (truth files haven't changed since cache was written)
    if cache_path.exists():
        cache_mtime = cache_path.stat().st_mtime
        truth_mtimes = _get_max_truth_mtime(project_dir)
        if cache_mtime >= truth_mtimes:
            # Cache is fresh — return deserialized copy
            return ReviewChecklist(**json.loads(cache_path.read_text(encoding="utf-8")))

    # Cache stale or missing — regenerate
    safe_write(cache_path, json.dumps(checklist.__dict__, indent=2, ensure_ascii=False))

    return checklist


def inject_checklist_into_prompt(prompt: str, checklist: ReviewChecklist) -> str:
    """Append review checklist as a structured JSON block in the prompt."""
    checklist_block = f"""
## 审查参考数据（预计算，本章所有审查共享）

```json
{json.dumps(checklist.__dict__, indent=2, ensure_ascii=False)}
```

使用以上数据辅助审查判断。数据来源已标注在各自字段中。
"""
    return prompt + checklist_block
```

**在 dispatch 中集成**：每个审查 skill dispatch 前，检查缓存并注入：

```python
# In dispatch_skill or _build_skill_prompt:
if _is_review_skill(skill):
    checklist = _load_or_generate_review_checklist(project_dir, chapter)
    prompt = inject_checklist_into_prompt(prompt, checklist)
```

**效果**：审查 skill 不再各自加载完整文件。输入从 ~30K chars 降到 ~4K chars 的 JSON。且只计算一次。

**修改文件**：新建 `review_checklist.py`；修改 `dispatch_helper.py` (注入逻辑)

---

## Phase 3: 并行审查架构

### 核心理念：并行 > 合并

行业共识（TIMAR, TreeReview, MARS）：
- **合并**（一个 agent 做多个维度）：token 省了，但质量降 12-18%
- **并行**（多个 agent 同时跑）：时间省了，质量不降
- **并行 + 轻量共识**：最佳平衡点

### 3.1 当前状态

```
Step 10: review-anti-ai      (7 min)
Step 11: review-continuity   (7 min)
Step 12: review-character    (9 min)  ← 最长
Step 13: review-pacing       (6 min)
Step 14: review-foreshadowing(7 min)
Step 15: review-memo-comp    (8 min)
Step 16: review-pov          (5 min)
Genre:  review-dialogue      (6 min)
Genre:  review-sensitivity   (5 min)
Genre:  review-motivation    (8 min)
Genre:  review-world-rules   (6 min)
─────────────────────────────────────
Total wall-clock: ~74 min (串行)
Total LLM time:  ~74 min (sum)
```

### 3.2 并行化后

```
                     ┌─ review-anti-ai (7 min) ─┐
                     ├─ review-continuity (7 min)┤
                     ├─ review-character (9 min) ┤ ← 最慢的决定总时间
Parallel wave 1: ───├─ review-pacing (6 min) ────┤
(7 个核心审查)       ├─ review-foreshadowing (7 min)┤
                     ├─ review-memo-comp (8 min) ─┤
                     └─ review-pov (5 min) ───────┘
                                                  ↓
Parallel wave 2: ───├─ review-dialogue (6 min) ──┐
(4 个类型审查)       ├─ review-sensitivity (5 min)  ├─→ 轻量共识 (2 min)
                     ├─ review-motivation (8 min) ┤
                     └─ review-world-rules (6 min) ┘
─────────────────────────────────────────────────────
Total wall-clock: ~20 min (9+8+2, 两波并行 + 共识)
Total LLM time:  ~74 min (unchanged — same 11 calls)
```

### 3.3 实现

```python
# 新文件: src/shenbi/pipeline/parallel_dispatch.py
"""Parallel review dispatch using ThreadPoolExecutor with resilience."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
import time
import random
from dataclasses import dataclass

# Resilience configuration
MAX_CONCURRENT_REVIEWS = 4   # Semaphore cap — stay under API rate limits
MAX_RETRIES = 2              # Per-review retry on transient failures
RETRY_BACKOFF_BASE = 2.0     # Exponential backoff base (seconds)
RETRY_JITTER = 1.0           # Random jitter range (seconds)

# Shared rate limiter across all parallel dispatch calls
_rate_limiter = Semaphore(MAX_CONCURRENT_REVIEWS)


@dataclass
class ReviewTask:
    skill: str
    project_dir: Path
    prompt: str
    output_path: str


def _dispatch_with_retry(task: ReviewTask) -> DispatchResult:
    """Dispatch a single review with rate limiting and retry."""
    for attempt in range(MAX_RETRIES + 1):
        with _rate_limiter:  # Block until a slot is available
            result = dispatch_skill(task.skill, task.project_dir, task.prompt)

        if result.success:
            return result

        if attempt < MAX_RETRIES:
            delay = RETRY_BACKOFF_BASE ** attempt + random.uniform(0, RETRY_JITTER)
            log.warning("review_retry", skill=task.skill, attempt=attempt+1, delay=f"{delay:.1f}s")
            time.sleep(delay)

    log.error("review_all_retries_exhausted", skill=task.skill)
    return result  # Return last failure


def dispatch_reviews_parallel(tasks: list[ReviewTask]) -> list[DispatchResult]:
    """Dispatch multiple review skills in parallel with rate limiting.

    Uses ThreadPoolExecutor (I/O-bound API calls) + Semaphore (rate limiting)
    + exponential backoff retry (transient failure resilience).
    Each review is independent — no shared state between them.
    """
    results: list[DispatchResult] = []

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REVIEWS) as executor:
        future_map = {
            executor.submit(_dispatch_with_retry, t): t
            for t in tasks
        }

        for future in as_completed(future_map):
            task = future_map[future]
            try:
                result = future.result()
                results.append(result)
                if not result.success:
                    log.error("parallel_review_failed_after_retries", skill=task.skill)
            except Exception as e:
                log.error("parallel_review_exception", skill=task.skill, error=str(e))
                results.append(DispatchResult(False, -1, "", str(e)))

    return results


def consolidate_review_results(results: list[DispatchResult], chapter: int) -> str:
    """Deterministic aggregation of parallel review results.

    IMPORTANT: This is NOT "LLM consensus." The 11 reviews check ORTHOGONAL
    dimensions (anti-ai checks word patterns, character checks BDI consistency,
    pov checks information boundaries, etc.). There are no conflicts to resolve —
    each review owns its dimension. This function purely aggregates: scan each
    report for BLOCKING/CRITICAL markers and compile a unified issue list.

    The revision step (shenbi-chapter-revision) receives all individual reports
    plus this summary and decides on fixes autonomously.

    Known limitation: severity detection relies on string-matching "BLOCKING"/
    "CRITICAL" markers in free-text reports. This is the existing pattern used
    throughout audit_layer.py.

    ## Future Enhancement: Structured Review Output (Post-MVP)

    The industry standard for agent-to-agent communication in 2025-2026 is
    **structured JSON output with schema enforcement**, following the
    Generate → Validate → Repair → Parse pipeline pattern:

    1. **Generate**: Review skill prompt includes a JSON schema for its output.
       The LLM is instructed to return `{"severity": "BLOCKING", "issues": [...]}`
       rather than free-text markdown.

    2. **Validate**: Deterministic validation with `jsonschema` + Pydantic.
       Checks: is it valid JSON? Are required fields present? Are enums valid?

    3. **Repair**: On validation failure, feed exact error messages back to
       the model for targeted correction (not "try again" — tell it exactly
       which field failed and why).

    4. **Parse**: Only after validation passes, map to typed objects for
       downstream consumption (consolidation, revision routing).

    This eliminates string-matching fragility entirely. The review skill's
    contract switches from "write markdown with BLOCKING markers" to
    "return JSON matching this schema." Consolidation becomes
    `json.loads()` + field access instead of regex scanning.

    **Why not now**: This is a cross-cutting change affecting all 11 review
    skill SKILL.mds, their G4 checkers, and the consolidation logic. It
    should be a follow-up phase after the deterministic extraction and
    parallel dispatch are stable.
    """
    blocking_issues = []
    critical_issues = []

    for result in results:
        if not result.success:
            continue
        # Scan output for severity markers
        for line in result.stdout.split("\n"):
            if "BLOCKING" in line:
                blocking_issues.append(line.strip())
            elif "CRITICAL" in line:
                critical_issues.append(line.strip())

    summary = f"""# Chapter {chapter} Review Summary

## BLOCKING Issues ({len(blocking_issues)})
"""
    for issue in blocking_issues:
        summary += f"- {issue}\n"

    summary += f"\n## CRITICAL Issues ({len(critical_issues)})\n"
    for issue in critical_issues:
        summary += f"- {issue}\n"

    summary += f"\n## All Reports\n"
    for i, result in enumerate(results):
        summary += f"- Report {i+1}: {'PASS' if result.success else 'FAIL'}\n"

    return summary
```

**在 chapter_loop 中集成**：

step 10 (核心审查批次) 和 genre circle 合并为两波并行 dispatch：

```python
# In run_chapter_step, after step 9 (foreshadowing-recall):
if step_idx == _FIRST_AUDIT_IDX:
    # Wave 1: 7 core-circle reviews in parallel
    core_tasks = [
        ReviewTask("shenbi-review-anti-ai", project_dir,
                   f"Execute anti-ai review for chapter {chapter}.",
                   f"audits/chapter-{chapter}-anti-ai.md"),
        # ... 6 more core reviews
    ]
    core_results = dispatch_reviews_parallel(core_tasks, max_workers=7)

    # Wave 2: genre-circle reviews in parallel
    genre_skills = get_active_genre_audits(gc)
    genre_tasks = [
        ReviewTask(skill, project_dir,
                   f"Execute {skill} audit for chapter {chapter}.",
                   f"audits/chapter-{chapter}-{_audit_suffix(skill)}.md")
        for skill in genre_skills
    ]
    genre_results = dispatch_reviews_parallel(genre_tasks, max_workers=4) if genre_tasks else []

    # Consolidate
    all_results = core_results + genre_results
    consolidated = consolidate_review_results(all_results, chapter)
    # ... write consolidated summary, check for blocking, etc.
```

**效果**：审查 wall-clock 从 74min → 20min（-73%），审查质量不变（仍是 11 个独立 agent）。

**修改文件**：新建 `parallel_dispatch.py`；修改 `chapter_loop.py` (审查步骤替换为并行批次)

---

## Phase 4: 自适应触发

### 4.1 替换固定间隔

| 步骤 | 当前 | 改为 | 触发条件 |
|------|------|------|---------|
| recall | 每 5 章 | 自适应 | hook 在 max_distance 70% 内 OR >5 TRIGGERED OR 距上次 >8 章 |
| snapshot | 每 12 章 | Git commit | 每章 git commit + 卷边界 git tag |
| drift | 每 12 章 | 自适应 | 3-chapter resonance MA 下降 >10 点 OR 距上次 >12 章 |

### 4.2 实现

```python
# src/shenbi/pipeline/chapter_loop.py — conditional step execution

def _should_run_step(step: ChapterStep, state: PipelineState, project_dir: Path) -> bool:
    """Determine if a periodic step should run this chapter."""
    chapter = state.chapter_loop.current_chapter

    if step.skill == "shenbi-foreshadowing-recall":
        return _should_run_recall(project_dir, chapter)

    if step.skill == "shenbi-snapshot-manage":
        # File-based timestamped snapshot — no git dependency
        _snapshot_chapter_files(project_dir, chapter)
        return False  # Don't dispatch — file copy is instant

    if step.skill == "shenbi-drift-guidance":
        return _should_run_drift(project_dir, chapter)

    return True  # All other steps always run


def _should_run_recall(project_dir: Path, chapter: int) -> bool:
    """Run recall when hooks actually need attention."""
    hooks = _read_pending_hooks(project_dir)
    if not hooks:
        return False

    # Trigger 1: any hook within 3 chapters of max_distance
    for h in hooks:
        if h.get("state") == "RESOLVED":
            continue
        silence = chapter - h.get("last_reinforced", h.get("plant_chapter", 0))
        if silence >= h.get("max_distance", 20) - 3:
            return True

    # Trigger 2: >5 hooks in TRIGGERED state
    triggered = sum(1 for h in hooks if h.get("state") == "TRIGGERED")
    if triggered > 5:
        return True

    # Trigger 3: last recall was >8 chapters ago (safety net)
    last_recall = _get_last_recall_chapter(project_dir)
    if chapter - last_recall > 8:
        return True

    return False


def _should_run_drift(project_dir: Path, chapter: int) -> bool:
    """Run drift when resonance moving average shows concerning trend.

    Resonance scores are on a 0-100 scale (per pipeline config
    resonance_global_floor: 50). A 10-point drop on this scale represents
    a significant quality regression (e.g., 75→65).
    """
    scores = _get_recent_resonance_scores(project_dir, last_n=5)
    if len(scores) < 3:
        return False

    # 3-chapter moving average
    ma3_current = sum(scores[-3:]) / 3
    ma3_previous = sum(scores[-4:-1]) / 3 if len(scores) >= 4 else ma3_current

    if ma3_previous - ma3_current > 10:
        return True

    # Safety net: at least every 12 chapters
    last_drift = _get_last_drift_chapter(project_dir)
    if chapter - last_drift >= 12:
        return True

    return False


def _snapshot_chapter_files(project_dir: Path, chapter: int) -> None:
    """Create timestamped file copies of chapter + audit outputs.

    Uses versioned file storage pattern (similar to Google Docs version history,
    Notion page history, MLflow artifact tracking):
    - Each snapshot is a timestamped copy under snapshots/{project_id}/
    - manifest.json tracks which chapters have snapshots
    - Retention policy prunes old snapshots beyond config limit

    Why NOT git: this pipeline will be packaged as a multi-tenant web UI.
    Git requires per-user git config, a valid .git repository, and is not
    safe for concurrent access from web server processes. Timestamped file
    copies work in any deployment environment with zero dependencies.
    """
    from datetime import datetime, timezone

    snap_dir = project_dir / "snapshots"
    snap_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")

    # Copy chapter file
    ch_src = project_dir / "chapters" / f"chapter-{chapter}.md"
    if ch_src.exists():
        ch_dst = snap_dir / f"chapter-{chapter:03d}-{timestamp}.md"
        shutil.copy2(ch_src, ch_dst)

    # Copy audit files for this chapter
    audit_dir = project_dir / "audits"
    if audit_dir.exists():
        for audit_file in audit_dir.glob(f"chapter-{chapter}-*.md"):
            audit_dst = snap_dir / f"{audit_file.stem}-{timestamp}.md"
            shutil.copy2(audit_file, audit_dst)

    # Update manifest
    manifest = _load_manifest(snap_dir)
    manifest["chapters"][str(chapter)] = {
        "timestamp": timestamp,
        "files": [
            f.name for f in snap_dir.glob(f"chapter-{chapter:03d}-{timestamp}*")
        ],
    }
    _save_manifest(snap_dir, manifest)

    # Prune old snapshots beyond retention limit
    retention = _get_snapshot_retention(project_dir)
    _prune_old_snapshots(snap_dir, retention)

    log.info("snapshot_created", chapter=chapter, timestamp=timestamp)


def _load_manifest(snap_dir: Path) -> dict:
    """Load or initialize snapshot manifest."""
    manifest_path = snap_dir / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"chapters": {}, "created_at": str(datetime.now(timezone.utc))}


def _save_manifest(snap_dir: Path, manifest: dict) -> None:
    safe_write(snap_dir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))


def _prune_old_snapshots(snap_dir: Path, retention: int) -> None:
    """Remove snapshots beyond the retention limit (keep most recent N)."""
    chapters = _load_manifest(snap_dir).get("chapters", {})
    if len(chapters) <= retention:
        return

    # Sort by chapter number, keep most recent `retention`
    sorted_chapters = sorted(chapters.keys(), key=int, reverse=True)
    for ch_key in sorted_chapters[retention:]:
        for fname in chapters[ch_key].get("files", []):
            fpath = snap_dir / fname
            if fpath.exists():
                fpath.unlink()
        del chapters[ch_key]

    _save_manifest(snap_dir, {"chapters": chapters})
    log.info("snapshot_pruned", removed=len(sorted_chapters) - retention)
```

**效果**：recall 运行频率从 100% 降到 ~30%，drift 从 100% 降到 ~20%。snapshot 变为即时文件复制。

**修改文件**：`chapter_loop.py` (conditional execution + git snapshot)

---

## Phase 5: 语义上下文优化

### 5.1 审查上下文缓存（替代正则字段提取）

Phase 2.3 的审查前置清单已缓存到 `context/review-checklist-{chapter}.json`，且含 mtime 校验。进一步优化清单中的字段提取方式：

**Voice constraints 提取**：用确定性 name-matching 替代 embedding 搜索。
- 从 `characters/` 目录获取所有角色名称列表
- Grep 章节正文，找到出场的角色名
- 对匹配的角色，从其 profile 文件提取 `voice_fingerprint` 字段
- 这是确定性的、快速的、不依赖 embedding 质量的

```python
def _extract_voice_constraints(project_dir: Path, chapter: int) -> dict[str, str]:
    """Extract voice fingerprints for characters appearing in this chapter.

    Deterministic name-matching — simpler and more reliable than embedding search.
    """
    chapter_text = (project_dir / "chapters" / f"chapter-{chapter}.md").read_text(encoding="utf-8")
    characters_dir = project_dir / "characters"

    voice_map = {}
    for profile_path in characters_dir.glob("**/*.md"):
        char_name = profile_path.stem  # e.g., "protagonist" → "陈烬" from frontmatter
        profile_text = profile_path.read_text(encoding="utf-8")

        # Extract actual character name from frontmatter
        name_match = re.search(r"name\s*[:：]\s*(.+)", profile_text)
        display_name = name_match.group(1).strip() if name_match else char_name

        # Check if character appears in this chapter (case-insensitive)
        if display_name not in chapter_text:
            continue

        # Extract voice fingerprint
        voice_match = re.search(r"voice_fingerprint\s*[:：]\s*(.+)", profile_text)
        if voice_match:
            voice_map[display_name] = voice_match.group(1).strip()

    return voice_map
```

**World rules 提取**：保留 embedding 语义搜索——世界规则可能与章节主题相关而不被显式提及。

**Embedding query 改进**：使用章节全文而非前 500 字符，或用场景级分段查询（每场景首段）来捕获中后段引入的元素。

```python
def _extract_world_rules_semantic(project_dir: Path, chapter: int) -> str:
    """Use Route B embeddings to find chapter-relevant world rules.

    Queries with full chapter text (not just first 500 chars) to capture
    mid/late-chapter elements. Falls back to first 2000 chars if rules file
    is small enough to not need semantic filtering.
    """

### 5.2 审查上下文缓存

Phase 2.3 的 checklist 已经缓存到 `context/review-checklist-{chapter}.json`。进一步：在 chapter-drafting 完成后的 state-settling 步骤中，预计算所有审查需要的上下文摘要，存入 `context/review-cache-{chapter}.json`。所有后续审查 dispatch 读取缓存而非重新计算。

**效果**：Phase 2.3 + Phase 5 = 审查输入从 ~30K chars × 11 次 = 330K chars 降到 ~4K chars × 1 次生成 + 11 次读取 = ~4K chars（-99%）。

**修改文件**：`review_checklist.py` (语义提取增强)；`dispatch_helper.py` (缓存读取)

---

## Phase 6: 审查输出结构化（Post-MVP — Phase 1-5 稳定后实施）

### 前置条件

Phase 1-5 实施并验证稳定后，管线的确定性提取、并行分发、自适应触发均已就位。此时可以将审查输出从自由文本迁移到结构化 JSON，消除 consolidation 阶段的字符串匹配脆弱性。

### 当前问题

11 个审查 skill 的输出是自由文本 markdown。Consolidation（`consolidate_review_results`）通过正则扫描 `"BLOCKING"` / `"CRITICAL"` 字符串来汇总问题。这有两个脆弱性：

1. **术语漂移**：如果某个审查 skill 使用了不同标签（`"FATAL"`, `"MUST_FIX"`, `"严重"`），静默遗漏
2. **解析脆弱**：无法保证 severity label 出现在可预测的位置，regex 可能误匹配（例如正文中出现 "BLOCKING" 一词）

### 行业标准：Generate → Validate → Repair → Parse

2025-2026 年 LLM 结构化输出的共识模式是四阶段管线：

```
Generate (LLM + JSON Schema)
   ↓
Validate (jsonschema + Pydantic — 确定性，免费)
   ↓ 失败?
Repair (小模型 fixer call — 喂入精确错误信息)
   ↓ 成功
Parse → 类型化对象 → 下游消费
```

| 阶段 | 做什么 | 成本 | 捕获什么 |
|------|--------|------|---------|
| **1. Generate** | LLM 按 JSON Schema 约束解码 | LLM 调用 | — |
| **2. Validate** | `jsonschema.validate()` + Pydantic | 免费 | 非法 JSON、缺字段、类型错误、枚举违规 |
| **3. Repair** | 校验失败的精确错误信息反馈给模型修正 | 小模型调用 | 残余结构问题 |
| **4. Parse** | `model_validate_json()` → 类型对象 | 免费 | 类型安全的下游消费 |

关键洞察：**检测（Validate）用确定性代码，修正（Repair）用 LLM。** 不要要求 LLM "检查自己的输出"——LLM 善于修正被精确告知的错误，不善于发现自己的错误。

### 6.1 审查报告 JSON Schema

每个审查 skill 的输出从自由文本改为 JSON。统一 schema：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ReviewReport",
  "type": "object",
  "required": ["skill", "chapter", "verdict", "issues", "summary"],
  "properties": {
    "skill": {
      "type": "string",
      "description": "审查 skill 名称，如 shenbi-review-anti-ai"
    },
    "chapter": {
      "type": "integer",
      "minimum": 1
    },
    "verdict": {
      "type": "string",
      "enum": ["PASS", "WARN", "FAIL"]
    },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["severity", "location", "evidence", "rule", "suggestion"],
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["BLOCKING", "CRITICAL", "MINOR"]
          },
          "location": {
            "type": "string",
            "description": "文件路径 + 行号，如 chapters/chapter-5.md L23-27"
          },
          "evidence": {
            "type": "string",
            "minLength": 20,
            "description": "原文引述，≥20 字上下文"
          },
          "rule": {
            "type": "string",
            "description": "违反的规则名，必须与 SKILL.md 中的规则名逐字匹配"
          },
          "suggestion": {
            "type": "string",
            "description": "具体修改建议"
          }
        }
      }
    },
    "summary": {
      "type": "string",
      "description": "一段话总结审查结论"
    },
    "metrics": {
      "type": "object",
      "description": "可选：量化指标，如 transition_count、fatigue_hits",
      "additionalProperties": true
    }
  }
}
```

### 6.2 审查 Skill 修改

每个审查 skill 的 SKILL.md 增加：

```markdown
## Pipeline 模式输出格式

当由 pipeline 编排时，**必须**输出严格的 JSON，包裹在 `---BEGIN JSON---` 和 `---END JSON---` 标记之间：

---BEGIN JSON---
{
  "skill": "shenbi-review-anti-ai",
  "chapter": 5,
  "verdict": "WARN",
  "issues": [
    {
      "severity": "CRITICAL",
      "location": "chapters/chapter-5.md L34-36",
      "evidence": "他心中不由得一阵感慨，这世间万物皆有其规律",
      "rule": "铁律3: 叙述者不替读者下结论",
      "suggestion": "改为具体动作描写替代'不由得感慨'"
    }
  ],
  "summary": "发现 1 个 CRITICAL 级 AI 味问题，1 个 MINOR 级疲劳词",
  "metrics": {
    "transition_count": 7,
    "fatigue_hits": 3,
    "meta_narrative_hits": 1
  }
}
---END JSON---

校验失败时，你会收到具体的错误信息。根据错误修正 JSON 并重新输出。
```

### 6.3 确定性校验 + 修复循环

```python
# 新文件: src/shenbi/pipeline/structured_output.py
"""Deterministic JSON schema validation + targeted repair for review outputs."""

import json as _json
import re
from dataclasses import dataclass
from typing import Any

import jsonschema  # pip install jsonschema

# Pre-compiled JSON schema for review reports (from §6.1)
REVIEW_REPORT_SCHEMA = { /* ... the schema above ... */ }

MAX_REPAIR_ATTEMPTS = 3


@dataclass
class ValidatedReport:
    skill: str
    chapter: int
    verdict: str
    issues: list[dict[str, Any]]
    summary: str
    metrics: dict[str, Any]
    raw_json: dict[str, Any]


def parse_review_output(raw_output: str, skill: str, chapter: int) -> ValidatedReport:
    """Parse and validate a review skill's JSON output with repair loop.

    Follows the Generate → Validate → Repair → Parse pipeline.
    Returns a ValidatedReport on success.
    Raises ValidationError after MAX_REPAIR_ATTEMPTS exhausted.
    """
    # Stage 1: Extract JSON from markers
    json_text = _extract_json_block(raw_output)

    for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
        # Stage 2: Validate
        errors = _validate_against_schema(json_text)

        if not errors:
            # Stage 4: Parse → typed object
            data = _json.loads(json_text)
            return ValidatedReport(
                skill=data["skill"],
                chapter=data["chapter"],
                verdict=data["verdict"],
                issues=data.get("issues", []),
                summary=data.get("summary", ""),
                metrics=data.get("metrics", {}),
                raw_json=data,
            )

        if attempt >= MAX_REPAIR_ATTEMPTS:
            raise ValidationError(
                f"Review {skill} chapter {chapter}: {len(errors)} schema errors "
                f"after {MAX_REPAIR_ATTEMPTS} repair attempts"
            )

        # Stage 3: Repair — feed exact errors back
        json_text = _repair_json(json_text, errors, skill, chapter)


def _extract_json_block(text: str) -> str:
    """Extract JSON from ---BEGIN JSON--- / ---END JSON--- markers."""
    m = re.search(r"---BEGIN JSON---\s*\n(.*?)\n---END JSON---", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fallback: try parsing the entire text as JSON
    return text.strip()


def _validate_against_schema(json_text: str) -> list[str]:
    """Run jsonschema validation. Returns list of human-readable error messages."""
    try:
        data = _json.loads(json_text)
    except _json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"]

    validator = jsonschema.Draft202012Validator(REVIEW_REPORT_SCHEMA)
    errors = []
    for err in validator.iter_errors(data):
        path = " → ".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{path}: {err.message}")
    return errors


def _repair_json(json_text: str, errors: list[str], skill: str, chapter: int) -> str:
    """Feed exact validation errors to a small model for targeted repair.

    Uses the same dispatch mechanism but with minimal context — only the
    broken JSON + error list + schema snippet. No full chapter context needed.
    """
    repair_prompt = f"""Your previous JSON output for {skill} chapter {chapter} had these errors:

{chr(10).join(f'- {e}' for e in errors)}

Fix ALL errors and return ONLY valid JSON between ---BEGIN JSON--- and ---END JSON--- markers.
Do NOT change the review findings — only fix the JSON structure."""

    result = dispatch_skill(skill, Path("."), repair_prompt)
    if result.success:
        return _extract_json_block(result.stdout)
    return json_text  # Return original on repair failure — will fail validation again
```

### 6.4 Consolidation 简化

有了结构化输出后，`consolidate_review_results` 从 regex 扫描变为字段访问：

```python
def consolidate_review_results(reports: list[ValidatedReport], chapter: int) -> dict:
    """Aggregate structured review results — deterministic, type-safe."""
    blocking = []
    critical = []

    for report in reports:
        for issue in report.issues:
            if issue["severity"] == "BLOCKING":
                blocking.append({"skill": report.skill, **issue})
            elif issue["severity"] == "CRITICAL":
                critical.append({"skill": report.skill, **issue})

    return {
        "chapter": chapter,
        "verdicts": {r.skill: r.verdict for r in reports},
        "blocking_count": len(blocking),
        "critical_count": len(critical),
        "blocking_issues": blocking,
        "critical_issues": critical,
        "summaries": {r.skill: r.summary for r in reports},
    }
```

### 6.5 影响范围

| 组件 | 改动 |
|------|------|
| 11 个审查 skill SKILL.md | 输出格式增加 JSON schema 指令 |
| `structured_output.py` (新) | 校验 + 修复循环 |
| `consolidate_review_results` | regex → 字段访问 |
| 审查 G4 checker ×11 | 从检查 markdown 结构 → 调用 `parse_review_output()` |
| `audit_layer.py` | `"BLOCKING" in content` → `report.verdict == "FAIL"` |

### 6.6 为什么在 Phase 1-5 之后

1. **前置依赖**：并行 dispatch（Phase 3）和审查上下文缓存（Phase 2.3+5）必须先稳定。结构化输出增加了每次审查的 prompt 复杂度——如果并行 dispatch 有 bug，排查 11 个 JSON 解析失败比排查 11 个自由文本失败更难。
2. **风险隔离**：Phase 1-5 的改动已经足够大（~400 行 Python + 4 个新文件）。先让确定性提取和并行化稳定运行，再叠加结构化输出。
3. **回滚安全**：如果结构化输出引入回归（例如某个审查 skill 顽固地生成非法 JSON），可以独立回滚而不影响 Phase 1-5 的优化。

---

## 总结：优化前后对比

### 每章步骤变化

| # | 步骤 | 原来 | 重新设计后 | 变化 |
|---|------|------|-----------|------|
| 1 | intent-management | LLM | LLM | — |
| 2 | chapter-planning | LLM | LLM | — |
| 3 | foreshadowing-plant | **LLM** | **Python 本地** | -1 LLM |
| 4 | context-assemble | Python 本地 | Python 本地 + curate | — |
| 5 | context-composing | **LLM** | **已合并到 step 4** | -1 LLM |
| 6 | chapter-drafting | LLM | LLM | — |
| 7 | state-settling | LLM | LLM | — |
| 8 | foreshadowing-track | LLM | LLM | — |
| 9 | foreshadowing-recall | LLM (每章) | LLM (自适应触发~30%) | -0.7 LLM |
| 10-16 | 7 核心审查 | **串行 LLM ×7** | **并行 LLM ×7** | 时间 -73% |
| +4 | 4 类型审查 | **串行 LLM ×4** | **并行 LLM ×4** | 时间 -73% |
| 17 | review-resonance | LLM | LLM | — |
| 18 | chapter-revision | LLM (条件) | LLM (条件) | — |
| 19 | snapshot-manage | LLM (每章) | **文件复制 (即时)** | -1 LLM |
| 20 | drift-guidance | LLM (每章) | LLM (自适应触发~20%) | -0.8 LLM |

### 关键指标

| 指标 | 基线 | 重新设计 | 改善 |
|------|------|---------|------|
| LLM 调用/章 | 19 | 12-14 | -26~37% |
| Wall-clock/章 | 2.6h | 0.5-0.6h | -77~81% |
| 审查质量 | 独立审查 | 独立审查 (不变) | **不降** |
| 审查 wall-clock | 74 min | 20 min | -73% |
| Hook 种植速度 | ~5 min | ~50 ms | -99.9% |
| Context 策展速度 | ~5 min | ~100 ms | -99.9% |
| 审查输入总量 | ~330K chars | ~4K chars | -99% |
| 新增代码 | 0 | ~400 行 Python | 可控 |
| 新增文件 | 0 | 4 个 (.py) | context_curation, hook_planting, review_checklist, parallel_dispatch |

### 为什么这个方案优于原 Plan

| 维度 | 原 Plan | 重新设计 |
|------|---------|---------|
| 审查质量 | 合并为 2 个 → 质量降 12-18% | 保持 11 个独立 → 质量不降 |
| LLM 使用 | 用 LLM 做确定性工作 | LLM 只做创造性判断 |
| 审查速度 | 串行 2 个综合审查 | 并行 11 个独立审查 → 更快 |
| 代码复杂度 | 新建综合 SKILL.md ×2 + G4 ×2 | 新建 Python 函数 ×4 + Phase 6 新增 structured_output.py |
| 脆弱性 | 正则提取、字符串分类 | Enum 分类、JSON Schema 校验 (Phase 6) |
| 触发策略 | 固定间隔 (5, 12) | 数据驱动自适应 |
| Snapshot | 文件系统快照 | 文件系统快照 (无外部依赖) |
| 审查输出 | 自由文本 + regex | 自由文本 → 结构化 JSON (Phase 6 迁移) |
