"""
Both footer axes at once (#98), so a cross-axis regression is visible.

Holds a caller-supplied ``LinkRow`` and the footer box's own surface —
``align``, ``background_color``, ``text_color`` — which is the *same*
``BoxSurface`` the header mixes in. A regression here means the two boxes
have stopped sharing one API, which is the claim the epic ships.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import (
    CardGroup,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    TextBlock,
)
from svc.builder.images import EmailImage
from svc.builder.models import Card, FooterLink, LinkRow

from ._png import solid_png

#: Attached rather than hosted: the sign-off mark is the one image the footer
#: region can carry, and only an attached one proves it reaches the manifest
#: through ``Footer.images()``.
_MARK = EmailImage.attached(solid_png(120, 36, (232, 238, 242)), alt="Hermes mark", width=100)


def build(template_dir: Path | None = None) -> Email:
    """Build the custom-footer email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Custom Footer — the closing box, tuned",
                "preheader_text": "A coloured footer box and a link row of its own.",
                "firm_name": "Hermes Research",
                "campaign_name": "custom-footer",
                "date_range": "Week ending 24 August",
                "issue_label": "Issue 006",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/006",
            }
        )
        .footer(
            Footer(
                align="left",
                background_color="#1B2A38",
                text_color="#D6E0E8",
                border=True,
                border_color="#2E4356",
                image=_MARK,
                disclaimer="<p>Distributed to registered recipients only.</p>",
                link_row=LinkRow(
                    copyright="© 2026 Hermes Research — all rights reserved",
                    links=[
                        FooterLink("Privacy", "https://example.com/privacy"),
                        FooterLink("Stop receiving this", "https://example.com/unsubscribe"),
                        FooterLink("Contact the desk", "mailto:research@example.com"),
                    ],
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
        .section(
            FullWidth(
                title="Same Body, Different Close",
                content=TextBlock(
                    "<p>The box below is the footer's half of the shared surface; the "
                    "strip above renders on the theme's own tokens.</p>"
                ),
            )
        )
        .build()
    )
