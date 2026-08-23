"""
Data models for the email builder.

Uses dataclasses for structured configuration with validation.
These models define the shape of data flowing through the builder —
metadata for the email skeleton, typed data for each component, etc.
"""

import re
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any

from .exceptions import ValidationError

if TYPE_CHECKING:  # pragma: no cover - import cycle: images imports _validate_url
    from .images import EmailImage, ImageAsset

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def _require(value: Any, name: str) -> None:
    """Raise if value is None or empty string."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"'{name}' is required and cannot be empty.")


def _validate_color(value: str, name: str) -> None:
    """Raise if value is not a valid hex color."""
    if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
        raise ValidationError(f"'{name}' must be a hex color (e.g. #4A7C59), got: {value}")


# Schemes safe to emit into an href/src in an HTML email.  `cid` covers
# images embedded as MIME parts.
_ALLOWED_URL_SCHEMES = frozenset({"http", "https", "mailto", "cid"})


def _validate_url(value: str, name: str) -> None:
    """
    Raise if value carries a scheme that is unsafe in an href/src.

    Escaping (#12) stops a URL breaking *out* of its attribute; it does
    nothing about what the URL then does when followed, which is what this
    checks.  Empty is allowed — every URL field in the builder is optional.

    Scheme-only: whether the URL resolves, and what its host or path are,
    is not this function's business.
    """
    if not value:
        return
    scheme, separator, _ = value.partition(":")
    if not separator:
        return  # relative URL — no scheme to object to
    if scheme.lower().strip() not in _ALLOWED_URL_SCHEMES:
        allowed = ", ".join(sorted(_ALLOWED_URL_SCHEMES))
        raise ValidationError(
            f"'{name}' uses unsupported URL scheme '{scheme}'; allowed: {allowed}. Got: {value!r}"
        )


# ──────────────────────────────────────────────────────────────────────
# Email-level metadata
# ──────────────────────────────────────────────────────────────────────


@dataclass
class EmailMetadata:
    """
    Top-level metadata for the email skeleton (header, footer, preheader).

    Every field maps to a variable in ``templates/base.html``.
    """

    email_subject: str = ""
    preheader_text: str = ""
    header_disclaimer: str = ""
    header_bg_image_url: "str | EmailImage" = ""
    logo_url: "str | EmailImage" = ""
    #: Logo alt text. Falls back to the EmailImage's own ``alt`` when the
    #: logo is one, then to ``firm_name`` — the logo is never left unlabelled.
    logo_alt: str = ""
    #: Logo display width in px. Falls back to the EmailImage's own ``width``,
    #: then to ``DEFAULT_LOGO_WIDTH``.
    logo_width: int | None = None
    firm_name: str = ""
    campaign_name: str = ""
    date_range: str = ""
    issue_label: str = ""
    contact_description: str = ""
    contact_url: str = ""
    footer_disclaimer: str = ""
    current_year: str = ""
    unsubscribe_url: str = ""
    view_in_browser_url: str = ""

    # Skeleton copy. Defaults reproduce what base.html used to hardcode, so
    # existing emails are unchanged; override for different wording or a
    # newsletter that isn't in English.
    contact_heading: str = "Questions or feedback?"
    contact_cta_label: str = "Contact Us"
    unsubscribe_label: str = "Unsubscribe"
    view_in_browser_label: str = "View in browser"

    #: Metadata fields that may hold an EmailImage instead of a bare URL.
    IMAGE_FIELDS = ("logo_url", "header_bg_image_url")

    #: Logo width used when neither the metadata nor the EmailImage sets one.
    DEFAULT_LOGO_WIDTH = 90

    def validate(self) -> None:
        """Validate required fields and URL schemes."""
        for fname in ("email_subject", "firm_name", "campaign_name"):
            _require(getattr(self, fname), fname)
        for fname in (
            "logo_url",
            "header_bg_image_url",
            "contact_url",
            "unsubscribe_url",
            "view_in_browser_url",
        ):
            value = getattr(self, fname)
            # An EmailImage validated its own URL (or its own bytes) at
            # construction; only a bare string still needs checking here.
            if isinstance(value, str):
                _validate_url(value, f"metadata.{fname}")

    def images(self) -> "list[EmailImage]":
        """Return the EmailImages held in the metadata's image fields."""
        from .images import EmailImage

        return [
            value
            for fname in self.IMAGE_FIELDS
            if isinstance(value := getattr(self, fname), EmailImage)
        ]

    def assets(self) -> "list[ImageAsset]":
        """Return the attachment manifest entries for the metadata images."""
        return [image.asset for image in self.images() if image.asset is not None]

    def to_dict(self) -> dict[str, Any]:
        """
        Flatten to the template context for ``base.html``.

        Image fields collapse to their resolved ``src`` — the skeleton wants
        a string to drop into an attribute, and the bytes behind a ``cid:``
        reference travel through the asset manifest instead.
        """
        from .images import EmailImage

        context = {
            f.name: value.src if isinstance(value := getattr(self, f.name), EmailImage) else value
            for f in fields(self)
        }
        context["logo_alt"] = self.resolved_logo_alt()
        context["logo_width"] = self.resolved_logo_width()
        return context

    def resolved_logo_alt(self) -> str:
        """
        The alt text the logo actually renders with.

        Explicit ``logo_alt`` wins; otherwise an ``EmailImage`` logo supplies
        its own ``alt``; otherwise the firm name, which is what the skeleton
        hardcoded before this was configurable.
        """
        from .images import EmailImage

        if self.logo_alt:
            return self.logo_alt
        if isinstance(self.logo_url, EmailImage) and self.logo_url.alt:
            return self.logo_url.alt
        return self.firm_name

    def resolved_logo_width(self) -> int:
        """The logo width actually rendered: metadata, then image, then default."""
        from .images import EmailImage

        if self.logo_width is not None:
            return self.logo_width
        if isinstance(self.logo_url, EmailImage) and self.logo_url.width is not None:
            return self.logo_url.width
        return self.DEFAULT_LOGO_WIDTH


# ──────────────────────────────────────────────────────────────────────
# Component data models
# ──────────────────────────────────────────────────────────────────────


@dataclass
class Card:
    """
    A callout: a value, a piece of wording, or both.

    The shared unit behind every card group — a KPI cell in a horizontal
    strip and a stacked row in a vertical one are the same data, laid out
    differently.

    Attributes:
        label:    Short eyebrow above the value (e.g. "S&P 500"). Required.
        value:    The headline figure or phrase, set large.
        color:    Hex colour for the value. Defaults to neutral grey.
        sublabel: Small caption under the value (e.g. "+1.42% WoW").
        body:     Optional prose beneath the card. **HTML field** — emitted
                  raw so callers can pass markup, so escaping untrusted text
                  in it is the caller's job (see filters.escape_html).

    Either ``value`` or ``body`` must be present: a card with only a label
    has nothing to say.
    """

    label: str
    value: str = ""
    color: str = "#5A5A5A"
    sublabel: str = ""
    body: str = ""

    def validate(self) -> None:
        _require(self.label, "card.label")
        _validate_color(self.color, "card.color")
        if not self.value and not self.body:
            raise ValidationError(
                "'card' requires a 'value' or a 'body'; a label alone says nothing."
            )


@dataclass
class KpiItem(Card):
    """
    A :class:`Card` used as a KPI stat.

    Adds no fields — it exists so KPI code reads as KPI code, and so the
    stricter rule holds: a KPI always has a value, where a general card may
    carry prose instead.
    """

    def validate(self) -> None:
        _require(self.label, "kpi.label")
        _require(self.value, "kpi.value")
        _validate_color(self.color, "kpi.color")


@dataclass
class TableRow:
    """A single row in a data table."""

    cells: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)

    def validate(self) -> None:
        # colors is index-aligned with cells; the template indexes it directly
        # (row.colors[loop.index0]), so a short list raises under StrictUndefined.
        # Empty means "no colors" and is allowed.
        if self.colors and len(self.colors) != len(self.cells):
            raise ValidationError(
                f"'table_row.colors' must be empty or the same length as 'cells' "
                f"({len(self.cells)}), got {len(self.colors)}."
            )
        for c in self.colors:
            if c:
                _validate_color(c, "table_row.color")


@dataclass
class NumberedItem:
    """A single item in a numbered list."""

    number: str
    title: str
    body: str

    def validate(self) -> None:
        _require(self.title, "numbered_item.title")
        _require(self.body, "numbered_item.body")


# ──────────────────────────────────────────────────────────────────────
# Section configuration
# ──────────────────────────────────────────────────────────────────────


@dataclass
class SectionConfig:
    """
    Configuration for one email section.

    Attributes:
        container:   Container template name (e.g. ``"full-width"``).
        component:   Component template path relative to templates/
                     (e.g. ``"analysis/kpi-strip"``).
        data:        Data dict passed to the component template.
        title:       Optional section heading.
        background_color: Optional background color override.
    """

    container: str
    component: str
    data: dict[str, Any] = field(default_factory=dict)
    title: str | None = None
    background_color: str | None = None

    def validate(self) -> None:
        _require(self.container, "section.container")
        _require(self.component, "section.component")
        if self.background_color:
            _validate_color(self.background_color, "section.background_color")
