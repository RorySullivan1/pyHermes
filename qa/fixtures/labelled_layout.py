"""
Labels and status, in an inbox (#328): ``a4_labelled_layout``'s sections as an email.

Badged cards, cells and section titles, a status column of dots and a row of
tags, so the golden pins what the Word engine is sent: a square label with
non-breaking spaces for padding, and a VML oval for each dot.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email, EmailBuilder

from . import _labelled


def build(template_dir: Path | None = None) -> Email:
    """Build the labelled email. Deterministic: same bytes every call."""
    builder = EmailBuilder(template_dir=template_dir).metadata(
        {
            "email_subject": "Rates, Labelled",
            "firm_name": "Hermes Research",
            "campaign_name": "Rates, Labelled",
        }
    )
    for section in _labelled.sections():
        builder.section(section)
    return builder.build()
