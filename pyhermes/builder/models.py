"""
Data models for the email builder.

Uses dataclasses for structured configuration with validation.
These models define the shape of data flowing through the builder —
metadata for the email skeleton, typed data for each component, etc.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import InitVar, dataclass, field, fields, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar, Self

from . import formats
from .apparatus import check_markers
from .enums import ColumnAlign, ColumnKind, RowKind, SizeTheme, Tone, Trend
from .exceptions import ValidationError
from .prose import refuse_top_headings

if TYPE_CHECKING:  # pragma: no cover - import cycle: images/regions import from here
    from .images import EmailImage
    from .regions import Banner, Footer, Header
    from .theming import Theme
    from .typography import FontTheme

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


# A language tag is subtags joined by hyphens, each alphanumeric: "en",
# "en-GB", "zh-Hant-TW".  The *shape* is what this library can check.
_LANGUAGE_TAG = re.compile(r"^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$")


#: The longest stamp a sheet can carry across its diagonal at a readable size.
STAMP_MAX = 24


def _validate_stamp(value: str) -> None:
    """Raise unless ``value`` is empty or one line of at most :data:`STAMP_MAX` characters."""
    if not isinstance(value, str):
        raise ValidationError(f"'metadata.stamp' must be a string, got: {type(value).__name__}")
    if value and (not value.strip() or not value.isprintable() or len(value) > STAMP_MAX):
        raise ValidationError(
            f"'metadata.stamp' must be one line of 1 to {STAMP_MAX} printable "
            f"characters, such as 'DRAFT', got: {value!r}"
        )


def _validate_language(value: str, name: str) -> None:
    """
    Raise unless value is shaped like a language tag.

    Shape, never the registry — ``_validate_url``'s philosophy applied to
    the other attribute a reader depends on.  Whether ``fr-CA`` is a
    registered IANA subtag is not this library's business, and a lookup
    table shipped in a wheel goes stale between releases while a
    hyphen in the wrong place stays wrong forever.

    What the shape rules out is worth naming, because a bare character
    class would let all of it through: an empty tag, a leading or
    trailing hyphen, and a doubled one.  Those are the malformations a
    caller actually produces by string-building a tag from parts.
    """
    _require(value, name)
    if not _LANGUAGE_TAG.match(value):
        raise ValidationError(
            f"'{name}' must be a language tag such as 'en' or 'en-GB' — "
            f"letters, digits and single separating hyphens, got: {value}"
        )


def _validate_align(value: str, name: str) -> None:
    """
    Raise unless value is one of the three alignments a band of copy takes.

    Shared by the region boxes and the body's containers, because they
    align the same thing — see :class:`~pyhermes.builder.enums.TextAlign` for
    why that is one vocabulary and the table's is another.  Empty is
    allowed and means *unset*: a container that states no alignment emits
    no declaration, which is what keeps every pre-existing render
    byte-identical.
    """
    from .enums import TextAlign

    if value and value not in tuple(TextAlign):
        raise ValidationError(
            f"'{name}' must be one of {sorted(a.value for a in TextAlign)}, got: {value!r}"
        )


def check_valign(value: object, owner: str) -> str:
    """
    ``value`` as stored: one of :class:`~pyhermes.builder.enums.VerticalAlign`'s three (#354).

    Raises:
        ValidationError: On anything else, naming the three.
    """
    from .enums import VerticalAlign

    if isinstance(value, str) and value in tuple(VerticalAlign):
        return str(VerticalAlign(value))
    raise ValidationError(
        f"{owner}'s valign is one of {[a.value for a in VerticalAlign]}, got: {value!r}"
    )


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
    """A default strip. Imported lazily for the same cycle reason as below."""
    from .regions import Header

    return Header()


def _default_banner() -> "Banner":
    """
    A blank :class:`~pyhermes.builder.regions.Banner`.

    Imported inside the function because ``regions`` imports this module for
    its validators — the same lazy-cycle rule ``images`` follows.
    """
    from .regions import Banner

    return Banner()


def _default_footer() -> "Footer":
    """A default :class:`~pyhermes.builder.regions.Footer`. Same lazy-cycle rule."""
    from .regions import Footer

    return Footer()


def _default_fonts() -> "FontTheme":
    """The shipped typefaces. Lazy, for the same cycle reason as below."""
    from .typography import DEFAULT_FONTS

    return DEFAULT_FONTS


def _default_theme() -> "Theme":
    """
    The shipped palette. Imported inside the function because ``theming``
    imports this module for :func:`_validate_color` — the same lazy-cycle
    rule ``images`` and ``regions`` follow.
    """
    from .theming import DEFAULT_THEME

    return DEFAULT_THEME


@dataclass
class DocumentMetadata:
    """
    The facts a document is built from, whatever it is rendered onto.

    **Facts live here; presentation lives on a region.** Who sent this, when,
    in what language, under what legal copy — these are true of the document,
    and a region is handed them at render time and cannot contradict one.
    :class:`EmailMetadata` adds the facts that are true only of an email.

    Two boundary calls are worth knowing, both made for a reason rather than
    by shape:

    ``header_disclaimer`` is a *fact*, though it is displayed in the masthead:
    it is legal copy, and legal copy belongs to the document rather than to
    any one way of presenting it. #95 moved it between regions for free
    precisely because it had never been a region's to begin with.

    ``language`` is the one optional field whose default is a *claim* rather
    than a blank. An unset ``lang`` leaves a screen reader to guess from the
    reader's locale, so the field is always populated and validated by shape,
    never against the IANA registry — a lookup table shipped in a wheel goes
    stale between releases, while a trailing hyphen stays wrong forever.

    The three design axes sit here too: every medium has colours, a density
    and typefaces, and each is resolved once by the document's ``render()``.
    """

    #: The language the document is written in, as a BCP 47 tag — the
    #: ``lang`` attribute on the root element. See the class docstring for
    #: why its default is a claim rather than an absence.
    language: str = "en"
    header_disclaimer: str = ""
    firm_name: str = ""
    campaign_name: str = ""
    #: The desk within the firm, e.g. "Rates Strategy". A *fact*, decided
    #: rather than assumed: a department is who the document is from, the
    #: same kind of truth as ``firm_name``. Putting it on a region would let
    #: two renders of one document disagree about its sender. Optional —
    #: empty collapses the line entirely rather than reserving space for it.
    department: str = ""
    date_range: str = ""
    issue_label: str = ""
    current_year: str = ""
    #: A status word such as ``"DRAFT"`` on every sheet, or ``""`` for none
    #: (#342). A fact, since every medium shows it: a paper medium sets it
    #: across each sheet, an email in its header strip, and the text part
    #: opens on it. Plain text, escaped, at most :data:`STAMP_MAX` characters.
    stamp: str = ""

    #: Every colour and shadow the document renders with. A
    #: :class:`~pyhermes.builder.theming.Theme` instance or the name of a curated
    #: preset; see :mod:`pyhermes.builder.theming` for the token table. Unlike a
    #: region, this is the *entire* colour surface — there is deliberately no
    #: per-component colour parameter anywhere in the builder.
    theme: "Theme | str" = field(default_factory=_default_theme)

    #: How dense the document renders. A :class:`~pyhermes.builder.enums.SizeTheme`
    #: member or its bare string, and nothing else — deliberately narrower
    #: than ``theme``, which also takes a custom object. See
    #: :mod:`pyhermes.builder.sizing` for the token table and for why the two
    #: differ: callers pick a density, never a px. The *page* it renders onto
    #: is the medium's, not this field's (#159).
    size_theme: "SizeTheme | str" = SizeTheme.STANDARD

    #: Every typeface the document renders with. A
    #: :class:`~pyhermes.builder.typography.FontTheme` instance or the name of a
    #: curated preset — ``theme``'s width rather than ``size_theme``'s
    #: narrowness, and the asymmetry argument runs the *other way* here.
    #: Density is names-only because an untested scheme interacts with the
    #: clipping limit, the Word engine and the mobile collapse at once;
    #: a custom ``FontTheme`` is safe **by construction**, because the
    #: terminal-generic rule means Outlook always walks a chain the caller
    #: curated down to a websafe floor. A house brand face with fallbacks is
    #: the axis's core use case. See :mod:`pyhermes.builder.typography`.
    font_theme: "FontTheme | str" = field(default_factory=_default_fonts)

    def __post_init__(self) -> None:
        from .sizing import resolve_size_scheme
        from .theming import resolve_theme
        from .typography import resolve_font_theme

        _validate_language(self.language, "metadata.language")
        _validate_stamp(self.stamp)

        # Resolve only to check: a preset name that names nothing is a typo,
        # and a typo belongs to construction, not to render. The field keeps
        # whatever the caller passed — render() is the one resolution point
        # that turns it into a concrete Theme.
        resolve_theme(self.theme)
        resolve_size_scheme(self.size_theme)
        resolve_font_theme(self.font_theme)

    #: Fields :meth:`to_dict` keeps out of the template context. The three
    #: axes reach every template through the bound engine, so carrying them
    #: here too would give one value two sources. A subclass extends this.
    CONTEXT_SKIP: ClassVar[frozenset[str]] = frozenset({"theme", "size_theme", "font_theme"})

    def validate(self) -> None:
        """Validate the facts every document must carry."""
        for fname in ("firm_name", "campaign_name"):
            _require(getattr(self, fname), fname)

    def to_dict(self) -> dict[str, Any]:
        """
        Flatten to the template context the skeleton reads.

        Regions are excluded where a subclass has them: each renders itself
        from its own facts and arrives in the skeleton as the slot strings it
        fills. See :attr:`CONTEXT_SKIP`.
        """
        skip = type(self).CONTEXT_SKIP
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in skip}


@dataclass
class EmailMetadata(DocumentMetadata):
    """
    What an email adds to :class:`DocumentMetadata`.

    A subject line, inbox-preview text and the two outbound URLs are true of
    an *email* and of nothing else; the shared facts — firm, campaign, dates,
    language, legal copy — are the base class's. Splitting them is what lets
    a paged document reuse the facts without inheriting a subject line it
    could never have.

    **Masthead presentation lives on the header, not here.** The background
    image, the logo and its resolution chains are one way of *presenting*
    these facts and belong to :class:`~pyhermes.builder.regions.Banner`. The
    footer's disclaimer and contact copy are presentation on the same terms
    (pass ``Footer(disclaimer=...)``, or a
    :class:`~pyhermes.builder.components.ContactBlock` for the contact card).

    Every remaining field maps to a variable in ``templates/base.html``.

    The flat region keyword arguments are still accepted and build the region
    for you, so an email written before the header split is unchanged: four
    for the masthead (``logo_url``, ``logo_alt``, ``logo_width``,
    ``header_bg_image_url``) and two for the footer (``unsubscribe_label``,
    ``view_in_browser_label``). Passing one *and* the region it belongs to is
    an error rather than a silent precedence rule.
    """

    email_subject: str = ""
    preheader_text: str = ""
    unsubscribe_url: str = ""
    view_in_browser_url: str = ""

    #: How the strip at the top of the email presents its copy. Defaults to
    #: the centred band on the theme's own colours; ``Email(header=...)``
    #: overrides it for one email.
    header: "Header" = field(default_factory=_default_header)

    #: How the masthead presents the facts above. Defaults to a blank header;
    #: ``Email(banner=...)`` overrides it for one email.
    banner: "Banner" = field(default_factory=_default_banner)

    #: How the closing region words them. Defaults to the copy ``base.html``
    #: used to hardcode; ``Email(footer=...)`` overrides it for one email.
    footer: "Footer" = field(default_factory=_default_footer)

    # Back-compatible region keywords. InitVars, so they are constructor
    # arguments only: they never become attributes and never appear in
    # ``fields()``, ``repr`` or ``==`` — the region is the single owner.
    logo_url: InitVar["str | EmailImage | None"] = None
    logo_alt: InitVar["str | None"] = None
    logo_width: InitVar["int | None"] = None
    header_bg_image_url: InitVar["str | EmailImage | None"] = None
    unsubscribe_label: InitVar["str | None"] = None
    view_in_browser_label: InitVar["str | None"] = None

    #: The three regions join the axes: each arrives in the skeleton as the
    #: slot strings it fills, never as context of its own.
    CONTEXT_SKIP: ClassVar[frozenset[str]] = DocumentMetadata.CONTEXT_SKIP | {
        "header",
        "banner",
        "footer",
    }

    #: Document facts the strip renders. Each stays a fact rather than moving
    #: onto the region with the box's presentation: legal copy and a status
    #: belong to the *document*, the same call the footer's two URLs get.
    HEADER_FACTS = ("header_disclaimer", "stamp")

    #: Document facts the masthead renders. Passed *down* to it; the banner
    #: layers them over its own context, so it cannot shadow one.
    BANNER_FACTS = (
        "firm_name",
        "campaign_name",
        "department",
        "date_range",
        "issue_label",
    )

    #: Facts the footer region renders, on the same terms. The two URLs are
    #: here rather than on the region because an unsubscribe address is a
    #: property of the mailing, not a way of wording it — and :meth:`validate`
    #: already checks both schemes.
    FOOTER_FACTS = (
        "firm_name",
        "current_year",
        "unsubscribe_url",
        "view_in_browser_url",
    )

    def __post_init__(
        self,
        logo_url: "str | EmailImage | None",
        logo_alt: "str | None",
        logo_width: "int | None",
        header_bg_image_url: "str | EmailImage | None",
        unsubscribe_label: "str | None",
        view_in_browser_label: "str | None",
    ) -> None:
        from .regions import Banner, Footer

        self.banner = self._hydrate(
            Banner,
            "banner",
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
                "unsubscribe_label": unsubscribe_label,
                "view_in_browser_label": view_in_browser_label,
            },
        )

        # After hydration, so a flat-keyword conflict still names itself
        # before a bad language tag or a misspelt preset does.
        super().__post_init__()

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
        super().validate()
        _require(self.email_subject, "email_subject")
        for fname in ("unsubscribe_url", "view_in_browser_url"):
            _validate_url(getattr(self, fname), f"metadata.{fname}")

    def header_facts(self) -> dict[str, Any]:
        """The document facts the strip renders."""
        return {name: getattr(self, name) for name in self.HEADER_FACTS}

    def banner_facts(self) -> dict[str, Any]:
        """The document facts a masthead region renders."""
        return {name: getattr(self, name) for name in self.BANNER_FACTS}

    def footer_facts(self) -> dict[str, Any]:
        """The document facts a footer region renders."""
        return {name: getattr(self, name) for name in self.FOOTER_FACTS}


# ──────────────────────────────────────────────────────────────────────
# Component data models
# ──────────────────────────────────────────────────────────────────────


@dataclass
class FooterLink:
    """
    One link in the footer's copyright row.

    A pair, because a link is a pair — the label and where it goes. The URL
    passes the same scheme check every URL here does, which is a **safety**
    rule (no ``javascript:`` in an ``href``) rather than a content one: the
    library has opinions about what a link may *do*, never about which links
    an email must carry.

    Both are plain text and escaped on the way out.
    """

    label: str
    url: str

    def __post_init__(self) -> None:
        _require(self.label, "footer_link.label")
        _validate_url(self.url, "footer_link.url")


@dataclass
class LinkRow:
    """
    The footer's copyright and link line, as data rather than a template.

    ``© {year} {firm} · Unsubscribe · View in browser`` was a fixed
    structure: #64 made the *labels* fields, but the *set* stayed the
    template's, so a footer could not add a "Privacy" link or drop
    "View in browser" without forking the markup. This is the object the
    epic's requirement asked for, and the trigger is the one that made
    :class:`Card` and :class:`TableRow` objects — **the row has a
    variable-length part, and variable length is what fields cannot
    express.**

    **The library does not decide what an email must say.** pyHermes cannot
    know whether a given email is a commercial newsletter, an internal
    research note or a transactional receipt, and each answers that question
    differently — so ``links=[]`` is valid and renders a link-free row, a row
    omitting the unsubscribe destination is valid and renders what the caller
    composed, and an empty ``copyright`` is valid too. What is still
    guaranteed is narrower and worth keeping: a region *variant* may not
    silently drop what the caller supplied. That is a rule about structure,
    not about content.

    Attributes:
        copyright: Free-form **plain text**. Write the characters you mean —
                   ``©``, an em dash, an accent — and the builder emits each
                   as a numeric reference, so the line survives a client that
                   guesses the charset wrong. Writing an entity yourself
                   escapes it to literal text (#148). Empty means *resolve
                   to* ``© {current_year} {firm_name}`` from the email's own
                   facts, which is what makes an unset row byte-identical to
                   the pre-#100 render.
        links:     ``None`` means *build the default pair* from the metadata's
                   two URLs and the footer's labels — so ``link_row=None``
                   changes nothing. An explicit list, including an empty one,
                   is taken exactly as given.
    """

    copyright: str = ""
    links: list[FooterLink] | None = None

    def __post_init__(self) -> None:
        if self.links is None:
            return
        for index, link in enumerate(self.links):
            if not isinstance(link, FooterLink):
                raise ValidationError(
                    f"'link_row.links[{index}]' must be a FooterLink, got: {type(link).__name__}"
                )


#: The share of a sparkline's height its lowest value still fills, so no bar vanishes.
SERIES_FLOOR = 0.15


@dataclass(frozen=True)
class Series:
    """
    A short run of figures, drawn as a sparkline (#321).

    Each value is scaled to the series' own lowest and highest, so the shape is
    the series' and never an axis's. The lowest still fills ``SERIES_FLOOR`` of
    the height; a flat series fills half throughout.

    Attributes:
        values: Two to ``Config.sparkline_max`` figures, oldest first.
        fmt:    How the plain text writes the lowest, the last and the highest.
    """

    values: tuple[Any, ...]
    fmt: Callable[[Any], str] = formats.number

    def validate(self, owner: str = "sparkline") -> None:
        from pyhermes.config import get_config

        limit = get_config().sparkline_max
        if not 2 <= len(self.values) <= limit:
            raise ValidationError(
                f"a {owner} draws 2 to {limit} values (Config.sparkline_max), "
                f"got {len(self.values)}"
            )
        for i, value in enumerate(self.values):
            if not is_figure(value) or value != value:
                raise ValidationError(f"{owner} value {i} must be a number, got: {value!r}")
        if not callable(self.fmt):
            raise ValidationError(f"a {owner}'s format must be callable, got: {self.fmt!r}")

    def heights(self) -> list[float]:
        """Each value's share of the full height, to four places."""
        low, high = min(self.values), max(self.values)
        if high == low:
            return [0.5] * len(self.values)
        span = 1 - SERIES_FLOOR
        return [
            round(SERIES_FLOOR + span * float((value - low) / (high - low)), 4)
            for value in self.values
        ]

    def drawn(self, tone: str = "", highlight_last: bool = True) -> dict[str, Any]:
        """What ``analysis/sparkline-bars.html`` draws: the heights, the tone and the summary."""
        return {
            "heights": self.heights(),
            "tone": tone or str(Tone.NEUTRAL),
            "highlight_last": highlight_last,
            "summary": self.summary(),
        }

    def summary(self) -> str:
        """``min 3.1 · last 4.2 · max 4.2``: the series in plain text."""
        ends = (min(self.values), self.values[-1], max(self.values))
        low, last, high = (self.fmt(value) for value in ends)
        return f"min {low} · last {last} · max {high}"


def coerce_series(
    values: Any, fmt: Callable[[Any], str] | None = None, owner: str = "sparkline"
) -> Series:
    """A :class:`Series`, or a sequence of figures written with ``fmt``, validated."""
    if isinstance(values, Series):
        series = values if fmt is None else replace(values, fmt=fmt)
    elif isinstance(values, (list, tuple)):
        series = Series(tuple(values), fmt or formats.number)
    else:
        raise ValidationError(
            f"a {owner} takes a list of figures or a Series, got: {type(values).__name__}"
        )
    series.validate(owner)
    return series


@dataclass(frozen=True)
class Badge:
    """
    A short toned label on a card, a cell or a section title (#325).

    It takes a tone, never a colour, so it recolours with the theme as
    ``Card.tone`` does: drawn on a light tint of the tone's semantic colour,
    in that colour. Unset, the tone is ``neutral``. The plain-text part
    reads it as ``[LABEL]`` beside what it labels.

    Attributes:
        label: Plain text, escaped on the way out; at most ``Config.badge_max_chars``.
        tone:  ``positive``, ``negative`` or ``neutral``.
    """

    label: str
    tone: str = "neutral"

    def validate(self, owner: str = "badge") -> None:
        from pyhermes.config import get_config

        if not isinstance(self.label, str) or not self.label.strip():
            raise ValidationError(f"{owner!r} needs a label: plain text, got: {self.label!r}")
        limit = get_config().badge_max_chars
        if len(self.label) > limit:
            raise ValidationError(
                f"{owner!r} label {self.label!r} is {len(self.label)} characters; a badge takes "
                f"at most {limit} (Config.badge_max_chars). Put a longer note in the copy."
            )
        _validate_tone(self.tone, f"{owner}.tone")
        if not self.tone:
            raise ValidationError(f"{owner!r} needs a tone: {[t.value for t in Tone]}")

    def text(self) -> str:
        """``[LABEL]``: how the plain-text part marks what this labels."""
        return f"[{self.label.upper()}]"

    def drawn(self) -> dict[str, str]:
        """What the badge partial draws: the label and the tone."""
        return {"label": self.label, "tone": self.tone}


def coerce_badge(value: "Badge | str | None", owner: str = "badge") -> "Badge | None":
    """``value`` as a validated :class:`Badge`: a bare label takes the neutral tone."""
    if value is None:
        return None
    if isinstance(value, str):
        value = Badge(value)
    if not isinstance(value, Badge):
        raise ValidationError(f"{owner!r} must be a Badge or a label, got: {type(value).__name__}")
    value.validate(owner)
    return value


def check_kicker(value: object, title: str | None, owner: str) -> str:
    """
    ``value`` as a section's kicker (#333): plain text within ``Config.kicker_max_chars``.

    Raises:
        ValidationError: On a non-string, a blank, an overlong label, or a
            kicker on an untitled section, which would label nothing.
    """
    from pyhermes.config import get_config

    if value is None:
        return ""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{owner}'s kicker is plain text, got: {value!r}")
    if not title:
        raise ValidationError(
            f"{owner}'s kicker sits above its title (#333); give the section a title"
        )
    limit = get_config().kicker_max_chars
    if len(value) > limit:
        raise ValidationError(
            f"{owner}'s kicker {value!r} is {len(value)} characters; a kicker takes at most "
            f"{limit} (Config.kicker_max_chars). It orients the reader; the title says the rest."
        )
    return value


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
        color:    Hex colour for the value. **Unset by default**, and resolved
                  at render to the active theme's neutral, which a
                  construction-time default could not see. Validated if set.
        sublabel: Small caption under the value (e.g. "+1.42% WoW").
        body:     Optional prose beneath the card. **HTML field** — emitted
                  raw so callers can pass markup, so escaping untrusted text
                  in it is the caller's job (see filters.escape_html).
        tone:     What the value *means* — ``positive``, ``negative`` or
                  ``neutral`` — resolved to the live theme's semantic token
                  at render (#178). An explicit ``color`` still wins.
        trend:    Figures, or a :class:`Series`, drawn as a sparkline under the value (#321).
        badge:    A :class:`Badge`, or a label, set beside the card's label (#325).
        arrow:    The change's direction (#319), set only by :meth:`from_number`.

    Either ``value`` or ``body`` must be present: a card with only a label
    has nothing to say.
    """

    label: str
    value: str = ""
    color: str = ""
    sublabel: str = ""
    body: str = ""
    tone: str = ""
    trend: "Series | Sequence[Any] | None" = None
    badge: "Badge | str | None" = None
    arrow: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if self.trend is not None:
            self.trend = coerce_series(self.trend, owner="card trend")
        self.badge = coerce_badge(self.badge, "card.badge")

    def validate(self) -> None:
        _require(self.label, "card.label")
        if self.color:
            _validate_color(self.color, "card.color")
        _validate_tone(self.tone, "card.tone")
        if not self.value and not self.body:
            raise ValidationError(
                "'card' requires a 'value' or a 'body'; a label alone says nothing."
            )
        refuse_top_headings(self.body, "card.body")

    @classmethod
    def from_number(
        cls,
        label: str,
        value: Any,
        fmt: Callable[[Any], str] = formats.number,
        *,
        change: Any = None,
        change_fmt: Callable[[Any], str] | None = None,
        tone: str = "auto",
        good: str = "up",
        body: str = "",
        arrow: bool = False,
        trend: "Sequence[Any] | None" = None,
    ) -> Self:
        """
        A headline figure, its change beneath it, toned by what the move means (#274).

        ``value`` is written with ``fmt``; ``change``, when given, with
        ``change_fmt`` (``fmt`` if unset) into the sublabel. ``tone="auto"``
        reads the sign of the change, or of the value when there is none, through
        :func:`tone_of`, so a change shown as zero is never coloured.
        ``good="down"`` flips it, for a figure whose rise is bad news: a yield,
        the VIX. Pass a :class:`~pyhermes.builder.enums.Tone` to state it instead.
        ``arrow=True`` draws the change's direction before it, in the same tone,
        and ``trend`` a series under the value, its summary written with ``fmt``.
        """
        if good not in ("up", "down"):
            raise ValidationError(f"good must be 'up' or 'down', got: {good!r}")
        if arrow and change is None:
            raise ValidationError("an arrow marks a change; pass 'change' to draw one")
        change_fmt = change_fmt or fmt
        if tone == "auto":
            moved = tone_of(change, change_fmt) if change is not None else tone_of(value, fmt)
            flip = {Tone.POSITIVE: Tone.NEGATIVE, Tone.NEGATIVE: Tone.POSITIVE}
            tone = flip.get(moved, moved) if good == "down" else moved
        sublabel = change_fmt(change) if change is not None else ""
        series = None if trend is None else coerce_series(trend, fmt, "card trend")
        card = cls(
            label=label,
            value=fmt(value),
            sublabel=sublabel,
            body=body,
            tone=str(tone),
            trend=series,
        )
        if arrow:
            card.arrow = str(trend_of(change, change_fmt))
        card.validate()
        return card


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
        _validate_tone(self.tone, "kpi.tone")


@dataclass
class Column:
    """
    One column of a :class:`~pyhermes.builder.components.DataTable`.

    Replaces the bare header string, and with it the ``loop.first``
    convention that decided alignment, typeface and weight in the template and
    again in :mod:`pyhermes.builder.textgen`; `data-table.md` records why.

    Both presentation fields default to empty, meaning **resolve** — and the
    resolution reproduces the old convention exactly, so a table built from
    plain strings renders byte-identically to one built before this class
    existed.

    Attributes:
        header: The column's heading. Plain text, escaped on the way out.
        align:  ``left`` / ``center`` / ``right``. Empty resolves from
                :attr:`kind`.
        kind:   ``text``, ``numeric``, ``sparkline`` or ``status``. Empty resolves from
                the *position* (first text, the rest numeric); a ``format`` makes it numeric.
        format: How a raw figure in this column is written (#225).
        tone:   ``auto`` (the sign decides) or a ``Tone`` for its raw figures.
        align_decimal: Pad the figures so their decimal points line up (#226).
        unit:   Printed once, in a units row beneath the heads. Plain text.
        scale:  A :class:`HeatScale` tinting each cell by its raw figure (#227).
        bar:    Draw each raw figure as a bar in its cell (#227).
        width:  A relative weight for this column's share of the width (#271).
        arrow:  Draw each raw figure's direction before it (#319).
        statuses: For ``kind="status"`` (#326), ``{word: tone}``: a dot before the word.
        rule_after: Draw a vertical rule after this column, head and body (#390).
    """

    header: str
    align: str = ""
    kind: str = ""
    format: Callable[[Any], str] | None = None
    tone: str = ""
    align_decimal: bool = False
    unit: str = ""
    scale: "HeatScale | None" = None
    bar: bool = False
    width: int | float | None = None
    arrow: bool = False
    statuses: "Mapping[str, str] | None" = None
    rule_after: bool = False

    def validate(self) -> None:
        _require(self.header, "column.header")
        if not isinstance(self.rule_after, bool):
            raise ValidationError(f"'column.rule_after' is True or False, got: {self.rule_after!r}")
        self._check_statuses()
        if self.width is not None and not (
            isinstance(self.width, (int, float))
            and not isinstance(self.width, bool)
            and self.width > 0
        ):
            raise ValidationError(f"'column.width' must be a positive weight, got: {self.width!r}")
        if self.format is not None and not callable(self.format):
            raise ValidationError(f"'column.format' must be callable, got: {self.format!r}")
        if self.tone != "auto":
            _validate_tone(self.tone, "column.tone")
        if not isinstance(self.unit, str):
            raise ValidationError(f"'column.unit' must be text, got: {self.unit!r}")
        if self.scale is not None:
            if not isinstance(self.scale, HeatScale):
                raise ValidationError(f"'column.scale' must be a HeatScale, got: {self.scale!r}")
            self.scale.validate()
        if self.align and self.align not in tuple(ColumnAlign):
            raise ValidationError(
                f"'column.align' must be one of {[a.value for a in ColumnAlign]}, "
                f"got: {self.align!r}"
            )
        if self.kind and self.kind not in tuple(ColumnKind):
            raise ValidationError(
                f"'column.kind' must be one of {[k.value for k in ColumnKind]}, got: {self.kind!r}"
            )

    def _check_statuses(self) -> None:
        """A status column names its words and their tones, and only a status column does."""
        if (self.kind == ColumnKind.STATUS) != bool(self.statuses):
            raise ValidationError(
                f"column {self.header!r}: kind='status' and statuses={{word: tone}} go together"
            )
        for word, tone in (self.statuses or {}).items():
            if not isinstance(word, str) or not word:
                raise ValidationError(f"column {self.header!r} has a status that is not a word")
            _validate_tone(tone, f"column {self.header} status {word!r}")
            if not tone:
                raise ValidationError(f"column {self.header!r} status {word!r} needs a tone")

    def resolved_kind(self, index: int) -> ColumnKind:
        """
        What this column holds, falling back to its position.

        The position rule *is* the old ``loop.first``: column zero labels the
        row, everything after it carries figures.
        """
        if self.kind:
            return ColumnKind(self.kind)
        if self.format is not None:
            return ColumnKind.NUMERIC
        return ColumnKind.TEXT if index == 0 else ColumnKind.NUMERIC

    def resolved_align(self, index: int) -> ColumnAlign:
        """
        How this column's text sits, falling back to what it holds.

        Note the chain runs through :meth:`resolved_kind` rather than
        straight to the position: a caller who says ``kind="text"`` on the
        third column gets left alignment without also having to say so, which
        is the point of naming the kind at all.
        """
        if self.align:
            return ColumnAlign(self.align)
        kind = self.resolved_kind(index)
        textual = kind in (ColumnKind.TEXT, ColumnKind.STATUS)
        return ColumnAlign.LEFT if textual else ColumnAlign.RIGHT

    def resolved(self, index: int) -> "Column":
        """This column with both presentation fields filled in."""
        return replace(self, align=self.resolved_align(index), kind=self.resolved_kind(index))


@dataclass(frozen=True)
class HeatScale:
    """
    A numeric range a column's figures are tinted across (#227).

    The ends are the theme's, never the caller's: a figure at ``low`` takes the
    surface, one at ``high`` the positive token. With a ``mid``, figures below
    it run from the surface to the negative token instead.

    Attributes:
        low, high: The range. A figure outside it is clamped to the nearer end.
        mid:       Where a diverging scale turns, strictly between the two.
    """

    low: float
    high: float
    mid: float | None = None

    def validate(self) -> None:
        for name in ("low", "high", "mid"):
            value = getattr(self, name)
            if (value is not None or name != "mid") and not is_figure(value):
                raise ValidationError(f"'heat_scale.{name}' must be a number, got: {value!r}")
        if not self.low < self.high:
            raise ValidationError(
                f"'heat_scale.low' ({self.low}) must be below 'heat_scale.high' ({self.high})"
            )
        if self.mid is not None and not self.low < self.mid < self.high:
            raise ValidationError(
                f"'heat_scale.mid' ({self.mid}) must lie strictly between low and high"
            )

    def position(self, value: Any) -> tuple[float, Tone]:
        """Where ``value`` sits, in ``[0, 1]``, and the token it runs toward."""
        if self.mid is not None and value < self.mid:
            return _clamp((self.mid - value) / (self.mid - self.low)), Tone.NEGATIVE
        start = self.low if self.mid is None else self.mid
        return _clamp((value - start) / (self.high - start)), Tone.POSITIVE


def _clamp(fraction: Any) -> float:
    return float(min(1, max(0, fraction)))


@dataclass(frozen=True)
class ColumnGroup:
    """
    A head spanning adjacent columns of a :class:`~pyhermes.builder.components.DataTable`.

    The header tier is the one place a span is admitted (#223): a body cell
    stays unmerged, for the reasons `data-table.md` records.

    Attributes:
        label: The group's heading. Plain text, escaped on the way out.
        span:  How many columns it covers, left to right. At least one.
    """

    label: str
    span: int = 1

    def validate(self) -> None:
        _require(self.label, "column_group.label")
        if isinstance(self.span, bool) or not isinstance(self.span, int) or self.span < 1:
            raise ValidationError(f"'column_group.span' must be a positive int, got: {self.span!r}")


def coerce_groups(groups: "Sequence[ColumnGroup] | None", width: int) -> list[ColumnGroup]:
    """``groups`` validated, and required to cover exactly ``width`` columns."""
    if not groups:
        return []
    for i, group in enumerate(groups):
        if not isinstance(group, ColumnGroup):
            raise ValidationError(
                f"'data_table.groups[{i}]' must be a ColumnGroup, got: {type(group).__name__}"
            )
        group.validate()
    total = sum(group.span for group in groups)
    if total != width:
        raise ValidationError(
            f"'data_table.groups' span {total} columns but the table has {width}; "
            "every column sits under exactly one group."
        )
    return list(groups)


def coerce_column(value: "str | Column", field_name: str = "column") -> Column:
    """
    Accept either a :class:`Column` or a bare header string.

    Lets ``DataTable(headers=["Factor", "1M"])`` keep working untouched while
    accepting a full column spec — the same union-coercion
    :func:`~pyhermes.builder.images.coerce_image` applies to images, and for the
    same reason: a new capability should not cost every existing call site a
    rewrite.
    """
    if isinstance(value, Column):
        value.validate()
        return value
    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name!r} must be a Column or a header string, got: {type(value).__name__}"
        )
    column = Column(header=value)
    column.validate()
    return column


@dataclass
class Cell:
    """
    One cell of a :class:`TableRow`.

    Replaces the bare string, and with it the two index-aligned lists
    (``cells`` and ``colors``) that a validator had to hold in step. That
    shape is what an object exists to replace, for :class:`LinkRow`'s reason:
    **the row has a variable-length part, and variable length is what fields
    cannot express.**

    **On the two colours — they are the caller's claim about a figure, not
    control over appearance.** ``color`` is the field
    ``TableRow.colors`` already set, and CLAUDE.md justifies it as *"the
    caller's statement about the number ('this is down'), not a styling
    choice"*. ``background`` is admitted on exactly that footing: a shaded
    cell in a financial table says *breached its limit*, *stale mark*,
    *estimate* — a claim about the figure, of the same kind its text colour
    already makes. That is what makes this the **fourth** bounded exception
    to the closed colour rule rather than a hole in the palette.

    What it is deliberately **not**: a styling surface. There is no cell
    font, no cell size, no border control, and no per-cell override of
    anything the theme owns for structural reasons. If these fields ever read
    as *"the caller styles cells"*, the closed list has opened and the rule
    is dead — a ``title_color=`` with more steps.

    ``tone`` (#178) is that claim as a word the theme resolves.

    Attributes:
        text:       The cell's contents. Plain text, escaped on the way out.
        align:      Overrides the column's resolved alignment. Empty inherits.
        color:      Text colour, ``#RRGGBB``. Wins over ``tone``.
        background: Cell background, ``#RRGGBB``. Empty leaves the row's
                    alternating tint in place.
        tone:       ``positive`` / ``negative`` / ``neutral``, as the live
                    theme's semantic token. Empty takes the column's kind.
        value:      The raw figure ``text`` was formatted from (#225).
        badge:      A :class:`Badge`, or a label, after the cell's text (#325).
    """

    text: str = ""
    align: str = ""
    color: str = ""
    background: str = ""
    tone: str = ""
    value: Any = None
    badge: "Badge | str | None" = None

    def __post_init__(self) -> None:
        self.badge = coerce_badge(self.badge, "cell.badge")

    def validate(self) -> None:
        if self.align and self.align not in tuple(ColumnAlign):
            raise ValidationError(
                f"'cell.align' must be one of {[a.value for a in ColumnAlign]}, got: {self.align!r}"
            )
        if self.color:
            _validate_color(self.color, "cell.color")
        if self.background:
            _validate_color(self.background, "cell.background")
        _validate_tone(self.tone, "cell.tone")

    @classmethod
    def from_number(
        cls,
        value: Any,
        fmt: Callable[[Any], str] = formats.number,
        *,
        tone: str = "auto",
        align: str = "",
        background: str = "",
    ) -> "Cell":
        """
        A cell formatted once, with a tone that cannot disagree with its text.

        ``tone="auto"`` reads the tone off the sign via :func:`tone_of`, which
        is handed the same ``fmt``, so ``0.00%`` is neutral whatever the
        unrounded sign was. Pass a :class:`~pyhermes.builder.enums.Tone` to state
        it instead — a falling VIX is good news.
        """
        resolved = tone_of(value, fmt) if tone == "auto" else tone
        cell = cls(text=fmt(value), align=align, background=background, tone=resolved, value=value)
        cell.validate()
        return cell

    def resolved_align(self, column_align: str) -> str:
        """This cell's alignment, falling back to its column's resolved one."""
        return self.align or column_align


def tone_of(value: Any, fmt: Callable[[Any], str] | None = None) -> Tone:
    """
    The tone a figure's sign implies: up is positive, down negative.

    Zero, ``None`` and NaN are neutral, and so is a figure that ``fmt``
    renders as zero — so the colour cannot contradict the string beside it.
    """
    if fmt is not None and formats.displays_zero(fmt(value)):
        return Tone.NEUTRAL
    if value is None or value != value:  # NaN is the one value unequal to itself
        return Tone.NEUTRAL
    if value > 0:
        return Tone.POSITIVE
    return Tone.NEGATIVE if value < 0 else Tone.NEUTRAL


def trend_of(value: Any, fmt: Callable[[Any], str] | None = None) -> Trend:
    """
    The direction a change's sign implies, on :func:`tone_of`'s rule (#319).

    A figure ``fmt`` renders as zero is flat, so the arrow cannot contradict the
    string beside it; so are zero, ``None`` and NaN.
    """
    return {Tone.POSITIVE: Trend.UP, Tone.NEGATIVE: Trend.DOWN}.get(tone_of(value, fmt), Trend.FLAT)


#: What a brand tone's name may be: a lowercase word the theme declares (#387).
TONE_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")


#: How a frame is drawn, the one vocabulary for a section, a ``Callout`` and a table (#390).
FRAMES = ("solid", "dashed")


def _validate_frame(value: str, field_name: str) -> None:
    """Refuse a frame style outside :data:`FRAMES`."""
    if value not in FRAMES:
        raise ValidationError(f"{field_name!r} must be one of {list(FRAMES)}, got: {value!r}")


def _validate_tone(value: str, field_name: str) -> None:
    """
    Refuse a tone that is not a word: a semantic one, or a name a theme may declare.

    Whether a brand tone's name is declared is the document's question, asked
    when its section is added, because only the document knows its theme.
    """
    if value and not (isinstance(value, str) and TONE_NAME.match(value)):
        raise ValidationError(
            f"{field_name!r} must be one of {[t.value for t in Tone]} or a tone the theme "
            f"declares, got: {value!r}. A tone is a word the theme resolves; pass a hex as "
            "'color' instead."
        )


def coerce_cell(value: "str | Cell", field_name: str = "cell") -> Cell:
    """
    Accept a :class:`Cell`, a bare string, or a raw figure its column formats.

    ``TableRow(cells=["Value", "+1.8%"])`` keeps working untouched — the same
    union-coercion :func:`coerce_column` and
    :func:`~pyhermes.builder.images.coerce_image` apply, for the same reason.
    """
    if isinstance(value, Cell):
        value.validate()
        return value
    if is_figure(value):
        return Cell(value=value)
    if isinstance(value, (list, tuple)) and value and all(map(is_figure, value)):
        return Cell(value=tuple(value))
    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name!r} must be a Cell, a string or a number, got: {type(value).__name__}"
        )
    return Cell(text=value)


def is_figure(value: Any) -> bool:
    """Whether ``value`` is a raw number a column may format: never a bool."""
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


@dataclass
class TableRow:
    """
    A single row in a data table.

    ``cells`` accepts bare strings or :class:`Cell` objects, mixed freely,
    and coerces at construction — so ``row.cells`` is always a list of
    ``Cell``.

    ``colors`` survives as the **flat spelling**: the index-aligned list this
    row took before :class:`Cell` existed, kept working because it is the
    common call path. It is an ``InitVar`` — a constructor argument only,
    absent from ``fields()``, ``repr`` and ``==`` — so the ``Cell`` is the
    single owner of a cell's colour and the two spellings cannot drift.
    Passing ``colors`` *and* a ``Cell`` that carries its own ``color`` raises
    rather than silently picking one, exactly as ``EmailMetadata`` does for
    its flat region keywords.

    ``kind`` says what the row *is* — see :class:`~pyhermes.builder.enums.RowKind`.
    It is chrome rather than data: a total is ruled and bolded from theme
    tokens, and unlike a cell's colour it takes nothing from the caller but
    the word. A ``subhead`` may be given a single cell and is padded to the
    table's width, because a merged cell has no honest plain-text projection
    and making the caller write the empty ones would be ceremony.
    """

    cells: list[Any] = field(default_factory=list)
    colors: InitVar[list[str] | None] = None
    kind: str = RowKind.DATA

    def __post_init__(self, colors: list[str] | None) -> None:
        if self.kind not in tuple(RowKind):
            raise ValidationError(
                f"'table_row.kind' must be one of {[k.value for k in RowKind]}, got: {self.kind!r}"
            )
        self.cells = [
            coerce_cell(cell, f"table_row.cells[{i}]") for i, cell in enumerate(self.cells)
        ]
        if colors:
            if len(colors) != len(self.cells):
                raise ValidationError(
                    f"'table_row.colors' must be empty or the same length as 'cells' "
                    f"({len(self.cells)}), got {len(colors)}."
                )
            for cell, color in zip(self.cells, colors, strict=True):
                if color and cell.color:
                    raise ValidationError(
                        "'table_row.colors' and a Cell's own 'color' both set for the same "
                        "cell; pass one or the other, not both."
                    )
                if color:
                    _validate_color(color, "table_row.color")
                    cell.color = color

    def validate(self) -> None:
        """Re-check every cell. Coercion already validated at construction."""
        for cell in self.cells:
            cell.validate()


@dataclass
class Footnote:
    """
    A note attached to one place in the copy, numbered by the document (#182).

    **The text is plain, and escaped on the way out**, for ``disclosure``'s
    reason: the raw-HTML set stays closed at five, and widening a plain field
    later is additive where narrowing one is not. So a note carries no link.

    Its place in the copy is a marker, ``[^1]``, written in the field of the
    component that carries it. ``number`` is the document's to assign.
    """

    text: str
    number: int | None = field(default=None, init=False, compare=False, repr=False)

    def validate(self) -> None:
        _require(self.text, "footnote.text")


def coerce_notes(
    notes: Sequence[Footnote | str] | None, copy: Sequence[str], owner: str
) -> list[Footnote]:
    """
    ``notes`` as validated ``Footnote`` objects, each called once from ``copy``.

    A bare string is a note's text. Raises ``ValidationError`` on an empty
    note, or on markers in ``copy`` that do not call ``[^1]`` to ``[^n]`` once.
    """
    coerced = [note if isinstance(note, Footnote) else Footnote(note) for note in notes or ()]
    for note in coerced:
        note.validate()
    check_markers(copy, len(coerced), owner)
    return coerced


@dataclass
class NumberedItem:
    """A single item in a numbered list; ``notes`` are called from ``body``."""

    number: str
    title: str
    body: str
    notes: list[Footnote | str] = field(default_factory=list)

    def validate(self) -> None:
        _require(self.title, "numbered_item.title")
        _require(self.body, "numbered_item.body")
        refuse_top_headings(self.body, "numbered_item.body")
        self.notes = list[Footnote | str](
            coerce_notes(self.notes, [self.body], f"NumberedItem {self.title!r}")
        )

    def footnotes(self) -> list[Footnote]:
        """This item's notes, once :meth:`validate` has coerced them."""
        return [note for note in self.notes if isinstance(note, Footnote)]


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
