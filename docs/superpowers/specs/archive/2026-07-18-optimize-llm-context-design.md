# LLM 调用上下文设计全面优化 Spec

> **日期:** 2026-07-18
> **状态:** 设计中
> **严重度:** 🟠 High（系统性效率缺陷）
> **前置:** Spec CN3（Truth 追加模式）、Spec S2（Checklist 静态提取）、Spec Volume Map 消费
> **目的:** 基于行业最佳实践，对 pipeline 中每次 LLM 调用的上下文设计进行逐个审查和优化——压缩浪费、补充缺失、重构结构。

---

## 1. 背景

### 1.1 当前状态

每章 chapter loop 产生 **~24 次 LLM 调用**，每次调用推送 **~17K tokens 上下文**（平均），每章总上下文消耗 **~408K tokens**，56 章合计 **~22.9M tokens**。

其中估计 **38%（~153K tokens/章）是浪费**——要么是重复内容（13 个审计器各自读取同一章节）、要么是无关内容（volume_map 的 99% 无关章节）、要么是过期数据（truth 文件仅含最后一章）。

### 1.2 审查方法

对每个 LLM 调用类型，按四个维度评估：

| 维度 | 评估标准 |
|------|---------|
| **压缩机会** | 上下文中有多少是可以去除而不影响输出质量的 |
| **补充需求** | 缺少哪些上下文导致输出质量下降（如 state-settling 缺少 volume_map） |
| **结构优化** | 上下文组织方式是否符合"指令优先、分级提示、负面约束"的最佳实践 |
| **批处理机会** | 是否可以将多个 LLM 调用合并为一次 |

---

## 2. 逐 Skill 上下文审查

### 2.1 shenbi-chapter-planning（~22.5K tokens）

**当前上下文：** 7 个输入文件（83KB） + 5KB 系统 prompt + 1.5KB 用户模板

| 文件 | 大小 | 有效性 | 问题 |
|------|------|--------|------|
| volume_map.md | 26KB | **2%** | 460 行中仅 2 行与当前章相关 |
| current_focus.md | 20KB | 100% | ✅ |
| current_state.md | 10KB | **1%** | 覆盖 bug——仅 Ch56 数据 |
| pending_hooks.md | 10KB | 80% | 🟡 非结构化 |
| chapter_summaries.md | 6KB | **2%** | 覆盖 bug——仅 1 章 |
| story_frame.md | 5KB | 100% | ✅ |
| author_intent.md | 5KB | 100% | ✅ |

**压缩（-53% → ~10.5K tokens）：**
- volume_map：完整文件 → 当前章节点提取（Spec Volume Map 消费）
- current_state + chapter_summaries：修复 CN3 后变为有用，否则跳过过期文件
- pending_hooks：标准化格式（Spec CN2）

**补充：**
- 前 3 章的实际结尾段落（帮助 Section 2 "读者此刻在等什么" 更精准）
- 上一章的 resonance 评分（调整本章的野心级别）

**结构优化：**
- 当前：volume_map 在"Input Files"区与其他文件并列 → LLM 视为参考资料而非指令
- 改为：`## ⚠️ VOLUME MAP NODE (MUST ALIGN) → ## Input Files`
- 增加负面约束：`## DO NOT: 偏离以下卷纲节点超过 30%。如需要偏离，必须在 Section 1 中明确说明理由。`

---

### 2.2 shenbi-chapter-drafting（~10K tokens）

**当前上下文：** chapter plan + context + style_profile + genre-config + audit_drift

**压缩（-25% → ~7.5K tokens）：**
- style_profile：当前为 bootstrap（无实际数据）→ 在 CN4 修复前可跳过
- audit_drift：仅 849B → 保留但确保非空
- Plan 字段级读取：仅读取 section 1/3/6/8（已声明 `fields:`）→ 验证此项是否被实际执行

**补充：**
- **volume_map 当前章节点**（当前 drafting 不读 volume_map！）→ 确保章节内容不偏离卷纲
- **前章结尾段落**（帮助续写开头与上文衔接）

**结构优化：**
- 增加 `## STYLE CONSTRAINTS` 区——从 style_profile 提取关键约束（如果 CN4 已修复）
- 增加 `## CONTINUITY CHECKPOINTS`——前章的 3 个关键状态（位置、情感、活跃冲突）

---

### 2.3 shenbi-state-settling（~9K tokens）— 🔴 最严重的上下文不足

**当前上下文：** 仅 `chapters/chapter-N.md`（30KB）——**一个文件，零结构性上下文**。

**补充（+80% → ~16K tokens）：**

| 缺失的上下文 | 用途 | 大小估计 |
|------------|------|---------|
| 前一版 truth 文件 | 知道什么变了 → 追加而非覆盖 | ~5KB |
| volume_map 当前章节点 | 知道本章在弧线中的位置 | ~500B |
| character_matrix.md | 更新角色状态而非替换为参数 | ~4KB |
| 前章 chapter_summary | 维护跨章连续性 | ~1KB |
| pending_hooks 前版 | 追加新钩子而非覆盖旧钩子 | ~5KB |

**这是 CN3（覆盖模式）和 CN1（角色消失）的直接根因——LLM 没有足够上下文来做出正确的"追加 vs 覆盖"判断。**

---

### 2.4 审计组（13 skills × ~20K tokens = 260K tokens/章）— 🔴 最大的浪费源

**当前上下文：** 每个审计器独立接收 `chapter-N.md`（30KB）+ `chapter-N-plan.md`（13KB）+ 共享 truth 文件（~30KB）。

**问题：13 个审计器各自独立读取同一份 30KB 章节文件 = 390KB 重复传输。**

**压缩方案 A：共享上下文缓存（-85%）**

```
传统模式：                       共享缓存模式：
Audit 1 ← chapter(30KB)         Audit 1 ─┐
Audit 2 ← chapter(30KB)         Audit 2 ─┤
...                              ...     ├─ Shared: chapter(30KB) + plan(13KB) + truth(30KB)
Audit 13 ← chapter(30KB)        Audit 13 ─┘  = 73KB total (not 13×73KB)

Each: 73KB context              Each: 3KB audit-specific instructions + 73KB shared
Total: 13 × 73KB = 949KB        Total: 73KB + 13 × 3KB = 112KB
Savings: 837KB/章 (88%)
```

**实现**：在 `dispatch_helper.py` 中增加 `_build_shared_audit_context()`，所有审计 skill 共享同一份章节+计划+truth 上下文，每审计器仅附加其特定的审计检查清单（从 SKILL.md 提取）。

**压缩方案 B：级联审计（-50%）**

如果前 4 个核心审计（continuity + character + world-rules + pacing）全部 PASS 且 confidence > 90%：
→ 跳过其余 9 个审计
→ 但 resonance 和 memo-compliance 始终运行（质量评分需要）

---

### 2.5 shenbi-review-resonance（~14K tokens）

**补充：**
- 前 5 章的 resonance 趋势（修复 CN3 后）→ 评估当前章是否在改善或恶化
- volume_map 的张力曲线位置 → 根据章在弧线中的位置调整评分标准（高潮章应有更高标准）

**结构优化：**
- 当前 resonance 审计格式要求过于严格 → G4 重试 35 次
- 在 prompt 中增加**完整示例**（不仅仅是字段名列表）——Spec M5

---

### 2.6 shenbi-chapter-revision（~14K tokens）

**补充：**
- 审计报告摘要（哪些审计发现问题，哪些 PASS）→ 聚焦修订范围
- 前次修订历史（如果是第二次修订）→ 避免重复无效修改

**结构优化：**
- 增加 `## REVISION PRIORITIES`：按严重度排序的修订项
- 增加 `## DO NOT REGENERATE`：明确列出不应改动的段落

---

### 2.7 shenbi-context-composing（~18K tokens）

**压缩：**
- volume_map：同 planning，提取当前章节点
- Review checklist 静态字段 → Spec S2 提取到模板

**补充：**
- 前章 context 文件（如果存在）→ 维护 context 连续性
- 当前章的 resonance 评分 → 调整 context 的紧张度

---

### 2.8 shenbi-foreshadowing-plant/track/recall（各 ~8-12K tokens）

**补充：**
- volume_map 跨卷桥接（哪些钩子需要在 N 章后激活）→ 帮助规划钩子生命周期
- 前版 pending_hooks（修复 CN3 后）→ 知道哪些钩子已 PLANTED/TRIGGERED

---

### 2.9 shenbi-escalation-review（~8K tokens）

**压缩（-100%）：**
- Spec CN5：当无 escalation 信号时**完全跳过**此调用
- 当前 55/56 次调用产出相同模板——纯浪费

---

## 3. 行业最佳实践对照与具体修复方案

### 3.0 方法论：四个来源

| 来源 | 核心原则 | 本 Spec 应用 |
|------|---------|-------------|
| **Anthropic Context Engineering** | 指令置顶（primacy）、XML 结构化分隔、数据与指令分离、缓存复用 | §3.1, §3.4, §3.7 |
| **OpenAI Prompt Engineering** | 系统消息=角色/语调、用户消息=任务、few-shot 示例、CoT 复杂推理 | §3.2, §3.6 |
| **LangChain/LlamaIndex RAG** | 文档分块+重叠、检索增强生成、上下文预算、去重 | §3.3, §3.5 |
| **Google Prompt Design** | 任务优先排序、结构化输出、负面示例 | §3.8, §3.12 |

---

### 3.1 Bug 1：Glob 模式静默失败 → 文件通配符展开

**行业实践**：LangChain `DirectoryLoader` 模式——通配符应在上下文构建时展开，并在预算约束下优先级排序。

**具体修复**（`dispatch_helper.py:142-161`）：

```python
# 替换 L142-161 的简单路径拼接
import glob as globmod

def _resolve_read_path(project_dir: Path, read_path: str, chapter: int | None) -> list[tuple[str, str]]:
    """解析读取路径，支持通配符展开。返回 [(resolved_name, full_path_str), ...]。

    行业实践：通配符在构建时展开（LangChain DirectoryLoader），
    结果按优先级排序后纳入总预算。
    """
    resolved = resolve_or_skip(read_path, chapter)
    if resolved is None:
        return []

    # 通配符展开
    if '*' in resolved or '?' in resolved:
        pattern = str(project_dir / resolved)
        matches = sorted(globmod.glob(pattern, recursive=True))
        if not matches:
            log.warning("glob_no_matches", skill=skill, pattern=pattern)
            return [(resolved, f"[glob matched 0 files: {resolved}]")]

        # 按 mtime 降序（最新文件优先），限制数量
        matches_with_mtime = [(m, Path(m).stat().st_mtime) for m in matches]
        matches_with_mtime.sort(key=lambda x: -x[1])

        results = []
        for m_path, _ in matches_with_mtime[:50]:  # 最多 50 个文件
            rel = str(Path(m_path).relative_to(project_dir))
            results.append((rel, m_path))
        return results

    # 单文件路径
    full_path = project_dir / resolved
    return [(resolved, str(full_path))] if full_path.exists() else [(resolved, f"[file not found: {resolved}]")]
```

**额外收益**：`review-long-span` 恢复跨章 n-gram 分析能力；`review-character` 可读取 `characters/major/*.md`。

---

### 3.2 Bug 2：UTF-8 截断破坏多字节字符 → 安全截断函数

**行业实践**：Python `text[:limit]` 在字符边界操作（非字节），但 `len(text)` 计算的是码点数——中文字符 1 码点 = 1 长度。问题仅在 `text.encode()[:limit]` 时出现。核实后：当前代码使用 `len(text)`（字符数），截断在字符边界，**无 UTF-8 破坏**。

但存在另一个问题：**硬截断无指示**——LLM 收到被截断的文本但不知道。

**具体修复**：

```python
def _safe_truncate(text: str, limit: int, label: str = "") -> str:
    """安全截断，添加截断指示器。

    行业实践（Anthropic）：当内容被截断时，应明确告知模型，
    避免模型基于不完整信息做出错误推断。
    """
    if len(text) <= limit:
        return text

    # 在 limit 处截断，保留完整的段落/句子边界
    truncated = text[:limit]
    # 回退到最后一个完整段落
    last_para = truncated.rfind('\n\n')
    if last_para > limit * 0.7:  # 如果最后一段不太短
        truncated = truncated[:last_para]
    elif limit > 500:
        # 回退到最后一个完整句子
        for sent_end in ['。\n', '.\n', '！\n', '?\n', '？\n']:
            last_sent = truncated.rfind(sent_end)
            if last_sent > limit * 0.5:
                truncated = truncated[:last_sent + 1]
                break

    removed = len(text) - len(truncated)
    truncated += f"\n\n[截断指示：已省略 {removed} 字符（{removed//4} tokens）。原始文件：{label}]"
    return truncated
```

---

### 3.3 Bug 3：Code Fence 嵌套冲突 → XML 标签分隔

**行业实践**：Anthropic 推荐使用 XML 标签包裹结构化内容——`<document>` 不会与 Markdown 冲突。

**当前格式**（有问题）：
```
### outline/volume_map.md
```
## 第一卷...
```
此处如果 volume_map 包含 ``` 会破坏外层
```

**修复后格式**：
```python
# dispatch_helper.py L241-243 替换为：

for fname, content in input_texts.items():
    # 使用 XML 标签替代 code fence——不会与文件内容冲突
    # 行业实践（Anthropic）：<document> 标签用于分隔多个文档
    safe_content = content.replace('</doc>', '<\\/doc>')  # 转义内部标签
    user_parts.append(f'<document name="{fname}">\n{safe_content}\n</document>')
```

**效果**：
- `</doc>` 不会出现在正常 Markdown 中，零冲突
- LLM 可清晰识别文档边界（Anthropic 微调数据大量使用此格式）
- 可在标签上附加元数据（token 数、截断状态）

---

### 3.4 架构缺陷 1：策展上下文仅 drafting 消费 → 审计器共享上下文缓存

**行业实践**：LangChain `BaseCache` 模式——多次调用共享相同底层数据时使用缓存层。

**具体修复**：

```python
# 新增：dispatch_helper.py

def _build_shared_audit_context(project_dir: Path, chapter: int) -> dict[str, str]:
    """构建审计器共享上下文缓存。

    行业实践（LangChain Cache）：多个 LLM 调用共享相同的基础文档时，
    只构建一次，后续调用复用缓存。

    返回按审计类型索引的上下文片段字典。
    """
    cache_key = f"audit_context_ch{chapter}"
    if cache_key in _AUDIT_CONTEXT_CACHE:
        return _AUDIT_CONTEXT_CACHE[cache_key]

    # 一次性加载所有审计器需要的共享文件
    chapter_text = (project_dir / 'chapters' / f'chapter-{chapter}.md').read_text()
    plan_text = (project_dir / 'plans' / f'chapter-{chapter}-plan.md').read_text()

    # 从策展上下文提取特定节（而非让每个审计器各自读取原始 truth）
    curated = _get_or_create_curated_context(project_dir, chapter)

    shared = {
        'chapter_full': chapter_text,
        'plan_full': plan_text,
        # 按审计类型分发策展上下文的特定节
        'world_rules_context': curated.get('P7', ''),
        'character_context': curated.get('P5', '') + '\n' + curated.get('P6', ''),
        'continuity_context': curated.get('P6', '') + '\n' + curated.get('P4', ''),
        'pacing_context': curated.get('P4', ''),
        'hook_context': curated.get('hook_debt_briefing', ''),
    }

    _AUDIT_CONTEXT_CACHE[cache_key] = shared
    return shared
```

**效果**：13 个审计器 × 73KB → 1 次加载 73KB + 13 × 3KB（审计特定指令）。节省 ~88% 审计上下文。

---

### 3.5 架构缺陷 2：review-world-rules 33K tokens → 确定性世界规则摘要

**行业实践**：LlamaIndex `SummaryIndex`——对大文档先生成摘要，LLM 调用时使用摘要而非全文。

**具体修复**：

```python
# 新增：src/shenbi/pipeline/world_summarizer.py

def summarize_world_files(project_dir: Path, max_chars: int = 2000) -> dict[str, str]:
    """确定性摘要世界文件——无需 LLM。

    行业实践：对大型参考文档在上下文注入前进行确定性压缩。
    保留规则名称和关键约束，丢弃示例和叙述性描述。
    """
    summaries = {}

    # power_system.md: 提取规则名称+关键数字
    ps_text = (project_dir / 'world' / 'power_system.md').read_text()
    rules = re.findall(r'(?:###|##)\s+(.+?)(?=\n(?:###|##)|\Z)', ps_text, re.DOTALL)
    ps_summary = '\n'.join(
        f"- {r.split(chr(10))[0].strip()}"
        for r in rules if len(r) > 20
    )[:max_chars]
    summaries['power_system'] = ps_summary

    # locations.md: 提取地点名称+关键特征
    loc_text = (project_dir / 'world' / 'locations.md').read_text()
    locations = re.findall(r'###\s+(.+?)(?=\n###|\Z)', loc_text, re.DOTALL)
    loc_summary = '\n'.join(
        f"- {l.split(chr(10))[0].strip()}: {l.split(chr(10))[1].strip() if len(l.split(chr(10))) > 1 else ''}"
        for l in locations
    )[:max_chars]
    summaries['locations'] = loc_summary

    return summaries
```

**效果**：review-world-rules 从 33K tokens → ~10K tokens（-70%），且保留所有规则名称供验证。

---

### 3.6 架构缺陷 3：仅 40% reads 有字段过滤 → 系统性声明所有大文件字段

**行业实践**：OpenAI 的 "needle-in-haystack" 问题——给 LLM 的长文档中，只有小部分是相关的。字段过滤（Layer B）是已实现的解决方案，但覆盖不完整。

**具体修复**：为所有大于 5KB 的 reads 声明字段过滤。

```yaml
# shenbi-chapter-planning SKILL.md contract 更新
contract:
  reads:
    - {file: outline/volume_map.md, fields: [当前卷Objective, 当前章节点, 跨卷桥接]}
    - {file: truth/current_state.md, fields: [主角状态, 当前世界局势]}
    - {file: truth/chapter_summaries.md, fields: [最近3章]}
    # ... 其他已有字段声明的保持不变

# shenbi-review-world-rules SKILL.md contract 更新
contract:
  reads:
    - {file: chapters/chapter-N.md, fields: [世界规则相关段落]}  # 新增过滤
    - {file: world/rules.md, fields: [世界铁律]}                  # 已有
    - {file: world/power_system.md, fields: [核心规则]}           # 新增！
    - {file: world/locations.md, fields: [本章涉及地点]}         # 新增！
```

**实现**：`filter_to_fields`（`fields.py:44-52`）已支持 H2 节提取——只需在合约中声明字段名。

---

### 3.7 架构缺陷 4：均权截断 → 优先级驱动的上下文预算

**行业实践**：Anthropic 的 "Context Window Budgeting"——将 tokens 分配给最重要的内容，而非均分。

**具体修复**：

```python
# dispatch_helper.py 替换 L163-192

# 文件优先级权重（基于行业实践：指令 > 核心内容 > 参考数据）
_FILE_PRIORITY_WEIGHTS = {
    'plan': 1.0,           # 章节计划——最高优先级
    'chapter': 0.9,        # 章节正文
    'volume_map': 0.8,     # 卷纲
    'story_frame': 0.7,    # 故事框架
    'current_state': 0.6,  # 当前状态
    'pending_hooks': 0.6,  # 伏笔
    'character': 0.5,      # 角色数据
    'style': 0.4,          # 风格
    'audit_drift': 0.4,    # 漂移
    'world': 0.3,          # 世界设定（参考）
    'default': 0.5,
}

def _get_file_priority(filename: str) -> float:
    for key, weight in _FILE_PRIORITY_WEIGHTS.items():
        if key in filename.lower():
            return weight
    return _FILE_PRIORITY_WEIGHTS['default']

def _budgeted_truncate(raw_inputs: dict[str, str], total_budget: int) -> dict[str, str]:
    """优先级驱动的上下文预算分配。

    行业实践（Anthropic）：给指令和核心内容分配更多 tokens，
    给参考数据分配更少。
    """
    # 计算权重
    weights = {f: _get_file_priority(f) for f in raw_inputs}
    total_weight = sum(weights.values())

    # 按权重分配预算
    result = {}
    for fname, text in raw_inputs.items():
        budget = int(total_budget * weights[fname] / total_weight)
        budget = max(budget, 500)  # 最小 500 字符
        budget = min(budget, _INPUT_MAX_CHARS_PER_FILE)
        result[fname] = _safe_truncate(text, budget, fname)

    return result
```

---

### 3.8 审计级联：前 N 个审计 PASS 后跳过其余

**行业实践**：Google "early exit" 模式——低成本分类器先运行，仅在其不确定时才调用高成本模型。

**具体修复**（`chapter_loop.py` 审计步骤）：

```python
# chapter_loop.py:_run_audits 中增加级联逻辑

CORE_AUDITS = ['continuity', 'character', 'world-rules', 'pacing']
CASCADABLE_AUDITS = ['dialogue', 'motivation', 'sensitivity', 'foreshadowing',
                     'pov', 'memo-compliance', 'anti-ai', 'texture', 'reader-pull']

def _should_skip_cascaded_audit(audit_type: str, core_results: dict) -> bool:
    """如果核心审计全部 PASS 且 confidence > 90%，跳过级联审计。

    行业实践：Google 'cascade evaluation'——低风险项跳过详细审查。
    """
    if audit_type not in CASCADABLE_AUDITS:
        return False

    core_pass = all(
        r.get('status') == 'PASS' and r.get('confidence', 0) > 0.9
        for r in core_results.values()
    )
    return core_pass
```

**注意**：resonance 和 memo-compliance 始终运行（评分需要）。

---

### 3.9 SKILL.md 冗余 → 共享引用提取

**行业实践**：DRY（Don't Repeat Yourself）——20 个审计 skill 中逐字重复的"四元素缺陷证据格式"是典型的跨文件代码重复。

**具体修复**：

1. **提取共享引用文件**：`skills/_shared/defect-evidence-format.md`
```markdown
## 缺陷证据格式（所有审计 skill 共用）

每个发现的缺陷必须包含以下四元素：

| 元素 | 格式 | 示例 |
|------|------|------|
| position | `chapter-N.md L45-52` | 文件:行号范围 |
| quote | `> 原文引用` | 至少 20 字的原文摘录 |
| rule | `G4.{check_id}` | 违反的规则编号 |
| severity | `BLOCKING\|CRITICAL\|WARNING` | 严重度 |
```

2. **在审计 skill 中引用而非重复**：
```markdown
## 缺陷证据格式
见 `skills/_shared/defect-evidence-format.md`（所有审计 skill 共用）
```

3. **同样提取**：
   - `skills/_shared/u-shaped-gap-explanation.md`（resonance + arc-payoff 共用）
   - `skills/_shared/pipeline-integration-mode.md`（drafting + context-composing 共用）
   - `skills/_shared/anti-rationalization-base.md`（所有 skill 的基础反合理化表 + skill 特定追加）

---

### 3.10 指令优先级：三级层次结构

**行业实践**：Anthropic "Primacy Effect"——LLM 对提示开头和结尾的内容注意力最高。

**当前**：所有输入文件在 `## Input Files` 区平等呈现。

**修复后**（`_build_skill_prompt` 用户 prompt 重构）：

```python
def _build_user_prompt_with_hierarchy(skill, inputs, output_paths, chapter):
    """按三级优先级构建用户 prompt。

    行业实践（Anthropic）：
    - HARD CONSTRAINTS 放在最前面（违反=重试）
    - GUIDELINES 放在中间（优先遵循）
    - REFERENCE 放在最后（仅供参考）
    """
    parts = []

    # L1: HARD CONSTRAINTS（最高优先级，违反触发 G4 重试）
    parts.append("## 🔴 HARD CONSTRAINTS — 违反将触发 G4 重试\n")
    if 'volume_map' in inputs:
        parts.append(f"- **卷纲对齐**：本章必须对齐 volume_map 中声明的章节点：{inputs['volume_node']}")
    parts.append(f"- **8 节完整性**：计划必须包含全部 8 节，每节标题精确匹配")
    parts.append(f"- **输出格式**：严格使用 `### FILE:` 标记，JSON 文件禁止尾部注释\n")

    # L2: GUIDELINES（优先遵循，轻微偏离可接受）
    parts.append("## 🟡 GUIDELINES — 优先遵循\n")
    parts.append(f"- 从 volume_map 跨卷桥接中选取本章应推进的钩子")
    parts.append(f"- Section 1 从卷纲 Key Result 推导章节目标")
    parts.append(f"- 转折词预算：≤ {transition_budget} 次\n")

    # L3: TASK
    parts.append(f"## 📋 TASK\n{prompt}\n")

    # L4: REFERENCE（仅供参考）
    if inputs:
        parts.append("## 🔵 REFERENCE — 仅供参考")
        for fname, content in inputs.items():
            parts.append(f'<document name="{fname}">\n{content}\n</document>')

    return '\n'.join(parts)
```

---

### 3.11 负面提示：每个 Skill 的 DO NOT 区块

**行业实践**：OpenAI "Negative Prompting"——明确告知模型"不要做什么"与"要做什么"同等重要。减少模型在错误方向上的概率质量。

**具体修复**：在每个 skill 的 SKILL.md 末尾追加标准化的 `## DO NOT` 块：

```markdown
## ⛔ DO NOT

### 通用禁止（所有 skill 共用）
- DO NOT 在 JSON 文件后追加 markdown 解释
- DO NOT 输出 `### FILE:` 标记之外的内容
- DO NOT 询问澄清问题或等待人类确认
- DO NOT 使用 "注意：" "提示：" 等元注释引导语

### 本 Skill 特定禁止
- Planning: DO NOT 规划与 volume_map 章节点矛盾的内容
- Drafting: DO NOT 连续 2 章使用相同开篇句式
- State-settling: DO NOT 覆盖整个 truth 文件——仅追加新章数据
- Revision: DO NOT 在 no-op 路由下覆盖章节正文
```

---

### 3.12 上下文新鲜度检查

**行业实践**：数据管道中的 "Data Freshness SLA"——在消费数据前验证其时效性。

**具体修复**（`dispatch_helper.py`）：

```python
def _validate_context_freshness(input_texts: dict[str, str], chapter: int, skill: str) -> list[str]:
    """检查输入上下文是否包含过期数据。

    行业实践（Data Freshness SLA）：
    - 累积型 truth 文件（resonance_trend, chapter_summaries）应包含当前章附近的数据
    - 如果仅包含 1-2 章的数据但当前在 10+ 章，标记为过期
    """
    warnings = []

    for fname, text in input_texts.items():
        if 'chapter_summaries' in fname or 'resonance_trend' in fname:
            ch_refs = len(set(re.findall(r'[Cc]h(?:apter)?[ .-]*(\d+)', text)))
            if ch_refs <= 2 and chapter > 5:
                warnings.append(
                    f"STALE: {fname} 仅引用 {ch_refs} 章，"
                    f"但当前在第 {chapter} 章。可能使用了过期数据。"
                    f"根因：state-settling 覆盖模式（Spec CN3）。"
                )

        if 'style_profile' in fname and 'bootstrap' in text.lower() and chapter > 3:
            warnings.append(
                f"STALE: style_profile 仍为 bootstrap 模式，"
                f"但已生成 {chapter} 章。根因：style-learning 未更新（Spec CN4）。"
            )

    if warnings:
        log.warning("context_freshness", skill=skill, chapter=chapter, warnings=warnings)

    return warnings
```

---

## 4. 汇总

### 4.1 优化效果预估

| 优化项 | 节省/章 | 类型 |
|--------|---------|------|
| 审计共享上下文缓存 | -84K tokens | 压缩 |
| volume_map 章节点提取 | -6K tokens | 压缩 |
| escalation-review 条件跳过 | -8K tokens | 压缩 |
| 审计级联（≥90% confidence 跳过） | -90K tokens | 压缩 |
| Truth 文件修复（转废为宝） | +16K → 有用 | 修复 |
| State-settling 上下文补充 | +7K tokens | 补充 |
| **净效果** | **-165K tokens/章（-40%）** | |

### 4.2 优化后每章上下文

| 指标 | 当前 | 优化后 |
|------|------|--------|
| LLM 调用次数 | 24 | 14-24（级联） |
| 总 tokens/章 | 408K | ~243K |
| 有效信息占比 | 62% | ~90% |
| 56 章总 tokens | 22.9M | ~13.6M |

### 4.3 新 Spec 关联

| 本 Spec 建议 | 关联已有 Spec |
|-------------|-------------|
| volume_map 章节点提取 | Spec Volume Map 消费 |
| Truth 文件修复 | CN3 |
| Review checklist 静态提取 | S2 |
| escalation-review 跳过 | CN5 |
| State-settling 上下文补充 | CN1, CN3 |
| Resonance 格式示例 | M5 |
| Audit 共享上下文 | **新建** |
| 审计级联跳过 | **新建** |
| 上下文分层架构 | **新建（架构改进）** |
| 指令优先级 | **新建（prompt 工程）** |

---

### 4.4 系统 Prompt 层面冗余（SKILL.md 审计发现）

Agent 对 32 个 SKILL.md 进行逐文件审计，发现 8 类跨 skill 的 prompt 冗余：

| # | 冗余模式 | 影响范围 | 浪费量 | 修复 |
|---|---------|---------|--------|------|
| 1 | **自动生成的数据契约块**（`## 数据契约`） | 32 skills | ~160-320 行 | 移除或折叠——与 frontmatter 重复 |
| 2 | **四元素缺陷证据格式**（position+quote+rule+severity） | 20 review skills | ~120 行逐字重复 | 提取为共享引用 `defect-evidence-format.md` |
| 3 | **U型缺口/负向门控解释** | resonance + arc-payoff | ~30 行重复 | 提取为共享架构文档 |
| 4 | **Pipeline 集成模式描述** | drafting + context-composing | ~16 行 | 提取为共享引用 |
| 5 | **State-settling 人工审批门禁模板** | 1 skill | 65 行→15 行 | 压缩为结构描述 |
| 6 | **Foreshadowing-resolve CP 公式** | 1 skill | 出现 2 次 | 去重 |
| 7 | **AUTO-CHECK 空块** | 32 skills | ~100 行 | 移除空注释块 |
| 8 | **Escalation-review 无反合理化表** | 1 skill | 安全缺口 | **补充**（唯一缺少此表的 skill） |

**额外发现：最大的两个系统 prompt**
- `shenbi-review-resonance`：~12,600 字符（第二冗长）
- `shenbi-review-arc-payoff`：~12,100 字符（最冗长）
- 两者各花 15-20 行解释同一架构概念——可提取共享文档节省 ~40 行

**Prompt 大小分布：**
| 大小范围 | Skills 数 | 代表 |
|---------|----------|------|
| < 3,000 字符 | 4 | escalation-review(1,000), foreshadowing-recall(1,800) |
| 3,000-6,000 | 20 | 大部分审计 skills |
| 6,000-10,000 | 5 | chapter-planning, state-settling, chapter-revision |
| > 10,000 | 2 | resonance(12,600), arc-payoff(12,100) |

### 4.5 代码层 Bug 和架构缺陷（dispatch_helper 审计发现）

Agent 对 `dispatch_helper.py` 的逐行审计发现 **3 个 bug** 和 **4 个架构缺陷**：

#### Bug 1: Glob 模式从未展开（静默数据丢失）🔴

多个 SKILL.md 合约声明了 glob 读取：
```yaml
reads:
  - chapters/*.md           # review-long-span, review-arc-payoff
  - characters/major/*.md   # review-character, review-dialogue, review-motivation
```

但 `_build_skill_prompt` 的 L146 行 `full_path = project_dir / resolved` 将字面量 `*` 传给 `Path.exists()`——返回 False。结果是 `[file not found: chapters/*.md]`。

**影响**：
- `review-long-span` 无法做跨章 n-gram 分析（其核心功能）
- 角色审查 skills 看不到 major/ 目录下的配角档案
- **静默失败——无日志、无告警、LLM 收到占位符文本但不知道这是错误**

#### Bug 2: 截断破坏 UTF-8 多字节字符

L169 行 `text[:limit]` 在任意字节偏移处切割——中文字符 3 字节，切割可能在字符中间，产生损坏的尾部字节。

#### Bug 3: Code fence 嵌套冲突

L243 行用 ```` ``` ```` 包裹输入文件内容。如果文件本身包含 ```` ``` ````（如 META 块中的代码示例），内部 fence 会提前关闭外部包裹——LLM 解析混乱。

#### 架构缺陷 1: 策展上下文仅被 drafting 消费

`context_assemble.py` + `context_curation.py` 每章生成高质量的 9 节策展上下文（~12K chars），但 **13 个审计 skills 都不读取它**。它们各自独立重新读取原始 truth 文件。如果审计 skills 读取 `context/chapter-N-context.md` 的对应节（如 P7 世界铁律），可消除跨审计器的重复 truth 文件读取。

#### 架构缺陷 2: review-world-rules 单次调用 33K tokens

读取 7 个文件（chapter + rules + power_system + locations + bible + summaries + current_state），总计 ~115K 字符。是所有 LLM 调用中最大的。`world/power_system.md`（28.8K）和 `world/locations.md`（24.9K）未被摘要就被全量发送。

#### 架构缺陷 3: 仅 40% 的 reads 声明了字段过滤

最大的文件最需要字段过滤，但恰恰缺少：
- `chapters/chapter-N.md`（31K+）— 从未字段过滤
- `world/power_system.md`（28.8K）— 从未字段过滤
- `outline/volume_map.md`（26.3K）— 从未字段过滤

#### 架构缺陷 4: 截断是均权而非优先级驱动

当总输入超过 128K 时，每个文件获得均等预算——500 字节的 audit_drift 和 30K 字节的 chapter 获得相同切片。应该基于文件类型分配权重。

---

## 5. 验证标准

1. 每章总 token 消耗降低 ≥ 30%
2. 审计共享上下文缓存实现后，13 个审计器不再各自读取章节全文
3. 无 escalation 时 escalation-review 不产生 LLM 调用
4. State-settling 在补充上下文后产出正确的追加（而非覆盖）
5. `just check` 全量通过
