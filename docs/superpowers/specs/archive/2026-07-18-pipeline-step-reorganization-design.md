# Pipeline 步骤重组：删除、合并与新增 Spec

> **日期:** 2026-07-18
> **状态:** 设计中
> **严重度:** 🔴 Critical（架构级重组）
> **前置:** Spec LLM 上下文优化、Spec CN3、Spec CN5、Spec C2、Spec Volume Map 消费
> **目的:** 基于 56 章实际产出的全量审计数据，系统评估每章 ~24 个 pipeline 步骤的必要性——删除冗余、合并重复、补充缺失。

---

## 1. 评估方法

对每章 24 个步骤逐一评估三个维度：

| 维度 | 标准 |
|------|------|
| **价值密度** | 该步骤产出在最终小说质量中的边际贡献 |
| **替代性** | 是否可由确定性代码或其他步骤替代 |
| **上下文效率** | 上下文重复率（与相邻步骤共享多少输入文件） |

数据来源：56 章 xinghuo-ranqiong 产出 + 39 个 Spec 的审计发现。

---

## 2. 建议删除的步骤（3 个）

### DELETE-1: shenbi-escalation-review → 替换为确定性条件触发

**当前行为**：每章无条件运行，LLM 产出 `audits/chapter-N-review-summary.md`。

**审计证据**：
- 55/56 次调用产出 **99.3% 相同**的模板（"Reviews executed: 11, Successful: 11, Failed: 0"）
- 零章节特定信息
- 55 次 LLM dispatch 完全浪费

**替代方案**：
```python
# 确定性 review-summary 生成（无 LLM）
def generate_review_summary(project_dir, chapter):
    results = {}
    for audit_type in ALL_AUDIT_TYPES:
        audit_file = project_dir / 'audits' / f'chapter-{chapter}-{audit_type}.md'
        if audit_file.exists():
            results[audit_type] = _parse_audit_verdict(audit_file)

    # 仅在有 blocking/critical 时才调用 LLM 做 escalation
    has_blocking = any(r.get('blocking') for r in results.values())
    if has_blocking:
        return _dispatch_llm_escalation(project_dir, chapter, results)
    else:
        return _render_deterministic_summary(chapter, results)
```

**效果**：消除 55/56 次 LLM 调用，保留 escalation 能力。

---

### DELETE-2: shenbi-intent-management → 改为仅 volume boundary 运行

**当前行为**：每章运行，更新 `author_intent.md` 和 `current_focus.md`。

**审计证据**：
- `author_intent.md` 在整个 chapter loop 中仅最后被修改（Ch56 时间戳）
- `current_focus.md` 仅含 Ch56 数据（覆盖 bug CN3）
- `intent-management` 的 reads 合约仅读取 `author_intent.md` 和 `audit_drift.md`——**不读取当前章节**——因此无法基于实际叙事进展更新意图

**替代方案**：
- 仅在下述时机运行：volume boundary、drift-guidance 触发告警、author_intent 被人类修改
- chapter loop 中由 `_should_run_step` 拦截为非必要时跳过

**效果**：消除 ~52/56 次 LLM 调用（仅 volume boundary 运行）。

---

### DELETE-3: shenbi-context-composing → 已被确定性代码替代，应正式移除

**当前行为**：SKILL.md 仍存在于 skills/ 目录，chapter_loop 中 `shenbi-context-composing` 被 `_run_context_curation()` 拦截。

**审计证据**：
- `chapter_loop.py:1183-1197`：`context-composing` 被替换为确定性代码
- 但 STEP 定义中仍列出该 skill——造成混淆
- review checklist 生成也是确定性的（`review_checklist.py`）

**替代方案**：
- 从 `CHAPTER_STEPS` 中移除 `shenbi-context-composing` 条目
- 将 `pipeline-context-assemble` + 确定性策展合并为一个步骤（`pipeline-context-prepare`）
- `shenbi-context-composing` SKILL.md 标记为 DEPRECATED

---

## 3. 建议合并的步骤（2 组）

### MERGE-1: 3 个 foreshadowing skills → 1 个 lifecycle 调用

**当前**：每章 3 次独立 LLM 调用：
- `shenbi-foreshadowing-plant`（Step 3）：读取 plan + volume_map + pending_hooks，创建新钩子
- `shenbi-foreshadowing-track`（Step 8）：读取 chapter + pending_hooks，更新钩子生命周期
- `shenbi-foreshadowing-recall`（Step 9）：读取 pending_hooks，激活休眠钩子

**问题**：
- `pending_hooks.md`（10KB）被读取 **3 次**
- volume_map（26KB）被 plant 全量读取
- 三个操作共享同一数据集（pending_hooks）但各自独立调用
- plant（计划后）和 track（写作后）之间的时间差意味着 plant 的钩子在 track 之前不会被验证

**合并方案**：单一 `shenbi-foreshadowing-lifecycle` 调用（在 drafting 之后运行）：

```yaml
# 新 skill: shenbi-foreshadowing-lifecycle
contract:
  reads:
    - {file: plans/chapter-N-plan.md, fields: [7. 本章 hook 账]}
    - {file: chapters/chapter-N.md}  # 扫描钩子出现情况
    - {file: truth/pending_hooks.md}  # 一次读取
    - {file: outline/volume_map.md, fields: [跨卷桥接]}  # 仅提取当前卷桥接
  writes: []
  updates:
    - truth/pending_hooks.md
```

**操作顺序**（单次 LLM 调用内）：
1. **Recall**：扫描 pending_hooks 中的休眠钩子，判断是否应在本章重新激活
2. **Track**：对比 chapter 正文与 pending_hooks，更新每个钩子的生命周期状态
3. **Plant**：从 plan 和 volume_map 中提取新钩子，创建并注册

**效果**：
- LLM 调用：3 → 1（-67%）
- pending_hooks 读取：3 次 → 1 次
- volume_map 上下文：26KB → ~500B（字段过滤）
- 钩子生命周期一致性提升：plant 和 track 在同一上下文中，可交叉验证

---

### MERGE-2: 13 个审计器 → 5 个分组调用

**当前**：13 个独立 LLM 调用，每个独立读取完整 chapter-N.md（30KB × 13 = 390KB 重复）。

**分组逻辑**：按审计领域的上下文重叠度分组——共享相同输入文件的审计器合并。

| 组 | 合并的审计器 | 共享上下文 | 每章调用 | 合理性 |
|---|-----------|----------|---------|--------|
| **A: 事实一致性** | continuity + world-rules + pacing | chapter + world files + chapter_summaries | 1 | 三者都检查"事实是否自洽"——时间线、世界规则、节奏 |
| **B: 角色完整性** | character + dialogue + motivation + pov | chapter + protagonist + character_matrix | 1 | 四者都检查"角色是否一致"——人格、对话、动机、视角 |
| **C: 工艺质量** | texture + reader-pull + anti-ai | chapter + plan + genre-config | 1 | 三者都检查"写得怎么样"——段落节奏、读者吸引力、AI痕迹 |
| **D: 计划遵从** | memo-compliance + foreshadowing | chapter + plan + pending_hooks | 1 | 两者都检查"是否按计划执行"——8节遵从、伏笔兑现 |
| **E: 共鸣评分** | resonance | chapter + plan + style_profile + trend | 1 | 独立保留——评分需要不同的输出格式和趋势追踪 |
| **F: 合规** | sensitivity | chapter + genre-config + novel.json | 1 | 独立保留——敏感内容检查有特殊的通过/阻断逻辑 |

**从 13 → 6 个调用（-54%）**

**分组调用的 prompt 设计**：

```markdown
## 分组审计：角色完整性（character + dialogue + motivation + pov）

对你将收到的章节正文，从以下四个维度进行审计。
每个维度独立评分，发现缺陷时使用统一的四元素证据格式。

### 维度 1: 角色一致性 (character)
[audit instructions...]

### 维度 2: 对话质量 (dialogue)
[audit instructions...]

### 维度 3: 动机合理性 (motivation)
[audit instructions...]

### 维度 4: 视角一致性 (pov)
[audit instructions...]

## 输出格式
对每个维度输出独立的审计报告节，使用标准的缺陷证据格式。
```

**效果**：
- LLM 调用：13 → 6（-54%）
- chapter-N.md 重复读取：13 次 × 30KB → 6 次 × 30KB（-54%）
- 共享上下文缓存进一步减少到：1 次 × 30KB（共享）+ 6 次 × 审计特定指令
- 跨维度交叉验证：同一 LLM 在 character 和 dialogue 审计中可发现"角色在对话中 OOC"这种跨维度问题

---

## 4. 建议新增的步骤（4 个）

### ADD-1: pipeline-volume-align（确定性，无 LLM）

**时机**：chapter-planning 之后、chapter-drafting 之前

**功能**：
```python
def check_volume_alignment(project_dir, chapter, plan_text):
    """验证 chapter plan 是否与 volume_map 对齐。非阻断——仅 WARN。"""
    vm = (project_dir / 'outline' / 'volume_map.md').read_text()
    node = extract_chapter_node(vm, chapter)

    issues = []
    if node:
        # 关键术语匹配
        key_terms = extract_key_terms(node['desc'])
        match_rate = sum(1 for t in key_terms if t in plan_text) / len(key_terms)
        if match_rate < 0.3:
            issues.append(f"Volume alignment WARNING: only {match_rate:.0%} key terms from volume_map present in plan")

        # 人物登场检查
        expected_chars = extract_expected_characters(vm, chapter)
        for char in expected_chars:
            if char not in plan_text:
                issues.append(f"Volume alignment WARNING: {char} expected this chapter per volume_map but not in plan")

    return issues  # 不阻断，仅记录
```

**理由**：这是 volume_map 被忽略的直接修复——在 drafting 之前捕获偏离。

---

### ADD-2: pipeline-post-draft-extract（确定性，无 LLM）

**时机**：chapter-drafting 之后、state-settling 之前

**功能**：从刚完成的章节中自动提取关键事实，传递给 state-settling：

```python
def extract_chapter_facts(chapter_text):
    """确定性提取章节关键事实——无需 LLM。"""
    return {
        'character_locations': _extract_character_locations(chapter_text),
        'emotional_state': _extract_emotional_markers(chapter_text),
        'active_conflicts': _extract_conflict_markers(chapter_text),
        'hook_appearances': _extract_hook_references(chapter_text),
        'new_characters': _extract_new_character_introductions(chapter_text),
        'key_events': _extract_event_sentences(chapter_text),
    }
```

**理由**：state-settling 当前仅读 chapter-N.md（30KB 全量），缺少结构化指导。预先提取关键事实可：
- 减少 state-settling 需要的上下文（发送提取结果而非全量章节）
- 提高 truth 文件更新准确性（明确的"这是本章发生的事"）
- 使追加 vs 覆盖判断更清晰（对比提取结果与前一章的提取结果）

---

### ADD-3: pipeline-linguistic-drift-check（确定性，无 LLM）

**时机**：chapter-drafting G4 之后、审计之前

**功能**：Spec C2 的语言学漂移检测——每章运行，非条件触发：

```python
def check_linguistic_drift(project_dir, chapter):
    """每章运行语言学漂移检测。"""
    chapter_text = (project_dir / 'chapters' / f'chapter-{chapter}.md').read_text()
    baseline = _load_baseline(project_dir)

    metrics = compute_linguistic_drift(chapter_text, baseline)

    alerts = []
    if metrics['system_term_density'] > 30:
        alerts.append(f"System term density {metrics['system_term_density']:.0f}‰ — above 30‰ threshold")
    if metrics['em_dash_density'] > 20:
        alerts.append(f"Em-dash density {metrics['em_dash_density']:.0f}‰ — possible enumeration collapse")
    if metrics['dialogue_density'] < 1 and chapter > 10:
        alerts.append(f"Dialogue density near zero — possible character disappearance")

    # 连续 3 章触发 → 在下一章 planning prompt 中注入纠正指令
    return alerts
```

**理由**：C2 的根因是漂移检测未触发。每章确定性运行确保早期发现。

---

### ADD-4: pipeline-pre-revision-snapshot（确定性，无 LLM）

**时机**：chapter-revision 之前

**功能**：Spec C1 的修订前备份——在 revision 覆盖章节文件之前保存原文：

```python
def pre_revision_backup(project_dir, chapter):
    """修订前备份当前章节。"""
    chapter_path = project_dir / 'chapters' / f'chapter-{chapter}.md'
    backup_path = project_dir / 'chapters' / f'chapter-{chapter}-pre-rev.md'
    if chapter_path.exists():
        shutil.copy2(chapter_path, backup_path)
```

**理由**：Ch2/9/12/44/55 永久丢失的根因——修订 skill 覆盖了章节正文且无备份。

---

## 5. 重组后每章步骤

### 重组前（当前）：24 步骤，~24 次 LLM 调用

```
Step 1:  intent-management        [LLM]
Step 2:  chapter-planning          [LLM]
Step 3:  foreshadowing-plant       [LLM]
Step 4:  context-assemble          [确定性]
Step 5:  context-composing         [LLM — 已被确定性替代]
Step 6:  chapter-drafting          [LLM]
Step 7:  state-settling            [LLM]
Step 8:  foreshadowing-track       [LLM]
Step 9:  foreshadowing-recall      [LLM]
Step 10-22: 13 个审计器            [13 × LLM]
Step 23: chapter-revision          [LLM]
Step 24: escalation-review         [LLM]
(+ drift-guidance 条件触发)        [LLM]
(+ snapshot-manage)                [确定性]
```

### 重组后：~15 步骤，~10 次 LLM 调用

```
Step 1:  volume-align              [确定性] ← ADD-1
Step 2:  chapter-planning          [LLM]    ← volume_map 章节点提取后上下文减半
Step 3:  context-prepare           [确定性] ← DELETE-3: assemble+curation 合并
Step 4:  chapter-drafting          [LLM]
Step 5:  post-draft-extract        [确定性] ← ADD-2
Step 6:  linguistic-drift-check    [确定性] ← ADD-3
Step 7:  foreshadowing-lifecycle   [LLM]    ← MERGE-1: plant+track+recall 合并
Step 8:  state-settling            [LLM]    ← 补充 post-draft-extract 上下文
Step 9:  分组审计 A: 事实一致性    [LLM]    ← MERGE-2: continuity+world-rules+pacing
Step 10: 分组审计 B: 角色完整性    [LLM]    ← MERGE-2: character+dialogue+motivation+pov
Step 11: 分组审计 C: 工艺质量      [LLM]    ← MERGE-2: texture+reader-pull+anti-ai
Step 12: 分组审计 D: 计划遵从      [LLM]    ← MERGE-2: memo-compliance+foreshadowing
Step 13: 分组审计 E: 共鸣评分      [LLM]    ← resonance 独立保留
Step 14: 分组审计 F: 合规          [LLM]    ← sensitivity 独立保留
Step 15: pre-revision-snapshot      [确定性] ← ADD-4
Step 16: chapter-revision          [LLM]    ← 条件触发
(+ intent-management)              [LLM]    ← DELETE-2: 仅 volume boundary
(+ escalation-review)              [LLM]    ← DELETE-1: 仅 escalation 触发
(+ drift-guidance)                 [LLM]    ← 条件触发（drift-check 告警时）
(+ snapshot-manage)                [确定性]
```

---

## 6. 效果汇总

| 指标 | 当前 | 重组后 | 改善 |
|------|------|--------|------|
| 每章总步骤 | 24 | 16（+4 条件） | -33% |
| 每章 LLM 调用 | ~24 | ~10（+3 条件） | **-58%** |
| 每章 LLM tokens | ~337K | ~130K | **-61%** |
| chapter-N.md 读取次数 | 15 | 6（+共享缓存） | -60% |
| pending_hooks.md 读取次数 | 4 | 1（lifecycle 合并） | -75% |
| volume_map 全量传输 | 4 | 0（章节点提取 500B） | -100% |
| Glob 静默失败 | 5 skills | 0（修复展开） | 修复 |

### LLM 调用减少明细

| 来源 | 减少 |
|------|------|
| DELETE-1: escalation-review 条件化 | -0.9/章 |
| DELETE-2: intent-management 仅 boundary | -0.9/章 |
| DELETE-3: context-composing 确定性替代 | -1/章 |
| MERGE-1: 3 foreshadowing → 1 lifecycle | -2/章 |
| MERGE-2: 13 审计 → 6 分组 | -7/章 |
| **总减少** | **-11.8/章** |

---

## 7. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 分组审计降低单项审计质量 | 在每个分组 prompt 中保留完整的单审计检查清单；分组按共享上下文自然聚合 |
| foreshadowing lifecycle 合并后单次调用过于复杂 | 操作顺序为 recall→track→plant，逐步递进；保持独立输出节 |
| intent-management 仅 boundary 运行可能错过中期调整 | drift-guidance 触发时也运行 intent-management |
| 确定性步骤替代 LLM 后灵活性降低 | 所有确定性步骤产生 WARN 而非 HARD 阻断；LLM 可在后续步骤中覆盖 |

---

## 8. 新 Spec 关联

| 本 Spec 建议 | 关联已有 Spec |
|-------------|-------------|
| DELETE-1: escalation 条件化 | CN5 |
| DELETE-2: intent 仅 boundary | 新发现 |
| DELETE-3: context-composing 移除 | Spec LLM 上下文优化 |
| MERGE-1: foreshadowing 合并 | CN2（钩子系统修复的前提） |
| MERGE-2: 审计分组 | Spec LLM 上下文优化 §3.4 |
| ADD-1: volume-align | Spec Volume Map 消费 |
| ADD-2: post-draft-extract | CN1, CN3 |
| ADD-3: linguistic-drift-check | C2 |
| ADD-4: pre-revision-snapshot | C1 |
