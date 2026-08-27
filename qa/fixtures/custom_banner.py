"""
Every banner axis at once — the fixture that closes epic #88.

Each axis landed with its own tests, but the epic's promise is the
*combination*, and a per-axis test cannot see an interaction. This is the
email a cross-axis regression shows up in:

* **free-form copy** (#91) — a ``title`` and ``subtitle`` that are neither
  ``firm_name`` nor ``campaign_name``, so the golden pins that the masthead
  says one thing while every other site still says the other;
* **a department** (#92) — sharing the subtitle's row, which is what the 2x2
  masthead exists for;
* **an attached background image** — a ``cid:`` reference in a CSS
  ``background-image`` *and* in the VML ``v:fill``, which is the one embed
  path no other fixture covers. ``image_matrix`` pins that ``assets()``
  matches the HTML's references and ``minimal_banner`` pins a CID *logo*;
  nothing until now attached a CID **background**, and it reaches the
  manifest through ``Banner.images()``' walk of ``IMAGE_FIELDS`` rather than
  through a component;
* **a `BannerPalette`** (#93) — all eight roles, chosen *for the image
  underneath them* rather than as arbitrary distinctive values, because the
  whole reason the exception exists is a backdrop the theme cannot see.

The body is deliberately short. Its job is to put the masthead in a real
email rather than to re-exercise the component library — ``kitchen_sink``
already does that, and a fat body here would make this golden noisy for
reasons that have nothing to do with the banner.

**The theme stays ``classic``.** A preset *and* a palette moving at once
would leave a golden diff nobody can attribute, and ``slate_theme`` already
pins the preset path.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import (
    Banner,
    BannerPalette,
    CardGroup,
    DataTable,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    Rgba,
    TextBlock,
    TwoColumn,
)
from svc.builder.enums import TwoColumnRatio
from svc.builder.images import EmailImage
from svc.builder.models import Card, TableRow

from ._png import solid_png

#: A deep teal field. Solid rather than photographic because the gallery's
#: determinism rule forbids a checked-in binary, and what this fixture needs
#: from the image is that it *is* a caller's own backdrop with bytes to
#: attach — not that it looks like a photograph.
_BACKDROP = EmailImage.attached(solid_png(680, 220, (18, 58, 62)), alt="Masthead backdrop")

#: Attached too, so the manifest carries two distinct entries from one region
#: and the golden pins their order.
_LOGO = EmailImage.attached(solid_png(140, 40, (226, 214, 190)), alt="Hermes Research", width=118)

#: Tuned to ``_BACKDROP``, not picked for contrast with the theme. Warm sand
#: over deep teal reads; the theme's white-on-navy ladder would not, and that
#: mismatch is the entire argument for the field existing. Contrast stays a
#: recommendation — nothing here is validated for legibility, and this
#: fixture is judged by ``python -m qa.preview custom_banner --screenshot``.
_PALETTE = BannerPalette(
    band="#123A3E",
    title="#F4EADA",
    subtitle="#CBD9D6",
    meta="#8FAEA9",
    accent="#D9A05B",
    scrim=Rgba("#08211F", 0.45),
    title_shadow=Rgba("#04100F", 0.5),
    subtitle_shadow=Rgba("#04100F", 0.35),
)


def build(template_dir: Path | None = None) -> Email:
    """Build the custom-banner email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Q3 Outlook — the desk's own masthead",
                "preheader_text": "Free-form copy, a department, a backdrop and a palette.",
                "firm_name": "Hermes Research",
                "campaign_name": "custom-banner",
                "department": "Rates Strategy",
                "date_range": "Week ending 24 August",
                "issue_label": "Issue 004",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/004",
            }
        )
        .banner(
            Banner(
                background_image_url=_BACKDROP,
                logo_url=_LOGO,
                title="Q3 Outlook",
                subtitle="What the curve is pricing",
                palette=_PALETTE,
            )
        )
        .footer(Footer(disclaimer="<p>Distributed to registered recipients only.</p>"))
        .section(
            FullWidth(
                title="Market Snapshot",
                highlight=True,
                content=CardGroup(
                    [
                        Card("UST 2Y", "4.61%", "#B85450", "+8 bps"),
                        Card("UST 10Y", "4.28%", "#B85450", "+6 bps"),
                        Card("2s10s", "-33 bps", "#4A7C59", "+2 bps"),
                    ],
                    orientation="horizontal",
                ),
            )
        )
        .section(
            TwoColumn(
                title="Curve and Carry",
                ratio=TwoColumnRatio.WIDE_NARROW,
                left=TextBlock(
                    "<p>The front end repriced on the payrolls beat while the long "
                    "end barely moved, leaving the curve flatter into month-end.</p>"
                ),
                right=DataTable(
                    headers=["Tenor", "Δ 1W"],
                    rows=[
                        TableRow(["2Y", "+8 bps"], colors=["", "#B85450"]),
                        TableRow(["10Y", "+6 bps"], colors=["", "#B85450"]),
                        TableRow(["30Y", "+1 bp"], colors=["", "#4A7C59"]),
                    ],
                ),
            )
        )
        .build()
    )
