> **Date:** 2026-08-16 | **Status:** Design | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C27）| **依赖:** 无（与 C25 CI/just 同步簇有 security.yml 合写面，先到者在文件级加注释占位）| **范围:** .github/workflows/security.yml、uv.lock、SBOM 口径、pyproject 依赖集 | **核心洞察:** 安全审计对象错位——pip-audit 审临时环境而非项目依赖集，且 docs 组整体在 Security 门与 SBOM 之外（T1303），"无漏洞"结论是 false assurance

# C27 · 供应链/安全审计盲区修复（supply-chain-audit）

## 元信息
- 簇：C27（供应链/安全审计盲区），9 条，最高严重度 P1，证据等级=实验佐证（T1301/T1303 协调者核实 verified）
- 成员：T1303（代表）、T1301、T1302、T1304、T1305、F912、F1008、F1009、F1041
- 来源：`docs/superpowers/audit-runs/2026-08-15/findings-ledger.md` + thread-reports/T13.md + zone-reports/Z10.md

## 背景与根因
CI 的安全审计从未与"项目实际依赖集"对账，而是审计执行环境自身的临时包集合；同时 docs 依赖组被 `--group dev` 排除在 Security 门与发布 SBOM 之外。结果是被审计的对象与被分发的对象不是同一个集合——mkdocs 栈 26 包（含 T1302 的 ReDoS CVE 所在包）从不进入任何漏洞扫描。根因是审计口径（group 参数）与依赖真相（uv.lock 全集）之间无对账断言，"weekly pip-audit"（F912）这一声称的防线本身不存在。

### 证据要点
- **T1301（P1 verified）**：`uvx pip-audit` 审计的是临时环境 29 包而非项目依赖集，基线"无漏洞"结论无效
- **T1303（P1 verified）**：security.yml:13 `--group dev` 系统性排除 docs 组——mkdocs 栈 26 包在 Security 门和 SBOM 之外，是 T1302 漏检的直接成因
- **T1302（P2）**：pymdown-extensions 11.0 已知 ReDoS（CVE-2026-67422，修复于 11.0.1）；当前 mkdocs.yml 未启用四个受影响扩展，配置不可达，但依赖仍在锁内
- **T1304（P2）**：GPL 家族许可证混入 dev 工具链（yamllint GPL-3.0 直接依赖、chardet LGPL 传递）；上轮"无 GPL"结论事实错误（wheel 仅打包 src，分发面无传染，但口径未成文）
- **T1305（P2）**：未使用/错位依赖 4+1 项（pytest-asyncio/pytest-ordering/setuptools 等）零处置回归
- **F912（P2）**："pip-audit weekly"声称不存在（无 schedule/无 workflow）
- **F1008/F1009（P2）/F1041（M）**：.pre-commit-config.yaml 与 pyproject.toml 依赖面缺陷、SBOM dev 组口径过度包含（见 Z10 报告）

## 目标
1. 安全审计对象 = uv.lock 全量依赖集（含 docs 组），审计结果可复现地覆盖分发面
2. SBOM 口径成文：prod 组 vs dev/docs 组分列，GPL/LGPL 出现在哪个组、是否进分发面有显式判定记录
3. 漏洞处理闭环：T1302 类 CVE 即使"配置不可达"也在升级或豁免登记二选一，不允许静默留存

## 任务分解
### R1 · 审计对象对齐（T1301，P1）
- security.yml 改为对 `uv.lock` 全依赖集审计（`pip-audit -r uv.lock --require-hashes` 或 `uv export --frozen` 后审计），删除 `--group dev` 收窄（T1303）
- **验收**：手工在 lock 中注入一条带 CVE 的测试依赖（或用 T1302 现场验证），Security 门能 FAIL

### R2 · SBOM 与许可证口径（T1304 + F1041）
- SBOM 生成改为按组分层（prod/dev/docs），docs/dev 组标注"不分发"
- 新增 LICENSES 口径文档：GPL-3.0（yamllint）、LGPL（chardet 传递）判定为 dev-only 无传染，理由成文
- **验收**：SBOM 含 mkdocs 栈 26 包；许可证例外表存在且被 CI 校验（新依赖带 GPL 家族许可证时 FAIL）

### R3 · 漏洞处置闭环（T1302）
- pymdown-extensions 升级至 ≥11.0.1；建立"不可达 CVE 也须升级或登记豁免"规则
- **验收**：`uv tree | grep pymdown` 显示 ≥11.0.1；对 T1302 留一行 ledger 关闭注记

### R4 · 死依赖清理与防线真实化（T1305 + F912）
- 移除/合并 4+1 未使用依赖（以 `uv tree` + grep 双向核验零引用后删除）
- "pip-audit weekly"要么落地为 scheduled workflow，要么从文档删除该声称（F912）
- F1008/F1009 的 pre-commit/pyproject 依赖面项随本条一并处置
- **验收**：`uv sync --group dev` 后无未使用依赖残留；文档与 workflow 一致

## 验收（簇级）
- `just check` 全绿；Security workflow 对全依赖集运行且可在本地复现同口径
- C27 全部 9 条在 findings-ledger 回写 merged-into T1303 并随代表条目关闭

## 风险
- 全量审计可能引入新的真实 CVE FAIL（预期内：这正是 false assurance 的代价）——发现后按 R3 闭环逐条处置，不为绿灯回退审计范围
- security.yml 同时是 C25（CI/just 同步簇）的修复面——两 spec 合写同一文件时以本 spec R1 为准，C25 侧只做清单对账不重排步骤

## 验证命令
- 审计口径核对：`git grep -n "pip-audit\|--group" -- .github/workflows/security.yml`（应指向 uv.lock 全集）
- 依赖集快照：`uv tree --depth 1`（核对 docs 组在树内且被审计覆盖）
- CVE 处置核对：`uv tree | grep -i pymdown`（≥11.0.1）
- 死依赖核对：`uv tree` + 对 T1305 五项逐个 `git grep -n <pkg> -- src/ tests/ pyproject.toml`
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`T1303 <- F912, F1008-F1009, F1041, T1301-T1302, T1304-T1305`——代表条目关闭即成员关闭
- 上轮承接：#15（deps-supply-chain）的 D1-01 面在本簇 R1-R3 关闭后随 supersede 归档
