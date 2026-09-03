# 许可证口径与例外登记（spec #41 / C27）

> T1304 闭环：GPL 家族许可证出现在依赖集时必须显式判定并登记，不允许"上轮无 GPL"
> 这类未机械核对的结论再次出现。

## 分发面判定

- 本项目 wheel 仅打包 `src/shenbi`（`[tool.hatch.build.targets.wheel]`），**分发面 =
  `[project.dependencies]` 运行时依赖**（jieba/pydantic/pyyaml/structlog/openai/tenacity）。
- dev 组（测试/CI/类型检查工具链）与 docs 组（mkdocs 栈）**不进入分发物**，仅用于
  仓库内构建与验证，MIT 分发无传染。

## 已登记的 copyleft 例外（`tools/supply_chain_exceptions.json`）

| 包 | 许可证 | 组 | 判定 |
|---|---|---|---|
| yamllint | GPL-3.0-or-later | dev | CI lint 工具，不分发，无传染 |
| chardet | LGPL（cyclonedx-bom 传递） | dev | SBOM 工具链传递依赖，不分发 |
| cairosvg | LGPL-3.0-or-later | docs | mkdocs-material[imaging] 传递，仅 docs 构建 |

## 机械执法

`tools/check_licenses.py`（security.yml 步骤）解析三份分组 SBOM（prod/dev/docs，
`cyclonedx-py environment` 产物，含许可证元数据）：

1. 任何 GPL/LGPL/AGPL/SSPL 家族许可证命中且**未登记** → CI FAIL；
2. 已登记包名但许可证串与登记值不符 → CI FAIL（防登记漂移）；
3. pip-audit 任何 `--ignore-vuln <ID>` 必须在例外表 `ignore_vulns` 登记并带
   ledger ID 与理由——"不可达 CVE 也须升级或登记豁免，不允许静默留存"（T1302
   闭环规则；升级半已落地：pymdown-extensions 锁 11.0.1）。

新增 copyleft 依赖时：先在本表与 JSON 登记组归属/理由/ledger 引用，再进锁。
若未来引入 runtime/容器分发，dev/docs 组例外判定需重审（登记时 reason 必须重写）。
