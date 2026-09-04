"""
Market Snapshot — a small, realistic weekly-newsletter email.

Demonstrates the core of the builder in one readable pass:

- required metadata (subject / firm / campaign) plus a preheader,
- a highlighted ``FullWidth`` section wrapping a horizontal ``CardGroup`` of KPIs
  (the coloured strip that collapses to stacked cards on mobile),
- a plain ``FullWidth`` ``TextBlock`` for the week's commentary,
- a ``ContactBlock`` call-to-action as the closing body section, and
- a structured ``Footer`` — a tinted, bordered band with a disclaimer.

Run it directly to (re)generate ``market-snapshot.html`` next to this file:

    python examples/market-snapshot/market-snapshot.py

``build()`` is a pure, deterministic factory in the same shape as the fixtures
in ``qa/fixtures/`` — same bytes every call — so it can also be imported and
rendered without touching disk.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import (
    CardGroup,
    ContactBlock,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    TextBlock,
)
from svc.builder.enums import CardOrientation
from svc.builder.models import KpiItem

# Colour vocabulary is #RRGGBB everywhere — validated at construction time.
_GAIN = "#4A7C59"
_LOSS = "#B85450"


def build(template_dir: Path | None = None) -> Email:
    """Build the Market Snapshot email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Weekly Market Wrap",
                "preheader_text": "Equities firm into the close; rates drift lower.",
                "firm_name": "Hermes Research",
                "campaign_name": "market-snapshot",
                "date_range": "Week ending 24 August 2026",
            }
        )
        # Structured footer: a tinted, bordered band (the copyright + links line
        # always renders; the disclaimer is optional and emitted raw-but-unwrapped).
        .footer(
            Footer(
                background_color="#F2F1EE",
                border=True,
                disclaimer="For illustrative purposes only. Not investment advice.",
            )
        )
        # Highlighted KPI strip: 2–4 cards across, colour-coded by direction.
        .section(
            FullWidth(
                title="Market Snapshot",
                highlight=True,
                content=CardGroup(
                    [
                        KpiItem("S&P 500", "5,234", _GAIN, "+1.42%"),
                        KpiItem("UST 10Y", "4.28%", _LOSS, "+6 bps"),
                        KpiItem("Gold", "2,411", _GAIN, "+0.85%"),
                        KpiItem("VIX", "14.32", _GAIN, "-2.18 pts"),
                    ],
                    orientation=CardOrientation.HORIZONTAL,
                ),
            )
        )
        # Prose commentary. TextBlock.content is an HTML field — the caller
        # escapes any untrusted text; curated copy like this is passed as-is.
        .section(
            FullWidth(
                title="Week in Review",
                content=TextBlock(
                    "<p>Equity markets advanced through the week as softer inflation "
                    "data revived hopes of an earlier rate cut. Breadth improved, with "
                    "cyclicals leading defensives, while Treasury yields eased across "
                    "the curve.</p>"
                ),
            )
        )
        # Closing call-to-action. ContactBlock is a body component now (it left
        # the footer in the rework), so it's placed like any other section.
        .section(
            FullWidth(
                content=ContactBlock(
                    heading="Questions about this snapshot?",
                    description="Reach the research desk any time.",
                    cta_label="Contact us",
                    cta_url="mailto:research@example.com",
                )
            )
        )
        .build()
    )


if __name__ == "__main__":
    output = Path(__file__).with_suffix(".html")
    build().save(output)
    print(f"Wrote {output}")
