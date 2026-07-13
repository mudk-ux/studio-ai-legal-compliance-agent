"""Deterministic text preprocessing for screenplay assets."""

from __future__ import annotations

import re

_PG_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^*]*\*\*\*", re.IGNORECASE)
_PG_END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^*]*\*\*\*", re.IGNORECASE)


def strip_gutenberg_boilerplate(text: str) -> str:
    """Remove Project Gutenberg license header/footer, keeping only the work.

    PG-sourced scripts carry license blocks naming real organizations
    ('Project Gutenberg Literary Archive Foundation') that are not part of
    the screenplay and were flagged as uncleared references in live runs.
    Text without PG markers is returned unchanged.
    """
    start = _PG_START.search(text)
    if start:
        text = text[start.end():]
    end = _PG_END.search(text)
    if end:
        text = text[: end.start()]
    return text
