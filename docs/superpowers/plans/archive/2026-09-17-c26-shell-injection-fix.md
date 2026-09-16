# C26 shell/just 包装层注入修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 封死 justfile recipe 参数注入面（F1031/F1032）、把 run_pipeline.sh 降级为零状态写入的 smoke 工具（F002/F003/F1013/F1014/F1035/T1203/T1205）、修 README 快速开始（F902/F1030）、加 shellcheck 防线。

**Architecture:** justfile 统一改 positional-arguments 模式（`set shell := ["bash","-cu"]` + recipe 体用 `"$1"`/`"${@:N}"`，签名不变）；run_pipeline.sh 全部 `python3 -c` 拼接改 heredoc/argv，自动 approve 与 state 写入全删（裁决 B），状态提取改 JSON 解析；防线 = PATH-stub 注入矩阵测试（先例 `tests/test_round_exec_injection.py`）+ shellcheck（pre-commit mirror + `just check`）。零 `src/shenbi/` 生产代码改动。

**Tech Stack:** just 1.52、bash（bash-3.2 安全惯用法）、pytest（subprocess 驱动）、shellcheck-py、pre-commit。

## Global Constraints

- recipe 签名（参数名/默认值）不变，用户面零感知；唯一例外：`pipeline-init` 增补性 `*args` 透传（T2.8）
- 禁 `python3 -c` 字符串拼接；python 脚本经 heredoc（`python3 - args <<'PY'`）或 tools/ 辅助文件 argv 传参
- 禁裸 `"${A[@]}"`（bash<4.4 + `set -u` 报 unbound variable）——用分支拼接或 `${A[@]+"${A[@]}"}`
- 验收离线（F947）：禁真实 `shenbi-dispatch`/`pipeline` LLM dispatch；stub 目标是 `uv` 本身（PATH 前置 fake `uv`——`uv run` 把 venv bin 前置 PATH，stub `pipeline`/`shenbi-dispatch` 会被真入口遮蔽）
- `just --dry-run` 输出剥 shell 引号，不作注入修复的充分证据（只作 README 验收形态证据）
- 环境同构：一切验证走 `just`/`uv run`；测试标记 `@pytest.mark.unit`
- conventional commits；commit 显式列文件路径，禁 `git add -A`

## 验收覆盖表（spec 验收 → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| 1 注入矩阵六类样本 × 全含参 recipe，argv 字面量到达 | T1+T2 | `uv run pytest tests/test_justfile_injection.py -v` |
| 2 run_pipeline.sh 恶意路径响亮报错、无任意 Python | T3+T4 | `uv run pytest tests/test_run_pipeline_smoke.py -v` |
| 3 ESCALATION 停人工 checkpoint、零 state 写入 | T3+T4 | 同上（ESCALATION 用例 + state mtime/内容不变断言） |
| 4 README 快速开始离线验证 | T2 | `uv run pytest tests/test_justfile_injection.py -v`（--auto 透传用例）+ `just --dry-run pipeline-init` 人工核 |
| 5 shellcheck 全 *.sh 零 error + 头注释规约 + just check 绿 | T2+T5 | `uv run shellcheck <5 个 .sh>` + `just check` |

## 文件结构

- Modify: `justfile`（T2）、`run_pipeline.sh`（T4）、`README.md`（T2）、`.pre-commit-config.yaml`（T5）、`pyproject.toml`/`uv.lock`（T5 dev 依赖）
- Create: `tests/test_justfile_injection.py`（T1）、`tests/test_run_pipeline_smoke.py`（T3）、`tools/extract_json_field.py`（T4）

---

### Task 1: justfile 注入矩阵 harness（红）

**Files:**
- Create: `tests/test_justfile_injection.py`

**Interfaces:**
- Produces: `make_uv_stub(tmp_path, canned=None) -> Path`（返回 stub bin 目录；环境变量 `STUB_UV_OUT` 记录 argv、`STUB_UV_CANNED` 回放 canned 输出）；`parameterized_recipes() -> dict[str, list[str]]`（从 justfile 文本机械解析含参 recipe → 每条一组样本调用 argv）

**test_kind:** tdd_red_green（当前 justfile 必须红）

- [ ] **Step 1: 写失败测试**

```python
"""C26 / F1031+F1032 (spec #64): every parameterized justfile recipe must pass
arguments as literal argv entries — no shell re-parsing of interpolated values.

Mechanism: a fake ``uv`` is prepended to PATH (stubbing ``pipeline`` or
``shenbi-dispatch`` themselves is useless — ``uv run`` prepends the project
venv bin to PATH, shadowing them). The stub records every invocation's argv
to $STUB_UV_OUT. A recipe body that textually interpolates ``{{param}}``
unquoted lets ``;``-style payloads execute in the recipe shell (marker file
appears) and word-splits the payload; the positional-arguments pattern
(``"$1"`` / ``"${@:4}"``) delivers them inert.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Six sample classes from the spec (T1.3). Marker variants prove zero
# execution; the payload string itself must arrive as ONE argv entry.
MARKER = "pwned-by-just-recipe"
SAMPLES = [
    f"p; touch {MARKER}",
    "p$(touch pwned-cmdsub)",
    "p`touch pwned-backtick`",
    "it's quoted",
    'say "hello world"',
    "中文提示词 空格",
]

STUB = """#!/usr/bin/env bash
printf '%s\\n' "$@" >> "${STUB_UV_OUT:?}"
[ -z "${STUB_UV_CANNED:-}" ] || cat "${STUB_UV_CANNED}"
exit 0
"""


def make_uv_stub(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    (bin_dir / "uv").write_text(STUB, encoding="utf-8")
    (bin_dir / "uv").chmod(0o755)
    return bin_dir


def run_just(env_extra: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_extra)
    return subprocess.run(
        ["just", *args], capture_output=True, text=True, timeout=60, cwd=REPO_ROOT, env=env
    )


def stub_lines(tmp_path: Path) -> list[str]:
    out = tmp_path / "uv.args"
    return out.read_text(encoding="utf-8").splitlines()


# Mechanical derivation (spec T1.3): parse the justfile for recipe headers
# that declare parameters — a hand-maintained list would let new recipes
# escape the matrix.
def parameterized_recipes() -> dict[str, list[str]]:
    text = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
    recipes: dict[str, list[str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        # Recipe headers are column-0 in this justfile; indented lines are
        # recipe bodies (whose `=`/`:` flags would misfire the header regex).
        if not stripped or line[:1].isspace() or stripped.startswith(("#", "@", "-", "set ")):
            continue
        candidate = stripped.rstrip(":")
        if ":" not in stripped or " " not in candidate:
            continue
        name, _, params = candidate.partition(" ")
        if not name or not params or "{{" in line:
            continue
        if not name.replace("-", "").isalnum() or name[0].isdigit():
            continue
        # Header (ends with ':') whose parameter list is non-empty
        if stripped.endswith(":") or "=" in params:
            recipes[name] = []
    return recipes


EXPECTED_CALLS: dict[str, list[list[str]]] = {
    # recipe -> per-sample argument vectors (payload placed at the natural-
    # language position). All of these route through `uv`, so the stub
    # intercepts every one — no side effects, no LLM.
    "install": [["dev"], ["dev; touch pwned"]],
    "test": [["-q"]],
    "test-all": [["-q"]],
    "test-file": [["tests/test x.py"]],
    "audit-lint": [["--help"]],
    "gate": [["G0"], ["G0; touch pwned"]],
    "dispatch": [
        ["shenbi-x", "generative", "/tmp/r", "p; touch pwned-by-just-recipe"]
    ],
    "pipeline-init": [
        ["seed.md"], ["seed.md", "/tmp/dir with space", "--auto"],
    ],
    "pipeline-status": [["/tmp/dir; touch pwned"]],
    "pipeline-review": [
        ["/tmp/d", "approve", "needs work; fix it"],
    ],
    "pipeline-resume": [["/tmp/dir $(touch pwned-cmdsub)"]],
}


@pytest.mark.unit
def test_matrix_all_parameterized_recipes_pass_literals(tmp_path: Path) -> None:
    """Every recipe in EXPECTED_CALLS delivers payloads as literal argv."""
    bin_dir = make_uv_stub(tmp_path)
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "STUB_UV_OUT": str(tmp_path / "uv.args"),
    }
    for recipe, calls in EXPECTED_CALLS.items():
        for call in calls:
            proc = run_just(env, recipe, *call)
            assert proc.returncode == 0, f"{recipe} {call}: {proc.stderr}"

    lines = stub_lines(tmp_path)
    # Zero execution: no marker anywhere in the repo root (pwned = the bare
    # `touch pwned` variants used by the install/gate rows).
    for marker in (
        REPO_ROOT / MARKER,
        REPO_ROOT / "pwned-cmdsub",
        REPO_ROOT / "pwned-backtick",
        REPO_ROOT / "pwned",
    ):
        try:
            assert not marker.exists(), f"injection executed: {marker}"
        finally:
            marker.unlink(missing_ok=True)
    # F1031: the `;` payload reaches the stub as ONE argv entry.
    assert "p; touch pwned-by-just-recipe" in lines, "dispatch payload not literal argv"
    # F1032: feedback with spaces/`;` stays one argv entry after --feedback.
    assert "needs work; fix it" in lines
    # F1030/--auto passthrough: `--auto` reaches the pipeline CLI argv.
    assert "--auto" in lines
    # No recipe line word-split the space-containing project dir.
    assert "/tmp/dir with space" in lines


@pytest.mark.unit
def test_matrix_covers_every_parameterized_recipe() -> None:
    """Guard against new parameterized recipes escaping the matrix."""
    expected = set(EXPECTED_CALLS)
    actual = set(parameterized_recipes())
    missing = actual - expected
    assert not missing, f"recipes missing from EXPECTED_CALLS: {missing}"
```

- [ ] **Step 2: 跑测试确认红**

Run: `uv run pytest tests/test_justfile_injection.py -v`
Expected: 双 FAIL——主测试红（当前 `{{prompt}}` 无引号插值：marker 文件出现 / argv 拆散 / `--auto` 透传缺失）；coverage 守护测试对当前 justfile 应 PASS（含参 recipe 集 = EXPECTED_CALLS 键集——若红了先修 parser 再继续）

- [ ] **Step 3: Commit**

```bash
git add tests/test_justfile_injection.py
git commit -m "test: c26 justfile injection matrix harness (red) — six sample classes x parameterized recipes (spec #64 F1031/F1032)"
```

---

### Task 2: justfile positional-args 重写（绿）+ README 修复

**Files:**
- Modify: `justfile`（全部含参 recipe 体 + 顶部 `set shell` + 头注释规约）
- Modify: `README.md:45`（`--auto` 例子已可用，保持原文——透传落地后该行即为真）

**Interfaces:**
- Consumes: Task 1 的 `EXPECTED_CALLS` 断言集
- Produces: recipe 签名不变；`pipeline-init seed project_dir="" *args` 新增透传

- [ ] **Step 1: justfile 顶部加 shell 设置与规约头注释**

在 `set positional-arguments := true` 后加：

```
# Recipe-authoring covenant (spec #64 C26 / F1031): recipes taking
# natural-language or flag-value parameters MUST NOT interpolate {{param}}
# into the shell line (just substitutes textually BEFORE the shell parses,
# so `;`/`$()` in the value execute). Use positional references ("$1",
# "${@:N}") — see tests/test_justfile_injection.py. `${@:N}` is bash-only,
# hence the explicit bash shell below (dash would abort: Bad substitution).
set shell := ["bash", "-cu"]
```

- [ ] **Step 2: 逐 recipe 重写体（签名不变）**

```
install group="dev":
    uv sync --group "$1"

test *args:
    uv run pytest -n auto -m "unit" --no-cov "$@"

test-file file:
    uv run pytest "$1" -v --no-cov

audit-lint *args:
    uv run python tools/lint_audit_run.py "$@"

gate name *args:
    uv run shenbi-validate "$1" "${@:2}"

dispatch skill test_type round_dir *prompt:
    uv run shenbi-dispatch "$1" "$2" "$3" "${@:4}"

pipeline-init seed project_dir="" *args:
    if [ -n "$2" ]; then uv run pipeline init "$1" --project-dir "$2" "${@:3}"; else uv run pipeline init "$1" "${@:3}"; fi

pipeline-status project_dir:
    uv run pipeline status "$1"

pipeline-review project_dir decision feedback="":
    if [ -n "$3" ]; then uv run pipeline review "$1" "$2" --feedback "$3"; else uv run pipeline review "$1" "$2"; fi

pipeline-resume project_dir:
    uv run pipeline resume "$1"
```

要点：分支拼接用**单行 if/else**（just 1.52 对 recipe 体内多行块的缩进报 `recipe line has extra leading whitespace`，多行块非法）；无数组，规避 bash-3.2 `set -u` 空数组坑；just 对带默认值参数恒按位传参所以 `[ -n "$N" ]` 判空有效。

- [ ] **Step 3: 跑 Task 1 测试确认绿 + 手工双形态验证**

Run: `uv run pytest tests/test_justfile_injection.py -v`
Expected: 2 passed

Run: `just --dry-run dispatch shenbi-worldbuilding generative /tmp/round "p; echo PWNED"` 与 `just --dry-run pipeline-review ./my-novel approve "needs work; fix it"`（README 验收 4 形态证据，dry-run 剥引号属预期——真证据在 stub 测试）
Expected: 展示的命令行含 `"$1"`/`"$3"` 位置引用而非 payload 文本拼接

Run: `uv run pytest tests/test_justfile_injection.py -q && just --dry-run pipeline-init outline-example.md ./my-novel --auto`
Expected: `uv run pipeline init outline-example.md --project-dir ./my-novel "--auto"`（README:45 例子可跑）

- [ ] **Step 4: 全量快测确认无回归**

Run: `just test`
Expected: 全绿（recipe 体改动不影响 pytest 收集）

- [ ] **Step 5: Commit**

```bash
git add justfile README.md
git commit -m "fix: c26 justfile positional-args hardening — kill {{param}} interpolation in all parameterized recipes, pipeline-init *args passthrough (spec #64 F1031/F1032/F1030)"
```

（README 若无需改则不加 pathspec；harness 已在 T1 提交，不重复列）README 验收 4 说明：`pipeline-status`/`pipeline-resume` 两行由 EXPECTED_CALLS 对应 stub 行覆盖（argv 形态级），init/review/dispatch 另有 dry-run 人工核。

---

### Task 3: run_pipeline.sh smoke 化测试（红）

**Files:**
- Create: `tests/test_run_pipeline_smoke.py`

**Interfaces:**
- Consumes: Task 1 的 `make_uv_stub`（import：`from tests.test_justfile_injection import make_uv_stub`——若 tests 无包结构则复制函数，见 Step 1 注）
- Produces: 无

**test_kind:** tdd_red_green

- [ ] **Step 1: 写失败测试**

```python
"""C26 / F002+F003+F1013+F1014+F1035+T1203+T1205 (spec #64): run_pipeline.sh
must be a smoke tool — loud failure on hostile paths, zero state writes,
never auto-approving checkpoints. Offline: a fake ``uv`` on PATH replays
canned `pipeline resume` output (stubbing ``pipeline`` itself is useless —
``uv run`` prepends the venv bin to PATH).
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "run_pipeline.sh"

# T1205 replay: balanced-paren Python breakout payload in PROJECT_DIR.
HOSTILE_DIRS = [
    "x') and __import__('os').system('touch pwned-by-rp') and ('1",
    "dir with space",
    "dir( paren )",
]
# F1014/F002: an error message containing the over-broad grep words must NOT
# be auto-approved (canned output replays a fake "error" status whose text
# mentions escalation/gate/dispatch).
CANNED_ERROR = json.dumps(
    {"status": "error", "error": "dispatch failed inside gate escalation path"}
)
CANNED_ESCALATION_BLOCKED = json.dumps(
    {"status": "blocked", "checkpoint": "ESCALATION", "phase": "chapter_loop"}
)


def _run_script(tmp_path: Path, project_dir: str, canned: str) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir(exist_ok=True)
    canned_file = tmp_path / "canned.txt"
    canned_file.write_text(canned + "\n", encoding="utf-8")
    # Stub records EVERY invocation first (incl. `pipeline review`), replays
    # canned output only for `resume` — record-after-replay would make the
    # "no review issued" assertion vacuous.
    (bin_dir / "uv").write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$@" >> "${STUB_UV_OUT:?}"\n'
        '[ "$3" = "resume" ] && cat "$STUB_UV_CANNED"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    (bin_dir / "uv").chmod(0o755)
    env = os.environ.copy()
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        STUB_UV_CANNED=str(canned_file),
        STUB_UV_OUT=str(tmp_path / "uv.args"),
    )
    return subprocess.run(
        ["bash", str(SCRIPT), project_dir, "1"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
        env=env,
    )


@pytest.mark.unit
@pytest.mark.parametrize("dirname", HOSTILE_DIRS)
def test_hostile_project_dir_loud_failure_no_python_breakout(tmp_path: Path, dirname: str) -> None:
    # Vacuity guard (precedent tests/test_round_exec_injection.py): the
    # and-form breakout payload needs a literal `<tmp>/x` for open() to
    # succeed before the and-chain reaches os.system — without it the
    # pre-fix script silently takes the inert path and the test is vacuous.
    (tmp_path / "x").write_text("{}", encoding="utf-8")
    proc = _run_script(tmp_path, str(tmp_path / dirname), CANNED_ERROR)
    marker = REPO_ROOT / "pwned-by-rp"
    try:
        assert not marker.exists(), "T1205 python breakout executed"
    finally:
        marker.unlink(missing_ok=True)
    # F1035: not a silent death — some diagnostic reached stderr/stdout.
    assert proc.returncode != 0
    assert "FATAL" in proc.stdout + proc.stderr or "error" in (proc.stdout + proc.stderr).lower()


@pytest.mark.unit
def test_escalation_blocked_stops_without_approve_or_state_write(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()
    state = proj / "pipeline-state.json"
    state.write_text(json.dumps({"chapter_loop": {"step_index": 3}}), encoding="utf-8")
    before = state.read_text(encoding="utf-8")
    proc = _run_script(tmp_path, str(proj), CANNED_ESCALATION_BLOCKED)
    assert proc.returncode == 3
    assert "manual review required" in proc.stdout
    # F002: no `pipeline review` invocation ever issued...
    calls = (tmp_path / "uv.args").read_text(encoding="utf-8") if (tmp_path / "uv.args").exists() else ""
    assert "review" not in calls, "auto-approve survived"
    # ...and no state JSON mutation (step_index bump / retry clear gone).
    assert state.read_text(encoding="utf-8") == before


@pytest.mark.unit
def test_error_with_gate_words_is_fatal_not_approved(tmp_path: Path) -> None:
    proc = _run_script(tmp_path, str(tmp_path / "proj2"), CANNED_ERROR)
    assert proc.returncode == 1
    calls = (tmp_path / "uv.args").read_text(encoding="utf-8") if (tmp_path / "uv.args").exists() else ""
    assert "review" not in calls, "F1014 over-broad grep still auto-approving"
```

注：若 `from tests.test_justfile_injection import ...` 不可用（tests 非包），本文件自带 stub 构造（上面已内联，无需 import）。

- [ ] **Step 2: 跑测试确认红**

Run: `uv run pytest tests/test_run_pipeline_smoke.py -v`
Expected: FAIL——引号 payload 行红于 marker 执行（vacuity guard `<tmp>/x` 就位后，pre-fix `python3 -c` 的 and-form breakout 真的 `touch pwned-by-rp`——payload 是合法 Python，失败模式是"注入可执行"而非语法破坏，T1205）；escalation 行红于 exit 2 ≠ 3 **且** uv.args 含 review（stub 先记录后回放，F002 双证据）；error 行红于 exit 2 ≠ 1 + review 记录（F1014）。空间/括号行当前即通过（python3 -c 对它们语法合法且无害）——属预期，绿在其余行

- [ ] **Step 3: Commit**

```bash
git add tests/test_run_pipeline_smoke.py
git commit -m "test: c26 run_pipeline.sh smoke-tool matrix (red) — hostile dirs, escalation stop, no auto-approve (spec #64 F002/F1014/F1035/T1205)"
```

---

### Task 4: run_pipeline.sh 重写（绿）

**Files:**
- Modify: `run_pipeline.sh`（整文件替换）
- Create: `tools/extract_json_field.py`

**Interfaces:**
- Consumes: Task 3 断言（exit code 3 = blocked 人工停点、1 = fatal、无 review 调用、state 不变）
- Produces: `tools/extract_json_field.py`（stdin 混合文本 → argv[1] 字段名 → stdout 最后一处匹配值或 `unknown`；`main(argv) -> int`）

- [ ] **Step 1: 写 tools/extract_json_field.py**

```python
#!/usr/bin/env python3
"""Extract a JSON field from mixed log+JSON output (spec #64 C26, T1203).

Reads the whole stdin text, scans it with json.JSONDecoder.raw_decode for
every JSON object, and prints the value of the requested field from the
last object that carries it (or ``unknown``). Only string-valued fields are queried today; non-scalar
values print their Python repr. Replaces the old
``grep -o '"status": "..."'`` extraction, which agent stderr log previews
could pollute (T1203) and which silently misjudged on format drift.
"""

import json
import sys


def main(argv: list[str]) -> int:
    field = argv[1]
    text = sys.stdin.read()
    decoder = json.JSONDecoder()
    best: object | None = None
    i = 0
    while i < len(text):
        j = text.find("{", i)
        if j < 0:
            break
        try:
            obj, end = decoder.raw_decode(text[j:])
        except json.JSONDecodeError:
            i = j + 1
            continue
        if isinstance(obj, dict) and field in obj:
            best = obj[field]
        i = j + end
    print(best if best is not None else "unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 2: 整文件替换 run_pipeline.sh**

```bash
#!/bin/bash
# SMOKE TOOL — drives `pipeline resume` in a loop until the first
# checkpoint/error, then STOPS and reports for human action.
#
# NOT for production runs (spec #64 C26 / F002): this script never
# approves checkpoints and never writes pipeline-state.json. On a blocked
# checkpoint, run `just pipeline-review <dir> <decision> [feedback]`
# manually, then re-run this script.
set -euo pipefail

PROJECT_DIR="${1:-novel-${USER}-$(date +%Y%m%d-%H%M%S)}"
MAX_LOOPS="${2:-5000}"

die() { echo "FATAL: $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)" || die "cannot resolve script dir"
cd "$SCRIPT_DIR" || die "cannot cd into $SCRIPT_DIR"

mkdir -p "$PROJECT_DIR" || die "cannot create project dir (hostile name?)"
exec > >(tee -a "$PROJECT_DIR/pipeline.log") 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }
machine_status() { echo "SHENBI_STATUS:$1"; }

get_field() {
    python3 tools/extract_json_field.py "$1" || echo "unknown"
}

read_step() {
    python3 - "$PROJECT_DIR/pipeline-state.json" <<'PY' || echo "unknown"
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    cl = d.get("chapter_loop", {})
    print(f"{cl.get('current_chapter', 0)}-{cl.get('step_index', 0)}")
except Exception:
    print("unknown")
PY
}

LOOP=0
while [ "$LOOP" -lt "$MAX_LOOPS" ]; do
    LOOP=$((LOOP + 1))

    OUTPUT=$(uv run pipeline resume "$PROJECT_DIR" 2>&1) || true
    STATUS=$(printf '%s\n' "$OUTPUT" | get_field status)
    CP=$(printf '%s\n' "$OUTPUT" | get_field checkpoint)
    PHASE=$(printf '%s\n' "$OUTPUT" | get_field phase)
    CURRENT_STEP=$(read_step)

    log "[$LOOP] status=$STATUS phase=$PHASE cp=${CP:-none} step=$CURRENT_STEP"

    case "$STATUS" in
        ok)
            if [ "$PHASE" = "completed" ]; then
                log "*** PIPELINE COMPLETED SUCCESSFULLY! ***"
                machine_status '{"status":"completed"}'
                exit 0
            fi
            ;;
        blocked)
            machine_status "{\"status\":\"blocked\",\"checkpoint\":\"${CP:-unknown}\"}"
            log "BLOCKED at checkpoint '${CP:-unknown}' — manual review required."
            log "    just pipeline-review \"$PROJECT_DIR\" <approve|reject|modify> [feedback]"
            exit 3
            ;;
        error|failed)
            machine_status "{\"status\":\"$STATUS\"}"
            log "Pipeline $STATUS — manual investigation required (never auto-approved)."
            printf '%s\n' "$OUTPUT" | grep -i "error\|traceback" | head -5 || true
            exit 1
            ;;
        *)
            machine_status "{\"status\":\"unexpected\",\"raw\":\"$STATUS\"}"
            die "unexpected status: $STATUS"
            ;;
    esac
done

machine_status '{"status":"max-loops"}'
log "Max loops ($MAX_LOOPS) reached."
exit 2
```

要点：python3 只经 argv/heredoc（零字符串拼接——T1205 面封死）；stuck 检测与自动 approve 全删（裁决 B——blocked 一律停，exit 3）；`get_field` 兜底 `|| echo unknown` 使 `set -e` 下 FATAL 分支可达（F1035）；grep 只用于展示行（带 `|| true`），不参与状态判定（T1203）。

- [ ] **Step 3: 跑 Task 3 测试确认绿 + 手工正样本**

Run: `uv run pytest tests/test_run_pipeline_smoke.py -v`
Expected: 全 passed

Run（验收 2 正样本——**无 state 文件目录**，确定走 `project not found` JSON error 分支、零 LLM 风险；**禁**用带 pipeline-state.json 的伪造目录直跑：`PipelineState` 全默认可加载，cmd_resume 会真 dispatch）：
```bash
d=$(mktemp -d)/"dir' with (parens)"; mkdir -p "$d"; bash run_pipeline.sh "$d" 1; echo "exit=$?"
```
Expected: 非静默——响亮 error/FATAL 诊断 + exit 1（真实 `uv run pipeline resume` 对不存在项目返回 JSON error；python 读 step 经 argv 对 hostile 名安全打印 unknown）——关键是**不静默死**

- [ ] **Step 4: Commit**

```bash
git add run_pipeline.sh tools/extract_json_field.py
git commit -m "fix: c26 run_pipeline.sh smoke-tool rewrite — argv/heredoc python (F003/F1013/T1205), drop auto-approve + state writes (F002/F1014, ruling B), loud failure (F1035), JSON status extraction (T1203)"
```

---

### Task 5: shellcheck 防线

**Files:**
- Modify: `.pre-commit-config.yaml`（新增 shellcheck-py mirror hook）
- Modify: `pyproject.toml` + `uv.lock`（dev group 加 shellcheck-py）
- Modify: `justfile`（check 链加 shellcheck 行）
- Modify: `tools/pre-push-check.sh`、`tests/round-exec.sh`、`tests/lock-tool-hashes.sh`、`tests/test-gates.sh`（如 shellcheck 报 error/warning 的机械修复）

**Interfaces:** 无代码接口；产出 = CI/pre-commit 门禁。

**test_kind:** regression_guard

- [ ] **Step 1: 加依赖与门禁**

```bash
uv add --group dev shellcheck-py
```

`.pre-commit-config.yaml`（local 段之前）加：

```yaml
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.10.0.1
    hooks:
      - id: shellcheck
        files: \.sh$
```

`justfile` check 链（`uv run shenbi-sync-contracts` 行之前）加：

```
    uv run shellcheck run_pipeline.sh tools/pre-push-check.sh tests/round-exec.sh tests/lock-tool-hashes.sh tests/test-gates.sh
```

（显式五文件清单 = 验收 5 枚举；`git ls-files '*.sh'` 可随时核对无新增遗漏——有新 .sh 时清单须更新，pre-commit 的 regex 面自动覆盖）

- [ ] **Step 2: 跑 shellcheck 修存量**

Run: `uv run shellcheck run_pipeline.sh tools/pre-push-check.sh tests/round-exec.sh tests/lock-tool-hashes.sh tests/test-gates.sh`
Expected: 初跑可能对四个未重写脚本报 SC2086/SC2155 等——逐条机械修复（加引号/`local x=$(...)` 拆分/显式 `#!/usr/bin/env bash`）；run_pipeline.sh 与 extract_json_field.py 按本 plan 构造应零报。**warning 不得静默 disable**——确需豁免的逐行 `# shellcheck disable=SCXXXX` + 理由注释。

- [ ] **Step 3: 全量门禁**

Run: `just check`
Expected: EXIT=0（含新 shellcheck 行；`uv lock --check` 因 pyproject 变更须绿——uv add 已同步 lock）

Run: `uv run pre-commit run shellcheck --all-files`
Expected: Passed

- [ ] **Step 4: Commit**

```bash
git add .pre-commit-config.yaml pyproject.toml uv.lock justfile tools/pre-push-check.sh tests/round-exec.sh tests/lock-tool-hashes.sh tests/test-gates.sh
git commit -m "chore: c26 shellcheck defense line — shellcheck-py in pre-commit + just check, fix legacy *.sh findings (spec #64 T3)"
```

---

## Self-Review 记录

- 覆盖：11/11 finding → T1/T2（F1031/F1032/F1030）、T3/T4（F002/F003/F1013/F1014/F1035/T1203/T1205）、T2 README（F902）、T5（防线/验收 5）✓
- 占位符扫描：无 TBD/「适当处理」类；全部 recipe 体与脚本为完整代码 ✓
- 类型一致：`make_uv_stub` Task 1 产 Task 3 弃用（Task 3 内联 stub，避免跨文件 import 依赖 tests 非包结构）；exit code 契约（0/1/2/3）在 T3 断言与 T4 实现一致 ✓
- G0.9：无 LLM 产物 fixture 场景（全 stub/构造 JSON 状态，非 skill 输出仿造）✓
