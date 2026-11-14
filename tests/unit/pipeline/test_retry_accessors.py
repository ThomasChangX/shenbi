"""Spec #91 T4: retry-state accessors (locked writes + serial budget)."""

import threading

from shenbi.pipeline.state import PipelineState


def _fresh_state() -> PipelineState:
    return PipelineState.default(project_dir="/tmp/test")


def test_increment_retry_concurrent_equals_serial_sum():
    s = _fresh_state()

    def worker():
        for _ in range(200):
            s.increment_retry(1, "x")

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert s.chapter_loop.retry_counts["ch1-x"] == 400  # == serial sum


def test_charge_budget_concurrent_is_max_not_sum():  # characterization
    s = _fresh_state()

    def worker(n):
        for _ in range(100):
            s.charge_retry_budget(1, "x", n)

    ts = [threading.Thread(target=worker, args=(n,)) for n in (3, 7)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert s.chapter_loop.retry_budget_consumed["ch1-x"] == 7  # max, NOT 10


def test_increment_budget_monotonic():  # serial +=1, never loses
    s = _fresh_state()
    assert s.increment_retry_budget(1, "x") == 1
    assert s.increment_retry_budget(1, "x") == 2


def test_feedback_last_writer_wins():  # characterization (STORE_SUBSCR atomic)
    s = _fresh_state()
    s.set_retry_feedback("ch1-x", "a")
    s.set_retry_feedback("ch1-x", "b")
    assert s.get_retry_feedback("ch1-x") == "b"
    assert s.pop_retry_feedback("ch1-x") == "b"
    assert s.get_retry_feedback("ch1-x") is None


def test_clear_prefix_sweep():
    s = _fresh_state()
    s.set_retry_feedback("ch1-a", "x")
    s.set_retry_feedback("ch1-b", "y")
    s.clear_retry_feedback_prefix("ch1-")
    assert s.get_retry_feedback("ch1-a") is None
    assert s.get_retry_feedback("ch1-b") is None
