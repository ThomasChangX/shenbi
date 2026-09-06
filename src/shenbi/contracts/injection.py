"""Untrusted-source boundary markers — T306/T307 (spec #45 R5).

Single source for the injection-boundary format used by BOTH dispatch
faces (pipeline prompt injection and T1 codex manifest). Attribute values
and content are entity-escaped (F308/R2), so untrusted skill/chapter text
cannot close the wrapper or smuggle a ```verdict fence.
"""

from __future__ import annotations

import re


def escape_attr(value: str) -> str:
    """Escape a value for use inside a double-quoted XML-ish attribute.

    '&' first so entity output is not double-escaped.
    """
    return (
        value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


def escape_content(content: str) -> str:
    """Entity-escape untrusted document content (spec #45 R2/F308)."""
    return content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap_untrusted_source(path: str, content: str | None = None) -> str:
    """Wrap an untrusted input source in the boundary marker.

    With *content*: full block form (pipeline face). Without: self-closing
    manifest form (T1 face — codex reads the workspace itself, so only the
    path is annotated; zero token amplification).
    """
    attr = escape_attr(path)
    if content is None:
        return f'<untrusted-source path="{attr}"/>'
    return f'<untrusted-source path="{attr}">\n{escape_content(content)}\n</untrusted-source>'


def is_untrusted_boundary(text: str) -> bool:
    """True when *text* carries the untrusted-source boundary marker."""
    return bool(re.search(r"^<untrusted-source\s+path=", text, re.MULTILINE))
