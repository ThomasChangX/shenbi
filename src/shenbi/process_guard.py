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
            "returncode": getattr(r, "returncode", -1),
        }
    if not isinstance(out, dict):
        return {
            "status": GateStatus.FAIL,
            "error_kind": "bad_json",
            "raw_stdout": (r.stdout or "")[-_TAIL:],
            "raw_stderr": (r.stderr or "")[-_TAIL:],
            "returncode": getattr(r, "returncode", -1),
        }
    return out
