# 行为测试：修订模式路由 — 问题类型→修订策略

测试目标：验证 `shenbi-chapter-revision` 的 auto 模式能正确路由不同类型的问题到 spot-fix 或 rewrite。

## 测试场景

章节同时存在 3 个不同类型的问题，agent 必须分别为每个选择正确的修订模式。

## 输入（审计报告摘要）

```markdown
## 审计报告

### Anti-AI 审计
- [ERROR] 第3段：连续4个"了"字句（了字密度过高）
- [ERROR] 第7段："不由得倒吸一口凉气"（禁忌词）
- [WARNING] 第12段：段落长度与其他段落方差过大

### 角色一致性审计
- [ERROR] 主角 OOC：角色档案"谨慎谋定后动"，本章"不假思索冲入危险"
```

## 期望路由

| 问题 | 路由到 | 理由 |
|------|--------|------|
| 了字密度、禁忌词 | spot-fix (PATCHES) | 措辞/用词问题，局部替换即可 |
| 段落长度方差 | spot-fix (PATCHES) | 段落形状问题，局部调整 |
| 主角 OOC | rewrite (REVISED_CONTENT) | 角色行为是结构问题，需要重组段落 |

## 通过条件

- [ ] Anti-AI 问题路由到 spot-fix
- [ ] OOC 问题路由到 rewrite
- [ ] 最终修订使用混合策略（PATCHES + REVISED_CONTENT）
- [ ] 修订后 OOC 段落被重写（不仅是替换用词）

## 失败条件

- 所有问题都用 spot-fix → FAIL（OOC 是结构问题，不能只替换用词）
- 所有问题都用 rewrite → FAIL（了字和禁忌词只需靶向替换）
- 修后长度变化超过 ±15% → FAIL（铁律: 不超过 ±15%）
