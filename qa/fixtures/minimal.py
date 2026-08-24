"""
The smallest email the builder will accept.

Metadata's three required fields and one section. Its value is negative space:
it renders the skeleton with every optional region empty, so a golden on it
catches a change to ``base.html``'s defaults that the richer fixtures would
mask by supplying the value themselves.
"""

from __future__ import annotations

from svc.builder import Email, EmailBuilder, FullWidth, TextBlock


def build() -> Email:
    """Build the minimal email. Deterministic: same bytes every call."""
    return (
        EmailBuilder()
        .metadata(
            {
                "email_subject": "Minimal",
                "firm_name": "Hermes Research",
                "campaign_name": "minimal",
            }
        )
        .section(FullWidth(content=TextBlock("<p>The smallest valid email.</p>")))
        .build()
    )
