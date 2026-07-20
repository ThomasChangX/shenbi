# 修复 85 个 JSON 文件非标准格式 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** Spec H1（decisions.json 格式修复）
> **目的:** 修复 84 个 decisions.json 含尾部 markdown + 1 个真实损坏（staging/plans/chapter-49-plan-decisions.json 控制字符）。

---

## 1. 背景

### 1.1 发现（Agent 3 §3）

- 84 个 decisions.json：合法 JSON + 尾部 markdown（第一个 JSON 对象可解析）
- **1 个真实损坏**：`staging/plans/chapter-49-plan-decisions.json` line 21 column 160 —— 非法控制字符
- 所有 gate-marker 和 checklist JSON 正常

### 1.2 与 Spec H1 的关系

Spec H1 已设计了 Layer 1-3 防线。本 spec 补充：
- 对 staging 文件的同等验证
- 控制字符检测

---

## 2. 修复方案

### 2.1 staging JSON 同等验证

Spec H1 的 Layer 1（写入前验证）需同样应用于 staging 路径。

### 2.2 控制字符清洗

增加通用清洗函数：

```python
def sanitize_json_content(content):
    """移除 JSON 中的非法控制字符。"""
    # JSON 规范仅允许特定的控制字符（\n, \r, \t 等）
    # 移除其他控制字符（0x00-0x1F 除了 \n \r \t）
    import re
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    return cleaned
```

---

## 3. 验证标准

1. 所有 56 个 decisions.json 通过 `json.loads()`（单文档模式）
2. 0 个 staging JSON 含非法控制字符
3. `just check` 全量通过
