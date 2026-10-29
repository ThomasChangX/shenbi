"""observe_report (spec #81 §3 P1): one-shot observability report.

Four tables (膨胀曲线 / Loop depth / 失败簇 / 逃逸舱) + the archive
coverage row (the P1 minimal consumer of the dispatch archive — L-A)
+ the WARN tally line. Read-only over the project directory:

- cost/token-ledger.jsonl        (膨胀曲线; coverage denominator: attempt==1
                                  rows, real/est breakdown — est rows are
                                  IDE/legacy faces + usage-less failures)
- trace.jsonl                    (DISPATCH loop_id/reads; RETRY reasons)
- observability/dispatches/*.json(coverage numerator; blob pointers)
- observability/blobs/           (dedup ratio ground truth)
- observability/escape-hatch-state.json (current streaks)
- observability/archive-stats.json      (three WARN counters)

Usage: uv run python tools/observe_report.py <project_dir>
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue  # torn tail — report on what parses
    return rows


def _table_bloat(ledger: list[dict[str, Any]]) -> list[str]:
    """Table 1: per-skill average prompt tokens by chapter."""
    lines = ["## 膨胀曲线", "| skill | chapter | avg prompt tokens | rows |", "|---|---|---|---|"]
    by_skill_ch: dict[tuple[str, Any], list[int]] = defaultdict(list)
    for row in ledger:
        by_skill_ch[(str(row.get("skill")), row.get("chapter"))].append(
            int(row.get("prompt_tokens", 0))
        )
    for (skill, ch), toks in sorted(by_skill_ch.items(), key=lambda kv: (kv[0][0], kv[0][1] or -1)):
        avg = sum(toks) // max(len(toks), 1)
        lines.append(f"| {skill} | ch{ch} | {avg} | {len(toks)} |")
    lines.append("")
    return lines


def _table_loop_depth(
    dispatch_events: list[dict[str, Any]], retry_events: list[dict[str, Any]]
) -> list[str]:
    """Table 2: max loop_id per (skill, chapter) plus RETRY counts."""
    lines = ["## Loop depth", "| skill | chapter | max loop_id | retries |", "|---|---|---|---|"]
    loop_max: dict[tuple[str, Any], int] = {}
    for e in dispatch_events:
        payload = e.get("payload", {})
        lid = payload.get("loop_id")
        if lid is not None:
            key = (str(e.get("skill")), payload.get("chapter"))
            loop_max[key] = max(loop_max.get(key, 0), int(lid))
    retry_count: Counter[tuple[str, Any]] = Counter()
    for e in retry_events:
        payload = e.get("payload", {})
        retry_count[(str(payload.get("skill")), payload.get("chapter"))] += 1
    for key in sorted(set(loop_max) | set(retry_count), key=lambda k: (k[0], k[1] or -1)):
        skill, ch = key
        lines.append(f"| {skill} | ch{ch} | {loop_max.get(key, 0)} | {retry_count.get(key, 0)} |")
    lines.append("")
    return lines


def _reason_sample(reason: dict[str, Any]) -> str:
    if reason.get("kind") == "monitor_rewind":
        issues = reason.get("issues", [])
        return str(issues[0])[:60] if issues else ""
    ids = reason.get("check_ids", [])
    return str(ids[0])[:60] if ids else ""


def _table_failure_clusters(retry_events: list[dict[str, Any]]) -> list[str]:
    """Table 3: RETRY reasons clustered by kind."""
    lines = ["## 失败簇", "| kind | chapters | count | sample |", "|---|---|---|---|"]
    cluster: dict[str, list[str]] = defaultdict(list)
    for e in retry_events:
        payload = e.get("payload", {})
        reason = payload.get("reason", {}) if isinstance(payload.get("reason"), dict) else {}
        cluster[str(reason.get("kind", "unknown"))].append(f"ch{payload.get('chapter')}")
    for kind, chs in sorted(cluster.items()):
        sample = ""
        for e in retry_events:
            reason = e.get("payload", {}).get("reason", {})
            if isinstance(reason, dict) and reason.get("kind") == kind:
                sample = _reason_sample(reason)
                break
        lines.append(f"| {kind} | {', '.join(chs)} | {len(chs)} | {sample} |")
    lines.append("")
    return lines


def _table_escape_hatch(
    dispatch_events: list[dict[str, Any]], escape_state: dict[str, Any]
) -> list[str]:
    """Table 4: historical fields-mode misses per path + current streaks."""
    lines = ["## 逃逸舱", "| path | trace misses (historical) | current streak |", "|---|---|---|"]
    miss_hist: Counter[str] = Counter()
    for e in dispatch_events:
        for r in e.get("payload", {}).get("reads", []) or []:
            if r.get("mode") == "fields" and not r.get("matched_all", True):
                miss_hist[str(r.get("path"))] += 1
    streaks = escape_state.get("streaks", {}) if isinstance(escape_state, dict) else {}
    cur: dict[str, int] = {}
    for key, entry in streaks.items():
        if isinstance(entry, dict):
            path_only = str(key).split("|", 1)[0]
            streak = int(entry.get("streak", 0))
            cur[path_only] = max(cur.get(path_only, 0), streak)  # (path,fields) 键展平取 max
    for path_ in sorted(set(miss_hist) | set(cur)):
        lines.append(f"| {path_} | {miss_hist.get(path_, 0)} | {cur.get(path_, 0)} |")
    lines.append("")
    return lines


def _blob_pointers(rec: dict[str, Any]) -> list[str]:
    pointers: list[str] = []
    for key in ("system_prompt_blob", "user_prompt_blob", "response_blob", "feedback_ref"):
        v = rec.get(key)
        if isinstance(v, str) and v.startswith("sha256:"):
            pointers.append(v.split(":", 1)[1])
    for r in rec.get("reads", []) or []:
        v = r.get("blob")
        if isinstance(v, str) and v.startswith("sha256:"):
            pointers.append(v.split(":", 1)[1])
    return pointers


def _referenced_bytes(archives: list[dict[str, Any]], blob_dir: Path) -> int:
    """Sum bytes PER REFERENCE.

    A shared blob counts once per archive entry referencing it — the dedup
    ratio is referenced-vs-stored physical bytes.
    """
    total = 0
    for rec in archives:
        for pointer in _blob_pointers(rec):
            f = blob_dir / pointer
            if f.exists():
                total += f.stat().st_size
    return total


def _coverage_row(
    archives: list[dict[str, Any]],
    dispatches_dir_exists: bool,
    ledger: list[dict[str, Any]],
    project: Path,
) -> list[str]:
    """Archive coverage: the P1 minimal consumer of the dispatch archive (L-A)."""
    lines = ["## 归档覆盖"]
    if not archives and not dispatches_dir_exists:
        lines.append("无归档 (特性前项目或归档关闭)。")
        lines.append("")
        return lines
    attempt1 = [row for row in ledger if int(row.get("attempt", 1)) == 1]
    n_est = sum(1 for row in attempt1 if row.get("estimated"))
    n_real = len(attempt1) - n_est
    # est attempt==1 rows = IDE/legacy faces (never archived) + usage-less
    # failures (archived) — shown explicitly instead of silently filtered,
    # so a failure-heavy project reads as a breakdown, not a false mismatch.
    lines.append(
        f"- 派发对账: ledger={len(attempt1)} (real={n_real}, est={n_est}) / archive={len(archives)}"
    )
    blob_dir = project / "observability" / "blobs"
    blob_hits = blob_total = 0
    for rec in archives:
        for pointer in _blob_pointers(rec):
            blob_total += 1
            if (blob_dir / pointer).exists():
                blob_hits += 1
    lines.append(
        f"- blob 存在性: {blob_hits}/{blob_total}"
        + (" (哈希在、内容失=配额跳过降级)" if blob_hits < blob_total else "")
    )
    if blob_dir.exists():
        stored = sum(p.stat().st_size for p in blob_dir.iterdir() if p.is_file())
        referenced = _referenced_bytes(archives, blob_dir)
        ratio = f"{stored / referenced:.2f}x" if referenced else "n/a"
        lines.append(f"- 去重率(实存/引用): {ratio} (stored={stored}B)")
    lines.append("")
    return lines


def _load_stats(project: Path) -> dict[str, Any]:
    try:
        loaded: dict[str, Any] = json.loads(
            (project / "observability" / "archive-stats.json").read_text(encoding="utf-8")
        )
        return loaded
    except (OSError, ValueError):
        return {}


def _load_escape_state(project: Path) -> dict[str, Any]:
    try:
        loaded: dict[str, Any] = json.loads(
            (project / "observability" / "escape-hatch-state.json").read_text(encoding="utf-8")
        )
        return loaded
    except (OSError, ValueError):
        return {}


def build_report(project_dir: Path | str) -> str:
    """Render the full observability report as markdown."""
    project = Path(project_dir)
    ledger = _load_jsonl(project / "cost" / "token-ledger.jsonl")
    trace = _load_jsonl(project / "trace.jsonl")
    dispatches_dir = project / "observability" / "dispatches"
    archives: list[dict[str, Any]] = []
    if dispatches_dir.exists():
        for p in sorted(dispatches_dir.glob("*.json")):
            try:
                loaded_rec: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
                archives.append(loaded_rec)
            except (OSError, ValueError):
                continue  # externally corrupted record — report on the rest
    stats = _load_stats(project)
    escape_state = _load_escape_state(project)
    dispatch_events = [e for e in trace if e.get("action") == "DISPATCH"]
    retry_events = [e for e in trace if e.get("action") == "RETRY"]

    lines: list[str] = [f"# Observability Report — {project.name}", ""]
    lines.extend(_table_bloat(ledger))
    lines.extend(_table_loop_depth(dispatch_events, retry_events))
    lines.extend(_table_failure_clusters(retry_events))
    lines.extend(_table_escape_hatch(dispatch_events, escape_state))
    lines.extend(_coverage_row(archives, dispatches_dir.exists(), ledger, project))
    lines.append(
        f"- WARN 汇总: archive_write_failed={stats.get('archive_write_failed', 0)}"
        f" / archive_quota_skip={stats.get('archive_quota_skip', 0)}"
        f" / archive_seq_collision={stats.get('archive_seq_collision', 0)}"
    )
    return "\n".join(lines)


_EXPECTED_ARGC = 2


def main(argv: list[str]) -> int:
    """CLI entry: observe_report.py <project_dir>."""
    if len(argv) != _EXPECTED_ARGC:
        print("usage: observe_report.py <project_dir>", file=sys.stderr)
        return 2
    print(build_report(argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
