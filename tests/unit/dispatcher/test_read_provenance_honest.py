"""诚实分层（spec C2）：read-provenance 仅 internal mode 可行；codex 子进程是已知盲点。

此测试锚定该事实，防回归误声称「真闭口」。
"""

from __future__ import annotations

import inspect

from shenbi.dispatcher.modes import codex as codex_mode


def test_codex_exec_runs_as_subprocess_cannot_intercept() -> None:
    src = inspect.getsource(codex_mode)
    # codex exec 经 subprocess.run（codex.py），Python 无法拦截其 syscall
    assert "subprocess.run" in src
    assert '["codex", "exec"' in src
    # 读 provenance 需 FUSE/ptrace/seccomp（future work）——本计划不声称在子进程路径真闭口
