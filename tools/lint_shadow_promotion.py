"""spec #82 T5/验收1: shadow-promotion lint (转正催转).

A shadow gate that has emitted WARN events (trace action="WARN", gate=shadow)
for 2+ consecutive bundles with zero misfire rulings, and whose config entry
still says shadow:true, is a forgotten gate — WARN forever equals never
built. Exit 1 with findings when any registered shadow key is overdue for
promotion. Misfire rulings live in the driver ledger (vol1-ledger style:
a `shadow 误伤` line naming the gate); any ruling resets that gate's
clean streak.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# gate id (prefixed, from WARN payload item) → config location, same map as
# gates/g4/shadow.py GATE_TO_SHADOW_KEY — kept in sync there (single source).
from shenbi.gates.g4.shadow import GATE_TO_SHADOW_KEY

MISFIRE_RE = re.compile(r"shadow\s*误伤[：:]\s*(\S+)")

#: 连续干净束数阈值——达到即应转正（spec #82 验收 1）
_PROMOTE_AFTER_CLEAN_BUNDLES = 2


def load_warn_events(project_dir: Path) -> list[dict[str, object]]:
    """Read WARN events (gate=shadow) from the #81 trace face."""
    trace = project_dir / "trace.jsonl"
    if not trace.is_file():
        return []
    out: list[dict[str, object]] = []
    for line in trace.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("action") == "WARN" and ev.get("gate") == "shadow":
            out.append(ev)
    return out


def misfired_gates(ledger_path: Path | None) -> set[str]:
    """Gate names with a misfire ruling in the driver ledger."""
    if ledger_path is None or not ledger_path.is_file():
        return set()
    return set(MISFIRE_RE.findall(ledger_path.read_text(encoding="utf-8")))


def check_promotion(project_dir: Path, ledger: Path | None) -> list[str]:
    """Return promotion-overdue findings for every registered shadow gate."""
    findings: list[str] = []
    events = load_warn_events(project_dir)
    if not events:
        return [
            "shadow-promotion: 无 shadow WARN 事件（trace 面零记录——新门未试运行或 trace 未接线）"
        ]
    misfires = misfired_gates(ledger)
    from shenbi.gates.shared import read_genre_config  # noqa: PLC0415

    cfg = read_genre_config(str(project_dir)) or {}
    # bundle streak per gate: consecutive chapters with a WARN, no misfire
    per_gate_chapters: dict[str, set[int]] = {}
    for ev in events:
        payload = ev.get("payload")
        if not isinstance(payload, dict):
            continue
        item = str(payload.get("item", ""))
        ch = payload.get("chapter")
        m = re.match(r"\[?shadow\]?\s*G4\.([a-z_.]+)", item) or re.match(r"G4\.([a-z_.]+)", item)
        if m and isinstance(ch, int):
            per_gate_chapters.setdefault(m.group(1), set()).add(ch)
    for gate_id, chapters in sorted(per_gate_chapters.items()):
        key = GATE_TO_SHADOW_KEY.get(gate_id)
        if key is None:
            continue
        block, cfg_key = key
        entry = (cfg.get(block) or {}).get(cfg_key, {})
        if not (isinstance(entry, dict) and entry.get("shadow", True) is True):
            continue  # already promoted (shadow:false)
        if any(gate_id.split(".")[-1] in mf or mf in gate_id for mf in misfires):
            continue  # misfire ruled — streak reset
        if len(chapters) >= _PROMOTE_AFTER_CLEAN_BUNDLES:
            findings.append(
                f"shadow-promotion: {gate_id} 已连续 {len(chapters)} 束 WARN 零误伤"
                f"（ch{sorted(chapters)}）——按纪律应转正（{block}.{cfg_key}.shadow: false）；"
                f"遗忘性 shadow 永久化 = 门停在 WARN = 没建"
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entry."""
    parser = argparse.ArgumentParser(description="shadow gate promotion lint (spec #82)")
    parser.add_argument("project_dir")
    parser.add_argument("--ledger", default=None, help="driver ledger path (misfire rulings)")
    args = parser.parse_args(argv)
    findings = check_promotion(Path(args.project_dir), Path(args.ledger) if args.ledger else None)
    for f in findings:
        print(f"FAIL [{f}]")
    if findings:
        print(f"shadow-promotion lint: findings={len(findings)}")
        return 1
    print("shadow-promotion lint: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
