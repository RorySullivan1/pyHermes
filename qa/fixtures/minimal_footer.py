"""
The ``MinimalFooter`` variant, in the gallery.

The footer's counterpart to :mod:`qa.fixtures.minimal_header`, and the same
argument: a seam with one implementation is a refactor. This email differs
from the default-footer fixtures in exactly one argument —
``EmailBuilder.footer(MinimalFooter())`` — and nothing about the skeleton,
the body, the masthead or the email's own facts moves with it.

What the golden on this fixture pins that no other one can:

* the contact card is **absent**, and with it the ``v:roundrect`` dual
  emission — the footer's most fragile markup, gone by omission rather than
  by a conditional in a template;
* the legal block is **byte-identical** to the one the default footer
  renders, because the variant composes that template rather than forking
  it — disclaimer, copyright line, unsubscribe and view-in-browser links all
  still there, which is the compliance floor the region enforces;
* the email-level facts still flow down unchanged.

It pairs ``MinimalFooter`` with the default ``Header`` on purpose: the two
region choices are independent, and a fixture that swapped both at once
could not say which one moved a byte.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import (
    DataTable,
    Email,
    EmailBuilder,
    FullWidth,
    MinimalFooter,
    TextBlock,
    TwoColumn,
)
from svc.builder.models import TableRow


def build(template_dir: Path | None = None) -> Email:
    """Build the minimal-footer email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Minimal Footer — legal only, no contact card",
                "preheader_text": "The closing region without its courtesy half.",
                "firm_name": "Hermes Research",
                "campaign_name": "minimal-footer",
                "date_range": "Week ending 31 August",
                "issue_label": "Issue 003",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "footer_disclaimer": (
                    "<p>Distributed to registered recipients only. "
                    "Past performance is not indicative of future results.</p>"
                ),
                "contact_url": "https://example.com/contact",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/003",
            }
        )
        # The label goes on the region, not in the metadata dict: an explicit
        # region replaces the one the flat keywords built, so a flat
        # ``unsubscribe_label`` here would be silently discarded. Presentation
        # belongs to whichever region actually renders.
        .footer(MinimalFooter(unsubscribe_label="Remove me from this list"))
        .section(
            FullWidth(
                title="Same Email, Shorter Close",
                content=TextBlock(
                    "<p>Choosing a footer region is an argument, not a template fork — "
                    "and the contact card is dropped by leaving a slot unfilled, so no "
                    "template grows a conditional to express its absence.</p>"
                ),
            )
        )
        .section(
            TwoColumn(
                ratio="50-50",
                title="Two Views",
                left=TextBlock(
                    "<p>The legal block below is rendered from the very same template "
                    "the default footer uses.</p>"
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
