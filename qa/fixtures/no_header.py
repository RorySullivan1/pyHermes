"""
An email with no strip at all — the ``EmptyHeader`` variant, in the gallery.

The variant that proves the seam, and a seam with one implementation is a
refactor. This differs from ``minimal`` in exactly one argument —
``EmailBuilder.header(EmptyHeader())`` — so its golden pins that a region
which fills *no* slot renders genuinely nothing: no band, no empty ``<tr>``,
no trace of the strip's markup at all.

Two deliberate pairings:

* **The default banner**, per ``minimal_footer``'s worked reasoning. The two
  region choices are independent, and an email swapping both at once could
  not say which one moved a byte. So the masthead below is byte-identical to
  the way a default ``Header`` renders it.
* **A `header_disclaimer` that is set.** ``minimal`` already covers the empty
  one, and an empty one here would prove nothing — the strip would be
  absent either way, and the golden could not tell "the variant omitted it"
  from "there was nothing to render". Copy the email owns, and a region that
  declines to display it, is the whole distinction.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import Email, EmailBuilder, EmptyHeader, FullWidth, TextBlock


def build(template_dir: Path | None = None) -> Email:
    """Build the no-header email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "No Header — the strip omitted entirely",
                "preheader_text": "The region fills no slot, so nothing renders.",
                "firm_name": "Hermes Research",
                "campaign_name": "no-header",
                "date_range": "Week ending 24 August",
                "issue_label": "Issue 005",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/005",
            }
        )
        .header(EmptyHeader())
        .section(
            FullWidth(
                title="Body Unchanged",
                content=TextBlock(
                    "<p>Omitting the strip is a region choice; nothing below it moves.</p>"
                ),
            )
        )
        .build()
    )
