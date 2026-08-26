"""
The ``MinimalHeader`` variant, in the gallery.

The proof that a region is a seam and not a refactor: this email differs from
the others in exactly one argument — ``EmailBuilder.header(MinimalHeader(...))``
— and nothing about the skeleton, the body, or the email's own facts moves
with it.

What the golden on this fixture pins that no other one can:

* the variant renders **no** ``v:rect``/``v:fill``/``v:textbox`` and no
  ``background-image``, which is the whole reason it exists;
* the email-level facts still flow down — firm name, campaign name, date
  range, issue label and the header disclaimer all appear, from
  ``EmailMetadata``, exactly as they do under the default header;
* a **CID logo** on a variant reaches ``assets()`` once, through the region's
  own ``images()`` rather than through the metadata.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import (
    CardGroup,
    Email,
    EmailBuilder,
    FullWidth,
    MinimalHeader,
    TextBlock,
)
from svc.builder.images import EmailImage
from svc.builder.models import Card

from ._png import solid_png

#: Attached, not hosted: the manifest claim above is only worth pinning if the
#: logo actually has bytes to attach.
_LOGO = EmailImage.attached(solid_png(64, 64, (91, 138, 154)), alt="Hermes mark", width=72)


def build(template_dir: Path | None = None) -> Email:
    """Build the minimal-header email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Minimal Header — the variant, same facts",
                "preheader_text": "A flat masthead band, no background image, no VML.",
                "firm_name": "Hermes Research",
                "campaign_name": "minimal-header",
                "date_range": "Week ending 24 August",
                "issue_label": "Issue 002",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "footer_disclaimer": "<p>Distributed to registered recipients only.</p>",
                "contact_description": "Reach the research desk with questions.",
                "contact_url": "https://example.com/contact",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/002",
            }
        )
        .header(MinimalHeader(logo_url=_LOGO))
        .section(
            FullWidth(
                title="Same Body, Different Masthead",
                content=TextBlock(
                    "<p>The body is untouched by the choice of header region — "
                    "selecting one is an argument, not a template fork.</p>"
                ),
            )
        )
        .section(
            FullWidth(
                title="Market Snapshot",
                highlight=True,
                content=CardGroup(
                    [
                        Card("S&P 500", "5,234", "#4A7C59", "+1.42%"),
                        Card("UST 10Y", "4.28%", "#B85450", "+6 bps"),
                    ],
                    orientation="horizontal",
                ),
            )
        )
        .build()
    )
