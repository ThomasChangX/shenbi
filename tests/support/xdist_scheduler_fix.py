"""Backports and a stall guard for pytest-xdist's crash-replacement path.

pytest-xdist 3.8.0 (the newest release as of 2026-11) breaks in four places
when a worker dies under ``--dist loadscope`` / ``loadfile`` / ``loadgroup``.
In this repo that is pytest-timeout killing a worker whose test ran past the
limit. All four live in ``LoadScopeScheduling``, which the other two inherit.

``finished-units-requeued``
    ``remove_node`` puts every unit the crashed node ever touched back in the
    queue, finished ones included, and the replacement is handed exactly one
    unit per reschedule. It draws a finished unit, has nothing to run, and
    nothing triggers the next reschedule: deadlock (upstream #1323, #1327,
    #1378; fixed on master, unreleased).
``no-lookahead``
    A worker starts an item only once it knows the item after it. A
    replacement handed a single-test unit while work is still queued waits for
    a successor that no completion will ever trigger: deadlock (upstream
    #1417; unfixed on master).
``collecting-replacement``
    ``_reschedule`` indexes ``registered_collections`` for a replacement that
    is still collecting: ``KeyError``, and the run ends in ``INTERNALERROR``
    (upstream #1425; fixed on master, unreleased).
``crash-item-rerun``
    ``remove_node`` leaves the test that killed its worker flagged as pending,
    so each replacement runs it again and dies in turn until
    ``--max-worker-restart`` is spent, although ``handle_crashitem`` has
    already reported it failed (upstream PR #1371, open). Behind a 120s
    timeout that is up to 4 x workers timeouts before the run gives up.

:func:`install` probes the installed class for each defect and replaces only
what is still broken, so it stands down by itself as releases carry the fixes.
``tests/unit/test_xdist_scheduler_fix.py`` turns red once nothing is left, to
say the backport can be deleted. :func:`arm_stall_watchdog` covers what is not
known yet: a distributed session with no worker event for five minutes is
rescheduled, and after ten it fails with a message instead of hanging.

``tests/conftest.py`` loads it for every run, so no xdist entry point (a
recipe, the git hook or a direct ``pytest -n`` call) depends on being
remembered.
"""

from __future__ import annotations

import enum
import inspect
import os
import queue
import time
import warnings
from collections import OrderedDict
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, cast

import pytest
from xdist.report import report_collection_diff
from xdist.scheduler.loadscope import LoadScopeScheduling

if TYPE_CHECKING:
    from xdist.dsession import DSession
    from xdist.remote import Producer
    from xdist.workermanage import WorkerController

_WORKER_ENV = "PYTEST_XDIST_WORKER"
_WATCHDOG_ENV = "SHENBI_XDIST_STALL_WATCHDOG"
_HEAL_AFTER_S = 300.0
_FAIL_AFTER_S = 600.0
_FAIL_PER_TIMEOUT = 4.0
_RESCHEDULE = "_reschedule"

# The installed methods, captured before anything is patched.
_UPSTREAM_REMOVE_NODE: Callable[..., str | None] = LoadScopeScheduling.remove_node
_UPSTREAM_RESCHEDULE: Callable[..., None] = getattr(LoadScopeScheduling, _RESCHEDULE)
_UPSTREAM_ADD_NODE_COLLECTION: Callable[..., None] = LoadScopeScheduling.add_node_collection


class Defect(enum.StrEnum):
    """A way the installed loadscope scheduler family mishandles a dead worker."""

    FINISHED_UNITS_REQUEUED = "finished-units-requeued"
    NO_LOOKAHEAD = "no-lookahead"
    COLLECTING_REPLACEMENT = "collecting-replacement"
    CRASH_ITEM_RERUN = "crash-item-rerun"
    COLLECTION_MISMATCH = "collection-mismatch"


# --------------------------------------------------------------------------
# Probes: run the installed (unpatched) methods on a bare scheduler
# --------------------------------------------------------------------------


class _ProbeNode:
    """Stand-in for a WorkerController: records what the scheduler sends it."""

    def __init__(self) -> None:
        self.shutdown_requested = False
        self.sent: list[list[int]] = []

    @property
    def shutting_down(self) -> bool:
        return self.shutdown_requested

    def shutdown(self) -> None:
        self.shutdown_requested = True

    def send_runtest_some(self, indices: Sequence[int]) -> None:
        self.sent.append(list(indices))


def _node() -> WorkerController:
    """A scheduler's eye view of a _ProbeNode."""
    return cast("WorkerController", _ProbeNode())


def bare_scheduler(
    items: Sequence[str], cls: type[LoadScopeScheduling] = LoadScopeScheduling
) -> LoadScopeScheduling:
    """A scheduler holding only the state the probed methods touch.

    ``cls`` lets the tests exercise the loadfile and loadgroup subclasses, which
    inherit every method the backport replaces.
    """
    sched = object.__new__(cls)
    sched.collection = list(items)
    sched.workqueue = OrderedDict()
    sched.assigned_work = {}
    sched.registered_collections = {}
    sched.log = cast("Producer", lambda *args: None)
    return sched


def _probe_remove_node() -> set[Defect]:
    """A node that finished one unit and died inside another."""
    sched = bare_scheduler(["u_done::t_ok", "u_crash::t_crash", "u_crash::t_later"])
    node = _node()
    sched.assigned_work[node] = {
        "u_done": {"u_done::t_ok": True},
        "u_crash": {"u_crash::t_crash": False, "u_crash::t_later": False},
    }
    crashitem = _UPSTREAM_REMOVE_NODE(sched, node)
    defects: set[Defect] = set()
    if "u_done" in sched.workqueue:
        defects.add(Defect.FINISHED_UNITS_REQUEUED)
    if crashitem is None or sched.workqueue.get("u_crash", {}).get(crashitem) is not True:
        defects.add(Defect.CRASH_ITEM_RERUN)
    return defects


def _probe_reschedule() -> set[Defect]:
    defects: set[Defect] = set()
    # A replacement that is still collecting must be skipped, not indexed.
    sched = bare_scheduler(["u::t"])
    node = _node()
    sched.assigned_work[node] = {}
    sched.workqueue["u"] = {"u::t": False}
    try:
        _UPSTREAM_RESCHEDULE(sched, node)
    except KeyError:
        defects.add(Defect.COLLECTING_REPLACEMENT)
    # A node handed one single-test unit needs a successor before it can start.
    sched = bare_scheduler(["u1::t1", "u2::t2"])
    probe = _ProbeNode()
    node = cast("WorkerController", probe)
    sched.registered_collections[node] = list(sched.collection or [])
    sched.assigned_work[node] = {}
    sched.workqueue["u1"] = {"u1::t1": False}
    sched.workqueue["u2"] = {"u2::t2": False}
    _UPSTREAM_RESCHEDULE(sched, node)
    if not probe.shutdown_requested and sched._pending_of(sched.assigned_work[node]) < 2:
        defects.add(Defect.NO_LOOKAHEAD)
    return defects


def _probe_add_node_collection() -> set[Defect]:
    """Only source inspection works here: the defect is a missing branch."""
    source = inspect.getsource(_UPSTREAM_ADD_NODE_COLLECTION)
    return set() if "node.shutdown()" in source else {Defect.COLLECTION_MISMATCH}


def remaining_defects() -> set[Defect] | None:
    """Defects still present in the installed (unpatched) pytest-xdist.

    None when the installed class could not be probed, which means its
    internals changed: nothing is patched then and the process-level tests
    in tests/unit/test_xdist_scheduler_fix.py tell whether it still works.
    """
    try:
        return _probe_remove_node() | _probe_reschedule() | _probe_add_node_collection()
    except (AttributeError, IndexError, TypeError):
        return None


# --------------------------------------------------------------------------
# Replacements
# --------------------------------------------------------------------------


def fixed_remove_node(self: LoadScopeScheduling, node: WorkerController) -> str | None:
    """``remove_node`` with both crash fixes.

    Only units that still have unfinished tests go back in the queue, so the
    replacement draws something to run. The test that killed the worker is
    marked done first: ``handle_crashitem`` has already reported it failed, so
    running it again can only take the replacement down too. ``LoadScheduling``
    drops the crashed item for the same reason.
    """
    workload = self.assigned_work.pop(node)
    if not self._pending_of(workload):
        return None

    # The node crashed, identify test that crashed
    crashitem: str | None = None
    for work_unit in workload.values():
        for nodeid, completed in work_unit.items():
            if not completed:
                crashitem = nodeid
                work_unit[nodeid] = True
                break
        else:
            continue
        break
    if crashitem is None:
        raise RuntimeError("Unable to identify crashitem on a workload with pending items")

    for scope, work_unit in workload.items():
        if any(not completed for completed in work_unit.values()):
            self.workqueue[scope] = work_unit

    for other in self.assigned_work:
        self._reschedule(other)

    return crashitem


def guarded_reschedule(self: LoadScopeScheduling, node: WorkerController) -> None:
    """Upstream's ``_reschedule``, repeated until *node* can start an item.

    ``WorkerInteractor.run_one_test`` blocks on the next index before it runs
    the current one, so a node must hold two unfinished tests or know that it
    is finishing. One unit per call leaves a freshly stocked replacement that
    drew a single-test unit waiting for a successor no completion will trigger
    (upstream #1417). A replacement still collecting is skipped instead of
    being indexed (upstream #1425).
    """
    if node not in self.registered_collections:
        return
    unfinished = self._pending_of(self.assigned_work[node])
    _UPSTREAM_RESCHEDULE(self, node)
    while not node.shutting_down:
        current = self._pending_of(self.assigned_work[node])
        if current >= 2 or current <= unfinished:
            return
        unfinished = current
        _UPSTREAM_RESCHEDULE(self, node)


def guarded_add_node_collection(
    self: LoadScopeScheduling, node: WorkerController, collection: Sequence[str]
) -> None:
    """Upstream's ``add_node_collection``, minus the silent drop on a mismatch.

    A replacement whose collection differs from the official one used to stay
    unregistered and be indexed anyway. It is reported and shut down instead,
    so the session can still end (upstream master).
    """
    if self.collection_is_completed and list(collection) != self.collection:
        assert self.collection is not None
        assert self.registered_collections
        first = next(iter(self.registered_collections))
        message = report_collection_diff(
            self.collection, list(collection), first.gateway.id, node.gateway.id
        )
        self.config.hook.pytest_collectreport(
            report=pytest.CollectReport(
                nodeid=node.gateway.id, outcome="failed", longrepr=message, result=[]
            )
        )
        node.shutdown()
        return
    _UPSTREAM_ADD_NODE_COLLECTION(self, node, collection)


_REPLACEMENTS: dict[str, tuple[Defect, ...]] = {
    # loadfile and loadgroup inherit every one of these from LoadScopeScheduling.
    "remove_node": (Defect.FINISHED_UNITS_REQUEUED, Defect.CRASH_ITEM_RERUN),
    _RESCHEDULE: (Defect.NO_LOOKAHEAD, Defect.COLLECTING_REPLACEMENT),
    "add_node_collection": (Defect.COLLECTION_MISMATCH,),
}
_FIXED_METHODS: dict[str, Callable[..., Any]] = {
    "remove_node": fixed_remove_node,
    _RESCHEDULE: guarded_reschedule,
    "add_node_collection": guarded_add_node_collection,
}


def install() -> bool:
    """Replace the still-broken scheduler methods on the installed class.

    Returns True when the installed class carries the backport after this
    call. It is a no-op inside xdist worker processes, when xdist is not
    importable, and when nothing is left to fix.
    """
    if os.environ.get(_WORKER_ENV):
        return False
    already = [
        name for name in _REPLACEMENTS if getattr(LoadScopeScheduling, name) is _FIXED_METHODS[name]
    ]
    if already:
        return True
    defects = remaining_defects()
    if defects is None:
        warnings.warn(
            "tests/support/xdist_scheduler_fix.py could not probe the installed "
            "pytest-xdist scheduler, so nothing was patched; the xdist regression "
            "tests say whether the crash-replacement path still works.",
            RuntimeWarning,
            stacklevel=2,
        )
        return False
    for name, triggers in _REPLACEMENTS.items():
        if defects.intersection(triggers):
            setattr(LoadScopeScheduling, name, _FIXED_METHODS[name])
    return bool(defects)


# --------------------------------------------------------------------------
# Stall watchdog
# --------------------------------------------------------------------------


class _StallWatchingQueue(queue.Queue[tuple[str, dict[str, Any]]]):
    """DSession's event queue, reporting every quiet poll and every event."""

    def __init__(
        self,
        source: queue.Queue[tuple[str, dict[str, Any]]],
        on_event: Callable[[], None],
        on_idle: Callable[[], None],
    ) -> None:
        super().__init__()
        self._on_event = on_event
        self._on_idle = on_idle
        self.watchdog_armed = True
        while True:
            try:
                self.put(source.get_nowait())
            except queue.Empty:
                break

    def get(self, block: bool = True, timeout: float | None = None) -> tuple[str, dict[str, Any]]:
        try:
            item = super().get(block, timeout)
        except queue.Empty:
            self._on_idle()
            raise
        self._on_event()
        return item


def _thresholds(config: pytest.Config) -> tuple[float, float | None]:
    """Seconds of silence before a heal, and before a failure (None disarms it)."""
    heal, fail = _HEAL_AFTER_S, _FAIL_AFTER_S
    override = os.environ.get(_WATCHDOG_ENV, "")
    if override:
        heal_s, _, fail_s = override.partition(",")
        heal = float(heal_s)
        return heal, (float(fail_s) if fail_s else None)
    if not config.pluginmanager.hasplugin("timeout"):
        return heal, None
    timeout = cast("float | None", config.getoption("timeout", default=None))
    if not timeout or timeout <= 0:
        # Nothing bounds a test, so a slow one must not pass for a stall.
        return heal, None
    return heal, max(fail, _FAIL_PER_TIMEOUT * timeout)


def _nudge(sched: Any, node: Any) -> None:
    """One more scheduling pass for *node*: what a completed test would trigger.

    The loadscope family reschedules through ``_reschedule``, the default and
    workstealing schedulers through ``check_schedule``. Both hand out more work
    when there is some and tell the node to finish when there is none.
    """
    reschedule = getattr(sched, _RESCHEDULE, None)
    if reschedule is not None:
        reschedule(node)
    elif hasattr(sched, "check_schedule"):
        sched.check_schedule(node)


def arm_stall_watchdog(config: pytest.Config) -> bool:
    """Make a stalled distributed session recover, or fail; never hang.

    ``DSession.loop_once`` waits on the worker event queue with no deadline, so
    a scheduling stall is silent forever (every deadlock above looked like a
    run stuck at 99%). This wraps that queue. After the heal threshold without
    an event every node gets the scheduling pass a completion would have
    triggered, which repairs a missed trigger and changes nothing otherwise;
    after the fail threshold the session is shut down and the run ends with a
    message.
    """
    if os.environ.get(_WORKER_ENV):
        return False
    dsession: DSession | None = config.pluginmanager.get_plugin("dsession")
    if dsession is None or config.getoption("looponfail", default=False):
        # -f waits for file changes between loops: silence is normal there.
        return False
    if getattr(dsession.queue, "watchdog_armed", False):
        return False
    heal_after, fail_after = _thresholds(config)
    last_event = time.monotonic()

    def on_event() -> None:
        nonlocal last_event
        last_event = time.monotonic()

    def on_idle() -> None:
        nonlocal last_event
        idle = time.monotonic() - last_event
        if idle < heal_after:
            return
        if not dsession.shuttingdown:
            sched = getattr(dsession, "sched", None)
            for node in sched.nodes if sched is not None else []:
                _nudge(sched, node)
        if fail_after is not None and idle >= fail_after:
            dsession.triggershutdown()
            pytest.exit(
                f"pytest-xdist session stalled: no worker event for {idle:.0f}s while the "
                "scheduler still had work (tests/support/xdist_scheduler_fix.py watchdog).",
                returncode=pytest.ExitCode.INTERNAL_ERROR,
            )

    dsession.queue = _StallWatchingQueue(dsession.queue, on_event, on_idle)
    return True


def pytest_configure(config: pytest.Config) -> None:
    """Install when loaded as a plugin (``-p tests.support.xdist_scheduler_fix``)."""
    install()


def pytest_sessionstart(session: pytest.Session) -> None:
    """Arm the stall watchdog when loaded as a plugin."""
    arm_stall_watchdog(session.config)
