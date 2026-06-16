#!/usr/bin/env python3
"""compute_pattern.py — Deterministic pattern analytics for shenbi-chapter-pattern.

Takes a JSON list of chapter pattern classifications (from LLM judgment) and
computes entropy, distribution coverage, consecutive runs, and monotony.
All computation is deterministic.

Usage:
  echo '[{"num":1,"pattern":"引入"},...]' | python3 compute_pattern.py
  python3 compute_pattern.py patterns.json
"""

import json
import math
import sys
from typing import Any
from collections import Counter, defaultdict
from pathlib import Path


PATTERNS = [
    "引入",
    "升级",
    "转折",
    "揭示",
    "决战",
    "沉淀",
    "日常",
    "训练",
    "探索",
    "阴谋",
    "逃亡",
    "回忆",
    "总结",
]

MAX_CONSECUTIVE = {
    "决战": 2,
    "转折": 2,
    "升级": 4,
    "日常": 3,
    "训练": 3,
}
DEFAULT_MAX_CONSECUTIVE = 3

DISTRIBUTION_MIN = {5: 3, 10: 5, 20: 8, 30: 10}

ENTROPY_THRESHOLDS = [
    (2.5, "优秀", "模式分布高度多样"),
    (2.0, "健康", "分布合理"),
    (1.5, "轻度单调", "开始出现模式集中"),
    (1.0, "中度单调", "模式明显集中"),
    (0.0, "严重单调", "几乎单一模式"),
]


def compute_consecutive(patterns):
    """Compute longest consecutive runs per pattern and overall."""
    runs = defaultdict(list)
    current_pattern = None
    current_len = 0
    for p in patterns:
        if p == current_pattern:
            current_len += 1
        else:
            if current_pattern:
                runs[current_pattern].append(current_len)
            current_pattern = p
            current_len = 1
    if current_pattern:
        runs[current_pattern].append(current_len)
    result = {}
    for pattern in PATTERNS:
        pattern_runs = runs.get(pattern, [])
        result[pattern] = max(pattern_runs) if pattern_runs else 0
    return result


def compute_entropy(patterns):
    """Compute Shannon entropy H = -Σ(p_i × log₂(p_i))."""
    n = len(patterns)
    if n == 0:
        return 0.0, []
    counter = Counter(patterns)
    terms = []
    entropy = 0.0
    for pattern in PATTERNS:
        count = counter.get(pattern, 0)
        if count > 0:
            p = count / n
            term = -p * math.log2(p)
            terms.append(
                {
                    "pattern": pattern,
                    "count": count,
                    "frequency": round(p, 4),
                    "p_log2p": round(term, 4),
                }
            )
            entropy += term
        else:
            terms.append({"pattern": pattern, "count": 0, "frequency": 0, "p_log2p": 0})
    terms.sort(key=lambda x: -x["count"])
    return round(entropy, 4), terms


def classify_entropy(h):
    for threshold, label, desc in ENTROPY_THRESHOLDS:
        if h > threshold:
            return label, desc
    return "严重单调", "几乎单一模式"


def check_distribution(patterns, recent_n):
    """Check if recent-N distribution meets minimum pattern coverage."""
    if len(patterns) < recent_n:
        return None
    recent = patterns[-recent_n:]
    unique = len(set(recent))
    required: int = DISTRIBUTION_MIN.get(recent_n) or (recent_n // 2)
    return {
        "window": recent_n,
        "unique_patterns": unique,
        "required": required,
        "pass": unique >= required,
    }


def check_consecutive_warnings(consecutive):
    """Check consecutive runs against thresholds."""
    warnings = []
    for pattern, max_run in consecutive.items():
        threshold = MAX_CONSECUTIVE.get(pattern, DEFAULT_MAX_CONSECUTIVE)
        if max_run > threshold:
            warnings.append(
                {"pattern": pattern, "max_run": max_run, "threshold": threshold, "level": "high"}
            )
        elif max_run == threshold:
            warnings.append(
                {"pattern": pattern, "max_run": max_run, "threshold": threshold, "level": "med"}
            )
    return warnings


def compute_transition_matrix(patterns):
    """Build pattern transition matrix."""
    matrix = defaultdict(lambda: defaultdict(int))
    for i in range(len(patterns) - 1):
        matrix[patterns[i]][patterns[i + 1]] += 1
    rows: list[dict[str, Any]] = []
    for p1 in PATTERNS:
        row: dict[str, Any] = {"from": p1, "to": {}}
        for p2 in PATTERNS:
            count = matrix.get(p1, {}).get(p2, 0)
            row["to"][p2] = count
        rows.append(row)
    return rows


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if isinstance(data, list):
        chapters = data
    else:
        chapters = data.get("chapters", data.get("data", []))
    patterns = [c.get("pattern", c.get("主模式", "未分类")) for c in chapters]
    n = len(patterns)
    # Compute all analytics
    consecutive = compute_consecutive(patterns)
    entropy_vals = {}
    entropy_terms = {}
    for w in [5, 10, 20, 30]:
        if n >= w:
            h, terms = compute_entropy(patterns[-w:])
            label, desc = classify_entropy(h)
            entropy_vals[f"window_{w}"] = {
                "chapters": f"{chapters[-w].get('num', '?')}-{chapters[-1].get('num', '?')}"
                if chapters
                else "?",
                "entropy": h,
                "rating": label,
                "description": desc,
            }
            entropy_terms[f"window_{w}"] = terms
    distribution = {}
    for w in [5, 10, 20, 30]:
        if n >= w:
            distribution[f"window_{w}"] = check_distribution(patterns, w)
    consecutive_warnings = check_consecutive_warnings(consecutive)
    pattern_counts = Counter(patterns)
    result = {
        "sample": {"chapters": n},
        "pattern_distribution": [
            {
                "pattern": p,
                "count": pattern_counts.get(p, 0),
                "ratio": round(pattern_counts.get(p, 0) / n, 3) if n > 0 else 0,
            }
            for p in PATTERNS
        ],
        "max_consecutive": [{"pattern": p, "max_run": consecutive.get(p, 0)} for p in PATTERNS],
        "consecutive_warnings": consecutive_warnings,
        "entropy": entropy_vals,
        "entropy_terms": entropy_terms,
        "distribution_coverage": distribution,
        "transition_matrix": compute_transition_matrix(patterns),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
