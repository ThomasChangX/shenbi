# 修复上下文组装持久化缺口 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:**
> - Spec C2（文风漂移）— 共享根因
> **目的:** 修复 43/56 章（77%）缺失 `context/chapter-N-context.md` 的缺陷，恢复 L3 层记忆。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

context 文件覆盖情况：

- **有 context 的章节**：Ch1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 55, 56（13 章）
- **缺失 context 的章节**：Ch2, 13-54（43 章，77%）
- **缺失模式**：Ch1-12 基本完整（仅 Ch2 缺失），Ch13-54 全部缺失，Ch55-56 恢复

### 1.2 与文风崩塌的关联

Ch13 恰是 context 开始缺失的起点，而 Ch30 是系统术语密度开始显著上升的转折点。延迟效应（17 章）符合预期：LLM 上下文窗口逐渐失去叙事锚点，参数化语言逐步替代自然散文。

### 1.3 当前上下文生成机制

`chapter_loop.py:128-133`（step 4）：
```python
# Step 4: Context assembly + curation
if step.calls_context_assembly:
    _run_context_assembly(project_dir, state, round_dir)
    _run_context_curation(project_dir, state)
```

`context_assemble.py:209-269`（`assemble_context`）：
- Route A（entity index）+ Route B（embedding search）+ Route C（fixed rules）
- 结果写入 `context/chapter-N-context.md`（line 269）

`context_curation.py:81-115`（`curate_context`）：
- P1-P7 优先级重排 + ending diversity check + hook debt briefing
- 产出 9-section 文档

---

## 2. 根因分析

### 2.1 为什么 Ch13-54 缺失

需要核实 `_run_context_assembly` 的实际行为。可能原因：

1. **Step 4 被跳过**：`calls_context_assembly` 标记在某些条件下为 False
2. **写入路径问题**：`assemble_context` 返回了数据但未写入磁盘
3. **文件被覆盖**：后续步骤覆盖了 context 文件
4. **条件触发**：context assembly 可能仅在特定条件下触发（如 volume boundary）

### 2.2 需要代码核实的关键点

- `CHAPTER_STEPS` 中 step 4 的 `calls_context_assembly` 是否为 True
- `_run_context_assembly` 是否在所有分支都调用了 `assemble_context`
- `assemble_context` 的 `safe_write` 调用是否在正常路径上

---

## 3. 修复方案

### 3.1 强制持久化

在 `chapter_loop.py` 的 `_run_context_assembly` 函数中，确保无论何种路径都调用 `assemble_context` 并验证输出文件存在：

```python
def _run_context_assembly(project_dir: Path, state: PipelineState, round_dir: Path) -> None:
    """运行上下文组装，必须产生 context/chapter-N-context.md。"""
    from shenbi.pipeline.context_assemble import assemble_context
    from shenbi.pipeline.context_curation import curate_context

    chapter = state.chapter_loop.current_chapter

    # 1. 确定性上下文检索
    assemble_context(project_dir, chapter)

    # 2. 确定性策展
    curate_context(project_dir, chapter)

    # 3. 强制验证：输出文件必须存在
    context_path = project_dir / "context" / f"chapter-{chapter}-context.md"
    if not context_path.exists():
        logger.error("context_assembly_no_output", chapter=chapter)
        # 回退：写入最小 context（仅 Route C 固定规则）
        _write_minimal_context(project_dir, chapter)
```

### 3.2 启动时覆盖审计

在 `pipeline resume` 的初始化阶段，增加 context 覆盖检查：

```python
def _audit_context_coverage(project_dir: Path, state: PipelineState) -> dict:
    """检查已生成章节的 context 文件覆盖。"""
    missing = []
    for ch in range(1, state.chapter_loop.current_chapter):
        ctx_path = project_dir / "context" / f"chapter-{ch}-context.md"
        if not ctx_path.exists():
            missing.append(ch)

    if missing:
        logger.warning("context_coverage_gap", missing_chapters=missing,
                       gap_ratio=f"{len(missing)}/{state.chapter_loop.current_chapter - 1}")

    return {"missing": missing, "total": state.chapter_loop.current_chapter - 1}
```

### 3.3 回填策略

对于已缺失 context 的章节（如 Ch13-54），提供回填命令：

```bash
uv run pipeline backfill-context <project_dir> --chapters 13-54
```

回填逻辑：对每个缺失章节，运行 `assemble_context` + `curate_context`（这些是确定性函数，可重复执行）。

---

## 4. 验证标准

1. **单元测试**：`tests/unit/pipeline/test_context_assembly.py`
   - 模拟 `assemble_context` → 断言 `context/chapter-N-context.md` 存在
   - 模拟 `_audit_context_coverage` → 正确报告缺失章节

2. **集成测试**：运行 3 章 mini-pipeline，验证每章均有 context 文件

3. **回归检查**：`just check` 全量通过

---

## 5. 依赖关系

```
无前置依赖（独立修复）
  ↓
下游：Spec C2（文风漂移）受益于 L3 恢复
```
