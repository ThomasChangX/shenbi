# Spec #41 C27 供应链/安全审计盲区修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Security 门审计对象对齐 uv.lock 全集（含 docs 组与 extras）、SBOM 按组分层、许可证/豁免机械执法、死依赖清理与防线真实化。

**Architecture:** 全部为 CI workflow / 工具脚本 / 依赖配置改动，无 src/shenbi 运行时代码变更。审计口径统一为 `uv export --frozen --all-groups --all-extras --no-emit-project` → `pip-audit -r <file> --no-deps --disable-pip`；SBOM 用 `cyclonedx-py requirements` 按组生成；新增 `tools/check_licenses.py` 同时执法许可证例外表与 pip-audit `--ignore-vuln` 豁免登记。

**Tech Stack:** uv 0.10.7、pip-audit 2.10.1、cyclonedx-bom 7.3.1、GitHub Actions、pytest。

## Global Constraints

- 禁止真实 LLM dispatch 验证（核心原则 8）；一切验证走 `just`/`uv run`（与 CI `uv run --frozen` 同构）
- fixtures 只能是真实产物或其改制副本 + provenance 成文（G0.9）；禁止手写 SBOM/requirements
- 框架代码（若有）无 print、pathlib；本 plan 不触 src/shenbi
- conventional commits；每 task commit 后产出 `.superpowers/sdd/audit-T<N>.md`
- C25（#63）合写面：security.yml 改动处加注释占位，C25 侧只做清单对账不重排步骤
- spec：docs/superpowers/specs/2026-08-16-c27-supply-chain-audit-design.md（Revised 2026-09-03 版，commit d8f0e834）

---

### Task 1: R1 审计口径对齐（T1301+T1303）

**复杂度: infra · test_kind: regression_guard（workflow 结构断言）+ 手动 FAIL 路径验证**

**Files:**
- Modify: `.github/workflows/security.yml`（全文件重写 audit job 步骤）
- Modify: `tools/pre-push-check.sh:37-39`（本地镜像同步同口径）
- Create: `tests/fixtures/security/req-vulnerable.txt`（真实 export 产物改制）
- Create: `tests/fixtures/security/PROVENANCE.md`
- Test: `tests/unit/tools/test_security_workflow_contract.py`

**Interfaces:**
- Produces: security.yml audit 口径命令串（Task 2 SBOM 步骤与其同处一文件）；fixture `req-vulnerable.txt`（Task 3 check_licenses 测试不依赖它，独立）
- 审计口径（唯一信源，后续 task 引用）：
  `uv export --frozen --all-groups --all-extras --no-emit-project -o <file> && uv run pip-audit -r <file> --no-deps --disable-pip`

- [ ] **Step 1: 生成真实 export fixture 并注入已知漏洞 pin**

```bash
mkdir -p tests/fixtures/security
uv export --frozen --all-groups --all-extras --no-emit-project -o tests/fixtures/security/req-vulnerable.txt
```
然后编辑该文件：将其中一行 pin 替换为带已知 CVE 的版本（用 `requests==2.30.0 \` 替换现有 requests pin 行，保留该行原有的 `--hash` 行删除——pip-audit `--no-deps` 模式不校验哈希完整性；requests 2.30.0 有 PYSEC-2023-262 等已知漏洞）。保留文件头 uv 自动生成注释。

`tests/fixtures/security/PROVENANCE.md` 内容：
```markdown
# fixtures/security provenance

- `req-vulnerable.txt`: 真实 `uv export --frozen --all-groups --all-extras --no-emit-project`
  产物（2026-09-03，uv 0.10.7，main @ <commit>），仅将 requests pin 行替换为
  `requests==2.30.0`（已知 CVE：CVE-2023-32681 等）用于 pip-audit FAIL 路径回归。
  替换行原 --hash 已随替换移除（--no-deps 模式不校验）。
```

- [ ] **Step 2: 重写 security.yml audit 步骤**

新 audit job steps（checkout/setup-uv 不变；`actions/checkout@v4`、`astral-sh/setup-uv@v3` 维持现状不动——版本 bump 归 dependabot）：

```yaml
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      # Spec #41 (C27) R1: 审计对象 = uv.lock 全集（--all-groups 含 docs 组，
      # --all-extras 含 embeddings；默认 export 仅 prod+dev 是 T1303 盲区）。
      # C25 (#63) 合写面：本 audit 步骤归 spec #41 R1 所有，C25 侧清单对账勿重排。
      - run: uv export --frozen --all-groups --all-extras --no-emit-project -o req-audit.txt
      - run: uv run pip-audit -r req-audit.txt --no-deps --disable-pip
      - run: uv run cyclonedx-py requirements -o sbom.cdx.json req-audit.txt   # Task 2 改为分组三份
      - uses: actions/upload-artifact@v7
        with:
          name: sbom
          path: sbom.cdx.json
```
（注：删除 `uv sync` 行后 `uv run` 会隐式 sync 默认组使 pip-audit/cyclonedx 可解析——无需恢复显式 sync 行。Task 1 阶段 cyclonedx 行先保持单份 `environment`→`requirements` 最小变更也可；Task 2 统一改分组——两 task 同文件串行，以 Task 2 终态为准。）

- [ ] **Step 3: 同步 pre-push-check.sh 本地镜像**

`tools/pre-push-check.sh` :37-39 的 `uv sync --frozen --group dev` + `uv run pip-audit` 替换为同一 export+audit 管线（echo 文案同步改为 "pip-audit (uv.lock full set, mirroring CI security.yml)"）。

- [ ] **Step 4: 写 workflow 契约测试**

`tests/unit/tools/test_security_workflow_contract.py`：
```python
"""Spec #41 (C27) R1: security.yml 审计口径契约——审计对象必须是 uv.lock 全集。

T1301/T1303 回归守卫：任何收窄审计范围的改动（如恢复 --group dev、去掉
--all-groups/--all-extras、退回 uvx pip-audit/环境审计）都会使本测试 FAIL。
"""
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/security.yml"
PRE_PUSH = Path(__file__).resolve().parents[3] / "tools/pre-push-check.sh"
REQUIRED_EXPORT = "uv export --frozen --all-groups --all-extras --no-emit-project"
FORBIDDEN = ("--group dev", "uvx pip-audit")


def test_security_yml_audits_full_lock_set() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert REQUIRED_EXPORT in text
    assert "pip-audit -r" in text
    for token in FORBIDDEN:
        assert token not in text, f"audit scope narrowed: {token!r} re-introduced"


def test_pre_push_mirrors_ci_audit_scope() -> None:
    text = PRE_PUSH.read_text(encoding="utf-8")
    assert REQUIRED_EXPORT in text
```
（cyclonedx 行不在断言范围——Task 2 会改它，避免跨 task 耦合。）

- [ ] **Step 5: 跑测试 + FAIL 路径实证验收**

```bash
uv run pytest tests/unit/tools/test_security_workflow_contract.py -v   # PASS
uv run pip-audit -r tests/fixtures/security/req-vulnerable.txt --no-deps --disable-pip ; echo "rc=$?"
```
预期第二条 rc=1 且输出含 requests 2.30.0 漏洞条目——这是 spec R1 验收（同一调用能报漏洞），输出全文粘贴 progress.md `## 验收证据`。

- [ ] **Step 6: `uv run yamllint --strict .github/workflows/security.yml` + commit**

```bash
git add .github/workflows/security.yml tools/pre-push-check.sh tests/fixtures/security/ tests/unit/tools/test_security_workflow_contract.py
git commit -m "fix(security): audit uv.lock full set (all-groups+all-extras) — C27 T1301/T1303, spec #41 R1"
```

---

### Task 2: R2 SBOM 按组分层（T1304 面 + F1041）

**复杂度: infra · test_kind: regression_guard（workflow 结构断言）**

**Files:**
- Modify: `.github/workflows/security.yml`（SBOM 步骤）
- Modify: `.github/workflows/release.yml:14-18,46`
- Modify: `SECURITY.md:25`
- Test: `tests/unit/tools/test_security_workflow_contract.py`（追加）

**Interfaces:**
- Consumes: Task 1 的 export 口径
- Produces: 三份 SBOM 产物名 `sbom-prod.cdx.json` / `sbom-dev.cdx.json` / `sbom-docs.cdx.json`（Task 3 check_licenses.py 在 CI 中解析的输入名）

- [ ] **Step 1: security.yml SBOM 步骤改分组三份**

```yaml
      # Spec #41 (C27) R2: SBOM 按组分层（F1041——environment 子命令无法分组，
      # 且 dev/docs 组不分发）。prod 必须 --no-dev（默认 export 是 prod+dev）。注：uv 不允许 --only-group 与 --all-extras 同用（实测 error）——extras 不属于 dev/docs 组；dev 组 SBOM 仍含 ML 栈（sentence-transformers 是 dev 直接依赖）。
      - run: uv export --frozen --no-dev --all-extras --no-emit-project -o req-prod.txt
      - run: uv export --frozen --only-group dev --no-emit-project -o req-dev.txt
      - run: uv export --frozen --only-group docs --no-emit-project -o req-docs.txt
      - run: uv run cyclonedx-py requirements --output-reproducible -o sbom-prod.cdx.json req-prod.txt
      - run: uv run cyclonedx-py requirements --output-reproducible -o sbom-dev.cdx.json req-dev.txt
      - run: uv run cyclonedx-py requirements --output-reproducible -o sbom-docs.cdx.json req-docs.txt
      - run: uv run python tools/check_licenses.py sbom-prod.cdx.json sbom-dev.cdx.json sbom-docs.cdx.json   # Task 3 接线
      - uses: actions/upload-artifact@v7
        with:
          name: sbom
          path: |
            sbom-prod.cdx.json
            sbom-dev.cdx.json
            sbom-docs.cdx.json
```
（check_licenses 行在 Task 3 落地前先注释占位或本 task 提前到 Task 3 一起启用——串行执行，Task 3 完成后终态启用；本 task commit 时脚本尚不存在则该行必须留到 Task 3，避免 CI 红。）

- [ ] **Step 2: release.yml 同步**

release.yml:14-18 的 `uv sync --frozen --group dev` + `cyclonedx-py environment -o sbom.cdx.json` 替换为与 security.yml 相同的三组 export+cyclonedx 管线（release 面只需 prod+dev+docs 三份同生成）；:46 `files:` 列表 `sbom.cdx.json` 替换为三份新文件名。

- [ ] **Step 3: SECURITY.md:25 措辞**

`SBOM ... attached to GitHub Releases` 相关行改为反映三份分组 SBOM（prod=分发面 / dev、docs=不分发，仅溯源）。

- [ ] **Step 4: 追加契约测试断言**

```python
def test_sbom_layered_per_group() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for group in ("prod", "dev", "docs"):
        assert f"sbom-{group}.cdx.json" in text
    assert "cyclonedx-py environment" not in text  # F1041: environment 无法分组


def test_release_uploads_three_group_sboms() -> None:
    release = WORKFLOW.parent / "release.yml"
    text = release.read_text(encoding="utf-8")
    for group in ("sbom-prod.cdx.json", "sbom-dev.cdx.json", "sbom-docs.cdx.json"):
        assert group in text
    assert "cyclonedx-py requirements" in text
    assert "cyclonedx-py environment" not in text  # F1041 原发地
```

- [ ] **Step 5: 验收 + commit**

```bash
uv run pytest tests/unit/tools/test_security_workflow_contract.py -v
uv run yamllint --strict .github/workflows/security.yml .github/workflows/release.yml
git add .github/workflows/security.yml .github/workflows/release.yml SECURITY.md tests/unit/tools/test_security_workflow_contract.py
git commit -m "fix(security): per-group layered SBOM (prod/dev/docs) — C27 F1041, spec #41 R2"
```
（SBOM 含 mkdocs 栈的验收在 CI 真实运行时由 sbom-docs 产物体现；本地可先 `uv run cyclonedx-py requirements -o /tmp/t.cdx.json req-docs.txt && grep -c pymdown /tmp/t.cdx.json` 实证 ≥1，粘贴 progress.md。）

---

### Task 3: R2+R3 check_licenses.py + 豁免登记机械执法（协调者亲自实现）

**复杂度: infra · test_kind: tdd_red_green**

**Files:**
- Create: `tools/check_licenses.py`
- Create: `tools/supply_chain_exceptions.json`
- Create: `docs/framework/licenses.md`（LICENSES 口径文档）
- Modify: `.github/workflows/security.yml`（启用 check_licenses 行）
- Create: `tests/fixtures/security/sbom-gpl-fixture.cdx.json`（真实 cyclonedx 输出改制）
- Modify: `tests/fixtures/security/PROVENANCE.md`
- Test: `tests/unit/tools/test_check_licenses.py`

**Interfaces:**
- Consumes: Task 2 的三份 SBOM 文件名；pip-audit `--ignore-vuln`（若 security.yml 未来出现）ID 集
- Produces: `python tools/check_licenses.py <sbom...>` — rc=0 全过 / rc=1 发现未登记 copyleft 或未登记 ignore-vuln；异常表 schema：
```json
{
  "licenses": {
    "GPL-3.0-or-later": {"package": "yamllint", "group": "dev", "ledger": "T1304",
                          "reason": "dev-only CI tool, wheel only packages src/shenbi, no distribution contagion"},
    "LGPL-2.1-or-later": {"package": "chardet", "group": "dev", "ledger": "T1304",
                          "reason": "transitive of cyclonedx-bom, dev-only, not distributed"}
  },
  "ignore_vulns": {}
}
```
（chardet 实际 license 字段以真实 SBOM 为准——实现时以 fixture 实测值填 key；UNKNOWN/无 license 字段组件不 FAIL，仅记 WARN。）

- [ ] **Step 1: 生成真实 SBOM fixture**

```bash
uv export --frozen --only-group docs --no-emit-project -o /tmp/req-docs.txt
uv run cyclonedx-py requirements --output-reproducible -o tests/fixtures/security/sbom-gpl-fixture.cdx.json /tmp/req-docs.txt
```
再复制一份将任一组件 license 改为 `GPL-3.0-only`（改制副本，PROVENANCE.md 记录改了哪个组件）→ `sbom-gpl-injected.cdx.json`。PROVENANCE.md 追加两条记录。

- [ ] **Step 2: 写失败测试**

`tests/unit/tools/test_check_licenses.py`：
```python
"""Spec #41 (C27) R2/R3: check_licenses.py 许可证例外表 + ignore-vuln 豁免机械执法。"""

# noqa 惯例见同目录既有测试；tmp_path 为 pytest 内建 fixture
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIX = REPO / "tests/fixtures/security"
TOOL = REPO / "tools/check_licenses.py"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_clean_sbom_passes() -> None:
    result = run_tool(str(FIX / "sbom-gpl-fixture.cdx.json"), "--exceptions", str(REPO / "tools/supply_chain_exceptions.json"))
    assert result.returncode == 0, result.stdout + result.stderr


def test_unregistered_gpl_fails() -> None:
    result = run_tool(str(FIX / "sbom-gpl-injected.cdx.json"), "--exceptions", str(REPO / "tools/supply_chain_exceptions.json"))
    assert result.returncode == 1
    assert "GPL-3.0-only" in result.stdout


def test_ignore_vuln_must_be_registered(tmp_path) -> None:
    # 模拟 security.yml 含未登记 --ignore-vuln ID
    wf = tmp_path / "fake-workflow.yml"
    wf.write_text("run: pip-audit --ignore-vuln PYSEC-FAKE-0001\n", encoding="utf-8")
    try:
        result = run_tool(str(FIX / "sbom-gpl-fixture.cdx.json"),
                          "--exceptions", str(REPO / "tools/supply_chain_exceptions.json"),
                          "--workflows", str(wf))
        assert result.returncode == 1
        assert "PYSEC-FAKE-0001" in result.stdout
    finally:
        wf.unlink()
```
（fake-workflow.yml 写入 pytest tmp_path 运行时临时目录，非 repo fixture 树，不违反 G0.9。）
Run: `uv run pytest tests/unit/tools/test_check_licenses.py -v` → FAIL（模块不存在）。

- [ ] **Step 3: 实现 check_licenses.py**

要点（完整实现约 120 行）：
- argparse：位置参数 sbom 文件列表；`--exceptions`（默认 `tools/supply_chain_exceptions.json`）；`--workflows`（默认 `.github/workflows/security.yml`，可多值）
- 解析 CycloneDX JSON：`components[].licenses[].license.id`（无 id 用 `.name`）；GPL/LGPL/AGPL/SSPL 前缀族命中 copyleft
- copyleft 命中且不在 exceptions.licenses（key=license id 且 package 匹配）→ print 违规行 + rc=1；在表内 → print 登记引用（ledger ID）
- 解析 workflows 文本提取全部 `--ignore-vuln <ID>`，任一 ID 不在 exceptions.ignore_vulns → rc=1
- 无 license 字段/UNKNOWN → stderr WARN 不 FAIL
- 纯 stdlib（json/argparse/pathlib/re/sys），rc 语义与 tools/ 既有 lint 一致

- [ ] **Step 4: 跑测试到绿 + 接线 security.yml**

```bash
uv run pytest tests/unit/tools/test_check_licenses.py -v
```
security.yml 启用 Task 2 预留的 `uv run python tools/check_licenses.py sbom-prod.cdx.json sbom-dev.cdx.json sbom-docs.cdx.json` 行。

- [ ] **Step 5: docs/framework/licenses.md 口径文档**

内容框架：wheel 只打包 src/shenbi（[tool.hatch.build.targets.wheel]）→ 分发面=prod 组运行时依赖；dev/docs 组不分发；GPL 家族（yamllint GPL-3.0-or-later、chardet LGPL）判定 dev-only 无传染；例外表 `tools/supply_chain_exceptions.json` 由 check_licenses.py 机械执法；新增 copyleft 依赖必须先登记（带 ledger/reason）再进锁。

- [ ] **Step 6: commit**

```bash
git add tools/check_licenses.py tools/supply_chain_exceptions.json docs/framework/licenses.md .github/workflows/security.yml tests/unit/tools/test_check_licenses.py tests/fixtures/security/
git commit -m "feat(security): license exception registry + ignore-vuln enforcement — C27 T1304/R3 closure rule, spec #41"
```

---

### Task 4: R4 死依赖清理 + 防线真实化（T1305/F1008/F1009/F912）

**复杂度: infra（依赖面） · test_kind: regression_guard（uv lock + 全量测试）**

**Files:**
- Modify: `pyproject.toml`（:14 numpy、:30/:33/:48 三删、:472 asyncio_mode、:22-23 embeddings extra）
- Modify: `uv.lock`（`uv lock` 再生成）
- Modify: `.pre-commit-config.yaml:42`（rev v1.33.0 → v1.38.0）
- Modify: `.github/workflows/security.yml`（加 weekly schedule）
- Modify: `SECURITY.md:26`（weekly 声明变为真实）

**Interfaces:**
- Consumes: 无
- Produces: numpy 归位 embeddings extra；`uv lock --check` 绿

- [ ] **Step 1: pyproject 编辑**

- `[project.dependencies]` 删 `"numpy>=1.26.0",` 行（含注释行）
- `[project.optional-dependencies]` embeddings = `["sentence-transformers>=5.7.0", "numpy>=1.26.0"]`
- dev 组删 `"pytest-asyncio>=0.23.0",`、`"pytest-ordering>=0.6",`、`"setuptools>=81.0.0",`
- `[tool.pytest.ini_options]` 删 `asyncio_mode = "auto"` 行
- `[tool.mypy.overrides] module = "numpy.*"`（pyproject:88-91）随迁移变死配置，一并删除
- 保留 sentence-transformers dev 双声明（embeddings-smoke.yml 有意重复）

- [ ] **Step 2: 重新锁 + 验证**

```bash
uv lock
uv lock --check          # 绿
uv sync --group dev --group docs
uv run pytest -n auto -m "not last" --no-cov -q | tail -3
grep -c 'name = "pytest-asyncio"\|name = "pytest-ordering"\|name = "setuptools"' uv.lock  # 0
```
（numpy 仍在锁内——dev 组 sentence-transformers 传递依赖；`uv tree | grep -i pymdown` 仍 11.0.1。）

- [ ] **Step 3: pre-commit rev + weekly schedule**

- `.pre-commit-config.yaml` yamllint hook `rev: v1.38.0`
- security.yml `on:` 加：
```yaml
  schedule:
    - cron: "0 3 * * 1"
```
（周一 03:00 UTC，与 codeql 周一 cron、autoupdate 周一 02:00 错峰；F912——使 SECURITY.md:26 weekly 声明成真。）

- [ ] **Step 4: 验收 + commit**

```bash
uv run pre-commit run yamllint --all-files || true   # rev 变更后需 uv sync（已做）
git add pyproject.toml uv.lock .pre-commit-config.yaml .github/workflows/security.yml
git commit -m "chore(deps): drop dead deps (pytest-asyncio/ordering/setuptools), numpy→embeddings extra, yamllint rev 1.38.0, weekly audit schedule — C27 T1305/F1008/F1009/F912, spec #41 R4"
```

---

### Task 5: ledger 回写 + d1-baseline 注记（簇级验收收尾）

**复杂度: leaf（纯 docs） · test_kind: n/a（git grep 验证）**

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（9 行）
- Modify: `docs/superpowers/audit-runs/2026-08-15/d1/d1-baseline.md`（⑨ 勘误终态注记）

**Interfaces:** 无

- [ ] **Step 1: 9 条 findings 回写**

F912/F1008/F1009/F1041/T1301/T1302/T1304/T1305 状态列 open→closed，处置列记 `fixed by spec #41 (T1303 代表条目, PR #N)`；T1303 行同样关闭并加代表注记（`merged-into 关系：T1303 <- F912,F1008-F1009,F1041,T1301-T1302,T1304-T1305`）。PR 号合并后补（先写 `PR #<pending>`，阶段 10 后 amend 或在归档 PR 补）。

- [ ] **Step 2: d1-baseline ⑨ 终态注记**

勘误块追加一句：`2026-09-03 终态：审计口径已按 spec #41 (C27) R1 固化为 uv export --all-groups --all-extras → pip-audit -r（security.yml + pre-push 镜像）`。

- [ ] **Step 3: commit + 簇级验收核对**

```bash
git grep -n "T1301\|T1302\|T1303\|T1304\|T1305\|F912\|F1008\|F1009\|F1041" docs/superpowers/audit-runs/2026-08-15/findings-ledger.md | grep -c closed  # 9
git add docs/superpowers/audit-runs/2026-08-15/
git commit -m "docs(ledger): close C27 cluster 9 findings via spec #41 (T1303 representative)"
```

---

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| R1 FAIL 路径 | T1 | `uv run pip-audit -r tests/fixtures/security/req-vulnerable.txt --no-deps --disable-pip` rc=1 |
| R1 口径固化 | T1 | `test_security_yml_audits_full_lock_set` + `git grep "--group dev" security.yml` = 0 |
| R2 SBOM 含 mkdocs 栈 | T2 | 本地 cyclonedx 生成 docs 组 SBOM grep pymdown ≥1 + CI artifact |
| R2 license FAIL 路径 | T3 | `test_unregistered_gpl_fails` rc=1 |
| R3 豁免执法 | T3 | `test_ignore_vuln_must_be_registered` rc=1 |
| R3 ledger 注记 | T5 | ledger T1302 行含关闭注记 |
| R4 死依赖清零 | T4 | uv.lock grep 三包 = 0 + `uv lock --check` 绿 |
| R4 文档/workflow 一致 | T4 | security.yml 有 schedule + SECURITY.md:26 保留 weekly |
| R4 pre-commit 对齐 | T4 | `.pre-commit-config.yaml:42` rev == 锁内 yamllint 版本 |
| 簇级：just check 全绿 | 全部 | `just check` |
| 簇级：本地复现同口径 | T1 | pre-push 管线同命令 |
