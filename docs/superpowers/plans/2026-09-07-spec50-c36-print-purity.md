# Spec #50 C36 print-purity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消灭 src/shenbi 的 6 处 `print()`（迁入 `cli_utils.echo`/`emit_json`），AGENTS.md/logging.md 成文三类输出通道裁决，ruff T20 执法（src/shenbi 零豁免）。

**Architecture:** 复用既有 `src/shenbi/cli_utils.py`（已含 `emit_json`）：新增 `echo(msg, *, err=False)` 人面文本函数（write+flush+BrokenPipe 语义对齐 emit_json，不用 print）。机器 JSON 两处迁 `emit_json`，人面四处迁 `echo`。lint 用 ruff 内建 T20 + 框架外 per-file-ignores，零新清单行。

**Tech Stack:** Python 3.11+, ruff (T20/flake8-print), pytest capsys, structlog（不动）。

## Global Constraints

- `src/shenbi/` 内 `print(` 零命中（剔除 `_text_fingerprint` 3 处子串误报后）——ruff T201/T203 在 src/shenbi 零 per-file-ignores
- 机器 JSON 契约：`escalation/check.py` 字节级不变（emit_json 同为 ensure_ascii=False）；`foreshadowing_recall/recall.py` 有意从 `\uXXXX` 转义变为非转义 UTF-8（JSON 语义等价，零活消费方）
- stderr 语义：`cost/report.py:135` 与 `pipeline/cli.py:1067` 保持 stderr（`err=True`）
- structlog 仍是唯一日志通道；echo/emit_json 只管 CLI 输出面，不改日志
- 验证一律 `just`/`uv run`（与 CI `uv run --frozen` 同构）
- Conventional commits；所有 commit 显式列文件路径（禁 `git add -A`）

---

### Task ### Task 1: `cli_utils.echo()` + T1 测试

**复杂度: infra**（公共模块，8 个既有消费方所在文件）· **test_kind: tdd_red_green** · **层级: T1**

**Files:**
- Modify: `src/shenbi/cli_utils.py`（在 `emit_json` 后追加）
- Create: `tests/unit/test_cli_utils.py`

**Interfaces:**
- Produces: `echo(msg: str, *, err: bool = False) -> None`——写 `msg + "\n"` 到 stdout（默认）或 stderr（err=True），flush，`BrokenPipeError → SystemExit(0)`（与 `emit_json(data: Any) -> None` 完全同语义）

- [x] **Step 1: 写失败测试** `tests/unit/test_cli_utils.py`

```python
"""T1 tests for cli_utils output channels (spec #50 / C36)."""

import json

import pytest

from shenbi.cli_utils import echo, emit_json


def test_echo_writes_stdout_with_newline(capsys):
    echo("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
    assert captured.err == ""


def test_echo_err_writes_stderr(capsys):
    echo("boom", err=True)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "boom\n"


def test_emit_json_non_escaped_utf8(capsys):
    emit_json([{"detail": "中文"}])
    captured = capsys.readouterr()
    assert captured.out == json.dumps([{"detail": "中文"}], ensure_ascii=False) + "\n"


def test_echo_broken_pipe_exits_clean(monkeypatch):
    import sys

    class _Closed:
        def write(self, _):
            raise BrokenPipeError

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", _Closed())
    with pytest.raises(SystemExit) as exc:
        echo("x")
    assert exc.value.code == 0
```

- [x] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_cli_utils.py -v`
Expected: FAIL（`ImportError: cannot import name 'echo'`）

- [x] **Step 3: 最小实现**（`src/shenbi/cli_utils.py` 追加，并更新模块 docstring 通道分工句）

```python
def echo(msg: str, *, err: bool = False) -> None:
    """Write a human-facing message to stdout (or stderr with err=True).

    Mirrors emit_json's durability semantics: flush, and a closed pipe
    (e.g. piped into head) exits cleanly rather than tracebacking.
    """
    stream = sys.stderr if err else sys.stdout
    try:
        stream.write(msg + "\n")
        stream.flush()
    except BrokenPipeError:
        raise SystemExit(0) from None
```

- [x] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_cli_utils.py -v`
Expected: 4 passed

- [x] **Step 5: Commit**

```bash
git add src/shenbi/cli_utils.py tests/unit/test_cli_utils.py
git commit -m "feat: add cli_utils.echo for human-facing output (spec #50 R1)"
```

---

### Task ### Task 2: 6 处 print 迁移

**复杂度: infra**（`pipeline/cli.py` 属 infra 模块）· **test_kind: characterization**（行为保持：stdout/stderr 流向与 JSON 负载不变）· **层级: T1**

**Files:**
- Modify: `src/shenbi/cost/report.py:135,137`
- Modify: `src/shenbi/pipeline/cli.py:1065,1067`
- Modify: `src/shenbi/skill_utils/escalation/check.py:164-168`
- Modify: `src/shenbi/skill_utils/foreshadowing_recall/recall.py:61`

**Interfaces:**
- Consumes: Task 1 的 `echo(msg, *, err=False)`；既有 `emit_json(data)`

- [x] **Step 1: cost/report.py**（先加 import `from shenbi.cli_utils import echo`，删除已不再使用的 `import sys` 仅当无其他 sys 用途——该文件 main 里只有这两处 print 用 sys，grep 确认）

```python
# :135 原: print(f"error: project dir not found: {args.project_dir}", file=sys.stderr)
echo(f"error: project dir not found: {args.project_dir}", err=True)
# :137 原: print(render_report(args.project_dir))
echo(render_report(args.project_dir))
```

- [x] **Step 2: pipeline/cli.py**（backfill 循环内；既有 `from shenbi.cli_utils import emit_json`（cli.py:30）合并为 `from shenbi.cli_utils import echo, emit_json`）

```python
# :1065 原: print(f"  Backfilled context for chapter {ch}")
echo(f"  Backfilled context for chapter {ch}")
# :1067 原: print(f"  FAILED chapter {ch}: {e}", file=sys.stderr)
echo(f"  FAILED chapter {ch}: {e}", err=True)
```

- [x] **Step 3: escalation/check.py**

```python
# 文件头 import 区：删除 import json（迁移后该文件唯一 json 用点消失，F401 会红），加 from shenbi.cli_utils import emit_json
# 原 print(json.dumps([...], ensure_ascii=False)) 整块替换：
emit_json([{"trigger": s.trigger, "detail": s.detail} for s in signals])
```

- [x] **Step 4: foreshadowing_recall/recall.py**（import 区加 `from shenbi.cli_utils import emit_json`；该文件 `json.loads` 仍在用，`import json` 保留）

```python
# 原: print(json.dumps(overdue))
emit_json(overdue)
```

- [x] **Step 5: 流向/负载表征测试**（追加到 `tests/unit/test_cli_utils.py`）

```python
def test_report_main_error_stderr(capsys, tmp_path):
    from shenbi.cost import report

    code = report.main(["report", str(tmp_path / "nope")])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert captured.err.startswith("error: project dir not found:")


def test_recall_main_json_payload(capsys, monkeypatch):
    import sys

    from shenbi.skill_utils.foreshadowing_recall import recall

    argv = [
        "prog",
        "--hooks-json",
        '[{"id": "h1", "last_reinforced": 1, "max_distance": 2}]',
        "--current-chapter",
        "10",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    recall.main()
    captured = capsys.readouterr()
    assert captured.out == '["h1"]\n'
```

（fixture 须含 `max_distance` 字段——`recall_overdue_hooks` 跳过缺该字段的 hook；测试意图是「stdout == json.dumps(overdue) + 换行」契约形态。）

- [x] **Step 6: 运行测试 + 相关回归**

Run: `uv run pytest tests/unit/test_cli_utils.py tests/unit/skill_utils/test_foreshadowing_recall.py tests/unit/skill_utils -q`
Expected: all passed

- [x] **Step 7: 全局扫描零命中**

Run: `git grep -n "print(" -- 'src/shenbi/' | grep -v _text_fingerprint`
Expected: 空输出（exit 1）

- [x] **Step 8: Commit**

```bash
git add src/shenbi/cost/report.py src/shenbi/pipeline/cli.py src/shenbi/skill_utils/escalation/check.py src/shenbi/skill_utils/foreshadowing_recall/recall.py tests/unit/test_cli_utils.py
git commit -m "fix: migrate 6 print sites to cli_utils.echo/emit_json (spec #50 R2, C36)"
```

---

### Task ### Task 3: ruff T20 执法 + 豁免成文

**复杂度: infra**（lint 配置全局生效）· **test_kind: regression_guard** · **层级: T1（负例验证）**

**Files:**
- Modify: `pyproject.toml`（`[tool.ruff.lint]` select 与 `[tool.ruff.lint.per-file-ignores]`）
- Modify: `AGENTS.md`（Python Conventions 节一句）
- Modify: `docs/framework/logging.md`（三类通道裁决正文）

**Interfaces:**
- Consumes: 无（独立于 T1/T2 代码面，但依赖 T2 完成后 src/shenbi 才能零豁免全绿）

- [x] **Step 1: pyproject.toml**

`[tool.ruff.lint]` 的 `select` 列表追加 `"T20"`（保持字母序位置按现有列表风格）。`[tool.ruff.lint.per-file-ignores]` 追加两条 + 合并一条：

```toml
"tools/**" = ["T201"]
"scripts/**" = ["T201"]
# 既有 "tests/**" = ["BLE001"] 改为（其上方解释 BLE001 的注释行一并补 T201 语义）：
"tests/**" = ["BLE001", "T201"]
```

- [x] **Step 2: 验证存量全绿**

Run: `uv run ruff check .`
Expected: 无 T20 相关错误（src/shenbi 零命中；tools/scripts/tests 豁免生效）

- [x] **Step 3: 负例验证（加临时 print → 红 → 还原）**

```bash
echo 'print("x")' >> src/shenbi/paths.py
uv run ruff check src/shenbi/paths.py   # Expected: FAIL T201
git stash push -- src/shenbi/paths.py && git stash pop   # 还原（不销毁任何既有本地改动）
uv run ruff check src/shenbi/paths.py   # Expected: PASS
```

- [x] **Step 4: AGENTS.md Python Conventions 句替换**

原句（该节末尾）："No `print()` in framework code; use structlog."
替换为："No `print()` in framework code (enforced by ruff T20, zero exemptions in `src/shenbi/`); user-facing text goes through `shenbi.cli_utils.echo` (`err=True` for stderr), machine-readable CLI stdout through `shenbi.cli_utils.emit_json` or direct `sys.stdout.write`; use structlog for logging."

- [x] **Step 5: docs/framework/logging.md 扩充**（保留既有指向 `../api/logging.md` 的链接，追加「输出通道裁决」节：structlog 日志 / cli_utils.echo 人面 / cli_utils.emit_json 或 sys.stdout.write 机器 stdout 三类，附 ruff T20 执法说明与框架外豁免清单）

- [x] **Step 6: docs/api/logging.md 一致性核查**（若该文提及 print 政策则同步；仅核查，无则零改动）

Run: `grep -n "print" docs/api/logging.md`

- [x] **Step 7: 全量门禁**

Run: `just check`
Expected: 全绿（含 ruff/format/mypy/basedpyright/两段 pytest）

- [x] **Step 8: Commit**

```bash
git add pyproject.toml AGENTS.md docs/framework/logging.md
git commit -m "feat: enforce ruff T20 print ban with 3-channel output ruling (spec #50 R1+R3, C36)"
```

---

### Task ### Task 4### Task 4

**复杂度: leaf**（机械文本编辑）· **test_kind: regression_guard**（git diff 审查）· **层级: docs**

**Files:**
- Modify: `docs/superpowers/audit-runs/2026-08-15/findings-ledger.md`（D102/F324/F616 三行）

**Interfaces:** 无代码接口。

- [x] **Step 1: 三行状态 `open` → `closed (C-36 spec #50, PR #N)`**（N = 本 PR 号，出 PR 后、合并前回填；对齐既有 F605/F627/F606 关闭行格式。顺手修正 D102 行内「2 处误报」→「3 处（chapter_drafting.py:133,141,320）」，不改证据列历史行号——仅注记现行行号已漂移）
- [x] **Step 2: `just audit-lint` 全绿**（spec #49 审计产物 lint）

Run: `just audit-lint`
Expected: exit 0

- [x] **Step 3: Commit**（与 PR 号回填同 commit）

```bash
git add docs/superpowers/audit-runs/2026-08-15/findings-ledger.md
git commit -m "docs(ledger): close D102/F324/F616 via C36 spec #50"
```

---

## 验收覆盖表（spec → task → 验证命令）

| spec 验收 | task | 验证 |
|---|---|---|
| R1 规则文本合入（AGENTS.md + logging.md） | T3 S4-5 | `git diff main -- AGENTS.md docs/framework/logging.md` 非空且含三通道句 |
| R1 src/shenbi grep 零命中 | T2 S7 | `git grep -n "print(" -- 'src/shenbi/' \| grep -v _text_fingerprint` 空 |
| R2 pytest console 用例 | T1 S1 / T2 S5 | `uv run pytest tests/unit/test_cli_utils.py -q` 全绿 |
| R2 INDEX 行号同步 | （已在阶段 3 完成 commit e12fdf45） | `grep report.py:135 docs/superpowers/specs/INDEX.md` 命中 |
| R3 负例 FAIL / 豁免 PASS | T3 S2-3 | 负例输出粘贴 progress.md |
| 簇级 just check 全绿 | T3 S6 | `just check` 完整输出粘贴 progress.md |
| G3.4 独立评分 | 不适用（无 LLM 产物评分场景；spec 验收全部为机械可验证命令） | — |
