"""Smoke test file to verify mypy --strict is active.

If mypy is correctly configured, this file's intentional type error
will be caught when uncommented. The file should NOT be imported or
executed by pytest (it's purely a mypy canary).
"""


def add(a: int, b: int) -> int:
    """Return sum of two integers."""
    return a + b


# Intentional type error (uncomment to verify mypy catches it):
# result: str = add(1, 2)
