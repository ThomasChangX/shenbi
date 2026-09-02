# Spec #38 裸崩边界守卫 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 C12 簇 27 条裸崩/垃圾落盘 finding——全部子进程边界结构化失败、LLM stdout 提取硬化 + quarantine、CLI argparse 化、exit code 契约修复、防复发 lint。

**Architecture:** 新增 `src/shenbi/process_guard.py` 单一子进程 JSON 守卫原语(真实子进程边界专用);gate 进程内 jload 按既有 g5.py:38-48 守卫惯例逐点包裹;dispatch_helper 提取失败改 quarantine 不落目标;phase_runner main() 换 argparse(error 路径仍走 structlog JSON,保 test_logging 兼容)。

**Tech Stack:** Python 3.11+ / pathlib / structlog / pytest / just。

**Spec:** `docs/superpowers/specs/2026-08-16-audit-crash-boundary-guards-fix.md`(Revised 2026-09-02)
**Drift record:** `.superpowers/sdd/spec-deviations.md`(阶段 2 收窄:F442 剔除、F204 重钉、F403 收窄至 g5.py:59+g_reconcile.py:34)

## Global Constraints

- `src/shenbi/` 禁 `print()`(structlog);gate 检查器纯函数幂等无副作用;pathlib;conventional commits
- 状态字面量唯一定义于 `src/shenbi/status.py`(`GateStatus` :20(FAIL :24)无 BLOCKED;`CommandStatus.BLOCKED="blocked"` :47;`tools/lint_status_strings.py` 红 = Critical)——不新增裸状态字符串
- 测试 scenario 输入只引用 `tests/fixtures/` 真实产物(G0.9);rubric/scores.json 非 skill 产物,按仓内既有惯例(tests/unit/test_scoring.py:41 `sample_rubric` tmp_path 构造)允许 tmp_path 构造并在用例 docstring 声明理由
- 验证命令走 `uv run` / `just`(CI 同构);系统 python 结果不算证据
- **全部 8 个 task 均为 infra**(触及 phase_runner/scoring/gates/pipeline/trace/audit/records)→ 协调者亲自实现,TDD 红-绿,每 task commit 后 fresh-context 全量重审出 `audit-T<N>.md`

---

### Task 1 (T1a): `run_subprocess_json()` 子进程守卫原语 + 四调用点迁移

**Files:**
- Create: `src/shenbi/process_guard.py`
- Modify: `src/shenbi/phase_runner.py:113-134`(run_gate)、`src/shenbi/phase_runner.py:346`(cmd_post_score)
- Modify: `src/shenbi/scoring.py:375-391`(--gate-only)、`src/shenbi/scoring.py:417-438`(G3 前置子进程)
- Test: `tests/unit/test_process_guard.py`

**Interfaces:**
- Produces: `run_subprocess_json(cmd: list[str], *, timeout: float | None = None) -> dict[str, Any]`——永不 raise;成功 → 解析后的 JSON dict(原样,须为 dict);失败 → `{"status": <CommandStatus.BLOCKED|GateStatus.FAIL>, "error_kind": "timeout|bad_json|os_error", "raw_stdout": <尾 2000 字符>, "raw_stderr": <尾 2000 字符>, "returncode": int}`;超时状态值取 `CommandStatus.BLOCKED`(status.py:47,"blocked";勿造新字面量);bad_json/os_error 用 `GateStatus.FAIL`(status.py:20)

**实际签名核对(已实读 main HEAD):**
- `phase_runner.py:113` `def run_gate(gate: str, args: list[str]) -> dict[str, Any]:` 现捕获 `(json.JSONDecodeError, ValueError, OSError)`,**缺 TimeoutExpired**(timeout=60 在 :122)
- `scoring.py:380-391` --gate-only:`sys.argv[sys.argv.index("--type")+1]` IndexError 面(T3 管);:381-385 subprocess.run **无 timeout**;:386 `json.loads(proc_result.stdout)` 裸调
- `scoring.py:419-438` G3 前置:subprocess.run **无 timeout** + `except Exception: pass` 吞错
- `phase_runner.py:346` `json.loads(Path(scores_file).read_text(...))` 裸(文件读,该点守卫不换 helper,按 cmd_post_score 既有 FAIL 分支形态包裹,见 Step 3)

- [ ] **Step 1: 红测**——`tests/unit/test_process_guard.py`:

```python
import sys

from shenbi.process_guard import run_subprocess_json


def test_timeout_returns_blocked():
    # 子进程 sleep 超过 timeout → 结构化 blocked,不 raise
    r = run_subprocess_json([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2)
    assert r["status"] == "blocked"
    assert r["error_kind"] == "timeout"


def test_bad_json_returns_fail_with_stdout_tail():
    r = run_subprocess_json([sys.executable, "-c", "print('not json')"])
    assert r["status"] == "FAIL"
    assert r["error_kind"] == "bad_json"
    assert "not json" in r["raw_stdout"]


def test_valid_json_passthrough():
    r = run_subprocess_json(
        [sys.executable, "-c", "import json; print(json.dumps({'status':'PASS'}))"]
    )
    assert r == {"status": "PASS"}


def test_run_gate_timeout_propagates_blocked(monkeypatch, tmp_path):
    # phase_runner.run_gate 经 helper:gate 子进程超时 → BLOCKED dict 而非 TimeoutExpired traceback。
    # run_gate 显式传 timeout=60,故 monkeypatch run_subprocess_json 本体的默认时长不可行;
    # 直接 patch helper 强制 0.2s 并跑一个真实慢 gate 命令(monkeypatch sys.executable 不动,
    # 用 -m shenbi.gates.cli 走真实 CLI 的同时 patch process_guard 层 timeout 参数注入)。
    import shenbi.phase_runner as pr
    import shenbi.process_guard as pg

    monkeypatch.setattr(pg, "SUBPROCESS_TIMEOUT_DEFAULT", 0.1)
    # run_gate 传 timeout=60 会覆盖默认——所以同时 patch pr.run_gate 使用的入口:
    # 实现侧约定 run_gate 不再显式传 timeout,改用 helper 默认(见 Step 3),
    # 本测试即钉死该约定:默认 0.1s 时慢 gate 必须 blocked(python -m 启动 ~0.4s,margin 4x)。
    r = pr.run_gate("G5", ["t2-skill", str(tmp_path), str(tmp_path)])
    assert r.get("status") == "blocked"
```

Run: `uv run pytest tests/unit/test_process_guard.py -x -q` → Expected: FAIL(ModuleNotFoundError: process_guard)

- [ ] **Step 2: 实现** `src/shenbi/process_guard.py`:

```python
"""子进程 JSON 边界守卫(spec #38 T1a)。

只用于真实子进程边界(gate/scoring CLI 调用);gate 进程内文件读 jload 不在此
(T1b 按 g5.py 守卫惯例逐点处理)。永不 raise——超时/坏 JSON/OS 错误一律结构化
返回,携带 stdout/stderr 尾部上下文供诊断。
"""
from __future__ import annotations

import json
import subprocess
from typing import Any

from shenbi.logging import get_logger
from shenbi.status import CommandStatus, GateStatus

log = get_logger(__name__)

SUBPROCESS_TIMEOUT_DEFAULT = 120.0
_TAIL = 2000


def run_subprocess_json(cmd: list[str], *, timeout: float | None = None) -> dict[str, Any]:
    t = SUBPROCESS_TIMEOUT_DEFAULT if timeout is None else timeout
    r: subprocess.CompletedProcess[str] | None = None
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
    except subprocess.TimeoutExpired as e:
        log.error("subprocess_timeout", cmd=cmd[:3], timeout=t)
        return {
            "status": CommandStatus.BLOCKED,
            "error_kind": "timeout",
            "raw_stdout": "",
            "raw_stderr": str(e)[:_TAIL],
            "returncode": -1,
        }
    except OSError as e:
        return {
            "status": GateStatus.FAIL,
            "error_kind": "os_error",
            "raw_stdout": "",
            "raw_stderr": str(e)[:_TAIL],
            "returncode": -1,
        }
    try:
        out = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return {
            "status": GateStatus.FAIL,
            "error_kind": "bad_json",
            "raw_stdout": (r.stdout or "")[-_TAIL:],
            "raw_stderr": (r.stderr or "")[-_TAIL:],
            "returncode": r.returncode,
        }
    if not isinstance(out, dict):
        return {
            "status": GateStatus.FAIL,
            "error_kind": "bad_json",
            "raw_stdout": (r.stdout or "")[-_TAIL:],
            "raw_stderr": (r.stderr or "")[-_TAIL:],
            "returncode": r.returncode,
        }
    return out
```

- [ ] **Step 3: 迁移四调用点**
  - `phase_runner.py` run_gate:**不显式传 timeout**(用 helper 默认 120s;原 60s 收紧到 120s 放宽无妨——gate 子进程本应远短于此,超时语义从 crash 改 blocked 才是修复本体),body 换 `return run_subprocess_json([sys.executable, "-m", "shenbi.gates.cli", gate] + args)`
  - `phase_runner.py:346` cmd_post_score:`json.loads(...)` 包 try/except `json.JSONDecodeError` → 既有 emit_json FAIL 形态(对齐 :336-341 "Scores file not found" 分支,消息 `Scores file malformed: <path>`),exit 1
  - `scoring.py:381-391` --gate-only:换 `run_subprocess_json(...)`(默认 timeout);exit 判定见下方消费面同步项
  - `scoring.py:419-438` G3 前置:换 helper;删除 `except Exception: pass`,helper 返回的 FAIL dict → `emit_json(gate_out); sys.exit(1)`
  - **下游消费面同步(blocked 不得静默变 PASS/OK)**:
    - `phase_runner.py:282` cmd_post_skill:`if g4_status == "FAIL":` → `if g4_status in ("FAIL", "blocked"):`(超时 G4 走同一 BLOCKED + exit 1 分支);同法 grep run_gate 全部消费点(`grep -n "run_gate(" src/shenbi/phase_runner.py`)逐个核:非 PASS 状态皆不得落入 OK 出口(例外:`phase_runner.py:267` G2 为 echo-only 非阻断消费方,blocked 与既有 FAIL 同待遇,已安全勿收紧)
    - `scoring.py:390` --gate-only exit 判定:`sys.exit(0 if gate_output.get("status") not in ("FAIL", "blocked") else 1)`
    - `scoring.py:435` G3 前置:helper 返回 blocked/FAIL 皆 `emit_json + sys.exit(1)`(同 bad_json 分支,不静默续行)
- [ ] **Step 4: 绿测** `uv run pytest tests/unit/test_process_guard.py -q` + 既有 phase/score 回归 `uv run pytest tests/unit -k "gate or score or phase" -q` → PASS
- [ ] **Step 5: Commit** `git add src/shenbi/process_guard.py src/shenbi/phase_runner.py src/shenbi/scoring.py tests/unit/test_process_guard.py && git commit -m "fix: T1a run_subprocess_json unified subprocess guard — F106/F107(subprocess面)/F125残余/F204重钉/F124 (spec #38)"`

---

### Task 2 (T1b): gate 进程内 jload 守卫扫尾

**Files:**
- Modify: `src/shenbi/gates/g5.py:59`、`src/shenbi/gates/g_reconcile.py:34`
- Test: `tests/unit/gates/` 既有 g5/g_reconcile 测试文件扩展(`ls tests/unit/gates/` 定名;无则新建 test_g5_guard.py)

**Interfaces:** 无新接口——按 `g5.py:38-48` 既有守卫形态(`except (json.JSONDecodeError, OSError, ValueError): return fail(...)`)逐点包裹。守卫无副作用(纯函数幂等)。

- [ ] **Step 1: 红测**(两处各一):t1-report 文件内容 `{bad`(tmp_path 写)→ `gate_G5(...)` 返回含 `G5.1:<skill>:report_unreadable` 的 fail 字符串而非 raise;progress.json 内容 `{bad` → `gate_G_RECONCILE(...)` 返回 fail(`progress.json unreadable or malformed`)而非 raise
- [ ] **Step 2: 跑红** `uv run pytest tests/unit/gates -k "unreadable or malformed" -q` → FAIL(traceback)
- [ ] **Step 3: 实现**:g5.py:59 `rdata = jload(str(report))` 包 try → `mf.append(f"G5.1:{pr}:report_unreadable")` + score 保持 0;g_reconcile.py:34 `progress = jload(str(pp))` 包 try → `return fail("G_RECONCILE", [], "reconcile", ["progress.json unreadable or malformed"])`
- [ ] **Step 4: 绿测** + 全 gates 回归 `uv run pytest tests/unit/gates -q`
- [ ] **Step 5: Commit** `git add src/shenbi/gates/g5.py src/shenbi/gates/g_reconcile.py tests/unit/gates/ && git commit -m "fix: T1b guarded jload sweep g5/g_reconcile — F403 residual (spec #38)"`

---

### Task 3 (T2a): codex JSON 提取候选化(F203)

**Files:**
- Modify: `src/shenbi/dispatcher/modes/codex.py:131`(`re.search(r"\{[^{}]*\}")` 最内层扁平)
- Test: `tests/unit/dispatcher/` 既有 codex 测试扩展(`ls tests/unit/dispatcher/` 定名;无则新建)

**Interfaces:**
- Produces: `_extract_json_object(text: str) -> dict[str, Any]`(module 私有,无有效对象 → `SubAgentProtocolError`)——策略:`json.JSONDecoder().raw_decode` 从每个 `{` 位置尝试,候选中**含嵌套 dict 值的最外层合法对象**优先;均扁平且多个 → raise(不猜)

- [ ] **Step 1: 红测**:嵌套输出(正文包裹 `Here is the result: {"scores": {"维度A": 88}, "summary": "..."} done`)→ 现正则取最内层 `{"维度A": 88}`;断言新行为:返回完整外层对象(含 summary 键)
- [ ] **Step 2: 跑红** → FAIL
- [ ] **Step 3: 实现** `_extract_json_object`;调用点 :131 换用
- [ ] **Step 4: 绿测** + `uv run pytest tests/unit/dispatcher -q`
- [ ] **Step 5: Commit** `git add src/shenbi/dispatcher/modes/codex.py tests/unit/dispatcher/ && git commit -m "fix: T2a codex JSON extraction all-candidates + schema discrimination — F203 (spec #38)"`

---

### Task 4 (T2b): `_write_parsed_outputs` 回退删除 + quarantine + 截断拒绝 + 提取器硬化(F329/T509/F234/F223)

**Files:**
- Modify: `src/shenbi/pipeline/dispatch_helper.py:1455-1457`(回退)、`_parse_file_outputs`(:977 截断面)、`src/shenbi/contracts/paths.py:155-162`(extract_chapter)、`src/shenbi/contracts/skills/pacing_design.py:85-92`(from_markdown)
- Test: `tests/pipeline/test_quarantine.py`(新)

**Interfaces:**
- Produces: `_quarantine_output(project_dir: Path, skill: str, raw: str, reason: str) -> Path`——写 `<project_dir>/_quarantine/<skill>-<utc时间戳>.md`(mkdir parents,原样 raw,首行 reason 注释),返回路径;structlog `log.error("output_quarantined", ...)`
- 行为契约:literal 路径在 `parsed` 无匹配 → **不写目标、不回退 `__stdout__`**,quarantine + 该路径计 FAIL;`__stdout__` 作为契约声明路径的路由(:1468 wildcard 循环 `if rel_path == "__stdout__": continue` 之前的显式分支)保留
- 截断拒绝:最后输出以未闭合的 `### FILE:` 块结束(末个 FILE: 后无有效内容直至文本尾)→ 整轮拒绝(quarantine 原始 stdout + 结构化失败),**独立于 C29 标记协议**
- `extract_chapter(text: str, *, strict: bool = False) -> int | None`:strict 下多个**不同**非零章号 → raise `AmbiguousChapterError`(新异常,`contracts/paths.py` 定义);默认行为不变(grep 调用方后 G4 路由处接 strict,其余不动)
- `from_markdown`:beat/line 百分比提取限定**结构行**(表格行 `|`、紧凑 `XX: n%`、`XX | n%` 形态)内匹配,散文句中数字不采;无命中 → 该键缺省不猜

- [ ] **Step 1: 红测**(`tests/pipeline/test_quarantine.py`;`### FILE:` 形态输入取 `tests/fixtures/` 真实 skill 输出剪裁;quarantine 断言用 tmp project_dir):
  1. `parsed={"a.md": "..."}` 但 contract literal 含 `b.md` → 目标 `b.md` 不存在、`_quarantine/` 出现文件、含 raw
  2. `__stdout__` 在 contract 声明 → 正常落盘(回归保护)
  3. 截断输入(真实 FILE 输出剪尾)→ 拒绝 + quarantine
  4. `extract_chapter("chapter 3 ... chapter 7", strict=True)` → raise;单章仍返回;默认多章仍首个(回归)
  5. `from_markdown`:散文 "第 3 章预算 25% 用于铺垫" → beats 为空;表格行 `铺垫 | 25%` → 采集
- [ ] **Step 2: 跑红** → 全 FAIL
- [ ] **Step 3: 实现**(逐条;先 grep `_write_parsed_outputs` 调用方确认返回/FAIL 汇合点)
- [ ] **Step 4: 绿测** + `uv run pytest tests/pipeline -q`(既有依赖 literal 回退的测试若翻红:按收紧语义改期望——垃圾落盘改 FAIL 是本 spec 预期,记 deviation)
- [ ] **Step 5: Commit** `git add src/shenbi/pipeline/dispatch_helper.py src/shenbi/contracts/paths.py src/shenbi/contracts/skills/pacing_design.py tests/pipeline/ && git commit -m "fix: T2b quarantine + truncation rejection + extractor hardening — F329/T509/F234/F223 (spec #38)"`

---

### Task 5 (T3): CLI argparse 化 + 参数哨兵(F102/F123/F135/F437/F107 argv 面/F337 残余/F1018)

**Files:**
- Modify: `src/shenbi/phase_runner.py:390-438`(main)、`src/shenbi/gates/cli.py:120`(`a1.split(",")`)与 G4 dispatch 分支(~:135-142,捕 `resolve_input_path` 的 ValueError——该函数在 `gates/shared.py:65`)、`src/shenbi/scoring.py:380`(--type 缺值)、`tools/generate_autocheck_docs.py:122`
- Test: `tests/unit/test_phase_cli.py`(新)、`tests/unit/gates/` 扩展

**Interfaces:**
- `phase_runner.main()` 换 argparse 子命令,**兼容既有形态**(位置参数 + flag):`start <phase> --round-dir <dir> [--project-dir <dir>]`、`pre-skill <phase> <skill> --round-dir <dir>`、`post-skill <phase> <skill> --round-dir <dir> [--project-dir <dir>] [--chapter <int>]`、`pre-score <phase> --round-dir <dir>`、`post-score <phase> <scores_file> --round-dir <dir>`、`finalize <phase> --round-dir <dir> [--project-dir <dir>]`
- **test_logging 兼容约束**:`tests/unit/test_logging.py:169-172` 断言裸 `shenbi-phase` 在 stderr 出**JSON 日志行**——argparse 默认 error() 输出纯文本会破。实现:子类 `ArgumentParser`,`error()` 与无参路径 override 为 `log.error("usage_error", message=...)`(structlog,stderr)后 `sys.exit(2)`;`--help` 走 argparse 原生
- F102 哨兵:`project_dir` 值为 `"None"`/空串 → 视为未提供;`cmd_start`/`cmd_finalize` 内 `run_gate("G5", [phase, str(round_dir)] + ([str(project_dir)] if project_dir else []))`
- gates/cli.py G4 分支:`resolve_input_path` ValueError → `emit_json(fail(...))` 结构化输出 exit 1;`a1.split(",")` 逗号歧义:grep 现调用方,若均不含逗号文件名 → 加 `# bare-split-exempt: callers pass comma-free file lists` 注记 + 单测钉死该假设
- `tools/generate_autocheck_docs.py:122`:`_PATTERN.sub(block, ...)` → `_PATTERN.sub(lambda m: block, ...)`(防 `\g` 转义)
- `--type` 缺值(scoring.py:380):`idx + 1 < len(sys.argv)` 守卫 → usage 错误 exit 2(structlog)

- [ ] **Step 1: 红测**:
  1. `phase_runner.main()` argv=`["start", "t2-skill"]`(缺 --round-dir)→ SystemExit code 2,**stderr 含 JSON 日志行**(兼容 test_logging)
  2. argv=`["post-skill", "t2", "skill", "--round-dir", str(rd), "--chapter", "abc"]` → exit 2 非 ValueError traceback
  3. F102 哨兵:argv 含 `--project-dir None` → run_gate 收到的 args 无 "None" 字符串
  4. `--help` smoke:phase_runner/scoring/gates.cli 三入口 exit 0
  5. `shenbi-phase start t2-skill --round-dir <tmp>`(AGENTS.md 文档形态)→ 走到 G5 不 crash
- [ ] **Step 2: 跑红** → FAIL
- [ ] **Step 3: 实现**(argparse `add_subparsers`;`find_flag` 删除)
- [ ] **Step 4: 绿测** + `uv run pytest tests/unit/test_logging.py tests/unit/gates -q`;grep 调用方核对兼容:`git grep -n "shenbi-phase\|phase_runner" justfile docs/ tests/ -- ':!docs/superpowers/archive'`
- [ ] **Step 5: Commit** `git add src/shenbi/phase_runner.py src/shenbi/gates/cli.py src/shenbi/scoring.py tools/generate_autocheck_docs.py tests/ && git commit -m "fix: T3 argparse CLI protocol + None sentinel + usage errors — F102/F123/F135/F437/F107/F337/F1018 (spec #38)"`

---

### Task 6 (T4): 散点裸崩修复(F409/F509/F526/F608/F621/F626/F627/F517 双面/F614)

**Files+点面(全部已实读核对):**
- `src/shenbi/gates/g4/foreshadowing_plant.py:69`:hooks 循环加 `if not isinstance(h, dict): mf.append(f"G4.fp.hook_not_dict:{fp}"); continue`
- `src/shenbi/audit/snapshot.py:104-107`:`_diff_records` 无 id 记录(r.get("id") is None)跳过 + structlog WARN(不归 "None" 键);`:58-59` `read_text` 包 `try: ... except (UnicodeDecodeError, IsADirectoryError, OSError): log.warning(...); None`
- `src/shenbi/trace/writer.py:63`:`json.loads(ln)` 包 try → `log.warning("trace_torn_tail_skipped", seq=count)` + `break`
- `src/shenbi/skill_utils/chapter_pattern/compute_pattern.py:181`:列表推导加 `if isinstance(c, dict)` + 非 dict WARN
- `src/shenbi/trace/versioning.py:35-37`:`MIGRATIONS.get(e.schema_version)` 缺注册 → `raise ValueError(f"no migration registered from schema_version {e.schema_version}")`(替代 `_identity` 死循环)
- `src/shenbi/plugins/generate.py:50-51`:`fields.get("marketplace", "...")`/`fields.get("type", "...")` 缺省 + WARN
- `src/shenbi/dispatcher/executor.py:302-306`:finally 块整体 try/except → `log.error("audit_chain_error", ...)` + `log.error("write_audit_infra_error", ...)`(对齐 dispatch_helper.py:2438-2445 形态——那是 structlog 事件名,非函数,无既有可 grep 的函数) + rc 置 2;原 `dispatch_exc` 照旧上抛(不掩盖)
- `src/shenbi/records/parser.py:40`(F517 第二面):`yaml.safe_load(body)` 包 `except yaml.YAMLError as e: raise ValueError(f"## hooks block YAML invalid: {e}") from e`——畸形 YAML 从裸 YAMLError traceback 转结构化 ValueError;grep `parse_records` 调用方确认其对 ValueError 的处理面(消费方已按 ValueError 设计则直达;否则调用方补 except → 结构化审计失败,审计行照写——executor finally 守卫是外层兜底)
- `src/shenbi/trace/materialize.py:81`:round 提不出 → `"unknown"`(替换 `"???"`)+ WARN
- Test: `tests/unit/audit/`、`tests/unit/trace/`、`tests/pipeline/` 对应扩展

- [ ] **Step 1: 红测**(每点一用例:字符串 hooks 元素 / 无 id 记录 / 非 UTF-8 文件 / torn-tail trace / 非 dict chapter / 缺迁移 raise ValueError(而非死循环,用 `pytest.raises` + 小 timeout 保护)/ 缺 fields / finally 中 snapshot_tree monkeypatch raise → rc=2 + 原异常上抛 + infra error 落账 / `round-` 前缀缺失目录 → "unknown" / 畸形 YAML body → ValueError 非 YAMLError)
- [ ] **Step 2: 跑红** → FAIL
- [ ] **Step 3: 实现**(逐点, WARN 全走 structlog)
- [ ] **Step 4: 绿测** + `uv run pytest tests/unit/audit tests/unit/trace tests/unit/records tests/pipeline -q`(records 无测试目录则并入 pipeline)
- [ ] **Step 5: Commit** `git add src/shenbi/ tests/ && git commit -m "fix: T4 scattered crash guards — F409/F509/F526/F608/F621/F626/F627/F517/F614 (spec #38)"`

---

### Task 7 (T5): shenbi-score exit code 契约(F976)

**Files:**
- Modify: `src/shenbi/scoring.py:359`(`def main() -> dict[str, Any]:` → `-> int`)、`:550`(`return result` → `return 0`)
- Test: `tests/unit/test_score_exit_code.py`(新)

**Interfaces:** `main() -> int`(0 = 成功含 FAIL 分类输出;非 0 仅错误路径);`emit_json(result)` 输出不变。**先 grep 调用方**:`git grep -n "scoring.main\|from shenbi.scoring import main\|scoring import main" src tests` —— `tests/unit/test_scoring.py:573/748` 等消费 `main()` 返回 dict 的测试一并改(改断言为 rc==0 + stdout JSON)。

**fixture 说明(G0.9 口径):** rubric/scores.json 是框架自产 JSON 而非 skill 输出,仓内既有惯例即 tmp_path 构造(test_scoring.py:41 `sample_rubric`)——沿用,测试 docstring 声明此豁免理由;不用手写"真实产物"伪装。

- [ ] **Step 1: 红测**:(a) tmp_path rubric + scores 构造 → `subprocess.run([sys.executable, "-m", "shenbi.scoring", ...])` returncode == 0 且 stdout 合法 JSON(当前 rc=1,红);(b) `main()` 直接调用返回 0(当前返回 dict,红)
- [ ] **Step 2: 跑红** → FAIL
- [ ] **Step 3: 实现**(签名 + return;--gate-only 等 sys.exit 路径不动)
- [ ] **Step 4: 绿测** + `uv run pytest tests/unit/test_scoring.py tests/unit/test_score_exit_code.py -q`
- [ ] **Step 5: Commit** `git add src/shenbi/scoring.py tests/unit/test_score_exit_code.py tests/unit/test_scoring.py && git commit -m "fix: T5 shenbi-score exit 0 on success path — F976 (spec #38)"`

---

### Task 8 (T6): 防复发 lint

**Files:**
- Create: `tools/lint_bare_subprocess_json.py`(建模 `tools/lint_bare_writes.py`:命中 + 白名单 + 逐项豁免注记)
- Modify: `justfile` check recipe(加一行)

**Interfaces:** 规则(对齐 spec 验收 3 口径):扫描 `src/shenbi` 内 `json.loads(` 调用,**stdout/output/proc_result 相关**的必须位于 `process_guard.py` 或带 `# bare-json-exempt: <reason>` 注记;纯文件读 jload(gate shared/安全写路径)天然不属子进程边界,不匹配 stdout/output 模式即豁免——lint 输出清单与豁免注记,违规 exit 1。另附 spec 原命令等价断言:`git grep -nE "json\.loads\(" src/shenbi | grep -v process_guard` 的每项输出须带豁免注记(检查该行上下文)。

- [ ] **Step 1: 手跑清点**:`git grep -nE "json\.loads\((.*(stdout|output))" src/shenbi` → 期望仅 helper 本体;确认豁免集
- [ ] **Step 2: 实现 + 接线 just check**;`uv run python tools/lint_bare_subprocess_json.py; echo $?` → 0
- [ ] **Step 3: 验证**:`just check` 全绿(阶段 7 前置证据)
- [ ] **Step 4: Commit** `git add tools/lint_bare_subprocess_json.py justfile && git commit -m "chore: T6 bare-subprocess-json lint into just check (spec #38)"`

---

## 验收覆盖表

| spec 验收 | task | 验证命令 |
|---|---|---|
| 1 文档化命令零 traceback + --help smoke | T3/T5 | `uv run pytest tests/unit/test_phase_cli.py tests/unit/test_score_exit_code.py -q` + 手跑 AGENTS.md 三形态(start 无 project-dir / 三段式 / 评分成功) |
| 2 超时→BLOCKED / 坏 JSON→FAIL+stderr / 截断→quarantine | T1a/T2b | `uv run pytest tests/unit/test_process_guard.py tests/pipeline/test_quarantine.py -q` |
| 3 裸 json.loads 清零/豁免注记 | T6 | `uv run python tools/lint_bare_subprocess_json.py; echo $?` → 0 |
| 4 just check 全绿 | 全部 | `just check` |
