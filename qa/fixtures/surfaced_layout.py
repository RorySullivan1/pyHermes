"""
Every surface axis at once (#265), so a cross-axis regression is visible.

A dark band whose type turns light by itself, and one in the caller's own
colour; a bordered split in a caller's frame colour; a highlighted band framed
on all four sides; a table and figures on a dark ground keeping their own
surfaces; and a callout in every tone. Theme, size and font stay default, so
every line of its golden is a surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyhermes.builder import (
    Button,
    Callout,
    CardGroup,
    DataTable,
    Divider,
    Email,
    EmailBuilder,
    FullWidth,
    Stack,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from pyhermes.builder.models import KpiItem, TableRow

_YEAR = "2026"
_NAVY = "#1B2A38"


def _metadata() -> dict[str, Any]:
    return {
        "email_subject": "Surfaced Layout — grounds, frames and boxes",
        "preheader_text": "One email exercising every surface axis at once.",
        "firm_name": "Hermes Research",
        "campaign_name": "surfaced-layout",
        "date_range": "Week ending 9 October",
        "issue_label": "Issue 011",
        "current_year": _YEAR,
        "unsubscribe_url": "https://example.com/unsubscribe",
        "view_in_browser_url": "https://example.com/archive/011",
    }


def build(template_dir: Path | None = None) -> Email:
    """Build the surfaced-layout email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(_metadata())
        # A dark ground with no text_color: the type turns light by itself (#266).
        .section(
            FullWidth(
                title="On a Dark Ground",
                background_color=_NAVY,
                content=Stack(
                    [
                        TextBlock("<p>The title and this paragraph read light on navy.</p>"),
                        DataTable(
                            ["Tenor", "Yield"],
                            [TableRow(["2Y", "3.91%"]), TableRow(["10Y", "4.28%"])],
                            caption="Treasury yields",
                        ),
                        Button("See the curve", "https://example.com/curve"),
                    ]
                ),
            )
        )
        # The caller's own type colour, and a split framed in a caller's colour (#267).
        .section(
            TwoColumn(
                ratio="50-50",
                title="Framed in the Accent",
                background_color="#22313F",
                text_color="#F2E6C9",
                border=True,
                border_color="#5B8A9A",
                left=TextBlock("<p>Type in the caller's own cream.</p>"),
                right=CardGroup(
                    [KpiItem("Duration", "6.2y"), KpiItem("Yield", "4.1%")],
                    orientation="vertical",
                ),
            )
        )
        # A highlighted band, framed on all four sides.
        .section(
            FullWidth(
                title="Highlighted and Framed",
                highlight=True,
                border=True,
                content=Callout(
                    TextBlock("<p>An unframed neutral box on the highlight band.</p>"),
                    tone="neutral",
                    border=False,
                ),
            )
        )
        # A callout in every tone, one per column, then a rule (#268, #269).
        .section(
            ThreeColumn(
                ratio="33-33-33",
                title="Three Tones",
                left=Callout(TextBlock("<p>Breadth improved.</p>"), tone="positive", label="Up"),
                center=Callout(TextBlock("<p>Spreads widened.</p>"), tone="negative", label="Down"),
                right=Callout(TextBlock("<p>Volumes flat.</p>"), tone="neutral", label="Flat"),
            )
        )
        .section(
            FullWidth(
                content=Stack(
                    [
                        Divider(),
                        Button("Email the desk", "mailto:desk@example.com", align="right"),
                    ]
                )
            )
        )
        .build()
    )
