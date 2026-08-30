"""Concurrency guard for the staging append_dedup route (SDD #21 R3).

Two parallel staging writers (state-settling vs foreshadowing-lifecycle run
in a ThreadPoolExecutor, chapter_loop.py) used to each merge their increment
against the LIVE file and whole-file overwrite ``staging/truth/<file>`` —
the second writer erased the first writer's rows (last-writer-wins, T7-03).
The fix: chained merge base (existing staging file wins over live) + per-path
lock around read-merge-write. These tests pin both properties.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from shenbi.pipeline.dispatch_helper import _route_append_dedup_write


def _row(key: str, note: str) -> str:
    return f"| {key} | {note} |"


def test_chained_base_keeps_first_writer_increment(tmp_path: Path) -> None:
    """Sequential two-writer scenario: writer B's staged snapshot must still
    contain writer A's row (A merged first; B chains onto the staged file).
    """
    live = tmp_path / "truth" / "hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text(
        "| hook | note |\n|------|------|\n" + _row("ch1", "live row"), encoding="utf-8"
    )

    _route_append_dedup_write(
        tmp_path, "staging/truth/hooks.md", _row("writer-a", "from A"), key_field="hook"
    )
    _route_append_dedup_write(
        tmp_path, "staging/truth/hooks.md", _row("writer-b", "from B"), key_field="hook"
    )

    staged = (tmp_path / "staging" / "truth" / "hooks.md").read_text(encoding="utf-8")
    assert "writer-a" in staged, "first writer's increment lost from staging (T7-03)"
    assert "writer-b" in staged
    assert "ch1" in staged  # live baseline carried through


def test_concurrent_writers_both_survive(tmp_path: Path) -> None:
    """True concurrency: two threads write different-key increments at the
    same time — both must be present in the staged file afterwards.
    """
    live = tmp_path / "truth" / "hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text(
        "| hook | note |\n|------|------|\n" + _row("ch1", "live row"), encoding="utf-8"
    )

    def _write(tag: str) -> None:
        _route_append_dedup_write(
            tmp_path, "staging/truth/hooks.md", _row(tag, f"from {tag}"), key_field="hook"
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        for fut in [pool.submit(_write, f"w{i}") for i in range(20)]:
            fut.result()

    staged = (tmp_path / "staging" / "truth" / "hooks.md").read_text(encoding="utf-8")
    for i in range(20):
        assert f"w{i}" in staged, f"writer w{i}'s increment lost under concurrency"


def test_sidecar_records_keyed_target_and_merges(tmp_path: Path) -> None:
    """The .staging-meta.json sidecar records the target's key_field (read ->
    dict.update -> write, second entry does not erase the first).
    """
    import json

    _route_append_dedup_write(tmp_path, "staging/truth/hooks.md", _row("a", "x"), key_field="hook")
    _route_append_dedup_write(
        tmp_path, "staging/truth/other.md", _row("b", "y"), key_field="chapter"
    )

    meta = json.loads((tmp_path / "staging" / ".staging-meta.json").read_text(encoding="utf-8"))
    assert meta["truth/hooks.md"] == {"update_mode": "append_dedup", "key_field": "hook"}
    assert meta["truth/other.md"]["key_field"] == "chapter"


def test_commit_does_not_clobber_live_rows_written_after_staging(tmp_path: Path) -> None:
    """SDD #21 R3 commit half: a row written to LIVE after staging (e.g. the
    resonance step) survives the commit; staged-only rows are added.
    """
    from shenbi.pipeline.checkpoint import commit_staging

    live = tmp_path / "truth" / "hooks.md"
    live.parent.mkdir(parents=True)
    live.write_text("| hook | note |\n|------|------|\n" + _row("k0", "baseline"), encoding="utf-8")

    _route_append_dedup_write(
        tmp_path, "staging/truth/hooks.md", _row("k1", "staged"), key_field="hook"
    )
    # live gains a NEW row after staging (second key, plus a richer k1)
    live.write_text(
        "| hook | note |\n|------|------|\n"
        + _row("k0", "baseline")
        + "\n"
        + _row("k1", "LIVE RICHER ROW")
        + "\n"
        + _row("k2", "live-only row"),
        encoding="utf-8",
    )

    commit_staging(tmp_path, ["truth/hooks.md"])

    text = live.read_text(encoding="utf-8")
    assert "LIVE RICHER ROW" in text, "commit clobbered a live row with the older staged copy"
    assert "live-only row" in text
    assert text.count("| k1 |") == 1  # one row per key after merge
