# 修复 Ch20 Plan-Content 不匹配 + 3 个事实性错误 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** 🟠 High
> **前置:** 无
> **目的:** 增加 plan-content 交叉验证——Ch20 计划要求 MH-003 advance 但章节正文零 MH-003 存在，连续性审计观察到但未标记为缺陷。同时修复 3 个事实性算术/逻辑错误。

---

## 1. 背景

### 1.1 Plan-Content 不匹配（Agent 1 Audit 1）

Ch20 计划 Section 7 Hook Ledger 明确要求：
```
| MH-003 | advance | 新基线中的巡逻密度确认——Ch19升级后是否稳定在更高频率 |
```

但章节正文**零 MH-003 存在**。连续性审计观察到但仅作"建议"而非缺陷标记。

### 1.2 三个事实性错误

| 位置 | 错误 | 正确 |
|------|------|------|
| Ch10 L293 | 铜币 "四十六枚半" | 算术应为 ~40.5 铜（6 枚差异） |
| Ch35 L301 | 光束偏移 "十六张" | 应为 15 张（每日+1 模式） |
| Ch50 plan §1 vs §7 | "五日" vs "四日" | 应为四日（周二距周日） |

---

## 2. 修复方案

### 2.1 Plan-content 交叉验证 G4 检查

新增 `G4.cp.plan_fulfillment` 检查——验证计划的 hook ledger 中的 hook 是否实际出现在章节正文中：

```python
# g4/chapter_drafting.py 新增
def check_hook_fulfillment(plan_path, chapter_path):
    plan_text = plan_path.read_text()
    chapter_text = chapter_path.read_text()

    # 提取 plan 中声明的 hook IDs
    plan_hooks = set(re.findall(r'MH-\d+', plan_text))
    chapter_hooks = set(re.findall(r'MH-\d+', chapter_text))

    missing = plan_hooks - chapter_hooks
    if missing:
        return [f"G4.cd.hook_unfulfilled: plan requires {missing} but not found in chapter"]
    return []
```

### 2.2 算术一致性检测

在 continuity 审计 prompt 中增加显式的算术验证指令：
- 铜币/货币累计验证
- 日期/计数模式验证（如每日+1 偏移）

---

## 3. 验证标准

1. Ch20 模拟回归 → hook_fulfillment 检测捕获 MH-003 缺失
2. continuity 审计捕获算术错误
3. `just check` 全量通过
