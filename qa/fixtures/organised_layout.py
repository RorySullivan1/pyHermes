"""
Organising content, in an inbox (#334): ``a4_organised_layout``'s sections as an email.

Fact lists, a timeline, teaser lists and kicked titles, so the golden pins
what the Word engine is sent: columns as cells that stack on a phone, the
rule as a cell border, and each thumbnail a ``cid:`` part in the manifest.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email, EmailBuilder

from . import _organised


def build(template_dir: Path | None = None) -> Email:
    """Build the organised email. Deterministic: same bytes every call."""
    builder = EmailBuilder(template_dir=template_dir).metadata(
        {
            "email_subject": "Gilt Fund, Organised",
            "firm_name": "Hermes Research",
            "campaign_name": "Gilt Fund, Organised",
        }
    )
    for section in _organised.sections():
        builder.section(section)
    return builder.build()
