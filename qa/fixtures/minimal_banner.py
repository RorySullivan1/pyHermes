"""
The ``MinimalBanner`` variant — a flat band with no VML.

The masthead's background image and its Outlook ``v:rect`` fallback are the
most fragile markup in the package, so the variant that omits both needs its
own golden: it is what shows the flat path still renders when the VML path
changes.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import (
    CardGroup,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    MinimalBanner,
    TextBlock,
)
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import Card

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
                "email_subject": "Minimal Banner — the variant, same facts",
                "preheader_text": "A flat masthead band, no background image, no VML.",
                "firm_name": "Hermes Research",
                "campaign_name": "minimal-header",
                "date_range": "Week ending 24 August",
                "issue_label": "Issue 002",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/002",
            }
        )
        .banner(MinimalBanner(logo_url=_LOGO))
        .footer(Footer(disclaimer="<p>Distributed to registered recipients only.</p>"))
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
