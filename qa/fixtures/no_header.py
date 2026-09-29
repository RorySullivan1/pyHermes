"""
An email with no disclaimer strip — the ``EmptyHeader`` variant.

A region that renders *nothing* is the case a four-region model most easily
gets wrong: the slot must be filled with emptiness rather than left undefined,
or the skeleton raises under ``StrictUndefined``. This golden is the proof it
does not.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Email, EmailBuilder, EmptyHeader, FullWidth, TextBlock


def build(template_dir: Path | None = None) -> Email:
    """Build the no-header email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "No Header — the strip omitted entirely",
                "preheader_text": "The region fills no slot, so nothing renders.",
                "firm_name": "Hermes Research",
                "campaign_name": "no-header",
                "date_range": "Week ending 24 August",
                "issue_label": "Issue 005",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/005",
            }
        )
        .header(EmptyHeader())
        .section(
            FullWidth(
                title="Body Unchanged",
                content=TextBlock(
                    "<p>Omitting the strip is a region choice; nothing below it moves.</p>"
                ),
            )
        )
        .build()
    )
