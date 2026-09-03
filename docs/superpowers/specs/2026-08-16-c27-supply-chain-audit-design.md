> **Date:** 2026-08-16 | **Status:** Design (Revised 2026-09-03 · 设计审查 R1：审计口径/验收可执行化/R3 done-at-HEAD/R4 逐项枚举/release.yml 入范围) | **Severity:** 🟠 P1 | **方法:** systematic-debugging 四阶段
> **系列:** 2026-08-15 全项目审计 · 阶段 5 修复 spec（批次 C，簇 C27）| **依赖:** 无（与 C25 CI/just 同步簇有 security.yml 合写面，先到者在文件级加注释占位）| **范围:** .github/workflows/security.yml、.github/workflows/release.yml（SBOM 面）、uv.lock、SBOM 口径、pyproject 依赖集、SECURITY.md、.pre-commit-config.yaml、tools/check_licenses.py（新增）、docs/（LICENSES 口径） | **核心洞察:** 安全审计对象错位——pip-audit 审临时环境而非项目依赖集，且 docs 组整体在 Security 门与 SBOM 之外（T1303），"无漏洞"结论是 false assurance

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
- security.yml 改为对 `uv.lock` 全依赖集审计，唯一口径（pip-audit 2.10.1 不支持 `-r uv.lock`——uv.lock 是 TOML 非 requirements 格式）：`uv export --frozen --all-groups --all-extras --no-emit-project -o <tmp>req.txt` → `uv run pip-audit -r <tmp>req.txt`。`--all-groups` 是修 T1303 的关键（默认 export 仅 prod+dev）；`--all-extras` 覆盖 [project.optional-dependencies]（`--all-groups` 不含 extras——R4 把 numpy 迁 embeddings extra 后若无此旗标将静默跌出审计集，复造 T1303 类盲区）；`--no-emit-project` 剔除 `-e .` 自引用（pip-audit/cyclonedx 会 choke）；哈希默认输出（uv 无 `--require-hashes` 旗标，仅 `--no-hashes`）；删除 `--group dev` 收窄（T1303）
- **验收**：R1 的 FAIL 路径用 checked-in fixture 验证——`tests/fixtures/security/` 下带已知漏洞 pin 的 requirements 文件（真实 `uv export` 产物替换一个 pin，provenance 成文；G0.9）经同一 pip-audit 调用能报漏洞；禁止用改 uv.lock 的方式验证（会破坏 `uv sync --frozen` 上游，FAIL 来自 sync 而非审计，属假验证）

### R2 · SBOM 与许可证口径（T1304 + F1041）
- SBOM 生成改为按组分层：按组 `uv sync --frozen`（prod=`--no-dev --all-extras`，dev=`--only-group dev`，docs=`--only-group docs`——默认 sync 是 prod+dev，prod 必须显式 `--no-dev` 否则复造 F1041 过度包含）后用 `cyclonedx-py environment .venv/bin/python`（R2 实现层修订：`requirements` 子命令产物不含许可证元数据，无法支撑 license 执法；cyclonedx-py 在 dev 组，docs-only 环境以 `uvx --from cyclonedx-bom` 调用）；docs/dev 组产物以命名标注"不分发"。security.yml 与 release.yml:17-18（第二修复面，spec 范围字段原漏列）同步改，release.yml `files:` 上传清单同步改三份分组 SBOM 文件名，SECURITY.md:25 "SBOM attached to Releases" 措辞同步
- 新增 LICENSES 口径文档 + `tools/check_licenses.py`：解析三份 R2 SBOM 的 License 字段（uv export requirements 无许可证元数据，不可作解析源）对照 allowlist + 例外表（yamllint GPL-3.0、chardet LGPL 判定 dev-only 无传染，理由成文），作为 security.yml 步骤接线——无脚本的"例外表被 CI 校验"是 dead wire
- **验收**：docs 组 SBOM 含 mkdocs 栈（pymdown-extensions 等 26 包）；`tools/check_licenses.py` 在新增 GPL 家族依赖时 FAIL（用 `tests/fixtures/security/` 下真实 `cyclonedx-py` 输出改制的 fixture SBOM 验证 FAIL 路径，provenance 成文，同 R1 原则）

### R3 · 漏洞处置闭环（T1302，升级半 done-at-HEAD）
- ~~pymdown-extensions 升级至 ≥11.0.1~~——已在 main 落地（pyproject:54 `>=11.0.1`、uv.lock 锁 11.0.1），无剩余工作
- 剩余闭环半：建立"不可达 CVE 也须升级或登记豁免"规则并给可执行载体——pip-audit 任何 `--ignore-vuln` 项必须在例外登记文件带 ledger ID/理由，否则规则是第二处 dead wire；对 T1302 留一行 ledger 关闭注记（升级已落地的回写）
- **验收**：豁免登记文件存在且被机械执法——check_licenses.py 解析 security.yml 的 `--ignore-vuln` ID 清单，任一 ID 不在登记文件即 FAIL（存在≠执法，防 dead wire）；ledger T1302 行有关闭注记

### R4 · 死依赖清理与防线真实化（T1305/F1009 + F912 + F1008）
- 逐项处置（以 grep 双向核验零引用为前提，2026-09-03 复核）：
  - **删除** pytest-asyncio + `asyncio_mode="auto"` 死配置（pyproject:30/:472；全仓无 `async def test`——test_density.py:31 命中为 docstring 字符串非消费者）
  - **删除** pytest-ordering（pyproject:33；`pytest.mark.order`=0，且与 pytest-randomly 语义冲突 = F1009）
  - **删除** setuptools（pyproject:48；`pkg_resources`=0）
  - **迁移** numpy 从 `[project.dependencies]` 至 embeddings extra（唯一引用 truth_embed.py:185 lazy import，Route B 可选路径）
  - **保留** sentence-transformers dev 组双声明（embeddings-smoke.yml:4-6 注释声明的有意重复，非缺陷）
- F912：SECURITY.md:26 "pip-audit runs on every PR and weekly" 的 weekly 半句不实——二选一：security.yml 加 schedule，或删该半句（CodeQL weekly 属实保留）
- F1008：.pre-commit-config.yaml:42 yamllint rev v1.33.0 → v1.38.0（对齐锁内 1.38.0）
- **验收**：`uv sync --group dev` 后被删项不在锁内；`git grep "pip-audit" SECURITY.md` 与 security.yml 触发面一致；pre-commit rev == 锁内 yamllint 版本

## 验收（簇级）
- `just check` 全绿；Security workflow 对全依赖集运行且可在本地复现同口径
- C27 全部 9 条在 findings-ledger 回写 merged-into T1303 并随代表条目关闭

## 风险
- 全量审计可能引入新的真实 CVE FAIL（预期内：这正是 false assurance 的代价）——发现后按 R3 闭环逐条处置，不为绿灯回退审计范围
- security.yml 同时是 C25（CI/just 同步簇）的修复面——两 spec 合写同一文件时以本 spec R1 为准，C25 侧只做清单对账不重排步骤

## 验证命令
- 审计口径核对：`git grep -n "pip-audit\|--group" -- .github/workflows/security.yml`（应指向 uv export --all-groups 全集）
- 依赖集快照：`uv tree --depth 1`（核对 docs 组在树内且被审计覆盖）
- CVE 处置核对：`uv tree | grep -i pymdown`（≥11.0.1）
- 死依赖核对：`uv tree` + 对 T1305 五项逐个 `git grep -n <pkg> -- src/ tests/ pyproject.toml`
- 回归：`just check` 全绿

## 回写
- merged 关系（phase4 §3）：`T1303 <- F912, F1008-F1009, F1041, T1301-T1302, T1304-T1305`——代表条目关闭即成员关闭
- d1-baseline ⑨ 勘误随 T1301 关闭更新为"已按本簇 R1 口径固化"终态注记
- 上轮承接：#15（deps-supply-chain）的 D1-01 面在本簇 R1-R3 关闭后随 supersede 归档
