# 修复章节被修订元输出覆盖 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:**
> - `docs/superpowers/specs/2026-07-16-pipeline-maturity-and-bp-fixes-design.md`（P0 阻断修复已落地）
> **目的:** 修复 `shenbi-chapter-revision` 在 no-op/auto-skip 路由下将修订元摘要写入 `chapters/chapter-N.md` 导致小说正文永久丢失的缺陷。

---

## 1. 背景

### 1.1 发现（2026-07-17 流水线审计）

对 `novel-output/xinghuo-ranqiong/` 的 56 章产出进行逐文件内容审计，发现 5 章（8.9%）的 `chapters/chapter-N.md` 不包含小说正文，而是包含修订元输出：

| 章节 | 文件大小 | 内容类型 | Snapshot 状态 |
|------|---------|---------|---------------|
| Ch2 | 916 bytes | "All three files have been output. Here's a summary of the revision..." | 无 snapshot |
| Ch9 | 367 bytes | "第9章修订结论: Auto-skip（无修订）" | 同样被污染 |
| Ch12 | 1,340 bytes | "The revision is complete. Here's a summary..." | 同样被污染 |
| Ch44 | 1,199 bytes | "All three output files have been produced..." | 同样被污染 |
| Ch55 | 101 bytes | "Chapter content unchanged — no revision needed." | 同样被污染 |

**关键事实：**
- Ch2 无 snapshot → 正文**永久丢失**
- Ch9/12/44/55 的 snapshot 同样包含修订元文本 → snapshot 恢复路径也无效
- 所有 5 章的 `chapter-N-decisions.json` 有完整的元数据，但正文不可恢复

### 1.2 影响范围

- 5/56 章（8.9%）的小说正文丢失
- 修订系统在 34/56 章被触发，其中 5 次（14.7%）导致了内容覆盖
- 丢失模式集中在 "auto-skip" 和 "no-op" 路由

---

## 2. 根因分析

### 2.1 修订路由逻辑

`shenbi-chapter-revision` 的 SKILL.md（`skills/shenbi-chapter-revision/SKILL.md:105-108`）定义两种输出模式：

```markdown
- **spot-fix mode:** Output PATCHES format
- **rewrite/rework mode:** Output complete revised body text
```

但存在第三种隐含路由：**no-op/auto-skip**——当审计发现无阻塞问题时，修订 skill 判定无需修改，此时 LLM 的"自然行为"是输出一个摘要说明而非保留原始正文。

### 2.2 写入路径

`dispatch_helper.py:294-323`（`_write_parsed_outputs`）解析 `### FILE: path/to/file.md` 标记，**无条件覆盖**目标路径：

```python
# dispatch_helper.py:316
safe_write(Path(path), content)
```

对于修订 skill，`writes` 合约包含 `chapters/chapter-N.md`（`dispatch_helper.py:195-203`），因此当 LLM 输出摘要到 `### FILE: chapters/chapter-N.md` 时，原文即被覆盖。

### 2.3 为什么修订前内容未保留

1. **无 pre-revision snapshot**：`state_snapshot-pre-rev.md` 仅在 revision 开始时写入 `truth/`（`SKILL.md:63`），但不备份 `chapters/chapter-N.md`
2. **chapter loop 无内容守卫**：`chapter_loop.py:1427-1438` 的 `_route_revision_after_resonance` 直接调度 revision，无覆盖前的内容保存
3. **snapshot 时机错误**：快照在 step 19（audit 完成后）而非 step 18（revision 前）生成（`chapter_loop.py:242-247`）

### 2.4 根因总结

```
shenbi-chapter-revision 的 no-op 路由
  → LLM 输出摘要到 ### FILE: chapters/chapter-N.md
    → _write_parsed_outputs 无条件覆盖
      → 原文永久丢失
```

**直接原因**：revision skill 的写入合约将 `chapters/chapter-N.md` 标记为输出文件，但 no-op 场景下不应写入。

**系统原因**：缺少修订前的文件内容快照机制。

---

## 3. 修复方案

### 3.1 方案 A：修订前自动快照（推荐）

**步骤：**

1. **`chapter_loop.py` step 18 前增加 pre-revision backup**

   在 `_route_revision_after_resonance`（`chapter_loop.py:1427` 附近）调度 revision 前，将 `chapters/chapter-N.md` 复制到 `chapters/chapter-N-pre-rev.md`：

   ```python
   # 新增：修订前备份原章节
   import shutil
   chapter_path = project_dir / f"chapters/chapter-{state.current_chapter}.md"
   backup_path = project_dir / f"chapters/chapter-{state.current_chapter}-pre-rev.md"
   if chapter_path.exists():
       shutil.copy2(chapter_path, backup_path)
   ```

2. **`dispatch_helper.py` 增加内容大小守卫**

   在 `_write_parsed_outputs`（`dispatch_helper.py:316` 附近）增加对章节文件的检查：

   ```python
   # 如果写入的章节内容明显小于原文件（< 原文件 20%），拒绝覆盖
   if path.match("chapters/chapter-*.md") and not path.match("*-pre-rev.md"):
       if Path(path).exists():
           original_size = Path(path).stat().st_size
           if len(content) < original_size * 0.2:
               logger.warning("revision_content_too_small", path=str(path),
                              original=original_size, new=len(content))
               # 不覆盖，保留原文件
               continue
   ```

3. **`shenbi-chapter-revision` SKILL.md 强化 no-op 指令**

   在 `SKILL.md:105-108` 增加显式的 no-op 输出指令：

   ```markdown
   - **no-op/auto-skip 模式（新增）:** 当判定无需修订时，
     章节正文文件 `chapters/chapter-N.md` **不得输出**（不写入该文件）。
     仅输出 `chapters/chapter-N-revision-decisions.json`，
     其中 `route: "no_op"`, `changes: []`, `rationale: "<跳过原因>"`。
   ```

### 3.2 方案 B：修订输出分离（备选，更大改动）

将 revision 的输出路径改为 `staging/chapters/chapter-N-revised.md`，经 G4 验证通过后才由代码 commit 到最终路径。此方案改动较大（需改 `uses_staging` 标记、checkpoint 逻辑），作为后续优化。

### 3.3 推荐方案

**方案 A**，理由：
- 最小改动（3 处代码 + 1 处 SKILL.md）
- 防御深度：pre-rev backup + content size guard + SKILL.md 指令
- 不改变现有 staging/checkpoint 架构

---

## 4. 验证标准

1. **单元测试**：`tests/unit/pipeline/test_revision_safety.py`（新增）
   - 模拟 revision dispatch 输出 200 字符摘要到 `chapters/chapter-N.md`，原文件 8000 字符 → 断言原文件未被覆盖
   - 模拟 pre-rev backup 生成 → 断言 `chapter-N-pre-rev.md` 存在且内容与原文件一致

2. **集成测试**：用已知好章节运行 revision skill，确认 no-op 路由后原文不变

3. **金丝雀验证**：修改后对已损坏的 Ch2/9/12/44/55 场景模拟重跑，确认不再发生覆盖

4. **回归检查**：`just check` 全量通过

---

## 5. 依赖关系

```
无前置依赖（独立修复）
  ↓
完成后可并行推进 C3（META块）、H2（修订系统）
```

## 6. 风险与权衡

| 风险 | 缓解 |
|------|------|
| Content size guard 可能误拦合法的精简重写（rewrite 模式输出更短正文） | 阈值设置为原文件 20%，且仅 WARN 不 HARD-block；rewrite 模式通过 SKILL.md 指令区分 |
| Pre-rev backup 增加磁盘占用 | 每章 ~10-40KB，56 章约 ~2MB；下一个 spec 可增加清理策略 |
