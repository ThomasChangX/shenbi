# P-1: Foundation Hygiene Design Spec

- **Status**: proposed
- **Date**: 2026-06-14
- **Decider**: ThomasChangX
- **Phase**: P-1 (precedes P0 Registry Metadata System)
- **Depends on**: none
- **Blocks**: P0, P1, P2, P3, P4, P5, P6

## Executive Summary

P-1 把 Shenbi 代码库从"散装脚本集合"升级到 2026 年现代 Python 项目工程基线。所有后续 P 阶段（P0-P6）与所有未来 round（008+）在此基线上构建。

P-1 的核心动作：

- ✅ 加配置文件（pyproject.toml / ruff / mypy / basedpyright / pre-commit / CI）
- ✅ 重构代码组织（validate-gate.py 机械拆分，dispatch-subagent.sh → Python 重写，行为不变）
- ✅ 改善代码质量（structlog / typed exceptions / type hints / docstrings）
- ✅ 建立测试基线（pytest 框架 + 470 sample tests）
- ✅ 归档历史 round（含每轮 README 索引）

P-1 的核心非动作：

- ❌ 不改业务逻辑
- ❌ 不引入新概念（Pydantic schemas、registry 等留给 P0）
- ❌ 不改协议（command-to-give.md 留给 P5）

## Scope

### 必做项（13 项）

1. `pyproject.toml` + `uv.lock`（含 dev 依赖与 hashes）
2. ruff 配置（lint + format，规则集选 strict preset）
3. mypy --strict + basedpyright（双重类型检查）
4. pytest 框架（pytest + pytest-cov + pytest-xdist + pytest-asyncio + pytest-timeout + pytest-benchmark + Hypothesis）
5. 改写 test_integrity.py 为 pytest 风格
6. GitHub Actions CI（lint + type + test + coverage gate + registry-freshness 检查）
7. pre-commit hooks（ruff/mypy/basedpyright + registry 自动 rebuild）
8. structlog 集成（取代所有 print）
9. typed exception hierarchy（ShenbiError 基类 + 子类层级）
10. ADR 模板 + 前 9 条 ADR
11. validate-gate.py 机械式拆分 + 非 P0 依赖的语义改善
12. dispatch-subagent.sh → Python 重写（行为不变）
13. phantom rounds 归档（含每轮 README + 索引）

### 加成项（5 项）

14. pytest-benchmark（基准测试，回归检测）
15. pip-audit / safety（CI 跑漏洞扫描）
16. SBOM 生成（CycloneDX，为未来产品发布准备）
17. mkdocs-material 自动文档（API 文档从 Pydantic 与 docstring 生成）
18. mutmut / cosmic-ray（mutation testing，验证测试质量）

### 目录重命名

- `tests/rounds/round-001-*` 至 `round-007-*` 移至 `tests/rounds/archived/`
- 每个归档 round 含 README.md 记录状态与归档原因
- `tests/rounds/archived/README.md` 是索引

## Section 1: Architecture

### 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│ 配置层（Configuration）                                          │
│                                                                 │
│ pyproject.toml          项目元数据 + 所有工具配置               │
│ uv.lock                 依赖锁定（含哈希）                      │
│ .pre-commit-config.yaml pre-commit hooks                       │
│ .github/workflows/      GitHub Actions CI                      │
│ mkdocs.yml              文档生成配置                            │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ 源代码层（Source Code）                                          │
│                                                                 │
│ tests/                                                          │
│   ├── __init__.py                                               │
│   ├── conftest.py          全局 pytest fixtures                │
│   ├── exceptions.py        ShenbiError 层级                    │
│   ├── logging.py           structlog 配置                      │
│   ├── validate-gate.py     CLI shim（~30 行，转发到 gates/）   │
│   ├── dispatch-subagent.sh CLI shim（~10 行，转发到 dispatcher/）│
│   ├── gates/                                                    │
│   │   ├── __init__.py                                           │
│   │   ├── shared.py       共享 utility                         │
│   │   ├── cli.py          argparse + 路由                      │
│   │   ├── g0.py ~ g7.py   一个 gate 一个文件                   │
│   │   └── g4/             G4 子目录                            │
│   │       ├── __init__.py 路由                                 │
│   │       ├── generic.py                                       │
│   │       └── <skill>.py  一个 skill 一个文件                  │
│   ├── dispatcher/                                               │
│   │   ├── __init__.py                                           │
│   │   ├── cli.py          argparse                             │
│   │   └── executor.py     核心调度逻辑                         │
│   ├── build_registry.py   P0 后激活，P-1 占位                  │
│   ├── load_registry.py    P0 后激活，P-1 占位                  │
│   ├── rounds/                                                   │
│   │   ├── round-000-TEMPLATE/                                   │
│   │   └── archived/                                             │
│   │       ├── README.md   索引                                 │
│   │       └── round-001-* ~ round-007-*/                        │
│   └── 其他保留                                                  │
│                                                                 │
│ docs/                                                           │
│   ├── adr/                Architecture Decision Records         │
│   │   ├── 0000-template.md                                     │
│   │   ├── 0001-pyproject-uv.md                                 │
│   │   ├── 0002-ruff-strict.md                                  │
│   │   ├── ...                                                  │
│   │   └── 0009-dispatcher-python-rewrite.md                    │
│   └── api/                mkdocs 自动生成（gitignored）        │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ 测试层（Tests）                                                  │
│                                                                 │
│ tests/unit/                单元测试（~780 最终）                │
│ tests/integration/         跨模块（~150 最终）                  │
│ tests/property/            Hypothesis（~50 最终）               │
│ tests/benchmark/           pytest-benchmark（~20 最终）         │
│ tests/fixtures/            测试 fixture 数据                    │
│ tests/baselines/           等价性测试 baseline                  │
│ tests/coverage/            覆盖率报告（gitignored）            │
└─────────────────────────────────────────────────────────────────┘
```

### 设计原则

1. **pyproject.toml 单一配置源**。所有工具配置集中在 pyproject.toml。
2. **职责分离的模块化**。每个文件单一职责。CLI 入口退化为 shim。
3. **测试金字塔**。unit : integration : property : benchmark = 78:15:5:2。
4. **文档与代码同源**。ADR 是手写决策；API 文档 mkdocs 自动生成。
5. **构建产物 gitignored**。`__pycache__/`、`.coverage`、`tests/coverage/`（HTML/JSON/XML 报告产出位置）、`docs/api/`（mkdocstrings 自动生成）不入 git。`htmlcov/` 是 pytest-cov 默认路径，本框架不用，但加入 `.gitignore` 防意外。
6. **归档与主流程隔离**。`tests/rounds/archived/` 不被主流程读取。

### P-1 不变量

| 项 | P-1 是否动 | 哪个 P 做 |
|---|----------|---------|
| `skills/` 目录结构 | 不动 | P0 |
| `tests/tiers/` 下任何 .json/.yaml 配置 | 不动 | P0 |
| `tests/fixtures/` 内容 | 不动 | 永久（fixtures 是源数据） |
| `tests/rounds/round-000-TEMPLATE/` 结构 | 不动 | P0/P1 配合 |
| `outline-example.md` 等顶级文档 | 不动 | 永久 |
| `CLAUDE.md` / `goal-prompt.md` / `command-to-give.md` | 不动 | P5 协议改造 |
| `hooks/`（Claude Code plugin hook） | 不动 | 与 P-1 无关 |
| G0-G7 各 gate 的**业务逻辑** | 不动 | P2 |
| `dispatch-subagent.sh` 的**调度策略** | 不动（行为保持） | P4 |
| `phase-runner.py` 内 phase 推进逻辑 | 不动 | P5 |

## Section 2: Components (17 PRs)

按依赖顺序排列。

### Group A: 项目元数据与代码质量工具（PR 1-4）

#### PR 1: pyproject.toml + uv.lock + .gitignore + 项目元数据

依赖管理选 uv（2024+ 业界最快）。Python >=3.11。依赖分 main 与 dev。

```toml
[project]
name = "shenbi"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.5.0",        # P-1 不用；为 P0 schemas 准备
    "pyyaml>=6.0.1",
    "structlog>=24.1.0",
    "patch>=1.16",
    "click>=8.1.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0", "pytest-cov>=4.1.0", "pytest-xdist>=3.5.0",
    "pytest-asyncio>=0.23.0", "pytest-timeout>=2.2.0", "pytest-benchmark>=4.0.0",
    "hypothesis>=6.97.0", "mypy>=1.8.0",
    "basedpyright>=1.13.0",   # 纯 Python 的 pyright fork，避免 Node.js 依赖
    "ruff>=0.1.13", "pre-commit>=3.6.0", "pip-audit>=2.7.0",
    "cyclonedx-bom>=4.0.0", "mutmut>=3.0.0",
    "coverage>=7.4.0",        # 用于 branch coverage 阈值强制
    "action-validator>=0.0.7",  # GitHub Actions YAML 校验
    "pytest-ordering>=0.6",    # @pytest.mark.last 用于 coverage threshold test
]
docs = ["mkdocs>=1.5.3", "mkdocs-material>=9.5.4", "mkdocstrings[python]>=0.24.0"]

[project.scripts]
shenbi-validate-gate = "tests.gates.cli:main"
shenbi-dispatch = "tests.dispatcher.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["tests"]
# skills/ 不是 Python 包（无 __init__.py），作为数据文件包含
[tool.hatch.build.targets.wheel.force-include]
"skills/" = "skills/"
"docs/adr/" = "docs/adr/"
```

**`.gitignore` 内容**（PR-1 创建）：
```
# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
.basedpyright_cache/

# Coverage
.coverage
coverage.xml
htmlcov/
tests/coverage/

# Build artifacts
*.egg-info/
dist/
build/

# Docs (auto-generated)
docs/api/
site/

# IDE
.idea/
.vscode/

# OS
.DS_Store

# Shenbi-specific
sbom.cdx.json
.mutmut-cache
```

**`renovate.json`**（PR-1 创建，依赖自动更新）：
```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended", ":semanticCommits"],
  "schedule": ["before 6am on monday"],
  "packageRules": [
    {
      "groupName": "ruff",
      "matchPackagePatterns": ["ruff"]
    },
    {
      "groupName": "pytest",
      "matchPackagePatterns": ["pytest"]
    },
    {
      "matchUpdateTypes": ["minor", "patch"],
      "automerge": true,
      "automergeType": "pr",
      "automergeStrategy": "squash"
    },
    {
      "matchUpdateTypes": ["major"],
      "automerge": false,
      "labels": ["major-bump"]
    }
  ]
}
```

`uv.lock` 由 `uv lock` 生成，提交到 git。

PR-1 验证：`uv build --wheel` 成功，无 warning；`uv sync --frozen` 在干净 clone 上可用；`uv run pytest --version` 可执行。

#### PR 2: ruff 配置 + 全仓库 auto-fix

ruff 取代 flake8 + isort + pylint + black。选 E,F,W,I,N,B,A,C4,PIE,RET,SIM,PL,UP,RUF,D 规则集。

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["tests/rounds/archived"]

[tool.ruff.lint]
select = ["E","F","W","I","N","B","A","C4","PIE","RET","SIM","PL","UP","RUF","D"]
ignore = ["D100","D104","PLR0913"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["D103"]
```

#### PR 3: mypy --strict 配置

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unreachable = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
no_implicit_reexport = true
namespace_packages = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = "tests.gates.g4.*"
disallow_untyped_defs = false  # P-1 拆分时允许，P2 改完移除

[[tool.mypy.overrides]]
module = "tests.rounds.archived.*"
ignore_errors = true
```

#### PR 4: basedpyright 配置（纯 Python 的 pyright fork，无 Node.js 依赖）

```toml
[tool.basedpyright]
include = ["tests", "skills"]
exclude = ["tests/rounds/archived", "**/__pycache__"]
typeCheckMode = "strict"
pythonVersion = "3.11"
reportMissingTypeStubs = "warning"
reportUnknownMemberType = "warning"
```

**理由**：`pyright`（Microsoft）需要 Node.js 运行时。`basedpyright` 是 pure-Python fork，避免 Node.js 隐式依赖，更适合"现代 Python 单语言基线"。CI 与本地都通过 `uv run basedpyright` 调用，无外部依赖。

### Group B: 测试框架（PR 5-6）

#### PR 5: pytest 框架 + conftest.py + sample test

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests/unit", "tests/integration", "tests/property", "tests/benchmark"]
addopts = [
    "--strict-markers",
    "--cov=tests",
    "--cov-report=term-missing",
    "--cov-report=html:tests/coverage",
    "--cov-report=xml:tests/coverage/coverage.xml",
    "--cov-branch",
    "-n=auto",
    "--timeout=60",
    "--timeout-method=thread",
    "--benchmark-min-rounds=5",
    "--benchmark-warmup=on",
]
markers = [
    "unit: fast unit tests",
    "integration: cross-module tests",
    "property: Hypothesis property-based tests",
    "benchmark: pytest-benchmark performance tests",
    "slow: > 5s tests",
]
asyncio_mode = "auto"

[tool.coverage.run]
branch = true
source = ["tests"]

[tool.coverage.report]
# Line coverage threshold (fail_under applies to line coverage only)
fail_under = 90
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

**测试子目录创建（PR-5 必做）**：

PR-5 创建空目录 + `.gitkeep`：
```
tests/unit/__init__.py
tests/unit/.gitkeep
tests/integration/__init__.py
tests/integration/.gitkeep
tests/property/__init__.py
tests/property/.gitkeep
tests/benchmark/__init__.py
tests/benchmark/.gitkeep
tests/coverage/.gitkeep
tests/baselines/.gitkeep
tests/fixtures/.gitkeep
```

否则 `testpaths = ["tests/unit", ...]` 在 pytest 启动时报"path does not exist"。

**Branch coverage 阈值强制（解决 `--cov-fail-under` 无法约束 branch 的问题）**：

pytest-cov 的 `--cov-fail-under=N` 仅作用于 line coverage。Branch coverage 阈值（80%）通过额外 pytest 测试强制：

```python
# tests/unit/test_coverage_thresholds.py
"""Enforce coverage thresholds post-test."""
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

COVERAGE_XML = Path("tests/coverage/coverage.xml")
LINE_THRESHOLD = 90
BRANCH_THRESHOLD = 80

# 通过 pytest-ordering 保证此测试在所有其他测试之后跑（coverage.xml 必须先生成）
# pytest-ordering 通过 @pytest.mark.last 或 [tool.pytest.ini_options] 中的 order 配置
@pytest.mark.last
def test_branch_coverage_meets_threshold():
    """Branch coverage must be >= 80%. Runs last to ensure coverage.xml exists."""
    if not COVERAGE_XML.exists():
        pytest.fail(
            "coverage.xml not found; ensure pytest runs with "
            "'--cov-report=xml:tests/coverage/coverage.xml' and "
            "test_coverage_thresholds runs AFTER all other tests"
        )

    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()

    total_branches_valid = 0
    total_branches_covered = 0
    for cls in root.findall(".//class"):
        for counter in cls.findall("counter"):
            if counter.get("type") == "BRANCH":
                total_branches_valid += int(counter.get("valid"))
                total_branches_covered += int(counter.get("covered"))

    if total_branches_valid == 0:
        pytest.skip("No branches in coverage data")

    branch_pct = (total_branches_covered / total_branches_valid) * 100
    assert branch_pct >= BRANCH_THRESHOLD, (
        f"Branch coverage {branch_pct:.1f}% below threshold {BRANCH_THRESHOLD}%. "
        f"Covered {total_branches_covered}/{total_branches_valid} branches."
    )
```

**pytest-ordering 依赖**：在 dev 依赖组加 `pytest-ordering>=0.6`（已隐含在前述 dev 列表，PR-1 时明确添加）。`@pytest.mark.last` 保证此测试最后跑，确保 `coverage.xml` 已由前面测试生成。

**Exit code 兼容性**：

pytest 内置 exit codes：0 (success)、1 (test fail)、2 (interrupted)、5 (no tests collected)。Shenbi 的 exit codes（Section 4.5）：0/1/2/3/4/5。当 pytest 作为子进程被 Shenbi CLI 调用时，**外层 Shenbi CLI 的 exit code 覆盖 pytest 的**（外层捕获 pytest exit code 并翻译为 Shenbi code）。文档明确：

```
Shenbi CLI exit codes（权威）：
  0  Success
  1  User error (gate FAIL / coverage fail / branch coverage fail)
  2  Framework error (registry stale / schema 错)
  3  Unexpected exception
  4  Timeout
  5  Skipped (explicit)

pytest exit codes（仅 pytest 自身，子进程内）：
  0  All tests passed
  1  Some tests failed
  2  Test execution interrupted
  5  No tests collected

当 pytest 被 Shenbi 调用时：
  pytest 0  → Shenbi 0
  pytest 1  → Shenbi 1 (test failure reported to user)
  pytest 2  → Shenbi 3 (interrupted = unexpected)
  pytest 5  → Shenbi 5 (skipped)
```

PR-13 (dispatcher rewrite) 实现此翻译逻辑。

#### PR 6: 改写 test_integrity.py 为 pytest 风格

现有 unittest 风格改为 pytest 风格。拆分到 tests/unit/test_gates_g0.py、test_gates_g4_worldbuilding.py 等。**不增不减测试覆盖**。

### Group C: CI/CD（PR 7-8）

#### PR 7: GitHub Actions CI（3 个 workflow 文件）

`ci.yml`（quality）、`security.yml`（audit + SBOM）、`docs.yml`（mkdocs build + 部署）三个独立文件，每个职责单一。

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push: { branches: [main] }
  pull_request: {}
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  quality:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv python install ${{ matrix.python-version }}
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy .
      - run: uv run basedpyright  # 纯 Python，无 Node.js
      - run: uv run pytest --hypothesis-profile=ci
      # test_branch_coverage_meets_threshold 已在 pytest 内，自动校验 80% branch

  action-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - name: Validate GitHub Actions YAML
        run: |
          for f in .github/workflows/*.yml; do
            uv run action-validator "$f"
          done
```

```yaml
# .github/workflows/security.yml
name: Security
on:
  push: { branches: [main] }
  pull_request: {}
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run pip-audit
      - run: uv run cyclonedx-py environment -o sbom.cdx.json
      - uses: actions/upload-artifact@v4
        with: { name: sbom, path: sbom.cdx.json }
```

```yaml
# .github/workflows/docs.yml
name: Docs
on:
  push: { branches: [main] }
  pull_request: {}
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen --extra docs
      - run: uv run mkdocs build --strict
      - uses: actions/upload-artifact@v4
        with:
          name: docs-site
          path: site/
  deploy:
    needs: build
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen --extra docs
      - run: uv run mkdocs gh-deploy --force
```

**`registry-freshness.yml` 暂不创建**：P-1 时点无 `.yaml` 文件可校验。P0 加 registry.lock.json 后由 P0 spec 负责新增 `registry-freshness.yml`。pre-commit 中的 `registry-lockfile-fresh` hook 同理（见 PR-8 注释）。

#### PR 8: pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.13
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.5]
        args: [--strict]
  - repo: local
    hooks:
      # basedpyright 没有官方 pre-commit mirror（基于 Node.js 的 pyright mirror 不适用）
      # 改用 local hook 调用 uv run basedpyright，版本由 uv.lock 锁定
      - id: basedpyright
        name: basedpyright (strict type check)
        entry: uv run basedpyright
        language: system
        types: [python]
        pass_filenames: false
        # 校验整个仓库，不传文件名（pyright 自身管理 include/exclude）
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: detect-private-key
  - repo: https://github.com/adrienverge/yamllint
    rev: v1.33.0
    hooks:
      - id: yamllint
        args: [--strict]
        files: \.(yaml|yml)$
        exclude: ^tests/rounds/archived/
  
  - repo: local
    hooks:
      # P0 scaffolding：P-1 时点 skills/ 无 .yaml，tests/tiers/ 也不存在，
      # 此 hook 不会触发。P0 完成 skills/<name>/meta.yaml + scenarios/*.yaml 迁移后激活。
      - id: registry-lockfile-fresh
        name: registry.lock.json freshness (P0 scaffolding, no-op in P-1)
        entry: tests/build_registry.py
        language: system
        files: ^(skills/.*\.yaml|tests/tiers/.*\.yaml)$
        pass_filenames: false
        # stub 实现在 PR-1 占位阶段，输出警告即退出 0；P0 替换为真实 build

      - id: action-validator
        name: GitHub Actions YAML validation
        entry: uv run action-validator
        language: system
        files: ^\.github/workflows/.*\.yml$
        pass_filenames: true
        # 版本由 uv.lock 锁定，无显式 rev 标签
```

### Group D: 代码质量基础设施（PR 9-10）

#### PR 9: structlog 集成 + 替换所有 print

JSON 输出（生产）+ console 输出（dev），环境变量 `SHENBI_LOG_FORMAT=json|console`。每次工具调用 = 一个 event，含结构化字段。替换所有 print（约 93 处，跨 `tests/*.py` 全部文件）。

```python
# tests/logging.py
import os
import structlog

def configure_logging() -> None:
    """Configure structured logging for the framework."""
    log_format = os.environ.get("SHENBI_LOG_FORMAT", "console")
    renderer = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger."""
    return structlog.get_logger(name)
```

#### PR 10: typed exception hierarchy + error_guidance.py + recovery.py

异常层级（见 Section 4）。

PR-10 同时产出：
- `tests/exceptions.py`：ShenbiError 层级
- `tests/error_guidance.py`：用户友好的错误指引（ERROR_GUIDANCE dict + get_guidance）
- `tests/recovery.py`：自动恢复策略枚举 + RECOVERY_STRATEGIES dict（P-1 只定义，不接入主流程；P3 实施）

三个文件共同实现"错误生命周期"：raise → log → guide user → optional auto-recover。

### Group E: ADR（PR 11）

#### PR 11: ADR 模板 + 前 9 条 ADR

ADR 编号 4 位（0001, 0002, ...）。模板：Michael Nygard 经典格式。

前 9 条覆盖 P-1 全部决策：
- 0001-pyproject-uv.md
- 0002-ruff-strict.md
- 0003-mypy-basedpyright-dual.md
- 0004-pytest-framework.md
- 0005-structlog.md
- 0006-typed-exceptions.md
- 0007-adr-process.md
- 0008-validate-gate-modularization.md
- 0009-dispatcher-python-rewrite.md

#### PR 17: mkdocs-material 自动文档

> PR 17 在 Section 2 的最后呈现，因其依赖 PR-1（pyproject.toml 的 docs 依赖组）且属于"外围"工作。Group E（ADR）只含 PR 11。

```yaml
# mkdocs.yml
site_name: Shenbi
theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - search.suggest
    - content.code.copy
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true
            show_signature_annotations: true
            separate_signature: true
            show_root_heading: true
nav:
  - Home: index.md
  - Architecture: architecture.md
  - ADRs: adr/
  - API: api/
```

### Group F: 重构（PR 12-13）

#### PR 12: validate-gate.py 机械拆分 + 切法 D 改善

Q1=D（机械拆分 + 所有"不依赖 P0"的语义改善）。

物理拆分到 tests/gates/。同时改善（无需 P0；structlog 已由 PR9 完成）：
- 用 typed exceptions 替代字符串返回
- 加完整 type hints（PEP 484）
- 移除死代码
- 加 docstring（Google style）
- 统一 G4 函数签名 `(project_dir, file_paths, round_dir)`
- 提取共享 utility
- 拆分长函数（> 50 行的拆）

`tests/validate-gate.py` 退化为 ~30 行 shim。

依赖 P0 的部分（Pydantic schemas、registry 路径解析）留在 P2。

#### PR 13: dispatch-subagent.sh → Python 重写

Q1=D 不改业务（行为完全一致）。Shell wrapper 保留 ~10 行（向后兼容）。

```
tests/dispatch-subagent.sh         # CLI shim (~10 行)
tests/dispatcher/
  __init__.py
  cli.py                           # argparse
  executor.py                      # 核心调度逻辑
```

### Group G: 清理（PR 14-15）

#### PR 14: phantom rounds 归档 + 每轮 README

Q2=D（归档 + 每轮 README + 索引）。

```
tests/rounds/archived/
  README.md                        # 索引（所有归档轮次状态表）
  round-001-2026-06-11/
    README.md                      # 本轮状态、已知问题、归档原因
  round-002-2026-06-11/
    README.md
  ...
  round-007-2026-06-14/
    README.md                      # 详细记录 3 个完成 skill 的得分
```

`archived/README.md` 含表格：Round | Date | Status | Known Issues。

每轮 README 含：Status、Disposal Reason、What's Useful Here、What's NOT Useful、Cross-references。

#### PR 15: 目录重命名 novel-output → skill-output

`novel-output` 误导（实际包含所有 skill 输出，不只 novel）。重命名 + 同步更新所有引用。

**已知引用清单**（基于 `grep "novel-output" tests/` 实际扫描，PR-15 必须全部更新）：

| 文件 | 行 | 引用形式 |
|------|---|---------|
| `tests/update-progress.py` | L104 | `"novel-output"` 在 subdir list |
| `tests/dispatch-subagent.sh` | L51, L98 | `${ROUND_DIR}/novel-output/${SKILL}` |
| `tests/validate-gate.py` | L288, L413-414, L424, L431, L441 | `PROJECT / "novel-output"` 路径解析 |
| `tests/validate-gate.py` | L1683, L1685 | `proj_dir.name != "novel-output"` 路径检测 |
| `tests/validate-gate.py` | L3405, L3421 | `rd / "novel-output"` + `"novel-output/ not found"` |
| `tests/round-exec.sh` | L33, L87 | `novel-output` 在 mkdir 与 find |

**注意**：PR-12 (validate-gate.py 拆分) 与 PR-15 (rename) 有依赖关系。PR-15 必须在 PR-12 之后，否则路径字符串分散在 `tests/gates/` 多个文件，rename 工作量爆炸。Section 6 PR 顺序表已正确反映此依赖（PR-15 依赖 PR-12 完成）。

**重命名策略**：使用 `git mv`（保留历史），同时全文替换字符串 `novel-output` → `skill-output`。

**回滚预案**：若 PR-15 引入未发现的引用断裂（如外部脚本依赖 `novel-output` 路径），可在 24 小时内 revert。所有引用更新都在单一 PR，revert 干净。

### Group H: 安全与性能（PR 16）

#### PR 16: pytest-benchmark + pip-audit + SBOM

- pytest-benchmark：每个核心函数一个 benchmark 测试。回归 > 10% 报警。
- pip-audit：CI 跑漏洞扫描。
- cyclonedx-bom：生成 SBOM（CycloneDX 格式）。

### 关键决策一览

| 决策点 | 选择 |
|--------|------|
| 包管理器 | uv |
| Linter | ruff (strict) |
| Formatter | ruff format |
| 类型检查 | mypy + basedpyright (双重，均纯 Python) |
| 测试框架 | pytest + 8 插件（cov / xdist / asyncio / timeout / benchmark / hypothesis / ordering / action-validator）|
| 覆盖率门槛 | 90% line（pytest-cov 内置）+ 80% branch（自写测试强制） |
| 日志 | structlog (JSON + console) |
| CI 平台 | GitHub Actions（3 个 workflow 文件：ci / security / docs） |
| 文档 | mkdocs-material |
| ADR 格式 | Nygard |
| Python 版本 | 3.11 + 3.12 matrix |
| 单测试超时 | 60s |
| Coverage 报告 | term + html + xml |
| CI YAML 校验 | action-validator + yamllint |
| 依赖更新 | Renovate（自动 PR）|

## Section 3: Data Flow

### 3.1 开发生命周期

```
Developer → Edit → git add
                      ↓
                  pre-commit hooks
                  (ruff / mypy / basedpyright / check-yaml / detect-private-key)
                      ↓ (若失败，回到 edit)
                  git commit
                      ↓
                  git push
                      ↓
                  GitHub Actions CI
                  (quality / security / docs jobs)
                      ↓ (若失败，回到 edit)
                  Open PR → Reviewer review → Merge to main
                      ↓
                  Deploy docs to GH Pages
```

### 3.2 日志流（structlog）

```
Tool execution
    ↓
get_logger(name).bind(context)
    ↓
log.info("event_name", **fields)
    ↓
structlog processor chain
(merge_contextvars → add_log_level → TimeStamper → StackInfoRenderer → format_exc_info → Renderer)
    ↓
Output to stderr (JSON or Console format)
```

JSON 格式（生产）：
```json
{"event":"dispatch_start","skill":"shenbi-worldbuilding","level":"info",
 "timestamp":"2026-06-14T10:00:00Z","agent_id":"abc123"}
```

Console 格式（dev 默认）：
```
2026-06-14 10:00:00 [info     ] dispatch_start
  skill=shenbi-worldbuilding agent_id=abc123
```

### 3.3 异常传播

```
Tool execution (任何深度)
    ↓ raise typed exception
ShenbiError 子类 (携带 context)
    ↓
CLI boundary catch
    ↓
Log exception (structlog.exception)
Translate to user message
Exit (0/1/2/3/4/5)
```

Exit code 约定：

| Code | 类别 | 含义 |
|------|------|------|
| 0 | Success | 操作完成 |
| 1 | User error | gate FAIL / 测试失败 / 覆盖率不足 |
| 2 | Framework error | registry stale / schema 错 / 迁移失败 |
| 3 | Unexpected | 未捕获异常 |
| 4 | Timeout | 操作超时 |
| 5 | Skipped | 显式 skip |

### 3.4 Gate 执行流（refactor 后）

```
tests/validate-gate.py CLI 入口 (shim, ~30 行)
    ↓
tests/gates/cli.py:main()
    ↓ parse_args, configure_logging
    ↓ route by gate name
gates.g0.run() / gates.g1.run() / ... / gates.g7.run()
    ↓
GateResult dataclass (gate / status / checks / must_fix / blocked_action)
    ↓
serialize to JSON (向后兼容)
write gate marker (if PASS)
print to stdout, exit 0 | 1
```

### 3.5 Dispatch 流（Python rewrite 后）

```
tests/dispatch-subagent.sh (shim, ~10 行)
    ↓ exec python3 -m tests.dispatcher.cli "$@"
tests/dispatcher/cli.py:main()
    ↓ parse_args, configure_logging
tests/dispatcher/executor.py:dispatch_scoring()
    ↓
    1. resolve input/output files
    2. validate G1
    3. validate G2
    4. detect dispatch mode (codex / codex-api / internal)
    5. spawn sub-agent
    6. parse scores JSON
    7. compute final score (scoring.py)
    8. update progress (update-progress.py)
    9. return DispatchResult
```

### 3.6 测试执行流（pytest）

```
pytest invocation
    ↓
load conftest.py (global fixtures)
    ↓
discover tests (testpaths = tests/{unit,integration,property,benchmark})
    ↓
run tests in parallel (pytest-xdist -n=auto)
    ↓ each test: timeout (60s unit / 300s property), acquire fixtures, run, capture, collect coverage
    Hypothesis tests: 1000 runs each (CI profile)
    ↓
aggregate coverage
    ↓ check --cov-fail-under=90
generate reports (term/html/xml)
    ↓
exit 0 | 1 | 2 | 5
```

## Section 4: Error Handling

### 4.1 异常层级

```
ShenbiError (基类)
├── FrameworkError (框架基础设施问题)
│   ├── RegistryError
│   │   ├── RegistryStaleError
│   │   ├── RegistryMissingError
│   │   └── RegistryCorruptError
│   ├── SchemaValidationError
│   ├── DefectApplicationError
│   ├── MigrationError
│   ├── DispatcherError
│   │   ├── SubAgentTimeoutError
│   │   ├── SubAgentProtocolError
│   │   └── SubAgentUnavailable
│   └── ConfigurationError
├── IntegrityError
│   └── ToolTamperError
├── GateError
│   └── GateMarkerMissingError
└── ScoringError
    └── ScoringRejectError
```

### 4.2 异常类统一接口

```python
class ShenbiError(Exception):
    """Base for all Shenbi errors."""
    
    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        **context: Any,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.context = context
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for failure catalog and structured logging."""
        return {
            "error_class": type(self).__name__,
            "message": self.message,
            "context": self.context,
            "cause_class": type(self.cause).__name__ if self.cause else None,
            "cause_message": str(self.cause) if self.cause else None,
        }
```

### 4.3 错误转换（boundary translation）

内部 raise typed exceptions。外部边界 translate to JSON / 用户消息。

```python
# tests/gates/cli.py
def main() -> int:
    try:
        result = run_gate(args)
        print(result.to_json())
        return 0 if result.status == "PASS" else 1
    except GateError as e:
        log.warning("gate_failed", **e.to_dict())
        print(json.dumps(_gate_error_to_json(e), ensure_ascii=False, indent=2))
        return 1
    except ShenbiError as e:
        log.exception("framework_error", **e.to_dict())
        print(f"Framework error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        log.exception("unexpected_error")
        return 3
```

### 4.4 用户友好的错误指引

每种错误类对应 ErrorGuidance（explanation / action / doc_url）：

```python
ERROR_GUIDANCE: dict[str, ErrorGuidance] = {
    "RegistryStaleError": ErrorGuidance(
        explanation="Source files have been modified since registry.lock.json was last built.",
        action="Run: python3 tests/build_registry.py\nThen commit the updated lockfile.",
        doc_url="docs/registry.md#stale-lockfile",
    ),
    # ... 完整 catalog
}
```

CLI 边界展示 guidance：错误信息 + Explanation + Suggested action + Documentation link。

### 4.5 自动恢复策略

P-1 定义接口，不接入主流程（P3 实施）：

```python
class RecoveryStrategy(Enum):
    NONE = "none"
    AUTO_RETRY = "auto_retry"
    AUTO_REBUILD = "auto_rebuild"
    HALT = "halt"

RECOVERY_STRATEGIES: dict[str, RecoveryStrategy] = {
    "RegistryStaleError": RecoveryStrategy.AUTO_REBUILD,
    "RegistryMissingError": RecoveryStrategy.AUTO_REBUILD,
    "GateMarkerMissingError": RecoveryStrategy.NONE,
    "SubAgentTimeoutError": RecoveryStrategy.AUTO_RETRY,
    "ToolTamperError": RecoveryStrategy.HALT,
    # ...
}
```

### 4.6 P3 failure catalog 预留接口

所有 ShenbiError 实例都具备 `to_dict()` 与必要 context。P3 可直接消费，无需额外适配。

### 4.7 异常 vs 字符串返回的兼容策略

1. **内部代码**：raise typed exceptions
2. **Gate 函数返回**：`GateResult` dataclass
3. **CLI 边界**：translate GateResult / exception → JSON 字符串
4. **向后兼容**：JSON 字符串格式与现有完全一致

外部消费者（dispatch-subagent.sh / scoring.py / phase-runner.py）看到的 JSON 字符串不变。

## Section 5: Testing

### 5.1 测试金字塔

```
            Property (Hypothesis)    ~5%  (~50 tests)
           Benchmark                 ~2%  (~20 tests)
          Integration                ~15% (~150 tests)
         Unit                        ~78% (~780 tests)
```

P-1 内只写测试基础设施本身所需的测试（约 470 tests）。P0-P6 各阶段在自己范围内加测试。

### 5.2 P-1 内必写的测试

- A. 测试框架自身（bootstrap tests）
- B. 类型检查与 lint 自身（subprocess 调用 ruff/mypy/basedpyright）
- C. 异常类与 logging
- D. Gate 拆分等价性测试（baseline 对比）
- E. Dispatcher 重写等价性测试
- F. Round 归档验证
- G. 工具哈希锁定（P-1 时 skipped，P0 后激活）
- H. property-based 测试基础设施
- I. benchmark 基础设施
- J. 文档测试（ADR + mkdocs）
- K. CI workflow 验证

### 5.3 测试覆盖率目标

| 模块 | 行覆盖率 | 分支覆盖率 |
|------|---------|----------|
| `tests/exceptions.py` | 100% | 100% |
| `tests/logging.py` | 95% | 90% |
| `tests/gates/shared.py` | 95% | 90% |
| `tests/gates/g0.py` - `g7.py` | 90% | 85% |
| `tests/gates/g4/<skill>.py` | 85% | 80% |
| `tests/dispatcher/` | 90% | 85% |
| 整体加权平均 | **≥ 90%** | **≥ 80%** |

未达标 → CI 失败。

### 5.4 Property-based 测试配置

```python
# tests/conftest.py
from hypothesis import settings
settings.register_profile("ci", max_examples=1000, deadline=None)
settings.register_profile("dev", max_examples=100, deadline=200)
settings.register_profile("debug", max_examples=10, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
```

CI 跑 `--hypothesis-profile=ci`（1000 次），dev 默认 100 次。

### 5.5 Mutation testing（P-1 加成）

引入 mutmut。P-1 内运行 `mutmut run` 作为参考基线。P0-P6 阶段逐步提高 mutation score 门槛。

```toml
[tool.mutmut]
paths_to_mutate = ["tests/exceptions.py", "tests/logging.py", "tests/gates/shared.py"]
tests_dir = "tests/unit/"
do_not_mutate = ["tests/rounds/archived/**"]
```

### 5.6 测试执行命令

```bash
# 全套（CI）
pytest

# 仅 unit
pytest tests/unit/

# 跳过 slow
pytest -m "not slow"

# 跳过 benchmark
pytest -m "not benchmark"

# 仅 property-based，CI 强度
pytest -m property --hypothesis-profile=ci

# 并行
pytest -n 8

# 覆盖率报告
pytest --cov-report=html:tests/coverage
```

### 5.7 测试数据管理

```
tests/
  fixtures/                  # 测试 fixture 数据
    sample-novel.json
    sample-worldbuilding-output/
    sample-character-design-output/
  baselines/                 # 等价性测试的 baseline 输出
    gate-output-G0-worldbuilding.json
    gate-output-G4-worldbuilding.json
  conftest.py                # 全局 fixtures
  unit/
  integration/
  property/
  benchmark/
```

`baselines/` 由 `tests/regenerate-baselines.sh` 一次性生成（P-1 开始前）。

### 5.8 CI 测试矩阵

| 维度 | 值 |
|------|---|
| Python 版本 | 3.11, 3.12 |
| 操作系统 | ubuntu-latest, macos-latest |
| Hypothesis profile | ci (1000 examples) |
| Coverage threshold | 90% line / 80% branch |

每 PR 跑 4 个组合。Main 分支跑全套。

### 5.9 回归测试策略

P-1 完成后，未来 P0-P6 的 PR 必须：

1. 不降低现有覆盖率（CI 强制）
2. 不破坏 baseline 等价性（gate/dispatcher 输出对比）
3. 不引入新 ruff/mypy/basedpyright 违规
4. 不减少 ADR 数量
5. mutation score 不下降

### 5.10 P-1 测试工作量

- 写 conftest.py + sample tests：~50 tests，2 小时
- 改写 test_integrity.py 为 pytest：~150 tests，4 小时
- 异常类测试：~80 tests，3 小时
- logging 测试：~30 tests，2 小时
- gate 等价性测试：~60 tests（含 baseline 生成），4 小时
- dispatcher 等价性测试：~40 tests，3 小时
- round 归档验证：~10 tests，1 小时
- 文档 + CI workflow 测试：~30 tests，2 小时
- property/benchmark 基础设施：~20 tests，2 小时

**P-1 总测试数：~470 tests**，工时合计 23 小时（精确求和：2+4+3+2+4+3+1+2+2=23）。

## Section 6: Rollout Strategy

### PR 顺序（17 个原子 PR）

| # | PR | 依赖 | 内容 |
|---|----|------|------|
| 1 | pyproject.toml + uv.lock | — | 项目元数据 |
| 2 | ruff config + auto-fix | PR1 | Lint/format |
| 3 | mypy config | PR1 | Type check |
| 4 | basedpyright config | PR1 | Type check |
| 5 | pytest framework + sample | PR1 | Test infra |
| 6 | migrate test_integrity.py | PR5 | Test rewrite |
| 7 | GitHub Actions CI | PR2-6 | CI |
| 8 | pre-commit hooks | PR2-4 | Local hooks |
| 9 | structlog integration | PR1 | Logging |
| 10 | typed exceptions | PR1 | Error handling |
| 11 | ADR template + 9 ADRs | — | Docs |
| 12 | validate-gate.py split | PR5,9,10 | Refactor |
| 13 | dispatch-subagent.sh → Python | PR5,9,10 | Refactor |
| 14 | phantom rounds archive | — | Cleanup |
| 15 | rename novel-output → skill-output | PR12 | Cleanup |
| 16 | pytest-benchmark + pip-audit + SBOM | PR7 | Quality |
| 17 | mkdocs-material docs | PR1 | Docs |

每个 PR < 500 行 diff，独立可 revert，独立可 review。

### 验收标准

P-1 完成的标志：

1. ✅ 所有 17 个 PR merged to main
2. ✅ CI 全套通过（lint + type + test + coverage + security + docs）
3. ✅ Coverage ≥ 90% line / 80% branch
4. ✅ tests/rounds/archived/ 建立完整索引
5. ✅ ADR 0001-0009 全部 accepted
6. ✅ mutation score 基线建立（mutmut run 成功）
7. ✅ mkdocs build --strict 通过
8. ✅ 所有 print() 替换为 structlog
9. ✅ 所有 ad-hoc error returns 替换为 typed exceptions
10. ✅ validate-gate.py 拆分后 baseline 等价性测试全过
11. ✅ dispatch-subagent.sh → Python 后行为等价性测试全过

### 与 P0 的接口

P-1 完成后，P0 在此基线上构建：

```
P0 在 P-1 上加：
  - skills/<name>/meta.yaml
  - skills/<name>/schema/*.py（Pydantic，受 mypy/basedpyright 监督）
  - tests/tiers/registry.lock.json（受 pre-commit 自动 rebuild）
  - tests/build_registry.py / load_registry.py（已占位，P0 实现）
  - G0 加新检查（G0.L1 lockfile freshness）
```

P0 完成后，P1-P6 在新基线上构建，每个阶段在 P-1 + P0 上**只加不改**。

## Section 7: Out of Scope

明确不在 P-1 范围内的工作：

| 项 | 责任 P 阶段 |
|---|------------|
| Pydantic schemas | P0 |
| Registry / lockfile 机制 | P0 |
| G4 业务逻辑重写（用 schemas 替代 regex） | P2 |
| Failure catalog 实现 | P3 |
| Sub-agent dispatch（替代 codex） | P4 |
| Vertical slice 协议改造 | P5 |
| Token/context 优化 | P6 |
| Protocol 文档（command-to-give.md）改造 | P5 |
| 任何业务逻辑变更 | — |

## Section 8: Risks & Mitigations

### Risk 1: 行为等价性回归

**风险**：validate-gate.py 拆分 + 改善后，gate 输出可能微妙变化，破坏现有评分 pipeline。

**缓解**：
- PR-12 前生成所有 gate baseline
- PR-12 后跑等价性测试，任何 mismatch 必须修复
- PR-13 同理

### Risk 2: uv 不可用

**风险**：开发者环境无 uv。

**缓解**：
- uv 是单文件二进制，安装简单
- 提供 fallback：`pip install -e .[dev]` 也可工作（但无 lock）
- CI 用 setup-uv action 保证可用

### Risk 3: Coverage 90% 门槛过高

**风险**：现有代码覆盖率不达 90%，CI 一直红。

**缓解**：
- PR-5 后跑 coverage，得到实际基线
- 若 < 90%，分阶段提高门槛：80% → 85% → 90%（每 PR +5%）
- 最终达到 90% 后 lock 住

### Risk 4: mypy/basedpyright 在现有代码上报大量错误

**风险**：3900 行 validate-gate.py 加 strict 后可能数百错误。

**缓解**：
- PR-3/4 用 per-module overrides 逐步收紧
- `tests.gates.g4.*` 在 P-1 时 disallow_untyped_defs = false，P2 改完移除
- 其他模块直接 strict，但 PR 内一次性 fix 所有错误

### Risk 5: 17 个 PR 周期太长

**风险**：每个 PR review + merge 平均 2 天，34 天周期。

**缓解**：
- 无依赖的 PR 并行 review（如 PR-11 ADR 与 PR-14 phantom rounds）
- 部分 PR 由 AI 自动 review（ruff/mypy/basedpyright 已是机器检查，review 重点是设计决策）
- 实际人工 review 重点：PR-12 (gate split), PR-13 (dispatcher rewrite), PR-11 (ADRs), PR-9 (structlog), PR-10 (exceptions)

### Risk 6: basedpyright 与 pyright 行为差异

**风险**：basedpyright 是 pyright 的 fork，默认行为略有不同（如更严格的类型推断）。CI 跑 basedpyright 可能报 pyright 不报的错误，反之亦然。

**缓解**：
- 业界经验：basedpyright 通常比 pyright 更严格，向上兼容
- 若发现误报，per-module 调整（pyproject.toml 的 `[tool.basedpyright.overrides]`）
- 长期监控 basedpyright 上游同步频率（每月一次），与 pyright 保持版本对应

### Risk 7: GitHub Actions 矩阵成本

**风险**：matrix testing（2 OS × 2 Python × 1 job = 4 并发 run）每 PR 4 个 run，付费账号 $0.008/min × ~10 min/run × 4 = $0.32/PR。每 PR 30+ min wall time。

**缓解**：
- 公共仓库免费配额充足（2,000 分钟/月）
- 私有仓库成本可控（预算 < $50/月）
- 长期若需压缩成本：去掉 macos-latest（Linux only），保留双 Python 版本

### Risk 8: PR-12 validate-gate.py 拆分后行为微变

**风险**：Q1=D 包括"非 P0 依赖的语义改善"（type hints、exceptions、长函数拆分）。即使 baseline 等价测试通过，也可能漏掉未在 baseline 中的输入场景。

**缓解**：
- baseline 覆盖所有 59 skill × 3 test type = 177 个 G4 调用组合
- 对 G0-G7 每个 gate 至少 5 个不同输入的 baseline
- 总 baseline 数 ≥ 200，覆盖绝大多数真实调用
- 残余风险（< 0.1%）：手动 review PR-12 的非等价改动列表

### Risk 9: Renovate/Dependabot 自动 PR 噪音

**风险**：依赖更新自动 PR 太多会淹没功能 PR（如 ruff 升级、pydantic 升级）。

**缓解**：
- 配置 Renovate schedule：weekends only / monthly
- minor 与 patch 升级自动 merge（CI 全过时）
- major 升级走人工 review
- 配置 `renovate.json` group 规则（如所有 ruff 系列一起升级）

## Appendix A: 关键文件清单

```
shenbi/
├── .github/workflows/
│   ├── ci.yml
│   ├── security.yml
│   └── docs.yml
├── .pre-commit-config.yaml
├── .gitignore
├── pyproject.toml
├── uv.lock
├── mkdocs.yml
├── renovate.json
├── docs/
│   └── adr/
│       ├── 0000-template.md
│       ├── 0001-pyproject-uv.md
│       ├── 0002-ruff-strict.md
│       ├── 0003-mypy-pyright-dual.md
│       ├── 0004-pytest-framework.md
│       ├── 0005-structlog.md
│       ├── 0006-typed-exceptions.md
│       ├── 0007-adr-process.md
│       ├── 0008-validate-gate-modularization.md
│       └── 0009-dispatcher-python-rewrite.md
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── exceptions.py
    ├── logging.py
    ├── error_guidance.py
    ├── recovery.py
    ├── validate-gate.py                 (CLI shim)
    ├── dispatch-subagent.sh              (CLI shim)
    ├── gates/
    │   ├── __init__.py
    │   ├── shared.py
    │   ├── cli.py
    │   ├── g0.py
    │   ├── g1.py
    │   ├── g2.py
    │   ├── g3.py
    │   ├── g4/
    │   │   ├── __init__.py
    │   │   ├── generic.py
    │   │   ├── worldbuilding.py
    │   │   ├── character_design.py
    │   │   ├── chapter_drafting.py
    │   │   └── ... (一个 skill 一个文件)
    │   ├── g5.py
    │   ├── g6.py
    │   └── g7.py
    ├── dispatcher/
    │   ├── __init__.py
    │   ├── cli.py
    │   └── executor.py
    ├── build_registry.py                (占位)
    ├── load_registry.py                 (占位)
    ├── rounds/
    │   ├── round-000-TEMPLATE/
    │   └── archived/
    │       ├── README.md
    │       ├── round-001-2026-06-11/README.md
    │       ├── round-002-2026-06-11/README.md
    │       ├── round-003-2026-06-11/README.md
    │       ├── round-004-2026-06-12/README.md
    │       ├── round-005-2026-06-12/README.md
    │       ├── round-006-2026-06-13/README.md
    │       └── round-007-2026-06-14/README.md
    ├── unit/                            (~780 tests 最终，PR-5 创建空目录)
    │   └── test_coverage_thresholds.py  (PR-5 创建，@pytest.mark.last)
    ├── integration/                     (~150 tests 最终，PR-5 创建空目录)
    ├── property/                        (~50 tests 最终，PR-5 创建空目录)
    ├── benchmark/                       (~20 tests 最终，PR-5 创建空目录)
    ├── fixtures/
    │   ├── sample-novel.json
    │   ├── sample-worldbuilding-output/
    │   └── sample-character-design-output/
    ├── baselines/
    │   ├── gate-output-G0.json
    │   ├── gate-output-G4-worldbuilding.json
    │   └── ...
    └── coverage/                        (gitignored)
```

## References

- [PEP 621: pyproject.toml](https://peps.python.org/pep-0621/)
- [uv documentation](https://docs.astral.sh/uv/)
- [ruff documentation](https://docs.astral.sh/ruff/)
- [mypy strict mode](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict)
- [pyright strict mode](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)
- [pytest documentation](https://docs.pytest.org/)
- [Hypothesis documentation](https://hypothesis.readthedocs.io/)
- [structlog documentation](https://www.structlog.org/)
- [mkdocs-material](https://squidfunk.github.io/mkdocs-material/)
- [Michael Nygard ADR template](https://github.com/joelparkerhenderson/architecture-decision-record)
- [Martin Fowler: Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html)
- [Google: Small PRs guideline](https://google.github.io/eng-practices/review/developer/small-cls.html)
