"""
Data models for the email builder.

Uses dataclasses for structured configuration with validation.
These models define the shape of data flowing through the builder —
metadata for the email skeleton, typed data for each component, etc.
"""

import re
from dataclasses import InitVar, dataclass, field, fields
from typing import TYPE_CHECKING, Any

from .enums import ColumnAlign, ColumnKind, RowKind, SizeTheme
from .exceptions import ValidationError

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
    A blank :class:`~svc.builder.regions.Banner`.

    Imported inside the function because ``regions`` imports this module for
    its validators — the same lazy-cycle rule ``images`` follows.
    """
    from .regions import Banner

    return Banner()


def _default_footer() -> "Footer":
    """A default :class:`~svc.builder.regions.Footer`. Same lazy-cycle rule."""
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
class EmailMetadata:
    """
    Email-level metadata: the facts an email is built from.

    **Facts live here; masthead presentation lives on the header.** Subject,
    preheader, firm, campaign, dates and the outbound URLs are things that are
    *true of the email*; the background image, the logo and its resolution
    chains are one way of *presenting* them, and belong to
    :class:`~svc.builder.regions.Banner`. The header is handed the facts at
    render time and cannot contradict them.

    ``header_disclaimer`` sits on the email side of that line deliberately:
    it is displayed in the masthead, but it is legal copy and legal copy is a
    fact about the email. The footer's disclaimer and contact card copy are now
    presentation — they belong to :class:`~svc.builder.regions.Footer` (pass a
    ``Footer(disclaimer=...)`` to set the fine-print, or use a
    :class:`~svc.builder.components.ContactBlock` component for the contact
    card).

    Every remaining field maps to a variable in ``templates/base.html``.

    The flat region keyword arguments are still accepted and build the region
    for you, so an email written before the header split is unchanged: four for
    the masthead (``logo_url``, ``logo_alt``, ``logo_width``,
    ``header_bg_image_url``). For the footer, ``unsubscribe_label`` and
    ``view_in_browser_label`` are still accepted as flat keywords.
    Passing one *and* the region it belongs to is an error rather than a
    silent precedence rule.
    """

    email_subject: str = ""
    preheader_text: str = ""
    #: The language the email is written in, as a BCP 47 tag — the ``lang``
    #: attribute on the root element.  A *fact*: what language an email is
    #: written in is true of the email, not a way of presenting it, so it
    #: sits beside ``firm_name`` rather than on a region.  It is what a
    #: screen reader picks its pronunciation from, which is why the default
    #: is a real claim rather than an absence: an unset ``lang`` leaves the
    #: reader to guess, and a wrong one is confidently wrong.
    language: str = "en"
    header_disclaimer: str = ""
    firm_name: str = ""
    campaign_name: str = ""
    #: The desk within the firm, e.g. "Rates Strategy". A *fact*, decided
    #: rather than assumed: a department is who the email is from, the same
    #: kind of truth as ``firm_name``. Putting it on the banner would let two
    #: renders of one email disagree about its sender. Optional — empty
    #: collapses the line entirely rather than reserving space for it.
    department: str = ""
    date_range: str = ""
    issue_label: str = ""
    current_year: str = ""
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

    #: Every typeface the email renders with. A
    #: :class:`~svc.builder.typography.FontTheme` instance or the name of a
    #: curated preset — ``theme``'s width rather than ``size_theme``'s
    #: narrowness, and the asymmetry argument runs the *other way* here.
    #: Density is names-only because an untested scheme interacts with the
    #: clipping limit, the Word engine and the mobile collapse at once;
    #: a custom ``FontTheme`` is safe **by construction**, because the
    #: terminal-generic rule means Outlook always walks a chain the caller
    #: curated down to a websafe floor. A house brand face with fallbacks is
    #: the axis's core use case. See :mod:`svc.builder.typography`.
    font_theme: "FontTheme | str" = field(default_factory=_default_fonts)

    # Back-compatible region keywords. InitVars, so they are constructor
    # arguments only: they never become attributes and never appear in
    # ``fields()``, ``repr`` or ``==`` — the region is the single owner.
    logo_url: InitVar["str | EmailImage | None"] = None
    logo_alt: InitVar["str | None"] = None
    logo_width: InitVar["int | None"] = None
    header_bg_image_url: InitVar["str | EmailImage | None"] = None
    unsubscribe_label: InitVar["str | None"] = None
    view_in_browser_label: InitVar["str | None"] = None

    #: Email-level facts the strip renders. One today, and it stays a fact
    #: rather than moving onto the region with the box's presentation: it is
    #: legal copy that belongs to the *email*, the same call the footer's
    #: two URLs get.
    HEADER_FACTS = ("header_disclaimer",)

    #: Email-level facts the masthead renders. Passed *down* to it; the
    #: banner layers them over its own context, so it cannot shadow one.
    BANNER_FACTS = (
        "firm_name",
        "campaign_name",
        "department",
        "date_range",
        "issue_label",
    )

    #: Email-level facts the footer region renders, on the same terms. The
    #: two URLs are here rather than on the region because an unsubscribe
    #: address is a property of the mailing, not a way of wording it — and
    #: :meth:`validate` already checks both schemes.
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
        from .sizing import resolve_size_scheme
        from .theming import resolve_theme
        from .typography import resolve_font_theme

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

        _validate_language(self.language, "metadata.language")

        # Resolve only to check: a preset name that names nothing is a typo,
        # and a typo belongs to construction, not to render. The field keeps
        # whatever the caller passed — Email.render() is the one resolution
        # point that turns it into a concrete Theme.
        resolve_theme(self.theme)
        resolve_size_scheme(self.size_theme)
        resolve_font_theme(self.font_theme)

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
        for fname in ("unsubscribe_url", "view_in_browser_url"):
            _validate_url(getattr(self, fname), f"metadata.{fname}")

    def header_facts(self) -> dict[str, Any]:
        """The email-level facts the strip renders."""
        return {name: getattr(self, name) for name in self.HEADER_FACTS}

    def banner_facts(self) -> dict[str, Any]:
        """The email-level facts a masthead region renders."""
        return {name: getattr(self, name) for name in self.BANNER_FACTS}

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
        value two sources — and ``size_theme`` and ``font_theme`` are excluded
        for exactly the same reason, since the resolved scheme and the
        resolved typefaces ride the same binder.
        """
        skip = {"header", "banner", "footer", "theme", "size_theme", "font_theme"}
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in skip}


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
        copyright: Free-form **plain text**, escaped on output. Empty means
                   *resolve to* ``© {current_year} {firm_name}`` from the
                   email's own facts, which is what makes an unset row
                   byte-identical to the pre-#100 render.
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
class Column:
    """
    One column of a :class:`~svc.builder.components.DataTable`.

    Replaces the bare header string, and with it the ``loop.first``
    convention that used to decide four things at once — alignment, typeface,
    weight, and (in another module entirely) the plain-text column alignment.
    That convention was correct and compact; what it could not be was
    *extended*, and the tell was that a fifth reader in
    :mod:`svc.builder.textgen` had to re-derive it to keep the two
    projections agreeing.

    Both presentation fields default to empty, meaning **resolve** — and the
    resolution reproduces the old convention exactly, so a table built from
    plain strings renders byte-identically to one built before this class
    existed.

    Attributes:
        header: The column's heading. Plain text, escaped on the way out.
        align:  ``left`` / ``center`` / ``right``. Empty resolves from
                :attr:`kind`.
        kind:   ``text`` or ``numeric``. Empty resolves from the column's
                *position*: the first column is text, the rest are numeric —
                which is what ``loop.first`` meant.
    """

    header: str
    align: str = ""
    kind: str = ""

    def validate(self) -> None:
        _require(self.header, "column.header")
        if self.align and self.align not in tuple(ColumnAlign):
            raise ValidationError(
                f"'column.align' must be one of {[a.value for a in ColumnAlign]}, "
                f"got: {self.align!r}"
            )
        if self.kind and self.kind not in tuple(ColumnKind):
            raise ValidationError(
                f"'column.kind' must be one of {[k.value for k in ColumnKind]}, got: {self.kind!r}"
            )

    def resolved_kind(self, index: int) -> ColumnKind:
        """
        What this column holds, falling back to its position.

        The position rule *is* the old ``loop.first``: column zero labels the
        row, everything after it carries figures.
        """
        if self.kind:
            return ColumnKind(self.kind)
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
        return (
            ColumnAlign.LEFT if self.resolved_kind(index) is ColumnKind.TEXT else ColumnAlign.RIGHT
        )

    def resolved(self, index: int) -> "Column":
        """This column with both presentation fields filled in."""
        return Column(
            header=self.header,
            align=self.resolved_align(index),
            kind=self.resolved_kind(index),
        )


def coerce_column(value: "str | Column", field_name: str = "column") -> Column:
    """
    Accept either a :class:`Column` or a bare header string.

    Lets ``DataTable(headers=["Factor", "1M"])`` keep working untouched while
    accepting a full column spec — the same union-coercion
    :func:`~svc.builder.images.coerce_image` applies to images, and for the
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

    The theme remains the fallback: an unset colour takes the token the
    column's kind implies, and an unset background leaves the row's
    alternating tint alone.

    Attributes:
        text:       The cell's contents. Plain text, escaped on the way out.
        align:      Overrides the column's resolved alignment. Empty inherits.
        color:      Text colour, ``#RRGGBB``. Empty takes the theme's token.
        background: Cell background, ``#RRGGBB``. Empty leaves the row's
                    alternating tint in place.
    """

    text: str = ""
    align: str = ""
    color: str = ""
    background: str = ""

    def validate(self) -> None:
        if self.align and self.align not in tuple(ColumnAlign):
            raise ValidationError(
                f"'cell.align' must be one of {[a.value for a in ColumnAlign]}, got: {self.align!r}"
            )
        if self.color:
            _validate_color(self.color, "cell.color")
        if self.background:
            _validate_color(self.background, "cell.background")

    def resolved_align(self, column_align: str) -> str:
        """This cell's alignment, falling back to its column's resolved one."""
        return self.align or column_align


def coerce_cell(value: "str | Cell", field_name: str = "cell") -> Cell:
    """
    Accept either a :class:`Cell` or a bare string.

    ``TableRow(cells=["Value", "+1.8%"])`` keeps working untouched — the same
    union-coercion :func:`coerce_column` and
    :func:`~svc.builder.images.coerce_image` apply, for the same reason.
    """
    if isinstance(value, Cell):
        value.validate()
        return value
    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name!r} must be a Cell or a string, got: {type(value).__name__}"
        )
    return Cell(text=value)


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

    ``kind`` says what the row *is* — see :class:`~svc.builder.enums.RowKind`.
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
