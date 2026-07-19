# 修复文风渐进式崩塌 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:**
> - `docs/superpowers/specs/2026-07-16-pipeline-maturity-and-bp-fixes-design.md`
> - Spec H3（上下文组装持久化缺口）— 共享根因
> **目的:** 阻止长篇生成中小说散文从自然叙事退化为系统规格枚举，恢复 Ch30-56 的文学可读性。

---

## 1. 背景

### 1.1 发现（2026-07-17 流水线审计）

对 56 章产出进行系统术语密度分析，发现从第 30 章起，小说散文发生渐进式退化：

| 阶段 | 章节 | 系统术语密度（‰） | "冷"出现次数 | "在场于"出现次数 | 叙述特征 |
|------|------|-------------------|-------------|-----------------|---------|
| **正常叙事** | Ch1-15 | 0-5.5 | 0-3 | 0 | 自然中文散文 |
| **初期退化** | Ch25-29 | 5.3-11.7 | 2-33 | 0 | 出现参数化句式 |
| **中期退化** | Ch30-35 | 9.6-28.6 | 54-197 | 0 | "——"枚举链 |
| **严重退化** | Ch40-45 | 33.6-74.8 | 33+ | 100+ | 系统规格文体 |
| **极重退化** | Ch46-56 | 74.8-135.8 | 114+ | 405+ | 不可读的枚举 |

退化后的典型文本（Ch50）：
> "冷知道自己在周二——冷知道周二在周一之后——冷知道周二在第二周——冷知道周一在周日之后——冷知道周日——冷知道周日不在——冷在场于周二——"

正常时期的对比文本（Ch1）：
> "他把铜线缠成圈塞进布袋。布袋里已经装了几块碎黄铜和一小截铅管，加起来不到两斤。"

### 1.2 影响范围

- 27/56 章（48%）出现不同程度退化
- Ch40 起（17 章，30%）实质上不可作为文学作品交付
- 退化是**单调递增**的：密度从 Ch30 的 9.6‰ 一路攀升至 Ch53 的 135.8‰

---

## 2. 根因分析

### 2.1 现有漂移检测为何未触发

`shenbi-drift-guidance` 使用三种触发条件（`src/shenbi/skill_utils/drift_detection/compute_drift.py:86-146`）：

1. **单调下降**（line 86-107）：连续 3+ 章 resonance 累计下降 ≥3 分
2. **低于均值-2σ**（line 109-133）：连续 2+ 章低于均值-2σ
3. **卷级下降**（line 136-146）：连续 2 卷得分下降

**这些检测全部基于 resonance 评分**。问题在于：resonance 评分由 LLM（`shenbi-review-resonance`）执行，而 **LLM 自身也受到文风漂移影响**——当整个上下文窗口被系统参数语言污染后，resonance 评分器对退化文本"习以为常"，评分不发生显著下降。

### 2.2 缺失的检测维度

当前 `compute_drift.py` **仅分析评分趋势**，不分析文本本身的语言特征：

- ❌ 系统术语密度（"参数"、"在场于"、"格式串"、"槽位"、"帧序列"等）
- ❌ 破折号密度（退化文本大量使用"——"作为枚举分隔符）
- ❌ 句号链密度（极短句连续堆叠：`<10字。` × N）
- ❌ "冷在"句式密度（已成为退化指纹）
- ❌ 标准叙事标点比例（对话引号"“"、逗号"，"等）

### 2.3 上下文压缩缺失的放大效应

Spec H3 发现 43/56 章缺失 `context/chapter-N-context.md`。L3 层的缺失意味着：

- 后续章节的 LLM 调用缺少前文叙事摘要
- LLM 只能看到最近的 chapter memo（参数化规划语言）+ 当前规划
- **形成自反馈回路**：参数化规划 → 参数化散文 → 参数化 resonance 评分 → 无告警 → 继续参数化

### 2.4 根因总结

```
L3 context 缺失（H3）
  → LLM 看到的是系统参数而非叙事散文
    → 散文退化为参数枚举
      → resonance 评分器也被污染
        → drift_detection 基于评分未触发
          → 无干预 → 持续退化
```

**直接原因**：drift_detection 缺少文本语言学指标。

**系统原因**：context 压缩缺失切断了叙事锚点。

---

## 3. 修复方案

### 3.1 方案：增加文本语言学漂移指标

**不替代现有 resonance 评分检测，而是增加独立的文本层检测。**

#### 3.1.1 新增检测器：`drift_detection/linguistic_drift.py`

```python
# 新增文件：src/shenbi/skill_utils/drift_detection/linguistic_drift.py

def compute_linguistic_drift(chapter_text: str, baseline: dict) -> dict:
    """计算章节文本的语言学漂移指标。

    返回与 baseline 的偏差百分比。
    """
    metrics = {}

    # 1. 系统术语密度
    SYSTEM_TERMS = re.compile(
        r'(参数|系统|格式串|历法|槽位|帧序列|阈值|在场于|'
        r'知道.{0,10}在|Phase\s+\d|MH-\d+|P[012]\.\d+)'
    )
    metrics['system_term_density'] = len(SYSTEM_TERMS.findall(chapter_text)) / len(chapter_text) * 1000

    # 2. 破折号密度（枚举分隔符）
    metrics['em_dash_density'] = chapter_text.count('——') / max(len(chapter_text), 1) * 1000

    # 3. 短句链密度（连续5+个 ≤15字句子）
    short_sents = re.findall(r'(?:[^。]{1,15}。){5,}', chapter_text)
    metrics['short_sentence_chain_density'] = sum(len(s) for s in short_sents) / max(len(chapter_text), 1) * 1000

    # 4. "冷在"句式密度
    metrics['leng_zai_density'] = chapter_text.count('冷在') / max(len(chapter_text), 1) * 1000

    # 5. 对话密度（" 出现次数 / 总字数）
    metrics['dialogue_density'] = chapter_text.count('"') / max(len(chapter_text), 1) * 1000

    # 计算与 baseline 的偏差
    deviations = {}
    for key, value in metrics.items():
        if key in baseline and baseline[key] > 0:
            deviations[key] = abs(value - baseline[key]) / baseline[key]

    return {
        'metrics': metrics,
        'deviations': deviations,
        'max_deviation': max(deviations.values()) if deviations else 0.0,
    }
```

#### 3.1.2 集成到 drift_detection 触发条件

在 `compute_drift.py` 中增加第四种触发条件：

```python
# compute_drift.py 新增（约 line 147 后）

def check_linguistic_drift_trigger(chapter_text: str, baseline_metrics: dict) -> bool:
    """检查语言学漂移是否触发告警。

    触发阈值：任一指标偏离 baseline 超过 500%。
    """
    result = compute_linguistic_drift(chapter_text, baseline_metrics)
    return result['max_deviation'] > 5.0  # 500% deviation
```

#### 3.1.3 baseline 建立

在 `shenbi-style-learning` 的 `compute_stats.py` 中增加 linguistic baseline 提取——从 bootstrap 或前 3 章的正常散文中计算术语密度、破折号密度等基线。

#### 3.1.4 干预策略

当语言学漂移触发时（建议在 `chapter_loop.py` 的 `_should_run_step` 中，`shenbi-drift-guidance` 触发前增加检查）：

1. **WARN 级别**（density 30-50‰）：在下一章的 `PRE_WRITE_CHECK` 中注入"避免参数化语言"提醒
2. **HARD 级别**（density > 50‰）：强制触发 `shenbi-drift-guidance`，在 audit_drift.md 中写入具体纠正指令
3. **ESCALATE 级别**（density > 100‰）：触发人类审查 checkpoint，暂停自动生成

### 3.2 与 Spec H3 的协同

Spec H3（上下文组装持久化）恢复后，每章将有 L3 压缩上下文可用。届时：
- Chapter planning 的 prompt 应包含"前一章叙事风格摘要"（从 L3 context 提取）
- 风格漂移应从 **上下文源头** 被阻断

---

## 4. 验证标准

1. **检测器单元测试**：`tests/unit/skill_utils/test_linguistic_drift.py`
   - 正常散文（Ch1 excerpt）→ max_deviation < 1.0
   - 退化散文（Ch50 excerpt）→ max_deviation > 5.0，system_term_density > 50‰
   - baseline 正确从正常散文计算

2. **集成测试**：在已有的正常章节 + 人工退化章节上运行 `compute_drift.py`，确认新条件触发

3. **端到端验证**：用修复后的 pipeline 生成 10+ 章，监控系统术语密度趋势，确认不再单调上升

4. **回归检查**：`just check` 全量通过

---

## 5. 依赖关系

```
Spec H3（context 持久化） ← 共享根因，但本 spec 可独立实施
  ↓
本 Spec（语言学漂移检测）
  ↓
无下游硬依赖
```

---

## 6. 风险与权衡

| 风险 | 缓解 |
|------|------|
| 术语列表不完整，未覆盖未来新的退化模式 | 设计为可扩展的 pattern 列表；增加 "未知高频词" 通用检测 |
| 某些文学风格天然高密度使用特定修辞（如重复） | baseline 从**本作品**的正常章节提取，而非外部标准 |
| 过早触发误报，打断合法风格探索 | WARN/HARD/ESCALATE 三级渐进；仅在连续 3 章触发后才 HARD-block |
