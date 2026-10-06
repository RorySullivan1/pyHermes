"""
Single-sheet print pieces, in an inbox (#386): ``letter_product_brief``'s sections as an email.

Every setting the epic added, set, so the golden pins how each degrades: a bled
band is the full-width band an email already draws, a pinned logo flows where
it sits, the "+" signs and the connector are cells of one row that stacks on a
phone, the arrow then pointing down.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email, EmailBuilder

from . import _brief, _product_brief


def build(template_dir: Path | None = None) -> Email:
    """Build the product brief as an email. Deterministic: same bytes every call."""
    builder = EmailBuilder(template_dir=template_dir).metadata(
        {
            "email_subject": "Meridian Broad Market Fund",
            "firm_name": "Hermes Research",
            "campaign_name": "Product brief",
            "font_theme": _brief.FONTS,
            "theme": _product_brief.THEME,
        }
    )
    for section in _product_brief.sections():
        builder.section(section)
    return builder.build()
