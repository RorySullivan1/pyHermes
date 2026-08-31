"""
All three embed strategies, side by side.

The fixture that exercises the manifest seam: ``hosted`` images contribute
nothing to ``assets()``, ``inline`` images carry their own bytes in the HTML,
and only ``attached`` images produce entries — so a render of this fixture is
the shortest proof that ``Email.assets()`` reports exactly the ``cid:``
references the HTML contains, no more and no fewer.

It is also the fixture the size budget bites on first: the data-URI section is
the one that spends the 102 KB budget rather than message weight.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import Email, EmailBuilder, Footer, FullWidth, ImageBlock, TextBlock, TwoColumn
from svc.builder.enums import ImageAlign, TwoColumnRatio
from svc.builder.images import EmailImage
from svc.builder.models import EmailMetadata

from ._png import solid_png

# Distinct colours so the three strategies are told apart in a screenshot, and
# distinct bytes so their content-addressed Content-IDs differ.
_HOSTED_PIXEL = solid_png(48, 48, (42, 61, 84))  # never embedded; hosted has no bytes
_ATTACHED_PNG = solid_png(160, 90, (74, 124, 89))
_INLINE_PNG = solid_png(120, 60, (184, 84, 80))

#: The same attached image used twice on purpose: Content-IDs are
#: ``sha256(bytes)[:16]``, so both references must resolve to one manifest
#: entry rather than attaching the bytes twice.
_REPEATED = EmailImage.attached(_ATTACHED_PNG, alt="Attached chart", width=160)


def build(template_dir: Path | None = None) -> Email:
    """Build the image-matrix email. Deterministic: same bytes every call."""
    metadata = EmailMetadata(
        email_subject="Image Matrix — hosted, attached, inline",
        preheader_text="One section per embed strategy.",
        firm_name="Hermes Research",
        campaign_name="image-matrix",
        current_year="2026",
    )

    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(metadata)
        .footer(Footer(disclaimer="<p>Distributed to registered recipients only.</p>"))
        .section(
            FullWidth(
                title="Remote",
                content=ImageBlock(
                    EmailImage.hosted(
                        "https://cdn.example.com/hosted-chart.png",
                        alt="Hosted chart",
                        width=160,
                    ),
                    caption=(
                        "Costs no message weight; Outlook blocks it until the reader allows images."
                    ),
                    link_url="https://example.com/charts/hosted",
                    align=ImageAlign.CENTER,
                ),
            )
        )
        .section(
            FullWidth(
                title="Attached (cid:)",
                content=ImageBlock(
                    _REPEATED,
                    caption=(
                        "Costs message size, not HTML size — renders in Outlook without a prompt."
                    ),
                    align=ImageAlign.LEFT,
                ),
            )
        )
        .section(
            FullWidth(
                title="Inline (data URI)",
                content=ImageBlock(
                    EmailImage.inline(_INLINE_PNG, alt="Inline sparkline", width=120),
                    caption="Spends the 102 KB budget directly; Gmail strips it.",
                    align=ImageAlign.RIGHT,
                ),
            )
        )
        .section(
            FullWidth(
                title="Decorative",
                content=ImageBlock(
                    EmailImage.hosted(
                        "https://cdn.example.com/divider-rule.png",
                        width=200,
                        decorative=True,
                    ),
                    caption=(
                        'Carries no information, so it renders alt="" and a screen '
                        "reader skips it — the caption is the copy meant to be read."
                    ),
                    align=ImageAlign.CENTER,
                ),
            )
        )
        # The repeated attachment, in a column layout, next to prose.
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.EQUAL,
                title="The Same Attachment, Twice",
                left=ImageBlock(_REPEATED, caption="Second reference to the same bytes."),
                right=TextBlock(
                    "<p>Content-IDs are content-addressed, so this resolves to the "
                    "single manifest entry above rather than attaching the image again.</p>"
                ),
            )
        )
        .build()
    )
