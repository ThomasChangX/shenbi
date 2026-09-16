#!/usr/bin/env python3
"""Extract a JSON field from mixed log+JSON output (spec #64 C26, T1203).

Reads the whole stdin text, scans it with json.JSONDecoder.raw_decode for
every JSON object, and prints the value of the requested field from the
last object that carries it (or ``unknown``). Only string-valued fields are
queried today; non-scalar
values print their Python repr. Replaces the old
``grep -o '"status": "..."'`` extraction, which agent stderr log previews
could pollute (T1203) and which silently misjudged on format drift.
"""

import json
import sys


def main(argv: list[str]) -> int:
    """Extract argv[1] field from JSON objects on stdin; print last match."""
    field = argv[1]
    text = sys.stdin.read()
    decoder = json.JSONDecoder()
    best: object | None = None
    i = 0
    while i < len(text):
        j = text.find("{", i)
        if j < 0:
            break
        try:
            obj, end = decoder.raw_decode(text[j:])
        except json.JSONDecodeError:
            i = j + 1
            continue
        if isinstance(obj, dict) and field in obj:
            best = obj[field]
        i = j + end
    print(best if best is not None else "unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
