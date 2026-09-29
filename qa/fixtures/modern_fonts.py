"""
``kitchen_sink`` at the ``modern`` font theme — the typeface axis's A/B.

Identical to ``kitchen_sink`` in every other respect, so the golden diff
between them is the font axis and nothing else. That is what makes a
tokenisation slip visible: a face that failed to move shows here as a pair of
goldens that disagree in fewer places than they should.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email

from . import kitchen_sink


def build(template_dir: Path | None = None) -> Email:
    """Build the modern-fonts email. Deterministic: same bytes every call."""
    return kitchen_sink.build(template_dir=template_dir, font_theme="modern")
