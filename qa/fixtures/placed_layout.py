"""
Placement across media, in an inbox (#361): ``a4_placed_layout``'s sections as an email.

A reversed split, a figure pair and a label beside its value that stay side by
side on a phone, and a button shown here alone. The print-only page note and
both sheet breaks emit nothing, so its golden pins that an email pays no byte
for paper's controls.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email, EmailBuilder

from . import _placed


def build(template_dir: Path | None = None) -> Email:
    """Build the placement email. Deterministic: same bytes every call."""
    builder = EmailBuilder(template_dir=template_dir).metadata(
        {
            "email_subject": "Rates, Placed",
            "firm_name": "Hermes Research",
            "campaign_name": "Rates, Placed",
        }
    )
    for section in _placed.sections():
        builder.section(section)
    return builder.build()
