"""
``kitchen_sink`` at the ``compact`` density — the size axis's A/B.

Identical in every other respect, so the golden diff against ``kitchen_sink``
is the density and nothing else. A px literal that failed to tokenise shows
here as a value that did not move.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email
from pyhermes.builder.enums import SizeTheme

from . import kitchen_sink


def build(template_dir: Path | None = None) -> Email:
    """Build the compact email. Deterministic: same bytes every call."""
    return kitchen_sink.build(template_dir=template_dir, size_theme=SizeTheme.COMPACT)
