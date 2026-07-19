# 修复 Style Learning 从未更新 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:** Spec CN3（Truth 文件覆盖模式）— 需要历史 resonance 数据
> **目的:** 修复 `style_profile.md` 在 56 章生成后仍为 bootstrap 模式（confidence: low, 样本章节数: 0）的缺陷。

---

## 1. 背景

### 1.1 发现（D12）

`style/style_profile.md` 状态：
- **生成方式**: 种子指纹（bootstrap）
- **confidence**: low
- **样本章节数**: 0
- **样本总字数**: 0
- **所有统计值**: "推测值"
- 首次正式提取应在**前 3 章完成后**触发 —— 从未触发
- 定期更新（每 12 章）—— 从未触发

### 1.2 影响

- 风格漂移检测（Spec C2）失去 baseline 参考
- 审计系统无法对比实际风格与期望风格
- 56 章的风格演变完全未被追踪
- 这是 C2（文风崩塌）未被检测到的**关键根因之一**

---

## 2. 根因分析

`chapter_loop.py` 中 style-learning 的触发逻辑可能：
1. 未被包含在 CHAPTER_STEPS 中
2. 条件触发（`_should_run_step`）的条件从未满足
3. 或被 `shenbi-context-composing` 替换后未保留

需要代码核实：`chapter_loop.py` 中是否有 `shenbi-style-learning` 步骤。

---

## 3. 修复方案

### 3.1 强制触发

在 chapter loop 中增加显式的 style-learning 触发点：
- Chapter 3 完成后（首次正式提取）
- 每 12 章（`style_learning_interval`）
- Volume boundary 时

```python
# chapter_loop.py: _complete_chapter 中增加
if chapter == 3 or chapter % config.style_learning_interval == 0:
    _run_style_learning(project_dir, state)
```

### 3.2 启动时自愈

pipeline resume 时，如果 style_profile 仍为 bootstrap（`confidence: low` + `样本章节数: 0`）且已有 ≥ 3 章完成，自动触发 style-learning。

---

## 4. 验证标准

1. 运行 4 章 → style_profile.md 非 bootstrap（confidence ≥ medium, 样本章节数 ≥ 3）
2. 运行 13 章 → style_profile.md 更新两次（Ch3 后 + Ch12 后）
3. `just check` 全量通过

---

## 5. 依赖

```
Spec CN3（Truth 文件追加） ← 需要历史数据
  ↓
本 Spec
```
