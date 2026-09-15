# C25 CI/just 双向同步漂移修复 Implementation Plan（spec #63）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消灭 ci.yml↔justfile 双清单漂移（CI 调 `just check` 单源化）、隔离 coverage 工件、闭合 hook/工具/workflow 激活面、清出 novel-output 生产产物并修忽略规则——spec `docs/superpowers/specs/archive/2026-08-16-audit-ci-just-sync-fix-Done-PR217.md`（簇 C25，22 条）。

**Architecture:** justfile `check` 成为唯一检查清单信源；CI quality job 收敛为「matrix 环境准备 + `uvx just check`」；codegen-idempotency job 并入 just check 后删除。coverage 从全局 addopts 拆到五个显式入口。工作态文件（.codex-plugin 生成物、novel-output 产物）一个入库一个出库。

**Tech Stack:** just、GitHub Actions、pytest-cov、pre-commit、git-cliff、pyproject.toml。

## Global Constraints

- 验证命令一律 `just`/`uv run`（与 CI `uv run --frozen` 同构）；本机 push 需 shim PATH（`env -i HOME=$HOME PATH=/tmp/shim-bin2 git push …`，codex 可达会使 pre-push 挂起——上批已知）
- 本仓 push 前本地门禁 = `just check` 全绿；pre-push hook 阻塞时禁 `--no-verify`，用 shim PATH
- conventional commits；pathspec commit（禁 `git add -A`）
- 改动 ci.yml 后跑 `uv run yamllint --strict .github/workflows/`（action-validation job 同构）
- 不触发任何真实 dispatch/pipeline（成本纪律）

## 关键裁决（plan 阶段落定，写入 spec-deviations）

1. **T1 方案 = 推荐向（CI 调 just check）**：quality job 保留 checkout/setup-uv/uv-python-install/uv-sync + lock check（matrix 钉扎是 CI 结构语义），其后的 ruff/mypy/lints/pytest/覆盖步骤**整体替换**为 `uvx just check`；codegen-idempotency job 删除（其三生成器+diff 并入 just check，quality 每个矩阵腿都跑，覆盖面更宽）。runner 上 just 经 `uvx` 提供（uv 已就位，零新 action 依赖）。
2. **F1003 方案 = A（.codex-plugin/ 入库）**：生成器是确定性单源（`shenbi-generate-plugins`），产物即生成物基线；先 `du` 测体积（预计 <1MB 文本 manifest），超过 5MB 才回退方案 B。
3. **T1504 = 全部出库（前向删除）**：`git rm -r novel-output` 1150 文件；删除 .gitignore 反忽略死行组；`novel-output/` 保持忽略；`tools/lint_artifact_contamination.py` 对默认树缺失改为显式 skip（exit 0 + stderr 提示），审计历史在 git log 与 C18 清洗记录中。
4. **F1207 = SECURITY.md 声明对齐**（codeql 保持 push-only——300-file-limit 设计理由已在 codeql.yml 注释文档化，不改触发面）。
5. **pytest 旗标统一落点 = justfile**：`--dist loadscope --timeout=120` 进 just check 的两段 pytest；addopts 保留 `--timeout=60` 作为单测默认（test-file/test 场景）。

---

### Task 1: 结构防线测试先行（red）

**Files:**
- Create: `tests/integration/test_ci_just_single_source.py`
- 参考: `.github/workflows/ci.yml`、`justfile`、`pyproject.toml`

**Interfaces:**
- Produces: 结构断言测试集（Task 2-7 的红灯基线；命名 `test_*` 全部 T2 归属 integration）

**复杂度:** infra（协调者亲自实现）· **test_kind:** tdd_red_green

- [ ] **Step 1: 写失败测试**（内容如下——覆盖 spec 验收 1/2 的机读形态）

```python
"""C25 spec #63 — CI/just single-source structural invariants (acceptance 1/2).

These tests encode the *converged* state. They are RED before Task 2-4 land
and GREEN after. They replace the manual grep-diff acceptance with machine-
readable assertions so future drift fails `just check` itself.
"""
from pathlib import Path
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
CI = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
JUSTFILE = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
PYPROJECT = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


class TestCISingleSource:
    def test_ci_invokes_just_check(self):
        assert "uvx just check" in CI

    def test_ci_has_no_direct_tool_lint_calls(self):
        import re
        direct = re.findall(r"uv run python (?:tools|scripts)/lint_\S+", CI)
        assert direct == [], f"ci.yml still dual-lists lints: {direct}"

    def test_ci_no_direct_pytest(self):
        # 唯一豁免：Hypothesis replay statistics 步骤（CI 结构语义，见 Task 3 I1 裁决）
        import re
        pytest_calls = re.findall(r"uv run pytest[^\n]*", CI)
        non_exempt = [c for c in pytest_calls if "tests/property" not in c]
        assert non_exempt == [], f"ci.yml still runs pytest outside just check: {non_exempt}"


class TestAddoptsCoverageIsolation:
    def test_global_addopts_have_no_cov(self):
        addopts = PYPROJECT["tool"]["pytest"]["ini_options"]["addopts"]
        cov_flags = [a for a in addopts if a.startswith("--cov")]
        assert cov_flags == [], f"global addopts still carry coverage: {cov_flags}"

    def test_just_test_is_nocov(self):
        pytest_lines = [l.strip() for l in JUSTFILE.splitlines() if "uv run pytest" in l]
        unit_only = [l for l in pytest_lines if '-m "unit"' in l]
        assert unit_only and all("--no-cov" in l for l in unit_only), unit_only


class TestJustfileCheckScope:
    def test_check_includes_lock_and_codegen_idempotency(self):
        check_body = JUSTFILE.split("check:", 1)[1].split("\n\n", 1)[0]
        assert "uv lock --check" in check_body
        assert "generate_autocheck_docs.py" in check_body
        assert "shenbi-generate-plugins" in check_body
        assert ".codex-plugin/" in check_body

    def test_check_runs_fixture_mirror(self):
        check_body = JUSTFILE.split("check:", 1)[1].split("\n\n", 1)[0]
        assert "check_fixture_mirror.py" in check_body

    def test_check_includes_ci_only_lints(self):
        check_body = JUSTFILE.split("check:", 1)[1].split("\n\n", 1)[0]
        assert "lint_no_forbid_with_computed_field.py" in check_body
        assert "lint_no_fs_mutation.py" in check_body

    def test_codex_plugin_tracked(self):
        gi = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".codex-plugin/" not in gi
```

- [ ] **Step 2: 跑红**：`uv run pytest tests/integration/test_ci_just_single_source.py -v --no-cov` → 预期 9 FAIL（CI 类 3 + addopts 类 2 + justfile 类 4）
- [ ] **Step 3: Commit**：`git add tests/integration/test_ci_just_single_source.py && git commit -m "test: C25 structural single-source invariants (red baseline, spec #63 T1)"`

---

### Task 2: justfile check 单源化 + .codex-plugin 入库（F004/F005/F1001-F1003/F911/F1012 + 旗标统一）

**Files:**
- Modify: `justfile:14-39`（check recipe）、`justfile:81-85`（lint-contracts 保持）
- Modify: `.gitignore:20`
- Create: `.codex-plugin/**`（生成器产物，提交入库）

**Interfaces:**
- Consumes: Task 1 测试集
- Produces: `just check` = 唯一清单源；`.codex-plugin/` tracked 基线

**复杂度:** infra · **test_kind:** tdd_red_green

- [ ] **Step 1: 生成并测量 .codex-plugin**
  `uv run shenbi-generate-plugins && du -sh .codex-plugin/`——若 >5MB 停下回阶段 1 重裁（方案 B 哈希对比），否则继续
- [ ] **Step 2: .gitignore 删 `.codex-plugin/` 行（L20）**
- [ ] **Step 3: 改 check recipe**（新 check 全文）：

```just
# Run all checks (single source of truth — CI calls this; see spec #63 C25)
check:
    uv lock --check
    uv run python tools/lint_status_strings.py
    uv run python tools/lint_routing_faces.py
    uv run python tools/audit-skill-descriptions.py
    uv run python tools/lint_registry_reconcile.py --allow-missing shenbi-score-arc,shenbi-score-stratum,shenbi-score-volume
    uv run python tools/lint_bare_writes.py
    uv run python tools/lint_bare_subprocess_json.py
    uv run python tools/check_severity_vocab.py
    uv run python tools/lint_repo_consistency.py
    uv run python tools/lint_key_reconciliation.py --strict
    uv run python tools/lint_decisions_sources.py
    uv run python tools/lint_helper_usage.py
    uv run python tools/lint_threshold_reconciliation.py
    uv run python tools/lint_dead_code_allowlist.py
    uv run python tools/lint_audit_run.py
    uv run python tools/lint_artifact_contamination.py
    uv run python tools/count_active_specs.py
    uv run python tools/check_fixture_mirror.py
    uv run python tools/lint_no_forbid_with_computed_field.py src/shenbi/contracts
    uv run python tools/lint_no_fs_mutation.py src/shenbi
    just lint-contracts
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src/shenbi/
    uv run basedpyright
    uv run shenbi-sync-contracts >/dev/null
    uv run python tools/generate_autocheck_docs.py
    uv run shenbi-generate-plugins
    git diff --exit-code -- tests/tiers/deps.json docs/framework/ skills/ .codex-plugin/
    uv run pytest -n auto --dist loadscope -m "not last" --hypothesis-profile=ci --timeout=120 --cov=shenbi --cov-branch --cov-report=json:coverage.json --cov-report=xml:tests/coverage/coverage.xml --cov-report=term-missing
    uv run python tools/check_module_coverage.py coverage.json
    uv run pytest -p no:xdist -m "last" --no-cov --hypothesis-profile=ci
```

注意：`--dist loadscope --timeout=120` 自 ci.yml 收编；`--cov-report=xml:tests/coverage/coverage.xml` 保留 `-m last` 阈值测试输入（addopts 拆分前置冗余无害，Task 4 后成为唯一来源）；html 报告不再在 check 生成（开发需要时 `just module-coverage` 或手动）。diff 收敛为一条（三生成器后一次全范围）。
- [ ] **Step 4: 跑 Task 1 测试转绿（仅 justfile/codex_plugin 类；CI 类仍红属 Task 3）**
  `uv run pytest tests/integration/test_ci_just_single_source.py -v --no-cov -k "Justfile or codex_plugin"`
- [ ] **Step 5: 全量 `just check`（shim PATH）** → 全绿
- [ ] **Step 6: Commit**：`git add justfile .gitignore .codex-plugin tests/integration/test_ci_just_single_source.py && git commit -m "feat: C25 single-source check — CI-bound codegen steps + fixture-mirror + flag unification in justfile; .codex-plugin baseline committed (F004/F005/F1001-F1003/F911/F1012, spec #63)"`

---

### Task 3: ci.yml 收敛为 just 调用

**Files:**
- Modify: `.github/workflows/ci.yml:47-91`（quality job 步骤体）、删除 `codegen-idempotency` job（L93-114）

**复杂度:** infra · **test_kind:** regression_guard（结构由 Task 1 测试守护；行为由 CI 实跑守护）

- [ ] **Step 1: quality job 步骤体替换**——保留 L38-46（checkout/setup-uv/python-install/lock-check/uv-sync）与 L82-89（Hypothesis replay statistics，见 I1 裁决），L47-81 + L90-91（`-m "last"` 步骤已并入 just check）替换为：

```yaml
      - name: Single-source checks (justfile is the authority; spec #63 C25)
        run: uvx just check
```

（matrix/continue-on-error/env PYTHONUTF8 原样保留；`uvx just` 用 uv 环境引导 just，just 内 `uv run` 继承已装环境。**I1 裁决**：ci.yml:82-89 "Hypothesis replay statistics" 步骤并入 just check pytest 段所属环境不可分——保留该步骤为 CI 结构步骤（矩阵腿可见性是 CI 可观测语义，与 matrix 钉扎同类），记 spec-deviations。**M1**：ci.yml L44-45 lock check 保留（CI 第一道门快失败语义），just check 内重复无害）
- [ ] **Step 2: 删除 codegen-idempotency job 整块**（其面已进 just check，quality 每矩阵腿都跑）
- [ ] **Step 3: `uv run yamllint --strict .github/workflows/`** → pass
- [ ] **Step 4: Task 1 测试全绿**：`uv run pytest tests/integration/test_ci_just_single_source.py -v --no-cov`
- [ ] **Step 5: Commit**：`git add .github/workflows/ci.yml && git commit -m "feat: C25 CI convergence — quality job runs 'uvx just check', codegen-idempotency job folded in (F004/F005, spec #63)"`

---

### Task 4: coverage 工件隔离（D101/F770/F1040/F1036/F1042）

**Files:**
- Modify: `pyproject.toml:437-449`（addopts）
- Modify: `justfile:47-57`（test/test-file）、`justfile:43-45`（module-coverage）
- Modify: `tools/pre-push-check.sh:70,74,82-85`
- Modify: `.github/workflows/nightly.yml:41`

**复杂度:** infra · **test_kind:** tdd_red_green（addopts 断言已在 Task 1；行为验收在本 task Step 内实跑）

- [ ] **Step 1: addopts 拆分**——新 addopts：

```toml
addopts = [
    "--strict-markers",
    "--timeout=60",
    "--timeout-method=thread",
    "--benchmark-min-rounds=5",
    "--benchmark-warmup=on",
]
```

（`--cov=shenbi/--cov-branch/--cov-report=*/` 全部移除；`[tool.coverage.report] fail_under = 85` 保留——pytest-cov 在显式 `--cov` 入口上仍读取该配置执行阈值，与现 CI 行为等价）
- [ ] **Step 2: 五入口显式化**
  - just check pytest 段：Task 2 已带全套 cov 旗标 ✓
  - `just module-coverage`：pytest 行改 `uv run pytest -n auto -m "not last" --cov=shenbi --cov-branch --cov-report=json:coverage.json -q`
  - `just test`：`uv run pytest -n auto -m "unit" --no-cov {{args}}`
  - `just test-file`：`uv run pytest {{file}} -v --no-cov`
  - `pre-push-check.sh:70`：`uv run pytest -n auto --dist loadscope -m "not last" --cov=shenbi --cov-branch --cov-report=xml:tests/coverage/coverage.xml --cov-fail-under=85 --timeout=120`（原行缺 loadscope/timeout 的漂移一并对齐 just check）
  - `nightly.yml:41`：`uv run pytest -n auto -m "not last" --cov=shenbi --cov-report=json:coverage.json --cov-fail-under=85`（json 报告使该门可诊断）
  - ci.yml 覆盖步骤：已随 Task 3 进 just check ✓
- [ ] **Step 3: F1036 守卫**——pre-push-check.sh:74 管道加 `|| true`：
  `UNUSED_COUNT=$( { grep -r 'reportUnusedFunction' src/shenbi/ --include='*.py' | grep -v test_ | grep -v __pycache__ || true; } | wc -l | tr -d ' ')`
- [ ] **Step 4: F1042 mkdocs 门显式报错**——pre-push-check.sh:44 一带改为：

```bash
if ! git rev-parse --verify main...HEAD >/dev/null 2>&1; then
  echo "pre-push: cannot resolve main...HEAD (shallow clone?); skipping mkdocs gate explicitly" >&2
else
  git diff --name-only main...HEAD | grep -qE '^(docs/|mkdocs\.yml)' && { uv run mkdocs build --strict || exit 1; }
fi
```

- [ ] **Step 5: 验收 2 实跑（红灯→绿灯证明；先跑一次 `just check` 产出新 coverage.xml 基线）**
  - `just check`（shim PATH）→ 绿，产 tests/coverage/coverage.xml
  - `S=$(shasum -a 256 tests/coverage/coverage.xml | cut -d' ' -f1); uv run pytest --co -q >/dev/null 2>&1; uv run pytest --co -q >/dev/null 2>&1; [ "$S" = "$(shasum -a 256 tests/coverage/coverage.xml | cut -d' ' -f1)" ] && echo "D101 FIXED" || echo "D101 STILL RED"`
  - `just test`（shim PATH）→ exit 0
  - `uv run pytest -p no:xdist -m "last" --no-cov tests/unit/test_coverage_thresholds.py -v` → 阈值测试可用既有 coverage.xml（先跑一次 check 产新）
- [ ] **Step 6: Commit**：`git add pyproject.toml justfile tools/pre-push-check.sh .github/workflows/nightly.yml && git commit -m "fix: C25 coverage isolation — addopts stripped, five explicit entries, just test no-cov, pre-push pipefail guard + mkdocs gate honesty (D101/F770/F1040/F1036/F1042, spec #63)"`

---

### Task 5: 文档安装命令与 workflow 面（F1038/F1006/F1207/F1021/F1026）

**Files:**
- Modify: `CONTRIBUTING.md:11`、`docs/getting-started/installation.md:43`、`AGENTS.md`（PR Review Protocol 1「等价命令」改述）
- Modify: `.pre-commit-config.yaml`（顶层加 `default_install_hook_types: [pre-commit, pre-push]`）
- Modify: `.github/workflows/codeql.yml:12-13`（push 加 `branches: [main]`）
- Modify: `SECURITY.md:27`（改述为 "CodeQL static analysis runs on every push to main and weekly"）
- Modify: `.github/workflows/release.yml:31-47`（changelog 走 cliff）
- Modify: `.github/workflows/docs.yml`（加 concurrency 组）

**复杂度:** leaf 可分派（无 src/ 改动）· **test_kind:** regression_guard

- [ ] **Step 1: F1038 + AGENTS.md 等价命令（spec T1.3）**——两处安装命令改 `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`；`.pre-commit-config.yaml` 顶部（`repos:` 之前）加：

```yaml
default_install_hook_types: [pre-commit, pre-push]
```

AGENTS.md PR Review Protocol 第 1 条的括号等价命令整体替换为：`（或等价：PATH 同构 CI 的环境下跑 just check；旧手工串联命令不含 lint 面与 -m "last" 第二段，非等价）`——消除 F005 补充点的失真表述。

- [ ] **Step 2: F1006/F1207**——codeql.yml `on: push:` 改 `push: branches: [main]`；SECURITY.md:27 对齐改述（裁决 4）
- [ ] **Step 3: F1021**——release.yml changelog step 三分支 git log 替换为：

```yaml
      - name: Generate release notes (git-cliff, conventional grouping)
        run: |
          prev_tag=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
          if [ -n "$prev_tag" ]; then
            notes=$(uvx git-cliff --unreleased ${prev_tag}..HEAD --strip header)
          else
            notes=$(uvx git-cliff --unreleased -n 100 --strip header)
          fi
          echo "notes<<EOF" >> $GITHUB_OUTPUT
          echo "$notes" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
```

（保持 HEAD^ 守卫注释；`uvx git-cliff` 与 justfile changelog recipe 同一工具）
- [ ] **Step 4: F1026**——docs.yml `on:` 之后加：

```yaml
concurrency:
  group: docs-${{ github.ref }}
  cancel-in-progress: true
```

- [ ] **Step 5: yamllint + pre-commit 配置自检**：`uv run yamllint --strict .github/workflows/ .pre-commit-config.yaml` → pass；`uv run pre-commit validate-config .pre-commit-config.yaml` → pass
- [ ] **Step 6: Commit**：`git add AGENTS.md CONTRIBUTING.md docs/getting-started/installation.md .pre-commit-config.yaml .github/workflows/codeql.yml SECURITY.md .github/workflows/release.yml .github/workflows/docs.yml && git commit -m "fix: C25 activation & workflow face — pre-push install activation, AGENTS.md equivalent-command rewrite, codeql branch filter + SECURITY.md alignment, cliff release notes, docs.yml concurrency (F1038/F006/F1207/F1021/F1026, spec #63)"`

---

### Task 6: 忽略规则与 novel-output 出库（F1019/F1020/F1039/T1504）

**Files:**
- Modify: `.gitignore:88-99`
- Modify: `justfile:107-111`（clean）
- Modify: `tools/lint_artifact_contamination.py:44`（默认树缺失处理）+ 头部 docstring Exit codes 段（missing tree 由 2 改述为 skip-0）
- Modify: `tools/check_severity_vocab.py:99`（默认树 novel-output 缺失时显式 skip——否则 T1504 后恒绿空转成 dead gate）
- Modify: `tests/unit/config/test_production_config_coherence.py:11`、`tests/unit/audit/test_write_audit_glob.py:31-32`（输入迁移 tests/fixtures）
- Delete: `novel-output/**`（1150 文件，前向删除）

**复杂度:** infra（触及 just check 依赖的 lint 工具与测试输入）· **test_kind:** regression_guard

- [ ] **Step 0: 出库前引用面迁移（C1）**——两个直读 novel-output 的测试输入改为 `tests/fixtures/` verbatim 副本（G0.9 真实产物 + provenance 注释指向原产树）：
  - `tests/fixtures/production-config/xinghuo-ranqiong/{genre-config.json,pipeline-state.json}` ← `novel-output/xinghuo-ranqiong/` 对应文件逐字复制；`test_production_config_coherence.py:11` 改 `PRODUCTION_DIR = Path(__file__).resolve().parents[2] / "tests/fixtures/production-config/xinghuo-ranqiong"`
  - `tests/fixtures/write-audit-glob/test-validation/` ← `novel-output/test-validation/`（write-audit.jsonl 及其 glob 面所需文件）；`test_write_audit_glob.py:31-32` 同式改指 fixtures，docstring「生产实证复现」注记 provenance（原树 novel-output/test-validation，出库前副本）
  - 迁移后 `uv run pytest tests/unit/config/test_production_config_coherence.py tests/unit/audit/test_write_audit_glob.py -v --no-cov` → 全绿

- [ ] **Step 1: lint_artifact_contamination 缺失树处理**——`main()` 入口处加：

```python
    if not args.tree.exists():
        print(f"artifact-contamination: tree {args.tree} absent — nothing to lint (skip)")
        return 0
```

（工具非 src/，print 允许——与该文件现有输出风格一致；头部 docstring Exit codes 段同步改述：missing tree = skip exit 0）
- [ ] **Step 1b: check_severity_vocab 同型处理**——`main()`/入口处树缺失时 `print("severity-vocab: tree absent — nothing to scan (skip)")` 后 `return 0`（T1504 出库后该门的默认树消失，显式 skip 优于静默空转）
- [ ] **Step 2: .gitignore 清理**——L93-99 区改为：

```
novel-output/
novel-*/
pipeline.log
```

（死行 `novel-output/`+反忽略组删除；`novel-*/` `pipeline.log` 为 F1020 新条目——run_pipeline.sh:6,13-14 产物）
- [ ] **Step 3: F1039**——justfile clean 的 `rm -rf tests/coverage/` 改 `mkdir -p tests/coverage && find tests/coverage -mindepth 1 ! -name .gitkeep -delete`（跟踪的 .gitkeep 保留；目录缺失也不失败）
- [ ] **Step 4: T1504 出库**——`git rm -r -q novel-output`（1150 文件前向删除；引用面已由 Step 0 迁移闭合一空）
- [ ] **Step 5: 验收 4 实跑**：`git ls-files novel-output | wc -l` → 0；`git check-ignore novel-x/pipeline.log pipeline.log novel-output/x` → 三者命中；`uv run python tools/lint_artifact_contamination.py` → skip 退出 0
- [ ] **Step 6: `just check` 全绿**（count_active_specs 等不受影响确认）
- [ ] **Step 7: Commit**：`git add .gitignore justfile tools/lint_artifact_contamination.py tools/check_severity_vocab.py tests/fixtures tests/unit/config/test_production_config_coherence.py tests/unit/audit/test_write_audit_glob.py && git rm -r -q novel-output && git commit -m "chore: C25 novel-output checkout (1150 files, forward delete) + fixture migration + gitignore dead-line cleanup + clean preserves .gitkeep (F1019/F1020/F1039/T1504, spec #63)"`

---

### Task 7: test_docs_accuracy 盲区缩小（F957）

**Files:**
- Modify: `tests/integration/test_docs_accuracy.py:15-32`

**复杂度:** leaf · **test_kind:** characterization（扩白名单与 codespan 形态后既有绿保持 + 新盲区样本变红再绿）

- [ ] **Step 1: 白名单扩为 docs/ 树内 markdown 清单**——DOCS_TO_CHECK 改为程序化枚举（保持排除生成物）：

```python
GENERATED_OR_EXEMPT = {
    "docs/skills",             # just generate 产物（sync-contracts 生成 skill 页）
    "docs/superpowers",        # 工作态文档（archive/audit-runs 历史冻结）
}
DOCS_TO_CHECK = sorted(
    str(p.relative_to(REPO_ROOT))
    for p in REPO_ROOT.glob("*.md")
) + sorted(
    str(p.relative_to(REPO_ROOT))
    for p in (REPO_ROOT / "docs").rglob("*.md")
    if not any(str(p).startswith(str(REPO_ROOT / e)) for e in GENERATED_OR_EXEMPT)
)
```

（C17 internal-links 防线覆盖 docs/superpowers；此处不重复建——分工与 spec T3.9 对齐）
- [ ] **Step 2: CODESPAN_PATTERN 放宽到含空格/路径形态**——`r"`([^`\n]+)`"`（多字符、允许空格与斜杠），路径型 codespan 解析为相对文件存在性检查仅当含 `/` 且以 docs/README 等已知前缀开头（避免误伤自然语言）
- [ ] **Step 3: 跑**：`uv run pytest tests/integration/test_docs_accuracy.py -v --no-cov`——新增面发现断链则修断链（本批 spec 改动引入的相对链接优先）
- [ ] **Step 4: Commit**：`git add tests/integration/test_docs_accuracy.py && git commit -m "test: C25 docs-accuracy blind-spot narrowing — full docs/ markdown sweep + codespan pattern widening (F957, spec #63)"`

---

### Task 8: 验收汇总 + 全量门禁

**复杂度:** infra · **test_kind:** regression_guard

- [ ] **Step 1: spec 验收 1-6 逐条实跑并粘贴 progress.md**
  1. `grep -cE 'uv run python (tools|scripts)/lint_' .github/workflows/ci.yml` = 0；`grep -c 'uvx just check' .github/workflows/ci.yml` ≥ 1；残余 `uv run (python (tools|scripts)/|pytest)` 计数 = 1 且唯一命中为 Hypothesis replay 步骤的 `pytest tests/property`（I1 裁决豁免；count_active_specs/check_module_coverage 均在替换范围内随之消失）
  2. Task 4 Step 5 输出
  3. `bash tools/pre-push-check.sh` 手跑记录（shim PATH）+ `grep -r reportUnusedFunction src/shenbi/ --include='*.py' | grep -v test_ || echo ZERO_MATCH_OK`（零命中不崩）
  4. Task 6 Step 5 输出
  5. `git diff main -- .github/workflows/codeql.yml` 摘录 + `uvx git-cliff --unreleased --strip header | head -20` dry-run
  6. `just check`（本地）+ PR CI（干净 runner）双绿对照
- [ ] **Step 2: `just check` 终跑（shim PATH）全绿 + `uv lock --check`**
- [ ] **Step 3: Commit**（如 spec 验收措辞需回写）：`git add docs/superpowers/specs/archive/2026-08-16-audit-ci-just-sync-fix-Done-PR217.md && git commit -m "docs: spec #63 execution-period revisions (SDD phase 3 review fixes + count erratum)"`
- [ ] **Step 4: 更新 .superpowers/sdd/{progress.md, spec-deviations.md}**

## 验收覆盖表

| spec 验收 | task | 验证 |
|---|---|---|
| 1 单源化结构断言 | T1/T2/T3 | pytest 结构测试 + Task 8.1 grep |
| 2 覆盖隔离 | T4 | Task 4 Step 5 三命令 |
| 3 pre-push 激活/零命中 | T5/T4 | Task 8.3 |
| 4 novel-output/忽略 | T6 | Task 6 Step 5 |
| 5 codeql/cliff | T5 | Task 8.5 |
| 6 just check ≡ CI | T2/T3/T8 | 双环境绿 |
