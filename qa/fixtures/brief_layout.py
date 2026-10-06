"""
Print typography, in an inbox (#385): ``letter_brief``'s sections as an email.

Every setting the epic added, set, so the golden pins how each degrades: the
house face's files are ignored and its stack walked, the display title drops
to ``title_mobile`` on a phone, fine print and justify render as unset, and
both qualifiers print.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email, EmailBuilder

from . import _brief


def build(template_dir: Path | None = None) -> Email:
    """Build the brief as an email. Deterministic: same bytes every call."""
    builder = EmailBuilder(template_dir=template_dir).metadata(
        {
            "email_subject": "Meridian Broad Market Fund",
            "firm_name": "Hermes Research",
            "campaign_name": "Product brief",
            "font_theme": _brief.FONTS,
        }
    )
    for section in _brief.sections():
        builder.section(section)
    return builder.build()
