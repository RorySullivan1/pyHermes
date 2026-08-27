"""
The ``slate`` preset, in the gallery.

The colour epic's counterpart to ``minimal_banner`` / ``minimal_footer``: a
fixture that exists to pin one *choice*. It differs from ``kitchen_sink`` in
exactly one metadata field — ``theme`` — and its golden is what proves the
palette is live in every corner of a rendered email rather than only in the
inline styles a spot-check would look at.

What this golden pins that no other one can:

* the second preset renders at all, and renders *completely*: no token
  falls back to a classic value anywhere, including inside the dark-mode
  forcing block and the mobile media query, which used to carry their own
  hardcoded copies of surface and text colours;
* both halves of the Outlook scrim move together — the CSS ``rgba()`` and
  the VML ``color``/``opacity`` attribute pair;
* an unset ``Card.color`` resolves against *this* theme's neutral, while a
  caller's explicit colour survives untouched — the semantic-vs-presentation
  boundary, in one email.

It also retires an exemption: ``kitchen_sink`` could not set ``theme`` to a
distinctive value while only one preset existed, so the metadata
completeness test skipped the field. This fixture is what makes it real.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import (
    AuthorBlock,
    CardGroup,
    DataTable,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    NumberedList,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from svc.builder.models import Card, NumberedItem, TableRow


def build(template_dir: Path | None = None) -> Email:
    """Build the slate-themed email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Slate — the same email in a second palette",
                "preheader_text": "One field changes; every colour follows.",
                "firm_name": "Hermes Research",
                "campaign_name": "slate-preset",
                "date_range": "Week ending 7 September",
                "issue_label": "Issue 004",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/004",
                "theme": "slate",
            }
        )
        .footer(Footer(disclaimer="<p>Distributed to registered recipients only.</p>"))
        .section(
            FullWidth(
                title="A Palette Is One Argument",
                content=TextBlock(
                    "<p>Choosing a theme is a single metadata field. Every surface, "
                    "rule, text tone and shadow in this email follows from it — "
                    "including the ones only Outlook and dark-mode clients see.</p>"
                ),
            )
        )
        .section(
            FullWidth(
                title="Highlighted Band",
                highlight=True,
                content=CardGroup(
                    [
                        # The left card states its own colour: caller data about
                        # the number. The right one says nothing and takes the
                        # theme's neutral. Both behaviours in one section.
                        Card("S&P 500", "5,234", "#3F7A63", "+1.42%"),
                        Card("Coverage", "128 names"),
                    ],
                    orientation="horizontal",
                ),
            )
        )
        .section(
            TwoColumn(
                ratio="30-70",
                title="Table And Prose",
                left=NumberedList(
                    [
                        NumberedItem("1", "Rates", "<p>Front end steady.</p>"),
                        NumberedItem("2", "Credit", "<p>Spreads firm.</p>"),
                    ]
                ),
                right=DataTable(
                    headers=["Metric", "Level", "Change"],
                    rows=[
                        TableRow(["Policy rate", "4.25%", "unch"]),
                        TableRow(["Core CPI", "2.8%", "-0.1"], colors=["", "", "#3F7A63"]),
                        TableRow(["Unemployment", "4.1%", "+0.1"]),
                    ],
                    source="Hermes Research",
                    as_of="7 September 2026",
                ),
            )
        )
        .section(
            ThreeColumn(
                ratio="33-33-33",
                left=TextBlock("<p>Left.</p>"),
                center=TextBlock("<p>Centre.</p>"),
                right=TextBlock("<p>Right.</p>"),
            )
        )
        .section(
            FullWidth(
                content=AuthorBlock(
                    name="A. Analyst",
                    job_title="Head of Research",
                    email="research@example.com",
                )
            )
        )
        .build()
    )
