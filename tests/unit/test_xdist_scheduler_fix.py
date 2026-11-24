"""pytest-xdist's crash-replacement path: the backport, its wiring, its expiry.

The defect list is in tests/support/xdist_scheduler_fix.py. Every
process-level test runs a fresh ``pytest -n1`` on a two-file project in which
one test kills its worker with ``os._exit`` — what pytest-timeout does to a
test that runs past its limit. On pytest-xdist 3.8.0, unpatched, four of the
six crash runs below never finish and the other two burn every worker restart
without running the remaining test.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from collections import OrderedDict
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from xdist.scheduler.loadfile import LoadFileScheduling
from xdist.scheduler.loadgroup import LoadGroupScheduling
from xdist.scheduler.loadscope import LoadScopeScheduling

from tests.support import xdist_scheduler_fix

if TYPE_CHECKING:
    from xdist.workermanage import WorkerController

REPO = Path(__file__).resolve().parents[2]
SCHEDULERS = [LoadScopeScheduling, LoadFileScheduling, LoadGroupScheduling]
CHILD_TIMEOUT_S = 30.0
_BACKPORT_PLUGIN = "tests.support.xdist_scheduler_fix"

_OK_THEN_CRASH = {
    "test_a_ok.py": "def test_a():\n    pass\n",
    "test_b_crash.py": (
        "import os\n\n\ndef test_crash():\n    os._exit(1)\n\n\ndef test_later():\n    pass\n"
    ),
}
_CRASH_THEN_OK = {
    "test_a_crash.py": (
        "import os\n\n\ndef test_crash():\n    os._exit(1)\n\n\ndef test_ok():\n    pass\n"
    ),
}


class _Worker:
    """What the scheduler may do to a worker: hand it tests, or shut it down."""

    def __init__(self, worker_id: str) -> None:
        self.gateway = SimpleNamespace(id=worker_id)
        self.shutdown_requested = False
        self.sent: list[list[int]] = []

    @property
    def shutting_down(self) -> bool:
        return self.shutdown_requested

    def shutdown(self) -> None:
        self.shutdown_requested = True

    def send_runtest_some(self, indices: Sequence[int]) -> None:
        self.sent.append(list(indices))


class _Reports:
    """Collector of the collection reports a scheduler emits."""

    def __init__(self) -> None:
        self.reports: list[pytest.CollectReport] = []
        self.hook = SimpleNamespace(pytest_collectreport=self._collect)

    def _collect(self, report: pytest.CollectReport) -> None:
        self.reports.append(report)


def _worker(worker_id: str = "gw0") -> tuple[WorkerController, _Worker]:
    """A worker as the scheduler types it, and the same object as this file does."""
    stand_in = _Worker(worker_id)
    return cast("WorkerController", stand_in), stand_in


def _scheduler(
    cls: type[LoadScopeScheduling] = LoadScopeScheduling, items: Sequence[str] = ()
) -> LoadScopeScheduling:
    return xdist_scheduler_fix.bare_scheduler(items, cls)


def _reschedule(sched: LoadScopeScheduling, node: WorkerController) -> None:
    """Call the scheduler's own heuristic, patched or not."""
    sched._reschedule(node)


@pytest.fixture
def controller() -> Iterator[None]:
    """Pretend this process is the xdist controller, where install() is active."""
    with pytest.MonkeyPatch.context() as patch:
        patch.delenv("PYTEST_XDIST_WORKER", raising=False)
        xdist_scheduler_fix.install()
        yield


# --------------------------------------------------------------------------
# The scheduler, method by method
# --------------------------------------------------------------------------


def test_backport_is_still_needed() -> None:
    """Fails on purpose once pytest-xdist ships every fix: delete the backport.

    Message for that day: remove tests/support/xdist_scheduler_fix.py, its
    wiring in tests/conftest.py and this file, in the same pull request as the
    pytest-xdist upgrade.
    """
    leftover = xdist_scheduler_fix.remaining_defects()
    assert leftover, (
        "pytest-xdist no longer has any known crash-replacement defect: "
        "delete tests/support/xdist_scheduler_fix.py, its wiring in "
        "tests/conftest.py, and tests/unit/test_xdist_scheduler_fix.py"
    )


@pytest.mark.parametrize("scheduler_cls", SCHEDULERS, ids=lambda cls: cls.__name__)
def test_dead_worker_puts_only_unfinished_work_back(
    controller: None, scheduler_cls: type[LoadScopeScheduling]
) -> None:
    """No finished unit ahead of the real work, and the crashed test is not replayed."""
    items = ["u_done::t_ok", "u_crash::t_crash", "u_crash::t_later"]
    sched = _scheduler(scheduler_cls, items)
    node, _ = _worker()
    sched.assigned_work[node] = {
        "u_done": {"u_done::t_ok": True},
        "u_crash": {"u_crash::t_crash": False, "u_crash::t_later": False},
    }

    assert sched.remove_node(node) == "u_crash::t_crash"

    # handle_crashitem has already reported the crashed test: it is done.
    assert sched.workqueue == {"u_crash": {"u_crash::t_crash": True, "u_crash::t_later": False}}


@pytest.mark.parametrize("scheduler_cls", SCHEDULERS, ids=lambda cls: cls.__name__)
def test_worker_that_finished_everything_adds_nothing(
    controller: None, scheduler_cls: type[LoadScopeScheduling]
) -> None:
    sched = _scheduler(scheduler_cls, ["u::t"])
    node, _ = _worker()
    sched.assigned_work[node] = {"u": {"u::t": True}}

    assert sched.remove_node(node) is None
    assert sched.workqueue == OrderedDict()


def test_node_handed_a_single_test_gets_its_successor(controller: None) -> None:
    """A worker starts an item only once it knows what follows it."""
    items = ["u1::t1", "u2::t2", "u3::t3"]
    sched = _scheduler(items=items)
    node, seen = _worker()
    sched.registered_collections[node] = items
    sched.assigned_work[node] = {}
    sched.workqueue["u1"] = {"u1::t1": False}
    sched.workqueue["u2"] = {"u2::t2": False}

    _reschedule(sched, node)

    assert seen.sent == [[0], [1]]
    assert seen.shutdown_requested is False


def test_node_with_nothing_left_to_draw_is_told_to_finish(controller: None) -> None:
    sched = _scheduler(items=["u1::t1"])
    node, seen = _worker()
    sched.registered_collections[node] = ["u1::t1"]
    sched.assigned_work[node] = {}
    sched.workqueue["u1"] = {"u1::t1": False}

    _reschedule(sched, node)

    assert seen.sent == [[0]]
    assert seen.shutdown_requested is True


def test_replacement_still_collecting_is_left_alone(controller: None) -> None:
    """It cannot map test ids to indexes yet; indexing them raised KeyError."""
    sched = _scheduler(items=["u::t"])
    node, seen = _worker()
    sched.assigned_work[node] = {}
    sched.workqueue["u"] = {"u::t": False}

    _reschedule(sched, node)

    assert seen.sent == []
    assert seen.shutdown_requested is False


def test_replacement_with_another_collection_is_reported_and_stopped(
    controller: None,
) -> None:
    """Silently dropping it left it without work and blocked the session."""
    sched = _scheduler(items=["official::t"])
    sched.config = cast(pytest.Config, _Reports())
    sched.numnodes = 1
    first, _ = _worker("gw0")
    late, late_seen = _worker("gw7")
    sched.registered_collections[first] = ["official::t"]
    sched.assigned_work[late] = {}

    sched.add_node_collection(late, ["other::t"])

    assert late not in sched.registered_collections
    assert late_seen.shutdown_requested is True
    reports = cast("_Reports", sched.config).reports
    assert [(r.nodeid, r.outcome) for r in reports] == [("gw7", "failed")]


def test_matching_collection_is_registered_as_usual(controller: None) -> None:
    items = ["official::t"]
    sched = _scheduler(items=items)
    sched.config = cast(pytest.Config, _Reports())
    sched.numnodes = 1
    node, _ = _worker("gw7")
    sched.assigned_work[node] = {}

    sched.add_node_collection(node, items)

    assert sched.registered_collections[node] == items
    assert cast("_Reports", sched.config).reports == []


# --------------------------------------------------------------------------
# Whole sessions
# --------------------------------------------------------------------------


def _project(root: Path, files: Mapping[str, str]) -> Path:
    for name, body in files.items():
        (root / name).write_text(body, encoding="utf-8")
    return root


def _run_pytest_xdist(
    project: Path,
    *args: str,
    plugins: Sequence[str] = (_BACKPORT_PLUGIN,),
    env_extra: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run pytest-xdist in a separate process group; a hang fails, it never blocks."""
    # The child is a controller of its own: drop this process's xdist identity.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTEST", "COV_CORE_"))}
    env["PYTHONPATH"] = os.pathsep.join([str(REPO), env.get("PYTHONPATH", "")])
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, "-m", "pytest", "-n1", "-p", "no:cacheprovider", "-p", "no:randomly"]
    for plugin in plugins:
        cmd += ["-p", plugin]
    process = subprocess.Popen(
        [*cmd, "-v", "--no-header", *args],
        cwd=project,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=CHILD_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        pytest.fail(
            f"xdist session did not finish within {CHILD_TIMEOUT_S:.0f}s. Output tail:\n"
            f"{output[-2000:]}"
        )
    return subprocess.CompletedProcess(process.args, process.returncode, output)


@pytest.mark.parametrize("dist", ["loadscope", "loadfile", "loadgroup"])
def test_session_finishes_when_the_last_worker_dies(tmp_path: Path, dist: str) -> None:
    """The replacement runs the unfinished tests; the crashed one fails once.

    Under loadscope and loadfile the replacement used to draw the unit the
    dead worker had already finished and then wait forever (pytest-xdist
    #1323); under loadgroup it waited for a successor that never came
    (pytest-xdist #1417).
    """
    result = _run_pytest_xdist(_project(tmp_path, _OK_THEN_CRASH), f"--dist={dist}")

    assert result.returncode == 1, result.stdout
    assert "replacing crashed worker gw0" in result.stdout
    assert "crashed while running 'test_b_crash.py::test_crash'" in result.stdout
    assert "1 failed, 2 passed" in result.stdout


@pytest.mark.parametrize("dist", ["loadscope", "loadgroup"])
def test_work_the_dead_worker_never_started_still_runs(tmp_path: Path, dist: str) -> None:
    """Each replacement used to replay the crashed test until the restarts ran out."""
    result = _run_pytest_xdist(_project(tmp_path, _CRASH_THEN_OK), f"--dist={dist}")

    assert "crashed while running 'test_a_crash.py::test_crash'" in result.stdout
    assert "1 failed, 1 passed" in result.stdout


def test_conftest_carries_the_backport_into_any_run(tmp_path: Path) -> None:
    """The real wiring (tests/conftest.py), not the plugin flag used above."""
    result = _run_pytest_xdist(
        _project(tmp_path, _OK_THEN_CRASH), "--dist=loadscope", plugins=("tests.conftest",)
    )

    assert "1 failed, 2 passed" in result.stdout, result.stdout


@pytest.mark.parametrize(
    ("dist", "scheduler", "hand_out"),
    [
        ("loadscope", "loadscope.LoadScopeScheduling", "_assign_work_unit"),
        ("load", "load.LoadScheduling", "_send_tests"),
    ],
)
def test_stalled_session_fails_instead_of_hanging(
    tmp_path: Path, dist: str, scheduler: str, hand_out: str
) -> None:
    """A stall none of the fixes knows about still ends the run, with a message.

    Parametrized over both scheduler families because the watchdog's nudge is
    not the same method on each.
    """
    module, _, name = scheduler.partition(".")
    project = _project(tmp_path, {"test_ok.py": "def test_ok():\n    pass\n"})
    (project / "conftest.py").write_text(
        f"from xdist.scheduler.{module} import {name}\n"
        "# Stand-in for an unknown scheduling deadlock: nothing is ever handed out.\n"
        f"{name}.{hand_out} = lambda self, node, *args: None\n",
        encoding="utf-8",
    )

    result = _run_pytest_xdist(
        project, f"--dist={dist}", env_extra={"SHENBI_XDIST_STALL_WATCHDOG": "2,6"}
    )

    assert result.returncode == pytest.ExitCode.INTERNAL_ERROR.value, result.stdout
    assert "pytest-xdist session stalled: no worker event for" in result.stdout


def test_backport_stays_out_of_worker_processes(request: pytest.FixtureRequest) -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("PYTEST_XDIST_WORKER", "gw0")

        assert xdist_scheduler_fix.install() is False
        assert xdist_scheduler_fix.arm_stall_watchdog(request.config) is False
