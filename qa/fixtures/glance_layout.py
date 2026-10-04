"""
Data at a glance, in an inbox (#323): ``a4_glance_layout``'s sections as an email.

Arrows, ranked and diverging bars, sparklines and hero figures, each drawn from
table cells and theme tokens, so the golden pins an email that reads with
images blocked.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email, EmailBuilder

from . import _glance


def build(template_dir: Path | None = None) -> Email:
    """Build the glance email. Deterministic: same bytes every call."""
    builder = EmailBuilder(template_dir=template_dir).metadata(
        {
            "email_subject": "Rates, at a Glance",
            "firm_name": "Hermes Research",
            "campaign_name": "Rates, at a Glance",
        }
    )
    for section in _glance.sections():
        builder.section(section)
    return builder.build()
