"""
Research Brief — a multi-section email exercising column geometry and a chart.

A step up from ``market-snapshot``: this one shows how containers compose.

- **Two data tables side by side** — a ``TwoColumn`` at the 50-50 ratio, a
  ``DataTable`` in each half (regional equities vs. rates), with per-cell
  gain/loss colouring.
- **A KPI card beside a written summary in a 30:70 split** — a ``TwoColumn`` at
  the 30-70 (``NARROW_WIDE``) ratio: a narrow vertical ``CardGroup`` of KPIs on
  the left, a wider ``TextBlock`` commentary on the right.
- **A full-width chart** — a ``FullWidth`` wrapping a ``ChartBlock``, which
  carries a hairline border and a source line under the image. The chart image
  is generated in code and **inlined** as a ``data:`` URI so the saved HTML
  renders in a browser with no network fetch (see ``_bar_chart_png`` below).

  Inlining is deliberate for a *local preview* example. In a real newsletter use
  a **hosted** URL instead — Gmail strips ``data:`` URIs and Outlook's Word
  engine will not render them.
- **A ``ContactBlock`` call-to-action** as the closing body section.
- **A fully structured ``Footer``** — a tinted, full-box-bordered band carrying
  an inline sign-off mark above the copyright line, plus a disclaimer. This is
  the whole new footer surface in one place.

Run it directly to (re)generate ``research-brief.html`` next to this file:

    python examples/research-brief/research-brief.py

``build()`` is a pure, deterministic factory in the same shape as the fixtures
in ``qa/fixtures/`` — same bytes every call — so it can also be imported and
rendered without touching disk.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Callable
from pathlib import Path

from pyhermes.builder import (
    CardGroup,
    ChartBlock,
    ContactBlock,
    DataTable,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.enums import CardOrientation, TwoColumnRatio
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import KpiItem, TableRow

# Colour vocabulary is #RRGGBB everywhere — validated at construction time.
_GAIN = "#4A7C59"
_LOSS = "#B85450"


Pixel = tuple[int, int, int]

# Shared palette for the two generated images.
_SLATE = (42, 61, 84)
_ACCENT = (74, 124, 89)  # gain green
_TINT = (242, 241, 238)  # == the footer's #F2F1EE, so the mark sits seamlessly


def _encode_png(width: int, height: int, pixel: Callable[[int, int], Pixel]) -> bytes:
    """
    Encode an 8-bit RGB PNG from a ``pixel(x, y) -> (r, g, b)`` function.

    No Pillow, no files — only ``struct`` + ``zlib``, so the example carries no
    image dependency. Deterministic for a deterministic ``pixel``, which keeps
    the rendered HTML stable run to run.
    """
    # Each scanline is a filter byte (0 = None) followed by RGB triples.
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw += bytes(pixel(x, y))

    def _chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit truecolour
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + _chunk(b"IEND", b"")
    )


def _bar_chart_png(width: int = 560, height: int = 200) -> bytes:
    """Five vertical bars on a light ground, the last one accented, over a baseline."""
    ground = (245, 247, 250)
    axis = (203, 209, 217)
    heights = [0.42, 0.61, 0.53, 0.74, 0.9]

    margin, gap = 24, 18
    n = len(heights)
    bar_w = (width - 2 * margin - gap * (n - 1)) // n
    baseline = height - margin

    def pixel(x: int, y: int) -> Pixel:
        if baseline <= y <= baseline + 1:
            return axis
        for i, frac in enumerate(heights):
            x0 = margin + i * (bar_w + gap)
            if x0 <= x < x0 + bar_w:
                top = baseline - int(frac * (baseline - margin))
                if top <= y < baseline:
                    return _ACCENT if i == n - 1 else _SLATE
                break
        return ground

    return _encode_png(width, height, pixel)


def _mark_png(width: int = 120, height: int = 40) -> bytes:
    """
    A minimal sign-off brand mark: an accent square beside a slate wordmark bar.

    A placeholder for the footer's ``image`` slot — in production you would pass
    ``EmailImage.hosted("https://cdn.example.com/logo.png", ...)`` instead. Its
    ground matches the footer tint so its edges disappear into the band.
    """
    pad = 6
    square = height - 2 * pad
    bar_x0 = pad + square + 8

    def pixel(x: int, y: int) -> Pixel:
        if pad <= y < height - pad and pad <= x < pad + square:
            return _ACCENT
        if pad + 4 <= y < height - pad - 4 and bar_x0 <= x < width - pad:
            return _SLATE
        return _TINT

    return _encode_png(width, height, pixel)


def build(template_dir: Path | None = None) -> Email:
    """Build the Research Brief email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Research Brief — Cross-Asset Review",
                "preheader_text": "Regional equities lead; the belly of the curve richens.",
                "firm_name": "Hermes Research",
                "campaign_name": "research-brief",
                "date_range": "Week ending 24 August 2026",
            }
        )
        # Fully structured footer: a tinted, full-box-bordered band with an inline
        # sign-off mark above the copyright line, plus a disclaimer. (Use
        # EmailImage.hosted(...) for the mark in production — see _mark_png.)
        .footer(
            Footer(
                background_color="#F2F1EE",
                border=True,
                image=EmailImage.inline(_mark_png(), alt="Hermes Research", width=120),
                disclaimer="For illustrative purposes only. Not investment advice.",
            )
        )
        # 1. Two DataTables side by side (50-50). colors is index-aligned with
        #    cells; "" leaves a cell its default colour.
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.EQUAL,
                title="Regional Equities & Rates",
                left=DataTable(
                    headers=["Index", "1W", "YTD"],
                    rows=[
                        TableRow(cells=["S&P 500", "+1.4%", "+12.8%"], colors=["", _GAIN, _GAIN]),
                        TableRow(cells=["Euro Stoxx", "+0.9%", "+8.1%"], colors=["", _GAIN, _GAIN]),
                        TableRow(cells=["Nikkei", "-0.3%", "+15.2%"], colors=["", _LOSS, _GAIN]),
                    ],
                    source="Hermes Research",
                    subtitle="Total return, local currency",
                ),
                right=DataTable(
                    headers=["Tenor", "Yield", "Δ1W"],
                    rows=[
                        TableRow(cells=["UST 2Y", "4.62%", "-4 bps"], colors=["", "", _GAIN]),
                        TableRow(cells=["UST 10Y", "4.28%", "-6 bps"], colors=["", "", _GAIN]),
                        TableRow(cells=["UST 30Y", "4.51%", "+2 bps"], colors=["", "", _LOSS]),
                    ],
                    source="Hermes Research",
                    subtitle="On-the-run Treasuries",
                ),
            )
        )
        # 2. KPI card (narrow) beside a text summary (wide), 30-70.
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.NARROW_WIDE,
                title="Positioning",
                left=CardGroup(
                    [
                        KpiItem("Net Equity", "62%", _GAIN, "+4 pts w/w"),
                        KpiItem("Duration", "5.1y", _LOSS, "-0.3y w/w"),
                    ],
                    orientation=CardOrientation.VERTICAL,
                ),
                right=TextBlock(
                    "<p>We added modestly to equities on the pullback, concentrating "
                    "the increase in cyclicals where earnings revisions have turned. "
                    "In rates we trimmed duration into the rally, keeping a curve-"
                    "steepening bias as the front end prices a nearer-term cut.</p>"
                ),
            )
        )
        # 3. Full-width chart, inlined so it renders on open with no network.
        #    In production pass EmailImage.hosted(url, ...) instead.
        .section(
            FullWidth(
                title="Cumulative Performance",
                content=ChartBlock(
                    EmailImage.inline(
                        _bar_chart_png(),
                        alt="Cumulative cross-asset performance, indexed to 100",
                        width=616,
                    ),
                    source="Hermes Research",
                    subtitle="Indexed to 100 at year start",
                ),
            )
        )
        # 4. Contact card — demonstrates the new ContactBlock component.
        .section(
            FullWidth(
                content=ContactBlock(
                    heading="Questions about this note?",
                    description="Reach the research desk.",
                    cta_label="Email the desk",
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
