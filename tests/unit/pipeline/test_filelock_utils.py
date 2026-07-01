"""Tests for pipeline file locking utilities."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from shenbi.pipeline.filelock_utils import ReadLock, WriteLock


class TestWriteLock:
    def test_acquire_and_release(self, tmp_project: Path):
        lock = WriteLock(tmp_project)
        with lock:
            assert (tmp_project / "pipeline-state.json.lockfile").exists()
        # Lock file may persist (filelock behavior) but is unlocked

    def test_concurrent_writes_are_serialized(self, tmp_project: Path):
        """Two writers should not overlap."""
        results: list[str] = []
        barrier = threading.Barrier(2)

        def writer(name: str):
            barrier.wait()
            with WriteLock(tmp_project):
                results.append(f"{name}-start")
                results.append(f"{name}-end")

        t1 = threading.Thread(target=writer, args=("a",))
        t2 = threading.Thread(target=writer, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Each writer's start and end should be adjacent (no interleaving)
        for i in range(0, len(results), 2):
            name = results[i].split("-")[0]
            assert results[i + 1] == f"{name}-end"

    def test_write_blocks_read(self, tmp_project: Path):
        """ReadLock should fail while WriteLock is held."""
        with (
            WriteLock(tmp_project),
            pytest.raises(TimeoutError),
            ReadLock(tmp_project, timeout=0.2),
        ):
            pass

    def test_timeout_raises_timeout_error(self, tmp_project: Path):
        """A second WriteLock should time out when the first is held."""
        with (
            WriteLock(tmp_project),
            pytest.raises(TimeoutError),
            WriteLock(tmp_project, timeout=0.2),
        ):
            pass


class TestReadLock:
    def test_concurrent_reads_allowed(self, tmp_project: Path):
        """Multiple readers should be able to hold the lock simultaneously."""
        results: list[str] = []
        barrier = threading.Barrier(2)

        def reader(name: str):
            barrier.wait()
            with ReadLock(tmp_project):
                results.append(f"{name}-in")

        t1 = threading.Thread(target=reader, args=("a",))
        t2 = threading.Thread(target=reader, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 2  # both readers entered

    def test_read_blocks_write(self, tmp_project: Path):
        """WriteLock should fail while ReadLock is held."""
        with (
            ReadLock(tmp_project),
            pytest.raises(TimeoutError),
            WriteLock(tmp_project, timeout=0.2),
        ):
            pass


class TestLockFileCreation:
    def test_creates_parent_dir(self, tmp_project: Path):
        """Lock should create the project directory if it doesn't exist."""
        nested = tmp_project / "deeply" / "nested"
        with WriteLock(nested):
            assert (nested / "pipeline-state.json.lockfile").exists()

    def test_same_lockfile_for_read_and_write(self, tmp_project: Path):
        """Both lock types must use the same lockfile for mutual exclusion."""
        w = WriteLock(tmp_project)
        r = ReadLock(tmp_project)
        assert w._lockfile == r._lockfile

    def test_release_allows_reacquire(self, tmp_project: Path):
        """After releasing, the lock should be immediately reacquirable."""
        with WriteLock(tmp_project):
            pass
        with WriteLock(tmp_project, timeout=1.0):
            pass  # should not timeout
