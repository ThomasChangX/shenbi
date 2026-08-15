> **Date:** 2026-08-14 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-14 全项目审查（补齐 spec 5/7） | **依赖:** 无 | **范围:** prompt injection/命令注入/路径穿越/env 暴露 | **核心洞察:** wrapper 边界失效 + truth 持久化放大 + codex 写面无约束 → prompt injection 为最大系统性风险

# 安全与提示注入（补齐 E）

## R1 · wrapper 属性注入与转义（T12-01, P1）
- 证据：`<document name="{fname}">` 零转义，`[^/]*` 放行 `"` 文件名 → 逃逸 wrapper 注入 prompt
- 修复：属性值转义（HTML/XML entity）+ 文件名词法白名单；**验收：含 `"` 文件名注入测试 FAIL**

## R2 · 持久化注入链与 codex 写面约束（T12-02, P1）
- 证据：codex（workspace-write, -C {dir}）路径不受 _write_parsed_outputs 契约校验，可直改 pipeline-state/gate-markers/scores；无写审计（F512）；truth 持久化跨章放大
- 修复：codex 写面纳入契约校验 + 写审计；状态文件只读保护；**验收：注入无法改写状态/门禁文件**

## P2 清单（命令注入/env 继承/路径穿越/skill 名校验）
- **T12-03（P2）** run_pipeline.sh 与 tests/round-exec.sh 将目录参数插值进 `python3 -c "…"` 双引号 shell 串 → `'`/`"`/`$()`/反引号 均可注入任意命令（命令注入；Z10 区确认 + 新实例）
- **T12-04（P2）** codex/zcode 子进程全量继承父环境：SHENBI_LLM_API_KEY（T1 路径）/CI token 等凭证可达 workspace-write 通用编码 agent；与 T12-02 注入链叠加构成凭证外泄路径
- **T12-05（P2）** 写路径穿越防御脆弱隐式：`relative_to` 词法不归一化 `..`（拦截仅靠 wildcard 正则形态）；symlink 目录逃逸（声明目录为 symlink 时契约校验通过的写落盘到 link 目标）；safe_write 零规范化
- **T12-06（P2）** 按名拼接的防御缺失：`skills/{skill}/SKILL.md` 与 `load_contract(skill)` 无 skill 名词法校验（当前调用方全为硬编码配置，未来不可信 skill 名 → 任意仓库文件读入 system prompt + 契约混淆）；plugins/generate.py `REPO_ROOT / config["output"]` 允许 `..`
