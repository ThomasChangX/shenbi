# 确定性预提取与共享章节表示（SCR） Spec

> **日期:** 2026-07-18
> **状态:** 设计中
> **严重度:** 🟠 High（系统性性能优化）
> **前置:** Spec 步骤重组、Spec LLM 上下文优化
> **目的:** 对 13 个 LLM 调用实施确定性预提取——每章一次提取共享的"结构化章节表示（SCR）"，消除 13 次调用各自重复扫描 30KB 全文的浪费。同时评估行业最佳实践方案的最优性。

---

## 1. 背景

### 1.1 问题

每章 19 次 LLM 调用中，14 次的核心任务是**从同一段 30KB 章节正文中提取/核查信息**——13 次各自独立全文扫描 = 390KB 重复上下文。

### 1.2 适用性分类

| 类别 | 调用数 | 任务性质 | 方法 |
|------|--------|---------|------|
| ✅ 完全适用 | 9 | 信息提取/事实核查 | Facts-Only：结构化事实替代原文 |
| ⚠️ 部分适用 | 4 | 需原文做定性判断 | Smart Excerpting：原文相关段落 |
| ❌ 不适用 | 5 | 需全文做创造性/质感判断 | 保留全文 |

---

## 2. 行业最佳实践评估

### 2.1 候选方案对比

| 方案 | 描述 | 优点 | 缺点 | 适用性 |
|------|------|------|------|--------|
| **A: Per-Call Pre-Extraction** | 每个 LLM 调用前各自运行确定性提取 | 实现简单，改动小 | 同一段 30KB 文本被提取 13 次——冗余计算 | 🟡 |
| **B: Shared SCR (Map-Reduce)** | 每章一次提取 → SCR → 各调用消费 | 提取一次，13 次复用 | 需设计 SCR 格式和缓存机制 | ✅ |
| **C: Tool-Use LLM** | LLM 通过工具调用动态查询章节 | 灵活，适应新审计类型 | 工具调用增加延迟，不可缓存，DeepSeek tool-use 稳定性未知 | ❌ |
| **D: Multi-Agent** | 多个专业 LLM agent 并行分析章节 | 专业化 | 协调开销大，agent 间通信成本高 | ❌ |
| **E: Full RAG with Embeddings** | 预计算嵌入 → 语义检索相关段落 | 语义理解好 | 过度工程化——我们知道需要什么（对话、事件等），不需要语义搜索 | ❌ |

### 2.2 方案 B（Shared SCR）是最优解

**核心理由**：13 个调用共享同一输入源（chapter-N.md）。各调用需要的是该输入源的**不同子集**（对话、事件、角色动作等）。一次性提取+分类 → 各调用按需消费 = 最少的重复计算 + 最大的缓存复用。

**对标行业实践**：
- **Anthropic Contextual Retrieval**：预计算文档的 chunk embeddings + 各查询动态检索 → SCR 等价于"预分类的 chunks"，但比 embeddings 更精确（确定性分类 vs 语义近似）
- **Map-Reduce（Google 2004）**：Map = 一次性提取章节的所有结构化信息，Reduce = 各 LLM 调用基于子集做判断
- **Apache Spark Catalyst**：查询优化器先分析所有查询的共性，提取共享子表达式 → SCR = 共享子表达式

---

## 3. 方案设计

### 3.1 架构

```
chapter-N.md (30KB)
       │
       ▼
┌──────────────────────────────────────┐
│  Structured Chapter Representation   │  ← 确定性提取，每章一次
│  (SCR)                               │
│                                      │
│  📍 character_locations: [...]       │  → audit-continuity, state-settling
│  💬 dialogue_segments: [...]         │  → audit-dialogue, audit-character
│  📅 event_timeline: [...]            │  → audit-continuity, audit-pacing
│  🎭 emotional_markers: [...]         │  → state-settling, audit-character
│  🪝 hook_appearances: [...]          │  → audit-foreshadowing, lifecycle
│  🌍 world_refs: [...]                │  → audit-world-rules
│  🔀 pov_shifts: [...]                │  → audit-pov
│  🔗 decision_points: [...]           │  → audit-motivation
│  📖 opening_paragraph                │  → audit-reader-pull
│  📖 closing_paragraph                │  → audit-reader-pull
│  📊 paragraph_stats                  │  → audit-pacing, audit-texture
│  ⚠️ sensitive_hits: [...]            │  → audit-sensitivity
│  🔤 fatigue_words: [...]             │  → audit-anti-ai (辅助)
│  🔤 transition_markers: [...]        │  → audit-anti-ai (辅助)
│  💡 implicit_info: [...]             │  → state-settling, audit-motivation
│                                      │  (隐式情感/关系段落——保留原文)
└──────────────────────────────────────┘
       │
       ├──→ chapter-planning: {volume_node, current_focus, story_frame,
       │                      character_locations_summary, event_summary}
       │
       ├──→ state-settling: {character_locations, emotional_markers,
       │                      event_timeline, hook_appearances, implicit_info}
       │
       ├──→ foreshadowing-lifecycle: {hook_appearances, plan_hooks}
       │
       ├──→ audit-continuity: {event_timeline, character_locations, world_refs}
       ├──→ audit-character: {dialogue_segments, emotional_markers, implicit_info}
       ├──→ audit-world-rules: {world_refs, world_rules_summary}
       ├──→ audit-pacing: {event_timeline, paragraph_stats}
       ├──→ audit-memo-compliance: {plan_checklist, event_timeline}
       ├──→ audit-foreshadowing: {hook_appearances, pending_hooks}
       ├──→ audit-pov: {pov_shifts}
       │
       ├──→ audit-dialogue: {dialogue_segments (+ original text)}
       ├──→ audit-motivation: {decision_points, implicit_info (+ original text)}
       ├──→ audit-reader-pull: {opening_paragraph, closing_paragraph (+ original)}
       └──→ audit-sensitivity: {sensitive_hits (+ original context)}
```

### 3.2 SCR 生成器

```python
# src/shenbi/pipeline/scr_extractor.py

@dataclass
class StructuredChapterRepresentation:
    chapter: int
    extracted_at: str

    # Facts-Only fields (deterministic, high precision)
    character_locations: list[dict]       # [{name, location, evidence, line_range}]
    dialogue_segments: list[dict]         # [{speaker, text, line_range, tags}]
    event_timeline: list[dict]            # [{description, line_range, characters_involved}]
    emotional_markers: list[dict]         # [{character, emotion, evidence, confidence}]
    hook_appearances: list[dict]          # [{hook_id, line_range, context}]
    world_refs: list[dict]               # [{element, category, line_range}]
    pov_shifts: list[dict]               # [{from_pov, to_pov, line_range}]
    decision_points: list[dict]           # [{character, decision, cause_chain, effect, line_range}]
    paragraph_stats: dict                 # {count, lengths, dialogue_density, etc.}
    sensitive_hits: list[dict]            # [{word, line_range, surrounding_context}]
    fatigue_word_hits: list[dict]         # [{word, count, line_ranges}]
    transition_markers: list[dict]        # [{marker, line_range}]

    # Smart-Excerpting fields (original text preserved)
    opening_paragraph: str                # 原始开头段落
    closing_paragraph: str                # 原始结尾段落
    implicit_info_passages: list[str]     # 隐式情感/关系的原始段落

    # Metadata
    total_chinese_chars: int
    extraction_confidence: float          # 0-1, 基于提取规则的覆盖率

def extract_scr(project_dir: Path, chapter: int) -> StructuredChapterRepresentation:
    """每章一次：确定性提取结构化章节表示。

    行业实践对标：
    - Anthropic Contextual Retrieval: 预计算文档结构
    - Map-Reduce: Map 阶段——一次扫描，多维输出
    - 高召回低精确：宁可多提取，不漏关键信息
    """
    chapter_text = (project_dir / 'chapters' / f'chapter-{chapter}.md').read_text()
    prose = extract_prose(chapter_text)  # 剥离 META 块

    scr = StructuredChapterRepresentation(
        chapter=chapter,
        extracted_at=datetime.now(timezone.utc).isoformat(),

        # 每项提取独立运行，可并行
        character_locations=_extract_character_locations(prose),
        dialogue_segments=_extract_dialogue_segments(prose),
        event_timeline=_extract_event_timeline(prose),
        emotional_markers=_extract_emotional_markers(prose),
        hook_appearances=_extract_hook_appearances(prose),
        world_refs=_extract_world_references(prose),
        pov_shifts=_extract_pov_shifts(prose),
        decision_points=_extract_decision_points(prose),
        paragraph_stats=_compute_paragraph_stats(prose),
        sensitive_hits=_scan_sensitive_words(prose),
        fatigue_word_hits=_scan_fatigue_words(prose),
        transition_markers=_scan_transition_markers(prose),

        opening_paragraph=_extract_opening(prose),
        closing_paragraph=_extract_closing(prose),
        implicit_info_passages=_extract_implicit_passages(prose),

        total_chinese_chars=sum(1 for c in prose if '\u4e00' <= c <= '\u9fff'),
        extraction_confidence=_compute_confidence(prose),
    )

    # 缓存到磁盘
    cache_path = project_dir / 'context' / f'chapter-{chapter}-scr.json'
    safe_write(cache_path, json.dumps(asdict(scr), ensure_ascii=False, indent=2))

    return scr
```

### 3.3 各 LLM 调用的 SCR 消费

```python
# dispatch_helper.py: 在 _build_skill_prompt 中

SCR_CONSUMER_MAP = {
    'shenbi-chapter-planning': ['volume_node', 'character_locations', 'event_timeline'],
    'shenbi-state-settling': ['character_locations', 'emotional_markers',
                               'event_timeline', 'hook_appearances', 'implicit_info_passages'],
    'shenbi-foreshadowing-lifecycle': ['hook_appearances', 'pending_hooks'],
    'shenbi-review-continuity': ['event_timeline', 'character_locations', 'world_refs'],
    'shenbi-review-character': ['dialogue_segments', 'emotional_markers', 'implicit_info_passages'],
    'shenbi-review-world-rules': ['world_refs', 'world_rules_summary'],
    'shenbi-review-pacing': ['event_timeline', 'paragraph_stats'],
    'shenbi-review-memo-compliance': ['plan_checklist', 'event_timeline'],
    'shenbi-review-foreshadowing': ['hook_appearances', 'pending_hooks'],
    'shenbi-review-pov': ['pov_shifts'],
    'shenbi-review-dialogue': ['dialogue_segments'],       # + original text preserved
    'shenbi-review-motivation': ['decision_points', 'implicit_info_passages'],
    'shenbi-review-reader-pull': ['opening_paragraph', 'closing_paragraph'],
    'shenbi-review-sensitivity': ['sensitive_hits'],
}

def inject_scr_context(skill_name: str, scr: StructuredChapterRepresentation,
                       existing_inputs: dict) -> dict:
    """将 SCR 的相关字段注入 LLM 上下文，替代原始文件。

    对于 Facts-Only 调用：完全替代 chapter-N.md
    对于 Smart-Excerpting 调用：SCR 字段 + 保留原始段落
    对于不适用调用：SCR 字段作为补充（不替代原文）
    """
    fields = SCR_CONSUMER_MAP.get(skill_name, [])
    if not fields:
        return existing_inputs  # 不适用——保留原文

    scr_context = {}
    for field in fields:
        value = getattr(scr, field, None)
        if value:
            scr_context[field] = value

    # 替换 chapter-N.md 为 SCR 字段
    if 'chapters/chapter-' in str(existing_inputs):
        del existing_inputs[list(existing_inputs.keys())[0]]  # 移除原始章节

    existing_inputs['_scr_extracted'] = json.dumps(scr_context, ensure_ascii=False, indent=2)
    return existing_inputs
```

---

## 4. 与"不适用"调用的协作

5 个不适用调用（drafting, anti-ai, texture, resonance, revision）仍然接收完整原文。但 SCR 可作为辅助：

| 调用 | SCR 辅助 |
|------|---------|
| drafting | SCR 不适用——但 plan + context 已被确定性生成 |
| anti-ai | `fatigue_word_hits` + `transition_markers` 作为预扫描参考 |
| texture | `paragraph_stats` 作为定量辅助 |
| resonance | SCR 不适用——但 `opening_paragraph` + `closing_paragraph` 可用于快速定位 |
| revision | SCR 不适用——但审计报告已提供修改指导 |

---

## 5. 效果

### 5.1 输入缩减

| 类别 | 调用数 | 当前输入/调用 | SCR 后输入/调用 | 节省/调用 | 总节省 |
|------|--------|------------|---------------|---------|--------|
| Facts-Only | 9 | 30-114KB | 3-8KB | 85-95% | ~400KB |
| Smart Excerpting | 4 | 30-42KB | 5-10KB | 75-85% | ~120KB |
| 不适用 | 5 | 30-55KB | 30-55KB | 0% | 0 |
| **总计** | **18** | **961KB** | **~280KB** | **71%** | **~680KB** |

### 5.2 时间节省

| 来源 | 节省 |
|------|------|
| 上下文处理减少（680KB × 0.1s/KB） | ~1 min |
| LLM 推理切换减少（14→1 次全文扫描） | ~15 min |
| 更快的 LLM 生成（更少的输入 → 更少的注意力分散） | ~10 min |
| **总计** | **~26 min/章** |

### 5.3 累积效果（与步骤重组+并行化叠加）

| 优化 | 每章 |
|------|------|
| 当前基线 | ~43 min |
| + 步骤重组（删除+合并） | ~30 min |
| + 并行化（lifecycle ∥ state-settling） | ~27 min |
| + SCR 预提取（本 Spec） | **~17 min** |
| **总改善** | **-60%** |

---

## 6. 验证标准

1. SCR 提取的 `character_locations` 与章节实际内容一致（抽查 5 章）
2. Facts-Only 调用使用 SCR 后的审计结果与使用全文的结果一致（A/B 对比，3 章）
3. Smart Excerpting 调用在 `implicit_info_passages` 中保留了所有含情感/关系标记的段落
4. SCR 缓存命中率 100%（同一章不重复提取）
5. `extraction_confidence ≥ 0.85`（覆盖了 85% 以上的已知提取模式）
6. `just check` 全量通过

---

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 新提取模式遗漏关键信息 | 高召回策略——宁可多提取。`extraction_confidence` 低于阈值时回退到全文 |
| 正则提取对非标准文本失效 | 多层回退：正则 → 启发式 → 标记为"低置信"，传给 LLM 时附带原文 |
| SCR 格式演变导致缓存失效 | SCR 含版本号，旧版本自动触发重新提取 |
| 部分调用仍需要全文（抗 AI、texture） | 这些调用的输入不变——SCR 仅作为补充元数据 |
