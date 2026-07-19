# 端到端修复后验证 Spec

> **日期:** 2026-07-17
> **状态:** 设计中
> **严重度:** — (验证计划)
> **前置:** 所有 C1-C3、H1-H5、M1-M5、L1-L3 修复
> **目的:** 定义所有修复完成后的端到端验证流程，确保修复有效且无回归。

---

## 1. 验证矩阵

### 1.1 修复验证清单

| Spec | 关键验证 | 通过标准 | 状态 |
|------|---------|---------|------|
| C1 | revision no-op 路由不覆盖章节正文 | 原文保留 + pre-rev backup 存在 | ⬜ |
| C2 | 语言学漂移检测触发 | 10章运行中 density 不单调上升 | ⬜ |
| C3 | 文档完备 | `chapter-file-format.md` 存在且准确 | ⬜ |
| H1 | decisions.json 为合法 JSON | `json.loads()` 成功 + `model_validate()` 通过 | ⬜ |
| H2 | revision 产出有效变更 | changes 非空且每项有 ≥20 字描述 | ⬜ |
| H3 | 每章有 context 文件 | 运行 N 章 → N 个 context 文件 | ⬜ |
| H4 | staging 无残留 | 运行后 `staging/` 为空 | ⬜ |
| H5 | current_step 非空 | 中断-恢复后状态一致 | ⬜ |
| M1 | 日志含 token 计数 | 每步有 token 日志 | ⬜ |
| M2 | progress.json 更新 | 每章完成后更新 | ⬜ |
| M3 | 所有章节有快照 | Ch1 起即有 | ⬜ |
| M4 | state-settling 无超时 | 大章不超 1800s | ⬜ |
| M5 | resonance 重试 ≤1 | 5 次运行中重试率 < 20% | ⬜ |
| L1-L3 | 计时/字数日志存在 | 完成时输出汇总 | ⬜ |

### 1.2 端到端验证流程

**Stage 1：单元测试**
```bash
just check  # ruff + mypy + basedpyright + pytest
```
要求：全量通过，零失败。

**Stage 2：3 章 mini-pipeline**
```bash
uv run pipeline init mini-test --seed test-seed.md
uv run pipeline run mini-test --auto --max-chapters 3
```
验证：
- 3 章全部完成（含所有 audit + revision）
- 所有 spec 的验证标准满足
- 零 staging 残留
- progress.json 更新

**Stage 3：10 章 smoke test**
```bash
uv run pipeline run mini-test --auto --max-chapters 10 --resume
```
验证：
- 系统术语密度不单调上升（C2）
- resonance 重试率 < 20%（M5）
- 每章 context 文件存在（H3）
- 所有 decisions.json 为合法 JSON（H1）

**Stage 4：质量门禁**
- [ ] 无 HARD G4 失败（除合法触发外）
- [ ] 无 `json.JSONDecodeError` 在任何 decisions.json
- [ ] 无 staging 残留
- [ ] 每章字数在目标范围（L3）
- [ ] 快照覆盖所有章节（M3）

---

## 2. 回归风险

| 风险 | 缓解 |
|------|------|
| 旧 pipeline state 格式与新代码不兼容 | Stage 1 的单元测试覆盖状态加载 |
| Content size guard 误拦合法精简重写 | 阈值保守（20%），仅 WARN |
| 语言学漂移检测在实验性风格上误报 | WARN/HARD/ESCALATE 三级；需连续触发 |
| G4 feedback 格式示例在某些模型上不生效 | 保留原始检查 ID，示例为附加 |

---

## 3. 回滚计划

如验证发现严重回归，按 spec 独立回滚：
1. 每个 spec 的变更集中在 ≤3 个文件中
2. 使用 `git revert <commit>` 逐 spec 回滚
3. 回滚后重新运行 Stage 1-2 确认恢复
