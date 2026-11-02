"""Text normalization used for fact/rule matching.

Facts are matched with *normalized exact string matching*: leading/trailing
whitespace is trimmed, repeated internal whitespace is collapsed and the text is
case-folded.  Two facts that only differ in casing or spacing are therefore
considered the same fact.
"""

from __future__ import annotations


def normalize(text: str) -> str:
    """Return the canonical form of ``text`` used for matching.

    ``None`` is treated as an empty string so callers never have to guard.
    """
    if text is None:
        return ""
    return " ".join(str(text).strip().split()).casefold()


def display(text: str) -> str:
    """Return a tidy human readable form (trim + collapse spaces, keep case)."""
    if text is None:
        return ""
    return " ".join(str(text).strip().split())


def same(a: str, b: str) -> bool:
    """True when two strings refer to the same normalized fact."""
    return normalize(a) == normalize(b)
