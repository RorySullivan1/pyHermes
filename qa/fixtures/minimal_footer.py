"""
The plain ``Footer`` variant, in the gallery.

The footer's counterpart to :mod:`qa.fixtures.minimal_header`. This email
uses a ``Footer`` with a disclaimer and custom label — demonstrating that
the footer region presents the email's legal copy as plain HTML, emitted
raw and unwrapped.

What the golden on this fixture pins that no other one can:

* the disclaimer is rendered inside a ``<div>`` (not a ``<p>``), so caller
  block elements render correctly;
* the copyright + links line always renders, regardless of the disclaimer;
* the email-level facts still flow down unchanged.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import (
    DataTable,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    TextBlock,
    TwoColumn,
)
from svc.builder.models import TableRow


def build(template_dir: Path | None = None) -> Email:
    """Build the footer-with-disclaimer email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Footer with Disclaimer — legal copy, structured close",
                "preheader_text": "The closing region with a disclaimer block.",
                "firm_name": "Hermes Research",
                "campaign_name": "minimal-footer",
                "date_range": "Week ending 31 August",
                "issue_label": "Issue 003",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/003",
            }
        )
        .footer(
            Footer(
                disclaimer=(
                    "<p>Distributed to registered recipients only. "
                    "Past performance is not indicative of future results.</p>"
                ),
                unsubscribe_label="Remove me from this list",
            )
        )
        .section(
            FullWidth(
                title="Same Email, Structured Close",
                content=TextBlock(
                    "<p>The footer region presents the email's legal copy as plain HTML, "
                    "emitted raw and unwrapped — a disclaimer passed as a block element "
                    "renders correctly inside a div wrapper, never inside a p.</p>"
                ),
            )
        )
        .section(
            TwoColumn(
                ratio="50-50",
                title="Two Views",
                left=TextBlock(
                    "<p>The legal block below renders from a single template — "
                    "the disclaimer, copyright line, and both links all present.</p>"
                ),
                right=DataTable(
                    headers=["Metric", "Level"],
                    rows=[
                        TableRow(["Policy rate", "4.25%"]),
                        TableRow(["Core CPI", "2.8%"]),
                    ],
                    source="Hermes Research",
                ),
            )
        )
        .build()
    )
