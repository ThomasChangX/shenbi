# 减少 Token 浪费 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟡 Medium
> **前置:** Spec M5（G4 共振审计格式冲突）— 间接减少重试 token
> **目的:** 量化和减少 pipeline 运行中的 token 浪费，降低 API 成本并加快生成速度。

---

## 1. 背景

### 1.1 发现（2026-07-17 审计）

对 56 章的 token 消耗估算：

| 类别 | Token 估算 | 备注 |
|------|-----------|------|
| 产出文件 token | ~4.1M | 所有输出文件 |
| 其中 META 块 | ~65K | 每章 31% 被剥离 |
| G4 失败重试 | ~170K | 35 次 resonance 重试 + 19 次其他重试 |
| 损坏 decisions.json | ~96K | 不可解析的 JSON |
| 审计产出 | ~1.1M | 722 个文件 |
| 模糊估算总浪费 | ~35% | — |

### 1.2 主要浪费来源

1. **G4 重试循环**（最大单项）：35 次 resonance 重试，每次 ~4K token
2. **META 块在每次 LLM 调用中被传输**：虽在最终消费时剥离，但 drafting 和 audit 阶段的 prompt 包含完整上下文
3. **审计文件缺乏质量过滤**：722 个审计文件，部分内容单薄
4. **decisions.json 损坏后的重写**：损坏文件被重新生成

---

## 2. 优化机会

### 2.1 减少 G4 重试（依赖 Spec M5）

修复 resonance 格式冲突（Spec M5）后，35 次重试可减少 50-80%。节省 ~85-136K token。

### 2.2 META 块不重复传输（与 Spec C3 协同）

当 META 块在 prompt context 中时，每次 LLM 调用都包含前几章的 META 块。方案：
- 在 context assembly 中剥离 META 块后再注入 prompt
- 预计节省 ~10-15% prompt token

### 2.3 审计早期终止

当前 13 种审计全部执行 55-56 章。可实现：
- 如果前 3 种审计（character, continuity, world-rules）均 PASS 且 confidence > 90%，跳过其余 10 种
- 预计节省 ~15-20% 审计 token

### 2.4 Token 计数追踪

在 dispatch 层增加 token 计数（为未来 P1.7 成本预算打基础）：

```python
# dispatch_helper.py 增加
import tiktoken

def _estimate_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))
```

---

## 3. 修复方案

### Phase 1（本 spec）：可观测性

1. **增加 dispatch 级别的 token 日志**：每次 LLM 调用记录 prompt_tokens + completion_tokens
2. **流水线结束时打印 token 汇总**：按 skill 分组

### Phase 2（依赖其他 spec）：优化

1. 消除 resonance G4 重试（Spec M5）
2. META 块上下文剥离（Spec C3 中期方案 A）
3. 审计早期终止（新增 G4 规则）

---

## 4. 验证标准

- Pipeline 运行日志包含每步 token 计数
- Pipeline 完成时输出 token 汇总报告
- 优化后重试 token 减少 > 50%

---

## 5. 依赖关系

```
Phase 1（可观测性）：无前置依赖
Phase 2（优化）：依赖 Spec M5, Spec C3
```
