"""
Data models for the email builder.

Uses dataclasses for structured configuration with validation.
These models define the shape of data flowing through the builder —
metadata for the email skeleton, typed data for each component, etc.
"""

import re
from dataclasses import InitVar, dataclass, field, fields
from typing import TYPE_CHECKING, Any

from .enums import SizeTheme
from .exceptions import ValidationError

if TYPE_CHECKING:  # pragma: no cover - import cycle: images/regions import from here
    from .images import EmailImage
    from .regions import Footer, Header
    from .theming import Theme

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


def _default_header() -> "Header":
    """
    A blank :class:`~svc.builder.regions.Header`.

    Imported inside the function because ``regions`` imports this module for
    its validators — the same lazy-cycle rule ``images`` follows.
    """
    from .regions import Header

    return Header()


def _default_footer() -> "Footer":
    """A default :class:`~svc.builder.regions.Footer`. Same lazy-cycle rule."""
    from .regions import Footer

    return Footer()


def _default_theme() -> "Theme":
    """
    The shipped palette. Imported inside the function because ``theming``
    imports this module for :func:`_validate_color` — the same lazy-cycle
    rule ``images`` and ``regions`` follow.
    """
    from .theming import DEFAULT_THEME

    return DEFAULT_THEME


@dataclass
class EmailMetadata:
    """
    Email-level metadata: the facts an email is built from.

    **Facts live here; masthead presentation lives on the header.** Subject,
    preheader, firm, campaign, dates and the contact/legal copy are things
    that are *true of the email*; the background image, the logo and its
    resolution chains are one way of *presenting* them, and belong to
    :class:`~svc.builder.regions.Header`. The header is handed the facts at
    render time and cannot contradict them.

    ``header_disclaimer`` sits on the email side of that line deliberately:
    it is displayed in the masthead, but it is legal copy pairing with
    ``footer_disclaimer``, and legal copy is a fact about the email. The
    footer's line falls the same way: the disclaimer, the copyright year and
    the three outbound URLs are facts; the wording that surrounds them —
    headings, the button label, the link labels — belongs to
    :class:`~svc.builder.regions.Footer`.

    Every remaining field maps to a variable in ``templates/base.html``.

    The flat region keyword arguments are still accepted and build the region
    for you, so an email written before either split is unchanged: four for
    the masthead (``logo_url``, ``logo_alt``, ``logo_width``,
    ``header_bg_image_url``) and five for the footer (``contact_heading``,
    ``contact_description``, ``contact_cta_label``, ``unsubscribe_label``,
    ``view_in_browser_label``). Passing one *and* the region it belongs to is
    an error rather than a silent precedence rule.
    """

    email_subject: str = ""
    preheader_text: str = ""
    header_disclaimer: str = ""
    firm_name: str = ""
    campaign_name: str = ""
    date_range: str = ""
    issue_label: str = ""
    contact_url: str = ""
    footer_disclaimer: str = ""
    current_year: str = ""
    unsubscribe_url: str = ""
    view_in_browser_url: str = ""

    #: How the masthead presents the facts above. Defaults to a blank header;
    #: ``Email(header=...)`` overrides it for one email.
    header: "Header" = field(default_factory=_default_header)

    #: How the closing region words them. Defaults to the copy ``base.html``
    #: used to hardcode; ``Email(footer=...)`` overrides it for one email.
    footer: "Footer" = field(default_factory=_default_footer)

    #: Every colour and shadow the email renders with. A
    #: :class:`~svc.builder.theming.Theme` instance or the name of a curated
    #: preset; see :mod:`svc.builder.theming` for the token table. Unlike a
    #: region, this is the *entire* colour surface — there is deliberately no
    #: per-component colour parameter anywhere in the builder.
    theme: "Theme | str" = field(default_factory=_default_theme)

    #: How dense the email renders. A :class:`~svc.builder.enums.SizeTheme`
    #: member or its bare string, and nothing else — deliberately narrower
    #: than ``theme``, which also takes a custom object. See
    #: :mod:`svc.builder.sizing` for the token table and for why the two
    #: differ: callers pick a density, never a px.
    size_theme: "SizeTheme | str" = SizeTheme.STANDARD

    # Back-compatible region keywords. InitVars, so they are constructor
    # arguments only: they never become attributes and never appear in
    # ``fields()``, ``repr`` or ``==`` — the region is the single owner.
    logo_url: InitVar["str | EmailImage | None"] = None
    logo_alt: InitVar["str | None"] = None
    logo_width: InitVar["int | None"] = None
    header_bg_image_url: InitVar["str | EmailImage | None"] = None
    contact_heading: InitVar["str | None"] = None
    contact_description: InitVar["str | None"] = None
    contact_cta_label: InitVar["str | None"] = None
    unsubscribe_label: InitVar["str | None"] = None
    view_in_browser_label: InitVar["str | None"] = None

    #: Email-level facts the header region renders. Passed *down* to it; the
    #: header layers them over its own context, so it cannot shadow one.
    HEADER_FACTS = (
        "header_disclaimer",
        "firm_name",
        "campaign_name",
        "date_range",
        "issue_label",
    )

    #: Email-level facts the footer region renders, on the same terms. The
    #: three URLs are here rather than on the region because an unsubscribe
    #: address is a property of the mailing, not a way of wording it — and
    #: :meth:`validate` already checks all three schemes.
    FOOTER_FACTS = (
        "firm_name",
        "current_year",
        "footer_disclaimer",
        "contact_url",
        "unsubscribe_url",
        "view_in_browser_url",
    )

    def __post_init__(
        self,
        logo_url: "str | EmailImage | None",
        logo_alt: "str | None",
        logo_width: "int | None",
        header_bg_image_url: "str | EmailImage | None",
        contact_heading: "str | None",
        contact_description: "str | None",
        contact_cta_label: "str | None",
        unsubscribe_label: "str | None",
        view_in_browser_label: "str | None",
    ) -> None:
        from .regions import Footer, Header
        from .sizing import resolve_size_scheme
        from .theming import resolve_theme

        self.header = self._hydrate(
            Header,
            "header",
            {
                "logo_url": logo_url,
                "logo_alt": logo_alt,
                "logo_width": logo_width,
                "background_image_url": header_bg_image_url,
            },
        )
        self.footer = self._hydrate(
            Footer,
            "footer",
            {
                "contact_heading": contact_heading,
                "contact_description": contact_description,
                "contact_cta_label": contact_cta_label,
                "unsubscribe_label": unsubscribe_label,
                "view_in_browser_label": view_in_browser_label,
            },
        )

        # Resolve only to check: a preset name that names nothing is a typo,
        # and a typo belongs to construction, not to render. The field keeps
        # whatever the caller passed — Email.render() is the one resolution
        # point that turns it into a concrete Theme.
        resolve_theme(self.theme)
        resolve_size_scheme(self.size_theme)

    def _hydrate(self, region_cls: type, attr: str, legacy: dict[str, Any]) -> Any:
        """
        Build a region from the flat keywords, or keep the one already set.

        The flat names are the pre-split spelling of the region's own fields,
        so supplying both is ambiguous rather than a precedence question —
        and the ambiguity is rejected rather than resolved. ``None`` is what
        marks a keyword unsupplied, which is why every one of them defaults
        to ``None`` rather than to the value it used to carry: the region
        holds the real default now.
        """
        current = getattr(self, attr)
        supplied = {name: value for name, value in legacy.items() if value is not None}
        if not supplied:
            return current
        if current != region_cls():
            raise ValidationError(
                f"EmailMetadata got both '{attr}=' and the flat {attr} field(s) "
                f"{sorted(supplied)}. Pass one or the other — the flat names are "
                f"the pre-split spelling of the same thing."
            )
        return region_cls(**supplied)

    def validate(self) -> None:
        """Validate required fields and URL schemes."""
        for fname in ("email_subject", "firm_name", "campaign_name"):
            _require(getattr(self, fname), fname)
        for fname in ("contact_url", "unsubscribe_url", "view_in_browser_url"):
            _validate_url(getattr(self, fname), f"metadata.{fname}")

    def header_facts(self) -> dict[str, Any]:
        """The email-level facts a header region renders."""
        return {name: getattr(self, name) for name in self.HEADER_FACTS}

    def footer_facts(self) -> dict[str, Any]:
        """The email-level facts a footer region renders."""
        return {name: getattr(self, name) for name in self.FOOTER_FACTS}

    def to_dict(self) -> dict[str, Any]:
        """
        Flatten to the template context for ``base.html``.

        The regions are excluded: each renders itself from its own facts and
        arrives in the skeleton as the slot strings it fills. ``theme`` is
        excluded for the mirror-image reason: it reaches every template
        through the bound engine, so carrying it here too would give one
        value two sources — and ``size_theme`` is excluded for exactly the
        same reason, since the resolved scheme rides the same binder.
        """
        skip = {"header", "footer", "theme", "size_theme"}
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in skip}


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
        color:    Hex colour for the value. **Unset by default**, and
                  resolved at render to the active theme's neutral — a
                  construction-time default could not see a render-time
                  theme, and would pin one colour outside the palette.
                  An explicit value is validated here, exactly as before.
        sublabel: Small caption under the value (e.g. "+1.42% WoW").
        body:     Optional prose beneath the card. **HTML field** — emitted
                  raw so callers can pass markup, so escaping untrusted text
                  in it is the caller's job (see filters.escape_html).

    Either ``value`` or ``body`` must be present: a card with only a label
    has nothing to say.
    """

    label: str
    value: str = ""
    color: str = ""
    sublabel: str = ""
    body: str = ""

    def validate(self) -> None:
        _require(self.label, "card.label")
        if self.color:
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
        if self.color:
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
