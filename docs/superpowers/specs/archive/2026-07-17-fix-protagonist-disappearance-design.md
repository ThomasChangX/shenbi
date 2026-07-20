# 修复叙事模式崩塌：人类主角消失 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🔴 Critical
> **前置:** Spec C2（文风漂移检测）
> **目的:** 阻止长篇生成中人类主角被参数代理替代——Ch35起林烽从文本中完全消失，被"冷""光""安静""缺口"等参数实体替代。

---

## 1. 背景

### 1.1 发现

**Agent 1 Audit 3** 追踪了主角林烽在56章中的存在：

| 维度 | Ch1-10 | Ch20 | Ch35 | Ch50 |
|------|--------|------|------|------|
| 人类对话 | 存在 | 无（独白章） | **不存在** | **不存在** |
| 物理动作 | 存在 | 存在（生理参数化） | **不存在** | **不存在** |
| 内心独白 | 存在 | 存在 | **不存在** | **不存在** |
| 名字"林烽" | 出现 | 出现 | **不出现** | **不出现** |

`characters/protagonist.md` 声明的角色弧线（利己主义生存→被迫卷入→从愤怒到方法→功成身退）停滞在 Stage 1。

`character_matrix.md` 被改写为参数描述："冷：系统层积记忆载体+宣告后层积第一显现日持有者"。

### 1.2 影响

- 约 21 章（Ch35-56，37.5%）无人类主角
- 声明的角色关系（陈卫民、赵铁柱、楚云岚等）全部未出场
- 这不是风格选择——是从人类叙事到参数叙事的**模式崩塌**

---

## 2. 根因分析

与 Spec C2（文风漂移）共享根因：
- L3 context 缺失 → LLM 失去叙事锚点
- Chapter memo 的参数化语言污染散文
- character_matrix 被 state-settling 逐步改写为参数描述

**新增发现**：`character_matrix.md` 作为唯一角色真相来源，被 state-settling 每章覆盖时，将参数代理作为"角色"写入——形成自我强化的参数角色体系。

---

## 3. 修复方案

### 3.1 Character matrix 写保护

`character_matrix.md` 应由人类角色架构定义，state-settling 只能**追加**状态更新，不能**替换**角色定义：

```python
# state_settling.py 或等效位置
# 规则：character_matrix.md 的"角色定义"部分不可被参数实体替换
# 参数实体（冷、光、安静等）应写入 particle_ledger.md，非 character_matrix.md
```

### 3.2 主角存在性 G4 检查

新增 `G4.cd.protagonist_presence` 检查（在 `chapter_drafting.py`）：

```python
# 检查章节正文是否包含主角名或主角相关代词
protagonist_names = ['林烽', '他']  # 从 protagonist.md 读取
text = extract_prose(chapter_path)
name_count = sum(text.count(n) for n in protagonist_names)
if name_count < 3:
    issues.append("G4.cd.protagonist_absent: 主角在正文中出现少于3次")
```

### 3.3 与 Spec C2 协同

语言学漂移检测（Spec C2）中增加"人类代理密度"指标——对话引导词（"说"、"道"、"问"）、人称代词（"他"、"她"）的密度。

---

## 4. 验证标准

1. 连续 10 章运行中，每章主角出现 ≥ 3 次
2. character_matrix.md 保留人类角色定义
3. `just check` 全量通过

---

## 5. 依赖

```
Spec C2（语言学漂移检测）← 共享检测框架
  ↓
本 Spec
```
