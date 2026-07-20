# 修复修订系统全面失效 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:**
> - Spec H1（decisions.json 格式修复）— JSON 验证修复后修订文件才能通过 G4
> - Spec C1（修订覆盖章节正文）— 共享修订 skill 修复
> **目的:** 修复 34 个 `chapter-N-revision-decisions.json` 全部无效（10 个 JSON 语法错误 + 24 个零变更记录）的缺陷。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

对 34 个修订文件逐一检查：

| 类型 | 数量 | 占比 | 示例 |
|------|------|------|------|
| JSON 语法错误 | 10 | 29.4% | Ch2: 空文件; Ch15: 非法逗号; Ch18: 控制字符 |
| 零变更记录 | 24 | 70.6% | `changes: []` 或缺少 changes 字段 |
| **有效修订** | **0** | **0%** | — |

**结论：修订系统运行了 34 次，产出 0 次有效修改。**

### 1.2 重试循环证据

Pipeline 记录了 54 条 retry_feedback，其中 35 条（65%）来自 `shenbi-review-resonance` 的 G4 失败。resonance 失败触发 revision → revision 产出无效文件 → G4 再次失败 → 再次重试 → 循环。

### 1.3 影响

- 所有审计发现的问题从未被实际修复
- 34 次 revision dispatch 的 token 消耗完全浪费
- Spec C2（文风漂移）本应在早期通过 revision 纠正，但因修订系统失效而持续恶化

---

## 2. 根因分析

### 2.1 G4 对 revision 的覆盖缺失

`gates/g4/generic.py:237`：
```python
"shenbi-chapter-revision": g4_decisions,
```

revision skill 的 G4 路由**仅运行 `g4_decisions`**（JSON 验证），不使用 `make_composite_checker`。这意味着：

- ❌ 不检查 revision 是否包含实际变更
- ❌ 不检查 `changes` 字段是否非空
- ❌ 不验证 "retention verification" 块（`SKILL.md:63-64` 要求）

当 `g4_decisions` 遇到 JSON 语法错误时**应该失败**，但有 10 个语法错误文件通过了流水线——进一步证实 Spec H1 的发现：G4 在自动模式中可能未被严格执行。

### 2.2 SKILL.md 缺少 no-op 变更描述要求

`shenbi-chapter-revision` SKILL.md 定义了 spot-fix 和 rewrite 两种模式（`:105-108`），但：
- 没有定义 no-op 模式的标准输出格式
- 没有要求 "如果 auto-skip，changes 必须为空但 rationale 必须解释原因"

导致 LLM 在判定"无需修改"时随意输出。

### 2.3 修订路由逻辑缺陷

`chapter_loop.py:1427-1438`（`_route_revision_after_resonance`）根据 resonance 评分决定 revision route。但：
- Route C（hard binary check）中 "未达成" 触发 regeneration，但 regeneration 可能再次判定 no-op
- Route B（spot-fix）触发时，LLM 可能找不到具体修改点

---

## 3. 修复方案

### 3.1 G4 revision checker 升级

创建 `gates/g4/chapter_revision.py`：

```python
def g4_chapter_revision(files: list[Path]) -> list[str]:
    """专门的 revision 输出检查器。"""
    issues = []
    for f in files:
        if f.suffix != '.json':
            continue
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError:
            issues.append(f"G4.rev.invalid_json:{f.name}")
            continue

        # HARD: 必须有 changes 字段
        changes = data.get('changes', data.get('revisions', []))
        if not changes:
            # 允许空 changes 但要求明确的 skip rationale
            route = data.get('route', data.get('mode', ''))
            rationale = data.get('rationale', data.get('skip_reason', ''))
            if route not in ('no_op', 'auto_skip', 'skip') or len(str(rationale)) < 50:
                issues.append(f"G4.rev.empty_changes_no_rationale:{f.name}")

        # HARD: 如果有 changes，每个 change 必须有 description 或 reason
        if isinstance(changes, list) and len(changes) > 0:
            for i, change in enumerate(changes):
                if isinstance(change, dict):
                    desc = change.get('description', change.get('reason', change.get('change', '')))
                    if len(str(desc)) < 20:
                        issues.append(f"G4.rev.change_{i}_no_detail:{f.name}")

    return issues
```

### 3.2 SKILL.md 更新

在 `skills/shenbi-chapter-revision/SKILL.md` 增加：

```markdown
### 修订模式与输出要求

- **spot-fix 模式**: changes 数组每项必须包含 `location`（行号范围）、
  `before`（修改前文本 ≥20字）、`after`（修改后文本 ≥20字）、
  `reason`（修改原因 ≥30字）
- **rewrite 模式**: changes 数组每项必须包含 `section`（重写段落标识）、
  `rationale`（重写理由 ≥50字）
- **no-op 模式**: `route: "no_op"`, `changes: []`,
  `rationale: "<具体解释为何无需修改，引用审计通过的具体维度>"`（≥50字）
- **auto-skip 模式**: 同 no-op，但 `route: "auto_skip"`
```

### 3.3 chapter_loop 增加 revision 后验证

在 `chapter_loop.py` 的 `run_chapter_step` 中，step 18（revision）完成后增加：

```python
# 修订后验证：changes 不能为空（除非是明确的 no_op）
rev_file = project_dir / f"chapters/chapter-{state.current_chapter}-revision-decisions.json"
if rev_file.exists():
    try:
        data = json.loads(rev_file.read_text())
        changes = data.get('changes', [])
        route = data.get('route', '')
        if len(changes) == 0 and route not in ('no_op', 'auto_skip'):
            logger.warning("revision_no_changes", chapter=state.current_chapter)
    except json.JSONDecodeError:
        logger.error("revision_json_invalid", chapter=state.current_chapter)
```

---

## 4. 验证标准

1. **单元测试**：`tests/unit/gates/g4/test_chapter_revision.py`
   - 有效 spot-fix revision（3 个有详细描述的变更）→ PASS
   - 有效 no-op revision（空 changes + ≥50字 rationale）→ PASS
   - 空 changes 无 rationale → HARD FAIL
   - changes 中有 1 项缺少 description → HARD FAIL
   - JSON 语法错误 → HARD FAIL（由 g4_decisions 捕获）

2. **集成测试**：在测试 round 上运行 revision skill，验证 G4 能区分离线有效/无效 revision

3. **回归检查**：`just check` 全量通过

---

## 5. 依赖关系

```
Spec H1（JSON 格式修复） ← 弱依赖（JSON 验证基础）
  ↓
本 Spec
  ↓
Spec C1（修订覆盖章节） ← 共享 revision skill 改修
```
