"""
The structured ``Footer`` variant, in the gallery.

The footer's counterpart to :mod:`qa.fixtures.minimal_banner`. This email
uses a ``Footer`` exercising the visual surface — ``background_color``,
``border=True``, and an attached sign-off image — in addition to a
disclaimer, demonstrating that:

* a tinted, bordered footer renders without a full kitchen-sink email;
* an attached ``EmailImage`` in the footer reaches the asset manifest;
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
from svc.builder.images import EmailImage
from svc.builder.models import TableRow

from ._png import solid_png

_SIGNOFF_PNG = solid_png(96, 96, (42, 61, 84))


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
                background_color="#F2F1EE",
                border=True,
                image=EmailImage.attached(
                    _SIGNOFF_PNG,
                    alt="Sign-off",
                    width=96,
                ),
                disclaimer=(
                    "<p>Distributed to registered recipients only. "
                    "Past performance is not indicative of future results.</p>"
                ),
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
