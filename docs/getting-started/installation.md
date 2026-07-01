# 安装 / Installation

## 前提条件 / Prerequisites

| 工具 / Tool | 最低版本 / Minimum Version | 说明 / Notes |
|-------------|---------------------------|-------------|
| Python | 3.11+ | `pyproject.toml` 声明 `requires-python >= 3.11` |
| uv | 0.5+ | 包管理器（必需）— [安装指南 / Install Guide](https://docs.astral.sh/uv/) |
| just | 最新 / latest | 任务运行器 / Task runner — [macOS](https://formulae.brew.sh/formula/just) `brew install just` / [其他 / Other](https://github.com/casey/just/releases) |

> **注意：** uv 是必需的，因为 justfile 的所有命令都通过 `uv run` 执行。
>
> **Note:** uv is required because the justfile uses `uv run` for every recipe.

## 安装步骤 / Installation Steps

### 1. 克隆仓库 / Clone the repository

```bash
git clone https://github.com/ThomasChangX/shenbi.git
cd shenbi
```

### 2. 安装依赖 / Install dependencies

```bash
uv sync --group dev
```

这会安装框架运行时依赖和开发依赖（ruff, mypy, pytest 等）。

This installs framework runtime dependencies and development dependencies (ruff, mypy, pytest, etc.).

### 3. 安装文档依赖（可选） / Install docs dependencies (optional)

```bash
uv sync --group docs
```

### 4. 安装 pre-commit hooks / Install pre-commit hooks

```bash
uv run pre-commit install
```

## 验证安装 / Verify Installation

### 运行完整检查 / Run full checks

```bash
just check
```

如果所有检查通过（ruff、mypy、pytest），安装成功。

If all checks pass (ruff, mypy, pytest), the installation is successful.

### 运行快速测试 / Run quick tests

```bash
just test
```

### 构建文档站点 / Build docs site

```bash
just docs
```

这会在 `http://127.0.0.1:8000` 启动本地文档服务器。

This starts a local docs server at `http://127.0.0.1:8000`.

## 常用命令 / Common Commands

| 命令 / Command | 作用 / Purpose |
|----------------|---------------|
| `just check` | 运行所有 CI 检查 / Run all CI checks |
| `just test` | 快速单元测试 / Fast unit tests only |
| `just fix` | 自动修复 lint 和格式 / Auto-fix lint and format |
| `just docs` | 启动文档服务器 / Start docs server |
| `just --list` | 列出所有命令 / List all commands |

## 测试数据说明 / Test Data Note

`tests/fixtures/` 包含真实的技能输出（非手工编写的 mock，遵循 G0.9 规则）。轮次目录位于 `tests/rounds/`。这些是测试框架使用的，正常写小说不需要。

`tests/fixtures/` contains real skill outputs (not hand-crafted mocks, per G0.9). Round directories live under `tests/rounds/`. These are used by the testing framework, not required for normal novel writing.
