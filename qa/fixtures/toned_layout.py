"""
Brand tones, in an inbox (#387): ``a4_toned_layout``'s sections as an email.

A theme declaring a gold and a sky beside the semantic three, named by a box,
a card, a badge, a hero figure, a cell, a status dot, a bar and a key, so the
golden pins each brand tone reaching the Word engine as a plain hex.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email, EmailBuilder

from . import _toned


def build(template_dir: Path | None = None) -> Email:
    """Build the toned email. Deterministic: same bytes every call."""
    builder = EmailBuilder(template_dir=template_dir).metadata(
        {
            "email_subject": "The Fund, In Brand",
            "firm_name": "Hermes Research",
            "campaign_name": "The Fund, In Brand",
            "theme": _toned.THEME,
        }
    )
    for section in _toned.sections():
        builder.section(section)
    return builder.build()
