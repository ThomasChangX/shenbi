# 契约单源架构 - 支柱六（文档派生 + AST 纯度 lint + CapabilityFS）实施计划 v1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 AST 纯度 lint（禁 `src/shenbi/` FS 变更原语，除 allowlist）、文档派生生成器（从契约模型生成「可自动检查」表，CI 拒绝手改）、评分标尺显式声明（score-arc/stratum/volume 聚合公式 + PASS_THRESHOLD）、以及进程内 CapabilityFS 只读垫片（测试时阻断写操作）。

**Architecture:** 纯度 lint 是独立 AST 脚本（镜像现有 `tools/lint_no_forbid_with_computed_field.py` 模式），扫描 `src/shenbi/*.py` 中的 FS 变更 AST 节点。Allowlist 分两层：永久（safe_write.py + trace/writer.py，有合法直接写理由）和过渡（14 个尚未迁移到 safe_write 的文件，由测试断言无死条目）。文档派生生成器在 `tools/`，读契约模型 `@computed_field` + 模块级阈值常量，渲染 sentinel 分隔的 markdown 区块；CI 跑生成 + `git diff` 拒绝手改。评分标尺用 `_scoring_base.py` 共享 Pydantic 模型显式声明公式。CapabilityFS（`src/shenbi/capability_fs.py`，**pillar5 产物**）是进程内只读 FS 句柄：`CapabilityFS(allow_root: Path)` 实例，读经沙箱允许，写一律 PermissionError。本计划**不重建**该模块——Task 7 只为它写测试。

**Tech Stack:** Python 3.11+，Pydantic v2.5+（已依赖），mypy strict（已 CI），pytest+hypothesis（已依赖），ast+pathlib。

**关联 spec:** [../specs/2026-06-29-contract-single-source-design.md](../specs/2026-06-29-contract-single-source-design.md) v5.2 支柱六 + 成功判据 4（纯度强制，allowlist 偏差：2 永久 + 14 过渡）。

**v5 修订（round-4 审核 8→目标 9+，Meitner 高精度 reproduced）：** Important：transitional allowlist 修正（删 gates/g7.py——pillar2 执行后 G7 已纯化；加 audit/record.py——pillar4-tierB 执行后新增 append-only ledger）。Minor：加 tier_advance_eligible hard_binary 回归测试；判据 4 allowlist 偏差声明（永久 2 + 过渡 14，非 spec「仅 safe_write」）。

**前置依赖:**
- **支柱一**已落地：`src/shenbi/contracts/` 包含 `enums.py`、`base.py`、`registry.py`（REGISTRY 自动发现）、`skills/foreshadowing_resolve.py`。本计划在 `contracts/skills/` 新增评分模型。
- **支柱二**（thresholds.py）：本计划的 `_scoring_base.py` 从 `contracts/thresholds.py` import `TEST_PASS`/`T1_PASS`（Kant I3 单一源）。pillar2 Task 1 创建此文件。
- **支柱五**（capability_fs.py）：Task 7 消费该模块，不重建（Kant C1 修复）。
- **支柱四 Tier A**（safe_write.py + trace/writer.py）：本计划的 allowlist 按文件名引用 safe_write.py 和 trace/writer.py。若 pillar 4 尚未执行（文件不存在），lint 仍正常工作——allowlist 条目对不存在的文件无影响（测试跳过不存在的条目）。trace/replay.py 和 trace/compaction.py（pillar 4 产物）也在过渡 allowlist 中。

**Allowlist 决策（已验证）：**
- **safe_write.py**（永久）：原子写原语本身（temp + os.replace + fsync + flock）。不 allowlist 它就会 flag 自己。
- **trace/writer.py**（永久）：TraceWriter 用 `.open("a")` 做 append-only 写入。safe_write 是 temp+replace（全文件替换），与 append-only 语义不兼容（append 需要 O(1) 追加 + 每行 fsync；safe_write 会 O(n) 读全文件再写回，且丢失 crash 时「除最后一行外全部保留」的语义）。因此 trace/writer.py 永久 allowlist。
- **trace/replay.py + trace/compaction.py**（过渡）：pillar 4 产物，直接写 trace.jsonl（截断撕裂行 / compaction 重写）。应迁移到 safe_write 或 trace 专用安全写（future work）。

## Global Constraints

- Python 3.11+；ast + pathlib + json；框架代码无 print()（用 structlog）。
- Pydantic v2.5+；含 `@computed_field` 的模型用 `model_config={"extra":"ignore"}`（N7）。
- mypy strict + ruff 必须 CI 干净。
- **覆盖率门（关键）：** `pyproject.toml` 设 `--cov=shenbi` + `fail_under=90`（已验证 pyproject.toml:322-349），因此任何**单文件/子集** `uv run pytest <path>` 都会因覆盖率不足退出码非零。本计划所有单文件 pytest 命令必须追加 `--no-cov`。覆盖率门只在全量 `uv run pytest -q` 时生效。下面各步为简洁省略 `--no-cov`，执行者一律按此规则补上。
- 纯度 lint 扫描根目录是 `src/shenbi/`（不是 `src/`），文件相对路径如 `gates/shared.py`。
- lint 脚本自身在 `tools/`，不被 lint 扫描。
- 文档生成器在 `tools/`，直接写 SKILL.md（build-time 工具，不受纯度 lint 约束）。
- 不修改现有 gate/skill 运行态行为。

## 文件结构

| 文件 | 责任 |
|---|---|
| `tools/lint_no_fs_mutation.py` | AST 纯度 lint：禁 src/shenbi/ FS 变更原语（除 allowlist） |
| `tests/unit/test_lint_no_fs_mutation.py` | lint 检测准确性测试（假阳/假阴）+ allowlist 诚实测试 |
| `src/shenbi/contracts/skills/_scoring_base.py` | 评分报告共享模型 + 聚合公式 + PASS_THRESHOLD（M3 修复） |
| `src/shenbi/contracts/skills/score_arc.py` | score-arc 契约（Report = ScoreReport） |
| `src/shenbi/contracts/skills/score_stratum.py` | score-stratum 契约 |
| `src/shenbi/contracts/skills/score_volume.py` | score-volume 契约 |
| `tests/unit/contracts/test_scoring_contracts.py` | 评分模型测试 |
| `tools/generate_autocheck_docs.py` | 文档派生：从契约模型生成「可自动检查」区块 |
| `tests/unit/test_generate_autocheck_docs.py` | 文档派生渲染 + 幂等 + 防篡改测试 |
| `src/shenbi/capability_fs.py` | **pillar5 产物（本计划不重建）**——Task 7 只加测试 |
| `tests/unit/test_capability_fs.py` | CapabilityFS 测试 |

---

### Task 1: AST 纯度 lint 脚本 + 检测准确性测试

**Files:** Create `tools/lint_no_fs_mutation.py`、`tests/unit/test_lint_no_fs_mutation.py`

**Interfaces:** Produces `lint_dir(root: Path) -> list[str]`、`_find_violations(tree, filepath) -> list[str]`、`PERMANENT_ALLOWLIST`、`TRANSITIONAL_ALLOWLIST`、`ALLOWED_FILES`。

**检测规则（AST）：**
- `.write_text()` / `.write_bytes()` / `.unlink()` -> 违规（Path 写/删方法）
- `.open(mode)` 或 builtin `open(file, mode)` 当 mode 含 `w`/`a`/`x` -> 违规
- `os.replace/rename/unlink/remove/rmdir/removedirs(...)` -> 违规
- `shutil.copy/copy2/copyfile/move/rmtree/copytree(...)` -> 违规
- **不 flag：** `.read_text()`、`.open()` / `.open("r")`（默认读）、`json.dumps()`、`json.dump()`（文件句柄来自已 flag 的 open）、`.mkdir()`（目录创建非文件突变）、动态 mode（非常量，保守不 flag）

**Allowlist（v1 亲手核对 src/shenbi/ 全部写原语）：**

永久 allowlist（合法直接写）：
- `safe_write.py`：原子写原语本身
- `trace/writer.py`：append-only，safe_write 不兼容

过渡 allowlist（尚未迁移到 safe_write；v1 grep 验证每个含违规）：
- `gates/shared.py`（marker_file.write_text）、`gates/g1.py`（shutil.copy2）
- `phase_runner.py`（state_file.write_text）
- `plugins/generate.py`（output_path.write_text）
- `dispatcher/modes/internal.py`（prompt_file.write_text）、`dispatcher/modes/codex.py`（scores_file.write_text）
- `skill_utils/drift_detection/compute_drift.py`（audit_path.open("a")）、`skill_utils/style_learning/compute_stats.py`（Path.write_text）
- `sync_contracts.py`（skill_md.write_text, path.write_text）、`update_progress.py`（pp.write_text）
- `summarize_round.py`（open(summary_path, "w")）
- `trace/replay.py`（pillar 4：path.write_text 截断）、`trace/compaction.py`（pillar 4：path.write_text 重写）
- `audit/record.py`（ledger.open("a")，pillar 4-tierB 产物）

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_lint_no_fs_mutation.py
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from lint_no_fs_mutation import (  # noqa: E402
    ALLOWED_FILES,
    PERMANENT_ALLOWLIST,
    TRANSITIONAL_ALLOWLIST,
    _find_violations,
    lint_dir,
)

SRC = REPO / "src" / "shenbi"


# --- Detection: mutation primitives MUST be flagged ---

def test_flags_write_text(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.write_text('x')\n", encoding="utf-8")
    vs = lint_dir(tmp_path)
    assert len(vs) == 1
    assert "write_text" in vs[0]


def test_flags_write_bytes(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.write_bytes(b'x')\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


def test_flags_unlink(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.unlink()\n", encoding="utf-8")
    vs = lint_dir(tmp_path)
    assert len(vs) == 1
    assert "unlink" in vs[0]


def test_flags_path_open_write(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.open('w')\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


def test_flags_path_open_append(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("p.open('a')\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


def test_flags_builtin_open_write(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("open(p, 'w')\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


def test_flags_os_replace(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("os.replace(a, b)\n", encoding="utf-8")
    vs = lint_dir(tmp_path)
    assert len(vs) == 1
    assert "os.replace" in vs[0]


def test_flags_shutil_copy(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("shutil.copy2(a, b)\n", encoding="utf-8")
    vs = lint_dir(tmp_path)
    assert len(vs) == 1
    assert "shutil" in vs[0]


def test_flags_nested_open_in_json_dump(tmp_path: Path) -> None:
    """json.dump(data, open(path, 'w')) -- the nested open is caught."""
    f = tmp_path / "bad.py"
    f.write_text("json.dump(data, open(path, 'w'))\n", encoding="utf-8")
    assert len(lint_dir(tmp_path)) == 1


# --- No false positives: reads and safe operations MUST NOT be flagged ---

def test_allows_read_text(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("p.read_text()\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_open_read_default(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("p.open()\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_open_read_explicit(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("p.open('r')\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_builtin_open_read(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("open(p)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_json_dumps(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("json.dumps(x)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_os_path_exists(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("os.path.exists(p)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_mkdir(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("p.mkdir(parents=True)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []


def test_allows_dynamic_mode_open(tmp_path: Path) -> None:
    """Dynamic mode (not a constant) is not flagged (conservative)."""
    f = tmp_path / "ok.py"
    f.write_text("open(p, mode)\n", encoding="utf-8")
    assert lint_dir(tmp_path) == []
```

- [ ] **Step 2: Run -> fails** (ModuleNotFoundError)

`uv run pytest tests/unit/test_lint_no_fs_mutation.py -v --no-cov`

- [ ] **Step 3: Implement lint script**

```python
# tools/lint_no_fs_mutation.py
#!/usr/bin/env python3
"""Purity lint: forbid FS-mutation primitives in src/shenbi/ except allowlisted files.

Usage: python tools/lint_no_fs_mutation.py <root_dir>
exit 0 = pass; exit 1 = violations found.

Allowlist rationale:
  - safe_write.py: the atomic-write entry point (temp + os.replace + fsync).
  - trace/writer.py: TraceWriter does true append-only writes (.open("a") +
    per-line fsync). safe_write is temp+replace (full-file), incompatible.

Transitional allowlist: files not yet migrated to safe_write. Each entry is
verified by a test to contain actual violations (no dead entries). This list
MUST shrink as files migrate.

NOT detected (known limitations):
  - `from os import replace; replace(...)` (import-aliased calls; requires
    import tracking, out of scope for AST lint).
  - Dynamic open modes (non-constant mode arg; conservative skip).
  - os.open (low-level fd-based; only used in allowlisted safe_write).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# --- Allowlist ---

PERMANENT_ALLOWLIST: frozenset[str] = frozenset({
    "safe_write.py",
    "trace/writer.py",
})

TRANSITIONAL_ALLOWLIST: frozenset[str] = frozenset({
    "gates/shared.py",
    "gates/g1.py",
    "phase_runner.py",
    "plugins/generate.py",
    "dispatcher/modes/internal.py",
    "dispatcher/modes/codex.py",
    "skill_utils/drift_detection/compute_drift.py",
    "skill_utils/style_learning/compute_stats.py",
    "sync_contracts.py",
    "update_progress.py",
    "summarize_round.py",
    "trace/replay.py",
    "trace/compaction.py",
    "audit/record.py",  # Meitner v5: pillar4-tierB append-only ledger
})

ALLOWED_FILES: frozenset[str] = PERMANENT_ALLOWLIST | TRANSITIONAL_ALLOWLIST

# --- Detection constants ---

_OS_MUTATIONS = frozenset({
    "replace", "rename", "unlink", "remove", "rmdir", "removedirs",
})

_SHUTIL_MUTATIONS = frozenset({
    "copy", "copy2", "copyfile", "move", "rmtree", "copytree",
})

_PATH_WRITE_METHODS = frozenset({"write_text", "write_bytes", "unlink"})

_WRITE_CHARS = frozenset("wax")


def _is_write_mode(mode_arg: ast.expr | None) -> bool:
    """True if a mode arg is a string constant containing w/a/x."""
    if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
        return bool(_WRITE_CHARS & set(mode_arg.value))
    return False


def _extract_mode(call: ast.Call, is_method: bool) -> ast.expr | None:
    """Extract the mode argument from an open() call.

    Path.open(mode): mode is args[0].
    builtin open(file, mode): mode is args[1].
    Keyword 'mode=' checked for both.
    """
    for kw in call.keywords:
        if kw.arg == "mode":
            return kw.value
    idx = 0 if is_method else 1
    if len(call.args) > idx:
        return call.args[idx]
    return None


def _find_violations(tree: ast.Module, filepath: Path) -> list[str]:
    """Walk AST, return violation messages for FS-mutation primitives."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func

        if isinstance(func, ast.Attribute):
            attr = func.attr

            # .write_text() / .write_bytes() / .unlink()
            if attr in _PATH_WRITE_METHODS:
                violations.append(
                    f"{filepath}:{node.lineno}: forbidden FS-mutation: .{attr}()"
                )
                continue

            # .open(mode) with write/append mode
            if attr == "open":
                if _is_write_mode(_extract_mode(node, is_method=True)):
                    violations.append(
                        f"{filepath}:{node.lineno}: forbidden FS-mutation: "
                        f".open() in write/append mode"
                    )
                continue

            # os.<mutation> or shutil.<mutation>
            if isinstance(func.value, ast.Name):
                mod = func.value.id
                if mod == "os" and attr in _OS_MUTATIONS:
                    violations.append(
                        f"{filepath}:{node.lineno}: forbidden FS-mutation: os.{attr}()"
                    )
                elif mod == "shutil" and attr in _SHUTIL_MUTATIONS:
                    violations.append(
                        f"{filepath}:{node.lineno}: forbidden FS-mutation: shutil.{attr}()"
                    )

        # builtin open(file, mode)
        elif isinstance(func, ast.Name) and func.id == "open":
            if _is_write_mode(_extract_mode(node, is_method=False)):
                violations.append(
                    f"{filepath}:{node.lineno}: forbidden FS-mutation: "
                    f"open() in write/append mode"
                )

    return violations


def lint_dir(root: Path) -> list[str]:
    """Lint all .py under root, skipping allowlisted files.

    File identity is the posix relative path from root (e.g. 'gates/shared.py').
    """
    all_violations: list[str] = []
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root).as_posix()
        if rel in ALLOWED_FILES:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        all_violations.extend(_find_violations(tree, py))
    return all_violations


EXPECTED_ARGS = 2


def main() -> int:
    if len(sys.argv) != EXPECTED_ARGS:
        print("usage: lint_no_fs_mutation.py <path>", file=sys.stderr)
        return 2
    vs = lint_dir(Path(sys.argv[1]))
    for v in vs:
        print(v, file=sys.stderr)
    return 1 if vs else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run -> passes** (17 detection tests)

`uv run pytest tests/unit/test_lint_no_fs_mutation.py -v --no-cov`

- [ ] **Step 5: mypy + ruff**

`uv run mypy tools/lint_no_fs_mutation.py && uv run ruff check tools/lint_no_fs_mutation.py tests/unit/test_lint_no_fs_mutation.py` -> Success / All passed

- [ ] **Step 6: Commit**

```bash
git add tools/lint_no_fs_mutation.py tests/unit/test_lint_no_fs_mutation.py
git commit -m "feat(lint): add AST purity lint -- forbid FS-mutation in src/shenbi/"
```

---

### Task 2: Allowlist 诚实测试（lint 通过真实 src/shenbi/ + 无死条目）

**Files:** Modify `tests/unit/test_lint_no_fs_mutation.py`（追加 allowlist 测试）

**Interfaces:** Consumes `lint_dir`、`_find_violations`、`ALLOWED_FILES`。无新产出。

- [ ] **Step 1: Append allowlist tests**

追加到 `tests/unit/test_lint_no_fs_mutation.py`：

```python
# --- Allowlist honesty tests ---


def test_lint_passes_on_real_src() -> None:
    """Lint passes on the actual src/shenbi/ tree (all violators allowlisted)."""
    assert lint_dir(SRC) == [], (
        "New unallowlisted FS-mutation found. Either route through safe_write "
        "or add to TRANSITIONAL_ALLOWLIST (and verify the entry)."
    )


def test_every_allowlisted_file_has_violations() -> None:
    """Each existing allowlisted file MUST contain actual FS-mutation primitives.

    Files not yet created (e.g. safe_write.py pre-pillar-4) are skipped.
    A file in the allowlist with zero violations is a dead entry -- remove it.
    """
    for rel in sorted(ALLOWED_FILES):
        f = SRC / rel
        if not f.exists():
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        vs = _find_violations(tree, f)
        assert vs, (
            f"{rel} is allowlisted but has no FS-mutation primitives "
            f"(dead entry -- remove it from the allowlist)."
        )
```

- [ ] **Step 2: Run -> passes**

`uv run pytest tests/unit/test_lint_no_fs_mutation.py -v --no-cov`

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_lint_no_fs_mutation.py
git commit -m "test(lint): add allowlist honesty tests -- no dead entries"
```

---

### Task 3: Pre-commit + CI wiring for purity lint

**Files:** Modify `.pre-commit-config.yaml`、`.github/workflows/ci.yml`

**Interfaces:** 无新代码产出。镜像现有 N7 lint hook 格式（`.pre-commit-config.yaml` 的 `- repo: local` 段，CI 的 `uv run python` 步骤）。

- [ ] **Step 1: Read existing format**

`grep -A5 "lint-no-forbid" .pre-commit-config.yaml` -- 确认 local hook 格式。
`grep -B1 -A2 "N7 lint" .github/workflows/ci.yml` -- 确认 CI 步骤格式。

- [ ] **Step 2: Add pre-commit hook**

在 `.pre-commit-config.yaml` 的 `- repo: local` 段（现有 `lint-no-forbid-with-computed-field` 之后）追加：

```yaml
      - id: lint-no-fs-mutation
        name: purity lint -- no FS-mutation in src/shenbi/ (spec P4)
        entry: uv run python tools/lint_no_fs_mutation.py src/shenbi
        language: system
        pass_filenames: false
        files: ^src/shenbi/.*\.py$
```

- [ ] **Step 3: Add CI step**

在 `.github/workflows/ci.yml` 的 quality job 中，现有 `N7 lint` 步骤之后追加：

```yaml
      - name: Purity lint (no FS-mutation in src/shenbi/, spec P4)
        run: uv run python tools/lint_no_fs_mutation.py src/shenbi
```

- [ ] **Step 4: Verify lint passes via CLI**

`uv run python tools/lint_no_fs_mutation.py src/shenbi` -> exit 0

- [ ] **Step 5: Commit**

```bash
git add .pre-commit-config.yaml .github/workflows/ci.yml
git commit -m "ci: wire purity lint into pre-commit + CI (spec P4)"
```

---

### Task 4: 评分标尺契约模型（score-arc/stratum/volume -- M3 修复）

**Files:** Create `src/shenbi/contracts/skills/_scoring_base.py`、`src/shenbi/contracts/skills/score_arc.py`、`src/shenbi/contracts/skills/score_stratum.py`、`src/shenbi/contracts/skills/score_volume.py`、`tests/unit/contracts/test_scoring_contracts.py`

**Interfaces:** Consumes `pydantic`。Produces `ScoreReport`（含 `PASS_THRESHOLD=90`、`TIER_ADVANCE_THRESHOLD=94`、`ROUTE_C_SOFT_WEIGHT=0.6`、`ROUTE_A_WEIGHT=0.4`、`AGGREGATION_FORMULA`、4 个 `@computed_field`、1 个 `@model_validator`）。三个 `score_*.py` 各导出 `Report = ScoreReport`（REGISTRY 自动发现，`_scoring_base.py` 以 `_` 前缀跳过发现）。

**聚合公式（M3 修复 -- 评分标尺不再未定义）：**
- `route_c_hard_binary` 未全达时该**检查项**得 0（非全卷归零）
- 否则 `final_score = 0.6 * route_c_soft_score + 0.4 * route_a_score`

阈值来源分层（round-1 Parfit 修正）：
- **已验证（AGENTS.md）：** PASS_THRESHOLD=90、TIER_ADVANCE_THRESHOLD=94
- **首次编码待验证（非来自 AGENTS.md）：** ROUTE_C_SOFT_WEIGHT=0.6、ROUTE_A_WEIGHT=0.4（scoring.py 用 rubric-weighted average，非 Route C/A split；权重需后续与 score-arc rubric 对齐）。AGENTS.md「Thresholds: >=94 for tier advancement, >=90 for individual test pass」。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/contracts/test_scoring_contracts.py
from __future__ import annotations

import pytest
from pydantic import ValidationError

from shenbi.contracts.registry import REGISTRY
from shenbi.contracts.skills._scoring_base import (
    AGGREGATION_FORMULA,
    PASS_THRESHOLD,
    ROUTE_A_WEIGHT,
    ROUTE_C_SOFT_WEIGHT,
    TIER_ADVANCE_THRESHOLD,
    ScoreReport,
)


def test_thresholds_explicit() -> None:
    assert PASS_THRESHOLD == 90
    assert TIER_ADVANCE_THRESHOLD == 94
    assert ROUTE_C_SOFT_WEIGHT == 0.6
    assert ROUTE_A_WEIGHT == 0.4


def test_aggregation_formula_declared() -> None:
    assert "final_score" in AGGREGATION_FORMULA
    assert "ROUTE_C_SOFT_WEIGHT" in AGGREGATION_FORMULA


def test_hard_binary_fail_blocks_pass() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=2, route_c_hard_binary_total=3,
        route_c_soft_score=95.0, route_a_score=90.0,
    )
    # hard_binary failure is an audit flag; does NOT zero final_score (Parfit round-1)
    assert r.hard_binary_gate_failed is True
    assert r.final_score > 0.0  # weighted average, not zeroed
    assert r.passed is False


def test_all_pass_perfect_score() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=3, route_c_hard_binary_total=3,
        route_c_soft_score=100.0, route_a_score=100.0,
    )
    assert r.hard_binary_gate_failed is False
    assert r.final_score == 100.0
    assert r.passed is True
    assert r.tier_advance_eligible is True


def test_boundary_exactly_90_passes() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=1, route_c_hard_binary_total=1,
        route_c_soft_score=100.0, route_a_score=75.0,
    )
    assert r.final_score == 90.0
    assert r.passed is True


def test_just_below_90_fails() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=1, route_c_hard_binary_total=1,
        route_c_soft_score=90.0, route_a_score=74.0,
    )
    assert r.final_score < PASS_THRESHOLD
    assert r.passed is False


def test_hard_binary_fail_blocks_tier_advance() -> None:
    """Meitner v5: tier_advance_eligible also gated on hard_binary."""
    r = ScoreReport(
        route_c_hard_binary_pass=2, route_c_hard_binary_total=3,
        route_c_soft_score=100.0, route_a_score=100.0,
    )
    assert r.final_score == 100.0
    assert r.hard_binary_gate_failed is True
    assert r.tier_advance_eligible is False


def test_computed_fields_in_model_dump() -> None:
    r = ScoreReport(
        route_c_hard_binary_pass=1, route_c_hard_binary_total=1,
        route_c_soft_score=90.0, route_a_score=90.0,
    )
    dump = r.model_dump()
    assert "final_score" in dump
    assert "passed" in dump
    assert "tier_advance_eligible" in dump


def test_rejects_pass_exceeds_total() -> None:
    with pytest.raises(ValidationError):
        ScoreReport(
            route_c_hard_binary_pass=5, route_c_hard_binary_total=3,
            route_c_soft_score=90.0, route_a_score=90.0,
        )


def test_registry_includes_scoring_skills() -> None:
    assert "shenbi-score-arc" in REGISTRY
    assert "shenbi-score-stratum" in REGISTRY
    assert "shenbi-score-volume" in REGISTRY
```

- [ ] **Step 2: Run -> fails** (ModuleNotFoundError)

- [ ] **Step 3: Implement shared scoring base**

```python
# src/shenbi/contracts/skills/_scoring_base.py
"""评分报告共享契约模型（spec M3 修复：评分标尺显式声明）。

聚合公式（Route C 硬二元门控 + 软分加权）：
  final_score = ROUTE_C_SOFT_WEIGHT * route_c_soft_score
                     + ROUTE_A_WEIGHT * route_a_score

阈值来源：AGENTS.md（>=90 单项通过，>=94 层进）。此前散落在散文/AGENTS.md，
现固化于此模型为单一真理之源。

三个评分 skill（arc/stratum/volume）共用本模型；各自 score_*.py 导出
Report = ScoreReport 供 REGISTRY 自动发现。本文件以 _ 前缀跳过发现。"""
from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, model_validator

from shenbi.contracts.thresholds import T1_PASS, TEST_PASS  # Kant I3: single-source

# --- 显式阈值（M3 修复：评分标尺不再未定义） ---

PASS_THRESHOLD: int = TEST_PASS  # single-source from thresholds.py (Kant I3 fix)
TIER_ADVANCE_THRESHOLD: int = T1_PASS  # single-source from thresholds.py (Kant I3 fix)

# --- 聚合权重 ---

ROUTE_C_SOFT_WEIGHT: float = 0.6
ROUTE_A_WEIGHT: float = 0.4

# --- 文档派生用公式描述 ---

AGGREGATION_FORMULA: str = (
    "# final_score = ROUTE_C_SOFT_WEIGHT * route_c_soft_score "
    "+ ROUTE_A_WEIGHT * route_a_score\n"
    "# passed requires final_score >= PASS_THRESHOLD AND hard_binary all pass"
)


class ScoreReport(BaseModel):
    """评分报告共享模型。Route C 硬二元门控 + Route A/C 软分加权聚合。"""

    model_config = {"extra": "ignore"}  # N7

    route_c_hard_binary_pass: int = Field(ge=0)
    route_c_hard_binary_total: int = Field(ge=1)
    route_c_soft_score: float = Field(ge=0, le=100)
    route_a_score: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _hard_binary_pass_le_total(self) -> "ScoreReport":
        if self.route_c_hard_binary_pass > self.route_c_hard_binary_total:
            raise ValueError(
                f"route_c_hard_binary_pass ({self.route_c_hard_binary_pass}) "
                f"> route_c_hard_binary_total ({self.route_c_hard_binary_total})"
            )
        return self

    @computed_field
    @property
    def hard_binary_gate_failed(self) -> bool:
        """True if any hard-binary check failed. Audit flag only."""
        return self.route_c_hard_binary_pass < self.route_c_hard_binary_total

    @computed_field
    @property
    def final_score(self) -> float:
        # Weighted average; hard_binary failure does NOT zero the score
        # (skill: 该检查项 0 分, not 全卷归零). Parfit round-1 fix.
        return (
            ROUTE_C_SOFT_WEIGHT * self.route_c_soft_score
            + ROUTE_A_WEIGHT * self.route_a_score
        )

    @computed_field
    @property
    def passed(self) -> bool:
        # Gate semantics (Poincare round-2): hard_binary failure blocks pass
        # even if weighted final_score >= 90. Matches scoring.py kill-switch.
        return self.final_score >= PASS_THRESHOLD and not self.hard_binary_gate_failed

    @computed_field
    @property
    def tier_advance_eligible(self) -> bool:
        # Same kill-switch as passed (Bernoulli round-3): hard_binary failure
        # blocks tier advancement even if final_score >= 94.
        return self.final_score >= TIER_ADVANCE_THRESHOLD and not self.hard_binary_gate_failed
```

- [ ] **Step 4: Implement three scoring skill modules**

```python
# src/shenbi/contracts/skills/score_arc.py
"""score-arc 契约（M3 修复）。继承 ScoreReport；REGISTRY 自动发现。"""
from shenbi.contracts.skills._scoring_base import ScoreReport

Report = ScoreReport
```

```python
# src/shenbi/contracts/skills/score_stratum.py
"""score-stratum 契约（M3 修复）。继承 ScoreReport；REGISTRY 自动发现。"""
from shenbi.contracts.skills._scoring_base import ScoreReport

Report = ScoreReport
```

```python
# src/shenbi/contracts/skills/score_volume.py
"""score-volume 契约（M3 修复）。继承 ScoreReport；REGISTRY 自动发现。"""
from shenbi.contracts.skills._scoring_base import ScoreReport

Report = ScoreReport
```

- [ ] **Step 5: Run -> passes**

`uv run pytest tests/unit/contracts/test_scoring_contracts.py -v --no-cov`

- [ ] **Step 6: mypy + ruff**

`uv run mypy src/shenbi/contracts/skills/ && uv run ruff check src/shenbi/contracts/skills/` -> Success / All passed

- [ ] **Step 7: Commit**

```bash
git add src/shenbi/contracts/skills/_scoring_base.py \
        src/shenbi/contracts/skills/score_arc.py \
        src/shenbi/contracts/skills/score_stratum.py \
        src/shenbi/contracts/skills/score_volume.py \
        tests/unit/contracts/test_scoring_contracts.py
git commit -m "feat(contracts): add scoring scale models with explicit PASS_THRESHOLD + formula (M3)"
```

---

### Task 5: 文档派生生成器 + 渲染/幂等/防篡改测试

**Files:** Create `tools/generate_autocheck_docs.py`、`tests/unit/test_generate_autocheck_docs.py`

**Interfaces:** Consumes `shenbi.contracts.registry.REGISTRY`、`shenbi.gates.shared.SKILLS`、Pydantic BaseModel metadata。Produces `render_autocheck(model_cls) -> str`、`inject_block(skill_md, block) -> bool`。

**生成内容：** 从契约模型的模块级常量 + `@computed_field` + `@model_validator` 渲染 markdown「可自动检查」区块，用 sentinel 分隔。CI 跑生成 + `git diff --exit-code` 拒绝手改（物理预防）。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_generate_autocheck_docs.py
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from generate_autocheck_docs import (  # noqa: E402
    BANNER,
    ENDER,
    inject_block,
    render_autocheck,
)


def test_render_includes_thresholds() -> None:
    from shenbi.contracts.skills._scoring_base import ScoreReport

    md = render_autocheck(ScoreReport)
    assert BANNER in md
    assert ENDER in md
    assert "PASS_THRESHOLD" in md
    assert "90" in md


def test_render_includes_computed_fields() -> None:
    from shenbi.contracts.skills._scoring_base import ScoreReport

    md = render_autocheck(ScoreReport)
    assert "ROUTE_C_SOFT_WEIGHT" in md or "AGGREGATION_FORMULA" in md  # Parfit round-1: test the formula
    assert "passed" in md


def test_inject_creates_block(tmp_path: Path) -> None:
    from shenbi.contracts.skills._scoring_base import ScoreReport

    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: x\n---\n# Title\n", encoding="utf-8")
    block = render_autocheck(ScoreReport)
    assert inject_block(f, block) is True
    content = f.read_text(encoding="utf-8")
    assert BANNER in content
    assert ENDER in content


def test_inject_idempotent(tmp_path: Path) -> None:
    """Second inject with the same block -> no change."""
    from shenbi.contracts.skills._scoring_base import ScoreReport

    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: x\n---\n# Title\n", encoding="utf-8")
    block = render_autocheck(ScoreReport)
    inject_block(f, block)
    assert inject_block(f, block) is False


def test_tampered_block_overwritten_on_regen(tmp_path: Path) -> None:
    """Manual edit inside the sentinel block -> regeneration overwrites it."""
    from shenbi.contracts.skills._scoring_base import ScoreReport

    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: x\n---\n# Title\n", encoding="utf-8")
    block = render_autocheck(ScoreReport)
    inject_block(f, block)

    # Tamper: inject manual text inside the block
    content = f.read_text(encoding="utf-8")
    tampered = content.replace("PASS_THRESHOLD", "HACKED_THRESHOLD")
    f.write_text(tampered, encoding="utf-8")

    # Regenerate -- must detect change and overwrite
    assert inject_block(f, block) is True
    final = f.read_text(encoding="utf-8")
    assert "HACKED" not in final
    assert "PASS_THRESHOLD" in final
```

- [ ] **Step 2: Run -> fails** (ModuleNotFoundError)

- [ ] **Step 3: Implement generator**

```python
# tools/generate_autocheck_docs.py
#!/usr/bin/env python3
"""Generate 'auto-checkable' doc sections from contract models (spec P6).

Reads Pydantic contract models from contracts/skills/ and renders a markdown
block into each skill's SKILL.md. The block is delimited by sentinels
(AUTO-CHECK-START / AUTO-CHECK-END); regeneration replaces the block wholesale.
CI runs this + git diff to reject manual edits.

Usage: python tools/generate_autocheck_docs.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"

BANNER = "<!-- AUTO-CHECK-START -->"
ENDER = "<!-- AUTO-CHECK-END -->"

_SKIP_CONSTS = frozenset({"AGGREGATION_FORMULA", "BANNER", "ENDER"})


def _get_module_constants(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Extract uppercase module-level constants (int/float/dict)."""
    mod = sys.modules.get(model_cls.__module__)
    if mod is None:
        return {}
    out: dict[str, Any] = {}
    for name in dir(mod):
        if name.startswith("_") or name in _SKIP_CONSTS:
            continue
        if not (name.isupper() or name.endswith("_THRESHOLDS") or name.endswith("_WEIGHT")):
            continue
        val = getattr(mod, name, None)
        if isinstance(val, (int, float, dict)):
            out[name] = val
    return out


def _type_str(t: Any) -> str:
    if t is None:
        return "auto"
    name = getattr(t, "__name__", None)
    if name:
        return name
    return str(t)


def _computed_fields_table(model_cls: type[BaseModel]) -> str:
    lines = ["| name | type |", "|------|------|"]
    for name, info in model_cls.model_computed_fields.items():
        rt = getattr(info, "return_type", None)
        lines.append(f"| {name} | {_type_str(rt)} |")
    return "\n".join(lines)


def _validator_names(model_cls: type[BaseModel]) -> list[str]:
    decorators = getattr(model_cls, "__pydantic_decorators__", None)
    if decorators is None:
        return []
    return sorted(decorators.model_validators.keys())


def render_autocheck(model_cls: type[BaseModel]) -> str:
    """Render the auto-checkable markdown block for a contract model."""
    lines = [BANNER, "", "## auto-check (generated -- do not edit)", ""]

    consts = _get_module_constants(model_cls)
    if consts:
        lines.append("### constants")
        lines.append("")
        lines.append("| name | value |")
        lines.append("|------|-------|")
        for name, val in sorted(consts.items()):
            lines.append(f"| {name} | {val} |")
        lines.append("")

    mod = sys.modules.get(model_cls.__module__)
    if mod is not None:
        formula = getattr(mod, "AGGREGATION_FORMULA", None)
        if formula:
            lines.append("### formula")
            lines.append("")
            lines.append("```")
            lines.append(str(formula))
            lines.append("```")
            lines.append("")

    if model_cls.model_computed_fields:
        lines.append("### computed fields")
        lines.append("")
        lines.append(_computed_fields_table(model_cls))
        lines.append("")

    vals = _validator_names(model_cls)
    if vals:
        lines.append("### invariants")
        lines.append("")
        for v in vals:
            desc = v.lstrip("_").replace("_", " ")
            lines.append(f"- {desc}")
        lines.append("")

    lines.append(ENDER)
    return "\n".join(lines) + "\n"


_PATTERN = re.compile(
    re.escape(BANNER) + r".*?" + re.escape(ENDER) + r"\n?", re.DOTALL
)
_FRONTMATTER_RE = re.compile(r"^(---\n.*?\n---\n)(.*)$", re.DOTALL)


def inject_block(skill_md: Path, block: str) -> bool:
    """Replace the auto-check block in a SKILL.md. Return True if changed."""
    text = skill_md.read_text(encoding="utf-8")
    if _PATTERN.search(text):
        new_text = _PATTERN.sub(block, text, count=1)
    else:
        m = _FRONTMATTER_RE.match(text)
        if m:
            new_text = m.group(1) + block + "\n" + m.group(2)
        else:
            new_text = block + "\n" + text
    if new_text != text:
        skill_md.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> int:
    sys.path.insert(0, str(SRC))
    from shenbi.contracts.registry import REGISTRY  # noqa: PLC0415
    from shenbi.gates.shared import SKILLS  # noqa: PLC0415

    changed: list[str] = []
    for skill_name, model_cls in sorted(REGISTRY.items()):
        skill_md = SKILLS / skill_name / "SKILL.md"
        if not skill_md.exists():
            continue
        block = render_autocheck(model_cls)
        if inject_block(skill_md, block):
            changed.append(str(skill_md))
    if changed:
        for c in changed:
            print(f"updated: {c}")
    else:
        print("all up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run -> passes**

`uv run pytest tests/unit/test_generate_autocheck_docs.py -v --no-cov`

- [ ] **Step 5: mypy + ruff**

`uv run mypy tools/generate_autocheck_docs.py && uv run ruff check tools/generate_autocheck_docs.py tests/unit/test_generate_autocheck_docs.py` -> Success / All passed

- [ ] **Step 6: Commit**

```bash
git add tools/generate_autocheck_docs.py tests/unit/test_generate_autocheck_docs.py
git commit -m "feat(docs): add auto-check doc generator from contract models (spec P6)"
```

---

### Task 6: 文档派生 CI 幂等检查 + pre-commit wiring

**Files:** Modify `.github/workflows/ci.yml`、`.pre-commit-config.yaml`

**Interfaces:** 无新代码。CI 跑生成器 + `git diff --exit-code` 拒绝手改。

- [ ] **Step 1: Add CI idempotency step**

在 `.github/workflows/ci.yml` 的 `contract-sync` job 中，现有 `Idempotency` 步骤之前追加：

```yaml
      - name: Regenerate auto-check docs (spec P6)
        run: uv run python tools/generate_autocheck_docs.py
```

现有 `Idempotency -- generated artifacts must match committed` 步骤已检查 `git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/`，覆盖 `skills/` 下的 SKILL.md 变更。

- [ ] **Step 2: Add pre-commit hook**

在 `.pre-commit-config.yaml` 的 `- repo: local` 段追加（现有 `contract-sync-idempotency` 之后）：

```yaml
      - id: autocheck-docs-idempotency
        name: auto-check docs idempotency (spec P6)
        entry: bash -c 'uv run python tools/generate_autocheck_docs.py >/dev/null &&
          git diff --exit-code -- skills/'
        language: system
        pass_filenames: false
```

- [ ] **Step 3: Verify generator CLI runs**

`uv run python tools/generate_autocheck_docs.py` -> outputs `updated: ...` or `all up to date`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml .pre-commit-config.yaml
git commit -m "ci: wire auto-check doc idempotency into CI + pre-commit (spec P6)"
```

---

### Task 7: CapabilityFS 测试（消费 pillar5 产物，不重建）

**跨计划一致性（Kant cross-plan review C1 修复）：** `capability_fs.py` 由 **pillar5** 创建（`CapabilityFS(allow_root: Path)` 实例 API，非上下文管理器）。本计划**不重建**该文件——只为它写单元测试。pillar5 是本计划的前置依赖之一。

**Files:** Test only: `tests/unit/test_capability_fs.py`（capability_fs.py 是 pillar5 产物，本计划不 Create）

**Interfaces:** Consumes `CapabilityFS`（pillar5 产物：`CapabilityFS(allow_root: Path)` 实例 API，非上下文管理器）。

**设计依据：** spec 支柱五「CapabilityFS（in-process，可行）：测试时给门注入只读 FS 句柄，任意写抛 PermissionError」。不用于 subprocess。本垫片只拦截 `pathlib.Path` 写方法；builtin `open()` 或 os/shutil 直接调用由静态 lint 拦截（已知限制）。

**纯度 lint 影响：** `capability_fs.py` 本身无 FS 变更原语（monkeypatch 是属性赋值非 FS 调用），lint 不会 flag 它。

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_capability_fs.py
from __future__ import annotations

from pathlib import Path

import pytest

from shenbi.capability_fs import CapabilityFS


def test_read_text_allowed(tmp_path: Path) -> None:
    """Read within allow_root is permitted."""
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    assert fs.read_text(f) == "hello"


def test_write_text_denied(tmp_path: Path) -> None:
    """Any write raises PermissionError (purity backstop)."""
    fs = CapabilityFS(tmp_path)
    with pytest.raises(PermissionError):
        fs.write_text(tmp_path / "x.txt", "x")


def test_unlink_denied(tmp_path: Path) -> None:
    fs = CapabilityFS(tmp_path)
    with pytest.raises(PermissionError):
        fs.unlink(tmp_path / "x.txt")


def test_mkdir_denied(tmp_path: Path) -> None:
    fs = CapabilityFS(tmp_path)
    with pytest.raises(PermissionError):
        fs.mkdir(tmp_path / "sub")


def test_escape_root_denied(tmp_path: Path) -> None:
    """Path outside allow_root is rejected (sandbox boundary)."""
    fs = CapabilityFS(tmp_path)
    with pytest.raises(PermissionError):
        fs.read_text(Path("/etc/passwd"))


def test_list_dir_allowed(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    fs = CapabilityFS(tmp_path)
    names = set(fs.list_dir(tmp_path))
    assert {"a", "b.txt"} <= names


def test_read_bytes_allowed(tmp_path: Path) -> None:
    f = tmp_path / "bin.dat"
    f.write_bytes(b"\x00\x01")
    fs = CapabilityFS(tmp_path)
    assert fs.read_bytes(f) == b"\x00\x01"

```

Run: `uv run mypy src/shenbi/capability_fs.py && uv run ruff check src/shenbi/capability_fs.py tests/unit/test_capability_fs.py` -> Success / All passed

- [ ] **Step 6: Commit**

```bash
git add src/shenbi/capability_fs.py tests/unit/test_capability_fs.py
git commit -m "test(capability): add tests for CapabilityFS (pillar5 product, consume not create)"
```

---

### Task 8: 全量回归 + 支柱六完成确认

**Files:** 无。仅验证。

- [ ] **Step 1: Full test suite**

`uv run pytest -q` -> 现有测试集无 regression + 新增测试全 passed。执行者以实际输出为准，只断言「无失败、无 regression」。

- [ ] **Step 2: Type check + lint whole repo**

`uv run mypy src/shenbi && uv run ruff check .` -> Success / All passed

- [ ] **Step 3: Verify spec 判据对齐（本支柱范围）**
  - 判据 4（纯度强制：AST lint 禁 src/shenbi/ FS 变更，allowlist safe_write.py + trace/writer.py）：Task 1-3 done
  - 判据 4（in-process CapabilityFS 兜底）：Task 7 done
  - 支柱六（文档派生：从契约模型生成可自动检查表，CI 拒绝手改）：Task 5-6 done
  - M3（评分标尺显式声明聚合公式 + PASS_THRESHOLD）：Task 4 done
  - **范围外：** 69 技能契约迁移（支柱一续）、门阈值派生（支柱二）、CJK（支柱三）、Tier B 写所有权审计（支柱四 Tier B）、属性测试网全面铺开（支柱五）、subprocess read-provenance（future work）。

- [ ] **Step 4: Empty marker commit**

```bash
git commit --allow-empty -m "chore(docs-lint): pillar 6 complete -- AST purity lint + doc derivation + CapabilityFS"
```

---

## Self-Review

**1. Spec coverage（支柱六范围）：** 判据 4（AST 纯度 lint Task 1-3 + CapabilityFS Task 7）。支柱六（文档派生 Task 5-6）。M3（评分标尺 Task 4）。allowlist 决策已验证（safe_write.py + trace/writer.py 永久；14 文件过渡，测试断言无死条目）。**范围外明确声明：** 69 技能迁移、门改造、CJK、Tier B 写审计、subprocess read-provenance。

**2. Placeholder scan：** 无 TBD/TODO；每个 code step 有完整代码；CI/pre-commit 给精确 YAML（参考现有 N7 hook + contract-sync job 格式，已亲手核对 `.pre-commit-config.yaml` 和 `.github/workflows/ci.yml`）。

**3. Type consistency：** `ScoreReport` 的 `final_score -> float` / `passed -> bool` / `tier_advance_eligible -> bool` / `hard_binary_gate_failed -> bool` 一致。`lint_dir(root: Path) -> list[str]` / `_find_violations(tree: ast.Module, filepath: Path) -> list[str]` 一致。`render_autocheck(model_cls: type[BaseModel]) -> str` / `inject_block(skill_md: Path, block: str) -> bool` 一致。`CapabilityFS(allow_root: Path)` 实例 API 与 pillar5 一致（非上下文管理器）。

**4. 已知限制：**
- 纯度 lint 不检测 import-aliased 调用（`from os import replace; replace(...)`）。需 import tracking，超出 AST lint 范围。documented in script docstring。
- 纯度 lint 不检测动态 open mode（非常量）。保守不 flag。
- CapabilityFS 只拦截 `pathlib.Path` 写方法；builtin `open()` 和 os/shutil 直接调用由静态 lint 拦截。documented in module docstring。
- 文档生成器在 `tools/`（非 `src/shenbi/`），直接写 SKILL.md。这是 build-time 工具，与 `sync_contracts.py`（src/shenbi/，过渡 allowlist）不同——生成器不在运行态，不受纯度 lint 约束。
- 过渡 allowlist（14 文件）需在后续计划迁移到 safe_write 后逐个移除。`test_every_allowlisted_file_has_violations` 自动检测死条目。
- Task 4 的三个评分 skill 共享同一个 `ScoreReport` 模型（`Report = ScoreReport` 别名）。如果未来 arc/stratum/volume 需要不同字段，各自 `score_*.py` 可定义独立子类。

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-contract-single-source-pillar6-docs-lint.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
