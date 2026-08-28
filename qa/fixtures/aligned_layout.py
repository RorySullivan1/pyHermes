"""
Every alignment axis at once — the fixture that closes epic #124.

#125 normalised the two spellings, #126 gave a container an ``align`` and
#127 gave five prose components one. Each landed with its own tests, and each
is invisible in a golden until an email actually uses it — so this is the
email a *cross-axis* regression shows up in, the way ``custom_banner`` is for
the masthead and ``rich_table`` for the table.

Four situations, because no fewer can carry the epic honestly:

* **a centred section whose title follows** — the specific thing #126 showed
  does not happen by itself. The heading and the content are sibling tables
  in ``full-width.html``, not parent and child, so the declaration has to
  land twice; a centred section with a left heading reads as a bug, and only
  this fixture makes it visible at a glance;
* **a component overriding its container** — a right-aligned block inside a
  centred section, which is what shows the cascade *as* a cascade rather
  than as a single setting. Nothing in Python resolves it: the component's
  declaration sits on a descendant of the cell carrying the container's, and
  inheritance is the weakest source;
* **a structural component inside an aligned section** — a ``CardGroup``
  and a ``DataTable`` in a **right**-aligned band, sitting unmoved. This is
  the epic's boundary rendered as an image, and the band is right-aligned on
  purpose: a centred one could not tell "the KPI strip kept its own
  alignment" from "the KPI strip inherited the section's";
* **an aligned split** — ``columns.html`` applies the declaration per column
  cell, which is a different shape from a centred full-width band.

The body is short for ``custom_banner``'s reason: ``kitchen_sink`` exercises
the component library, and a fat body here would make this golden noisy for
reasons unrelated to alignment. Theme, size and font stay **default** — a
preset moving alongside an alignment axis would leave a golden diff nobody
can attribute.

It also carries one thing that is **not** an alignment axis: an explicit
``Container.background_color``. Widening the field-completeness rule to
containers found that field — the original entry in the closed colour list —
had never been set by any fixture at all, so nothing pinned how a
caller-supplied band colour renders. A brand-new fixture is the cheapest
place to close that, since no existing golden has to move for it.

This fixture shipped one commit ahead of #129, when a column's content cell
still shrink-wrapped to its copy instead of filling its column — so a
split's alignment reached every cell correctly and had nowhere to show. Its
docstring predicted that fixing #129 would move this golden, and it did, by
five lines. The two columns are still written long enough to fill their
width: that was a workaround then and is honest content now, and shortening
them would only make the golden pin less.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from svc.builder import (
    CardGroup,
    DataTable,
    Email,
    EmailBuilder,
    FullWidth,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from svc.builder.models import Card, Column, TableRow

#: Fixed, like every string in the gallery: a golden cannot pin a value that
#: moves. See the module docstring in :mod:`qa.fixtures`.
_YEAR = "2026"


def _metadata() -> dict[str, Any]:
    return {
        "email_subject": "Aligned Layout — where a section's copy sits",
        "preheader_text": "One email exercising every alignment axis at once.",
        "firm_name": "Hermes Research",
        "campaign_name": "aligned-layout",
        "department": "Rates Strategy",
        "date_range": "Week ending 24 August",
        "issue_label": "Issue 009",
        "header_disclaimer": "For illustrative purposes. Not investment advice.",
        "current_year": _YEAR,
        "unsubscribe_url": "https://example.com/unsubscribe",
        "view_in_browser_url": "https://example.com/archive/009",
    }


def build(template_dir: Path | None = None) -> Email:
    """Build the aligned-layout email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(_metadata())
        # 1. The default. Present so the golden holds one section that states
        #    nothing, which is what makes the other four legible as deviations
        #    rather than as the house style.
        .section(
            FullWidth(
                title="Stated Nothing",
                content=TextBlock(
                    "This section sets no alignment, so it renders exactly as every "
                    "email did before the epic — which is the claim three of its four "
                    "commits make about the goldens."
                ),
            )
        )
        # 2. A centred section, title following.
        .section(
            FullWidth(
                title="Centred, Heading And All",
                align="center",
                content=TextBlock(
                    "The heading above and this paragraph take one declaration on two "
                    "sibling cells. A centred section whose heading stayed left is the "
                    "half-applied result that reads as a bug.",
                    subtitle="The standfirst belongs to the block, not to the section",
                ),
            )
        )
        # 3. A component disagreeing with its container.
        .section(
            FullWidth(
                title="Centred, With One Block Opting Out",
                align="center",
                content=TextBlock(
                    "This block sets its own alignment and wins by ordinary CSS "
                    "cascade — its declaration sits on a descendant of the cell "
                    "carrying the section's, and inheritance is the weakest source. "
                    "No Python resolves it, and no signature grew a parameter.",
                    align="right",
                ),
            )
        )
        # 4. The boundary: structural components in a right-aligned band.
        .section(
            FullWidth(
                title="Right-Aligned, Holding Structure",
                align="right",
                highlight=True,
                content=CardGroup(
                    [
                        Card("S&P 500", "5,234", "#4A7C59", "+1.42%"),
                        Card("UST 10Y", "4.28%", "#B85450", "+6 bps"),
                        Card("VIX", "14.32", "#4A7C59", "-2.18 pts"),
                    ],
                    orientation="horizontal",
                ),
            )
        )
        .section(
            FullWidth(
                title="Right-Aligned, Holding A Table",
                align="right",
                content=DataTable(
                    headers=[Column("Factor", kind="text"), "1M", "YTD"],
                    rows=[
                        TableRow(["Value", "+1.8%", "+7.4%"]),
                        TableRow(["Momentum", "-0.4%", "+11.2%"]),
                    ],
                    caption="Factor performance, gross of costs",
                ),
            )
        )
        # 5. A split, where the declaration lands per column cell.
        .section(
            TwoColumn(
                ratio="50-50",
                title="Centred Split",
                align="center",
                # Not an alignment axis, and here on purpose. Widening the
                # field-completeness rule to containers (#128) found that
                # `background_color` — the *original* entry in the closed
                # colour list — had never been set by any fixture, so no
                # golden pinned the caller's own band colour. This is the
                # cheapest place to close that: a brand-new fixture, so no
                # existing golden moves to accommodate it.
                background_color="#F4F1EC",
                left=TextBlock(
                    "The left half of a centred split, written wide enough that the "
                    "section's centring has room to be visible in a screenshot."
                ),
                right=TextBlock(
                    "The right half of the same split, written to the same width for "
                    "the same reason. Both cells carry the declaration."
                ),
            )
        )
        .section(
            ThreeColumn(
                ratio="33-33-33",
                title="Three Columns, One Disagreeing",
                align="center",
                left=TextBlock("Centred by the section, like its neighbour to the right."),
                center=TextBlock(
                    "This middle column states left and keeps it, inside a centred split.",
                    align="left",
                ),
                right=TextBlock("Centred by the section, like its neighbour to the left."),
            )
        )
        .build()
    )
