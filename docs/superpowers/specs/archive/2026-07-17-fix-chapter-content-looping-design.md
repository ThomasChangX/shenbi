# 修复 Ch36-39 连续四章内容循环 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** Spec HN1（跨章模板复制）
> **目的:** 检测并阻止连续多章的高内容重叠——Ch36-39 形成 32-52% 重叠的循环簇。

---

## 1. 背景

### 1.1 发现（Agent 2）

Ch36-Ch39 四章内容重叠异常：

| 章节对 | 相似度 |
|--------|--------|
| Ch37-Ch38（相邻） | 45.4% |
| Ch38-Ch39（相邻） | 47.1% |
| Ch37-Ch39（非相邻） | **51.9%** |

非相邻重叠超过相邻——表明内容在四章间循环而非线性推进。

---

## 2. 修复方案

扩展 Spec HN1 的检测到**滑动窗口**（连续 3-5 章）：

```python
def check_window_redundancy(chapter_texts, window_size=4, threshold=0.35):
    """检测滑动窗口内的内容循环。"""
    if len(chapter_texts) < window_size:
        return None

    window = chapter_texts[-window_size:]
    max_sim = 0
    for i in range(len(window)):
        for j in range(i+1, len(window)):
            sim = SequenceMatcher(None, window[i], window[j]).ratio()
            max_sim = max(max_sim, sim)

    if max_sim > threshold:
        return f"WINDOW_REDUNDANCY: max_sim={max_sim:.0%} in {window_size}-chapter window"
    return None
```

---

## 3. 验证标准

任意连续 4 章窗口内最大相似度 ≤ 35%

---

## 4. 依赖

```
Spec HN1（跨章模板复制）
  ↓
本 Spec（滑动窗口扩展）
```
