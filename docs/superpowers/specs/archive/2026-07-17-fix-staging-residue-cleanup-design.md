# 修复暂存文件泄漏 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** 无
> **目的:** 修复 pipeline 运行后 119 个 staging 文件未被清理的缺陷——确保 `--auto` 模式在 commit 后调用 `clear_staging()`。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

`novel-output/xinghuo-ranqiong/staging/` 含 119 个遗留文件：

| 目录 | 文件数 | 大小 |
|------|--------|------|
| `staging/plans/` | 111（56 .md + 55 .json） | ~1.2MB |
| `staging/truth/` | 8（state-settling 中间态） | ~45KB |

**所有 56 章均有对应的 final plans 文件**，staging 中的是重复副本。

### 1.2 设计预期

`checkpoint.py` 定义了完整的 staging 生命周期：
- `commit_staging()`（line 32-56）：将 staging 文件复制到最终路径
- `clear_staging()`（line 59-73）：`shutil.rmtree` 删除整个 staging 目录

预期流程：
```
dispatch skill → 写入 staging/ → G4 验证 → commit_staging → clear_staging
```

---

## 2. 根因分析

### 2.1 auto 模式未清理

`chapter_loop.py:516-545`（`_advance` 中的 auto 模式）：

```python
# Auto mode: commit staging without human checkpoint
if step.uses_staging:
    commit_staging(project_dir, step)
    # ❌ 缺少：clear_staging(project_dir)
```

`commit_staging` 复制文件后，staging 目录应该被清理，但代码中缺少 `clear_staging()` 调用。

### 2.2 人工审批路径正常

`cli.py:317-351`（`_commit_staging_for_checkpoint`）：
```python
commit_staging(project_dir, pending_checkpoint)
clear_staging(project_dir)  # ✅ 正确清理
```

人工审批路径正确调用了 `clear_staging()`。

### 2.3 state-settling 的 auto-commit 同样缺失

`chapter_loop.py:537`（auto-commit state-settling）：
```python
commit_staging(project_dir, step)
# ❌ 同样缺少 clear_staging()
```

---

## 3. 修复方案

### 3.1 修复点

两处 auto-commit 后增加 `clear_staging()`：

**修复点 1**：`chapter_loop.py:516-545`（`_advance` auto mode for chapter-planning）

```python
if step.uses_staging and not requires_checkpoint:
    commit_staging(project_dir, step)
    clear_staging(project_dir)  # 新增
```

**修复点 2**：`chapter_loop.py:537`（auto-commit state-settling）

```python
commit_staging(project_dir, step)
clear_staging(project_dir)  # 新增
```

### 3.2 启动时残留清理（防御层）

在 `pipeline resume` 入口处增加残留清理：

```python
# cli.py 或 chapter_loop.py 的 resume 入口
staging_dir = project_dir / "staging"
if staging_dir.exists():
    # 如果 pipeline 状态显示没有 pending staging 步骤，安全清理
    if not _has_pending_staging_step(state):
        clear_staging(project_dir)
        logger.info("cleaned_staging_residue", project_dir=str(project_dir))
```

### 3.3 `clear_staging` 安全加固

`checkpoint.py:59-73` 的 `clear_staging` 增加存在性检查（当前 `shutil.rmtree` 对不存在的目录会抛异常）：

```python
def clear_staging(project_dir: Path) -> None:
    staging = staging_dir(project_dir)
    if staging.exists():
        shutil.rmtree(staging)
```

---

## 4. 验证标准

1. **单元测试**：`tests/unit/pipeline/test_staging_commit.py`（已有，需扩展）
   - auto-commit 后断言 `staging/` 目录不存在
   - reject 路径断言 staging 被清理且文件未写入 final

2. **集成测试**：运行 mini-pipeline，验证 staging 目录始终为空（除进行中的步骤外）

3. **回归检查**：`just check` 全量通过

---

## 5. 依赖关系

```
无前置依赖（独立修复，2 行代码变更）
```
