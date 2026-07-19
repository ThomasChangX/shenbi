"""Tests for thread-safe PipelineState mutations (spec §3.3)."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from shenbi.pipeline.state import PipelineState


def _fresh_state() -> PipelineState:
    return PipelineState.default(project_dir="/tmp/test")


class TestInstanceLock:
    def test_lock_is_instance_attribute(self):
        """The lock must be per-instance, not shared across instances."""
        a = _fresh_state()
        b = _fresh_state()
        assert a._lock is not b._lock, (
            "PipelineState._lock must be an instance attribute (spec §3.3), "
            "not a class attribute shared across all instances"
        )

    def test_lock_is_not_class_attribute(self):
        """Lock lives on the instance, not on the class."""
        s = _fresh_state()
        assert "_lock" not in type(s).__dict__, "_lock must not be defined on the class"

    def test_lock_is_a_threading_lock(self):
        import threading

        s = _fresh_state()
        assert isinstance(s._lock, type(threading.Lock()))


class TestConcurrentAddStepDone:
    def test_eight_concurrent_appends_all_recorded(self):
        """8 threads each append a distinct step — no entries lost."""
        s = _fresh_state()
        barrier = threading.Barrier(8)
        steps = [f"skill-{i}" for i in range(8)]

        def runner(step: str) -> None:
            barrier.wait()
            s.add_step_done(chapter=1, step=step)

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(runner, st) for st in steps]
            for f in futs:
                f.result()

        cs = s.chapter_loop.chapter_states["1"]
        assert sorted(cs.steps_done) == sorted(steps), f"lost entries: got {sorted(cs.steps_done)}"

    def test_add_step_done_is_idempotent(self):
        s = _fresh_state()
        s.add_step_done(chapter=1, step="x")
        s.add_step_done(chapter=1, step="x")
        assert s.chapter_loop.chapter_states["1"].steps_done == ["x"]


class TestConcurrentRetryCounter:
    def test_eight_concurrent_increments(self):
        """8 threads each increment retry — durable count reaches 8."""
        s = _fresh_state()
        barrier = threading.Barrier(8)

        def runner() -> None:
            barrier.wait()
            s.increment_retry(chapter=1, skill="shenbi-chapter-drafting")

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(runner) for _ in range(8)]
            for f in futs:
                f.result()

        assert s.chapter_loop.retry_counts.get("ch1-shenbi-chapter-drafting") == 8

    def test_reset_retry_clears_count(self):
        s = _fresh_state()
        s.increment_retry(chapter=1, skill="s")
        s.reset_retry(chapter=1, skill="s")
        assert "ch1-s" not in s.chapter_loop.retry_counts
