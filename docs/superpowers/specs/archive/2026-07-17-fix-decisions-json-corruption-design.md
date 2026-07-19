# 修复 decisions.json 格式损坏 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:**
> - `docs/superpowers/specs/2026-07-16-pipeline-maturity-and-bp-fixes-design.md`
> **目的:** 修复 44/56 个 `chapter-N-decisions.json` 的格式损坏——LLM 追加 markdown 文本到合法 JSON 后，且 G2/G4 门禁未捕获。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

对 56 个 `chapters/chapter-N-decisions.json` 逐一进行 `json.loads()` 验证：

- **44/56（78.6%）含有 tailing markdown**：合法 JSON 后追加了 LLM 的总结文本
- **多个文件包含 JSON 对象拼接**：Ch5 含 35 个 JSON 对象、Ch54 含 22 个
- **损坏模式一致**：所有损坏都是 `json.JSONDecodeError: Extra data`

典型损坏示例（Ch1）：
```json
{"$schema": "shenbi-decisions-v1", "skill": "shenbi-chapter-drafting", ...}
```
```
---
**两项 G4 失败修复摘要：**
1. **G4.transition (7→0)** — 正文中监控转折词使用量为零...
```

### 1.2 为什么门禁未捕获

现有防线有两层：
1. **G2**（`gates/g2.py:85`）：`json.loads(content)` → 应抛出 `JSONDecodeError("Extra data")`
2. **G4**（`gates/g4/decisions_validator.py:53`）：同上 + `DecisionsDoc.model_validate(data)`（`decisions.py:69`，`extra="forbid"`）

**两者都应该捕获这些错误。** 但审计结果显示它们在生产运行中未生效。可能原因：

1. **G2/G4 仅在特定路径运行**：`chapter_loop.py` 的 dispatch 流程中，decisions.json 可能走的是不同的验证路径
2. **`_write_parsed_outputs` 在门禁前写入**：`dispatch_helper.py:294-323` 先写入文件，G2/G4 事后检查——但检查失败后文件已持久化
3. **G4 重试后产出新 decisions.json**：retry feedback 后 LLM 重新输出，但累积拼接了多次输出

### 1.3 影响

- decisions.json 对自动化工具不可读（破坏 P2.5 rationale 规则执行）
- 下游 skill 通过 `reads:` 声明消费 decisions.json 时获取不可解析数据
- `DecisionsDoc.model_validate()` 无法执行 `extra="forbid"` 的字段检查

---

## 2. 根因分析

### 2.1 直接原因

`dispatch_helper.py:294-323`（`_write_parsed_outputs`）的解析逻辑：

```python
# 解析 ### FILE: path/to/file.md 标记
# 提取 ``` 围栏中的内容
# 无条件写入 safe_write(path, content)
```

**无写入前 JSON 验证。** LLM 在 `### FILE: chapters/chapter-N-decisions.json` 标记后，既输出了 JSON，又输出了 markdown 总结。解析器提取了全部内容，包括 trailing markdown。

### 2.2 多JSON拼接的原因

G4 失败 → retry → LLM 重新输出到同一文件 → `safe_write` 覆盖。但如果 G4 失败后的 retry feedback 包含了上一次的完整输出，LLM 可能将新旧 JSON 都输出到同一标记下。

### 2.3 门禁为何未完全阻断

`chapter_loop.py` 中 G2/G4 的调用位置需要核实。如果 decisions.json 在 composite checker 中被 `.json` 扩展名路由到 `g4_decisions`，它**应该**在 `json.loads()` 处失败。但实际产出中有 44 个损坏文件——说明：

- 要么门禁未被调用（auto 模式跳过了某些检查）
- 要么门禁失败后的 retry 循环最终接受了损坏文件

---

## 3. 修复方案

### 3.1 三层防线

**Layer 1：写入前验证（`dispatch_helper.py`）**

在 `_write_parsed_outputs`（`dispatch_helper.py:316` 附近）中，对 `.json` 文件增加预写验证：

```python
if path.suffix == '.json':
    try:
        parsed = json.loads(content)
        # 额外：验证 shenbi-decisions-v1 schema
        if isinstance(parsed, dict) and parsed.get('$schema') == 'shenbi-decisions-v1':
            from shenbi.contracts.schemas.decisions import DecisionsDoc
            DecisionsDoc.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error("decisions_json_invalid", path=str(path), error=str(e))
        # 尝试恢复：截取第一个完整 JSON 对象
        try:
            decoder = json.JSONDecoder()
            clean_data, end_pos = decoder.raw_decode(content)
            logger.warning("decisions_json_truncated", path=str(path),
                           original_len=len(content), cleaned_len=end_pos)
            content = json.dumps(clean_data, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            # 无法恢复，写入失败标记
            raise ValueError(f"Decisions JSON invalid and unrecoverable: {e}")
```

**Layer 2：G2 增强（`gates/g2.py`）**

增加对多JSON拼接的显式检测：

```python
# g2.py 新增：G2.dec.4 多JSON拼接检测
if content.count('"$schema"') > 1:
    issues.append("G2.dec.4: multiple JSON objects concatenated")
```

**Layer 3：Sectioned output 格式修正（`dispatch_helper.py` prompt）**

在 `_build_skill_prompt` 的用户指令中强化 JSON 输出格式：

```markdown
### 输出 JSON 文件的铁律：
- JSON 文件（*.json）必须是纯 JSON，**禁止**在 JSON 后追加任何文字说明
- **禁止**使用 markdown 代码围栏包裹 JSON 文件
- **禁止**输出多个 JSON 对象到同一文件
- 如果你的回复中包含对 JSON 内容的解释，请放在 `### FILE:` 标记之外
```

### 3.2 调查任务

1. 核实 chapter_loop.py 中 G2/G4 对 decisions.json 的调用路径是否对所有 chapter 执行
2. 检查 auto 模式（`chapter_loop.py:516-545`）是否跳过了 decisions.json 的 G4 检查
3. 如有跳过，修复

---

## 4. 验证标准

1. **单元测试**：`tests/unit/test_decision_json_validation.py`
   - 输入有效 JSON → 通过
   - 输入 JSON + trailing markdown → Layer 1 截取第一个合法 JSON 对象
   - 输入 3 个拼接 JSON → Layer 1 截取第一个 + Layer 2 报告
   - 输入完全无效 JSON → Layer 1 抛出 ValueError

2. **集成测试**：用已损坏的 Ch1 decisions.json 原始内容模拟 dispatch 写入，确认写入后文件为合法 JSON

3. **回归检查**：`just check` 全量通过，现有 decisions.json 相关测试继续通过

---

## 5. 依赖关系

```
无前置依赖（独立修复）
  ↓
下游：Spec H2（修订系统）受益于 JSON 格式修复
```
